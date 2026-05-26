"""Tests for the Prozorro feed crawler."""

import httpx

from app.collector import crawler
from app.models.sync import SyncState

# Three logical pages: two with records, then an empty page that ends the walk.
PAGES: dict[str, dict] = {
    "p0": {
        "data": [
            {"id": "t1", "dateModified": "2025-01-01T00:00:00+00:00"},
            {"id": "t2", "dateModified": "2025-01-01T00:01:00+00:00"},
        ],
        "next_page": {"offset": "p1"},
    },
    "p1": {
        "data": [
            {"id": "t3", "dateModified": "2025-01-01T00:02:00+00:00"},
            {"id": "t4", "dateModified": "2025-01-01T00:03:00+00:00"},
        ],
        "next_page": {"offset": "p2"},
    },
    "p2": {"data": [], "next_page": {"offset": "p3"}},
}


def _make_handler(call_log: list[str]):
    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params.get("offset") or "p0"
        call_log.append(offset)
        return httpx.Response(200, json=PAGES.get(offset, {"data": []}))

    return handler


async def test_walks_all_pages_and_stops_on_empty(session):
    calls: list[str] = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_make_handler(calls))
    ) as client:
        records = [
            r
            async for r in crawler.crawl(
                client,
                session,
                base_url="https://example.test/api",
                initial_offset="p0",
            )
        ]

    # All non-empty pages yielded; empty page ended the walk.
    assert [r["id"] for r in records] == ["t1", "t2", "t3", "t4"]
    assert calls == ["p0", "p1", "p2"]


async def test_offset_is_persisted_to_sync_state(session):
    calls: list[str] = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_make_handler(calls))
    ) as client:
        async for _ in crawler.crawl(
            client,
            session,
            base_url="https://example.test/api",
            initial_offset="p0",
        ):
            pass

    # After the last non-empty page (p1 → response carrying next="p2"),
    # the offset stored is "p2"; reaching the empty page does not advance it.
    state = await session.get(SyncState, "tenders")
    assert state is not None
    assert state.last_offset == "p2"
    assert state.last_synced_at is not None


async def test_resumes_from_stored_offset(session):
    # Seed an existing sync_state — crawler must skip page 0 entirely.
    session.add(SyncState(feed_name="tenders", last_offset="p1"))
    await session.commit()

    calls: list[str] = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_make_handler(calls))
    ) as client:
        records = [
            r
            async for r in crawler.crawl(
                client,
                session,
                base_url="https://example.test/api",
                initial_offset="p0",
            )
        ]

    assert [r["id"] for r in records] == ["t3", "t4"]
    assert calls == ["p1", "p2"]


async def test_max_records_cap_stops_walk(session):
    calls: list[str] = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_make_handler(calls))
    ) as client:
        records = [
            r
            async for r in crawler.crawl(
                client,
                session,
                base_url="https://example.test/api",
                initial_offset="p0",
                max_records=2,
            )
        ]

    # After the first page yields 2 records the cap is reached — no further fetch.
    assert [r["id"] for r in records] == ["t1", "t2"]
    assert calls == ["p0"]


async def test_cap_smaller_than_page_size_is_exact(session):
    """The cap must stop yielding mid-page, not after consuming a full page."""
    calls: list[str] = []
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(_make_handler(calls))
    ) as client:
        records = [
            r
            async for r in crawler.crawl(
                client,
                session,
                base_url="https://example.test/api",
                initial_offset="p0",
                max_records=1,
            )
        ]

    # Exactly one record yielded — not the whole first page.
    assert [r["id"] for r in records] == ["t1"]
    assert calls == ["p0"]

    # The offset was not advanced past the page we partially consumed, so a
    # follow-up run would reprocess it (safe under idempotent persistence).
    state = await session.get(SyncState, "tenders")
    assert state is not None
    assert state.last_offset == "p0"


# --- Monthly stratified mode ----------------------------------------------


async def test_crawl_monthly_stops_at_quota_and_advances(session):
    """A 3-month feed with quota=2 must yield 2 records per month, then end."""
    # Three months, each with three records. dateModified inside each month
    # must monotonically increase and stay within the month range so the
    # boundary detection sees crossings exactly at the month border.
    pages_by_offset: dict[str, dict] = {}

    def _record(rid: str, dm: str) -> dict:
        return {"id": rid, "dateModified": dm}

    pages_by_offset["1767225600"] = {
        # 2026-01-01 onward
        "data": [
            _record("jan-1", "2026-01-02T00:00:00+00:00"),
            _record("jan-2", "2026-01-10T00:00:00+00:00"),
            _record("jan-3", "2026-01-25T00:00:00+00:00"),
            _record("feb-1", "2026-02-01T05:00:00+00:00"),
        ],
        "next_page": {"offset": "after-jan"},
    }
    pages_by_offset["1769904000"] = {
        # 2026-02-01 onward
        "data": [
            _record("feb-1", "2026-02-01T05:00:00+00:00"),
            _record("feb-2", "2026-02-10T00:00:00+00:00"),
            _record("feb-3", "2026-02-25T00:00:00+00:00"),
            _record("mar-1", "2026-03-01T05:00:00+00:00"),
        ],
        "next_page": {"offset": "after-feb"},
    }
    pages_by_offset["1772323200"] = {
        # 2026-03-01 onward
        "data": [
            _record("mar-1", "2026-03-01T05:00:00+00:00"),
            _record("mar-2", "2026-03-15T00:00:00+00:00"),
            _record("mar-3", "2026-03-28T00:00:00+00:00"),
        ],
        "next_page": {"offset": "after-mar"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params.get("offset") or ""
        return httpx.Response(
            200, json=pages_by_offset.get(offset, {"data": []})
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        records = [
            r
            async for r in crawler.crawl_monthly(
                client,
                session,
                start_year_month="2026-01",
                end_year_month="2026-03",
                quota_per_month=2,
                base_url="https://example.test/api",
            )
        ]

    # Exactly 2 records per month, in order, no cross-month bleed.
    assert [r["id"] for r in records] == [
        "jan-1", "jan-2",
        "feb-1", "feb-2",
        "mar-1", "mar-2",
    ]
    # Each month's sync_state row marked complete.
    for ym in ("2026-01", "2026-02", "2026-03"):
        state = await session.get(SyncState, f"tenders:{ym}")
        assert state is not None
        assert state.last_offset == "COMPLETE"
