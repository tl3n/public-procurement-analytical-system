"""initial schema

Revision ID: e986269114aa
Revises:
Create Date: 2026-05-22 13:09:15.497476
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e986269114aa"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- Tables ---
    op.create_table(
        "cpv_classification",
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("parent_code", sa.String(length=16), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["parent_code"], ["cpv_classification.code"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("related_entity_type", sa.String(length=32), nullable=False),
        sa.Column("related_entity_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("format", sa.String(length=128), nullable=True),
        sa.Column("date_published", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "procuring_entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("edrpou", sa.String(length=16), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("region", sa.String(length=128), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edrpou"),
    )
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("edrpou", sa.String(length=16), nullable=True),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("edrpou"),
    )
    op.create_table(
        "sync_state",
        sa.Column("feed_name", sa.String(length=64), nullable=False),
        sa.Column("last_offset", sa.Text(), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("feed_name"),
    )
    op.create_table(
        "tenders",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("tender_id_human", sa.String(length=32), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("procurement_method", sa.String(length=32), nullable=True),
        sa.Column("procurement_method_type", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("value_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("value_currency", sa.String(length=3), nullable=True),
        sa.Column("date_published", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tender_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tender_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("procuring_entity_id", sa.Uuid(), nullable=False),
        sa.Column("source_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["procuring_entity_id"], ["procuring_entities.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "complaints",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("tender_id", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("type", sa.String(length=64), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("date_submitted", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lots",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("tender_id", sa.String(length=32), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("value_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("value_currency", sa.String(length=3), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "risk_indicator_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tender_id", sa.String(length=32), nullable=False),
        sa.Column("indicator_code", sa.String(length=64), nullable=False),
        sa.Column("value_boolean", sa.Boolean(), nullable=True),
        sa.Column("value_numeric", sa.Numeric(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tender_id"], ["tenders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bids",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("lot_id", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("value_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("value_currency", sa.String(length=3), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "items",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("lot_id", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cpv_code", sa.String(length=16), nullable=True),
        sa.Column("quantity", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "awards",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("lot_id", sa.String(length=32), nullable=False),
        sa.Column("bid_id", sa.String(length=32), nullable=True),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("value_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("value_currency", sa.String(length=3), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["bid_id"], ["bids.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "contracts",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("award_id", sa.String(length=32), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("value_amount", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("value_currency", sa.String(length=3), nullable=True),
        sa.Column("date_signed", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "raw_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["award_id"], ["awards.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("award_id"),
    )

    # --- Foreign-key indexes ---
    # PostgreSQL does not index foreign keys automatically; without these every
    # join falls back to a sequential scan.
    op.create_index(
        "ix_cpv_classification_parent_code",
        "cpv_classification",
        ["parent_code"],
    )
    op.create_index(
        "ix_tenders_procuring_entity_id", "tenders", ["procuring_entity_id"]
    )
    op.create_index("ix_complaints_tender_id", "complaints", ["tender_id"])
    op.create_index("ix_lots_tender_id", "lots", ["tender_id"])
    op.create_index(
        "ix_risk_indicator_values_tender_id",
        "risk_indicator_values",
        ["tender_id"],
    )
    op.create_index("ix_bids_lot_id", "bids", ["lot_id"])
    op.create_index("ix_bids_supplier_id", "bids", ["supplier_id"])
    op.create_index("ix_items_lot_id", "items", ["lot_id"])
    op.create_index("ix_awards_lot_id", "awards", ["lot_id"])
    op.create_index("ix_awards_bid_id", "awards", ["bid_id"])
    op.create_index("ix_awards_supplier_id", "awards", ["supplier_id"])
    op.create_index("ix_contracts_supplier_id", "contracts", ["supplier_id"])
    # contracts.award_id is already indexed by its UNIQUE constraint.

    # Polymorphic document lookup.
    op.create_index(
        "ix_documents_related",
        "documents",
        ["related_entity_type", "related_entity_id"],
    )

    # --- Range-filter indexes on tenders ---
    op.create_index("ix_tenders_date_published", "tenders", ["date_published"])
    op.create_index("ix_tenders_value_amount", "tenders", ["value_amount"])

    # --- Composite indexes for multi-column filters ---
    # Columns ordered by decreasing selectivity (buyer, status, date).
    op.create_index(
        "ix_tenders_buyer_status_published",
        "tenders",
        ["procuring_entity_id", "status", "date_published"],
    )
    # Bids of a given supplier over time.
    op.create_index("ix_bids_supplier_date", "bids", ["supplier_id", "date"])

    # --- Partial index for the common "active tenders" dashboard query ---
    op.create_index(
        "ix_tenders_active",
        "tenders",
        ["date_published"],
        postgresql_where=sa.text("status LIKE 'active%'"),
    )

    # --- GIN index for ad-hoc queries into the raw JSONB document ---
    op.create_index(
        "ix_tenders_raw_data",
        "tenders",
        ["raw_data"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    # --- Indexes ---
    op.drop_index("ix_tenders_raw_data", table_name="tenders")
    op.drop_index("ix_tenders_active", table_name="tenders")
    op.drop_index("ix_bids_supplier_date", table_name="bids")
    op.drop_index("ix_tenders_buyer_status_published", table_name="tenders")
    op.drop_index("ix_tenders_value_amount", table_name="tenders")
    op.drop_index("ix_tenders_date_published", table_name="tenders")
    op.drop_index("ix_documents_related", table_name="documents")
    op.drop_index("ix_contracts_supplier_id", table_name="contracts")
    op.drop_index("ix_awards_supplier_id", table_name="awards")
    op.drop_index("ix_awards_bid_id", table_name="awards")
    op.drop_index("ix_awards_lot_id", table_name="awards")
    op.drop_index("ix_items_lot_id", table_name="items")
    op.drop_index("ix_bids_supplier_id", table_name="bids")
    op.drop_index("ix_bids_lot_id", table_name="bids")
    op.drop_index(
        "ix_risk_indicator_values_tender_id", table_name="risk_indicator_values"
    )
    op.drop_index("ix_lots_tender_id", table_name="lots")
    op.drop_index("ix_complaints_tender_id", table_name="complaints")
    op.drop_index("ix_tenders_procuring_entity_id", table_name="tenders")
    op.drop_index(
        "ix_cpv_classification_parent_code", table_name="cpv_classification"
    )

    # --- Tables ---
    op.drop_table("contracts")
    op.drop_table("awards")
    op.drop_table("items")
    op.drop_table("bids")
    op.drop_table("risk_indicator_values")
    op.drop_table("lots")
    op.drop_table("complaints")
    op.drop_table("tenders")
    op.drop_table("sync_state")
    op.drop_table("suppliers")
    op.drop_table("procuring_entities")
    op.drop_table("documents")
    op.drop_table("cpv_classification")
