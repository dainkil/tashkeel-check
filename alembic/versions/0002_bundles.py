"""단계 2 묶음 검수: bundles, review_items, name_dictionary. name_items.evidence_document_id, documents.bundle_id 64자.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("documents", "bundle_id", type_=sa.String(64), existing_type=sa.String(32))
    op.add_column("name_items", sa.Column("evidence_document_id", sa.String(64), nullable=True))
    op.create_table(
        "bundles",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("bundle_id", sa.String(64), nullable=False, unique=True),
        sa.Column("customer_id", sa.String(64), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "review_items",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("bundle_pk", sa.String(32), sa.ForeignKey("bundles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("mention_id", sa.String(128), nullable=False),
        sa.Column("document_id", sa.String(64), nullable=False),
        sa.Column("segment_id", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=True),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column("arabic_name", sa.Text(), nullable=False),
        sa.Column("arabic_key", sa.Text(), nullable=False),
        sa.Column("translated_name", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(32), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("suggestion", sa.Text(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_review_items_bundle_pk", "review_items", ["bundle_pk"])
    op.create_index("ix_review_items_status", "review_items", ["status"])
    op.create_table(
        "name_dictionary",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(16), nullable=False),
        sa.Column("arabic_key", sa.Text(), nullable=False),
        sa.Column("arabic_name", sa.Text(), nullable=False),
        sa.Column("english_name", sa.Text(), nullable=False),
        sa.Column("evidence_document_id", sa.String(64), nullable=True),
        sa.Column("evidence_segment_id", sa.String(32), nullable=True),
        sa.Column("evidence_quote", sa.Text(), nullable=True),
        sa.Column("verified_by", sa.String(16), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("customer_id", "entity_id", "arabic_key", name="uq_name_dictionary_key"),
    )


def downgrade() -> None:
    op.drop_table("name_dictionary")
    op.drop_index("ix_review_items_status", table_name="review_items")
    op.drop_index("ix_review_items_bundle_pk", table_name="review_items")
    op.drop_table("review_items")
    op.drop_table("bundles")
    op.drop_column("name_items", "evidence_document_id")
    op.alter_column("documents", "bundle_id", type_=sa.String(32), existing_type=sa.String(64))
