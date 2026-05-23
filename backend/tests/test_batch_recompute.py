"""Tests for the batch indicator recompute routine."""

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.analytics.batch import recompute_all
from app.analytics.indicators import registry as global_registry
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

UTC = timezone.utc


def _id(*parts: str) -> str:
    return hashlib.sha256("/".join(parts).encode()).hexdigest()[:32]


async def _seed_three_tenders(session) -> list[str]:
    """Three tenders for one buyer, all with the same single supplier."""
    buyer = ProcuringEntity(edrpou="brbatch", name="Buyer batch")
    session.add(buyer)
    supplier = Supplier(edrpou="srbatch", name="Supplier batch")
    session.add(supplier)
    await session.flush()

    tender_ids: list[str] = []
    base = datetime(2025, 1, 1, tzinfo=UTC)
    for i in range(3):
        tid = _id("batch", str(i))
        tender_ids.append(tid)
        date_pub = base + timedelta(days=i * 30)
        t = Tender(
            id=tid,
            procuring_entity_id=buyer.id,
            procurement_method="open",
            procurement_method_type="aboveThresholdUA",
            status="complete",
            value_amount=Decimal("100"),
            value_currency="UAH",
            date_published=date_pub,
            tender_period_start=date_pub,
            tender_period_end=date_pub + timedelta(days=20),
        )
        session.add(t)
        session.add(
            Lot(
                id=tid,
                tender_id=tid,
                value_amount=Decimal("100"),
                value_currency="UAH",
            )
        )
        await session.flush()
        session.add(Item(id=_id("item", tid), lot_id=tid, cpv_code="79950000-8"))
        aw_id = _id("aw", tid)
        cn_id = _id("ct", tid)
        session.add(
            Award(
                id=aw_id,
                lot_id=tid,
                supplier_id=supplier.id,
                status="active",
                value_amount=Decimal("100"),
                value_currency="UAH",
            )
        )
        await session.flush()
        session.add(
            Contract(
                id=cn_id,
                award_id=aw_id,
                supplier_id=supplier.id,
                status="active",
                value_amount=Decimal("100"),
                value_currency="UAH",
                date_signed=date_pub + timedelta(days=25),
            )
        )
        await session.flush()
    await session.commit()
    return tender_ids


async def _count_rows(session, tender_ids: list[str] | None = None) -> int:
    stmt = select(func.count()).select_from(RiskIndicatorValue)
    if tender_ids is not None:
        stmt = stmt.where(RiskIndicatorValue.tender_id.in_(tender_ids))
    return (await session.execute(stmt)).scalar_one()


async def test_batch_recompute_populates_every_indicator_for_every_tender(
    session,
):
    tender_ids = await _seed_three_tenders(session)
    expected_indicators = len(global_registry.enabled())  # 5

    summary = await recompute_all(session)
    assert summary["tenders_processed"] == len(tender_ids)

    total = await _count_rows(session, tender_ids)
    # Every (tender, indicator) pair produces exactly one row, NULL-valued or not.
    assert total == len(tender_ids) * expected_indicators


async def test_batch_recompute_has_no_duplicate_indicator_rows(session):
    tender_ids = await _seed_three_tenders(session)
    await recompute_all(session)

    rows = (
        await session.execute(
            select(RiskIndicatorValue.tender_id, RiskIndicatorValue.indicator_code)
        )
    ).all()
    pairs = [(r.tender_id, r.indicator_code) for r in rows]
    assert len(pairs) == len(set(pairs))


async def test_batch_recompute_is_idempotent(session):
    tender_ids = await _seed_three_tenders(session)
    await recompute_all(session)
    first_total = await _count_rows(session, tender_ids)

    # A second run must produce the same total — old rows wiped, new rows written.
    await recompute_all(session)
    second_total = await _count_rows(session, tender_ids)

    assert second_total == first_total


async def test_batch_recompute_handles_empty_database(session):
    summary = await recompute_all(session)
    assert summary == {"tenders_processed": 0, "bulk_rows_inserted": 0}
    total = await _count_rows(session)
    assert total == 0


async def test_batch_recompute_replaces_stale_rows(session):
    """Pre-existing risk_indicator_values for a known indicator must be replaced."""
    tender_ids = await _seed_three_tenders(session)
    # Seed a deliberately wrong prior row for one of the active indicators.
    session.add(
        RiskIndicatorValue(
            tender_id=tender_ids[0],
            indicator_code="risk.non_competitive",
            value_boolean=True,  # stale — the tender is aboveThresholdUA.
        )
    )
    await session.commit()

    await recompute_all(session)
    row = (
        await session.execute(
            select(RiskIndicatorValue).where(
                RiskIndicatorValue.tender_id == tender_ids[0],
                RiskIndicatorValue.indicator_code == "risk.non_competitive",
            )
        )
    ).scalar_one()
    # The stale True is gone; replaced with the correct False.
    assert row.value_boolean is False
