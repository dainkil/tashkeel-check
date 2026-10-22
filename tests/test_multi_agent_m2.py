"""조건 M2(ADR-022): 해시 고정, 두 역할 동시 실행, 검증자 격리, 보관함 선택은 확정을 못 바꿈, 툴 호출 상한.

C0~C3·M1의 골든과 해시는 test_golden.py·test_llm_inputs.py·test_multi_agent.py가 지킨다.
"""

from __future__ import annotations

import hashlib
import json
import threading

import pytest
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

from tashkeel_check.archive import CompanyArchive, InMemoryArchiveStore
from tashkeel_check.bundle.dictionary import InMemoryDictionary
from tashkeel_check.config import Settings
from tashkeel_check.fake import OUTPUT_TOOL_M2, RECORDS_TOOL, VERIFIER_TOOL_M2, FakeAgentModel, tool_call
from tashkeel_check.mcp.records import (
    ScopeRegistry,
    build_records_server,
    make_records_tool_factory,
    start_records_client,
)
from tashkeel_check.multi_agent_m2 import AgentOutputM2, VerifierOutputM2, archive_claims
from tashkeel_check.prompts import C1_SYSTEM_P1, m2_system_prompts, prompt_hash
from tashkeel_check.rag.bundle import PracticeEmbeddings
from tashkeel_check.runner import Reviewer, run_document
from tashkeel_check.text import segment_text, tokenize

from .conftest import fake_analyze, ids_of

# 2026-10-22 M2 지시문(번역자·검증자, p1 규칙)과 출력 스키마
PROMPT_HASH_M2 = "715047497c2c8928"
AGENT_OUTPUT_M2_SHA = "8f02558e597ac777"
VERIFIER_M2_SHA = "f38f234135e70f22"
EARLIER = "تفويض سابق\nالوكيل: راشد مسلم الكعبي (Rashid Musallam Al Kaabi)\n"


def _sha(data) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def test_m2_prompts_and_schemas_are_pinned():
    assert prompt_hash("M2", "p1") == prompt_hash("M2", "p0") == PROMPT_HASH_M2  # M2는 언제나 p1 규칙
    assert _sha(convert_to_openai_tool(AgentOutputM2)) == AGENT_OUTPUT_M2_SHA
    assert _sha(convert_to_openai_tool(VerifierOutputM2)) == VERIFIER_M2_SHA
    p = m2_system_prompts()
    assert (
        p["translator"].startswith(C1_SYSTEM_P1) and "\n8. You have a tool, search_company_records" in p["translator"]
    )
    assert "You do not translate" in p["verifier"] and "ANALYZER" not in p["verifier"]


@pytest.fixture
def records():
    archive = CompanyArchive(InMemoryArchiveStore(), PracticeEmbeddings(), "practice")
    archive.index_document("acme", "earlier", "earlier.txt", segment_text(EARLIER))
    scopes = ScopeRegistry()
    client = start_records_client(build_records_server(archive, InMemoryDictionary(), scopes))
    yield archive, scopes, client
    client.stop()


def _cand(s):
    return [{"reading": None, "romanized": s, "source": "llm"}]


def _hold(ids, archive=None, full=True):
    it = {
        "token_ids": ids,
        "candidates": _cand("Rashid"),
        "decision": "hold",
        "adopted": None,
        "evidence": None,
        "reason": "r",
        "archive": archive,
    }
    return {**it, "type": "proper_noun", "confidence": None} if full else it


def _adopt(ids, full=True):
    it = {
        "token_ids": ids,
        "candidates": _cand("Salem bin Hamad Al Muslim"),
        "decision": "evidence_adopt",
        "adopted": "Salem bin Hamad Al Muslim",
        "evidence": {"segment_id": "s03", "quote": "Salem bin Hamad Al Muslim"},
        "reason": "r",
        "archive": None,
    }
    return {**it, "type": "proper_noun", "confidence": 0.9} if full else it


