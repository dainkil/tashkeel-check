"""EXP-002 (Q1~Q3): 같은 합성 문서를 조건 C0~C3로 반복 실행하고 지표를 모은다(계획 6.2절).

비율은 문서별 비율의 평균이 아니라 개수를 합쳐서 계산한다(pooled).
반복 간 범위는 반복 회차별 pooled 비율의 최솟값·최댓값, 구간은 문서 단위 부트스트랩이다.
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
    "silent_rate": ("n_silent", "n_gold_without_evidence"),
    "unsupported_adopt_rate": ("n_unsupported_adopt", "n_gold_without_evidence"),
    "hold_rate": ("n_hold", "n_gold_without_evidence"),
    "evidence_pass_rate": ("n_evidence_correct", "n_gold_with_evidence"),
}
SUM_KEYS = [
    "n_unprocessed",
    "n_unprocessed_names",
    "n_unprocessed_ambiguous_words",
    "n_evidence_failed",
    "n_over_flag",
    "n_high_conf_unsupported",
    "n_inconsistent_names",
    "n_suspected_missed_names",
    "n_invalid_items",
    "n_items",
]


def _pooled(runs: list[dict], num: str, den: str) -> float | None:
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
                runs_by_condition[cond].append({**result["metrics"], "_doc_id": doc["doc_id"], "_repeat": rep})
    report = {
        "experiment": "EXP-002",
        "docs_dir": str(docs_dir),
        "n_docs": len(doc_paths),
        "repeats": repeats,
        "conditions": list(conditions),
        "model": settings.model,
        "summary": aggregate(runs_by_condition),
        "note": "합성 문서 기준 결과. 실제 서류의 오류율·포착률로 일반화하지 않는다.",
    }
    out.mkdir(parents=True, exist_ok=True)
    path = out / "summary.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
