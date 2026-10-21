"""Postgres 테이블(docs/roadmap.md 2.5절).

단계 1.5: documents, jobs, runs, name_items. 단계 2: bundles, review_items, name_dictionary.

번역을 포함한 결과 전체는 runs.result(JSONB, ReviewResult dump)에 두고, 확인 대기 목록은 name_items로 펼친다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(16))  # paste | sample
    doc_id: Mapped[str] = mapped_column(String(64))
    bundle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 단계 2
    customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 단계 2
    sha256: Mapped[str] = mapped_column(String(64))
    text_normalized: Mapped[str] = mapped_column(Text)
    segments: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    tokens: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    condition: Mapped[str] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(String(16))  # queued | running | done | failed
    node: Mapped[str | None] = mapped_column(String(16), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    condition: Mapped[str] = mapped_column(String(2))
    model: Mapped[str] = mapped_column(String(128))
    prompt_hash: Mapped[str] = mapped_column(String(64))
    analyzer_version: Mapped[dict[str, Any]] = mapped_column(JSONB)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB)
    run_meta: Mapped[dict[str, Any]] = mapped_column(JSONB)
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB)  # ReviewResult 전체(번역 포함)
    out_dir: Mapped[str | None] = mapped_column(Text, nullable=True)  # results/ 산출 파일 위치
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NameItem(Base):
    __tablename__ = "name_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    token_ids: Mapped[list[int]] = mapped_column(ARRAY(Integer))
    arabic: Mapped[str] = mapped_column(Text)
    arabic_key: Mapped[str] = mapped_column(Text)
    candidates: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    adopted: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(String(32))
    final_decision: Mapped[str] = mapped_column(String(32))
    evidence_source: Mapped[str | None] = mapped_column(String(16), nullable=True)  # document | bundle | glossary
    evidence_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_segment_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    flags: Mapped[list[str]] = mapped_column(ARRAY(String))


class BundleRow(Base):
    """서류 묶음 입력 전체(JSONB). 같은 bundle_id를 다시 검수하면 덮어쓴다."""

    __tablename__ = "bundles"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    bundle_id: Mapped[str] = mapped_column(String(64), unique=True)
    customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewItemRow(Base):
    """묶음 검수 결과 한 줄(bundle.schemas.ReviewItem)."""

    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    bundle_pk: Mapped[str] = mapped_column(ForeignKey("bundles.id", ondelete="CASCADE"), index=True)
    mention_id: Mapped[str] = mapped_column(String(128))
    document_id: Mapped[str] = mapped_column(String(64))
    segment_id: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(16))
    arabic_name: Mapped[str] = mapped_column(Text)
    arabic_key: Mapped[str] = mapped_column(Text)
    translated_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), index=True)  # confirmed | pending
    reason: Mapped[str] = mapped_column(String(32))
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    suggestion: Mapped[str | None] = mapped_column(Text, nullable=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NameDictionary(Base):
    """표기 사전. 키는 고객 + 대상 ID + 정규화 아랍어 표기(ADR-010 보완, ADR-018)."""

    __tablename__ = "name_dictionary"
    __table_args__ = (UniqueConstraint("customer_id", "entity_id", "arabic_key", name="uq_name_dictionary_key"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(16))
    arabic_key: Mapped[str] = mapped_column(Text)
    arabic_name: Mapped[str] = mapped_column(Text)
    english_name: Mapped[str] = mapped_column(Text)
    evidence_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_segment_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[str] = mapped_column(String(16))  # reviewer | auto
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
