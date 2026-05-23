"""Prozorro feed crawler.

Walks the tenders feed page by page, persisting the pagination offset after each
successfully processed page so that the next run resumes from exactly where this one
stopped. On the very first run, when ``sync_state`` has no row for the feed, the
crawler seeds the offset with the configured initial-load timestamp — the Prozorro
feed cursor accepts a bare Unix timestamp, which is the cleanest way to start the
walk at the beginning of 2025 without scanning the full historical archive.

The yielded records are the summary objects returned by the feed (``id`` and
``dateModified``). Fetching the full tender detail and persisting it to the database
is the responsibility of the normalizer module (commit 7).
"""

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.http_client import http_get_with_retry
from app.collector.normalizer import persist_tender
from app.config import settings
from app.models.sync import SyncState

log = logging.getLogger(__name__)


async def _get_or_create_sync_state(
    session: AsyncSession, feed_name: str, initial_offset: str
) -> SyncState:
    state = await session.get(SyncState, feed_name)
    if state is None:
        state = SyncState(feed_name=feed_name, last_offset=initial_offset)
        session.add(state)
        await session.flush()
    return state


async def crawl(
    client: httpx.AsyncClient,
    session: AsyncSession,
    *,
    feed_name: str = "tenders",
    base_url: str | None = None,
    initial_offset: str | None = None,
    max_records: int | None = None,
) -> AsyncIterator[dict]:
    """Yield feed summary records, persisting the offset after each page.

    Parameters mirror the configuration but can be overridden for tests.
    Yields one dict per record — typically ``{"id": ..., "dateModified": ...}``.
    """
    base_url = (base_url or settings.prozorro_api_url).rstrip("/") + f"/{feed_name}"
    initial_offset = initial_offset or str(settings.initial_load_start_timestamp)
    if max_records is None:
        max_records = settings.max_tenders

    state = await _get_or_create_sync_state(session, feed_name, initial_offset)
    offset = state.last_offset or initial_offset

    yielded = 0
    while True:
        response = await http_get_with_retry(
            client, base_url, params={"offset": offset}
        )
        payload = response.json()
        data = payload.get("data") or []
        if not data:
            # Empty page signals end of feed (for a periodic sync, this means
            # "caught up"; the next scheduled run will resume from `offset`).
            break

        hit_cap = False
        for record in data:
            yield record
            yielded += 1
            # A zero cap means "unlimited"; otherwise stop as soon as it is reached.
            if max_records and yielded >= max_records:
                hit_cap = True
                break

        if hit_cap:
            # Stop without advancing the stored offset: the next run reprocesses
            # this page, which is harmless because the normalizer is idempotent.
            break

        next_offset = (payload.get("next_page") or {}).get("offset")
        if next_offset:
            state.last_offset = next_offset
        state.last_synced_at = datetime.now(tz=UTC)
        await session.commit()

        if not next_offset:
            break
        offset = next_offset


async def run_sync(
    client: httpx.AsyncClient,
    session: AsyncSession,
    *,
    feed_name: str = "tenders",
    base_url: str | None = None,
    initial_offset: str | None = None,
    max_records: int | None = None,
) -> dict[str, int]:
    """Walk the feed, fetch each tender's detail, and persist it.

    Errors on a single record are logged and skipped so that one bad record
    cannot stop the whole sync. The pagination offset is still advanced
    (skipped records are not retried automatically — the next emission of the
    same id during a subsequent ``dateModified`` change will pick them up).

    Returns a small summary dict for the caller (the scheduler) to log.
    """
    resolved_base = (base_url or settings.prozorro_api_url).rstrip("/")
    detail_base = f"{resolved_base}/{feed_name}"

    processed = 0
    failed = 0
    async for summary in crawl(
        client,
        session,
        feed_name=feed_name,
        base_url=base_url,
        initial_offset=initial_offset,
        max_records=max_records,
    ):
        tender_id = summary["id"]
        try:
            response = await http_get_with_retry(
                client, f"{detail_base}/{tender_id}"
            )
            data = response.json().get("data") or {}
            await persist_tender(session, data)
            await session.commit()
            processed += 1
        except Exception as exc:
            # One bad record must not abort the whole sync.
            await session.rollback()
            failed += 1
            log.warning("skipping tender %s: %s", tender_id, exc)

    return {"processed": processed, "failed": failed}
