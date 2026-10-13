"""API 키 없이 그래프를 돌리는 가짜 모델(골격 노트북의 연습 모드와 같은 역할).

실제 번역이나 판단을 하지 않는다. 테스트는 responder로 응답을 직접 짠다.
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Callable, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool

Responder = Callable[[list[BaseMessage], list[str]], AIMessage]
OUTPUT_TOOL = "AgentOutput"
ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}


def tool_call(name: str, args: dict) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": args, "id": f"call_{uuid.uuid4().hex[:8]}", "type": "tool_call"}],
        usage_metadata=ZERO_USAGE,
    )


def _human_text(messages: list[BaseMessage]) -> str:
    return next((str(m.content) for m in messages if isinstance(m, HumanMessage)), "")


def practice_responder(messages: list[BaseMessage], bound: list[str]) -> AIMessage:
    """연습 모드 응답. C0는 구간 라벨만 붙인 표시 문장, C1~C3는 최소한의 유효한 구조화 출력."""
    text = _human_text(messages)
    seg_ids = re.findall(r"^\[(s\d+)\]", text, flags=re.M)
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
            try:
                analyzer_rows.extend(json.loads(m.content))
            except (TypeError, ValueError):
                pass
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
        {"translation": [{"segment_id": s, "english": "[practice mode: no LLM call]"} for s in seg_ids], "items": items},
    )


class FakeAgentModel(BaseChatModel):
    responder: Responder | None = None
    bound_tools: list[str] = []
    model_name: str = "fake-agent"

    @property
    def _llm_type(self) -> str:
        return "fake-agent"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        fn = self.responder or practice_responder
        return ChatResult(generations=[ChatGeneration(message=fn(list(messages), list(self.bound_tools)))])

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "FakeAgentModel":
        names = [convert_to_openai_tool(t)["function"]["name"] for t in tools]
        return self.model_copy(update={"bound_tools": names})
