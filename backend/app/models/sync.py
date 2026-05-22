"""Synchronization state entity.

sync_state is a service table holding the feed cursor for the collector.
It has one row per API feed and lets the collector
resume from its last position after a restart.
"""

from __future__ import annotations

import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SyncState(Base, TimestampMixin):
    """Стан синхронізації — the last processed feed offset for one API feed."""

    __tablename__ = "sync_state"

    # Feed name is the natural key, e.g. "tenders".
    feed_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    last_offset: Mapped[str | None] = mapped_column(Text)
    last_synced_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
