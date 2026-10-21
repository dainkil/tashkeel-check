"""완제품 패키지(ADR-019): customers, usage, jobs.customer_id, bundles 유일 키를 (customer_id, bundle_id)로.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("api_key_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "usage",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("customer_id", sa.String(32), nullable=True),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("job_id", sa.String(32), nullable=True),
        sa.Column("bundle_id", sa.String(64), nullable=True),
        sa.Column("review_id", sa.String(32), nullable=True),
        sa.Column("condition", sa.String(2), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_segments", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_arabic_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_usage_customer_id", "usage", ["customer_id"])
    op.create_index("ix_usage_created_at", "usage", ["created_at"])
    op.add_column("jobs", sa.Column("customer_id", sa.String(32), nullable=True))
    op.create_index("ix_jobs_customer_id", "jobs", ["customer_id"])
    # 0002가 만든 전역 유일 키(bundles_bundle_id_key)를 고객 + 묶음 ID로 바꾼다. NULL 고객(인증 끔)도 하나만.
    op.drop_constraint("bundles_bundle_id_key", "bundles", type_="unique")
    op.execute(
        "ALTER TABLE bundles ADD CONSTRAINT uq_bundles_customer_bundle "
        "UNIQUE NULLS NOT DISTINCT (customer_id, bundle_id)"
    )
    op.create_index("ix_bundles_customer_id", "bundles", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_bundles_customer_id", table_name="bundles")
    op.drop_constraint("uq_bundles_customer_bundle", "bundles", type_="unique")
    op.create_unique_constraint("bundles_bundle_id_key", "bundles", ["bundle_id"])
    op.drop_index("ix_jobs_customer_id", table_name="jobs")
    op.drop_column("jobs", "customer_id")
    op.drop_index("ix_usage_created_at", table_name="usage")
    op.drop_index("ix_usage_customer_id", table_name="usage")
    op.drop_table("usage")
    op.drop_table("customers")
