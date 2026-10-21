"""근거 검색과 인용 검증(가이드 4·5단계).

근거는 같은 묶음의 **다른 서류**에서, **같은 대상 ID**가 붙은 구간의 영문 칸이다.
아랍어 표기가 같다는 이유로 다른 대상의 구간을 쓰지 않는다. 검증은 서류·구간·인용·영문 표기를
원문과 다시 대조한다. 실패 코드는 `reconcile.verify_evidence`와 같은 이름 체계를 쓴다.
"""

from __future__ import annotations

from ..text import nfc
from .extractor import LABELS, english_fields
from .schemas import Bundle, BundleEvidence, EntityType, NameMention


def strict_form(spelling: str) -> str:
    """대소문자·앞뒤·연속 공백만 정리한 비교형. 철자는 바꾸지 않는다."""
    return " ".join(nfc(spelling).casefold().split())


def search_evidence(
    bundle: Bundle, mention: NameMention, labels: dict[str, EntityType] = LABELS
) -> list[BundleEvidence]:
    """같은 대상 ID가 붙은 다른 서류의 영문 칸을 전부 돌려준다. 검증은 하지 않는다."""
    if mention.entity_id is None:
        return []
    found: list[BundleEvidence] = []
    for doc in bundle.documents:
        if doc.document_id == mention.document_id:
            continue
        for seg in doc.segments:
            if seg.entity_id != mention.entity_id:
                continue
            for field in english_fields(seg.text, labels):
                found.append(
                    BundleEvidence(
                        document_id=doc.document_id,
                        segment_id=seg.segment_id,
                        quote=seg.text,
                        english_name=field.value,
                    )
                )
    return found


def validate_evidence(bundle: Bundle, evidence: BundleEvidence) -> tuple[bool, str | None]:
    """근거가 원문에 실제로 있는지 본다. (통과 여부, 실패 코드)."""
    doc = bundle.document(evidence.document_id)
    if doc is None:
        return False, "document_not_found"
    seg = doc.segment(evidence.segment_id)
    if seg is None:
        return False, "segment_not_found"
    if not evidence.quote.strip():
        return False, "empty_quote"
    if strict_form(evidence.quote) not in strict_form(seg.text):
        return False, "quote_not_in_segment"
    if not evidence.english_name.strip() or strict_form(evidence.english_name) not in strict_form(evidence.quote):
        return False, "name_not_in_quote"
    return True, None


def validated(bundle: Bundle, evidence: list[BundleEvidence]) -> list[BundleEvidence]:
    out: list[BundleEvidence] = []
    for ev in evidence:
        ok, failure = validate_evidence(bundle, ev)
        out.append(ev.model_copy(update={"valid": ok, "failure": failure}))
    return out
