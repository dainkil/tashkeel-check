"""
StubAgent — 실제 LLM/MCP 호출 없이 "에이전트 생성 비용"만 흉내 내는 스텁.

Wave 1(교두보 확보)의 실제 코드에서 build_agent()는
ChatOpenAI + MultiServerMCPClient(subprocess) + MemorySaver를 묶는
무거운 초기화 작업이다. 이 실습에서는 그 무거움을 재현하는 대신,
"생성될 때마다 카운트가 올라가고, 생성될 때마다 새로운 객체가 된다"는
핵심 성질만 남긴 스텁으로 대체한다.
"""

# 모듈 전역 카운터: StubAgent()가 몇 번 만들어졌는지 기록한다.
# naive_app.py에서는 요청마다 늘어나고, improved_app.py에서는 서버 시작 시 1번만 늘어난다.
CREATION_COUNT = 0


class StubAgent:
    """실제 build_agent()를 대신하는 가짜 에이전트.

    생성자가 호출될 때마다:
    1. 모듈 전역 CREATION_COUNT를 1 증가시킨다 (= MCP subprocess가 새로 뜬 횟수라고 가정).
    2. self.instance_id에 파이썬 객체의 id()를 저장한다 (= 같은 객체인지 다른 객체인지 구분하는 지표).
    """

    def __init__(self) -> None:
        global CREATION_COUNT
        CREATION_COUNT += 1
        self.instance_id = id(self)

    async def ainvoke(self, message: str) -> str:
        # 실제로는 LLM 호출 + MCP tool 호출이 일어나는 자리지만,
        # 이 실습에서는 외부 API를 호출하지 않고 고정 문자열만 반환한다.
        return f"(stub) '{message}'에 대한 응답 (instance_id={self.instance_id})"