class Roles:
    """바인딩된 출력 툴로 역할을 가른다. 역할마다 (기록 툴을 먼저 부를 이름들, 결과를 만드는 함수)."""

    def __init__(self, translator, verifier, barrier: threading.Barrier | None = None):
        self.fns = {OUTPUT_TOOL_M2: translator, VERIFIER_TOOL_M2: verifier}
        self.seen: dict[str, list] = {OUTPUT_TOOL_M2: [], VERIFIER_TOOL_M2: []}
        self.barrier = barrier

    def __call__(self, messages, bound):
        role = OUTPUT_TOOL_M2 if OUTPUT_TOOL_M2 in bound else VERIFIER_TOOL_M2
        self.seen[role].append(list(messages))
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        if self.barrier is not None and len(self.seen[role]) == 1:
            self.barrier.wait()  # 두 역할이 동시에 돌지 않으면 여기서 시간 초과로 깨진다
        names, make = self.fns[role]
        if isinstance(make, Exception):
            raise make
        if names and RECORDS_TOOL in bound and not tool_msgs:
            return tool_call(RECORDS_TOOL, {"names": names})
        rows = json.loads(str(tool_msgs[0].content)) if tool_msgs else []
        return tool_call(role, make(rows))


def _first_hit(rows):
    return next(h["hit_id"] for r in rows for h in r.get("hits", []))


def _run(mini_doc, records, roles, **settings_kw):
    _, scopes, client = records
    rv = Reviewer(
        FakeAgentModel(responder=roles),
        Settings(**settings_kw),
        analyze_fn=fake_analyze,
        records_tool_factory=make_records_tool_factory(client),
    )
    token = scopes.issue("acme", "now", None)
    try:
        return rv.run(mini_doc, "M2", records_scope=token)
    finally:
        scopes.revoke(token)


def test_both_roles_run_in_parallel_and_verifier_never_sees_translator(mini_doc, records):
    tokens = tokenize(mini_doc["segments"])
    principal = ids_of(tokens, "s02", ["سالم", "حمد", "المسلم"])
    translation = [{"segment_id": s["segment_id"], "english": "Mr. Salem appeared"} for s in mini_doc["segments"]]
    roles = Roles(
        (None, lambda rows: {"translation": translation, "items": [_adopt(principal)]}),
        (None, lambda rows: {"items": [_adopt(principal, full=False)]}),
        barrier=threading.Barrier(2, timeout=10),
    )
    result = _run(mini_doc, records, roles)
    m = result.metrics
    assert result.condition == "M2" and m["valid_output"] and m["usage"]["llm_calls"] == 2
    assert [it.final_decision for it in result.items if it.type == "proper_noun"] == ["evidence_adopt"]
    assert m["engine"]["arbiter"]["n_agreed_confirmed"] == 1 and m["engine"]["archive"] == []
    v_msgs = roles.seen[VERIFIER_TOOL_M2][0]
    assert all("Mr. Salem" not in str(x.content) for x in v_msgs)
    human = [str(x.content) for x in v_msgs if isinstance(x, HumanMessage)]
    assert human == [str(x.content) for x in roles.seen[OUTPUT_TOOL_M2][0] if isinstance(x, HumanMessage)]
    assert "ANALYZER" not in human[0]  # C1 입력


