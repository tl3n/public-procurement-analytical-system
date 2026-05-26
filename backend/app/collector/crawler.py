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
from datetime import UTC, date, datetime

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.http_client import http_get_with_retry
from app.collector.normalizer import persist_tender
from app.config import settings
from app.models import Tender
from app.models.sync import SyncState

log = logging.getLogger(__name__)

# Sentinel value persisted into ``sync_state.last_offset`` to mark a month as
# fully collected. Distinct from any real API offset, which is always either a
# bare numeric timestamp or a 4-segment cursor string.
_MONTH_COMPLETE = "COMPLETE"


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


# --- Monthly stratified mode ----------------------------------------------


def _parse_year_month(s: str) -> date:
    """Parse ``"YYYY-MM"`` into the first day of that month."""
    year, month = s.split("-")
    return date(int(year), int(month), 1)


def _next_month(d: date) -> date:
    return date(d.year + 1, 1, 1) if d.month == 12 else date(d.year, d.month + 1, 1)


def _current_month() -> date:
    today = datetime.now(tz=UTC).date()
    return date(today.year, today.month, 1)


def _month_bounds_ts(month: date) -> tuple[int, int]:
    """Return (start_ts, next_month_start_ts) as Unix timestamps."""
    start = datetime(month.year, month.month, 1, tzinfo=UTC)
    end = datetime.combine(_next_month(month), datetime.min.time(), tzinfo=UTC)
    return int(start.timestamp()), int(end.timestamp())


def _month_key(feed_name: str, month: date) -> str:
    return f"{feed_name}:{month.year:04d}-{month.month:02d}"


async def _count_records_in_month(session: AsyncSession, month: date) -> int:
    """Count tenders already persisted whose dateModified falls in ``month``.

    Used by ``crawl_monthly`` to honor the cumulative-per-month quota across
    scheduler cycles without storing the count in a dedicated column.
    """
    start = datetime(month.year, month.month, 1, tzinfo=UTC)
    end = datetime.combine(_next_month(month), datetime.min.time(), tzinfo=UTC)
    result = await session.execute(
        select(func.count())
        .select_from(Tender)
        .where(Tender.source_modified_at >= start)
        .where(Tender.source_modified_at < end)
    )
    return int(result.scalar_one())


async def crawl_monthly(
    client: httpx.AsyncClient,
    session: AsyncSession,
    *,
    start_year_month: str | None = None,
    end_year_month: str | None = None,
    quota_per_month: int | None = None,
    base_url: str | None = None,
    feed_name: str = "tenders",
    max_pages_per_cycle: int = 100,
) -> AsyncIterator[dict]:
    """Walk the feed by calendar month, yielding up to a per-month quota.

    Persists one ``sync_state`` row per month (``tenders:YYYY-MM``). Per cycle
    the function processes at most ``max_pages_per_cycle`` pages so that one
    scheduler tick has a bounded runtime; subsequent cycles pick up where the
    previous one stopped.
    """
    start = _parse_year_month(start_year_month or settings.monthly_start_year_month)
    end = (
        _parse_year_month(end_year_month)
        if end_year_month
        else (
            _parse_year_month(settings.monthly_end_year_month)
            if settings.monthly_end_year_month
            else _current_month()
        )
    )
    quota = quota_per_month if quota_per_month is not None else settings.monthly_quota
    base_url_resolved = (base_url or settings.prozorro_api_url).rstrip("/") + f"/{feed_name}"

    pages_done = 0
    current = start
    while current <= end and pages_done < max_pages_per_cycle:
        month_key = _month_key(feed_name, current)
        state = await session.get(SyncState, month_key)
        if state and state.last_offset == _MONTH_COMPLETE:
            current = _next_month(current)
            continue

        start_ts, end_ts = _month_bounds_ts(current)
        offset = state.last_offset if state and state.last_offset else str(start_ts)
        # Honor cumulative quota across cycles by counting what we already have.
        collected = await _count_records_in_month(session, current)

        month_finished = False
        while collected < quota and pages_done < max_pages_per_cycle:
            response = await http_get_with_retry(
                client, base_url_resolved, params={"offset": offset}
            )
            payload = response.json()
            data = payload.get("data") or []
            pages_done += 1

            if not data:
                # Out of records before quota — month is effectively done.
                month_finished = True
                break

            crossed_month_boundary = False
            for record in data:
                # Stop as soon as a record's dateModified leaves this month —
                # the feed is sorted ascending by dateModified.
                date_mod = record.get("dateModified")
                if date_mod:
                    try:
                        dm = datetime.fromisoformat(
                            date_mod.replace("Z", "+00:00")
                        )
                        if dm.timestamp() >= end_ts:
                            crossed_month_boundary = True
                            break
                    except (ValueError, TypeError):
                        pass
                yield record
                collected += 1
                if collected >= quota:
                    break

            if crossed_month_boundary or collected >= quota:
                month_finished = True
                break

            next_offset = (payload.get("next_page") or {}).get("offset")
            if not next_offset:
                month_finished = True
                break

            # Persist offset progress so the next cycle resumes mid-month.
            state = await _upsert_state(session, month_key, next_offset)
            offset = next_offset

        if month_finished:
            await _upsert_state(session, month_key, _MONTH_COMPLETE)
            current = _next_month(current)
        else:
            # Pages budget exhausted for this cycle — pause here and resume
            # on the next scheduler tick from the persisted offset.
            break


async def _upsert_state(
    session: AsyncSession, feed_name: str, last_offset: str
) -> SyncState:
    state = await session.get(SyncState, feed_name)
    if state is None:
        state = SyncState(feed_name=feed_name, last_offset=last_offset)
        session.add(state)
    else:
        state.last_offset = last_offset
    state.last_synced_at = datetime.now(tz=UTC)
    await session.commit()
    return state


async def run_sync_monthly(
    client: httpx.AsyncClient,
    session: AsyncSession,
    *,
    start_year_month: str | None = None,
    end_year_month: str | None = None,
    quota_per_month: int | None = None,
    base_url: str | None = None,
    feed_name: str = "tenders",
    max_pages_per_cycle: int = 100,
) -> dict[str, int]:
    """High-level orchestrator for the monthly stratified mode.

    Drives ``crawl_monthly`` and persists each fetched tender via the
    normalizer, with the same per-record try/except as ``run_sync``.
    """
    resolved_base = (base_url or settings.prozorro_api_url).rstrip("/")
    detail_base = f"{resolved_base}/{feed_name}"

    processed = 0
    failed = 0
    async for summary in crawl_monthly(
        client,
        session,
        start_year_month=start_year_month,
        end_year_month=end_year_month,
        quota_per_month=quota_per_month,
        base_url=base_url,
        feed_name=feed_name,
        max_pages_per_cycle=max_pages_per_cycle,
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
            await session.rollback()
            failed += 1
            log.warning("skipping tender %s: %s", tender_id, exc)

    return {"processed": processed, "failed": failed}
