"""EXP-002 (Q1~Q3): 같은 합성 문서를 조건 C0~C3로 반복 실행하고 지표를 모은다(계획 6.2절).

비율은 문서별 비율의 평균이 아니라 개수를 합쳐서 계산한다(pooled).
반복 간 범위는 반복 회차별 pooled 비율의 최솟값·최댓값, 구간은 문서 단위 부트스트랩이다.
판정(합격선과 중단 기준)은 실행 전에 고정해 코드로 둔다. 결과를 보고 기준을 바꾸지 않기 위해서다.

실행은 멈췄다가 이어서 할 수 있다(ADR-016). 실행 폴더의 plan.json에 설정을 고정하고, 실행이 하나 끝날 때마다
runs.jsonl에 한 줄을 덧붙인다. 재개하면 기록에 없는 실행만 돈다. 순서는 반복 → 문서 → 조건이라 어디서 멈춰도
네 조건이 같은 문서만큼 차 있다. 중간 확인(status)에는 사용량과 진행만 보이고 비율 지표와 판정은 넣지 않는다.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel

from .. import __version__
from ..analyzer import AnalyzeFn, analyzer_version
from ..config import CONDITIONS, Settings
from ..prompts import PROMPT_VERSION, prompt_hash
from ..romanize import MATCHER_VERSION
from . import harness
from .harness import (  # noqa: F401  (재개 장치의 이름을 EXP-002 모듈에서도 그대로 쓴다)
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
    done_runs,
    format_status,
    is_api_failure,
    latest_run_dir,
    load_plan,
    read_ledger,
    status,
)

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


def make_plan(
    docs_dir: str | Path,
    doc_paths: list[Path],
    conditions: tuple[str, ...],
    repeats: int,
    settings: Settings,
    label: str,
) -> dict:
    """재개할 때 그대로여야 하는 설정. 하나라도 다르면 같은 실험으로 이어 붙이지 않는다."""
    plan = {
        "experiment": "EXP-002",
        "docs_dir": str(docs_dir),
        "docs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in doc_paths},
        "conditions": list(conditions),
        "repeats": repeats,
        "order": ORDER,
        "model": settings.model,
        "model_label": label,
        "settings": {k: getattr(settings, k) for k in PLAN_SETTINGS},
        "prompt_version": PROMPT_VERSION,
        "prompt_hash": {c: prompt_hash(c) for c in conditions},
        "matcher_version": MATCHER_VERSION,
        "analyzer": analyzer_version(),
        "package_version": __version__,
    }
    return json.loads(json.dumps(plan))  # 저장했다 읽은 값과 그대로 비교할 수 있게 JSON 형태로 맞춘다


def report(plan: dict, runs_by_condition: dict[str, list[dict]]) -> dict:
    summary, comparisons = aggregate(runs_by_condition), compare(runs_by_condition)
    return {
        "summary": summary,
        "comparisons": comparisons,
        "pass_bar": {name: {"kind": kind, "bar": bar} for name, (kind, bar) in PASS_BAR.items()},
        "verdict": judge(summary, comparisons),
    }


def _configure(settings: Settings) -> Settings:
    """EXP-002는 지시문 p0·근거 검사 v1로 고정한다(ADR-017 이전 설정)."""
    return settings.model_copy(update={"prompt_version": "p0", "evidence_rule": "v1"})


SPEC = harness.Spec(name="EXP-002", plan=make_plan, report=report, configure=_configure)


def write_summary(run_dir: str | Path) -> Path:
    return harness.write_summary(SPEC, run_dir)


def run(
    docs_dir: str | Path,
    out_root: str | Path,
    model_factory: Callable[[], BaseChatModel],
    settings: Settings,
    conditions: tuple[str, ...] = CONDITIONS,
    repeats: int | None = None,
    limit: int | None = None,
    *,
    run_dir: str | Path | None = None,
    workers: int = 1,
    max_runs: int | None = None,
    token_budget: int | None = None,
    analyze_fn: AnalyzeFn | None = None,
) -> RunStatus:
    """실험을 새로 시작하거나(run_dir 없음) 이어서 한다. 장치는 harness.run, 멈춤 조건도 거기에 있다."""
    return harness.run(
        SPEC,
        docs_dir,
        out_root,
        model_factory,
        settings,
        conditions,
        repeats,
        limit,
        run_dir=run_dir,
        workers=workers,
        max_runs=max_runs,
        token_budget=token_budget,
        analyze_fn=analyze_fn,
    )
