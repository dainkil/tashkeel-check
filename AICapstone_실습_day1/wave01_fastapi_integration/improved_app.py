"""
개선된 접근: FastAPI lifespan으로 서버 시작 시 agent를 1회만 생성하는 싱글턴 패턴.

진화관점(12) Wave 1의 "개선된 접근" 코드를 그대로 재현한다.
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.agent = await build_agent()   # 서버 시작 시 1회만 생성
        yield

    app = FastAPI(lifespan=lifespan)

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        result = await app.state.agent.ainvoke(...)
        ...
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from stub_agent import StubAgent
import stub_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 서버가 시작될 때 딱 한 번만 StubAgent()를 생성해 app.state에 저장한다.
    app.state.agent = StubAgent()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/chat")
async def chat():
    # 요청마다 새로 만들지 않고, lifespan에서 만들어 둔 agent를 재사용한다.
    agent = app.state.agent
    return {
        "instance_id": agent.instance_id,
        "creation_count": stub_agent.CREATION_COUNT,
    }
