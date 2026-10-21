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
import logging
import os
import random
import re
import signal
import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any

import openai
from langchain_core.language_models.chat_models import BaseChatModel

from .. import __version__
from ..analyzer import AnalyzeFn, analyzer_version, camel_analyze
from ..config import CONDITIONS, Settings
from ..errors import InputError
from ..prompts import PROMPT_VERSION, prompt_hash
from ..results import ReviewResult
from ..romanize import MATCHER_VERSION
from ..runner import load_doc, model_label, run_document

logger = logging.getLogger(__name__)

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


ORDER = "repeat>doc>condition"
PLAN_FILE, LEDGER_FILE, STOP_FILE, SUMMARY_FILE = "plan.json", "runs.jsonl", "STOP", "summary.json"
PAUSE_LABELS = {
    "max_runs": "--max-runs에 닿음",
    "token_budget": "--token-budget에 닿음",
    "stop_file": "STOP 파일",
    "signal": "중단 신호(Ctrl+C·SIGTERM)",
    "api_error": "API 오류",
    "error": "실행 중 예외",
}
PLAN_SETTINGS = ("temperature", "max_retries", "recursion_limit", "max_candidates", "high_confidence")
# graph.agent는 예외를 "attempt N: <클래스 이름>: <메시지>"로 errors에 남긴다. 이름이 openai 오류면 API 오류다
API_ERRORS = frozenset(
    name for name, obj in dict(vars(openai)).items() if isinstance(obj, type) and issubclass(obj, openai.APIError)
)
_ERROR_NAME = re.compile(r"^attempt \d+: (\w+):")


@dataclass(frozen=True)
class RunStatus:
    run_dir: Path
    done: int
    planned: int
    paused_reason: str | None  # 다 끝났으면 None
    summary_path: Path | None  # 다 끝났을 때만 쓴다


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _code_hash() -> str:
    """패키지 소스(.py) 전체의 해시. 세션 사이에 코드가 바뀌었는지 기록하는 데만 쓴다."""
    root = Path(__file__).resolve().parents[1]
    h = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        h.update(str(path.relative_to(root)).encode())
        h.update(path.read_bytes())
    return h.hexdigest()[:16]


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "describe", "--always", "--dirty"],
            capture_output=True,
            text=True,
            check=True,
            cwd=Path(__file__).resolve().parent,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


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


def load_plan(run_dir: str | Path) -> dict:
    path = Path(run_dir) / PLAN_FILE
    if not path.exists():
        raise InputError(f"이어서 실행할 수 있는 실행 폴더가 아닙니다(plan.json 없음): {run_dir}")
    return json.loads(path.read_text(encoding="utf-8"))


def latest_run_dir(root: str | Path) -> Path | None:
    """plan.json이 있는 가장 최근 실행 폴더. 재개 기능 전의 실행 폴더는 건너뛴다."""
    dirs = sorted(p.parent for p in Path(root).glob(f"*/{PLAN_FILE}"))
    return dirs[-1] if dirs else None


def read_ledger(run_dir: str | Path) -> list[dict]:
    path = Path(run_dir) / LEDGER_FILE
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:  # 강제 종료로 끊긴 줄. 그 실행은 재개할 때 다시 돈다
            logger.warning("기록 파일의 깨진 줄을 건너뜁니다: %s", line[:80])
    return rows


def _append(run_dir: Path, row: dict) -> None:
    with (run_dir / LEDGER_FILE).open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())


def done_runs(rows: list[dict]) -> dict[tuple[str, str, int], dict]:
    """(조건, 문서, 회차) → 완료 기록. API 오류로 끝난 실행은 완료가 아니다."""
    return {
        (r["condition"], r["doc_id"], r["repeat"]): r
        for r in rows
        if r.get("type") == "run" and r.get("status") == "done"
    }


def is_api_failure(metrics: dict) -> bool:
    """출력을 못 얻었고 그 원인에 API 오류가 있으면 모델 실패가 아니라 실행 환경 문제로 본다."""
    if metrics.get("valid_output"):
        return False
    names = {m.group(1) for e in metrics.get("errors", []) if (m := _ERROR_NAME.match(e))}
    return bool(names & API_ERRORS)


