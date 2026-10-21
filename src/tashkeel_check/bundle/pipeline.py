"""이름 추출 → 근거 검색 → 인용 검증 → 판정을 잇는다(가이드 6단계 `review_bundle`).

LLM 경로(가이드 9단계): 단일 문서 결과(`ReviewResult`)의 proper_noun 항목을 `NameMention`으로 바꿔 같은 길을 태운다.
라벨 칸이 있는 구간은 라벨이 우선이고, LLM 항목은 라벨 칸이 없는 구간에서만 쓴다. LLM 호출 실패는 `model_error`다.
"""

from __future__ import annotations

from ..results import ReviewResult
from ..text import normalize_key
from .dictionary import DictionaryLookup
from .evidence import search_evidence, validated
from .extractor import LABELS, english_fields, extract_names, split_fields
from .rules import decide_status
from .schemas import Bundle, Document, EntityType, NameMention, ReviewItem


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


def mentions_from_result(
    result: ReviewResult, document: Document, entity_types: dict[str, EntityType] | None = None
) -> list[NameMention]:
    """단일 문서 결과의 유효한 proper_noun 항목을 NameMention으로. 대상 ID는 구간에서 가져온다.

    `translated_name`은 LLM이 채택한 표기(`adopted`)다. 근거 없이 채택한 표기(adopt_unsupported)도 묶음 근거와
    비교하는 대상이 된다. 보류(adopted 없음)는 번역 표기 없음으로 들어가 근거 표기를 제안받는다."""
    out: list[NameMention] = []
    for it in result.items:
        if it.type != "proper_noun" or not it.valid or it.segment_id is None:
            continue
        seg = document.segment(it.segment_id)
        if seg is None:
            continue
        out.append(
            NameMention(
                mention_id=f"{document.document_id}:{it.segment_id}:llm{it.item_index}",
                document_id=document.document_id,
                segment_id=it.segment_id,
                entity_id=seg.entity_id,
                entity_type=(entity_types or {}).get(seg.entity_id or "", "other"),
                arabic_name=it.arabic,
                arabic_key=normalize_key(it.arabic),
                translated_name=it.adopted or seg.translated_name,
                source="llm",
            )
        )
    return out


def merge_mentions(
    bundle: Bundle, label_mentions: list[NameMention], llm_mentions: list[NameMention]
) -> list[NameMention]:
    """라벨 칸이 있는 구간은 라벨 결과만 쓴다. LLM 항목은 라벨 칸 없는 구간에서만 더한다."""
    labeled: set[tuple[str, str]] = set()
    for doc in bundle.documents:
        for seg in doc.segments:
            if split_fields(seg.text):
                labeled.add((doc.document_id, seg.segment_id))
    extra = [m for m in llm_mentions if (m.document_id, m.segment_id) not in labeled]
    return label_mentions + extra


def model_error_item(document: Document, error: str) -> ReviewItem:
    """LLM 호출 실패(API 오류·실행 환경 문제)는 이름 미검출이 아니라 실행 오류로 기록한다."""
    return ReviewItem(
        mention_id=f"{document.document_id}:llm",
        document_id=document.document_id,
        segment_id="",
        entity_id=None,
        entity_type="other",
        arabic_name="",
        translated_name=None,
        evidence=[],
        status="pending",
        reason="model_error",
        detail=error,
    )
