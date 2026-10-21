"""EXP-003 판정(99% 두 기준, 서비스 기준 문구)과 실행 장치 공유. 가짜 모델로만 돌린다."""

import csv
import dataclasses
import json
from pathlib import Path

from tashkeel_check.cli import main
from tashkeel_check.config import Settings
from tashkeel_check.experiments import exp002, exp003, harness
from tashkeel_check.experiments.harness import clopper_pearson_lower
from tashkeel_check.fake import FakeAgentModel
from tashkeel_check.prompts import prompt_hash

from . import hard_responders as H
from .conftest import fake_analyze

HARD_DEV = Path("data/synthetic-hard/dev")


def test_clopper_pearson_matches_the_99_percent_sample_sizes():
    assert clopper_pearson_lower(1000, 1000) > 0.99
    assert clopper_pearson_lower(996, 1000) >= 0.99 > clopper_pearson_lower(995, 1000)
    assert clopper_pearson_lower(499, 500) >= 0.99 > clopper_pearson_lower(498, 500)
    assert clopper_pearson_lower(300, 300) >= 0.99 > clopper_pearson_lower(299, 300)
    assert clopper_pearson_lower(0, 10) == 0.0 and clopper_pearson_lower(0, 0) is None


def _runs(n_docs, units, errors_by_repeat, repeats=3):
    """문서 n_docs개 × 반복. 반복마다 정해진 수의 오류를 앞 문서부터 하나씩 나눠 준다."""
    runs = []
    for rep in range(repeats):
        left = errors_by_repeat[rep]
        for d in range(n_docs):
            err = 1 if left > 0 else 0
            left -= err
            ok = units - err
            runs.append(
                {
                    "_doc_id": f"d{d:02d}",
                    "_repeat": rep,
                    "n_scored_units": units,
                    "n_strict_correct": ok,
                    "n_safety_ok": ok,
                    "n_docs": 1,
                    "doc_strict_all_correct": int(ok == units),
                    "doc_safety_all_ok": int(ok == units),
                    "valid_output": True,
                    "by_case_type": {"A1": {"n": 2, "strict": 2, "safety_ok": 2}},
                }
            )
    return runs


def test_judge_and_service_claim():
    perfect = _runs(70, 20, [0, 0, 0])  # 1,400개 × 3회 오류 0
    near = _runs(70, 20, [10, 12, 9])  # 99.2~99.4%: 점추정은 넘지만 하한은 못 넘는다
    low = _runs(70, 20, [60, 70, 65])  # 약 95%
    summary = exp003.aggregate({"C1": low, "C2": perfect, "C3": near})
    assert summary["C2"]["service_claim"]["claim"] is True
    assert summary["C3"]["strict_accuracy"]["pooled"] >= 0.99 and summary["C3"]["service_claim"]["claim"] is False
    assert summary["C2"]["by_case_type"]["A1"]["n"] == 2 * 70 * 3
    verdict = exp003.judge(summary, exp003.compare({"C1": low, "C2": perfect, "C3": near}))
    assert verdict["decision"] == "pass" and "C2" in verdict["passing"]
    stop = exp003.aggregate({"C1": perfect, "C2": low})
    assert exp003.judge(stop, exp003.compare({"C1": perfect, "C2": low}))["decision"] == "stop"
    fail = exp003.aggregate({"C1": low, "C2": low, "C3": low})
    assert exp003.judge(fail, exp003.compare({"C1": low, "C2": low, "C3": low}))["decision"] == "fail"


def _oracle_factory(paths):
    """사용자 메시지의 구간 원문으로 문서를 찾아 그 문서의 정답대로 답하는 가짜 모델."""
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]

    def respond(messages, bound):
        text = str(next(m.content for m in messages if m.type == "human"))
        doc = next(d for d in docs if all(seg["text"] in text for seg in d["segments"][:3]))
        return H.make_responder(doc)(messages, bound)

    return lambda: FakeAgentModel(responder=respond)


