"""리팩토링 안전망: 결과와 산출 파일이 골든 스냅숏과 같아야 한다(tests/golden_cases.py)."""

from __future__ import annotations

import json
from functools import cache
from typing import Any

import pytest

from tashkeel_check.config import CONDITIONS

from .golden_cases import ANALYZERS, DEV_DOCS, RESPONDERS, golden_path, snapshot


@cache
def _golden(analyzer: str, responder: str) -> dict[str, Any]:
    return json.loads(golden_path(analyzer, responder).read_text(encoding="utf-8"))


CASES = [
    pytest.param(
        analyzer,
        responder,
        i,
        cond,
        marks=[pytest.mark.camel] if analyzer == "camel" else [],
        id=f"{analyzer}-{responder}-{path.stem}-{cond}",
    )
    for analyzer in ANALYZERS
    for responder in RESPONDERS
    for i, path in enumerate(DEV_DOCS)
    for cond in CONDITIONS
]


@pytest.mark.parametrize(("analyzer", "responder", "doc_index", "condition"), CASES)
def test_matches_golden(analyzer: str, responder: str, doc_index: int, condition: str) -> None:
    expected = _golden(analyzer, responder)[f"{DEV_DOCS[doc_index].stem}:{condition}"]
    assert snapshot(doc_index, condition, analyzer, responder) == expected
