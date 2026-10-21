"""멀티 에이전트 틀(조건 M1, ADR-019): 번역자 → 격리 검증자 → 규칙 중재자.

단일 문서 그래프의 `agent` 노드만 이 하위 그래프로 바뀐다. 나머지 노드·채점·골든 테스트는 그대로다.
- 번역자: C3와 같은 입력(원문·토큰 표·분석기 블록)에 묶음 참고 표기를 더해 `AgentOutput`을 낸다.
- 검증자: 같은 입력만 보고(번역자 출력은 절대 보지 않는다) 고유명사마다 처분을 낸다(`VerifierOutput`). 번역하지 않는다.
- 중재자: LLM이 아니라 규칙 함수. 둘 다 근거 채택이고 철자가 정확히 같고 둘 다 근거 검증을 통과할 때만 확정,
  아니면 보류(사유 코드). 다수결·근거 생성은 없다. 출력은 `AgentOutput` 모양이라 뒤 노드가 그대로 돈다.
다른 서류의 근거 표기는 참고일 뿐이다. `AgentOutput`의 근거는 문서 안 구간이고(스키마 해시 고정), 교차 서류 확정은
`bundle/rules.decide_status`가 한다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypedDict

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, Field

from .analyzer import TokenAnalysis
from .bundle.evidence import strict_form
from .config import Settings
from .prompts import bundle_evidence_block, engine_system_prompts, user_message
from .reconcile import verify_evidence
from .schemas import AgentOutput, CandidateReading, Evidence
from .text import Segment, Token

logger = logging.getLogger(__name__)

ToolFactory = Callable[[list[Token], list[dict]], BaseTool]
HOLD_CODES = (
    "translator_unsupported_adopt",  # 번역자가 proper_noun에 adopt/abstain(근거 없는 확정)을 씀
    "verifier_missing",  # 검증자가 같은 토큰 묶음의 항목을 내지 않음
    "verifier_hold",  # 검증자가 보류
    "spelling_disagree",  # 둘 다 근거 채택이지만 철자가 다름
    "evidence_failed",  # 한쪽이라도 근거 검증 실패
)


class VerifierItem(BaseModel):
    token_ids: list[int] = Field(description="Token ids from the token table; never rewrite Arabic")
    candidates: list[CandidateReading]
    decision: Literal["evidence_adopt", "hold"] = Field(description="evidence_adopt needs evidence; otherwise hold")
    adopted: str | None = Field(description="Latin spelling copied from the evidence, null when holding")
    evidence: Evidence | None
    reason: str


class VerifierOutput(BaseModel):
    """One item per personal name, family name and company name. No translation."""

    items: list[VerifierItem]


class EngineState(TypedDict, total=False):
    doc_id: str
    segments: list[Segment]
    tokens: list[Token]
    analyses: dict[int, TokenAnalysis]
    bundle_evidence: list[dict] | None
    translator_output: dict | None
    verifier_output: dict | None
    output: dict | None
    usage: dict
    tool_log: list[dict]
    errors: list[str]
    engine: dict


def add_usage(usage: dict, msg: AIMessage) -> None:
    meta = getattr(msg, "usage_metadata", None) or {}
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        usage[key] = usage.get(key, 0) + int(meta.get(key, 0) or 0)
    usage["llm_calls"] = usage.get("llm_calls", 0) + 1


def _zero() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "llm_calls": 0}


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
    runner = create_agent(model, tools=tools, system_prompt=system, response_format=ToolStrategy(schema))
    res = runner.invoke({"messages": [HumanMessage(user)]}, config={"recursion_limit": settings.recursion_limit})
    for m in res["messages"]:
        if isinstance(m, AIMessage):
            add_usage(usage, m)
    structured = res.get("structured_response")
    if structured is None:
        errors.append(f"{role}: no structured_response")
        return None
    return structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)


def _candidates_union(*groups: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for group in groups:
        for c in group:
            key = strict_form(c.get("romanized") or "")
            if key and key not in seen:
                seen.add(key)
                out.append(dict(c))
    return out


def _held(item: dict, code: str, candidates: list[dict]) -> dict:
    reason = item.get("reason") or ""
    return {
        **item,
        "decision": "hold",
        "adopted": None,
        "confidence": None,
        "evidence": None,
        "candidates": candidates,
        "reason": f"arbiter:{code}; translator: {reason}" if reason else f"arbiter:{code}",
    }


def _rewrite_translation(translation: list[dict], tokens: list[Token], held: list[tuple[dict, str | None]]) -> int:
    """보류로 바뀐 이름이 번역문에 채택 철자 그대로 있으면 [c1/c2]로 고쳐 쓴다(C1 규칙 5). 바꾼 수를 돌려준다."""
    seg_of = {t["id"]: t["segment_id"] for t in tokens}
    n = 0
    for item, adopted in held:
        if not adopted:
            continue
        bracket = "[" + "/".join(c["romanized"] for c in item["candidates"]) + "]"
        segs = {seg_of.get(i) for i in item["token_ids"]}
        for row in translation:
            if row.get("segment_id") in segs and adopted in (row.get("english") or ""):
                row["english"] = row["english"].replace(adopted, bracket)
                n += 1
    return n


def arbitrate(
    translator: dict, verifier: dict | None, tokens: list[Token], segments: list[Segment], evidence_rule: str
) -> tuple[dict, dict]:
    """규칙 중재. (AgentOutput 모양의 출력, 통계)."""
    seg_text = {s["segment_id"]: s["text"] for s in segments}
    v_items = {frozenset(it["token_ids"]): it for it in (verifier or {}).get("items", [])}
    matched: set[frozenset[int]] = set()
    stats: dict[str, Any] = {
        "n_translator_items": 0,
        "n_verifier_items": len(v_items),
        "n_agreed_confirmed": 0,
        "n_held_by_arbiter": 0,
        "by_code": dict.fromkeys(HOLD_CODES, 0),
        "n_verifier_only": 0,
        "n_translation_rewritten": 0,
    }
    out_items: list[dict] = []
    held: list[tuple[dict, str | None]] = []
    for item in translator.get("items", []):
        if item.get("type") != "proper_noun":
            out_items.append(dict(item))
            continue
        stats["n_translator_items"] += 1
        key = frozenset(item.get("token_ids", []))
        v = v_items.get(key)
        if v is not None:
            matched.add(key)
        cands = _candidates_union(item.get("candidates", []), (v or {}).get("candidates", []))
        code = None
        if item.get("decision") != "evidence_adopt":
            if item.get("decision") == "hold":
                out_items.append({**item, "candidates": cands})
                continue
            code = "translator_unsupported_adopt"
        elif v is None:
            code = "verifier_missing"
        elif v.get("decision") != "evidence_adopt":
            code = "verifier_hold"
        elif strict_form(item.get("adopted") or "") != strict_form(v.get("adopted") or ""):
            code = "spelling_disagree"
        elif (
            not verify_evidence(item, seg_text, evidence_rule)[0] or not verify_evidence(v, seg_text, evidence_rule)[0]
        ):
            code = "evidence_failed"
        if code is None:
            stats["n_agreed_confirmed"] += 1
            out_items.append({**item, "candidates": cands})
            continue
        stats["n_held_by_arbiter"] += 1
        stats["by_code"][code] += 1
        new = _held(item, code, cands)
        out_items.append(new)
        held.append((new, item.get("adopted")))
    for key, v in v_items.items():
        if key in matched:
            continue
        stats["n_verifier_only"] += 1
        out_items.append(
            {
                "token_ids": sorted(key),
                "type": "proper_noun",
                "candidates": _candidates_union(v.get("candidates", [])),
                "decision": "hold",
                "adopted": None,
                "reason": f"arbiter:verifier_only; verifier: {v.get('reason', '')}",
                "confidence": None,
                "evidence": None,
            }
        )
    translation = [dict(r) for r in translator.get("translation", [])]
    stats["n_translation_rewritten"] = _rewrite_translation(translation, tokens, held)
    return {"translation": translation, "items": out_items}, stats


def build_engine(
    model: BaseChatModel, settings: Settings, extra_tool_factories: list[ToolFactory] | None = None
) -> CompiledStateGraph:
    factories = extra_tool_factories or []
    prompts = engine_system_prompts(settings.prompt_version)

    def _common(state: EngineState) -> tuple[str, list[BaseTool]]:
        user = user_message(
            "C3", state["doc_id"], state["segments"], state["tokens"], state["analyses"], settings.max_candidates
        )
        rows = state.get("bundle_evidence") or []
        if rows:
            user += "\n\n" + bundle_evidence_block(rows)
        tools = [factory(state["tokens"], state["tool_log"]) for factory in factories]
        return user, tools

    def translator(state: EngineState) -> dict:
        usage, errors = dict(state.get("usage") or _zero()), list(state.get("errors", []))
        part = _zero()
        system = prompts["translator"] + (prompts["bundle_line"] if state.get("bundle_evidence") else "")
        user, tools = _common(state)
        output = None
        try:
            output = _invoke(model, system, user, tools, AgentOutput, settings, part, "translator", errors)
        except Exception as exc:
            logger.warning("%s M1 translator failed", state["doc_id"], exc_info=True)
            errors.append(f"translator: {type(exc).__name__}: {exc}")
        for k, v in part.items():
            usage[k] = usage.get(k, 0) + v
        engine = {**state.get("engine", {}), "translator": part}
        return {"translator_output": output, "usage": usage, "errors": errors, "engine": engine}

    def verifier(state: EngineState) -> dict:
        """번역자 출력은 읽지 않는다. 읽는 키: doc_id, segments, tokens, analyses, bundle_evidence."""
        usage, errors = dict(state.get("usage") or _zero()), list(state.get("errors", []))
        part = _zero()
        output = None
        if state.get("translator_output") is not None:  # 번역자가 실패했으면 호출을 아낀다(재시도가 둘 다 다시 돈다)
            system = prompts["verifier"] + (prompts["bundle_line"] if state.get("bundle_evidence") else "")
            user, tools = _common(state)
            try:
                output = _invoke(model, system, user, tools, VerifierOutput, settings, part, "verifier", errors)
            except Exception as exc:
                logger.warning("%s M1 verifier failed", state["doc_id"], exc_info=True)
                errors.append(f"verifier: {type(exc).__name__}: {exc}")
        for k, v in part.items():
            usage[k] = usage.get(k, 0) + v
        engine = {**state.get("engine", {}), "verifier": part}
        return {"verifier_output": output, "usage": usage, "errors": errors, "engine": engine}

    def arbiter(state: EngineState) -> dict:
        t = state.get("translator_output")
        if t is None:
            return {"output": None, "engine": {**state.get("engine", {}), "arbiter": None}}
        output, stats = arbitrate(
            t, state.get("verifier_output"), state["tokens"], state["segments"], settings.evidence_rule
        )
        if state.get("verifier_output") is None:
            stats["verifier_failed"] = True
        return {"output": output, "engine": {**state.get("engine", {}), "arbiter": stats}}

    builder = StateGraph(EngineState)
    builder.add_node("translator", translator)
    builder.add_node("verifier", verifier)
    builder.add_node("arbiter", arbiter)
    builder.add_edge(START, "translator")
    builder.add_edge("translator", "verifier")
    builder.add_edge("verifier", "arbiter")
    builder.add_edge("arbiter", END)
    return builder.compile()


def run_engine(engine: CompiledStateGraph, state: Mapping[str, Any], attempts: int, settings: Settings) -> dict:
    """그래프 agent 노드가 M1에서 부른다. 반환 키는 단일 에이전트 노드와 같고 `engine`이 더 있다."""
    usage = dict(state.get("usage", {}))
    tool_log = list(state.get("tool_log", []))
    errors = list(state.get("errors", []))
    before = len(errors)
    final = engine.invoke(
        {
            "doc_id": state["doc_id"],
            "segments": state["segments"],
            "tokens": state["tokens"],
            "analyses": state["analyses"],
            "bundle_evidence": state.get("bundle_evidence"),
            "usage": usage,
            "tool_log": tool_log,
            "errors": errors,
            "engine": {},
        }
    )
    new_errors = [f"attempt {attempts}: {e}" for e in final.get("errors", [])[before:]]
    engine_stats = {**final.get("engine", {}), "prompt_version": settings.prompt_version}
    return {
        "output": final.get("output"),
        "attempts": attempts,
        "usage": final.get("usage", usage),
        "tool_log": final.get("tool_log", tool_log),
        "errors": errors[:before] + new_errors,
        "engine": engine_stats,
    }
