"""보관함 저장소의 Postgres 구현(ADR-022). 메모리 구현은 `archive.store.InMemoryArchiveStore`."""

from __future__ import annotations

from ..archive.store import ArchiveDocument, ArchivePassage
from .db import Database


class DbArchiveStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, doc: ArchiveDocument, passages: list[ArchivePassage]) -> None:
        self.db.archive_add(doc.model_dump(), [p.model_dump() for p in passages])

    def candidates(self, customer_id: str, words: list[str]) -> list[ArchivePassage]:
        return [ArchivePassage.model_validate(r) for r in self.db.archive_candidates(customer_id, words)]

    def get_passage(self, customer_id: str, hit_id: str) -> ArchivePassage | None:
        row = self.db.archive_get(customer_id, hit_id)
        return None if row is None else ArchivePassage.model_validate(row)

    def list_documents(self, customer_id: str, limit: int = 200) -> list[ArchiveDocument]:
        return [ArchiveDocument.model_validate(r) for r in self.db.archive_list(customer_id, limit)]

    def delete_document(self, customer_id: str, document_id: str) -> bool:
        return self.db.archive_delete(customer_id, document_id)
