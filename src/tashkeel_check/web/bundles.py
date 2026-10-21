"""묶음 검수 저장소(가이드 7단계). DB가 없으면 메모리, 있으면 Postgres(`web/db.py`).

묶음 자체와 검수 결과, 표기 사전을 둔다. 사전 등록은 사람이 확인 대기 항목을 닫을 때만 한다(ADR-010·018).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from ..bundle.dictionary import DictionaryEntry, InMemoryDictionary
from ..bundle.schemas import Bundle, ReviewItem
from .db import Database


class BundleStore(Protocol):
    """조회의 `customer_id`는 범위다(ADR-019). None이면 범위 없이 묶음 ID로만 찾는다(인증을 끈 경우)."""

    def save(self, bundle: Bundle, items: list[ReviewItem]) -> None: ...
    def get(self, bundle_id: str, customer_id: str | None = None) -> Bundle | None: ...
    def items(self, bundle_id: str, customer_id: str | None = None) -> list[ReviewItem] | None: ...
    def recent(self, limit: int, customer_id: str | None = None) -> list[dict]: ...


class MemoryBundleStore:
    def __init__(self) -> None:
        self._bundles: dict[tuple[str | None, str], tuple[Bundle, list[ReviewItem], datetime]] = {}

    def save(self, bundle: Bundle, items: list[ReviewItem]) -> None:
        self._bundles[(bundle.customer_id, bundle.bundle_id)] = (bundle, list(items), datetime.now(UTC))

    def _row(self, bundle_id: str, customer_id: str | None):  # type: ignore[no-untyped-def]
        if customer_id is not None:
            return self._bundles.get((customer_id, bundle_id))
        rows = [r for (_, bid), r in self._bundles.items() if bid == bundle_id]
        return max(rows, key=lambda r: r[2]) if rows else None

    def get(self, bundle_id: str, customer_id: str | None = None) -> Bundle | None:
        row = self._row(bundle_id, customer_id)
        return None if row is None else row[0]

    def items(self, bundle_id: str, customer_id: str | None = None) -> list[ReviewItem] | None:
        row = self._row(bundle_id, customer_id)
        return None if row is None else list(row[1])

    def recent(self, limit: int, customer_id: str | None = None) -> list[dict]:
        rows = [r for (cid, _), r in self._bundles.items() if customer_id is None or cid == customer_id]
        rows = sorted(rows, key=lambda r: r[2], reverse=True)[:limit]
        return [_summary(b, items, at) for b, items, at in rows]


def _summary(bundle: Bundle, items: list[ReviewItem], at: datetime | None) -> dict:
    return {
        "bundle_id": bundle.bundle_id,
        "customer_id": bundle.customer_id,
        "documents": len(bundle.documents),
        "confirmed": sum(1 for i in items if i.status == "confirmed"),
        "pending": sum(1 for i in items if i.status == "pending"),
        "created_at": at.isoformat() if at else None,
    }


class DbBundleStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def save(self, bundle: Bundle, items: list[ReviewItem]) -> None:
        self.db.upsert_bundle(bundle.model_dump(mode="json"), [i.model_dump(mode="json") for i in items])

    def get(self, bundle_id: str, customer_id: str | None = None) -> Bundle | None:
        payload = self.db.get_bundle(bundle_id, customer_id)
        return None if payload is None else Bundle.model_validate(payload)

    def items(self, bundle_id: str, customer_id: str | None = None) -> list[ReviewItem] | None:
        rows = self.db.list_review_items(bundle_id, customer_id)
        return None if rows is None else [ReviewItem.model_validate(r) for r in rows]

    def recent(self, limit: int, customer_id: str | None = None) -> list[dict]:
        return self.db.recent_bundles(limit, customer_id)


class DbDictionary:
    def __init__(self, db: Database) -> None:
        self.db = db

    def register(self, entry: DictionaryEntry) -> DictionaryEntry:
        if entry.verified_at is None:
            entry = entry.model_copy(update={"verified_at": datetime.now(UTC)})
        self.db.upsert_dictionary_entry(entry.model_dump(mode="json"))
        return entry

    def lookup_verified_name(self, customer_id: str, entity_id: str, arabic_key: str) -> DictionaryEntry | None:
        row = self.db.lookup_verified_name(customer_id, entity_id, arabic_key)
        return None if row is None else DictionaryEntry.model_validate(row)


Dictionary = InMemoryDictionary | DbDictionary
