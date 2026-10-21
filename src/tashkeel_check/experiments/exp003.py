"""EXP-003: 어려운 시험지(synthetic-hard)에서 조건 C0~C3를 99% 정확도 기준으로 비교한다(ADR-017).

- 세는 단위는 이름 부분이 나올 때마다다. 안전 정확도(말없이 틀린 이름이 없음)와 엄격 정확도(기대 처분과 정확히
  일치)를 같이 낸다. 정의는 scoring_v2, docs/evaluation.md 6.4절.
- 판정은 실행 전에 고정해 코드로 둔다. 조건 비교 판정은 점추정 ≥ 0.99, "서비스 기준 99% 달성" 문구(service_claim)는
  반복마다의 Clopper–Pearson 한쪽 95% 하한 중 가장 낮은 값과 문서 단위 부트스트랩 한쪽 95% 하한이 모두 0.99 이상일 때만.
- 실행 장치(재개·동시 실행·사용량 확인)는 EXP-002와 같다(harness, ADR-016).
- 참고 조건 C1p0(C1 + 옛 지시문 p0)는 반복 1회에만 돌리고 판정에 쓰지 않는다. 반복은 단계적이다: 반복 1회 뒤
  C1~C3의 두 정확도가 하나라도 회색 구간 [0.98, 0.995)에 있으면 반복 2·3을 돈다(ADR-020, 실행 전 고정).
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from .. import __version__
from ..analyzer import AnalyzeFn, analyzer_version
from ..config import CONDITIONS, Settings
from ..data.synthetic_hard import GENERATOR_VERSION, GOLD_FORMAT
from ..prompts import prompt_hash
from ..romanize import MATCHER_VERSION, STRICT_VERSION
from ..scoring_v2 import C0_RULE, SAFETY_KINDS, SCORING_VERSION, STRICT_ONLY_KINDS, TRANSLATION_RULE
from . import harness
from .harness import (  # noqa: F401  (EXP-002 모듈과 같은 이름으로 쓴다)
    LEDGER_FILE,
    ORDER,
    PAUSE_LABELS,
    PLAN_FILE,
    PLAN_SETTINGS,
    STOP_FILE,
    SUMMARY_FILE,
    RunStatus,
    _bootstrap,
    _paired_diff,
    _pooled,
    bootstrap_lower,
    clopper_pearson_lower,
    done_runs,
    format_status,
    is_api_failure,
    latest_run_dir,
    load_plan,
    read_ledger,
    status,
)

PROMPT_VERSION = "p1"
EVIDENCE_RULE = "v2"
RATE_DEFS = {
    # 지표: (분자 키, 분모 키)
    "strict_accuracy": ("n_strict_correct", "n_scored_units"),
    "safety_accuracy": ("n_safety_ok", "n_scored_units"),
    # 민감도: 판단이 갈릴 수 있는 정답(arguable)을 뺀 값. 판정에는 쓰지 않는다
    "strict_accuracy_nonarguable": ("n_strict_correct_nonarguable", "n_scored_units_nonarguable"),
    "safety_accuracy_nonarguable": ("n_safety_ok_nonarguable", "n_scored_units_nonarguable"),
    "doc_strict_all_correct_rate": ("doc_strict_all_correct", "n_docs"),
    "doc_safety_all_ok_rate": ("doc_safety_all_ok", "n_docs"),
    "hold_must_include_rate": ("n_hold_must_include_ok", "n_hold_must_include"),
    "lookalike_flag_rate": ("n_lookalike_flagged_as_name", "n_lookalike_tokens"),
}
# 합격선(2026-10-21 사용자 확정, EXP-003 실행 전 고정): 두 정확도 모두 99% 이상(점추정)
PASS_BAR = {"strict_accuracy": ("min", 0.99), "safety_accuracy": ("min", 0.99)}
CLAIM_LEVEL = 0.99
CLAIM_ALPHA = 0.05
TOOL_CONDITIONS = ("C2", "C3")
COMPARISONS = (("C0", "C1"), *(("C1", c) for c in TOOL_CONDITIONS))
# 참고 조건(2026-10-21 사용자 결정, ADR-020): 지시문 변경과 시험지 변경을 떼어 본다. 판정에 쓰지 않는다
REFERENCE_ARMS = {"C1p0": ("C1", "p0")}  # 라벨 → (조건, 지시문 판)
ARMS = (*CONDITIONS, *REFERENCE_ARMS)
ARM_REPEATS = {"C1p0": 1}  # 참고 조건은 반복 1회에만 돈다
REFERENCE_COMPARISONS = (("C1", "C1p0"),)  # 반복 1회(r0)끼리 비교한다
# 단계적 반복(실행 전 고정, ADR-020): 반복 STAGE_AFTER회 뒤 아래 조건·정확도의 점추정이 하나라도
# STAGE_BAND 안이면 나머지 반복을 돌고, 하나도 없으면 거기서 마친다
STAGE_AFTER = 1
STAGE_BAND = (0.98, 0.995)  # [이상, 미만)
STAGE_CONDITIONS = ("C1", *TOOL_CONDITIONS)
REPEATS = 3
SUM_KEYS = [
    *(f"n_err_{k}" for k in SAFETY_KINDS),
    *(f"n_strict_only_{k}" for k in STRICT_ONLY_KINDS),
    "n_translation_not_found",
    "n_person_inconsistent",
    "n_evidence_failed",
    "n_invalid_items",
    "n_items",
    "n_scored_units",
    "n_scored_arabic_tokens",
]


def _rate_entry(runs: list[dict], num: str, den: str) -> dict:
    reps = sorted({r["_repeat"] for r in runs})
    per_rep = [v for k in reps if (v := _pooled([r for r in runs if r["_repeat"] == k], num, den)) is not None]
    return {
        "pooled": _pooled(runs, num, den),
        "repeat_range": [min(per_rep), max(per_rep)] if per_rep else None,
        "doc_bootstrap_95": _bootstrap(runs, num, den),
    }


def service_claim(runs: list[dict]) -> dict:
    """'서비스 기준 99% 달성'이라고 쓸 수 있는지. 두 정확도 모두에서 점추정, 반복마다의 한쪽 95% Clopper–Pearson 하한 중
    가장 낮은 값, 문서 단위 부트스트랩 한쪽 95% 하한이 모두 0.99 이상이어야 한다."""
    out: dict = {"level": CLAIM_LEVEL, "alpha_one_sided": CLAIM_ALPHA}
    holds = True
    for name in PASS_BAR:
        num, den = RATE_DEFS[name]
        reps = sorted({r["_repeat"] for r in runs})
        per_rep = []
        for k in reps:
            rr = [r for r in runs if r["_repeat"] == k]
            n, ok = sum(r.get(den) or 0 for r in rr), sum(r.get(num) or 0 for r in rr)
            per_rep.append(
                {"repeat": k, "n": n, "errors": n - ok, "cp_lower": clopper_pearson_lower(ok, n, CLAIM_ALPHA)}
            )
        lows = [p["cp_lower"] for p in per_rep if p["cp_lower"] is not None]
        point = _pooled(runs, num, den)
        boot = bootstrap_lower(runs, num, den)
        ok_all = (
            point is not None
            and point >= CLAIM_LEVEL
            and bool(lows)
            and min(lows) >= CLAIM_LEVEL
            and (boot is None or boot >= CLAIM_LEVEL)
        )
        out[name] = {
            "pooled": point,
            "per_repeat": per_rep,
            "worst_cp_lower": min(lows) if lows else None,
            "doc_bootstrap_lower_95": boot,
            "claim": ok_all,
        }
        holds = holds and ok_all
    out["claim"] = holds
    return out


def _by_case_type(runs: list[dict]) -> dict:
    total: dict[str, Counter] = {}
    for r in runs:
        for ct, v in (r.get("by_case_type") or {}).items():
            total.setdefault(ct, Counter()).update(v)
    return {
        ct: {
            "n": c["n"],
            "strict_accuracy": round(c["strict"] / c["n"], 4) if c["n"] else None,
            "safety_accuracy": round(c["safety_ok"] / c["n"], 4) if c["n"] else None,
        }
        for ct, c in sorted(total.items())
    }


def aggregate(runs_by_condition: dict[str, list[dict]]) -> dict:
    summary = {}
    for cond, runs in runs_by_condition.items():
        entry: dict = {
            "n_runs": len(runs),
            "n_docs": len({r["_doc_id"] for r in runs}),
            "repeats": len({r["_repeat"] for r in runs}),
        }
        for name, (num, den) in RATE_DEFS.items():
            entry[name] = _rate_entry(runs, num, den)
        for key in SUM_KEYS:
            vals = [v for r in runs if (v := r.get(key)) is not None]
            entry[key] = {"total": sum(vals), "mean_per_run": round(sum(vals) / len(vals), 3)} if vals else None
        entry["service_claim"] = service_claim(runs)
        entry["by_case_type"] = _by_case_type(runs)
        usage = [r.get("usage", {}) for r in runs]
        entry["tokens_in"] = sum(u.get("input_tokens", 0) for u in usage)
        entry["tokens_out"] = sum(u.get("output_tokens", 0) for u in usage)
        entry["failed_runs"] = sum(not r.get("valid_output") for r in runs)
        tool = [r["tool"] for r in runs if r.get("tool")]
        if tool:
            entry["tool_calls_mean"] = round(sum(t["calls"] for t in tool) / len(runs), 3)
        summary[cond] = entry
    return summary


def compare(runs_by_condition: dict[str, list[dict]]) -> dict:
    """조건 쌍마다 두 정확도의 차이(앞 조건 − 뒤 조건)와 같은 문서를 함께 뽑는 부트스트랩 95% 구간.

    참고 비교(C1 − C1p0)는 참고 조건이 반복 1회뿐이라 C1도 반복 1회(r0)만 쓴다. 판정에 쓰지 않는다.
    """
    out: dict[str, dict] = {}
    for a, b in COMPARISONS:
        if a in runs_by_condition and b in runs_by_condition:
            out[f"{a}-{b}"] = {
                name: _paired_diff(runs_by_condition[a], runs_by_condition[b], *RATE_DEFS[name]) for name in PASS_BAR
            }
    for a, b in REFERENCE_COMPARISONS:
        if a in runs_by_condition and b in runs_by_condition:
            first = [r for r in runs_by_condition[a] if r["_repeat"] == 0]
            ref: dict = {name: _paired_diff(first, runs_by_condition[b], *RATE_DEFS[name]) for name in PASS_BAR}
            out[f"{a}-{b}"] = {**ref, "reference": True, "repeats": [0]}
    return out


def _checks(entry: dict) -> dict[str, bool | None]:
    out: dict[str, bool | None] = {}
    for name, (_, bar) in PASS_BAR.items():
        v = entry[name]["pooled"]
        out[name] = None if v is None else v >= bar
    return out


def _improves(diff: dict | None) -> bool:
    """C1 − 도구 조건 차이의 95% 구간이 0을 포함하지 않고 도구 조건이 높은 쪽에 있는지."""
    ci = (diff or {}).get("doc_bootstrap_95")
    return ci is not None and ci[1] < 0


def judge(summary: dict, comparisons: dict) -> dict:
    """사전 등록한 판정. 판정별 의미는 docs/experiments/EXP-003.md에 실행 전에 적었다.

    - stop: C1(지시만)이 두 99% 기준을 넘었다. 어려운 시험지에서도 지시만으로 충족된다(G4상 단독 제품 근거가 약함)
    - pass: C1은 못 넘었고, 도구 조건이 두 기준을 넘으며 C1이 못 넘은 기준을 우연 이상으로 고쳤다 → 단계 2
    - fail: 그 밖. 프롬프트 재설계나 단계 3 검증자를 검토한다. 분석기가 쓸모없다는 뜻은 아니다
    """
    checks = {c: _checks(e) for c, e in summary.items() if c != "C0" and c not in REFERENCE_ARMS}
    claims = {c: e["service_claim"]["claim"] for c, e in summary.items()}
    if "C1" not in checks:
        return {"decision": None, "reason": "C1 결과가 없어 판정하지 않는다", "checks": checks, "service_claim": claims}
    c1 = checks["C1"]
    if all(c1.values()):
        return {
            "decision": "stop",
            "reason": "C1(지시만)이 두 99% 기준을 넘었다. 어려운 시험지에서도 지시만으로 충족",
            "checks": checks,
            "service_claim": claims,
        }
    c1_failed = [name for name, ok in c1.items() if not ok]
    passing = [
        c
        for c in TOOL_CONDITIONS
        if c in checks
        and all(checks[c].values())
        and all(_improves(comparisons.get(f"C1-{c}", {}).get(n)) for n in c1_failed)
    ]
    if passing:
        return {
            "decision": "pass",
            "reason": f"C1은 99%에 못 미치고, {', '.join(passing)}이 두 기준을 넘으며 C1이 못 넘은 기준"
            f"({', '.join(c1_failed)})을 우연 이상으로 고쳤다",
            "passing": passing,
            "checks": checks,
            "service_claim": claims,
        }
    return {
        "decision": "fail",
        "reason": "C1도 도구 조건도 99%에 못 미치거나 차이가 우연 수준이다",
        "checks": checks,
        "service_claim": claims,
    }


def arm(label: str, settings: Settings) -> tuple[str, Settings]:
    """라벨 → (실제 조건, 설정). 참고 조건은 지시문 판만 바꾼다(근거 검사·채점은 같다)."""
    if label in REFERENCE_ARMS:
        cond, version = REFERENCE_ARMS[label]
        return cond, settings.model_copy(update={"prompt_version": version})
    return label, settings


def stage_gate(plan: dict, runs_by_condition: dict[str, list[dict]]) -> dict:
    """사전 등록한 단계 규칙. 반복 STAGE_AFTER회의 점추정이 하나라도 회색 구간이면 계속한다.

    값이 없는(실행이 없거나 분모가 0인) 지표는 판단할 수 없으므로 계속하는 쪽으로 본다.
    """
    lo, hi = STAGE_BAND
    values: dict[str, dict[str, float | None]] = {}
    gray = []
    for cond in STAGE_CONDITIONS:
        values[cond] = {}
        for name in PASS_BAR:
            v = _pooled(runs_by_condition.get(cond, []), *RATE_DEFS[name])
            values[cond][name] = v
            if v is None or lo <= v < hi:
                gray.append(f"{cond}.{name}")
    return {
        "decision": "continue" if gray else "stop",
        "in_band": gray,
        "values": values,
        "rule": plan.get("stage_rule"),
    }


def make_plan(
    docs_dir: str | Path,
    doc_paths: list[Path],
    conditions: tuple[str, ...],
    repeats: int,
    settings: Settings,
    label: str,
) -> dict:
    """재개할 때 그대로여야 하는 설정. 채점·생성기·지시문 판까지 고정한다."""
    plan = {
        "experiment": "EXP-003",
        "docs_dir": str(docs_dir),
        "docs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in doc_paths},
        "conditions": list(conditions),
        "repeats": repeats,
        "order": ORDER,
        "model": settings.model,
        "model_label": label,
        "settings": {k: getattr(settings, k) for k in PLAN_SETTINGS},
        "prompt_version": settings.prompt_version,
        "prompt_hash": {c: prompt_hash(cond, s.prompt_version) for c in conditions for cond, s in [arm(c, settings)]},
        "reference_arms": {c: list(REFERENCE_ARMS[c]) for c in conditions if c in REFERENCE_ARMS},
        "arm_repeats": {c: n for c, n in ARM_REPEATS.items() if c in conditions},
        "stage_rule": {
            "after_repeat": STAGE_AFTER,
            "band": list(STAGE_BAND),
            "conditions": list(STAGE_CONDITIONS),
            "rates": list(PASS_BAR),
            "continue_if": "any value in [band[0], band[1]) or missing",
        },
        "evidence_rule": settings.evidence_rule,
        "matcher_version": MATCHER_VERSION,
        "scoring": {
            "scoring": SCORING_VERSION,
            "strict_spelling": STRICT_VERSION,
            "translation": TRANSLATION_RULE,
            "c0": C0_RULE,
        },
        "generator": GENERATOR_VERSION,
        "gold_format": GOLD_FORMAT,
        "pass_bar": {name: bar for name, (_, bar) in PASS_BAR.items()},
        "analyzer": analyzer_version(),
        "package_version": __version__,
    }
    return json.loads(json.dumps(plan))


def report(plan: dict, runs_by_condition: dict[str, list[dict]]) -> dict:
    summary, comparisons = aggregate(runs_by_condition), compare(runs_by_condition)
    return {
        "summary": summary,
        "comparisons": comparisons,
        "pass_bar": {name: {"kind": kind, "bar": bar} for name, (kind, bar) in PASS_BAR.items()},
        "verdict": judge(summary, comparisons),
    }


def _configure(settings: Settings) -> Settings:
    return settings.model_copy(update={"prompt_version": PROMPT_VERSION, "evidence_rule": EVIDENCE_RULE})


SPEC = harness.Spec(
    name="EXP-003",
    plan=make_plan,
    report=report,
    configure=_configure,
    arm=arm,
    stage_after=STAGE_AFTER,
    stage_gate=stage_gate,
)


def write_summary(run_dir: str | Path) -> Path:
    return harness.write_summary(SPEC, run_dir)


def run(
    docs_dir: str | Path,
    out_root: str | Path,
    model_factory: Callable[[], BaseChatModel],
    settings: Settings,
    conditions: tuple[str, ...] = ARMS,
    repeats: int | None = None,
    limit: int | None = None,
    *,
    run_dir: str | Path | None = None,
    workers: int = 1,
    max_runs: int | None = None,
    token_budget: int | None = None,
    analyze_fn: AnalyzeFn | None = None,
    session_info: dict | None = None,
) -> RunStatus:
    return harness.run(
        SPEC,
        docs_dir,
        out_root,
        model_factory,
        settings,
        conditions,
        repeats or REPEATS,
        limit,
        run_dir=run_dir,
        workers=workers,
        max_runs=max_runs,
        token_budget=token_budget,
        analyze_fn=analyze_fn,
        session_info=session_info,
    )


ERROR_COLUMNS = [
    "condition",
    "doc_id",
    "repeat",
    "unit_id",
    "person_id",
    "slot",
    "segment_id",
    "arabic",
    "case_types",
    "arguable",
    "expected",
    "expected_spelling",
    "disposition",
    "adopted",
    "error",
    "auto_judged",
    "human_check",
]


def export_errors(run_dir: str | Path, n_correct_sample: int = 50, seed: int = 0) -> Path:
    """사람 확인용 표(errors.csv): 자동 판정 오류 전부와, 정답으로 판정한 것에서 seed 고정 표본.

    99% 수준에서는 채점이 몇 건만 틀려도 판정이 바뀐다. 실행 뒤 이 표의 오류를 전부 사람이 확인한다(사전 등록).
    """
    run_dir = Path(run_dir)
    rows: list[dict] = []
    correct: list[dict] = []
    for (cond, doc_id, rep), _ in sorted(done_runs(read_ledger(run_dir)).items()):
        path = run_dir / cond / doc_id / f"r{rep}" / "metrics.json"
        units = json.loads(path.read_text(encoding="utf-8")).get("units", []) if path.exists() else []
        for u in units:
            row = {"condition": cond, "doc_id": doc_id, "repeat": rep, **u, "case_types": " ".join(u["case_types"])}
            (rows if u["error"] else correct).append(row)
    sample = random.Random(seed).sample(correct, min(n_correct_sample, len(correct)))
    out = run_dir / "errors.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=ERROR_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "auto_judged": "error", "human_check": ""})
        for row in sample:
            writer.writerow({**row, "auto_judged": "correct", "human_check": ""})
    return out


ITEM_FIELDS = ("token_ids", "type", "candidates", "decision", "adopted", "reason", "confidence", "evidence")


def rescore(run_dir: str | Path, analyze_fn: AnalyzeFn | None = None) -> Path:
    """저장된 출력(segments.json)을 지금의 채점 코드로 다시 채점해 summary_rescored_<채점 버전>.json을 쓴다.

    실행 뒤 채점 버그(사양과 다르게 센 것)를 찾았을 때만 쓴다. 원래 summary.json은 그대로 두고, 판정은 사전 등록한
    채점(plan.json의 scoring)으로 낸 원래 값을 쓴다. 다시 채점한 값은 나란히 보고한다.
    유효하지 않은 항목(토큰 ID가 틀림)은 segments.json에 남지 않아 다시 채점에서 빠진다.
    그런 항목은 덮는 토큰이 없어 정확도에는 영향이 없다.
    """
    from ..analyzer import analyze_tokens
    from ..reconcile import reconcile
    from ..runner import load_doc
    from ..text import Segment, nfc, tokenize

    run_dir = Path(run_dir)
    plan = load_plan(run_dir)
    runs_by_condition: dict[str, list[dict]] = {}
    for (cond, doc_id, rep), row in sorted(done_runs(read_ledger(run_dir)).items()):
        doc = load_doc(Path(plan["docs_dir"]) / f"{doc_id}.json")
        saved = json.loads((run_dir / cond / doc_id / f"r{rep}" / "segments.json").read_text(encoding="utf-8"))
        segments = [Segment(segment_id=s["segment_id"], text=nfc(s["text"])) for s in doc["segments"]]
        tokens = tokenize(segments)
        english = {s["segment_id"]: s["english"] or "" for s in saved["segments"]}
        output: str | dict
        if cond == "C0":
            output = "\n".join(f"[{sid}] {text}" for sid, text in english.items() if text)
        else:
            output = {
                "translation": [{"segment_id": sid, "english": text} for sid, text in english.items()],
                "items": [{f: it.get(f) for f in ITEM_FIELDS} for s in saved["segments"] for it in s["items"]],
            }
        result = reconcile(
            cond,
            segments,
            tokens,
            analyze_tokens(tokens, analyze_fn),
            output,
            gold=doc["gold"],
            high_conf=plan["settings"]["high_confidence"],
            evidence_rule=plan["evidence_rule"],
        )
        metrics = {k: v for k, v in result["metrics"].items() if k != "units"}
        metrics.update({k: row["metrics"].get(k) for k in ("valid_output", "usage", "attempts")})
        runs_by_condition.setdefault(cond, []).append({**metrics, "_doc_id": doc_id, "_repeat": rep})
    out = run_dir / f"summary_rescored_{SCORING_VERSION}.json"
    payload = {
        "experiment": "EXP-003",
        "rescored_with": {"scoring": SCORING_VERSION, "translation": TRANSLATION_RULE, "c0": C0_RULE},
        "preregistered_scoring": plan.get("scoring"),
        "note": "다시 채점한 참고 값이다. 판정은 사전 등록한 채점으로 낸 summary.json을 따른다.",
        **report(plan, runs_by_condition),
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
