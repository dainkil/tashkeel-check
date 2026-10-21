"""묶음 검수의 데이터 구조. 단일 문서 스키마(`schemas.py`)와는 별개다.

- `Bundle` → `Document` → `Segment`: 입력. 구간마다 대상 ID(`entity_id`)와, 있으면 번역 표기
  (`translated_name`)가 붙는다.
- `NameMention`: 서류에서 찾은 고유명사 한 건.
- `BundleEvidence`: 같은 대상의 다른 서류에서 찾은 영문 표기와 그 출처.
- `ReviewItem`: 판정 결과 한 줄. 상태는 확정(confirmed)과 확인 대기(pending) 둘뿐이다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EntityType = Literal["person", "organization", "other"]
ReviewStatus = Literal["confirmed", "pending"]
ReviewReason = Literal[
    "evidence_match",
    "dictionary_match",
    "no_evidence",
    "no_entity_id",
    "cross_document_conflict",
    "translation_mismatch",
    "no_translation",
    "validation_failed",
    "extraction_failed",
    "model_error",
]

# 화면·기록용 한국어 표시명. 판정 코드는 영문 그대로 저장한다.
REASON_LABELS: dict[str, str] = {
    "evidence_match": "근거 일치",
    "dictionary_match": "사전 일치",
    "no_evidence": "근거 없음",
    "no_entity_id": "대상 ID 없음",
    "cross_document_conflict": "서류 간 표기 충돌",
    "translation_mismatch": "번역 표기 불일치",
    "no_translation": "비교 대상 없음",
    "validation_failed": "검증 실패",
    "extraction_failed": "추출 실패",
    "model_error": "실행 오류",
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Segment(_Strict):
    segment_id: str = Field(min_length=1)
    text: str
    entity_id: str | None = None  # 이 구간이 가리키는 대상. 없으면 근거 검색을 하지 않는다
    translated_name: str | None = None  # 이 구간의 고유명사에 이미 붙은 영문 표기(검수 대상)


class Document(_Strict):
    document_id: str = Field(min_length=1)
    document_type: str = Field(min_length=1)
    segments: list[Segment]

    @model_validator(mode="after")
    def _unique_segments(self) -> Document:
        seen: set[str] = set()
        for seg in self.segments:
            if seg.segment_id in seen:
                raise ValueError(f"duplicate segment_id {seg.segment_id!r} in document {self.document_id!r}")
            seen.add(seg.segment_id)
        return self

    def segment(self, segment_id: str) -> Segment | None:
        return next((s for s in self.segments if s.segment_id == segment_id), None)


class Bundle(_Strict):
    bundle_id: str = Field(min_length=1)
    customer_id: str | None = None  # 사전 조회 범위. 없으면 사전을 보지 않는다
    synthetic: bool = False
    notice: str | None = None  # 합성 데이터 표시 등 사람이 읽는 안내
    entities: dict[str, EntityType] = Field(default_factory=dict)  # 대상 ID → 종류(표시·집계용)
    documents: list[Document] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_documents(self) -> Bundle:
        seen: set[str] = set()
        for doc in self.documents:
            if doc.document_id in seen:
                raise ValueError(f"duplicate document_id {doc.document_id!r}")
            seen.add(doc.document_id)
        return self

    def document(self, document_id: str) -> Document | None:
        return next((d for d in self.documents if d.document_id == document_id), None)

    def entity_type(self, entity_id: str | None, default: EntityType = "other") -> EntityType:
        if entity_id is None:
            return default
        return self.entities.get(entity_id, default)


class NameMention(_Strict):
    mention_id: str
    document_id: str
    segment_id: str
    entity_id: str | None
    entity_type: EntityType = "other"
    arabic_name: str
    arabic_key: str  # text.normalize_key(arabic_name)
    translated_name: str | None = None
    source: Literal["label", "llm"] = "label"
    extraction_error: str | None = None


class BundleEvidence(_Strict):
    document_id: str
    segment_id: str
    quote: str  # 그 구간의 원문 그대로
    english_name: str  # 인용 안의 영문 표기
    valid: bool | None = None  # validate_evidence 결과. None이면 아직 검증 전
    failure: str | None = None


class ReviewItem(_Strict):
    mention_id: str
    document_id: str
    segment_id: str
    entity_id: str | None
    entity_type: EntityType
    arabic_name: str
    translated_name: str | None
    evidence: list[BundleEvidence]
    status: ReviewStatus
    reason: ReviewReason
    detail: str = ""  # 사람이 읽는 보조 설명(충돌한 표기 목록, 실패 코드 등)
    suggestion: str | None = None  # 변이 일치로 찾은 표기. 확정에는 쓰지 않는다

    @property
    def reason_label(self) -> str:
        return REASON_LABELS[self.reason]
