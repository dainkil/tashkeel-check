"""
Wave 3a: 단발성 응답의 벽 — 나이브한 접근

Ch1의 /chat과 동일한 구조: 에이전트가 모든 작업을 마친 후에야 한 번에 응답하는
단발성 request/response 방식. 사용자는 응답이 완성될 때까지 화면에서 아무것도
보지 못한 채 기다려야 한다.

여기서는 실제 LangGraph agent 대신 `await asyncio.sleep(3)`으로 "생각하는 시간"을
흉내낸다 — 처리 속도를 아무리 최적화해도(즉 sleep 시간을 줄여도), 완료 전까지는
아무 진행 상황도 노출되지 않는다는 구조적 한계 자체는 그대로 남는다는 점을 보여주는
것이 이 데모의 목적이다.
"""
import asyncio

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

FAKE_ANSWER = (
    "데이터베이스가 다운되면 다음 절차를 따르세요. "
    "1) 헬스체크 알람을 확인합니다. "
    "2) 최근 배포 이력을 확인해 롤백 여부를 판단합니다. "
    "3) 복제본(replica)이 있다면 즉시 failover 합니다. "
    "4) 원인이 파악되면 인시던트 채널에 공유합니다."
)


class ChatRequest(BaseModel):
    message: str = "데이터베이스 다운 시 대응 절차를 알려주세요"


class ChatResponse(BaseModel):
    message: str


@app.post("/chat")
async def chat(request: ChatRequest | None = None) -> ChatResponse:
    # 실제로는 LangGraph agent.ainvoke(...)가 도구 호출 + 토큰 생성을 모두 마칠 때까지
    # 여기서 대기한다. 이 데모에서는 그 "완료까지 아무것도 안 보이는" 특성만 재현한다.
    await asyncio.sleep(3)
    return ChatResponse(message=FAKE_ANSWER)
