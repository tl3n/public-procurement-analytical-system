"""Tests for SQL-backed aggregations on a small seeded dataset."""

import hashlib
from datetime import datetime, timezone
from decimal import Decimal

from app.analytics import aggregations
from app.models import (
    Award,
    Bid,
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


async def _make_buyer(session, key: str, region: str) -> ProcuringEntity:
    pe = ProcuringEntity(edrpou=key, name=f"Buyer-{key}", region=region)
    session.add(pe)
    await session.flush()
    return pe


async def _make_supplier(session, key: str) -> Supplier:
    s = Supplier(edrpou=key, name=f"Supplier-{key}")
    session.add(s)
    await session.flush()
    return s


async def _make_tender(
    session,
    *,
    tid: str,
    buyer: ProcuringEntity,
    type_: str,
    date_pub: datetime,
    value: Decimal,
    cpv: str | None = None,
) -> Tender:
    tender = Tender(
        id=tid,
        procuring_entity_id=buyer.id,
        procurement_method="open",
        procurement_method_type=type_,
        status="complete",
        value_amount=value,
        value_currency="UAH",
        date_published=date_pub,
    )
    session.add(tender)
    session.add(Lot(id=tid, tender_id=tid, value_amount=value, value_currency="UAH"))
    await session.flush()
    if cpv:
        session.add(Item(id=_id("item", tid), lot_id=tid, cpv_code=cpv))
        await session.flush()
    return tender


async def _add_contract(
    session,
    *,
    tender: Tender,
    supplier: Supplier,
    value: Decimal,
    date_signed: datetime,
) -> Contract:
    aw_id = _id("aw", tender.id, supplier.edrpou or "")
    cn_id = _id("ct", tender.id, supplier.edrpou or "")
    session.add(
        Award(
            id=aw_id,
            lot_id=tender.id,
            supplier_id=supplier.id,
            status="active",
            value_amount=value,
        )
    )
    await session.flush()
    contract = Contract(
        id=cn_id,
        award_id=aw_id,
        supplier_id=supplier.id,
        status="active",
        value_amount=value,
        value_currency="UAH",
        date_signed=date_signed,
    )
    session.add(contract)
    await session.flush()
    return contract


async def _seed(session):
    """A small but heterogeneous dataset returned as a context bundle."""
    buyer_kyiv = await _make_buyer(session, "buy-kyiv", "Київ")
    buyer_lviv = await _make_buyer(session, "buy-lviv", "Львівська область")
    sup_a = await _make_supplier(session, "sup-a")
    sup_b = await _make_supplier(session, "sup-b")

    # Buyer Kyiv has two open tenders and one negotiation, Lviv has one open.
    t1 = await _make_tender(
        session,
        tid=_id("t1"),
        buyer=buyer_kyiv,
        type_="open",
        date_pub=datetime(2025, 1, 10, tzinfo=UTC),
        value=Decimal("100"),
        cpv="79950000-8",
    )
    t2 = await _make_tender(
        session,
        tid=_id("t2"),
        buyer=buyer_kyiv,
        type_="open",
        date_pub=datetime(2025, 2, 15, tzinfo=UTC),
        value=Decimal("250"),
        cpv="79950000-8",
    )
    t3 = await _make_tender(
        session,
        tid=_id("t3"),
        buyer=buyer_kyiv,
        type_="negotiation",
        date_pub=datetime(2025, 2, 20, tzinfo=UTC),
        value=Decimal("80"),
        cpv="33100000-1",
    )
    t4 = await _make_tender(
        session,
        tid=_id("t4"),
        buyer=buyer_lviv,
        type_="open",
        date_pub=datetime(2025, 3, 5, tzinfo=UTC),
        value=Decimal("400"),
        cpv="33100000-1",
    )

    # Three contracts: A wins twice (Kyiv & Lviv), B wins once.
    await _add_contract(
        session,
        tender=t1,
        supplier=sup_a,
        value=Decimal("100"),
        date_signed=datetime(2025, 1, 12, tzinfo=UTC),
    )
    await _add_contract(
        session,
        tender=t2,
        supplier=sup_b,
        value=Decimal("250"),
        date_signed=datetime(2025, 2, 18, tzinfo=UTC),
    )
    await _add_contract(
        session,
        tender=t4,
        supplier=sup_a,
        value=Decimal("400"),
        date_signed=datetime(2025, 3, 7, tzinfo=UTC),
    )

    # Two tenders flagged as high-risk on one indicator.
    session.add(
        RiskIndicatorValue(
            tender_id=t3.id,
            indicator_code="risk.non_competitive",
            value_boolean=True,
        )
    )
    session.add(
        RiskIndicatorValue(
            tender_id=t1.id,
            indicator_code="risk.single_bidding",
            value_boolean=True,
        )
    )
    await session.commit()
    return {
        "buyer_kyiv": buyer_kyiv,
        "buyer_lviv": buyer_lviv,
        "sup_a": sup_a,
        "sup_b": sup_b,
        "t1": t1,
        "t2": t2,
        "t3": t3,
        "t4": t4,
    }


# --- Distributions ----------------------------------------------------------


async def test_distribution_by_procurement_type(session):
    await _seed(session)
    buckets = await aggregations.distribution_by_procurement_type(session)
    by_label = {b.label: b for b in buckets}
    assert by_label["open"].tender_count == 3
    assert by_label["negotiation"].tender_count == 1
    assert by_label["open"].total_value == Decimal("750")


async def test_distribution_by_region(session):
    await _seed(session)
    buckets = await aggregations.distribution_by_region(session)
    by_label = {b.label: b for b in buckets}
    assert by_label["Київ"].tender_count == 3
    assert by_label["Львівська область"].tender_count == 1


async def test_distribution_by_cpv_dedupes_tenders(session):
    await _seed(session)
    buckets = await aggregations.distribution_by_cpv(session)
    by_label = {b.label: b for b in buckets}
    # Two tenders carry "79950000-8", two carry "33100000-1".
    assert by_label["79950000-8"].tender_count == 2
    assert by_label["33100000-1"].tender_count == 2


async def test_distribution_respects_time_window(session):
    await _seed(session)
    buckets = await aggregations.distribution_by_procurement_type(
        session,
        since=datetime(2025, 2, 1, tzinfo=UTC),
    )
    by_label = {b.label: b for b in buckets}
    # Only February+March tenders fall in the window — three records.
    assert sum(b.tender_count for b in buckets) == 3
    assert by_label["open"].tender_count == 2


# --- Time series ------------------------------------------------------------


async def test_procurement_volume_monthly(session):
    await _seed(session)
    points = await aggregations.procurement_volume_over_time(
        session, granularity="month"
    )
    counts_by_month = {p.period.month: p.tender_count for p in points}
    assert counts_by_month == {1: 1, 2: 2, 3: 1}


async def test_procurement_volume_rejects_invalid_granularity(session):
    import pytest

    with pytest.raises(ValueError, match="granularity"):
        await aggregations.procurement_volume_over_time(
            session, granularity="century"
        )


# --- Rankings ---------------------------------------------------------------


async def test_top_buyers_by_value(session):
    await _seed(session)
    rows = await aggregations.top_buyers(session, by="value")
    # Kyiv: 100 + 250 + 80 = 430.  Lviv: 400.
    by_edrpou = {r.edrpou: r for r in rows}
    assert by_edrpou["buy-kyiv"].total_value == Decimal("430")
    assert by_edrpou["buy-lviv"].total_value == Decimal("400")
    # Ordered descending by value.
    assert rows[0].edrpou == "buy-kyiv"
    assert rows[1].edrpou == "buy-lviv"


async def test_top_suppliers_aggregate_contract_value(session):
    await _seed(session)
    rows = await aggregations.top_suppliers(session)
    by_edrpou = {r.edrpou: r for r in rows}
    assert by_edrpou["sup-a"].total_value == Decimal("500")  # 100 + 400
    assert by_edrpou["sup-a"].contract_count == 2
    assert by_edrpou["sup-b"].total_value == Decimal("250")


# --- High-risk share --------------------------------------------------------


async def test_high_risk_share(session):
    await _seed(session)
    result = await aggregations.high_risk_share(session)
    # 4 total tenders, 2 flagged (t1, t3) → 0.5.
    assert result.total_tenders == 4
    assert result.high_risk_tenders == 2
    assert result.share == 0.5


async def test_high_risk_share_empty_db_no_division_by_zero(session):
    result = await aggregations.high_risk_share(session)
    assert result.total_tenders == 0
    assert result.high_risk_tenders == 0
    assert result.share == 0.0
