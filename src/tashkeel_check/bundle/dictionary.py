"""표기 사전(가이드 7단계). 키는 고객 ID + 대상 ID + 정규화한 아랍어 표기(ADR-010 보완, ADR-018).

등록은 사람이 확인 대기 항목을 닫을 때만 한다. 검수 결과를 자동으로 등록하지 않는다.

단일 문서 경로(ADR-021)는 대상 ID가 없으므로 `entity_id`에 `DOCUMENT_SCOPE`("*", 고객 전체)를 쓴다.
묶음 경로는 "*"를 조회하지 않는다(이름이 같다고 다른 대상을 잇지 않는다, ADR-018).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from .schemas import EntityType

DOCUMENT_SCOPE = "*"


class DictionaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None  # 저장소가 붙인다. 삭제(`DELETE /v1/dictionary/{id}`)에 쓴다
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
        key = (entry.customer_id, entry.entity_id, entry.arabic_key)
        old = self._entries.get(key)
        update: dict[str, object] = {}
        if entry.verified_at is None:
            update["verified_at"] = datetime.now(UTC)
        update["id"] = old.id if old is not None and old.id else (entry.id or uuid.uuid4().hex)
        entry = entry.model_copy(update=update)
        self._entries[key] = entry
        return entry

    def lookup_verified_name(self, customer_id: str, entity_id: str, arabic_key: str) -> DictionaryEntry | None:
        return self._entries.get((customer_id, entity_id, arabic_key))

    def list_entries(self, customer_id: str, limit: int = 200) -> list[DictionaryEntry]:
        rows = [e for e in self._entries.values() if e.customer_id == customer_id]
        rows.sort(key=lambda e: e.verified_at or datetime.min.replace(tzinfo=UTC), reverse=True)
        return rows[:limit]

    def delete(self, entry_id: str, customer_id: str) -> bool:
        for key, e in list(self._entries.items()):
            if e.id == entry_id and e.customer_id == customer_id:
                del self._entries[key]
                return True
        return False

    def __len__(self) -> int:
        return len(self._entries)
