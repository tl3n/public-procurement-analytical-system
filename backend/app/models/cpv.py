"""CPV classification entity.

The CPV / ДК 021:2015 classifier is hierarchical: a higher-level code is the parent
of more specific codes. The hierarchy is modelled as a self-reference through
parent_code. The CPV code itself is the natural primary key.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class CpvClassification(Base, TimestampMixin):
    """Довідник CPV — a node of the ДК 021:2015 classification tree."""

    __tablename__ = "cpv_classification"
    __table_args__ = (Index("ix_cpv_classification_parent_code", "parent_code"),)

    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    parent_code: Mapped[str | None] = mapped_column(
        ForeignKey("cpv_classification.code", ondelete="RESTRICT")
    )
    description: Mapped[str | None] = mapped_column(Text)

    parent: Mapped[CpvClassification | None] = relationship(
        back_populates="children", remote_side=[code]
    )
    children: Mapped[list[CpvClassification]] = relationship(
        back_populates="parent"
    )
