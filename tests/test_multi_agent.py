"""멀티 에이전트 틀 M1(ADR-019): 규칙 중재자 단위, 가짜 모델로 끝까지, 검증자 격리, 재시도, 해시 핀.

C0~C3(`CONDITIONS`)와 골든·해시는 바뀌지 않아야 한다(`test_llm_inputs.py`·`test_golden.py`가 지킨다).
"""

from __future__ import annotations

import hashlib
import json

import pytest
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from tashkeel_check.config import ALL_CONDITIONS, CONDITIONS, ENGINE_CONDITIONS, Settings
from tashkeel_check.fake import OUTPUT_TOOL, VERIFIER_TOOL, FakeAgentModel, practice_responder, tool_call
from tashkeel_check.multi_agent import HOLD_CODES, VerifierOutput, arbitrate
from tashkeel_check.prompts import prompt_hash
from tashkeel_check.runner import run_document
from tashkeel_check.text import tokenize

from .conftest import fake_analyze, ids_of

# 2026-10-21 M1 지시문 해시(번역자 = C3 지시문 + 검증자 + 묶음 참고 문장)와 검증자 스키마
PROMPT_HASHES_M1 = {"p0": "9788df7ee9b62319", "p1": "71d247a6603441f0"}
VERIFIER_SCHEMA_SHA = "455b39cb6ab5cff9"


def _sha(data) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def test_conditions_are_separate_and_pinned():
    assert CONDITIONS == ("C0", "C1", "C2", "C3") and ENGINE_CONDITIONS == ("M1",)
    assert ALL_CONDITIONS == ("C0", "C1", "C2", "C3", "M1")
    assert {v: prompt_hash("M1", v) for v in ("p0", "p1")} == PROMPT_HASHES_M1
    assert _sha(convert_to_openai_tool(VerifierOutput)) == VERIFIER_SCHEMA_SHA


# ---- 중재 규칙(순수 함수) ----
def _cand(*spellings):
    return [{"reading": None, "romanized": s, "source": "llm"} for s in spellings]


def _t_item(
    ids, decision="evidence_adopt", adopted="Salem bin Hamad Al Muslim", ev=("s03", "Salem bin Hamad Al Muslim")
):
    return {
        "token_ids": ids,
        "type": "proper_noun",
        "candidates": _cand(adopted or "Salim"),
        "decision": decision,
        "adopted": adopted,
        "reason": "t",
        "confidence": 0.9 if decision == "adopt" else None,
        "evidence": {"segment_id": ev[0], "quote": ev[1]} if ev and decision == "evidence_adopt" else None,
    }


def _v_item(
    ids, decision="evidence_adopt", adopted="Salem bin Hamad Al Muslim", ev=("s03", "Salem bin Hamad Al Muslim")
):
    return {
        "token_ids": ids,
        "candidates": _cand(adopted or "Salem"),
        "decision": decision,
        "adopted": adopted,
        "evidence": {"segment_id": ev[0], "quote": ev[1]} if ev and decision == "evidence_adopt" else None,
        "reason": "v",
    }


