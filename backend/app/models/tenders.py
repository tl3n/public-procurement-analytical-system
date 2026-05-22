"""Core procurement entities.

Tenders, lots, items, bids, awards, contracts and complaints originate from the
Prozorro API, so they use the API's 32-character hexadecimal identifiers as primary
keys  — this makes synchronization upserts straightforward.
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.organizations import ProcuringEntity, Supplier
    from app.models.risk import RiskIndicatorValue

# Money columns: NUMERIC(15, 2) — exact representation, no float drift.
Money = Numeric(15, 2)


class Tender(Base, TimestampMixin):
    """Тендерна процедура — the central entity of the model."""

    __tablename__ = "tenders"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # Human-readable identifier, format UA-YYYY-MM-DD-NNNNNN.
    tender_id_human: Mapped[str | None] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    procurement_method: Mapped[str | None] = mapped_column(String(32))
    # Procedure subtype: open / aboveThresholdUA / belowThreshold / negotiation / ...
    procurement_method_type: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str | None] = mapped_column(String(64))
    value_amount: Mapped[decimal.Decimal | None] = mapped_column(Money)
    value_currency: Mapped[str | None] = mapped_column(String(3))
    date_published: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    tender_period_start: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    tender_period_end: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    procuring_entity_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("procuring_entities.id", ondelete="RESTRICT")
    )

    # dateModified from the API — drives detection of updated records.
    source_modified_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    # Full original API object, kept for arbitrary later analysis.
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    procuring_entity: Mapped[ProcuringEntity] = relationship(back_populates="tenders")
    lots: Mapped[list[Lot]] = relationship(
        back_populates="tender", cascade="all, delete-orphan"
    )
    complaints: Mapped[list[Complaint]] = relationship(
        back_populates="tender", cascade="all, delete-orphan"
    )
    risk_indicator_values: Mapped[list[RiskIndicatorValue]] = relationship(
        back_populates="tender", cascade="all, delete-orphan"
    )


class Lot(Base, TimestampMixin):
    """Лот — a unit within a tender against which winners are determined."""

    __tablename__ = "lots"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tender_id: Mapped[str] = mapped_column(
        ForeignKey("tenders.id", ondelete="RESTRICT")
    )
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(String(64))
    value_amount: Mapped[decimal.Decimal | None] = mapped_column(Money)
    value_currency: Mapped[str | None] = mapped_column(String(3))

    tender: Mapped[Tender] = relationship(back_populates="lots")
    items: Mapped[list[Item]] = relationship(
        back_populates="lot", cascade="all, delete-orphan"
    )
    bids: Mapped[list[Bid]] = relationship(
        back_populates="lot", cascade="all, delete-orphan"
    )
    awards: Mapped[list[Award]] = relationship(
        back_populates="lot", cascade="all, delete-orphan"
    )


class Item(Base, TimestampMixin):
    """Предмет закупівлі — a good, work or service procured within a lot."""

    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"))
    description: Mapped[str | None] = mapped_column(Text)
    # CPV / ДК 021:2015 classification code.
    cpv_code: Mapped[str | None] = mapped_column(String(16))
    quantity: Mapped[decimal.Decimal | None] = mapped_column(Numeric)
    unit: Mapped[str | None] = mapped_column(String(64))

    lot: Mapped[Lot] = relationship(back_populates="items")


class Bid(Base, TimestampMixin):
    """Пропозиція — a supplier's offer on a lot."""

    __tablename__ = "bids"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"))
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT")
    )
    status: Mapped[str | None] = mapped_column(String(64))
    value_amount: Mapped[decimal.Decimal | None] = mapped_column(Money)
    value_currency: Mapped[str | None] = mapped_column(String(3))
    date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    lot: Mapped[Lot] = relationship(back_populates="bids")
    supplier: Mapped[Supplier | None] = relationship(back_populates="bids")


class Award(Base, TimestampMixin):
    """Присудження — the result of evaluating bids on a lot."""

    __tablename__ = "awards"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    lot_id: Mapped[str] = mapped_column(ForeignKey("lots.id", ondelete="RESTRICT"))
    bid_id: Mapped[str | None] = mapped_column(
        ForeignKey("bids.id", ondelete="RESTRICT")
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT")
    )
    status: Mapped[str | None] = mapped_column(String(64))
    value_amount: Mapped[decimal.Decimal | None] = mapped_column(Money)
    value_currency: Mapped[str | None] = mapped_column(String(3))
    date: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))

    lot: Mapped[Lot] = relationship(back_populates="awards")
    bid: Mapped[Bid | None] = relationship()
    supplier: Mapped[Supplier | None] = relationship(back_populates="awards")
    contract: Mapped[Contract | None] = relationship(back_populates="award")


class Contract(Base, TimestampMixin):
    """Договір — a contract concluded on the basis of a successful award (1:1)."""

    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    award_id: Mapped[str] = mapped_column(
        ForeignKey("awards.id", ondelete="RESTRICT"), unique=True
    )
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT")
    )
    status: Mapped[str | None] = mapped_column(String(64))
    value_amount: Mapped[decimal.Decimal | None] = mapped_column(Money)
    value_currency: Mapped[str | None] = mapped_column(String(3))
    date_signed: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    source_modified_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    award: Mapped[Award] = relationship(back_populates="contract")
    supplier: Mapped[Supplier | None] = relationship(back_populates="contracts")


class Complaint(Base, TimestampMixin):
    """Скарга — an appeal against the buyer's actions on a procedure."""

    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    tender_id: Mapped[str] = mapped_column(
        ForeignKey("tenders.id", ondelete="RESTRICT")
    )
    status: Mapped[str | None] = mapped_column(String(64))
    type: Mapped[str | None] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    date_submitted: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    tender: Mapped[Tender] = relationship(back_populates="complaints")
