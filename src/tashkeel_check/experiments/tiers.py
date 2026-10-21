"""OpenAI 처리 등급 flex로 실험을 돌릴 때 쓰는 모델(ADR-020).

flex는 기본 등급의 약 절반 값이지만, 용량이 없으면 429("Flex processing is temporarily unavailable")를 낸다.
그 오류가 그래프까지 올라가면 형식 실패용 재시도(Settings.max_retries) 예산을 써 버려, flex 사정이 실험 결과에
끼어든다(dev 점검 2026-10-21에서 한 번 있었다). 그래서 모델 안에서 처리한다.

- 잠깐 기다렸다 flex로 다시 부르고(FLEX_WAITS), 그래도 안 되면 그 호출만 기본 등급으로 보낸다.
- 같은 모델에 같은 요청이라 출력 분포는 같고, 값과 지연만 다르다.
- 몇 번 다시 불렀고 몇 번 기본 등급으로 보냈는지는 fallback_counts()로 센다(비용 어림을 고칠 때 쓴다).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from typing import Any

import openai
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

FLEX_UNAVAILABLE = "Flex processing is temporarily unavailable"
FLEX_WAITS = (5.0, 20.0)  # flex로 다시 부르기 전에 기다리는 초. 다 쓰면 기본 등급으로 보낸다

_lock = threading.Lock()
_counts: Counter[str] = Counter()


def _count(key: str) -> None:
    with _lock:
        _counts[key] += 1


def fallback_counts() -> dict[str, int]:
    with _lock:
        return dict(_counts)


def reset_fallback_counts() -> None:
    with _lock:
        _counts.clear()


class FlexChatOpenAI(ChatOpenAI):
    """service_tier="flex"로 부르고, flex 용량 부족(429)은 다시 부르거나 그 호출만 기본 등급으로 보낸다."""

    service_tier: str | None = "flex"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        for wait in FLEX_WAITS:
            try:
                return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
            except openai.RateLimitError as exc:
                if FLEX_UNAVAILABLE not in str(exc):
                    raise  # 보통 속도 제한은 클라이언트 재시도와 harness의 멈춤에 맡긴다
                _count("flex_retry")
                logger.warning("flex 용량 부족(429). %.0f초 뒤 flex로 다시 부릅니다.", wait)
                time.sleep(wait)
        try:
            return super()._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        except openai.RateLimitError as exc:
            if FLEX_UNAVAILABLE not in str(exc):
                raise
        _count("default_fallback")
        logger.warning("flex 용량 부족이 이어져 이 호출만 기본 등급으로 보냅니다.")
        return super()._generate(messages, stop=stop, run_manager=run_manager, **{**kwargs, "service_tier": "default"})
