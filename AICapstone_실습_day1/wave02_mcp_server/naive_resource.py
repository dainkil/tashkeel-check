"""Wave 2 나이브한 접근 재현 (진화관점(12) Wave 2 · 개념맵(11) Ch2 참고).

원본 문서의 버그 코드:

    # 나이브: 모니터링 상태 조회를 Read-Only이므로 Resource처럼 다루려는 시도
    @mcp.resource("monitoring://status/{system_name}")
    def get_monitoring_status(system_name: str) -> str:
        # 문제: 호출 시점마다 CPU/메모리 값이 달라지는데 Resource는 정적 문서를 전제로 한다
        ...

"조회 기능이니 정적 데이터처럼 다뤄도 되지 않을까"라는 직관으로, 모니터링 상태를
Resource(= URI로 식별 가능한 정적 문서)처럼 다룬다. Resource는 "한 번 만들어지면
바뀌지 않는 문서"를 전제로 하므로, 이 전제를 그대로 코드로 옮기면 "최초 조회 시
캐싱하고 그 다음부터는 캐시를 반환"하는 구현이 된다. 이 캐싱 자체가 버그다 --
모니터링 상태는 실제로는 매 순간 바뀌는 동적 데이터이기 때문이다.
"""

from shared_load import advance_and_read_load

# 모듈 레벨 캐시. Resource가 "정적 문서"라는 (잘못된) 전제를 코드로 표현한 것이다.
_cached_status = None


def get_monitoring_status_resource(system_name: str = "web-01"):
    """[나이브/버그] 최초 호출 시에만 실제 부하를 조회해 캐시하고, 이후 호출은
    캐시된 값을 그대로 반환한다.

    Resource는 URI로 식별되는 정적 문서를 전제로 하므로 "한 번 계산해서 캐싱"하는
    것이 Resource답게 구현한 것처럼 보이지만, 모니터링 상태는 시점마다 값이 달라지는
    동적 데이터라서 이 캐싱이 그대로 버그가 된다 -- 실제 부하는 매 호출 흘러가는데
    반환값은 최초 호출 시점에 멈춰 있다.
    """
    global _cached_status
    if _cached_status is None:
        cpu = advance_and_read_load()
        _cached_status = {
            "system_name": system_name,
            "cpu_percent": cpu,
            "status": "ok" if cpu < 45 else "degraded",
        }
    return _cached_status
