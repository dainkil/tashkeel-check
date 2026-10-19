"""여러 모듈이 공유하는 '실제 시스템 부하' 시뮬레이터.

실제 환경이라면 psutil.cpu_percent()나 Prometheus 쿼리처럼 "호출할 때마다 결과가
달라지는 실제 시스템 상태"에 해당한다. naive_resource.py(버그 재현)와
improved_tool.py(개선된 구현)가 이 모듈 하나를 공유해서 동일한 조건에서
비교할 수 있게 한다 (진화관점(12) Wave 2 · 개념맵(11) Ch2 참고).
"""

_tick = 0
_last_value = None


def advance_and_read_load():
    """배경에서 실제 시스템 부하가 한 단계 더 진행됐다고 가정하고 그 값을 읽는다.

    호출할 때마다 값이 달라진다 -- 이것이 모니터링 상태가 "동적 데이터"인 이유다.
    (개념맵(11) Ch2 4번: "결과의 동적성"이 Tool/Resource를 가르는 기준)
    """
    global _tick, _last_value
    _tick += 1
    # 실제라면 psutil.cpu_percent() 같은 실측값이 들어갈 자리.
    # 여기서는 재현 가능하도록 결정적으로(그러나 호출마다 다르게) 값을 변화시킨다.
    _last_value = round(20.0 + (_tick * 13) % 55, 1)
    return _last_value


def peek_last_load():
    """가장 최근에 관측된 실제 부하 값을 부작용 없이 확인한다 (비교 출력용)."""
    return _last_value
