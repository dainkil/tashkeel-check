"""조건 M2(ADR-022): 서비스 기본 검수 경로. M1 틀에 회사 기록 툴을 더하고 두 역할을 동시에 돌린다.

- 번역자: C1 입력(원문·토큰 표, 분석기 블록 없음) + p1 규칙 + 기록 툴 규칙. `AgentOutputM2`를 낸다.
- 검증자: 같은 입력만 보고(번역자 출력은 보지 않는다) 고유명사마다 처분을 낸다. 번역하지 않는다.
- 두 역할은 `search_company_records`(MCP, 회사 사전·문서 보관함)를 역할당 최대 2번 부른다.
- 중재자: M1의 `arbitrate`를 그대로 쓴다(문서 안 근거로 둘이 같은 철자를 냈을 때만 확정). 보관함 선택(`archive`)은
  확정을 바꾸지 못한다. 중재자는 그것을 항목에서 떼어 `engine["archive"]`에 적고, 화면에 낼지는 덧씌움
  (`archive_apply`)이 보관함 원문으로 다시 확인해 정한다.
두 역할이 같은 단계에서 돌기 때문에 사용량·툴 기록·오류를 역할별 키에 따로 쓴다(같은 키를 쓰면 LangGraph가 거부한다).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from .config import Settings
from .mcp.records import RECORDS_TOOL, RecordsContext, RecordsToolFactory
from .multi_agent import VerifierItem, _zero, add_usage, arbitrate
from .prompts import m2_system_prompts, user_message
from .romanize import strict_key
from .schemas import Item, SegmentTranslation
from .text import Segment, Token

logger = logging.getLogger(__name__)

TOOL_RUN_LIMIT = 2  # 역할당 기록 툴 호출 상한(호출마다 대화 전체를 다시 보내 비용이 커진다)
ROLES = ("translator", "verifier")


class ArchivePick(BaseModel):
    hit_id: str = Field(description="hit_id of a passage returned by search_company_records")
    spelling: str = Field(description="Latin-script spelling copied letter for letter from that passage")


class ItemM2(Item):
    archive: ArchivePick | None = Field(
        description="For a held proper noun: an earlier passage that refers to the same party; otherwise null"
    )


class AgentOutputM2(BaseModel):
    """Translation of every segment plus one item per ambiguous span or proper noun."""

    translation: list[SegmentTranslation]
    items: list[ItemM2]


class VerifierItemM2(VerifierItem):
    archive: ArchivePick | None = Field(
        description="For a held proper noun: an earlier passage that refers to the same party; otherwise null"
    )


class VerifierOutputM2(BaseModel):
    """One item per personal name, family name and company name. No translation."""

    items: list[VerifierItemM2]


class EngineM2State(TypedDict, total=False):
    doc_id: str
    segments: list[Segment]
    tokens: list[Token]
    records_scope: str | None
    translator_output: dict | None
    verifier_output: dict | None
    t_usage: dict
    v_usage: dict
    t_log: list[dict]
    v_log: list[dict]
    t_errors: list[str]
    v_errors: list[str]
    output: dict | None
    engine: dict


def _invoke(
    model: BaseChatModel,
    system: str,
    user: str,
    tools: list[BaseTool],
    schema: type[BaseModel],
    settings: Settings,
    usage: dict,
    role: str,
    errors: list[str],
) -> dict | None:
    middleware = [ToolCallLimitMiddleware(tool_name=RECORDS_TOOL, run_limit=TOOL_RUN_LIMIT)] if tools else []
    runner = create_agent(
        model, tools=tools, system_prompt=system, response_format=ToolStrategy(schema), middleware=middleware
    )
    res = runner.invoke({"messages": [HumanMessage(user)]}, config={"recursion_limit": settings.recursion_limit})
    for m in res["messages"]:
        if isinstance(m, AIMessage):
            add_usage(usage, m)
    structured = res.get("structured_response")
    if structured is None:
        errors.append(f"{role}: no structured_response")
        return None
    return structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)


def split_picks(items: list[dict]) -> tuple[list[dict], dict[frozenset[int], dict]]:
    """항목에서 `archive`를 떼어 (M1 모양 항목, 토큰 묶음 → 선택)으로 나눈다."""
    plain: list[dict] = []
    picks: dict[frozenset[int], dict] = {}
    for raw in items:
        it = dict(raw)
        pick = it.pop("archive", None)
        if isinstance(pick, dict) and pick.get("hit_id") and strict_key(pick.get("spelling") or ""):
            picks[frozenset(it.get("token_ids") or [])] = {"hit_id": pick["hit_id"], "spelling": pick["spelling"]}
        plain.append(it)
    return plain, picks


def returned_hits(log: list[dict]) -> set[str]:
    return {h for e in log if e.get("tool") == RECORDS_TOOL for h in e.get("hit_ids", [])}


def archive_claims(
    items: list[dict], picks: Mapping[str, dict[frozenset[int], dict]], returned: Mapping[str, set[str]]
) -> list[dict]:
    """중재 뒤 보류인 고유명사마다 역할별 보관함 선택을 모은다. 그 역할의 툴이 돌려준 구절만 받는다.
    같은 철자(엄격 키)는 하나로 묶고 고른 역할을 `by`에 적는다."""
    claims: list[dict] = []
    for it in items:
        if it.get("type") != "proper_noun" or it.get("decision") != "hold":
            continue
        key = frozenset(it.get("token_ids") or [])
        merged: list[dict] = []
        for role in ROLES:
            chosen = picks.get(role, {}).get(key)
            if chosen is None or chosen["hit_id"] not in returned.get(role, set()):
                continue
            same = next((m for m in merged if strict_key(m["spelling"]) == strict_key(chosen["spelling"])), None)
            if same is None:
                merged.append({"spelling": chosen["spelling"].strip(), "hit_ids": [chosen["hit_id"]], "by": [role]})
            else:
                same["by"].append(role)
                if chosen["hit_id"] not in same["hit_ids"]:
                    same["hit_ids"].append(chosen["hit_id"])
        if merged:
            claims.append({"token_ids": list(it.get("token_ids") or []), "picks": merged})
    return claims


def build_engine_m2(
    model: BaseChatModel, settings: Settings, records_factory: RecordsToolFactory | None = None
) -> CompiledStateGraph:
    prompts = m2_system_prompts()

    def _role(state: EngineM2State, role: str, schema: type[BaseModel]) -> tuple[dict | None, dict, list, list]:
        usage, errors, log = _zero(), [], []  # type: ignore[var-annotated]
        user = user_message("C1", state["doc_id"], state["segments"], state["tokens"])
        tools: list[BaseTool] = []
        if records_factory is not None:
            ctx = RecordsContext(state["tokens"], state["segments"], state.get("records_scope"), role, log)
            tools.append(records_factory(ctx))
        output = None
        try:
            output = _invoke(model, prompts[role], user, tools, schema, settings, usage, role, errors)
        except Exception as exc:
            logger.warning("%s M2 %s failed", state["doc_id"], role, exc_info=True)
            errors.append(f"{role}: {type(exc).__name__}: {exc}")
        return output, usage, log, errors

    def translator(state: EngineM2State) -> dict:
        out, usage, log, errors = _role(state, "translator", AgentOutputM2)
        return {"translator_output": out, "t_usage": usage, "t_log": log, "t_errors": errors}

    def verifier(state: EngineM2State) -> dict:
        """번역자 출력은 읽지 않는다(동시에 돌아서 읽을 수도 없다). 읽는 키: doc_id, segments, tokens, records_scope."""
        out, usage, log, errors = _role(state, "verifier", VerifierOutputM2)
        return {"verifier_output": out, "v_usage": usage, "v_log": log, "v_errors": errors}

    def arbiter(state: EngineM2State) -> dict:
        t_log, v_log = state.get("t_log") or [], state.get("v_log") or []
        engine: dict[str, Any] = {
            "translator": state.get("t_usage") or _zero(),
            "verifier": state.get("v_usage") or _zero(),
            "tool_calls": {"translator": len(t_log), "verifier": len(v_log)},
        }
        t, v = state.get("translator_output"), state.get("verifier_output")
        if t is None:
            return {"output": None, "engine": {**engine, "arbiter": None, "archive": []}}
        t_plain, t_picks = split_picks(t.get("items", []))
        v_plain, v_picks = split_picks((v or {}).get("items", []))
        output, stats = arbitrate(
            {**t, "items": t_plain},
            None if v is None else {"items": v_plain},
            state["tokens"],
            state["segments"],
            settings.evidence_rule,
        )
        if v is None:
            stats["verifier_failed"] = True
        claims = archive_claims(
            output["items"],
            {"translator": t_picks, "verifier": v_picks},
            {"translator": returned_hits(t_log), "verifier": returned_hits(v_log)},
        )
        return {"output": output, "engine": {**engine, "arbiter": stats, "archive": claims}}

    builder = StateGraph(EngineM2State)
    builder.add_node("translator", translator)
    builder.add_node("verifier", verifier)
    builder.add_node("arbiter", arbiter)
    builder.add_edge(START, "translator")
    builder.add_edge(START, "verifier")
    builder.add_edge(["translator", "verifier"], "arbiter")
    builder.add_edge("arbiter", END)
    return builder.compile()


def run_engine_m2(engine: CompiledStateGraph, state: Mapping[str, Any], attempts: int, settings: Settings) -> dict:
    """그래프 agent 노드가 M2에서 부른다. 반환 키는 단일 에이전트 노드와 같고 `engine`이 더 있다."""
    usage = dict(state.get("usage", {}))
    final = engine.invoke(
        {
            "doc_id": state["doc_id"],
            "segments": state["segments"],
            "tokens": state["tokens"],
            "records_scope": state.get("records_scope"),
        }
    )
    for part in (final.get("t_usage") or {}, final.get("v_usage") or {}):
        for k, val in part.items():
            usage[k] = usage.get(k, 0) + val
    tool_log = list(state.get("tool_log", [])) + list(final.get("t_log") or []) + list(final.get("v_log") or [])
    new_errors = [f"attempt {attempts}: {e}" for e in (final.get("t_errors") or []) + (final.get("v_errors") or [])]
    return {
        "output": final.get("output"),
        "attempts": attempts,
        "usage": usage,
        "tool_log": tool_log,
        "errors": list(state.get("errors", [])) + new_errors,
        "engine": {**final.get("engine", {}), "condition": "M2", "prompt_version": "p1"},
    }
