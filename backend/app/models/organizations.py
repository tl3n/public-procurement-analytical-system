"""Organization entities — procuring entities (buyers) and suppliers.

Both are system-generated entities: they are identified by ЄДРПОУ
and reused across many tenders, so they receive internal UUID primary keys.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenders import Award, Bid, Contract, Tender


class ProcuringEntity(Base, TimestampMixin):
    """Замовник — a buyer that initiates procurement procedures."""

    __tablename__ = "procuring_entities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    edrpou: Mapped[str | None] = mapped_column(String(16), unique=True)
    name: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(128))
    address: Mapped[str | None] = mapped_column(Text)

    tenders: Mapped[list[Tender]] = relationship(back_populates="procuring_entity")


class Supplier(Base, TimestampMixin):
    """Учасник — a supplier that submits bids on procedures."""

    __tablename__ = "suppliers"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    edrpou: Mapped[str | None] = mapped_column(String(16), unique=True)
    name: Mapped[str | None] = mapped_column(Text)

    bids: Mapped[list[Bid]] = relationship(back_populates="supplier")
    awards: Mapped[list[Award]] = relationship(back_populates="supplier")
    contracts: Mapped[list[Contract]] = relationship(back_populates="supplier")
