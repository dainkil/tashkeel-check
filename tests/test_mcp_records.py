"""회사 기록 MCP 서버(ADR-022): 메모리 전송, 범위 토큰, 고객 분리, 쓰기 도구 없음, LLM이 보는 툴 고정."""

from __future__ import annotations

import hashlib
import json

import pytest
from langchain_core.utils.function_calling import convert_to_openai_tool

from tashkeel_check.archive import CompanyArchive, InMemoryArchiveStore
from tashkeel_check.bundle.dictionary import InMemoryDictionary
from tashkeel_check.mcp.records import (
    RECORDS_TOOL,
    RecordsContext,
    ScopeRegistry,
    build_records_server,
    make_records_tool_factory,
    name_queries,
    start_records_client,
)
from tashkeel_check.rag.bundle import PracticeEmbeddings
from tashkeel_check.text import segment_text, tokenize

# 2026-10-22 LLM이 보는 기록 툴(이름·설명·인자). 바뀌면 M2 입력이 바뀐 것이다
RECORDS_TOOL_SHA = "0341c90145240280"
LEASE = "عقد إيجار\nالمؤجر: نوال الحربي (Nawal Al-Harbi)\n"
NOTICE = "إشعار حكومي\nالسيدة نوال الحربي مطلوبة"


@pytest.fixture
def setup():
    archive = CompanyArchive(InMemoryArchiveStore(), PracticeEmbeddings(), "practice")
    archive.index_document("acme", "lease", "lease.txt", segment_text(LEASE))
    scopes = ScopeRegistry()
    client = start_records_client(build_records_server(archive, InMemoryDictionary(), scopes))
    yield archive, scopes, client
    client.stop()


def _tool(client, scope, role="translator"):
    segs = segment_text(NOTICE)
    ctx = RecordsContext(tokenize(segs), segs, scope, role)
    return make_records_tool_factory(client)(ctx), ctx


def _sha(data) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:16]


def test_llm_facing_tool_takes_token_id_groups_only_and_is_pinned(setup):
    _, _, client = setup
    tool, _ = _tool(client, None)
    spec = convert_to_openai_tool(tool)
    assert spec["function"]["name"] == RECORDS_TOOL
    assert list(spec["function"]["parameters"]["properties"]) == ["names"]
    assert _sha(spec) == RECORDS_TOOL_SHA


def test_server_lists_only_the_read_tool(setup):
    _, _, client = setup
    assert client.list_tools() == [RECORDS_TOOL]


def test_scoped_call_goes_through_mcp_and_logs_returned_hits(setup):
    _, scopes, client = setup
    token = scopes.issue("acme", "notice", None)
    tool, ctx = _tool(client, token)
    calls_before = client.calls
    rows = tool.invoke({"names": [[3, 4], [2]]})
    assert client.calls == calls_before + 1
    assert rows[0]["arabic"] == "نوال الحربي" and rows[0]["hits"][0]["latin_candidates"] == ["Nawal Al-Harbi"]
    assert rows[1]["hits"] == []
    (entry,) = ctx.log
    assert (
        entry["via"] == "mcp" and entry["role"] == "translator" and entry["hit_ids"] == [rows[0]["hits"][0]["hit_id"]]
    )


@pytest.mark.parametrize("token", [None, "forged", "revoked"])
def test_missing_forged_or_revoked_scope_is_refused(setup, token):
    _, scopes, client = setup
    if token == "revoked":
        token = scopes.issue("acme", "notice", None)
        scopes.revoke(token)
    tool, ctx = _tool(client, token)
    rows = tool.invoke({"names": [[3, 4]]})
    if token is None:  # 범위가 없으면 부르지도 않는다
        assert rows == [] and "error" not in ctx.log[0]
    else:
        assert rows == [{"error": "records lookup failed"}] and "scope token" in ctx.log[0]["error"]


def test_scope_of_one_customer_never_sees_another(setup):
    _, scopes, client = setup
    tool, _ = _tool(client, scopes.issue("other", "notice", None))
    rows = tool.invoke({"names": [[3, 4]]})
    assert rows[0]["hits"] == [] and rows[0]["dictionary"] is None


def test_name_queries_skip_non_arabic_ids_and_collapse_repeats():
    segs = segment_text("نوال تكتب\nPrincipal: Nawal\nنوال")
    toks = tokenize(segs)
    nawal = [t["id"] for t in toks if t["text"] == "نوال"]
    latin = next(t["id"] for t in toks if t["script"] == "latin")
    q = name_queries(toks, segs, [nawal, [latin], [999]])
    assert len(q) == 1 and q[0]["arabic"] == "نوال" and q[0]["token_ids"] == nawal
    assert "Principal" in q[0]["context"]
