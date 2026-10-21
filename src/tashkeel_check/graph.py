"""LangGraph 그래프: load → analyze → agent → validate →(재시도 1회)→ reconcile → export.

분석기(analyze)는 모든 조건에서 돈다. 조건은 agent 노드에서 LLM에게 무엇을 보여 주는지만 바꾼다.
LLM이 필요 없는 검사와 집계는 일반 함수 노드다.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, TypedDict

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from .analyzer import AnalyzeFn, TokenAnalysis, analyze_tokens
from .config import CONDITIONS, Settings
from .errors import InputError
from .export import write_outputs
from .prompts import system_prompt, user_message
from .reconcile import parse_c0, reconcile
from .results import ReviewResult
from .schemas import AgentOutput
from .text import Segment, Token, nfc, tokenize
from .tools import make_analyze_tool

logger = logging.getLogger(__name__)

ToolFactory = Callable[[list[Token], list[dict]], BaseTool]
# C2의 analyze_tokens 툴을 바꿔 끼울 때(단계 1.5 MCP 경로). (tokens, analyses, tool_log, max_candidates) → 툴
AnalyzeToolFactory = Callable[[list[Token], dict[int, TokenAnalysis], list[dict], int], BaseTool]


class GraphState(TypedDict, total=False):
    doc_id: str
    condition: str
    segments: list[Segment]
    gold: dict | None
    out_dir: str | None
    meta: dict
    tokens: list[Token]
    analyses: dict[int, TokenAnalysis]
    output: Any
    tool_log: list[dict]
    usage: dict
    attempts: int
    errors: list[str]
    valid: bool
    reconciled: dict  # reconcile 노드의 결과(검증 전)
    result: ReviewResult  # export 노드가 검증한 최종 결과


def _add_usage(usage: dict, msg: AIMessage) -> None:
    meta = getattr(msg, "usage_metadata", None) or {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        usage[key] = usage.get(key, 0) + int(meta.get(key, 0) or 0)
    usage["llm_calls"] = usage.get("llm_calls", 0) + 1


def build_graph(
    model: BaseChatModel,
    settings: Settings,
    analyze_fn: AnalyzeFn | None = None,
    extra_tool_factories: list[ToolFactory] | None = None,
    analyze_tool_factory: AnalyzeToolFactory | None = None,
) -> CompiledStateGraph:
    extra_tool_factories = extra_tool_factories or []
    analyze_factory: AnalyzeToolFactory = analyze_tool_factory or make_analyze_tool

    def load(state: GraphState) -> dict:
        if state["condition"] not in CONDITIONS:
            raise InputError(f"unknown condition {state['condition']!r}")
        segments = [Segment(segment_id=s["segment_id"], text=nfc(s["text"])) for s in state["segments"]]
        if not segments:
            raise InputError("document has no segments")
        meta = {**state.get("meta", {}), "started_at_epoch": time.time()}
        return {
            "segments": segments,
            "tokens": tokenize(segments),
            "meta": meta,
            "attempts": 0,
            "errors": [],
            "tool_log": [],
            "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "llm_calls": 0},
        }

    def analyze(state: GraphState) -> dict:
        return {"analyses": analyze_tokens(state["tokens"], analyze_fn)}

    def agent(state: GraphState) -> dict:
        condition = state["condition"]
        attempts = state.get("attempts", 0) + 1
        usage = dict(state.get("usage", {}))
        tool_log = list(state.get("tool_log", []))
        errors = list(state.get("errors", []))
        system = system_prompt(condition, settings.prompt_version)
        user = user_message(
            condition, state["doc_id"], state["segments"], state["tokens"], state["analyses"], settings.max_candidates
        )
        output: Any = None
        try:
            if condition == "C0":
                chain = ChatPromptTemplate.from_messages([SystemMessage(system), ("human", "{document}")]) | model
                msg = chain.invoke({"document": user})
                _add_usage(usage, msg)
                output = msg.content if isinstance(msg.content, str) else str(msg.content)
            else:
                tools: list[BaseTool] = []
                if condition == "C2":
                    tools.append(analyze_factory(state["tokens"], state["analyses"], tool_log, settings.max_candidates))
                tools.extend(factory(state["tokens"], tool_log) for factory in extra_tool_factories)
                runner = create_agent(
                    model, tools=tools, system_prompt=system, response_format=ToolStrategy(AgentOutput)
                )
                res = runner.invoke(
                    {"messages": [HumanMessage(user)]}, config={"recursion_limit": settings.recursion_limit}
                )
                for m in res["messages"]:
                    if isinstance(m, AIMessage):
                        _add_usage(usage, m)
                structured = res.get("structured_response")
                if structured is None:
                    errors.append(f"attempt {attempts}: no structured_response")
                else:
                    output = structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)
        except Exception as exc:  # API 오류와 형식 오류를 기록하고 validate가 재시도를 정한다
            logger.warning("%s %s attempt %d failed", state["doc_id"], condition, attempts, exc_info=True)
            errors.append(f"attempt {attempts}: {type(exc).__name__}: {exc}")
        return {"output": output, "attempts": attempts, "usage": usage, "tool_log": tool_log, "errors": errors}

    def validate(state: GraphState) -> dict:
        seg_ids = [s["segment_id"] for s in state["segments"]]
        out = state.get("output")
        errors = list(state.get("errors", []))
        if out is None:
            ok = False
        elif state["condition"] == "C0":
            parsed = parse_c0(out)
            missing = [s for s in seg_ids if s not in parsed]
            ok = not missing
            if missing:
                errors.append(f"attempt {state['attempts']}: segments missing in translation: {missing}")
        else:
            got = {t["segment_id"] for t in out.get("translation", [])}
            missing = [s for s in seg_ids if s not in got]
            ok = not missing
            if missing:
                errors.append(f"attempt {state['attempts']}: segments missing in translation: {missing}")
        return {"valid": ok, "errors": errors}

    def route(state: GraphState) -> str:
        if state["valid"]:
            return "reconcile"
        return "agent" if state["attempts"] <= settings.max_retries else "reconcile"

    def reconcile_node(state: GraphState) -> dict:
        result = reconcile(
            state["condition"],
            state["segments"],
            state["tokens"],
            state["analyses"],
            state.get("output"),
            gold=state.get("gold"),
            tool_log=state.get("tool_log"),
            high_conf=settings.high_confidence,
            evidence_rule=settings.evidence_rule,
        )
        result["metrics"].update(
            {
                "usage": state.get("usage", {}),
                "attempts": state.get("attempts", 0),
                "valid_output": bool(state.get("valid")),
                "errors": state.get("errors", []),
                "n_tokens": len(state["tokens"]),
                "n_arabic_tokens": len(state["analyses"]),
            }
        )
        result["doc_id"] = state["doc_id"]
        return {"reconciled": result}

    def export(state: GraphState) -> dict:
        meta = dict(state.get("meta", {}))
        meta["elapsed_s"] = round(time.time() - meta.pop("started_at_epoch", time.time()), 3)
        meta["attempts"] = state.get("attempts", 0)
        meta["usage"] = state.get("usage", {})
        meta["tool_calls"] = len(state.get("tool_log", []))
        result = ReviewResult.model_validate({**state["reconciled"], "meta": meta})
        out_dir = state.get("out_dir")
        if out_dir:
            write_outputs(out_dir, result)
        return {"result": result, "meta": meta}

    builder = StateGraph(GraphState)
    for name, fn in [
        ("load", load),
        ("analyze", analyze),
        ("agent", agent),
        ("validate", validate),
        ("reconcile", reconcile_node),
        ("export", export),
    ]:
        builder.add_node(name, fn)
    builder.add_edge(START, "load")
    builder.add_edge("load", "analyze")
    builder.add_edge("analyze", "agent")
    builder.add_edge("agent", "validate")
    builder.add_conditional_edges("validate", route, {"agent": "agent", "reconcile": "reconcile"})
    builder.add_edge("reconcile", "export")
    builder.add_edge("export", END)
    return builder.compile()
