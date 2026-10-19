"""Wave 2 개선된 접근 재현 (진화관점(12) Wave 2 · 개념맵(11) Ch2 참고).

원본 문서의 개선된 코드:

    @mcp.tool()                      # 동적 결과 -> Tool
    def get_monitoring_status(system_name: str) -> SystemStatus:
        \"\"\"호출 시점마다 값이 달라지는 조회이므로 Tool로 분류.\"\"\"
        ...

"정적 vs 동적", "URI 식별 가능성"이라는 두 가지 명확한 판단 기준으로 볼 때,
모니터링 상태 조회는 Read-Only이지만 호출 시점마다 결과가 달라지므로 Tool로
분류해야 한다. Tool은 캐싱하지 않고 호출될 때마다 실제 상태를 다시 계산하는 것이
올바른 구현이다.
"""

from shared_load import advance_and_read_load


def get_monitoring_status_tool(system_name: str = "web-01"):
    """[개선] 호출할 때마다 실제 부하를 새로 조회한다 (캐시 없음).

    Tool은 "호출 시점마다 값이 달라지는 동적 행위"를 전제로 하므로, 캐싱하지 않고
    매번 최신 상태를 다시 계산하는 것이 올바른 구현이다.
    """
    cpu = advance_and_read_load()
    return {
        "system_name": system_name,
        "cpu_percent": cpu,
        "status": "ok" if cpu < 45 else "degraded",
    }
