"""MCP 서버를 stdio로 띄워 툴·리소스·프롬프트 3종을 부른다. 툴은 분석기가 필요해 camel 마커다."""

from __future__ import annotations

import pytest

from tashkeel_check.config import Settings
from tashkeel_check.errors import ConfigError
from tashkeel_check.fake import FakeAgentModel
from tashkeel_check.mcp.client import MCPClient, default_server_command, with_retry
from tashkeel_check.mcp.tools import ANALYZE_TOOL_DOC, make_mcp_analyze_tool_factory
from tashkeel_check.prompts import system_prompt
from tashkeel_check.runner import Reviewer
from tashkeel_check.tools import make_analyze_tool

from .conftest import fake_analyze


@pytest.fixture(scope="module")
def mcp():
    cmd, args, env = default_server_command("data")
    client = MCPClient(cmd, args, env=env, timeout=60)
    client.start()
    yield client
    client.stop()


def test_server_exposes_tool_resource_and_prompt(mcp):
    assert mcp.list_tools() == ["analyze_tokens"]
    assert mcp.list_prompts() == ["review_instructions"]
    assert mcp.list_resource_templates() == [
        "document://synthetic/{split}",
        "document://synthetic/{split}/{doc_id}",
    ]


def test_prompt_matches_in_process_system_prompt(mcp):
    for cond in ("C0", "C1", "C2", "C3"):
        assert mcp.get_prompt("review_instructions", {"condition": cond}) == system_prompt(cond)
    with pytest.raises(Exception, match="unknown condition"):
        mcp.get_prompt("review_instructions", {"condition": "C9"})


def test_resource_lists_and_reads_documents_without_gold(mcp):
    rows = mcp.read_json_resource("document://synthetic/dev")
    assert len(rows) == 10 and rows[4]["doc_id"] == "dev_005"
    doc = mcp.read_json_resource("document://synthetic/dev/dev_005")
    assert doc["doc_id"] == "dev_005" and "gold" not in doc and doc["segments"]
    with pytest.raises(Exception, match="document not found"):
        mcp.read_resource("document://synthetic/dev/nope")
    with pytest.raises(Exception, match="unknown split"):
        mcp.read_resource("document://synthetic/test")


@pytest.mark.camel
def test_tool_analyzes_known_ids_and_reports_bad_ids(mcp):
    tokens = [{"id": 0, "text": "وكالة", "script": "ar"}, {"id": 1, "text": "Z8495650", "script": "latin"}]
    rows = mcp.call_tool("analyze_tokens", {"tokens": tokens, "token_ids": [0, 1, 7], "max_candidates": 3})
    assert rows[0]["token_id"] == 0 and rows[0]["ambiguous"] is True and len(rows[0]["candidates"]) <= 3
    assert rows[1] == {"token_id": 1, "error": "not an Arabic token"}
    assert rows[2] == {"token_id": 7, "error": "unknown token id"}
    assert mcp.healthy and mcp.ping()


def test_mcp_tool_description_equals_in_process_tool():
    """LLM이 보는 툴 설명이 in-process 툴과 같아야 C2 조건이 바뀌지 않는다."""
    assert ANALYZE_TOOL_DOC.strip() == make_analyze_tool([], {}, [], 10).description


def test_dead_server_is_a_config_error_not_a_fallback():
    client = MCPClient("python-that-does-not-exist-xyz", ["-m", "nothing"], timeout=5)
    with pytest.raises(ConfigError, match="MCP 서버"):
        client.start()
    assert client.healthy is False and client.ping() is False


def test_stopped_server_fails_ping(mcp_stopped=None):
    cmd, args, env = default_server_command("data")
    client = MCPClient(cmd, args, env=env, timeout=60)
    client.start()
    assert client.ping()
    client.stop()
    assert client.ping() is False and client.healthy is False


def test_with_retry_retries_timeouts_only():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("slow")
        return "ok"

    assert with_retry(flaky, retries=3, base_delay=0) == ("ok", 2)

    def broken():
        raise ValueError("permanent")

    with pytest.raises(ValueError):
        with_retry(broken, retries=3, base_delay=0)


@pytest.mark.camel
def test_c2_through_mcp_tool_factory_matches_in_process_result(mcp):
    """USE_MCP_TOOLS 경로: 가짜 모델 C2가 MCP 툴을 부르고, 결과는 in-process 툴과 같다(elapsed 제외)."""
    from tashkeel_check.runner import load_doc

    doc = load_doc("data/synthetic/dev/dev_005.json")
    settings = Settings()
    via_mcp = Reviewer(
        FakeAgentModel(), settings, analyze_fn=fake_analyze, analyze_tool_factory=make_mcp_analyze_tool_factory(mcp)
    )
    plain = Reviewer(FakeAgentModel(), settings, analyze_fn=fake_analyze)
    before = mcp.calls
    a = via_mcp.run(doc, "C2").model_dump(exclude={"meta": {"elapsed_s"}})
    b = plain.run(doc, "C2").model_dump(exclude={"meta": {"elapsed_s"}})
    assert mcp.calls == before + 1
    # 분석기가 다르면(가짜 vs camel) 후보 내용은 다를 수 있으나 처분·토큰·구조는 같다
    assert a["meta"]["tool_calls"] == b["meta"]["tool_calls"] == 1
    assert [i["token_ids"] for i in a["items"]] == [i["token_ids"] for i in b["items"]]
    assert a["metrics"]["valid_output"] and a["meta"]["bundle_search"] is False
