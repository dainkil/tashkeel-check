"""
나이브한 접근: 매 요청마다 agent를 새로 만든다.

진화관점(12) Wave 1의 "나이브한 접근" 코드를 그대로 재현한다.
    @app.post("/chat")
    async def chat(request: ChatRequest):
        agent = await build_agent()   # 요청마다 MCP subprocess를 새로 기동 — 비효율
        ...

실제로는 build_agent()가 MCP 서버 subprocess를 새로 띄우는 무거운 작업이지만,
여기서는 StubAgent() 생성으로 그 "매번 새로 만든다"는 문제만 재현한다.
"""

from fastapi import FastAPI

from stub_agent import StubAgent
import stub_agent

app = FastAPI()


@app.post("/chat")
async def chat():
    # 문제 지점: 요청이 들어올 때마다 StubAgent()를 새로 생성한다.
    # 실제 코드라면 이 줄에서 MCP subprocess가 매번 새로 기동된다.
    agent = StubAgent()
    return {
        "instance_id": agent.instance_id,
        "creation_count": stub_agent.CREATION_COUNT,
    }
