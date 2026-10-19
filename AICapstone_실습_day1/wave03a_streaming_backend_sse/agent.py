"""
실제 langgraph.prebuilt.create_react_agent로 만든 진짜 ReAct 에이전트.

실제 Anthropic/OpenAI API 키가 이 실습 환경에 없어, LLM 자리에만 결정론적
FakeStreamingToolCallingChatModel을 꽂아 넣는다 — 그 외(그래프 컴파일, 도구 실행,
스트리밍, 체크포인터를 통한 thread_id 세션 유지)는 전부 실제 LangGraph/LangChain
코드가 그대로 수행한다. `_docs/01_FastAPI Integration.md`가 실제로 쓰는
`create_agent(model, tools, ...)` 패턴과 동일한 구조다.
"""
import json
from typing import AsyncIterator

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessageChunk, ToolMessage
from langchain_core.outputs import ChatGenerationChunk
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent


class FakeStreamingToolCallingChatModel(BaseChatModel):
    """실제 API 호출 없이 tool-calling ReAct 루프를 재현하는 결정론적 fake 모델.

    실제 langchain_core.language_models.BaseChatModel을 상속하므로
    create_react_agent가 진짜 채팅 모델로 취급하고, 반환하는 것도 진짜
    AIMessageChunk(tool_call_chunks 포함)다 — 이 클래스만 fake이고 나머지
    LangGraph 파이프라인 전체는 실제 코드다.
    """

    tool_name: str = "search_manual"
    tool_args: dict = {}
    final_answer_chunks: list[str] = []

    def bind_tools(self, tools, **kwargs):
        return self

    @property
    def _llm_type(self) -> str:
        return "fake-streaming-tool-calling-chat-model"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise NotImplementedError("이 fake 모델은 스트리밍(_astream) 전용이다.")

    async def _astream(
        self, messages, stop=None, run_manager=None, **kwargs
    ) -> AsyncIterator[ChatGenerationChunk]:
        has_tool_result = any(isinstance(m, ToolMessage) for m in messages)
        if not has_tool_result:
            # 1턴: 도구 호출을 결정 — 실제 tool_call_chunks 형식 그대로 스트리밍
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    tool_call_chunks=[{
                        "name": self.tool_name,
                        "args": json.dumps(self.tool_args, ensure_ascii=False),
                        "id": "call_1",
                        "index": 0,
                    }],
                )
            )
        else:
            # 2턴: 도구 응답을 본 뒤 최종 답변을 토큰 조각으로 스트리밍
            import asyncio
            for piece in self.final_answer_chunks:
                yield ChatGenerationChunk(message=AIMessageChunk(content=piece))
                await asyncio.sleep(0.3)


@tool
def search_manual(query: str) -> str:
    """운영 매뉴얼에서 관련 절차를 검색합니다."""
    return (
        f"'{query}' 관련 런북 3건 검색됨: "
        "db-down.md, replica-failover.md, incident-escalation.md"
    )


def build_agent():
    """실제 create_react_agent로 그래프를 컴파일한다. FastAPI startup에서 1회만 호출."""
    model = FakeStreamingToolCallingChatModel(
        tool_name="search_manual",
        tool_args={"query": "DB 다운 대응"},
        final_answer_chunks=[
            "데이터베이스가 다운되면 ",
            "다음 절차를 따르세요. ",
            "1) 헬스체크 알람을 확인하고, ",
            "2) 최근 배포 이력을 확인해 롤백 여부를 판단하고, ",
            "3) 복제본이 있다면 즉시 failover 하고, ",
            "4) 원인이 파악되면 인시던트 채널에 공유합니다.",
        ],
    )
    return create_react_agent(model=model, tools=[search_manual], checkpointer=MemorySaver())
