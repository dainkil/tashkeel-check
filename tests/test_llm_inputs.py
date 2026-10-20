"""LLM이 보는 입력이 바뀌지 않았는지 지키는 덫(ADR-013).

시스템 프롬프트, 구조화 출력 스키마, 툴 스키마, 사용자 메시지(구간·토큰 표·ANALYZER 블록)의 해시를 고정한다.
값이 바뀌면 리팩토링이 아니라 실험 조건 변경이다. PROMPT_VERSION을 올리고 변경 이력에 남긴 뒤에만 고친다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import pytest
from langchain_core.utils.function_calling import convert_to_openai_tool

from tashkeel_check.analyzer import AnalyzeFn, analyze_tokens
from tashkeel_check.config import CONDITIONS, Settings
from tashkeel_check.prompts import prompt_hash, user_message
from tashkeel_check.runner import load_doc
from tashkeel_check.schemas import AgentOutput
from tashkeel_check.text import Segment, nfc, tokenize
from tashkeel_check.tools import make_analyze_tool

from .conftest import fake_analyze
from .golden_cases import DEV_DOCS

# 2026-10-20, PROMPT_VERSION "p0" 기준
PROMPT_HASHES = {
    "C0": "726a89a5f223d058",
    "C1": "245cca21a7f9926e",
    "C2": "0cfc2227fdcbe5e0",
    "C3": "ef4637bd2f605534",
}
OUTPUT_SCHEMA_SHA = "309023d8e869b43e"
ANALYZE_TOOL_SHA = "ccd52b8087fddf37"
# 사용자 메시지는 dev 문서로 만든다. 2026-10-20 합성 문서 synthetic-v1로 바꾸며 갱신(ADR-014). 위 세 해시는 그대로다
USER_MESSAGES_SHA = {"fakeanalyzer": "beef1349540a797b", "camel": "81bb195d7668886c"}


def _sha(data: Any) -> str:
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _user_messages_sha(analyze_fn: AnalyzeFn | None) -> str:
    """dev 문서 10개 × C0~C3의 사용자 메시지를 그래프의 load·analyze와 같은 방식으로 만든다."""
    max_candidates = Settings().max_candidates
    messages = []
    for path in DEV_DOCS:
        doc = load_doc(path)
        segments = [Segment(segment_id=s["segment_id"], text=nfc(s["text"])) for s in doc["segments"]]
        tokens = tokenize(segments)
        analyses = analyze_tokens(tokens, analyze_fn)
        for cond in CONDITIONS:
            messages.append(user_message(cond, doc["doc_id"], segments, tokens, analyses, max_candidates))
    return _sha("\n\x00\n".join(messages))


def test_system_prompts_unchanged() -> None:
    assert {c: prompt_hash(c) for c in CONDITIONS} == PROMPT_HASHES


def test_structured_output_schema_unchanged() -> None:
    assert _sha(convert_to_openai_tool(AgentOutput)) == OUTPUT_SCHEMA_SHA


def test_analyze_tool_schema_unchanged() -> None:
    assert _sha(convert_to_openai_tool(make_analyze_tool([], {}, [], 10))) == ANALYZE_TOOL_SHA


def test_user_messages_unchanged() -> None:
    assert _user_messages_sha(fake_analyze) == USER_MESSAGES_SHA["fakeanalyzer"]


@pytest.mark.camel
def test_user_messages_with_camel_analyzer_unchanged() -> None:
    assert _user_messages_sha(None) == USER_MESSAGES_SHA["camel"]
