"""설정. 골격 노트북처럼 .env를 읽고, LangSmith 키가 없으면 추적만 끈다."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
CONDITIONS = ("C0", "C1", "C2", "C3")


@dataclass(frozen=True)
class Settings:
    model: str = "openai:gpt-6.1-sol"
    temperature: float | None = None  # 모델이 지원하면 .env에서 0으로 둔다
    max_retries: int = 1  # validate → agent 재시도 상한(앱 업무 재시도, LLM 클라이언트 재시도와 별개)
    recursion_limit: int = 25  # create_agent 내부 tool loop의 super-step 상한
    coverage_threshold: float = 0.5  # EXP-001 판단 기준: M5(방언 허용)가 이보다 낮으면 분석기를 이름 근거로 쓰지 않는다
    high_confidence: float = 0.8  # 근거 없이 이 확신도 이상으로 확정하면 "고확신 무근거 확정"
    dev_docs: int = 10
    eval_docs: int = 30
    repeats: int = 3
    max_candidates: int = 10  # 토큰당 LLM에게 보여 줄 분석기 후보 수 상한
    enable_bundle_search: bool = False  # 단계 2 틀(ADR-007). 단계 1 조건 C0~C3에서는 쓰지 않는다
    embedding_model: str = "text-embedding-3-small"
    langsmith_project: str = "tashkeel-check"


def _float_or_none(value: str | None) -> float | None:
    if value is None or value.strip() == "":
        return None
    return float(value)


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    defaults = Settings()
    return Settings(
        model=os.getenv("MODEL", defaults.model),
        temperature=_float_or_none(os.getenv("TEMPERATURE")),
        max_retries=int(os.getenv("MAX_RETRIES", defaults.max_retries)),
        recursion_limit=int(os.getenv("RECURSION_LIMIT", defaults.recursion_limit)),
        coverage_threshold=float(os.getenv("COVERAGE_THRESHOLD", defaults.coverage_threshold)),
        high_confidence=float(os.getenv("HIGH_CONFIDENCE", defaults.high_confidence)),
        dev_docs=int(os.getenv("DEV_DOCS", defaults.dev_docs)),
        eval_docs=int(os.getenv("EVAL_DOCS", defaults.eval_docs)),
        repeats=int(os.getenv("REPEATS", defaults.repeats)),
        max_candidates=int(os.getenv("MAX_CANDIDATES", defaults.max_candidates)),
        enable_bundle_search=os.getenv("ENABLE_BUNDLE_SEARCH", "false").lower() == "true",
        embedding_model=os.getenv("EMBEDDING_MODEL", defaults.embedding_model),
        langsmith_project=os.getenv("LANGSMITH_PROJECT", defaults.langsmith_project),
    )


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
