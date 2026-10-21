"""설정. 골격 노트북처럼 .env를 읽고, LangSmith 키가 없으면 추적만 끈다.

`Settings()`는 기본값만 쓰고 환경 변수를 읽지 않는다. 그래야 테스트가 실행 순서와 무관하게 같은 값을 본다.
환경 변수와 .env는 `load_settings()`만 읽고, 환경 변수 이름은 필드 이름을 대문자로 쓴 것이다(예: MODEL).
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import ConfigError

CONDITIONS = ("C0", "C1", "C2", "C3")


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    model: str = "openai:gpt-6.1-sol"
    temperature: float | None = Field(None, ge=0, le=2)  # 모델이 지원하면 .env에서 0으로 둔다
    max_retries: int = Field(1, ge=0)  # validate → agent 재시도 상한(앱 업무 재시도, LLM 클라이언트 재시도와 별개)
    recursion_limit: int = Field(25, ge=1)  # create_agent 내부 tool loop의 super-step 상한
    # EXP-001 판단 기준: M5(방언 허용)가 이보다 낮으면 분석기를 이름 근거로 쓰지 않는다
    coverage_threshold: float = Field(0.5, ge=0, le=1)
    high_confidence: float = Field(0.8, ge=0, le=1)  # 근거 없이 이 확신도 이상으로 확정하면 "고확신 무근거 확정"
    dev_docs: int = Field(10, ge=1)
    eval_docs: int = Field(30, ge=1)
    repeats: int = Field(3, ge=1)
    max_candidates: int = Field(10, ge=1)  # 토큰당 LLM에게 보여 줄 분석기 후보 수 상한
    # 달러/100만 토큰. 둘 다 있으면 exp002 진행 로그와 exp002-status에 추정 금액을 같이 보인다(청구 기준 아님)
    price_input_per_mtok: float | None = Field(None, ge=0)
    price_output_per_mtok: float | None = Field(None, ge=0)
    enable_bundle_search: bool = False  # 단계 2 틀(ADR-007). 단계 1 조건 C0~C3에서는 쓰지 않는다
    embedding_model: str = "text-embedding-3-small"
    langsmith_project: str = "tashkeel-check"
    data_dir: Path = Path("data")  # 상대 경로는 작업 디렉터리 기준. 컨테이너에서는 DATA_DIR로 준다
    results_dir: Path = Path("results")


def load_settings(env_file: str | Path | None = None) -> Settings:
    """환경 변수와 .env에서 설정을 읽는다. .env는 작업 디렉터리에서 위로 찾고, 이미 있는 환경 변수가 우선이다.

    빈 값은 설정하지 않은 것으로 본다. 값이 잘못되면 ConfigError를 낸다.
    """
    path = env_file or find_dotenv(usecwd=True)
    if path:
        load_dotenv(path, override=False)
    values = {name: raw for name in Settings.model_fields if (raw := os.getenv(name.upper(), "").strip())}
    try:
        return Settings.model_validate(values)
    except ValidationError as exc:
        raise ConfigError(f"설정 값이 잘못됐습니다.\n{exc}") from exc


def configure_tracing(settings: Settings) -> bool:
    """LangSmith 키가 있으면 추적을 켜고, 없으면 끈다. 켜졌는지 돌려준다."""
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ.setdefault("LANGSMITH_TRACING", "true")
    else:
        os.environ["LANGSMITH_TRACING"] = "false"
    return tracing_enabled()


def tracing_enabled() -> bool:
    return bool(os.getenv("LANGSMITH_API_KEY")) and os.getenv("LANGSMITH_TRACING", "").lower() == "true"


def has_openai_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
