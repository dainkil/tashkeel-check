"""Postgres 연결(SQLAlchemy 2 + psycopg 3). DATABASE_URL이 없으면 서비스는 DB 없이 돈다.

연결이 안 되면 기동은 되지만 /health가 db=false를 보이고, 검수 작업 생성은 503이다(예외 "DB 불통").
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..results import ReviewResult
from ..text import normalize_key
from .models import Base, BundleRow, Customer, Document, Job, NameDictionary, NameItem, ReviewItemRow, Run, UsageRow

logger = logging.getLogger(__name__)


def new_id() -> str:
    return uuid.uuid4().hex


def now() -> datetime:
    return datetime.now(UTC)


class Database:
    def __init__(self, url: str) -> None:
        self.url = url
        self.engine: Engine = create_engine(url, pool_pre_ping=True, future=True)
        self._session = sessionmaker(self.engine, expire_on_commit=False)

    def ping(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            logger.warning("DB 연결 실패: %s", exc)
            return False

    def create_all(self) -> None:
        """테스트·개발용. 배포는 alembic upgrade head."""
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self._session() as s:
            yield s
            s.commit()

    # -- 쓰기 --
    def insert_document(self, doc: dict, source: str, tokens: list[dict]) -> str:
        text_norm = "\n".join(s["text"] for s in doc["segments"])
        row = Document(
            id=new_id(),
            source=source,
            doc_id=doc["doc_id"],
            sha256=hashlib.sha256(text_norm.encode("utf-8")).hexdigest(),
            text_normalized=text_norm,
            segments=[dict(s) for s in doc["segments"]],
            tokens=[dict(t) for t in tokens],
            synthetic=bool(doc.get("synthetic")),
        )
        with self.session() as s:
            s.add(row)
        return row.id

    def insert_job(self, job_id: str, document_id: str, condition: str, customer_id: str | None = None) -> None:
        with self.session() as s:
            s.add(
                Job(id=job_id, document_id=document_id, condition=condition, status="queued", customer_id=customer_id)
            )

    def update_job(self, job_id: str, **fields: Any) -> None:
        with self.session() as s:
            row = s.get(Job, job_id)
            if row is None:
                return
            for k, v in fields.items():
                setattr(row, k, v)

    def insert_run(self, job_id: str, document_id: str, result: ReviewResult, out_dir: str | None) -> str:
        dump = result.model_dump(mode="json")
        run = Run(
            id=new_id(),
            job_id=job_id,
            document_id=document_id,
            condition=result.condition,
            model=result.meta.model,
            prompt_hash=result.meta.prompt_hash,
            analyzer_version=dump["meta"]["analyzer"],
            metrics=dump["metrics"],
            run_meta=dump["meta"],
            usage=dump["meta"]["usage"],
            result=dump,
            out_dir=out_dir,
        )
        items = [
            NameItem(
                id=new_id(),
                run_id=run.id,
                document_id=document_id,
                token_ids=list(it.token_ids),
                arabic=it.arabic,
                arabic_key=normalize_key(it.arabic),
                candidates=[c.model_dump(mode="json") for c in it.candidates],
                adopted=it.adopted,
                decision=it.decision,
                final_decision=it.final_decision,
                evidence_source="document" if it.evidence is not None else None,
                evidence_document_id=document_id if it.evidence is not None else None,
                evidence_segment_id=it.evidence.segment_id if it.evidence is not None else None,
                evidence_quote=it.evidence.quote if it.evidence is not None else None,
                flags=list(it.flags),
            )
            for it in result.items
            if it.type == "proper_noun"
        ]
        with self.session() as s:
            s.add(run)
            s.add_all(items)
        return run.id

    # -- 읽기 --
    def recent_jobs(self, limit: int) -> list[dict]:
        with self.session() as s:
            rows = s.execute(select(Job).order_by(Job.created_at.desc()).limit(limit)).scalars().all()
            return [
                {
                    "job_id": r.id,
                    "document_id": r.document_id,
                    "condition": r.condition,
                    "status": r.status,
                    "node": r.node,
                    "attempts": r.attempts,
                    "error": r.error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]

    def run_for_job(self, job_id: str) -> dict | None:
        with self.session() as s:
            row = s.execute(select(Run).where(Run.job_id == job_id)).scalars().first()
            return None if row is None else {"run_id": row.id, "result": row.result, "out_dir": row.out_dir}

    def count_name_items(self, run_id: str) -> int:
        with self.session() as s:
            return len(s.execute(select(NameItem.id).where(NameItem.run_id == run_id)).all())

    # -- 묶음 검수(단계 2) --
    @staticmethod
    def _bundle_query(bundle_id: str, customer_id: str | None):  # type: ignore[no-untyped-def]
        q = select(BundleRow).where(BundleRow.bundle_id == bundle_id)
        if customer_id is not None:
            q = q.where(BundleRow.customer_id == customer_id)
        return q.order_by(BundleRow.updated_at.desc())

    def upsert_bundle(self, bundle: dict, items: list[dict]) -> str:
        """같은 고객의 같은 bundle_id면 입력과 결과를 통째로 바꾼다(ADR-019)."""
        with self.session() as s:
            row = (
                s.execute(
                    select(BundleRow).where(
                        BundleRow.bundle_id == bundle["bundle_id"],
                        BundleRow.customer_id.is_not_distinct_from(bundle.get("customer_id")),
                    )
                )
                .scalars()
                .first()
            )
            if row is None:
                row = BundleRow(id=new_id(), bundle_id=bundle["bundle_id"], customer_id=bundle.get("customer_id"))
                s.add(row)
            row.payload = bundle
            row.updated_at = now()
            s.flush()
            for old in s.execute(select(ReviewItemRow).where(ReviewItemRow.bundle_pk == row.id)).scalars().all():
                s.delete(old)
            s.add_all(
                ReviewItemRow(
                    id=new_id(),
                    bundle_pk=row.id,
                    mention_id=it["mention_id"],
                    document_id=it["document_id"],
                    segment_id=it["segment_id"],
                    entity_id=it.get("entity_id"),
                    entity_type=it["entity_type"],
                    arabic_name=it["arabic_name"],
                    arabic_key=normalize_key(it["arabic_name"]),
                    translated_name=it.get("translated_name"),
                    status=it["status"],
                    reason=it["reason"],
                    evidence=it["evidence"],
                    suggestion=it.get("suggestion"),
                    detail=it.get("detail", ""),
                )
                for it in items
            )
            return row.id

    def get_bundle(self, bundle_id: str, customer_id: str | None = None) -> dict | None:
        with self.session() as s:
            row = s.execute(self._bundle_query(bundle_id, customer_id)).scalars().first()
            return None if row is None else dict(row.payload)

    def list_review_items(self, bundle_id: str, customer_id: str | None = None) -> list[dict] | None:
        with self.session() as s:
            row = s.execute(self._bundle_query(bundle_id, customer_id)).scalars().first()
            if row is None:
                return None
            rows = s.execute(
                select(ReviewItemRow).where(ReviewItemRow.bundle_pk == row.id).order_by(ReviewItemRow.mention_id)
            ).scalars()
            return [
                {
                    "mention_id": r.mention_id,
                    "document_id": r.document_id,
                    "segment_id": r.segment_id,
                    "entity_id": r.entity_id,
                    "entity_type": r.entity_type,
                    "arabic_name": r.arabic_name,
                    "translated_name": r.translated_name,
                    "evidence": r.evidence,
                    "status": r.status,
                    "reason": r.reason,
                    "detail": r.detail,
                    "suggestion": r.suggestion,
                }
                for r in rows
            ]

    def recent_bundles(self, limit: int, customer_id: str | None = None) -> list[dict]:
        with self.session() as s:
            q = select(BundleRow)
            if customer_id is not None:
                q = q.where(BundleRow.customer_id == customer_id)
            rows = s.execute(q.order_by(BundleRow.updated_at.desc()).limit(limit)).scalars().all()
            out = []
            for r in rows:
                counts = s.execute(
                    select(ReviewItemRow.status, func.count())
                    .where(ReviewItemRow.bundle_pk == r.id)
                    .group_by(ReviewItemRow.status)
                ).all()
                by = {status: n for status, n in counts}
                out.append(
                    {
                        "bundle_id": r.bundle_id,
                        "customer_id": r.customer_id,
                        "documents": len(r.payload.get("documents", [])),
                        "confirmed": by.get("confirmed", 0),
                        "pending": by.get("pending", 0),
                        "created_at": r.updated_at.isoformat() if r.updated_at else None,
                    }
                )
            return out

    def upsert_dictionary_entry(self, entry: dict) -> str:
        """등록·갱신하고 행 id를 돌려준다. 같은 키(고객·대상·아랍어)면 덮어쓴다."""
        skip = {"verified_at", "id"}
        with self.session() as s:
            row = (
                s.execute(
                    select(NameDictionary).where(
                        NameDictionary.customer_id == entry["customer_id"],
                        NameDictionary.entity_id == entry["entity_id"],
                        NameDictionary.arabic_key == entry["arabic_key"],
                    )
                )
                .scalars()
                .first()
            )
            if row is None:
                row = NameDictionary(id=new_id(), **{k: v for k, v in entry.items() if k not in skip})
                s.add(row)
            else:
                for k, v in entry.items():
                    if k not in skip:
                        setattr(row, k, v)
            row.verified_at = datetime.fromisoformat(entry["verified_at"]) if entry.get("verified_at") else now()
            return row.id

    @staticmethod
    def _dictionary_dict(row: NameDictionary) -> dict:
        return {
            "id": row.id,
            "customer_id": row.customer_id,
            "entity_id": row.entity_id,
            "entity_type": row.entity_type,
            "arabic_key": row.arabic_key,
            "arabic_name": row.arabic_name,
            "english_name": row.english_name,
            "evidence_document_id": row.evidence_document_id,
            "evidence_segment_id": row.evidence_segment_id,
            "evidence_quote": row.evidence_quote,
            "verified_by": row.verified_by,
            "verified_at": row.verified_at,
        }

    def list_dictionary(self, customer_id: str, limit: int = 200) -> list[dict]:
        with self.session() as s:
            rows = (
                s.execute(
                    select(NameDictionary)
                    .where(NameDictionary.customer_id == customer_id)
                    .order_by(NameDictionary.verified_at.desc())
                    .limit(limit)
                )
                .scalars()
                .all()
            )
            return [self._dictionary_dict(r) for r in rows]

    def delete_dictionary_entry(self, entry_id: str, customer_id: str) -> bool:
        with self.session() as s:
            row = s.get(NameDictionary, entry_id)
            if row is None or row.customer_id != customer_id:
                return False
            s.delete(row)
            return True

    def mark_name_items_glossary(self, run_id: str, hits: list[tuple[list[int], str]]) -> None:
        """단일 문서 경로의 사전 적중(ADR-021)을 name_items에 남긴다. hits: (토큰 ID 목록, 영문 표기)."""
        if not hits:
            return
        wanted = {tuple(ids): english for ids, english in hits}
        with self.session() as s:
            rows = s.execute(select(NameItem).where(NameItem.run_id == run_id)).scalars().all()
            for r in rows:
                english = wanted.get(tuple(r.token_ids))
                if english is not None:
                    r.evidence_source = "glossary"
                    r.evidence_quote = english

    def lookup_verified_name(self, customer_id: str, entity_id: str, arabic_key: str) -> dict | None:
        with self.session() as s:
            row = (
                s.execute(
                    select(NameDictionary).where(
                        NameDictionary.customer_id == customer_id,
                        NameDictionary.entity_id == entity_id,
                        NameDictionary.arabic_key == arabic_key,
                    )
                )
                .scalars()
                .first()
            )
            return None if row is None else self._dictionary_dict(row)

    # -- 고객·API 키·사용량(ADR-019) --
    @staticmethod
    def _customer_dict(row: Customer) -> dict:
        return {
            "id": row.id,
            "name": row.name,
            "key_prefix": row.key_prefix,
            "active": row.active,
            "created_at": row.created_at,
            "revoked_at": row.revoked_at,
        }

    def insert_customer(self, name: str, api_key_hash: str, key_prefix: str) -> dict:
        row = Customer(id=new_id(), name=name, api_key_hash=api_key_hash, key_prefix=key_prefix, active=True)
        with self.session() as s:
            s.add(row)
            s.flush()
            s.refresh(row)
            return self._customer_dict(row)

    def customer_by_hash(self, api_key_hash: str) -> dict | None:
        with self.session() as s:
            row = s.execute(select(Customer).where(Customer.api_key_hash == api_key_hash)).scalars().first()
            return None if row is None else self._customer_dict(row)

    def list_customers(self) -> list[dict]:
        with self.session() as s:
            rows = s.execute(select(Customer).order_by(Customer.created_at)).scalars().all()
            return [self._customer_dict(r) for r in rows]

    def revoke_customer(self, customer_id: str) -> bool:
        with self.session() as s:
            row = s.get(Customer, customer_id)
            if row is None or not row.active:
                return False
            row.active = False
            row.revoked_at = now()
            return True

    def count_active_customers(self) -> int:
        with self.session() as s:
            return int(s.execute(select(func.count()).select_from(Customer).where(Customer.active)).scalar_one())

    def insert_usage(self, rec: dict) -> None:
        with self.session() as s:
            s.add(UsageRow(id=new_id(), **rec))

    def usage_rows(self, customer_id: str | None, start: datetime, end: datetime) -> list[dict]:
        with self.session() as s:
            q = select(UsageRow).where(UsageRow.created_at >= start, UsageRow.created_at < end)
            if customer_id is not None:
                q = q.where(UsageRow.customer_id == customer_id)
            rows = s.execute(q.order_by(UsageRow.created_at)).scalars().all()
            return [
                {
                    c: getattr(r, c)
                    for c in (
                        "customer_id",
                        "kind",
                        "job_id",
                        "bundle_id",
                        "review_id",
                        "condition",
                        "input_tokens",
                        "output_tokens",
                        "total_tokens",
                        "llm_calls",
                        "n_segments",
                        "n_arabic_tokens",
                        "created_at",
                    )
                }
                for r in rows
            ]