def _tokens(usage: dict) -> tuple[int, int]:
    return int(usage.get("input_tokens", 0) or 0), int(usage.get("output_tokens", 0) or 0)


def _cost(tokens_in: float, tokens_out: float, settings: Settings) -> float | None:
    if settings.price_input_per_mtok is None or settings.price_output_per_mtok is None:
        return None
    return round((tokens_in * settings.price_input_per_mtok + tokens_out * settings.price_output_per_mtok) / 1e6, 2)


def _progress(run_dir: Path, plan: dict, rows: list[dict], settings: Settings, workers: int | None = None) -> dict:
    runs = [r for r in rows if r.get("type") == "run"]
    done = list(done_runs(rows).values())
    sessions = [r for r in rows if r.get("type") == "session"]
    per_cond = len(plan["docs"]) * plan["repeats"]
    planned = per_cond * len(plan["conditions"])
    used_in = sum(_tokens(r.get("usage", {}))[0] for r in runs)
    used_out = sum(_tokens(r.get("usage", {}))[1] for r in runs)
    all_in = [_tokens(r.get("usage", {}))[0] for r in done]
    all_out = [_tokens(r.get("usage", {}))[1] for r in done]
    rem_in = rem_out = 0.0
    conds = {}
    for c in plan["conditions"]:
        d = [r for r in done if r["condition"] == c]
        tin = [_tokens(r.get("usage", {}))[0] for r in d] or all_in  # 아직 없는 조건은 전체 평균으로 어림한다
        tout = [_tokens(r.get("usage", {}))[1] for r in d] or all_out
        if tin:
            rem_in += (per_cond - len(d)) * sum(tin) / len(tin)
            rem_out += (per_cond - len(d)) * sum(tout) / len(tout)
        tot = [_tokens(r.get("usage", {}))[0] + _tokens(r.get("usage", {}))[1] for r in d]
        conds[c] = {
            "done": len(d),
            "planned": per_cond,
            "invalid_output": sum(not r["metrics"].get("valid_output") for r in d),
            "retried": sum((r["metrics"].get("attempts") or 0) > 1 for r in d),
            "tokens_mean": round(sum(tot) / len(tot)) if tot else None,
            "tokens_max": max(tot) if tot else None,
        }
    workers = workers or (sessions[-1].get("workers") if sessions else None) or 1
    elapsed = [r.get("elapsed_s") or 0 for r in done]
    remaining_s = round((planned - len(done)) * sum(elapsed) / len(elapsed) / workers) if elapsed else None
    priced = _cost(0, 0, settings) is not None
    return {
        "run_dir": str(run_dir),
        "done": len(done),
        "planned": planned,
        "complete": len(done) == planned,
        "conditions": conds,
        "api_error_runs": sum(r.get("status") == "api_error" for r in runs),
        "tokens": {"input": used_in, "output": used_out, "total": used_in + used_out},
        "estimate": {
            "total_tokens": round(used_in + used_out + rem_in + rem_out) if done else None,
            "remaining_tokens": round(rem_in + rem_out) if done else None,
            "remaining_s": remaining_s,
        },
        "cost_usd": {
            "used": _cost(used_in, used_out, settings),
            "estimated_total": _cost(used_in + rem_in, used_out + rem_out, settings) if done else None,
        }
        if priced
        else None,
        "sessions": len(sessions),
        "workers": workers,
        "pauses": [{"at": r.get("at"), "reason": r.get("reason")} for r in rows if r.get("type") == "pause"],
        "stop_file": (run_dir / STOP_FILE).exists(),
    }


def status(run_dir: str | Path, settings: Settings) -> dict:
    """사용량과 진행만 모은다. 결과를 보고 멈출지 정하지 않도록 비율 지표와 판정은 넣지 않는다."""
    run_dir = Path(run_dir)
    return _progress(run_dir, load_plan(run_dir), read_ledger(run_dir), settings)


