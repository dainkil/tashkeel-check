"""Postgres 테이블 4개(docs/roadmap.md 2.5절, M1.5 부분집합): documents, jobs, runs, name_items.

번역을 포함한 결과 전체는 runs.result(JSONB, ReviewResult dump)에 두고, 확인 대기 목록은 name_items로 펼친다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(String(16))  # paste | sample
    doc_id: Mapped[str] = mapped_column(String(64))
    bundle_id: Mapped[str | None] = mapped_column(String(32), nullable=True)  # 단계 2
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
    evidence_segment_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    flags: Mapped[list[str]] = mapped_column(ARRAY(String))
