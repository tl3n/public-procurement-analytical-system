"""Document entity.

A document is an auxiliary entity attached to several parent entities (tender, lot,
bid, complaint). The link is polymorphic — a (related_entity_type, related_entity_id)
pair rather than a set of separate foreign keys — which simplifies
the schema at the cost of declarative referential integrity.
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Document(Base, TimestampMixin):
    """Документ — a file attachment linked polymorphically to a parent entity."""

    __tablename__ = "documents"
    # Index supporting the polymorphic parent lookup.
    __table_args__ = (
        Index("ix_documents_related", "related_entity_type", "related_entity_id"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # Polymorphic link: type in {tender, lot, bid, complaint}, id of that entity.
    related_entity_type: Mapped[str] = mapped_column(String(32))
    related_entity_id: Mapped[str] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str | None] = mapped_column(String(128))
    date_published: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
