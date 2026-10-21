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

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ..results import ReviewResult
from ..text import normalize_key
from .models import Base, Document, Job, NameItem, Run

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

    def insert_job(self, job_id: str, document_id: str, condition: str) -> None:
        with self.session() as s:
            s.add(Job(id=job_id, document_id=document_id, condition=condition, status="queued"))

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