@pytest.fixture
def ctx(mini_doc):
    tokens = tokenize(mini_doc["segments"])
    principal = ids_of(tokens, "s02", ["سالم", "حمد", "المسلم"])
    agent = ids_of(tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    translation = [{"segment_id": s["segment_id"], "english": "x"} for s in mini_doc["segments"]]
    translation[1]["english"] = "Mr. Salem bin Hamad Al Muslim, UAE national, appeared."
    return tokens, mini_doc["segments"], principal, agent, translation


def _arb(ctx, t_items, v_items, rule="v1"):
    tokens, segments, _, _, translation = ctx
    out, stats = arbitrate({"translation": translation, "items": t_items}, {"items": v_items}, tokens, segments, rule)
    return out, stats


def test_both_agree_with_valid_evidence_confirms(ctx):
    _, _, principal, _, _ = ctx
    out, stats = _arb(ctx, [_t_item(principal)], [_v_item(principal)])
    assert out["items"][0]["decision"] == "evidence_adopt" and stats["n_agreed_confirmed"] == 1
    assert stats["n_held_by_arbiter"] == 0 and out["translation"][1]["english"].startswith("Mr. Salem")


@pytest.mark.parametrize(
    "t_kw, v_items_fn, code",
    [
        ({"decision": "adopt", "ev": None}, lambda p: [_v_item(p)], "translator_unsupported_adopt"),
        ({}, lambda p: [], "verifier_missing"),
        ({}, lambda p: [_v_item(p, decision="hold", adopted=None, ev=None)], "verifier_hold"),
        (
            {},
            lambda p: [_v_item(p, adopted="Salim bin Hamad Al Muslim", ev=("s03", "Salem bin Hamad Al Muslim"))],
            "spelling_disagree",
        ),
        ({"ev": ("s03", "not in segment")}, lambda p: [_v_item(p)], "evidence_failed"),
    ],
)
def test_disagreement_or_bad_evidence_holds(ctx, t_kw, v_items_fn, code):
    _, _, principal, _, _ = ctx
    out, stats = _arb(ctx, [_t_item(principal, **t_kw)], v_items_fn(principal))
    item = out["items"][0]
    assert item["decision"] == "hold" and item["adopted"] is None and item["evidence"] is None
    assert item["reason"].startswith(f"arbiter:{code}") and stats["by_code"][code] == 1
    assert stats["n_held_by_arbiter"] == 1 and stats["n_agreed_confirmed"] == 0
    assert code in HOLD_CODES
    # 보류로 바뀐 이름이 번역문에 채택 철자 그대로 있었으면 [c1/c2]로 고쳐 쓴다(C1 규칙 5)
    assert out["translation"][1]["english"].startswith("Mr. [") and stats["n_translation_rewritten"] == 1


def test_translator_hold_passes_and_candidates_merge(ctx):
    _, _, principal, _, _ = ctx
    t = _t_item(principal, decision="hold", adopted=None, ev=None)
    t["candidates"] = _cand("Salim")
    out, stats = _arb(ctx, [t], [_v_item(principal, decision="hold", adopted=None, ev=None)])
    item = out["items"][0]
    assert item["decision"] == "hold" and [c["romanized"] for c in item["candidates"]] == ["Salim", "Salem"]
    assert stats["n_held_by_arbiter"] == 0  # 번역자가 이미 보류한 것은 중재자가 바꾼 게 아니다


def test_verifier_only_name_is_added_as_hold_and_words_pass(ctx):
    _, _, principal, agent, _ = ctx
    word = {
        "token_ids": [1],
        "type": "word",
        "candidates": _cand("power of attorney"),
        "decision": "adopt",
        "adopted": "power of attorney",
        "reason": "w",
        "confidence": 0.8,
        "evidence": None,
    }
    out, stats = _arb(ctx, [word, _t_item(principal)], [_v_item(principal), _v_item(agent, "hold", None, None)])
    assert out["items"][0] == word
    extra = out["items"][-1]
    assert extra["token_ids"] == sorted(agent) and extra["decision"] == "hold" and "verifier_only" in extra["reason"]
    assert stats["n_verifier_only"] == 1 and stats["n_agreed_confirmed"] == 1


# ---- 가짜 모델로 끝까지 ----
class Dispatcher:
    """바인딩된 툴 이름으로 응답을 고른다(호출 순서에 의존하지 않는다). 받은 메시지를 기록한다."""

    def __init__(self, translator, verifier):
        self.translator, self.verifier = translator, verifier
        self.seen: dict[str, list] = {OUTPUT_TOOL: [], VERIFIER_TOOL: []}
        self.calls = 0

    def __call__(self, messages, bound):
        self.calls += 1
        if VERIFIER_TOOL in bound:
            self.seen[VERIFIER_TOOL].append(messages)
            r = self.verifier
        else:
            self.seen[OUTPUT_TOOL].append(messages)
            r = self.translator
        if isinstance(r, Exception):
            raise r
        return r(messages) if callable(r) else r


def _texts(messages):
    return [str(m.content) for m in messages if isinstance(m, (HumanMessage, SystemMessage, ToolMessage))]


def test_m1_runs_end_to_end_with_fake_model(mini_doc, tmp_path):
    tokens = tokenize(mini_doc["segments"])
    principal = ids_of(tokens, "s02", ["سالم", "حمد", "المسلم"])
    translation = [{"segment_id": s["segment_id"], "english": "x"} for s in mini_doc["segments"]]
    d = Dispatcher(
        tool_call(OUTPUT_TOOL, {"translation": translation, "items": [_t_item(principal)]}),
        tool_call(VERIFIER_TOOL, {"items": [_v_item(principal)]}),
    )
    result = run_document(
        mini_doc, "M1", FakeAgentModel(responder=d), Settings(), out_dir=tmp_path, analyze_fn=fake_analyze
    )
    m = result.metrics
    assert result.condition == "M1" and m["valid_output"] and m["attempts"] == 1 and d.calls == 2
    assert m["usage"]["llm_calls"] == 2
    eng = m["engine"]
    assert eng["translator"]["llm_calls"] == 1 and eng["verifier"]["llm_calls"] == 1
    assert eng["arbiter"]["n_agreed_confirmed"] == 1 and eng["prompt_version"] == "p0"
    assert [it.final_decision for it in result.items if it.type == "proper_noun"]
    for name in ("segments.json", "proper_nouns.csv", "metrics.json", "run_meta.json"):
        assert (tmp_path / name).exists()
    assert json.loads((tmp_path / "run_meta.json").read_text())["prompt_hash"] == PROMPT_HASHES_M1["p0"]
    # 검증자는 번역자 출력을 보지 않는다: 메시지에 번역문도 AgentOutput 툴도 없다
    v_msgs = d.seen[VERIFIER_TOOL][0]
    assert all("Mr. Salem" not in t and t != "x" for t in _texts(v_msgs))
    assert not any(isinstance(m_, ToolMessage) for m_ in v_msgs)
    assert "You do not translate" in str(v_msgs[0].content) and "ANALYZER" in str(v_msgs[-1].content)
    assert "BUNDLE EVIDENCE" not in str(v_msgs[-1].content)


def test_m1_practice_mode_runs(mini_doc, tmp_path):
    result = run_document(
        mini_doc, "M1", FakeAgentModel(responder=practice_responder), Settings(), analyze_fn=fake_analyze
    )
    assert result.metrics["valid_output"] and result.metrics["engine"]["arbiter"]["n_verifier_items"] >= 0


def test_m1_retry_reruns_both_agents(mini_doc):
    translation = [
        {"segment_id": s["segment_id"], "english": "x"} for s in mini_doc["segments"][:1]
    ]  # 구간 누락 → 재시도
    d = Dispatcher(
        tool_call(OUTPUT_TOOL, {"translation": translation, "items": []}), tool_call(VERIFIER_TOOL, {"items": []})
    )
    result = run_document(mini_doc, "M1", FakeAgentModel(responder=d), Settings(), analyze_fn=fake_analyze)
    assert result.metrics["attempts"] == 2 and d.calls == 4 and not result.metrics["valid_output"]
    assert result.metrics["usage"]["llm_calls"] == 4


def test_m1_translator_failure_skips_verifier(mini_doc):
    d = Dispatcher(RuntimeError("boom"), tool_call(VERIFIER_TOOL, {"items": []}))
    result = run_document(mini_doc, "M1", FakeAgentModel(responder=d), Settings(max_retries=0), analyze_fn=fake_analyze)
    assert not result.metrics["valid_output"] and d.seen[VERIFIER_TOOL] == []
    assert any("translator: RuntimeError" in e for e in result.metrics["errors"])


def test_bundle_evidence_is_context_for_both_agents(mini_doc):
    tokens = tokenize(mini_doc["segments"])
    principal = ids_of(tokens, "s02", ["سالم", "حمد", "المسلم"])
    translation = [{"segment_id": s["segment_id"], "english": "x"} for s in mini_doc["segments"]]
    d = Dispatcher(
        tool_call(OUTPUT_TOOL, {"translation": translation, "items": [_t_item(principal)]}),
        tool_call(VERIFIER_TOOL, {"items": [_v_item(principal)]}),
    )
    doc = dict(mini_doc)
    doc["bundle_evidence"] = [
        {
            "segment_id": "s02",
            "entity_id": "p1",
            "english": "Salem Hamad Almuslim",
            "document_id": "id_001",
            "source_segment_id": "s01",
        }
    ]
    run_document(doc, "M1", FakeAgentModel(responder=d), Settings(), analyze_fn=fake_analyze)
    for tool in (OUTPUT_TOOL, VERIFIER_TOOL):
        msgs = d.seen[tool][0]
        assert "BUNDLE EVIDENCE" in str(msgs[-1].content) and "Salem Hamad Almuslim" in str(msgs[-1].content)
        assert "context, not citable evidence" in str(msgs[0].content)
