"""단일 문서 결과에 회사 사전을 덧씌운다(ADR-021). LLM 없이 코드가 한다.

`ReviewResult`는 건드리지 않는다(골든·실험 경로 보호). 결과 위에 겹쳐 보이는 "덧씌움"(overlay)만 만들고,
작업 응답(`GET /v1/jobs/{id}/result`의 `dictionary`)과 화면이 그것을 쓴다.

규칙(묶음 경로 `bundle/rules.py`와 같은 정신):
- 보류(hold)나 근거 검증에 실패한 확정(adopt_unsupported) + 사전 적중
  → `dictionary_adopt`(사전 표기로 확정, 출처 glossary)
- 문서 근거로 확정(evidence_adopt) + 사전 적중인데 표기가 다름 → `conflict`(확정하지 않음, 사유 "사전 vs 문서")
- 문서 근거로 확정 + 사전 표기와 같음 → `agree`(정보만)
- 적중이 없으면 아무것도 만들지 않는다
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .bundle.dictionary import DOCUMENT_SCOPE, DictionaryEntry, DictionaryLookup
from .bundle.evidence import strict_form
from .results import CheckedItem, ReviewResult
from .text import normalize_key

OverlayStatus = Literal["dictionary_adopt", "conflict", "agree"]


class DictionaryOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_index: int
    token_ids: list[int]
    arabic: str
    arabic_key: str
    status: OverlayStatus
    english: str  # 사전 표기
    entry_id: str | None = None
    document_spelling: str | None = None  # conflict·agree일 때 문서 근거 표기
    detail: str = ""


def name_text(it: CheckedItem) -> str:
    """항목의 아랍어 이름 한 벌. 모델이 같은 이름의 두 등장을 한 항목에 묶으면(`token_ids` [11, 86] → "نوال نوال")
    반복을 걷어 낸다. 사전 키와 등록 표기는 이 값으로 만든다."""
    return collapse_repeats(it.arabic)


def collapse_repeats(arabic: str) -> str:
    """단어열이 같은 묶음의 반복이면 한 벌만 남긴다("نوال نوال" → "نوال")."""
    words = arabic.split()
    n = len(words)
    for period in range(1, n):
        if n % period == 0 and words == words[:period] * (n // period):
            return " ".join(words[:period])
    return " ".join(words)


def _overlay(it: CheckedItem, key: str, hit: DictionaryEntry) -> DictionaryOverlay | None:
    status: OverlayStatus
    if it.final_decision == "evidence_adopt" and it.adopted:
        if strict_form(it.adopted) == strict_form(hit.english_name):
            status, detail = "agree", "사전과 문서 근거가 같다"
        else:
            status, detail = "conflict", f"사전 {hit.english_name!r} vs 문서 {it.adopted!r}"
        document_spelling: str | None = it.adopted
    elif it.final_decision in ("hold", "adopt_unsupported"):
        status, detail, document_spelling = "dictionary_adopt", "사람이 확정한 사전 표기", None
    else:
        return None
    return DictionaryOverlay(
        item_index=it.item_index,
        token_ids=list(it.token_ids),
        arabic=name_text(it),
        arabic_key=key,
        status=status,
        english=hit.english_name,
        entry_id=hit.id,
        document_spelling=document_spelling,
        detail=detail,
    )


def apply_dictionary(
    result: ReviewResult, lookup: DictionaryLookup | None, customer_id: str | None
) -> list[DictionaryOverlay]:
    if lookup is None or not customer_id:
        return []
    out: list[DictionaryOverlay] = []
    for it in result.items:
        if it.type != "proper_noun" or not it.valid:
            continue
        key = normalize_key(name_text(it))
        hit = lookup.lookup_verified_name(customer_id, DOCUMENT_SCOPE, key)
        if hit is None:
            continue
        overlay = _overlay(it, key, hit)
        if overlay is not None:
            out.append(overlay)
    return out
