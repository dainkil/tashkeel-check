"""
LangGraph event -> SSE event 변환.

_docs/03_Streaming.md "S1. 3. LangGraph Event Converter 작성"을 그대로 옮겼다.
`agent.py`가 실제 langgraph.prebuilt.create_react_agent로 만든 진짜 에이전트이므로,
여기서 isinstance 검사하는 AIMessageChunk/ToolMessage도 실제
langchain_core.messages의 클래스다 — mock이 아니다.

다음 4가지 SSE event로 변환:
- TokenEvent
- ToolCallStartEvent
- ToolCallEndEvent
- DoneEvent
"""
import json
from typing import AsyncIterator

from langchain_core.messages import AIMessageChunk, ToolMessage

from schemas.stream import (
    DoneEvent,
    StreamEvent,
    ToolCallEndEvent,
    ToolCallStartEvent,
    TokenEvent,
)


async def convert_langgraph_events(
    langgraph_stream: AsyncIterator,
    thread_id: str,
) -> AsyncIterator[StreamEvent]:
    """LangGraph event stream을 SSE event stream으로 변환.

    Args:
        langgraph_stream: agent.astream(...)이 반환한 async iterator
        thread_id: 이번 stream의 thread_id (DoneEvent에 포함)

    Yields:
        StreamEvent 인스턴스
    """
    async for mode, data in langgraph_stream:

        if mode == "messages":
            # LLM token chunk (이 모드에는 ToolMessage도 섞여 나올 수 있어 타입을 반드시 확인한다)
            message_chunk, metadata = data

            if isinstance(message_chunk, AIMessageChunk):
                # Tool call이 시작된 chunk인지 확인
                if message_chunk.tool_call_chunks:
                    for tc_chunk in message_chunk.tool_call_chunks:
                        if tc_chunk.get("name"):
                            # tool_call_chunks의 args는 (아직 조립 중일 수 있는) JSON 문자열이다 —
                            # 실제 스트리밍 중에는 조각난 문자열일 수 있으므로 파싱 실패 시 빈 dict로 대체한다.
                            raw_args = tc_chunk.get("args") or "{}"
                            try:
                                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                            except json.JSONDecodeError:
                                parsed_args = {}
                            yield ToolCallStartEvent(
                                tool_name=tc_chunk["name"],
                                args=parsed_args,
                            )
                # 일반 token (텍스트 content)
                elif message_chunk.content:
                    yield TokenEvent(content=message_chunk.content)

        elif mode == "updates":
            # Node 단위 업데이트 — tool 응답 도착 시 ToolCallEndEvent
            for node_name, node_update in data.items():
                if "messages" in node_update:
                    for msg in node_update["messages"]:
                        if isinstance(msg, ToolMessage):
                            yield ToolCallEndEvent(
                                tool_name=msg.name,
                                result=str(msg.content)[:200],  # preview
                            )

    # 모든 event 처리 완료 후 done event
    yield DoneEvent(thread_id=thread_id)
