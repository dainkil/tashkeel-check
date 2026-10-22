"""API 키 없이 그래프를 돌리는 가짜 모델(골격 노트북의 연습 모드와 같은 역할).

실제 번역이나 판단을 하지 않는다. 테스트는 responder로 응답을 직접 짠다.
"""

from __future__ import annotations

import contextlib
import json
import re
import uuid
from collections.abc import Callable, Sequence
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool

Responder = Callable[[list[BaseMessage], list[str]], AIMessage]
OUTPUT_TOOL = "AgentOutput"
VERIFIER_TOOL = "VerifierOutput"  # M1 검증자(ADR-019)
OUTPUT_TOOL_M2 = "AgentOutputM2"  # M2 번역자·검증자(ADR-022)
VERIFIER_TOOL_M2 = "VerifierOutputM2"
RECORDS_TOOL = "search_company_records"  # mcp.records.RECORDS_TOOL과 같다
ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def tool_call(name: str, args: dict) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}", "type": "tool_call"}],
        usage_metadata=ZERO_USAGE,
    )


def _human_text(messages: list[BaseMessage]) -> str:
    return next((str(m.content) for m in messages if isinstance(m, HumanMessage)), "")


# 연습 모드 M2가 보관함 영문 후보를 고를 때 쓰는 거친 첫 자음 대응. 실제 판단이 아니다(LLM 없음)
_AR_INITIAL = {
    "ا": "aeiou", "أ": "aeiou", "إ": "ei", "آ": "a", "ب": "b", "ت": "t", "ث": "t", "ج": "jg", "ح": "h", "خ": "k",
    "د": "d", "ذ": "dz", "ر": "r", "ز": "z", "س": "s", "ش": "s", "ص": "s", "ض": "d", "ط": "t", "ظ": "dz",
    "ع": "aeiou", "غ": "g", "ف": "f", "ق": "qgk", "ك": "k", "ل": "l", "م": "m", "ن": "n", "ه": "h", "و": "wou",
    "ي": "yie",
}  # fmt: skip


def _initial_match(arabic: str, spans: list[str]) -> str | None:
    """한 단어 아랍어와 첫 자음이 맞는 라틴 단어(정관사 al-/el-은 서로 맞춰 뗀다)."""
    word = arabic.strip()
    article = word.startswith("ال") and len(word) > 2
    core = word[2:] if article else word
    allowed = _AR_INITIAL.get(core[:1], "")
    for span in spans:
        if article:  # Al-Harbi, Al Rayyan, El Kaabi
            for m in re.finditer(r"\b(?:al|el)[-\s]?([A-Za-z'’]+)", span, flags=re.I):
                if m.group(1)[:1].lower() in allowed:
                    return m.group(0)
            continue
        for w in span.split():
            if w[:1].lower() in allowed:
                return w
    return None


def _practice_m2(messages: list[BaseMessage], bound: list[str], text: str, seg_ids: list[str]) -> AIMessage:
    """연습 모드 M2. 아랍어 토큰을 하나씩 회사 기록에서 찾고, 사전 표기나 보관함 후보가 있는 것만 보류 항목으로 낸다."""
    tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
    if RECORDS_TOOL in bound and not tool_msgs:
        table = re.findall(r"(\d+)=(\S+)", text.split("TOKENS", 1)[-1])
        names = [[int(i)] for i, w in table if len(w) >= 3][:40]
        if names:
            return tool_call(RECORDS_TOOL, {"names": names})
    rows: list[dict] = []
    for m in tool_msgs:
        with contextlib.suppress(TypeError, ValueError):
            loaded = json.loads(str(m.content))
            if isinstance(loaded, list):
                rows.extend(r for r in loaded if isinstance(r, dict))
    items = []
    for r in rows:
        spelling, pick = None, None
        if r.get("dictionary"):
            spelling = r["dictionary"].get("english")
        else:
            for h in r.get("hits", []):
                word = _initial_match(str(r.get("arabic", "")), list(h.get("latin_candidates", [])))
                if word:
                    spelling, pick = word, {"hit_id": h["hit_id"], "spelling": word}
                    break
        if not spelling or not r.get("token_ids"):
            continue
        items.append(
            {
                "token_ids": list(r["token_ids"]),
                "candidates": [{"reading": None, "romanized": spelling, "source": "llm"}],
                "decision": "hold",
                "adopted": None,
                "evidence": None,
                "reason": "practice mode: found in company records",
                "archive": pick,
            }
        )
    if VERIFIER_TOOL_M2 in bound:
        return tool_call(VERIFIER_TOOL_M2, {"items": items})
    full = [{**it, "type": "proper_noun", "confidence": None} for it in items]
    return tool_call(
        OUTPUT_TOOL_M2,
        {
            "translation": [{"segment_id": s, "english": "[practice mode: no LLM call]"} for s in seg_ids],
            "items": full,
        },
    )


