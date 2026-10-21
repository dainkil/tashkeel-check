"""EXP-002 실행 루프: 재개, 멈춤 조건, API 오류 차단, 동시 실행. 가짜 모델과 분석기 대역으로 돌린다."""

import json
from pathlib import Path

import httpx
import openai
import pytest

from tashkeel_check.cli import main
from tashkeel_check.config import Settings
from tashkeel_check.errors import InputError
from tashkeel_check.experiments import exp002
from tashkeel_check.fake import FakeAgentModel, practice_responder

from .conftest import fake_analyze

DEV = Path("data/synthetic/dev")
SETTINGS = Settings()


def _run(out_root, responder=None, **kw):
    kw.setdefault("repeats", 1)
    return exp002.run(
        DEV,
        out_root,
        lambda: FakeAgentModel(responder=responder),
        kw.pop("settings", SETTINGS),
        limit=2,
        analyze_fn=fake_analyze,
        **kw,
    )


def _report(status):
    report = json.loads(status.summary_path.read_text(encoding="utf-8"))
    return {k: report[k] for k in ("summary", "comparisons", "verdict")}


def _run_keys(run_dir):
    return [(r["repeat"], r["doc_id"], r["condition"]) for r in exp002.read_ledger(run_dir) if r["type"] == "run"]


def _with_usage(messages, bound):
    msg = practice_responder(messages, bound)
    return msg.model_copy(update={"usage_metadata": {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}})


def _rate_limited(messages, bound):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    raise openai.RateLimitError("quota exceeded", response=httpx.Response(429, request=request), body=None)


def test_resume_runs_only_what_is_left_in_repeat_doc_condition_order(tmp_path):
    first = _run(tmp_path / "a", repeats=2, max_runs=3)
    assert first.paused_reason == "max_runs" and first.done == 3 and first.summary_path is None
    assert _run_keys(first.run_dir) == [(0, "dev_001", "C0"), (0, "dev_001", "C1"), (0, "dev_001", "C2")]
    resumed = _run(tmp_path / "a", repeats=2, run_dir=first.run_dir)
    assert resumed.paused_reason is None and resumed.done == resumed.planned == 16
    keys = _run_keys(first.run_dir)
    assert len(keys) == len(set(keys)) == 16
    assert keys[:8] == [(0, d, c) for d in ("dev_001", "dev_002") for c in ("C0", "C1", "C2", "C3")]
    # 끊었다 이어서 한 결과가 한 번에 돈 결과와 같다
    assert _report(resumed) == _report(_run(tmp_path / "b", repeats=2))


def test_parallel_workers_give_the_same_result(tmp_path):
    assert _report(_run(tmp_path / "a", workers=3)) == _report(_run(tmp_path / "b"))


def test_resume_refuses_a_different_plan(tmp_path):
    first = _run(tmp_path, max_runs=1)
    with pytest.raises(InputError, match="repeats"):
        _run(tmp_path, repeats=2, run_dir=first.run_dir)


def test_api_error_is_not_counted_as_done_and_stops_the_run(tmp_path):
    failed = _run(tmp_path, responder=_rate_limited)
    assert failed.paused_reason == "api_error" and failed.done == 0
    rows = [r for r in exp002.read_ledger(failed.run_dir) if r["type"] == "run"]
    assert [r["status"] for r in rows] == ["api_error"]  # 첫 실행에서 멈추고 나머지를 실패로 채우지 않는다
    assert "RateLimitError" in rows[0]["metrics"]["errors"][0]
    resumed = _run(tmp_path, run_dir=failed.run_dir)
    assert resumed.summary_path is not None and resumed.done == 8


def test_format_failure_is_a_model_result_not_an_api_error():
    assert not exp002.is_api_failure({"valid_output": False, "errors": ["attempt 1: segments missing in translation"]})
    assert not exp002.is_api_failure({"valid_output": False, "errors": ["attempt 1: RuntimeError: boom"]})
    assert exp002.is_api_failure({"valid_output": False, "errors": ["attempt 2: APITimeoutError: timed out"]})
    assert not exp002.is_api_failure({"valid_output": True, "errors": ["attempt 1: RateLimitError: slow down"]})


def test_stop_file_pauses_before_the_next_run_and_is_removed(tmp_path):
    first = _run(tmp_path, max_runs=1)
    (first.run_dir / exp002.STOP_FILE).touch()
    again = _run(tmp_path, run_dir=first.run_dir)
    assert again.paused_reason == "stop_file" and again.done == 1
    assert not (first.run_dir / exp002.STOP_FILE).exists()


def test_token_budget_counts_this_session_only(tmp_path):
    first = _run(tmp_path, responder=_with_usage, token_budget=100)
    assert first.paused_reason == "token_budget" and first.done == 1  # C0 한 번(150토큰)으로 넘는다
    again = _run(tmp_path, responder=_with_usage, run_dir=first.run_dir, token_budget=100)
    assert again.done == 2


def test_torn_last_line_is_skipped_and_that_run_is_redone(tmp_path):
    first = _run(tmp_path, max_runs=2)
    with (first.run_dir / exp002.LEDGER_FILE).open("a", encoding="utf-8") as f:
        f.write('{"type": "run", "status": "do')  # 쓰다가 끊긴 줄
    resumed = _run(tmp_path, run_dir=first.run_dir)
    assert resumed.done == 8 and len(_run_keys(first.run_dir)) == 8


def test_status_reports_usage_and_progress_but_no_rates(tmp_path):
    first = _run(tmp_path, responder=_with_usage, max_runs=4)
    priced = Settings(price_input_per_mtok=2, price_output_per_mtok=10)
    s = exp002.status(first.run_dir, priced)
    assert (s["done"], s["planned"], s["complete"]) == (4, 8, False)
    assert s["conditions"]["C2"]["tokens_mean"] == 300  # 툴 호출 1회 + 출력 1회
    assert s["estimate"]["total_tokens"] == s["tokens"]["total"] * 2
    assert s["cost_usd"]["used"] == round((s["tokens"]["input"] * 2 + s["tokens"]["output"] * 10) / 1e6, 2)
    assert "rate" not in json.dumps(s) and "verdict" not in s
    assert exp002.status(first.run_dir, SETTINGS)["cost_usd"] is None  # 단가가 없으면 토큰만
    assert "진행: 4/8" in exp002.format_status(s)


def test_finalize_writes_a_partial_summary(tmp_path):
    first = _run(tmp_path, max_runs=4)
    report = json.loads(exp002.write_summary(first.run_dir).read_text(encoding="utf-8"))
    assert report["complete"] is False and report["n_runs_done"] == 4 and "부분 결과" in report["note"]


def test_cli_resume_needs_consent_and_status_prints(tmp_path, capsys):
    first = _run(tmp_path, max_runs=1)
    assert main(["exp002", "--split", "dev", "--resume", str(first.run_dir)]) == 1
    assert "남은 7회" in capsys.readouterr().out
    assert main(["exp002", "--split", "dev", "--resume", str(first.run_dir), "--repeats", "2", "--fake"]) == 2
    assert main(["exp002-status", str(first.run_dir)]) == 0
    assert "진행: 1/8" in capsys.readouterr().out
