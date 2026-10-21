"""표기 사전(가이드 7단계). 키는 고객 ID + 대상 ID + 정규화한 아랍어 표기(ADR-010 보완, ADR-018).

등록은 사람이 확인 대기 항목을 닫을 때만 한다. 검수 결과를 자동으로 등록하지 않는다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from .schemas import EntityType


class DictionaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: str
    entity_id: str
    entity_type: EntityType = "other"
    arabic_key: str
    arabic_name: str
    english_name: str
    evidence_document_id: str | None = None
    evidence_segment_id: str | None = None
    evidence_quote: str | None = None
    verified_by: str = "reviewer"
    verified_at: datetime | None = None


class DictionaryLookup(Protocol):
    def lookup_verified_name(self, customer_id: str, entity_id: str, arabic_key: str) -> DictionaryEntry | None: ...


class InMemoryDictionary:
    """테스트와 DB 없는 실행용."""

    def __init__(self) -> None:
        self._entries: dict[tuple[str, str, str], DictionaryEntry] = {}

    def register(self, entry: DictionaryEntry) -> DictionaryEntry:
        if entry.verified_at is None:
            entry = entry.model_copy(update={"verified_at": datetime.now(UTC)})
        self._entries[(entry.customer_id, entry.entity_id, entry.arabic_key)] = entry
        return entry

    def lookup_verified_name(self, customer_id: str, entity_id: str, arabic_key: str) -> DictionaryEntry | None:
        return self._entries.get((customer_id, entity_id, arabic_key))

    def __len__(self) -> int:
        return len(self._entries)
