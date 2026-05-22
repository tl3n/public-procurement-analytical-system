"""Risk indicator value entity.

A risk indicator value is a derived entity produced by the analytics module.
It is system-generated, hence a UUID primary key, and is
deleted together with its parent tender on re-load — its foreign key therefore uses
ON DELETE CASCADE (design.md §2.4.2).
"""

from __future__ import annotations

import datetime
import decimal
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tenders import Tender


class RiskIndicatorValue(Base, TimestampMixin):
    """Значення індикатора ризику — a computed indicator result for one tender."""

    __tablename__ = "risk_indicator_values"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    tender_id: Mapped[str] = mapped_column(
        ForeignKey("tenders.id", ondelete="CASCADE")
    )
    indicator_code: Mapped[str] = mapped_column(String(64))
    # A boolean indicator (NULL = cannot be computed yet) or a numeric one.
    value_boolean: Mapped[bool | None] = mapped_column()
    value_numeric: Mapped[decimal.Decimal | None] = mapped_column(Numeric)
    computed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    tender: Mapped[Tender] = relationship(back_populates="risk_indicator_values")