def _fmt_tok(n: float | None) -> str:
    if n is None:
        return "-"
    if n >= 1e6:
        return f"{n / 1e6:.2f}M"
    if n >= 1e3:
        return f"{n / 1e3:.1f}k"
    return str(round(n))


def _fmt_s(seconds: float) -> str:
    m = round(seconds / 60)
    if m >= 60:
        return f"약 {m // 60}시간 {m % 60}분"
    return f"약 {m}분" if m else "1분 미만"


def _usd(v: float | None) -> str:
    return "" if v is None else f" (${v:.2f})"


def format_status(s: dict) -> str:
    conds, tokens, est, cost = s["conditions"], s["tokens"], s["estimate"], s["cost_usd"] or {}
    lines = [
        f"실행: {s['run_dir']} (세션 {s['sessions']}, 동시 {s['workers']})",
        f"진행: {s['done']}/{s['planned']}{' 완료' if s['complete'] else ''} ("
        + " · ".join(f"{c} {v['done']}/{v['planned']}" for c, v in conds.items())
        + ")",
        f"토큰: 입력 {_fmt_tok(tokens['input'])} · 출력 {_fmt_tok(tokens['output'])} · 합계 {_fmt_tok(tokens['total'])}"
        + _usd(cost.get("used")),
        "실행당 토큰 평균/최대: "
        + " · ".join(f"{c} {_fmt_tok(v['tokens_mean'])}/{_fmt_tok(v['tokens_max'])}" for c, v in conds.items()),
        f"형식 실패 {sum(v['invalid_output'] for v in conds.values())} · "
        f"재시도 {sum(v['retried'] for v in conds.values())} · API 오류 {s['api_error_runs']}",
    ]
    if est["total_tokens"] is not None:
        line = f"예상: 총 {_fmt_tok(est['total_tokens'])}{_usd(cost.get('estimated_total'))} · "
        line += f"남은 {_fmt_tok(est['remaining_tokens'])}"
        if est["remaining_s"]:
            line += f" · 남은 시간 {_fmt_s(est['remaining_s'])}(동시 {s['workers']})"
        lines.append(line)
    if s["pauses"]:
        pauses = (f"{p['at']} {PAUSE_LABELS.get(p['reason'], p['reason'])}" for p in s["pauses"])
        lines.append("정지 이력: " + ", ".join(pauses))
    if s["stop_file"]:
        lines.append("STOP 파일 있음: 다음 실행을 시작하기 전에 멈춥니다")
    return "\n".join(lines)


def _progress_line(run_dir: Path, plan: dict, rows: list[dict], settings: Settings, workers: int, session: int) -> str:
    row, p = rows[-1], _progress(run_dir, plan, rows, settings, workers)
    est, cost = p["estimate"], p["cost_usd"] or {}
    state = "ok" if row["metrics"].get("valid_output") else "형식 실패"
    if row["status"] == "api_error":
        state = "API 오류"
    parts = [f"세션 {_fmt_tok(session)}", f"누적 {_fmt_tok(p['tokens']['total'])}"]
    if est["total_tokens"] is not None:
        parts.append(f"예상 총 {_fmt_tok(est['total_tokens'])} tok{_usd(cost.get('estimated_total'))}")
    if est["remaining_s"]:
        parts.append(f"남은 {_fmt_s(est['remaining_s'])}")
    return (
        f"[{p['done']:>{len(str(p['planned']))}}/{p['planned']}] r{row['repeat']} {row['doc_id']} {row['condition']} "
        f"{state} {_fmt_tok(sum(_tokens(row['usage'])))} tok {row['elapsed_s']:.0f}s | " + " · ".join(parts)
    )


def _thread_safe_analyzer() -> AnalyzeFn:
    """camel-tools는 스레드 안전을 보장하지 않아 호출을 하나씩 들여보낸다. 메인 스레드에서 먼저 띄운다."""
    camel_analyze("كتب")
    lock = threading.Lock()

    def analyze(surface: str) -> list[dict]:
        with lock:
            return camel_analyze(surface)

    return analyze