def test_archive_pick_never_changes_a_decision_and_only_returned_hits_count(mini_doc, records):
    tokens = tokenize(mini_doc["segments"])
    principal = ids_of(tokens, "s02", ["سالم", "حمد", "المسلم"])
    agent = ids_of(tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    translation = [{"segment_id": s["segment_id"], "english": "x"} for s in mini_doc["segments"]]

    def t_out(rows):
        pick = {"hit_id": _first_hit(rows), "spelling": "Rashid Musallam Al Kaabi"}
        bogus = {"hit_id": _first_hit(rows), "spelling": "Salem"}  # 확정된 이름에 붙인 선택은 버린다
        return {"translation": translation, "items": [{**_adopt(principal), "archive": bogus}, _hold(agent, pick)]}

    def v_out(rows):
        fabricated = {"hit_id": "ffffffffff", "spelling": "Rashid Musallam Al Kaabi"}  # 툴이 돌려주지 않은 구절
        return {"items": [_adopt(principal, full=False), _hold(agent, fabricated, full=False)]}

    result = _run(mini_doc, records, Roles(([agent], t_out), ([agent], v_out)))
    decisions = {tuple(it.token_ids): it.final_decision for it in result.items if it.type == "proper_noun"}
    assert decisions == {tuple(principal): "evidence_adopt", tuple(agent): "hold"}
    (claim,) = result.metrics["engine"]["archive"]
    assert claim["token_ids"] == agent
    assert claim["picks"] == [
        {"spelling": "Rashid Musallam Al Kaabi", "hit_ids": [claim["picks"][0]["hit_ids"][0]], "by": ["translator"]}
    ]
    assert result.metrics["engine"]["tool_calls"] == {"translator": 1, "verifier": 1}
    assert result.meta.tool_calls == 2  # 역할당 한 번(via mcp는 test_mcp_records.py가 본다)


def test_record_tool_is_capped_per_role(mini_doc, records):
    tokens = tokenize(mini_doc["segments"])
    agent = ids_of(tokens, "s04", ["راشد", "مسلم", "الكعبي"])
    translation = [{"segment_id": s["segment_id"], "english": "x"} for s in mini_doc["segments"]]

    class Greedy(Roles):
        def __call__(self, messages, bound):
            role = OUTPUT_TOOL_M2 if OUTPUT_TOOL_M2 in bound else VERIFIER_TOOL_M2
            n = sum(isinstance(m, ToolMessage) for m in messages)
            if n < 5:  # 상한을 넘겨도 계속 부르려 한다
                return tool_call(RECORDS_TOOL, {"names": [agent]})
            out = {"items": []} if role == VERIFIER_TOOL_M2 else {"translation": translation, "items": []}
            return tool_call(role, out)

    result = _run(mini_doc, records, Greedy((None, None), (None, None)))
    assert result.metrics["engine"]["tool_calls"] == {"translator": 2, "verifier": 2}
    assert result.metrics["valid_output"]


def test_translator_failure_does_not_stop_the_parallel_verifier(mini_doc, records):
    roles = Roles((None, RuntimeError("boom")), (None, lambda rows: {"items": []}))
    result = _run(mini_doc, records, roles, max_retries=0)
    assert not result.metrics["valid_output"] and len(roles.seen[VERIFIER_TOOL_M2]) == 1
    assert any("translator: RuntimeError" in e for e in result.metrics["errors"])


def test_m2_runs_without_records_tool(mini_doc):
    """회사 기록 툴이 없으면(CLI 등) 기록 없이 돈다. 연습 모드는 항목을 내지 않는다."""
    from tashkeel_check.fake import practice_responder

    result = run_document(
        mini_doc, "M2", FakeAgentModel(responder=practice_responder), Settings(), analyze_fn=fake_analyze
    )
    assert result.metrics["valid_output"] and result.meta.tool_calls == 0
    assert result.metrics["engine"]["archive"] == [] and result.meta.prompt_hash == PROMPT_HASH_M2


def test_archive_claims_merge_same_spelling_and_ignore_confirmed_items():
    held = {"token_ids": [4, 5], "type": "proper_noun", "decision": "hold"}
    done = {"token_ids": [1], "type": "proper_noun", "decision": "evidence_adopt"}
    key, done_key = frozenset([4, 5]), frozenset([1])
    picks = {
        "translator": {key: {"hit_id": "a", "spelling": "Al-Kaabi"}, done_key: {"hit_id": "a", "spelling": "X"}},
        "verifier": {key: {"hit_id": "b", "spelling": "AL KAABI"}},
    }
    claims = archive_claims([held, done], picks, {"translator": {"a"}, "verifier": {"b"}})
    assert claims == [
        {
            "token_ids": [4, 5],
            "picks": [{"spelling": "Al-Kaabi", "hit_ids": ["a", "b"], "by": ["translator", "verifier"]}],
        }
    ]
