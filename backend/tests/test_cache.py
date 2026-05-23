"""Tests for the Redis caching layer applied to aggregation endpoints."""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from redis.asyncio import Redis

from app.cache import Cache, get_cache
from app.config import settings
from app.db import get_session
from app.main import app
from app.models import Lot, ProcuringEntity, Tender

UTC = timezone.utc


def _id(*parts: str) -> str:
    return hashlib.sha256("/".join(parts).encode()).hexdigest()[:32]


# --- Fixtures --------------------------------------------------------------


@pytest_asyncio.fixture(autouse=True)
async def _flush_cache():
    """Wipe Redis before every test so cache state never leaks across cases."""
    try:
        r = Redis.from_url(settings.redis_url, decode_responses=True)
        await r.flushdb()
        await r.aclose()
    except Exception:
        # No Redis available — tests that depend on cache hits will detect that.
        pass
    yield


@pytest_asyncio.fixture
async def client(session):
    async def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _make_buyer(session, key: str) -> ProcuringEntity:
    pe = ProcuringEntity(edrpou=key, name=f"Buyer {key}", region="Київ")
    session.add(pe)
    await session.flush()
    return pe


async def _add_tender(session, *, key: str, buyer, date_pub: datetime, value: Decimal):
    tid = _id("cache", key)
    t = Tender(
        id=tid,
        procuring_entity_id=buyer.id,
        procurement_method="open",
        procurement_method_type="aboveThresholdUA",
        status="complete",
        value_amount=value,
        value_currency="UAH",
        date_published=date_pub,
    )
    session.add(t)
    session.add(Lot(id=tid, tender_id=tid, value_amount=value, value_currency="UAH"))
    await session.flush()
    return t


# --- Tests ----------------------------------------------------------------


async def test_dashboard_serves_cached_value_on_repeat_request(client, session):
    """An identical second request must return the cached body, not refetch."""
    buyer = await _make_buyer(session, "c1")
    await _add_tender(
        session, key="t1", buyer=buyer,
        date_pub=datetime(2025, 1, 1, tzinfo=UTC), value=Decimal("100"),
    )
    await session.commit()

    r1 = await client.get("/dashboard")
    assert r1.status_code == 200
    snapshot = r1.json()
    assert snapshot["kpis"]["total_tenders"] == 1

    # Slip an additional tender past the cache (no invalidation here).
    await _add_tender(
        session, key="t2", buyer=buyer,
        date_pub=datetime(2025, 1, 2, tzinfo=UTC), value=Decimal("200"),
    )
    await session.commit()

    r2 = await client.get("/dashboard")
    # The new tender is not reflected — second request was served from cache.
    assert r2.json()["kpis"]["total_tenders"] == snapshot["kpis"]["total_tenders"]


async def test_recompute_invalidates_aggregation_cache(client, session):
    """After /admin/recompute, the next request must re-read fresh data."""
    buyer = await _make_buyer(session, "c2")
    await _add_tender(
        session, key="t1", buyer=buyer,
        date_pub=datetime(2025, 1, 1, tzinfo=UTC), value=Decimal("100"),
    )
    await session.commit()

    first = (await client.get("/dashboard")).json()
    assert first["kpis"]["total_tenders"] == 1

    await _add_tender(
        session, key="t2", buyer=buyer,
        date_pub=datetime(2025, 1, 2, tzinfo=UTC), value=Decimal("200"),
    )
    await session.commit()

    recompute = await client.post("/admin/recompute")
    assert recompute.status_code == 200

    second = (await client.get("/dashboard")).json()
    assert second["kpis"]["total_tenders"] == 2  # cache wiped — fresh count


async def test_rankings_endpoint_is_cached(client, session):
    buyer = await _make_buyer(session, "c3")
    await _add_tender(
        session, key="t1", buyer=buyer,
        date_pub=datetime(2025, 1, 1, tzinfo=UTC), value=Decimal("100"),
    )
    await session.commit()

    snapshot = (await client.get("/statistics/rankings")).json()

    # Add a tender; without explicit invalidation the cached snapshot stands.
    await _add_tender(
        session, key="t2", buyer=buyer,
        date_pub=datetime(2025, 1, 2, tzinfo=UTC), value=Decimal("999"),
    )
    await session.commit()

    second = (await client.get("/statistics/rankings")).json()
    assert second == snapshot


async def test_endpoint_works_when_cache_is_unavailable(client, session):
    """Override get_cache with a disabled Cache → endpoint still serves data."""
    buyer = await _make_buyer(session, "c4")
    await _add_tender(
        session, key="t1", buyer=buyer,
        date_pub=datetime(2025, 1, 1, tzinfo=UTC), value=Decimal("100"),
    )
    await session.commit()

    async def _no_cache():
        yield Cache(redis=None, ttl_seconds=60)

    app.dependency_overrides[get_cache] = _no_cache
    try:
        r1 = await client.get("/dashboard")
        # Now with no cache an additional tender must be visible immediately.
        await _add_tender(
            session, key="t2", buyer=buyer,
            date_pub=datetime(2025, 1, 2, tzinfo=UTC), value=Decimal("200"),
        )
        await session.commit()
        r2 = await client.get("/dashboard")
    finally:
        del app.dependency_overrides[get_cache]

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["kpis"]["total_tenders"] == 1
    assert r2.json()["kpis"]["total_tenders"] == 2  # no cache → live read


async def test_cache_class_is_no_op_when_redis_is_none():
    cache = Cache(redis=None, ttl_seconds=60)
    assert not cache.enabled
    assert await cache.get_json("anything") is None
    await cache.set_json("anything", {"a": 1})  # must not raise
    assert await cache.invalidate_all() == 0
