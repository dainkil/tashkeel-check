"""이름 추출 → 근거 검색 → 인용 검증 → 판정을 잇는다(가이드 6단계 `review_bundle`)."""

from __future__ import annotations

from .dictionary import DictionaryLookup
from .evidence import search_evidence, validated
from .extractor import LABELS, english_fields, extract_names
from .rules import decide_status
from .schemas import Bundle, EntityType, NameMention, ReviewItem


def bundle_mentions(bundle: Bundle, labels: dict[str, EntityType] = LABELS) -> list[NameMention]:
    """검수 대상 고유명사. 같은 구간에 영문 칸이 있는 아랍어 칸은 근거 출처이지 검수 대상이 아니다.
    단, 그 구간에 `translated_name`이 따로 붙어 있으면 검수한다."""
    out: list[NameMention] = []
    for doc in bundle.documents:
        for m in extract_names(doc, labels, bundle.entities):
            seg = doc.segment(m.segment_id)
            assert seg is not None
            if seg.translated_name is None and english_fields(seg.text, labels):
                continue
            out.append(m)
    return out


def review_mentions(
    bundle: Bundle, mentions: list[NameMention], dictionary: DictionaryLookup | None = None
) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    for m in mentions:
        evidence = validated(bundle, search_evidence(bundle, m))
        hit = None
        if dictionary is not None and bundle.customer_id and m.entity_id:
            hit = dictionary.lookup_verified_name(bundle.customer_id, m.entity_id, m.arabic_key)
        items.append(decide_status(m, evidence, hit))
    return items


def review_bundle(bundle: Bundle, dictionary: DictionaryLookup | None = None) -> list[ReviewItem]:
    return review_mentions(bundle, bundle_mentions(bundle), dictionary)
