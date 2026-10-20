"""그래프 전체를 가짜 모델(스크립트된 tool call)로 돌리는 결정적 테스트."""

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from tashkeel_check.config import Settings
from tashkeel_check.fake import FakeAgentModel, tool_call
from tashkeel_check.runner import run_document

from .conftest import fake_analyze, ids_of

SETTINGS = Settings()


def _translation(doc):
    return [{"segment_id": s["segment_id"], "english": "x"} for s in doc["segments"]]


class Recorder:
    """응답을 순서대로 내고, 모델이 받은 메시지를 기록한다."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.seen: list[list] = []
        self.bound: list[list[str]] = []

    def __call__(self, messages, bound):
        self.seen.append(messages)
        self.bound.append(bound)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r(messages) if callable(r) else r

    def texts(self):
        return [str(m.content) for msgs in self.seen for m in msgs]


def _run(doc, condition, recorder, tmp_path=None):
    model = FakeAgentModel(responder=recorder)
    return run_document(doc, condition, model, SETTINGS, out_dir=tmp_path, analyze_fn=fake_analyze)


def test_c1_structured_output_writes_all_artifacts(mini_doc, mini_tokens, tmp_path):
    agent = ids_of(mini_tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    out = {
        "translation": _translation(mini_doc),
        "items": [
            {
                "token_ids": agent,
                "type": "proper_noun",
                "candidates": [{"reading": None, "romanized": "Musallam", "source": "llm"}],
                "decision": "hold",
                "adopted": None,
                "reason": "no evidence",
                "confidence": None,
                "evidence": None,
            }
        ],
    }
    rec = Recorder(tool_call("AgentOutput", out))
    result = _run(mini_doc, "C1", rec, tmp_path)
    m = result.metrics
    assert m["valid_output"] and m["attempts"] == 1
    assert m["hold_rate"] == 1.0
    for name in ("segments.json", "proper_nouns.csv", "metrics.json", "run_meta.json"):
        assert (tmp_path / name).exists()
    meta = json.loads((tmp_path / "run_meta.json").read_text())
    assert meta["condition"] == "C1" and meta["model"] == "fake-agent" and meta["prompt_hash"]
    assert "analyze_tokens" not in rec.bound[0]


def test_gold_never_reaches_the_model(mini_doc):
    rec = Recorder(tool_call("AgentOutput", {"translation": _translation(mini_doc), "items": []}))
    _run(mini_doc, "C3", rec)
    joined = "\n".join(rec.texts())
    assert "Kaabi" not in joined and "Rashid" not in joined and "english_used" not in joined


def test_c2_binds_the_analyzer_tool_and_logs_calls(mini_doc, mini_tokens):
    musallam = ids_of(mini_tokens, "s04", ["مسلم"])
    final = tool_call("AgentOutput", {"translation": _translation(mini_doc), "items": []})
    rec = Recorder(tool_call("analyze_tokens", {"token_ids": musallam + [999]}), final)
    result = _run(mini_doc, "C2", rec)
    assert "analyze_tokens" in rec.bound[0]
    tool_msgs = [m for m in rec.seen[1] if isinstance(m, ToolMessage)]
    payload = json.loads(tool_msgs[0].content)
    assert payload[0]["ambiguous"] is True and payload[1]["error"] == "unknown token id"
    assert result.metrics["tool"]["calls"] == 1
    assert result.meta.tool_calls == 1


def test_only_c3_shows_analyzer_results_and_only_c2_mentions_the_tool(mini_doc):
    prompts = {}
    for cond in ("C1", "C2", "C3"):
        rec = Recorder(tool_call("AgentOutput", {"translation": _translation(mini_doc), "items": []}))
        _run(mini_doc, cond, rec)
        sys_msg = next(m for m in rec.seen[0] if isinstance(m, SystemMessage))
        human = next(m for m in rec.seen[0] if isinstance(m, HumanMessage))
        prompts[cond] = (str(sys_msg.content), str(human.content))
    assert "ANALYZER" in prompts["C3"][1] and "ANALYZER" not in prompts["C1"][1] and "ANALYZER" not in prompts["C2"][1]
    assert "analyze_tokens" in prompts["C2"][0] and "analyze_tokens" not in prompts["C1"][0]
    assert prompts["C1"][1] == prompts["C2"][1]  # C2는 사용자 메시지를 바꾸지 않는다


def test_c0_plain_translation(mini_doc):
    text = "\n".join(f"[{s['segment_id']}] line" for s in mini_doc["segments"])
    rec = Recorder(AIMessage(content=text))
    result = _run(mini_doc, "C0", rec)
    assert result.metrics["valid_output"]
    assert result.metrics["silent_rate"] == 1.0  # 이름이 번역문에 없으면 not_found로 말없이 찍음에 들어간다
    human = next(m for m in rec.seen[0] if isinstance(m, HumanMessage))
    assert "TOKENS" not in str(human.content)


def test_retry_once_on_missing_segments_then_succeed(mini_doc):
    partial = tool_call("AgentOutput", {"translation": _translation(mini_doc)[:2], "items": []})
    full = tool_call("AgentOutput", {"translation": _translation(mini_doc), "items": []})
    result = _run(mini_doc, "C1", Recorder(partial, full))
    assert result.metrics["attempts"] == 2 and result.metrics["valid_output"]


def test_gives_up_after_one_retry_and_still_reconciles(mini_doc):
    partial = tool_call("AgentOutput", {"translation": _translation(mini_doc)[:1], "items": []})
    result = _run(mini_doc, "C1", Recorder(partial, partial))
    m = result.metrics
    assert m["attempts"] == 2 and not m["valid_output"]
    assert m["silent_rate"] == 1.0 and len(m["errors"]) == 2


def test_model_error_is_recorded_and_retried(mini_doc):
    full = tool_call("AgentOutput", {"translation": _translation(mini_doc), "items": []})
    result = _run(mini_doc, "C1", Recorder(RuntimeError("API down"), full))
    m = result.metrics
    assert m["valid_output"] and m["attempts"] == 2
    assert "API down" in m["errors"][0]


def test_practice_mode_runs_every_condition(mini_doc):
    for cond in ("C0", "C1", "C2", "C3"):
        result = run_document(mini_doc, cond, FakeAgentModel(), SETTINGS, analyze_fn=fake_analyze)
        assert result.metrics["valid_output"], cond


def test_reused_reviewer_matches_fresh_runs():
    from tashkeel_check.runner import Reviewer, load_doc

    from .golden_cases import DEV_DOCS

    def strip(result):
        return result.model_dump(exclude={"meta": {"elapsed_s"}})

    reviewer = Reviewer(FakeAgentModel(), SETTINGS, analyze_fn=fake_analyze)
    for path in DEV_DOCS[:3]:
        doc = load_doc(path)
        for cond in ("C0", "C1", "C2", "C3"):
            fresh = run_document(doc, cond, FakeAgentModel(), SETTINGS, analyze_fn=fake_analyze)
            assert strip(reviewer.run(doc, cond)) == strip(fresh), (doc["doc_id"], cond)
