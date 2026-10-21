"""단계 1.5 초기 테이블: documents, jobs, runs, name_items (docs/roadmap.md 2.5절 M1.5 부분집합)

Revision ID: 0001
Revises:
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("doc_id", sa.String(64), nullable=False),
        sa.Column("bundle_id", sa.String(32), nullable=True),
        sa.Column("customer_id", sa.String(32), nullable=True),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("text_normalized", sa.Text(), nullable=False),
        sa.Column("segments", postgresql.JSONB(), nullable=False),
        sa.Column("tokens", postgresql.JSONB(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("condition", sa.String(2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("node", sa.String(16), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("job_id", sa.String(32), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("condition", sa.String(2), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("analyzer_version", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("run_meta", postgresql.JSONB(), nullable=False),
        sa.Column("usage", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("out_dir", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "name_items",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("runs.id"), nullable=False),
        sa.Column("document_id", sa.String(32), sa.ForeignKey("documents.id"), nullable=False),
        sa.Column("token_ids", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("arabic", sa.Text(), nullable=False),
        sa.Column("arabic_key", sa.Text(), nullable=False),
        sa.Column("candidates", postgresql.JSONB(), nullable=False),
        sa.Column("adopted", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("final_decision", sa.String(32), nullable=False),
        sa.Column("evidence_source", sa.String(16), nullable=True),
        sa.Column("evidence_segment_id", sa.String(16), nullable=True),
        sa.Column("evidence_quote", sa.Text(), nullable=True),
        sa.Column("flags", postgresql.ARRAY(sa.String()), nullable=False),
    )
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])
    op.create_index("ix_runs_job_id", "runs", ["job_id"])
    op.create_index("ix_name_items_run_id", "name_items", ["run_id"])
    op.create_index("ix_name_items_arabic_key", "name_items", ["arabic_key"])


def downgrade() -> None:
    op.drop_table("name_items")
    op.drop_table("runs")
    op.drop_table("jobs")
    op.drop_table("documents")
