"""EXP-002 (Q1~Q3): 같은 합성 문서를 조건 C0~C3로 반복 실행하고 지표를 모은다(계획 6.2절).

비율은 문서별 비율의 평균이 아니라 개수를 합쳐서 계산한다(pooled).
반복 간 범위는 반복 회차별 pooled 비율의 최솟값·최댓값, 구간은 문서 단위 부트스트랩이다.
판정(합격선과 중단 기준)은 실행 전에 고정해 코드로 둔다. 결과를 보고 기준을 바꾸지 않기 위해서다.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from ..config import CONDITIONS, Settings
from ..runner import load_doc, run_document

RATE_DEFS = {
    # 지표: (분자 키, 분모 키)
    "hidden_pick_rate": ("n_hidden_pick", "n_gold_without_evidence"),
    "silent_rate": ("n_silent", "n_gold_without_evidence"),
    "unsupported_adopt_rate": ("n_unsupported_adopt", "n_gold_without_evidence"),
    "hold_rate": ("n_hold", "n_gold_without_evidence"),
    "evidence_pass_rate": ("n_evidence_correct", "n_gold_with_evidence"),
    "hold_candidate_hit_rate": ("n_hold_candidate_hit", "n_hold"),
}
# 합격선(2026-10-20 사용자 확정, EXP-002 실행 전 고정). 세 기준을 모두 넘어야 그 조건이 합격이다
PASS_BAR = {
    "hidden_pick_rate": ("max", 0.10),  # 근거 없는 이름을 말없이 찍거나 근거 없이 확정한 비율
    "unsupported_adopt_rate": ("max", 0.02),  # 그중 근거 없이 확정한 비율
    "evidence_pass_rate": ("min", 0.90),  # 근거 있는 이름을 근거대로 확정한 비율(전부 보류로 점수를 따지 못하게)
}
TOOL_CONDITIONS = ("C2", "C3")
COMPARISONS = (("C0", "C1"), *(("C1", c) for c in TOOL_CONDITIONS))
SUM_KEYS = [
    "n_unprocessed",
    "n_unprocessed_names",
    "n_unprocessed_ambiguous_words",
    "n_evidence_failed",
    "n_over_flag_tokens",
    "n_unsupported_adopt_tokens",
    "n_high_conf_unsupported_tokens",
    "n_inconsistent_names",
    "n_suspected_missed_names",
    "n_invalid_items",
    "n_items",
]


def _pooled(runs: list[dict], num: str, den: str) -> float | None:
    if not any(num in r for r in runs):  # 그 조건에 없는 지표(예: C0의 보류율)를 0으로 보고하지 않는다
        return None
    n = sum(r.get(num) or 0 for r in runs)
    d = sum(r.get(den) or 0 for r in runs)
    return round(n / d, 4) if d else None


def _bootstrap(runs: list[dict], num: str, den: str, iters: int = 1000, seed: int = 0) -> list[float] | None:
    docs = sorted({r["_doc_id"] for r in runs})
    if len(docs) < 2:
        return None
    by_doc = {d: [r for r in runs if r["_doc_id"] == d] for d in docs}
    rng = random.Random(seed)
    vals = []
    for _ in range(iters):
        sample = [r for d in rng.choices(docs, k=len(docs)) for r in by_doc[d]]
        v = _pooled(sample, num, den)
        if v is not None:
            vals.append(v)
    if not vals:
        return None
    vals.sort()
    return [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]]


def _paired_diff(
    runs_a: list[dict], runs_b: list[dict], num: str, den: str, iters: int = 1000, seed: int = 0
) -> dict | None:
    """두 조건의 비율 차이(a − b)와, 같은 문서를 함께 뽑는 문서 단위 부트스트랩 95% 구간."""
    point_a, point_b = _pooled(runs_a, num, den), _pooled(runs_b, num, den)
    if point_a is None or point_b is None:
        return None
    docs = sorted({r["_doc_id"] for r in runs_a} & {r["_doc_id"] for r in runs_b})
    by_a = {d: [r for r in runs_a if r["_doc_id"] == d] for d in docs}
    by_b = {d: [r for r in runs_b if r["_doc_id"] == d] for d in docs}
    rng = random.Random(seed)
    vals = []
    for _ in range(iters if len(docs) >= 2 else 0):
        sample = rng.choices(docs, k=len(docs))
        a = _pooled([r for d in sample for r in by_a[d]], num, den)
        b = _pooled([r for d in sample for r in by_b[d]], num, den)
        if a is not None and b is not None:
            vals.append(round(a - b, 4))
    vals.sort()
    ci = [vals[int(0.025 * len(vals))], vals[int(0.975 * len(vals)) - 1]] if vals else None
    return {"diff": round(point_a - point_b, 4), "doc_bootstrap_95": ci}


def compare(runs_by_condition: dict[str, list[dict]]) -> dict:
    """COMPARISONS의 조건 쌍마다 합격선 지표와 말없이 찍음 비율의 차이(앞 조건 − 뒤 조건)."""
    out = {}
    for a, b in COMPARISONS:
        if a in runs_by_condition and b in runs_by_condition:
            out[f"{a}-{b}"] = {
                name: _paired_diff(runs_by_condition[a], runs_by_condition[b], *RATE_DEFS[name])
                for name in (*PASS_BAR, "silent_rate")
            }
    return out


def _checks(entry: dict) -> dict[str, bool | None]:
    """조건 하나가 합격선의 기준마다 넘는지. 값이 없으면 None."""
    out: dict[str, bool | None] = {}
    for name, (kind, bar) in PASS_BAR.items():
        v = entry[name]["pooled"]
        out[name] = None if v is None else (v <= bar if kind == "max" else v >= bar)
    return out


def _improves(diff: dict | None, kind: str) -> bool:
    """C1 − 도구 조건 차이의 95% 구간이 0을 포함하지 않고, 도구 조건이 나은 쪽에 있는지."""
    ci = (diff or {}).get("doc_bootstrap_95")
    if not ci:
        return False
    return ci[0] > 0 if kind == "max" else ci[1] < 0


def judge(summary: dict, comparisons: dict) -> dict:
    """사전 등록한 판정. C1이 합격이면 중단(지시만으로 충분), 아니면 C1이 못 넘은 기준을 우연 이상으로 고치고
    합격한 도구 조건이 있으면 합격, 둘 다 아니면 불합격."""
    checks = {c: _checks(e) for c, e in summary.items() if c != "C0"}
    if "C1" not in checks:
        return {"decision": None, "reason": "C1 결과가 없어 판정하지 않는다", "checks": checks}
    c1 = checks["C1"]
    if all(c1.values()):
        return {"decision": "stop", "reason": "C1(지시만)이 합격선을 넘었다. 지시만으로 충분", "checks": checks}
    c1_failed = [name for name, ok in c1.items() if not ok]
    passing = [
        c
        for c in TOOL_CONDITIONS
        if c in checks
        and all(checks[c].values())
        and all(_improves(comparisons.get(f"C1-{c}", {}).get(n), PASS_BAR[n][0]) for n in c1_failed)
    ]
    if passing:
        return {
            "decision": "pass",
            "reason": f"C1은 불합격, {', '.join(passing)}이 합격하고 C1이 못 넘은 기준({', '.join(c1_failed)})을 "
            "우연 이상으로 고쳤다",
            "passing": passing,
            "checks": checks,
        }
    return {"decision": "fail", "reason": "C1도 도구 조건도 합격하지 못했거나, 차이가 우연 수준이다", "checks": checks}


def aggregate(runs_by_condition: dict[str, list[dict]]) -> dict:
    summary = {}
    for cond, runs in runs_by_condition.items():
        reps = sorted({r["_repeat"] for r in runs})
        entry: dict = {"n_runs": len(runs), "n_docs": len({r["_doc_id"] for r in runs}), "repeats": len(reps)}
        for name, (num, den) in RATE_DEFS.items():
            per_rep = [v for k in reps if (v := _pooled([r for r in runs if r["_repeat"] == k], num, den)) is not None]
            entry[name] = {
                "pooled": _pooled(runs, num, den),
                "repeat_range": [min(per_rep), max(per_rep)] if per_rep else None,
                "doc_bootstrap_95": _bootstrap(runs, num, den),
            }
        for key in SUM_KEYS:
            vals = [v for r in runs if (v := r.get(key)) is not None]
            entry[key] = {"total": sum(vals), "mean_per_run": round(sum(vals) / len(vals), 3)} if vals else None
        usage = [r.get("usage", {}) for r in runs]
        entry["tokens_in"] = sum(u.get("input_tokens", 0) for u in usage)
        entry["tokens_out"] = sum(u.get("output_tokens", 0) for u in usage)
        entry["failed_runs"] = sum(not r.get("valid_output") for r in runs)
        tool = [r["tool"] for r in runs if r.get("tool")]
        if tool:
            entry["tool_calls_mean"] = round(sum(t["calls"] for t in tool) / len(runs), 3)
        summary[cond] = entry
    return summary


def run(
    docs_dir: str | Path,
    out_root: str | Path,
    model_factory: Callable[[], BaseChatModel],
    settings: Settings,
    conditions: tuple[str, ...] = CONDITIONS,
    repeats: int | None = None,
    limit: int | None = None,
) -> Path:
    repeats = repeats or settings.repeats
    doc_paths = sorted(Path(docs_dir).glob("*.json"))[:limit]
    out = Path(out_root) / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    runs_by_condition: dict[str, list[dict]] = {c: [] for c in conditions}
    for cond in conditions:
        for path in doc_paths:
            doc = load_doc(path)
            for rep in range(repeats):
                result = run_document(
                    doc, cond, model_factory(), settings, out_dir=out / cond / doc["doc_id"] / f"r{rep}", repeat=rep
                )
                runs_by_condition[cond].append({**result.metrics, "_doc_id": doc["doc_id"], "_repeat": rep})
    summary, comparisons = aggregate(runs_by_condition), compare(runs_by_condition)
    report = {
        "experiment": "EXP-002",
        "docs_dir": str(docs_dir),
        "n_docs": len(doc_paths),
        "repeats": repeats,
        "conditions": list(conditions),
        "model": settings.model,
        "summary": summary,
        "comparisons": comparisons,
        "pass_bar": {name: {"kind": kind, "bar": bar} for name, (kind, bar) in PASS_BAR.items()},
        "verdict": judge(summary, comparisons),
        "note": "합성 문서 기준 결과. 실제 서류의 오류율·포착률로 일반화하지 않는다.",
    }
    out.mkdir(parents=True, exist_ok=True)
    path = out / "summary.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
