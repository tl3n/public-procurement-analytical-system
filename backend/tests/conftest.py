"""Shared pytest fixtures.

Tests that need database access depend on ``session``. The fixture rebuilds the
schema from the ORM models for every test so cases stay isolated. Tests that do not
declare a ``session`` argument do not pay this cost.

``seeded`` builds a small heterogeneous dataset (2 buyers, 2 suppliers, 4 tenders,
1 contract, 3 risk-indicator rows) used by API and aggregation tests.
"""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.models import (
    Award,
    Contract,
    Item,
    Lot,
    ProcuringEntity,
    RiskIndicatorValue,
    Supplier,
    Tender,
)
from app.models.base import Base

UTC = timezone.utc


def _id(*parts: str) -> str:
    return hashlib.sha256("/".join(parts).encode()).hexdigest()[:32]


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(settings.database_url)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield eng
    finally:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as s:
        yield s


@pytest_asyncio.fixture
async def seeded(session) -> dict:
    """Small dataset shared by API and aggregation tests.

    Layout:
      * Buyers: Kyiv (3 tenders) and Lviv (1 tender).
      * Tenders: t.k1 / t.k2 / t.k3 / t.l1 spanning Jan–Mar 2026, two CPV codes.
      * Contracts: one on t.l1 to supplier-a (400 UAH).
      * Risk values: single_bidding=True on k1, non_competitive=False on k1 and
        =True on k3 (so 2 distinct high-risk tenders for the share metric).
    """
    kyiv = ProcuringEntity(edrpou="buy-kyiv", name="Buyer Kyiv", region="Київ")
    lviv = ProcuringEntity(
        edrpou="buy-lviv", name="Buyer Lviv", region="Львівська область"
    )
    session.add_all([kyiv, lviv])
    sup_a = Supplier(edrpou="sup-a", name="Supplier A")
    sup_b = Supplier(edrpou="sup-b", name="Supplier B")
    session.add_all([sup_a, sup_b])
    await session.flush()

    tenders: dict[str, Tender] = {}

    def make_tender(key, buyer, *, type_, status, value, dp, cpv=None):
        tid = _id("seeded", key)
        t = Tender(
            id=tid,
            procuring_entity_id=buyer.id,
            procurement_method="open",
            procurement_method_type=type_,
            status=status,
            value_amount=value,
            value_currency="UAH",
            date_published=dp,
            title=f"Tender {key}",
        )
        session.add(t)
        session.add(
            Lot(id=tid, tender_id=tid, value_amount=value, value_currency="UAH")
        )
        tenders[key] = t
        if cpv:
            session.add(Item(id=_id("item", tid), lot_id=tid, cpv_code=cpv))
        return t

    make_tender(
        "k1", kyiv,
        type_="aboveThresholdUA", status="complete",
        value=Decimal("100"), dp=datetime(2026, 1, 10, tzinfo=UTC),
        cpv="79950000-8",
    )
    make_tender(
        "k2", kyiv,
        type_="aboveThresholdUA", status="active.tendering",
        value=Decimal("250"), dp=datetime(2026, 2, 15, tzinfo=UTC),
        cpv="79950000-8",
    )
    make_tender(
        "k3", kyiv,
        type_="negotiation", status="complete",
        value=Decimal("80"), dp=datetime(2026, 2, 20, tzinfo=UTC),
        cpv="33100000-1",
    )
    make_tender(
        "l1", lviv,
        type_="aboveThresholdUA", status="complete",
        value=Decimal("400"), dp=datetime(2026, 3, 5, tzinfo=UTC),
        cpv="33100000-1",
    )
    await session.flush()

    aw_id = _id("aw", tenders["l1"].id)
    cn_id = _id("ct", tenders["l1"].id)
    session.add(
        Award(
            id=aw_id,
            lot_id=tenders["l1"].id,
            supplier_id=sup_a.id,
            status="active",
            value_amount=Decimal("400"),
        )
    )
    await session.flush()
    session.add(
        Contract(
            id=cn_id,
            award_id=aw_id,
            supplier_id=sup_a.id,
            status="active",
            value_amount=Decimal("400"),
            value_currency="UAH",
            date_signed=datetime(2026, 3, 7, tzinfo=UTC),
        )
    )
    session.add_all(
        [
            RiskIndicatorValue(
                tender_id=tenders["k1"].id,
                indicator_code="risk.single_bidding",
                value_boolean=True,
            ),
            RiskIndicatorValue(
                tender_id=tenders["k1"].id,
                indicator_code="risk.non_competitive",
                value_boolean=False,
            ),
            RiskIndicatorValue(
                tender_id=tenders["k3"].id,
                indicator_code="risk.non_competitive",
                value_boolean=True,
            ),
        ]
    )
    await session.commit()
    return {
        "kyiv": kyiv,
        "lviv": lviv,
        "sup_a": sup_a,
        "sup_b": sup_b,
        "tenders": tenders,
    }
