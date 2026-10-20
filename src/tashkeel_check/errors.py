"""이 패키지가 의도해서 내는 오류.

호출하는 쪽이 원인별로 다르게 처리할 수 있게 나눈다. CLI는 종료 코드로 바꾸고(`cli.EXIT_CODES`),
단계 1.5 API는 InputError를 400, ConfigError를 503으로 바꾼다. 기존 호출부의 `except ValueError`·
`except RuntimeError`가 그대로 동작하도록 표준 예외도 함께 상속한다.
"""

from __future__ import annotations


class TashkeelError(Exception):
    """이 패키지 오류의 기반."""


class InputError(TashkeelError, ValueError):
    """입력 문서나 조건이 잘못됐다. 요청한 쪽이 고칠 수 있다."""


class ConfigError(TashkeelError, RuntimeError):
    """설정·키·실행 환경이 잘못됐다. 운영하는 쪽이 고친다."""


class AnalyzerUnavailable(ConfigError):
    """CAMeL 분석기를 쓸 수 없다. LLM이나 다른 방법으로 대신 채우지 않는다(ADR-004)."""