def _start_session(run_dir: Path, rows: list[dict], **info: Any) -> None:
    path = run_dir / LEDGER_FILE
    if path.exists() and (data := path.read_bytes()) and not data.endswith(b"\n"):
        with path.open("a", encoding="utf-8") as f:  # 끊긴 줄 뒤에 이어 쓰지 않는다
            f.write("\n")
    code = _code_hash()
    sessions = [r for r in rows if r.get("type") == "session"]
    if sessions and sessions[-1].get("code_hash") != code:
        logger.warning("이전 세션 뒤로 패키지 코드가 바뀌었습니다(%s → %s).", sessions[-1].get("code_hash"), code)
    _append(run_dir, {"type": "session", "at": _now(), **info, "git_commit": _git_commit(), "code_hash": code})


def write_summary(run_dir: str | Path) -> Path:
    """기록 파일의 완료 실행으로 지표·비교·판정을 낸다. 계획한 규모를 못 채웠으면 complete=false로 표시한다."""
    run_dir = Path(run_dir)
    plan, rows = load_plan(run_dir), read_ledger(run_dir)
    done = done_runs(rows)
    runs_by_condition: dict[str, list[dict]] = {c: [] for c in plan["conditions"]}
    for (cond, doc_id, rep), r in sorted(done.items()):
        runs_by_condition[cond].append({**r["metrics"], "_doc_id": doc_id, "_repeat": rep})
    runs_by_condition = {c: runs for c, runs in runs_by_condition.items() if runs}
    planned = len(plan["conditions"]) * len(plan["docs"]) * plan["repeats"]
    complete = len(done) == planned
    note = "합성 문서 기준 결과. 실제 서류의 오류율·포착률로 일반화하지 않는다."
    if not complete:
        note += f" 계획한 규모를 채우지 못한 부분 결과다({len(done)}/{planned}회)."
    summary, comparisons = aggregate(runs_by_condition), compare(runs_by_condition)
    report = {
        "experiment": "EXP-002",
        "docs_dir": plan["docs_dir"],
        "n_docs": len(plan["docs"]),
        "repeats": plan["repeats"],
        "conditions": plan["conditions"],
        "model": plan["model"],
        "summary": summary,
        "comparisons": comparisons,
        "pass_bar": {name: {"kind": kind, "bar": bar} for name, (kind, bar) in PASS_BAR.items()},
        "verdict": judge(summary, comparisons),
        "note": note,
        "run_dir": str(run_dir),
        "complete": complete,
        "n_runs_done": len(done),
        "n_runs_planned": planned,
        "sessions": sum(r.get("type") == "session" for r in rows),
        "api_error_runs": sum(r.get("type") == "run" and r.get("status") == "api_error" for r in rows),
        "pauses": [{"at": r.get("at"), "reason": r.get("reason")} for r in rows if r.get("type") == "pause"],
    }
    path = run_dir / SUMMARY_FILE
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


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
    """실험을 새로 시작하거나(run_dir 없음) 이어서 한다.

    멈춤 조건(중단 신호, STOP 파일, max_runs, token_budget, API 오류)에 걸리면 새 실행을 시작하지 않고,
    돌던 실행만 마저 기록하고 돌아온다. max_runs·token_budget은 이번 호출(세션) 기준이다.
    """
    repeats = repeats or settings.repeats
    doc_paths = sorted(Path(docs_dir).glob("*.json"))[:limit]
    plan = make_plan(docs_dir, doc_paths, conditions, repeats, settings, model_label(model_factory(), settings))
    if run_dir is None:
        out = Path(out_root) / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        out.mkdir(parents=True)
        text = json.dumps({**plan, "created_at": _now()}, ensure_ascii=False, indent=2) + "\n"
        (out / PLAN_FILE).write_text(text, encoding="utf-8")
    else:
        out = Path(run_dir)
        stored = load_plan(out)
        diff = sorted(k for k in (plan.keys() | stored.keys()) - {"created_at"} if plan.get(k) != stored.get(k))
        if diff:
            raise InputError(f"이어서 실행하려는 실험과 설정이 다릅니다({', '.join(diff)}): {out / PLAN_FILE}")
    rows = read_ledger(out)
    _start_session(out, rows, workers=workers, max_runs=max_runs, token_budget=token_budget)
    docs = [load_doc(p) for p in doc_paths]
    planned = len(conditions) * len(docs) * repeats
    done = done_runs(rows)
    todo = [
        (rep, doc, cond)
        for rep in range(repeats)
        for doc in docs
        for cond in conditions
        if (cond, doc["doc_id"], rep) not in done
    ]
    fn = _thread_safe_analyzer() if workers > 1 and analyze_fn is None else analyze_fn

    signals = submitted = session_tokens = 0

    def on_signal(signum: int, frame: FrameType | None) -> None:
        nonlocal signals
        signals += 1
        if signals == 1:
            logger.warning("돌던 실행을 마치고 멈춥니다. 바로 끝내려면 한 번 더 누르세요(돌던 실행은 버려집니다).")
            return
        _append(out, {"type": "pause", "at": _now(), "reason": "signal"})
        os._exit(130)

    def stop_reason() -> str | None:
        if signals:
            return "signal"
        if (out / STOP_FILE).exists():
            (out / STOP_FILE).unlink()
            return "stop_file"
        if max_runs is not None and submitted >= max_runs:
            return "max_runs"
        if token_budget is not None and session_tokens >= token_budget:
            return "token_budget"
        return None

    previous: dict[int, Any] = {}
    if threading.current_thread() is threading.main_thread():
        previous = {s: signal.signal(s, on_signal) for s in (signal.SIGINT, signal.SIGTERM)}
    reason: str | None = None
    error: BaseException | None = None
    pending: dict[Future[ReviewResult], tuple[int, dict, str]] = {}
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            i = 0
            while True:
                while reason is None and i < len(todo) and len(pending) < workers:
                    reason = stop_reason()
                    if reason is None:
                        rep, doc, cond = todo[i]
                        run_out = out / cond / doc["doc_id"] / f"r{rep}"
                        fut = pool.submit(
                            run_document, doc, cond, model_factory(), settings, run_out, rep, analyze_fn=fn
                        )
                        pending[fut] = todo[i]
                        i += 1
                        submitted += 1
                if not pending:
                    break
                finished, _ = wait(pending, timeout=1.0, return_when=FIRST_COMPLETED)
                for fut in finished:
                    rep, doc, cond = pending.pop(fut)
                    if (exc := fut.exception()) is not None:
                        logger.error("%s %s r%d 실행 중 예외로 멈춥니다: %r", doc["doc_id"], cond, rep, exc)
                        error, reason = error or exc, reason or "error"
                        continue
                    result = fut.result()
                    m = result.metrics
                    row = {
                        "type": "run",
                        "status": "api_error" if is_api_failure(m) else "done",
                        "condition": cond,
                        "doc_id": doc["doc_id"],
                        "repeat": rep,
                        "finished_at": _now(),
                        "elapsed_s": result.meta.elapsed_s,
                        "usage": m.get("usage", {}),
                        "metrics": m,
                    }
                    _append(out, row)
                    rows.append(row)
                    session_tokens += sum(_tokens(row["usage"]))
                    logger.info(_progress_line(out, plan, rows, settings, workers, session_tokens))
                    if row["status"] == "api_error":
                        logger.error("API 오류로 멈춥니다: %s", " / ".join(m.get("errors", [])))
                        reason = reason or "api_error"
    finally:
        for s, handler in previous.items():
            signal.signal(s, handler)
    n_done = len(done_runs(rows))
    if n_done < planned:
        _append(out, {"type": "pause", "at": _now(), "reason": reason})
    if error is not None:
        raise error
    if n_done < planned:
        return RunStatus(out, n_done, planned, reason, None)
    return RunStatus(out, n_done, planned, None, write_summary(out))
