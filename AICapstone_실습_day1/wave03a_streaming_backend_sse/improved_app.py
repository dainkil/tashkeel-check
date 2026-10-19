"""
Wave 3a: 단발성 응답의 벽 — 개선된 접근 (Backend SSE 파이프라인, 실제 LangGraph agent 포함판)

_docs/03_Streaming.md "S1. Backend SSE Endpoint 구현"의 4단계를 실제로 4개 파일로
분리해 반영한다:
  1. schemas/stream.py         — Event Schema
  2. streaming/sse_formatter.py — SSE Formatter
  3. streaming/event_converter.py — LangGraph Event Converter (실제 AIMessageChunk/ToolMessage 사용)
  4. 이 파일                    — FastAPI SSE Endpoint (agent.astream → Converter → Formatter)

`agent.py`가 실제 langgraph.prebuilt.create_react_agent로 만든 진짜 ReAct 에이전트를
반환한다 — 실제 LLM API 키가 없어 그 자리에만 결정론적 fake 모델을 꽂았을 뿐,
그래프 컴파일·도구 실행·스트리밍·체크포인터는 전부 실제 LangGraph/LangChain 코드다.
Wave 1(FastAPI Integration)의 교훈대로 agent는 `lifespan`에서 1회만 생성한다.
"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agent import build_agent
from streaming.event_converter import convert_langgraph_events
from streaming.sse_formatter import format_sse


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = build_agent()  # Wave 1의 교훈: 요청마다 재생성하지 않고 1회만 생성
    yield


app = FastAPI(lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = "데이터베이스 다운 시 대응 절차를 알려주세요"
    thread_id: str | None = None


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest | None = None) -> StreamingResponse:
    """4단계가 실제로 연결되는 지점: 실제 LangGraph agent.astream → Event Converter → SSE Formatter."""
    req = request or ChatRequest()
    thread_id = req.thread_id or str(uuid.uuid4())

    async def event_generator():
        langgraph_stream = app.state.agent.astream(
            {"messages": [{"role": "user", "content": req.message}]},
            config={"configurable": {"thread_id": thread_id}},
            stream_mode=["messages", "updates"],
        )
        async for event in convert_langgraph_events(langgraph_stream, thread_id):
            yield format_sse(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            # 프록시/로드밸런서가 응답을 버퍼링해 스트리밍 효과가 사라지는 것을 방지한다.
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
