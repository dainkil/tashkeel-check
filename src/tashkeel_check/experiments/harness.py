"""실험 실행 장치(ADR-016): 재개·동시 실행·멈춤 조건·사용량 확인, 그리고 비율 집계에 쓰는 통계 함수.

실험마다 다른 것(실행 계획에 고정할 설정, 지표·합격선·판정, 설정 덮어쓰기)은 Spec으로 받는다.
EXP-002(exp002.py)와 EXP-003(exp003.py)이 같은 장치를 쓴다. EXP-002의 동작과 산출 형식은 이 분리 전과 같다.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import random
import re
import signal
import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import FrameType
from typing import Any

import langchain_openai.chat_models.base  # noqa: F401  (감싼 API 오류 클래스를 API_ERRORS에 넣으려고 불러 둔다)
import openai
from langchain_core.language_models.chat_models import BaseChatModel

from ..analyzer import AnalyzeFn, thread_safe_analyze
from ..config import CONDITIONS, Settings
from ..errors import InputError
from ..results import ReviewResult
from ..runner import load_doc, model_label, run_document

logger = logging.getLogger(__name__)


# ---------- 통계 ----------


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


def clopper_pearson_lower(k: int, n: int, alpha: float = 0.05) -> float | None:
    """n번 중 k번 맞았을 때 정확도의 한쪽 (1 − alpha) Clopper–Pearson 하한. 정확도 99%를 주장할 수 있는지 볼 때 쓴다.

    k = n이면 alpha^(1/n)이다(예: 300개 중 0개 오류 → 0.990). 표본이 서로 독립이라고 가정하므로,
    같은 사람·문서에 오류가 몰리면 실제보다 좁다. 그래서 문서 단위 부트스트랩 하한과 같이 본다.
    """
    if n <= 0:
        return None
    if k <= 0:
        return 0.0
    if k == n:
        return round(alpha ** (1 / n), 6)

    def upper_tail(p: float) -> float:  # P(X ≥ k | n, p)
        log_n = math.lgamma(n + 1)
        logs = [
            log_n - math.lgamma(i + 1) - math.lgamma(n - i + 1) + i * math.log(p) + (n - i) * math.log1p(-p)
            for i in range(k, n + 1)
        ]
        top = max(logs)
        return math.exp(top) * sum(math.exp(v - top) for v in logs)

    lo, hi = 0.0, k / n
    for _ in range(80):
        mid = (lo + hi) / 2
        if upper_tail(mid) < alpha:
            lo = mid
        else:
            hi = mid
    return round(lo, 6)


def bootstrap_lower(runs: list[dict], num: str, den: str, iters: int = 1000, seed: int = 0) -> float | None:
    """문서 단위 부트스트랩 분포의 5백분위수(한쪽 95% 하한). 같은 문서의 반복을 함께 뽑는다."""
    docs = sorted({r["_doc_id"] for r in runs})
    if len(docs) < 2:
        return None
    by_doc = {d: [r for r in runs if r["_doc_id"] == d] for d in docs}
    rng = random.Random(seed)
    vals = sorted(
        v
        for _ in range(iters)
        if (v := _pooled([r for d in rng.choices(docs, k=len(docs)) for r in by_doc[d]], num, den)) is not None
    )
    return vals[int(0.05 * len(vals))] if vals else None


# ---------- 실행 장치 ----------


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
STAGE_LABELS = {"continue": "계속(다음 회차를 돈다)", "stop": "끝(사전 규칙에 따라 여기서 마친다)"}
# 처리 등급별 단가 배수. flex는 Batch와 같은 약 50% 할인으로 본다(추정, 청구 기준 아님)
TIER_PRICE = {"flex": 0.5}
PLAN_SETTINGS = ("temperature", "max_retries", "recursion_limit", "max_candidates", "high_confidence")


def _api_error_names() -> frozenset[str]:
    """openai.APIError와 그 하위 클래스 이름 전부. langchain-openai가 감싼 오류(OpenAIRateLimitError 등)도 들어간다.

    처음에는 openai 모듈에 있는 이름만 봐서, 감싼 429가 형식 실패로 기록됐다(EXP-003 eval 2026-10-21, C0 1회).
    """
    names: set[str] = set()
    stack: list[type] = [openai.APIError]
    while stack:
        cls = stack.pop()
        names.add(cls.__name__)
        stack.extend(cls.__subclasses__())
    return frozenset(names)


# graph.agent는 예외를 "attempt N: <클래스 이름>: <메시지>"로 errors에 남긴다. 이름이 API 오류 클래스면 API 오류다
API_ERRORS = _api_error_names()
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


@dataclass(frozen=True)
class Spec:
    """실험 하나의 정의. plan은 재개할 때 그대로여야 하는 설정, report는 완료 실행으로 지표·비교·판정을 낸다."""

    name: str
    plan: Callable[[str | Path, list[Path], tuple[str, ...], int, Settings, str], dict]
    report: Callable[[dict, dict[str, list[dict]]], dict]
    configure: Callable[[Settings], Settings] = lambda s: s
    # 기록 파일에 넣지 않을 큰 지표. 실행 폴더의 metrics.json에는 남는다
    ledger_drop: tuple[str, ...] = field(default=("units",))
    # 라벨 → (실제 조건, 설정). 참고 조건(다른 지시문 판의 C1 등)을 라벨 하나로 돌릴 때 쓴다
    arm: Callable[[str, Settings], tuple[str, Settings]] = lambda label, s: (label, s)
    # 단계적 반복: 회차 stage_after 앞이 다 끝나면 stage_gate(plan, 라벨별 완료 실행)가 계속할지 정한다.
    # 라벨별 반복 수(plan["arm_repeats"])와 단계 규칙(plan["stage_rule"])은 spec.plan이 plan에 넣는다
    stage_after: int | None = None
    stage_gate: Callable[[dict, dict[str, list[dict]]], dict] | None = None


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
    """(조건, 문서, 회차) → 완료 기록. API 오류로 끝난 실행은 완료가 아니다.

    기록 당시 API 오류를 못 알아본 줄(status는 done이지만 지표로는 API 실패)도 완료로 치지 않아, 재개하면 다시 돈다.
    """
    return {
        (r["condition"], r["doc_id"], r["repeat"]): r
        for r in rows
        if r.get("type") == "run" and r.get("status") == "done" and not is_api_failure(r.get("metrics", {}))
    }


def stage_row(rows: list[dict]) -> dict | None:
    """단계 판단 기록(있으면 마지막 것)."""
    return next((r for r in reversed(rows) if r.get("type") == "stage"), None)


def label_repeats(plan: dict, rows: list[dict] | None = None) -> dict[str, int]:
    """라벨마다 돌릴 반복 수. 라벨별 반복 수(arm_repeats)와, 단계 판단이 '끝'이면 그 회차까지만 센다."""
    reps = plan["repeats"]
    stage = stage_row(rows or [])
    if stage is not None and stage.get("decision") == "stop":
        reps = min(reps, stage["after_repeat"])
    arm = plan.get("arm_repeats") or {}
    return {c: min(reps, arm.get(c, reps)) for c in plan["conditions"]}


def planned_runs(plan: dict, rows: list[dict] | None = None) -> int:
    return len(plan["docs"]) * sum(label_repeats(plan, rows).values())


def runs_by_label(plan: dict, rows: list[dict], before_repeat: int | None = None) -> dict[str, list[dict]]:
    """라벨별 완료 실행의 지표(_doc_id·_repeat를 붙임). before_repeat를 주면 그 앞 회차만."""
    out: dict[str, list[dict]] = {c: [] for c in plan["conditions"]}
    for (cond, doc_id, rep), r in sorted(done_runs(rows).items()):
        if cond in out and (before_repeat is None or rep < before_repeat):
            out[cond].append({**r["metrics"], "_doc_id": doc_id, "_repeat": rep})
    return {c: runs for c, runs in out.items() if runs}


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


def _priced_tokens(rows: list[dict]) -> tuple[float, float]:
    """실행마다 그 세션의 처리 등급 배수(TIER_PRICE)를 곱한 토큰 합. 비용 어림에만 쓴다."""
    factor, tin, tout = 1.0, 0.0, 0.0
    for r in rows:
        if r.get("type") == "session":
            factor = TIER_PRICE.get(r.get("service_tier") or "", 1.0)
        elif r.get("type") == "run":
            i, o = _tokens(r.get("usage", {}))
            tin, tout = tin + i * factor, tout + o * factor
    return tin, tout


def _progress(run_dir: Path, plan: dict, rows: list[dict], settings: Settings, workers: int | None = None) -> dict:
    runs = [r for r in rows if r.get("type") == "run"]
    done = list(done_runs(rows).values())
    sessions = [r for r in rows if r.get("type") == "session"]
    per_label = {c: len(plan["docs"]) * n for c, n in label_repeats(plan, rows).items()}
    planned = sum(per_label.values())
    used_in = sum(_tokens(r.get("usage", {}))[0] for r in runs)
    used_out = sum(_tokens(r.get("usage", {}))[1] for r in runs)
    all_in = [_tokens(r.get("usage", {}))[0] for r in done]
    all_out = [_tokens(r.get("usage", {}))[1] for r in done]
    rem_in = rem_out = 0.0
    conds = {}
    for c in plan["conditions"]:
        per_cond = per_label[c]
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
    tier = (sessions[-1].get("service_tier") if sessions else None) or None
    paid_in, paid_out = _priced_tokens(rows)
    rem_factor = TIER_PRICE.get(tier or "", 1.0)
    stage = stage_row(rows)
    return {
        "run_dir": str(run_dir),
        "done": len(done),
        "planned": planned,
        "complete": len(done) == planned,
        "conditions": conds,
        "api_error_runs": sum(r.get("status") == "api_error" or is_api_failure(r.get("metrics", {})) for r in runs),
        "tokens": {"input": used_in, "output": used_out, "total": used_in + used_out},
        "estimate": {
            "total_tokens": round(used_in + used_out + rem_in + rem_out) if done else None,
            "remaining_tokens": round(rem_in + rem_out) if done else None,
            "remaining_s": remaining_s,
        },
        "cost_usd": {
            "used": _cost(paid_in, paid_out, settings),
            "estimated_total": _cost(paid_in + rem_in * rem_factor, paid_out + rem_out * rem_factor, settings)
            if done
            else None,
        }
        if priced
        else None,
        "service_tier": tier,
        # 단계 판단은 결정만 보인다. 값은 summary에만 남긴다(사람이 결과를 보고 멈추지 않게, ADR-016·020)
        "stage": None if stage is None else {"after_repeat": stage["after_repeat"], "decision": stage["decision"]},
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
        f"실행: {s['run_dir']} (세션 {s['sessions']}, 동시 {s['workers']}"
        + (f", 처리 등급 {s['service_tier']}" if s.get("service_tier") else "")
        + ")",
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
    if s.get("stage"):
        st = s["stage"]
        lines.append(f"단계 판단(반복 {st['after_repeat']}회 뒤): {STAGE_LABELS.get(st['decision'], st['decision'])}")
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


def write_summary(spec: Spec, run_dir: str | Path) -> Path:
    """기록 파일의 완료 실행으로 지표·비교·판정을 낸다. 계획한 규모를 못 채웠으면 complete=false로 표시한다."""
    run_dir = Path(run_dir)
    plan, rows = load_plan(run_dir), read_ledger(run_dir)
    done = done_runs(rows)
    runs_by_condition = runs_by_label(plan, rows)
    planned = planned_runs(plan, rows)
    complete = len(done) == planned
    note = "합성 문서 기준 결과. 실제 서류의 오류율·포착률로 일반화하지 않는다."
    if not complete:
        note += f" 계획한 규모를 채우지 못한 부분 결과다({len(done)}/{planned}회)."
    report = {
        "experiment": spec.name,
        "docs_dir": plan["docs_dir"],
        "n_docs": len(plan["docs"]),
        "repeats": plan["repeats"],
        "conditions": plan["conditions"],
        "model": plan["model"],
        **spec.report(plan, runs_by_condition),
        "note": note,
        "run_dir": str(run_dir),
        "complete": complete,
        "n_runs_done": len(done),
        "n_runs_planned": planned,
        "sessions": sum(r.get("type") == "session" for r in rows),
        "api_error_runs": sum(
            r.get("type") == "run" and (r.get("status") == "api_error" or is_api_failure(r.get("metrics", {})))
            for r in rows
        ),
        "pauses": [{"at": r.get("at"), "reason": r.get("reason")} for r in rows if r.get("type") == "pause"],
    }
    if (stage := stage_row(rows)) is not None:
        report["stage"] = {k: v for k, v in stage.items() if k not in ("type",)}
    if plan.get("arm_repeats"):
        report["repeats_by_condition"] = label_repeats(plan, rows)
    path = run_dir / SUMMARY_FILE
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _decide_stage(spec: Spec, plan: dict, out: Path, rows: list[dict], after: int) -> dict:
    """회차 after 앞의 완료 실행으로 사전 등록한 단계 규칙을 적용하고 기록한다."""
    assert spec.stage_gate is not None
    expected = len(plan["docs"]) * sum(min(after, n) for n in label_repeats(plan).values())
    before = runs_by_label(plan, rows, before_repeat=after)
    got = sum(len(v) for v in before.values())
    if got != expected:  # 앞 회차가 다 끝나지 않았다(멈춤 조건이 먼저 걸려야 한다)
        raise RuntimeError(f"stage gate before repeat {after}: {got}/{expected} runs done")
    decision = spec.stage_gate(plan, before)
    row = {"type": "stage", "at": _now(), "after_repeat": after, **decision}
    _append(out, row)
    rows.append(row)
    logger.info("단계 판단(반복 %d회 뒤): %s", after, STAGE_LABELS.get(row["decision"], row["decision"]))
    return row


def run(
    spec: Spec,
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
    session_info: dict[str, Any] | None = None,
) -> RunStatus:
    """실험을 새로 시작하거나(run_dir 없음) 이어서 한다.

    멈춤 조건(중단 신호, STOP 파일, max_runs, token_budget, API 오류)에 걸리면 새 실행을 시작하지 않고,
    돌던 실행만 마저 기록하고 돌아온다. max_runs·token_budget은 이번 호출(세션) 기준이다.
    spec.stage_after가 있으면 그 회차 앞이 다 끝난 뒤 spec.stage_gate로 다음 회차를 돌지 정하고 기록한다.
    session_info(처리 등급 등 모델 출력에 영향이 없는 실행 환경)는 세션 기록에 남긴다.
    """
    settings = spec.configure(settings)
    repeats = repeats or settings.repeats
    doc_paths = sorted(Path(docs_dir).glob("*.json"))[:limit]
    plan = spec.plan(docs_dir, doc_paths, conditions, repeats, settings, model_label(model_factory(), settings))
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
    _start_session(out, rows, workers=workers, max_runs=max_runs, token_budget=token_budget, **(session_info or {}))
    rows = read_ledger(out)
    docs = [load_doc(p) for p in doc_paths]
    planned = planned_runs(plan, rows)
    reps_of = label_repeats(plan, rows)
    done = done_runs(rows)
    todo = [
        (rep, doc, cond)
        for rep in range(repeats)
        for doc in docs
        for cond in conditions
        if rep < reps_of[cond] and (cond, doc["doc_id"], rep) not in done
    ]
    arms = {c: spec.arm(c, settings) for c in conditions}
    gate_after = spec.stage_after if spec.stage_gate is not None and spec.stage_after is not None else None
    stage = stage_row(rows)
    fn = thread_safe_analyze() if workers > 1 and analyze_fn is None else analyze_fn

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
                    rep, doc, cond = todo[i]
                    if gate_after is not None and stage is None and rep >= gate_after:
                        if pending:  # 앞 회차가 다 끝나기를 기다린다
                            break
                        stage = _decide_stage(spec, plan, out, rows, gate_after)
                        if stage["decision"] == "stop":  # todo는 회차 순서라 i 뒤는 모두 다음 회차다
                            todo, planned = todo[:i], planned_runs(plan, rows)
                            break
                    reason = stop_reason()
                    if reason is None:
                        run_out = out / cond / doc["doc_id"] / f"r{rep}"
                        real, arm_settings = arms[cond]
                        fut = pool.submit(
                            run_document, doc, real, model_factory(), arm_settings, run_out, rep, analyze_fn=fn
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
                        "metrics": {k: v for k, v in m.items() if k not in spec.ledger_drop},
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
    return RunStatus(out, n_done, planned, None, write_summary(spec, out))