def practice_responder(messages: list[BaseMessage], bound: list[str]) -> AIMessage:
    """연습 모드 응답. C0는 구간 라벨만 붙인 표시 문장, C1~C3는 최소한의 유효한 구조화 출력."""
    text = _human_text(messages)
    seg_ids = re.findall(r"^\[(s\d+)\]", text, flags=re.M)
    if OUTPUT_TOOL_M2 in bound or VERIFIER_TOOL_M2 in bound:
        return _practice_m2(messages, bound, text, seg_ids)
    if VERIFIER_TOOL in bound:  # M1 검증자: 분석기가 모르는 토큰을 보류 항목으로
        rows = [json.loads(ln) for ln in text.split("ANALYZER", 1)[-1].splitlines() if ln.startswith("{")]
        items = [
            {
                "token_ids": [r["token_id"]],
                "candidates": [{"reading": None, "romanized": "?", "source": "llm"}],
                "decision": "hold",
                "adopted": None,
                "evidence": None,
                "reason": "practice mode: unknown to analyzer",
            }
            for r in rows
            if r.get("analysis_count") == 0
        ]
        return tool_call(VERIFIER_TOOL, {"items": items})
    if OUTPUT_TOOL not in bound:
        return AIMessage(
            content="\n".join(f"[{s}] [practice mode: no LLM call]" for s in seg_ids), usage_metadata=ZERO_USAGE
        )
    analyzer_rows: list[dict] = []
    if "analyze_tokens" in bound and not any(isinstance(m, ToolMessage) for m in messages):
        ids = [int(x) for x in re.findall(r"(\d+)=", text.split("TOKENS", 1)[-1])][:5]
        return tool_call("analyze_tokens", {"token_ids": ids})
    for m in messages:
        if isinstance(m, ToolMessage):
            with contextlib.suppress(TypeError, ValueError):
                analyzer_rows.extend(json.loads(str(m.content)))
    if "ANALYZER" in text:
        for line in text.split("ANALYZER", 1)[1].splitlines():
            if line.startswith("{"):
                analyzer_rows.append(json.loads(line))
    items = [
        {
            "token_ids": [r["token_id"]],
            "type": "proper_noun",
            "candidates": [{"reading": None, "romanized": "?", "source": "llm"}],
            "decision": "hold",
            "adopted": None,
            "reason": "practice mode: unknown to analyzer",
            "confidence": None,
            "evidence": None,
        }
        for r in analyzer_rows
        if r.get("analysis_count") == 0
    ]
    return tool_call(
        OUTPUT_TOOL,
        {
            "translation": [{"segment_id": s, "english": "[practice mode: no LLM call]"} for s in seg_ids],
            "items": items,
        },
    )


class FakeAgentModel(BaseChatModel):
    responder: Responder | None = None
    bound_tools: list[str] = []
    model_name: str = "fake-agent"

    @property
    def _llm_type(self) -> str:
        return "fake-agent"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any
    ) -> ChatResult:
        fn = self.responder or practice_responder
        return ChatResult(generations=[ChatGeneration(message=fn(list(messages), list(self.bound_tools)))])

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> FakeAgentModel:
        names = [convert_to_openai_tool(t)["function"]["name"] for t in tools]
        return self.model_copy(update={"bound_tools": names})