def test_fake_oracle_run_resumes_and_reports(tmp_path):
    paths = sorted(HARD_DEV.glob("*.json"))[:2]
    first = exp003.run(
        HARD_DEV, tmp_path, _oracle_factory(paths), Settings(), limit=2, repeats=1, max_runs=3, analyze_fn=fake_analyze
    )
    assert first.paused_reason == "max_runs"
    plan = exp003.load_plan(first.run_dir)
    assert (plan["experiment"], plan["prompt_version"], plan["evidence_rule"]) == ("EXP-003", "p1", "v2")
    assert plan["pass_bar"] == {"strict_accuracy": 0.99, "safety_accuracy": 0.99}
    done = exp003.run(
        HARD_DEV,
        tmp_path,
        _oracle_factory(paths),
        Settings(),
        limit=2,
        repeats=1,
        run_dir=first.run_dir,
        analyze_fn=fake_analyze,
    )
    report = json.loads(done.summary_path.read_text(encoding="utf-8"))
    for cond in ("C0", "C1", "C2", "C3"):
        assert report["summary"][cond]["strict_accuracy"]["pooled"] == 1.0, cond
    assert report["verdict"]["decision"] == "stop"
    assert report["verdict"]["service_claim"]["C1"] is False  # 문서 2개로는 하한이 0.99에 못 미친다
    rows = [r for r in exp003.read_ledger(first.run_dir) if r["type"] == "run"]
    assert all("units" not in r["metrics"] for r in rows)
    metrics = json.loads((first.run_dir / "C1" / paths[0].stem / "r0" / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["units"] and metrics["n_scored_units"] == len(metrics["units"])
    rescored = json.loads(exp003.rescore(first.run_dir, analyze_fn=fake_analyze).read_text(encoding="utf-8"))
    for cond in ("C0", "C1", "C2", "C3"):
        assert rescored["summary"][cond]["strict_accuracy"] == report["summary"][cond]["strict_accuracy"], cond
    out = exp003.export_errors(first.run_dir, n_correct_sample=5)
    with out.open(encoding="utf-8-sig") as f:
        table = list(csv.DictReader(f))
    assert len(table) == 5 and {r["auto_judged"] for r in table} == {"correct"}


def test_exp002_plan_keys_are_unchanged_by_the_shared_harness():
    plan = exp002.make_plan(
        "data/synthetic/dev",
        sorted(Path("data/synthetic/dev").glob("*.json"))[:2],
        ("C0", "C1"),
        1,
        Settings(),
        "fake-agent",
    )
    assert list(plan) == [
        "experiment",
        "docs_dir",
        "docs",
        "conditions",
        "repeats",
        "order",
        "model",
        "model_label",
        "settings",
        "prompt_version",
        "prompt_hash",
        "matcher_version",
        "analyzer",
        "package_version",
    ]
    assert plan["prompt_version"] == "p0"
    hard = Settings(prompt_version="p1", evidence_rule="v2")
    assert exp002.SPEC.configure(hard).prompt_version == "p0" and exp002.SPEC.configure(hard).evidence_rule == "v1"


def test_reference_arm_runs_once_with_p0_and_the_stage_rule_stops_outside_the_gray_zone(tmp_path):
    """C1p0는 반복 1회에만 p0로 돈다. 정답대로 답하면 1.0이라 회색 구간 밖이어서 반복 1회로 끝난다(ADR-020)."""
    paths = sorted(HARD_DEV.glob("*.json"))[:1]
    st = exp003.run(HARD_DEV, tmp_path, _oracle_factory(paths), Settings(), limit=1, workers=2, analyze_fn=fake_analyze)
    plan = exp003.load_plan(st.run_dir)
    assert plan["conditions"] == ["C0", "C1", "C2", "C3", "C1p0"] and plan["repeats"] == 3
    assert plan["arm_repeats"] == {"C1p0": 1} and plan["stage_rule"]["band"] == [0.98, 0.995]
    assert plan["prompt_hash"]["C1p0"] == prompt_hash("C1", "p0") != plan["prompt_hash"]["C1"]
    meta = json.loads((st.run_dir / "C1p0" / paths[0].stem / "r0" / "run_meta.json").read_text(encoding="utf-8"))
    assert (meta["condition"], meta["prompt_version"]) == ("C1", "p0")
    rows = exp003.read_ledger(st.run_dir)
    stages = [r for r in rows if r["type"] == "stage"]
    assert [(r["after_repeat"], r["decision"]) for r in stages] == [(1, "stop")]
    assert {r["repeat"] for r in rows if r["type"] == "run"} == {0}
    report = json.loads(st.summary_path.read_text(encoding="utf-8"))
    assert report["complete"] is True and report["n_runs_planned"] == 5
    assert report["stage"]["decision"] == "stop" and report["repeats_by_condition"]["C1"] == 1
    assert report["comparisons"]["C1-C1p0"]["reference"] is True
    assert "C1p0" not in report["verdict"]["checks"]
    s = exp003.status(st.run_dir, Settings())
    assert "values" not in json.dumps(s) and "단계 판단(반복 1회 뒤): 끝" in exp003.format_status(s)
    again = exp003.run(
        HARD_DEV, tmp_path, _oracle_factory(paths), Settings(), limit=1, run_dir=st.run_dir, analyze_fn=fake_analyze
    )
    assert again.summary_path is not None and again.planned == 5
    assert len([r for r in exp003.read_ledger(st.run_dir) if r["type"] == "run"]) == 5


def test_stage_continue_runs_the_remaining_repeats_without_the_reference_arm(tmp_path):
    paths = sorted(HARD_DEV.glob("*.json"))[:1]
    spec = dataclasses.replace(exp003.SPEC, stage_gate=lambda plan, runs: {"decision": "continue", "in_band": ["x"]})
    st = harness.run(
        spec, HARD_DEV, tmp_path, _oracle_factory(paths), Settings(), exp003.ARMS, 2, 1, analyze_fn=fake_analyze
    )
    runs = [r for r in exp003.read_ledger(st.run_dir) if r["type"] == "run"]
    assert st.summary_path is not None and st.planned == len(runs) == 9  # C0~C3 × 2 + C1p0 × 1
    assert {r["condition"] for r in runs if r["repeat"] == 1} == {"C0", "C1", "C2", "C3"}


def test_stage_rule_band_edges():
    plan = {"stage_rule": {"after_repeat": 1}}

    def gate(**by_cond):
        return exp003.stage_gate(plan, by_cond)

    def at(errors):  # 문서 70 × 이름 부분 20 = 1,400개 중 오류 수
        return _runs(70, 20, [errors], repeats=1)

    assert gate(C1=at(0), C2=at(0), C3=at(0))["decision"] == "stop"
    assert gate(C1=at(60), C2=at(60), C3=at(7))["decision"] == "stop"  # 0.957 / 0.995(구간 밖)
    edge = gate(C1=at(60), C2=at(28), C3=at(0))  # 0.98은 구간 안
    assert edge["decision"] == "continue" and edge["in_band"] == ["C2.strict_accuracy", "C2.safety_accuracy"]
    assert gate(C1=at(60), C2=at(60))["decision"] == "continue"  # C3가 없으면 판단할 수 없어 계속한다


def test_flex_sessions_are_priced_at_half_and_cli_shows_the_plan(capsys):
    rows = [
        {"type": "session", "service_tier": "flex"},
        {"type": "run", "usage": {"input_tokens": 1000, "output_tokens": 2000}},
        {"type": "session", "service_tier": "default"},
        {"type": "run", "usage": {"input_tokens": 1000, "output_tokens": 2000}},
    ]
    assert harness._priced_tokens(rows) == (1500, 3000)
    assert main(["exp003", "--split", "dev", "--limit", "1", "--service-tier", "flex"]) == 1
    out = capsys.readouterr().out
    assert "C1p0" in out and "= 13회" in out and "처리 등급 flex" in out  # C0~C3 × 3 + C1p0 × 1


def test_flex_model_retries_then_falls_back_to_the_default_tier(monkeypatch):
    """flex 용량 부족(429)은 그래프 재시도 예산을 쓰지 않고 모델 안에서 처리한다(ADR-020)."""
    import httpx
    import openai
    from langchain_core.messages import AIMessage, HumanMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    from langchain_openai import ChatOpenAI

    from tashkeel_check.experiments import tiers

    def rate_limited(text):
        response = httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))
        return openai.RateLimitError(text, response=response, body=None)

    calls = []

    def fake_generate(self, messages, stop=None, run_manager=None, **kwargs):
        calls.append(kwargs.get("service_tier", self.service_tier))
        if plan.pop(0):
            raise rate_limited(tiers.FLEX_UNAVAILABLE + ". Please try again later.")
        return ChatResult(generations=[ChatGeneration(message=AIMessage("ok"))])

    monkeypatch.setattr(ChatOpenAI, "_generate", fake_generate)
    monkeypatch.setattr(tiers, "FLEX_WAITS", (0.0, 0.0))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    tiers.reset_fallback_counts()
    model = tiers.FlexChatOpenAI(model="gpt-test")
    plan = [True, False]  # 한 번 막히고 다시 부르면 된다
    assert model.invoke([HumanMessage("hi")]).content == "ok" and calls == ["flex", "flex"]
    plan, calls[:] = [True, True, True, False], []  # flex가 계속 막히면 그 호출만 기본 등급
    assert model.invoke([HumanMessage("hi")]).content == "ok" and calls == ["flex", "flex", "flex", "default"]
    assert tiers.fallback_counts() == {"flex_retry": 3, "default_fallback": 1}
    plan = [False]

    def other_limit(self, messages, stop=None, run_manager=None, **kwargs):
        raise rate_limited("Rate limit reached for requests")

    monkeypatch.setattr(ChatOpenAI, "_generate", other_limit)
    try:
        model.invoke([HumanMessage("hi")])
    except openai.RateLimitError:
        pass
    else:
        raise AssertionError("보통 속도 제한은 그대로 올라가야 한다")
