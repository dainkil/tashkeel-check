"""회사 문서 보관함(ADR-022): archive_documents, archive_passages, documents.customer_id 색인과 되채우기.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-22
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archive_documents",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("document_label", sa.Text(), nullable=False),
        sa.Column("document_sha256", sa.String(64), nullable=False),
        sa.Column("n_passages", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("customer_id", "document_id", name="uq_archive_documents_key"),
    )
    op.create_index("ix_archive_documents_customer_id", "archive_documents", ["customer_id"])
    op.create_table(
        "archive_passages",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("hit_id", sa.String(16), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("document_label", sa.Text(), nullable=False),
        sa.Column("document_sha256", sa.String(64), nullable=False),
        sa.Column("segment_id", sa.String(32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("window", sa.Text(), nullable=False),
        sa.Column("text_key", sa.Text(), nullable=False),
        sa.Column("latin_spans", postgresql.JSONB(), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("customer_id", "hit_id", name="uq_archive_passages_hit"),
    )
    op.create_index("ix_archive_passages_customer_id", "archive_passages", ["customer_id"])
    op.create_index("ix_archive_passages_document_id", "archive_passages", ["document_id"])
    op.create_index("ix_documents_customer_id", "documents", ["customer_id"])
    # 0003까지는 documents.customer_id를 채우지 않았다. 작업의 고객으로 되채운다
    op.execute(
        "UPDATE documents AS d SET customer_id = j.customer_id FROM jobs AS j "
        "WHERE j.document_id = d.id AND d.customer_id IS NULL AND j.customer_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_documents_customer_id", table_name="documents")
    op.drop_index("ix_archive_passages_document_id", table_name="archive_passages")
    op.drop_index("ix_archive_passages_customer_id", table_name="archive_passages")
    op.drop_table("archive_passages")
    op.drop_index("ix_archive_documents_customer_id", table_name="archive_documents")
    op.drop_table("archive_documents")
