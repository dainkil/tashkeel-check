"""확정·확인 대기 판정(가이드 6단계).

확정은 **정확 일치**(대소문자·공백만 무시)일 때만이다. 공식 서류의 영문 표기는 그대로 써야 하므로
`Mohammed`/`Mohamed`는 다른 표기다. 변이 일치(`romanize.match_spelling`)는 제안(`suggestion`)에만 쓴다.
사전 적중은 근거가 없을 때만 확정 근거가 되고, 근거와 다르면 충돌로 본다.
"""

from __future__ import annotations

from ..romanize import match_spelling
from .dictionary import DictionaryEntry
from .evidence import strict_form
from .schemas import BundleEvidence, NameMention, ReviewItem, ReviewReason, ReviewStatus


def strict_equal(a: str, b: str) -> bool:
    return strict_form(a) == strict_form(b)


def near_match(a: str, b: str) -> bool:
    """같은 독법의 다른 철자인가. 확정에는 쓰지 않는다."""
    try:
        return match_spelling(a, b, dialect=True)
    except Exception:
        return False


def _item(
    mention: NameMention,
    evidence: list[BundleEvidence],
    status: ReviewStatus,
    reason: ReviewReason,
    detail: str = "",
    suggestion: str | None = None,
) -> ReviewItem:
    return ReviewItem(
        mention_id=mention.mention_id,
        document_id=mention.document_id,
        segment_id=mention.segment_id,
        entity_id=mention.entity_id,
        entity_type=mention.entity_type,
        arabic_name=mention.arabic_name,
        translated_name=mention.translated_name,
        evidence=evidence,
        status=status,
        reason=reason,
        detail=detail,
        suggestion=suggestion,
    )


def _compare(
    mention: NameMention, evidence: list[BundleEvidence], reference: str, match_reason: ReviewReason, detail: str
) -> ReviewItem:
    """번역 표기를 기준 표기(근거 또는 사전)와 비교한다."""
    if mention.translated_name is None or not mention.translated_name.strip():
        return _item(mention, evidence, "pending", "no_translation", detail, suggestion=reference)
    if strict_equal(mention.translated_name, reference):
        return _item(mention, evidence, "confirmed", match_reason, detail)
    suggestion = reference if near_match(mention.translated_name, reference) else None
    return _item(
        mention,
        evidence,
        "pending",
        "translation_mismatch",
        f"{detail}; translated={mention.translated_name!r}" if detail else f"translated={mention.translated_name!r}",
        suggestion=suggestion,
    )


def decide_status(
    mention: NameMention, evidence: list[BundleEvidence], dictionary_hit: DictionaryEntry | None = None
) -> ReviewItem:
    """검증을 마친 근거 목록으로 상태와 사유를 정한다. 순서가 곧 우선순위다."""
    if mention.extraction_error:
        return _item(mention, evidence, "pending", "extraction_failed", mention.extraction_error)
    if mention.entity_id is None:
        return _item(mention, evidence, "pending", "no_entity_id")

    valid = [e for e in evidence if e.valid]
    if evidence and not valid:
        codes = sorted({e.failure or "unknown" for e in evidence})
        return _item(mention, evidence, "pending", "validation_failed", ", ".join(codes))

    forms: dict[str, str] = {}
    for e in valid:
        forms.setdefault(strict_form(e.english_name), e.english_name)
    if dictionary_hit is not None and valid and strict_form(dictionary_hit.english_name) not in forms:
        forms.setdefault(strict_form(dictionary_hit.english_name), dictionary_hit.english_name)
        spellings = " / ".join(forms.values())
        return _item(mention, evidence, "pending", "cross_document_conflict", f"dictionary vs document: {spellings}")
    if len(forms) > 1:
        return _item(mention, evidence, "pending", "cross_document_conflict", " / ".join(forms.values()))
    if valid:
        reference = next(iter(forms.values()))
        sources = ", ".join(f"{e.document_id}/{e.segment_id}" for e in valid)
        return _compare(mention, evidence, reference, "evidence_match", f"evidence={reference!r} ({sources})")
    if dictionary_hit is not None:
        return _compare(
            mention,
            evidence,
            dictionary_hit.english_name,
            "dictionary_match",
            f"dictionary={dictionary_hit.english_name!r}",
        )
    return _item(mention, evidence, "pending", "no_evidence")
