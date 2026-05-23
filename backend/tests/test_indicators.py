"""Tests for the five baseline risk indicators."""

import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.analytics.indicators.base import IndicatorRegistry, compute_for_tender
from app.analytics.indicators.buyer_concentration import BuyerConcentrationIndicator
from app.analytics.indicators.non_competitive import NonCompetitiveIndicator
from app.analytics.indicators.price_deviation import PriceDeviationIndicator
from app.analytics.indicators.shortened_period import ShortenedPeriodIndicator
from app.analytics.indicators.single_bidding import SingleBiddingIndicator
from app.models import (
    Award,
    Bid,
    Contract,
    Item,
    Lot,
    ProcuringEntity,
    Supplier,
    Tender,
)

UTC = timezone.utc


# --- Helpers ---------------------------------------------------------------


def _id(*parts: str) -> str:
    return hashlib.sha256("/".join(parts).encode()).hexdigest()[:32]


async def _make_buyer(session, key: str) -> ProcuringEntity:
    pe = ProcuringEntity(edrpou=key, name=f"Buyer-{key}")
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
    procurement_method_type: str | None = "open",
    status: str = "complete",
    value_amount: Decimal | None = Decimal("100"),
    date_published: datetime | None = None,
    tender_period_start: datetime | None = None,
    tender_period_end: datetime | None = None,
    bid_count: int = 0,
    cpv: str | None = None,
) -> Tender:
    if date_published is None:
        date_published = datetime(2025, 6, 1, tzinfo=UTC)
    tender = Tender(
        id=tid,
        procuring_entity_id=buyer.id,
        procurement_method="open",
        procurement_method_type=procurement_method_type,
        status=status,
        value_amount=value_amount,
        value_currency="UAH",
        date_published=date_published,
        tender_period_start=tender_period_start,
        tender_period_end=tender_period_end,
    )
    session.add(tender)
    session.add(
        Lot(id=tid, tender_id=tid, value_amount=value_amount, value_currency="UAH")
    )
    await session.flush()
    if cpv:
        session.add(Item(id=_id("item", tid), lot_id=tid, cpv_code=cpv))
    for i in range(bid_count):
        session.add(
            Bid(
                id=_id("bid", tid, str(i)),
                lot_id=tid,
                status="active",
                value_amount=value_amount,
            )
        )
    await session.flush()
    return tender


async def _add_award_and_contract(
    session,
    *,
    tender: Tender,
    supplier: Supplier,
    value: Decimal,
    date_signed: datetime,
) -> Contract:
    aw_id = _id("award", tender.id, supplier.edrpou or "")
    cn_id = _id("contract", tender.id, supplier.edrpou or "")
    session.add(
        Award(
            id=aw_id,
            lot_id=tender.id,
            supplier_id=supplier.id,
            status="active",
            value_amount=value,
            value_currency="UAH",
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


async def _run(session, indicator, tender_id: str):
    """Run one indicator via the dispatcher and return the persisted row."""
    reg = IndicatorRegistry()
    reg.register(indicator)
    rows = await compute_for_tender(session, tender_id, registry=reg)
    return rows[0] if rows else None


# --- Single bidding --------------------------------------------------------


async def test_single_bidding_true_one_bid(session):
    buyer = await _make_buyer(session, "sb-true")
    tid = _id("sb-true")
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        procurement_method_type="aboveThresholdUA",
        status="complete",
        bid_count=1,
    )
    row = await _run(session, SingleBiddingIndicator(), tid)
    assert row.value_boolean is True


async def test_single_bidding_false_two_bids(session):
    buyer = await _make_buyer(session, "sb-false")
    tid = _id("sb-false")
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        procurement_method_type="aboveThresholdUA",
        status="complete",
        bid_count=2,
    )
    row = await _run(session, SingleBiddingIndicator(), tid)
    assert row.value_boolean is False


async def test_single_bidding_null_non_competitive(session):
    buyer = await _make_buyer(session, "sb-na")
    tid = _id("sb-na")
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        procurement_method_type="negotiation",
        status="complete",
        bid_count=1,
    )
    row = await _run(session, SingleBiddingIndicator(), tid)
    assert row.value_boolean is None


async def test_single_bidding_null_still_open(session):
    buyer = await _make_buyer(session, "sb-open")
    tid = _id("sb-open")
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        procurement_method_type="aboveThresholdUA",
        status="active.tendering",
        bid_count=1,
    )
    row = await _run(session, SingleBiddingIndicator(), tid)
    assert row.value_boolean is None


# --- Non-competitive procedure --------------------------------------------


async def test_non_competitive_true(session):
    buyer = await _make_buyer(session, "nc-true")
    tid = _id("nc-true")
    await _make_tender(
        session, tid=tid, buyer=buyer, procurement_method_type="negotiation"
    )
    row = await _run(session, NonCompetitiveIndicator(), tid)
    assert row.value_boolean is True


async def test_non_competitive_false(session):
    buyer = await _make_buyer(session, "nc-false")
    tid = _id("nc-false")
    await _make_tender(
        session, tid=tid, buyer=buyer, procurement_method_type="aboveThresholdUA"
    )
    row = await _run(session, NonCompetitiveIndicator(), tid)
    assert row.value_boolean is False


async def test_non_competitive_null_unknown_type(session):
    buyer = await _make_buyer(session, "nc-null")
    tid = _id("nc-null")
    await _make_tender(session, tid=tid, buyer=buyer, procurement_method_type=None)
    row = await _run(session, NonCompetitiveIndicator(), tid)
    assert row.value_boolean is None


# --- Shortened submission period ------------------------------------------


async def test_shortened_period_true(session):
    """aboveThresholdUA requires 15 working days; we give 5."""
    buyer = await _make_buyer(session, "sp-true")
    tid = _id("sp-true")
    start = datetime(2025, 6, 2, tzinfo=UTC)  # Mon
    end = datetime(2025, 6, 9, tzinfo=UTC)  # Mon — 5 working days later
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        procurement_method_type="aboveThresholdUA",
        tender_period_start=start,
        tender_period_end=end,
    )
    row = await _run(session, ShortenedPeriodIndicator(), tid)
    assert row.value_boolean is True


async def test_shortened_period_false(session):
    """30+ working days easily clears the 15-day minimum."""
    buyer = await _make_buyer(session, "sp-false")
    tid = _id("sp-false")
    start = datetime(2025, 6, 2, tzinfo=UTC)
    end = datetime(2025, 7, 21, tzinfo=UTC)  # ~35 working days
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        procurement_method_type="aboveThresholdUA",
        tender_period_start=start,
        tender_period_end=end,
    )
    row = await _run(session, ShortenedPeriodIndicator(), tid)
    assert row.value_boolean is False


async def test_shortened_period_null_missing_dates(session):
    buyer = await _make_buyer(session, "sp-null")
    tid = _id("sp-null")
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        procurement_method_type="aboveThresholdUA",
        tender_period_start=None,
        tender_period_end=None,
    )
    row = await _run(session, ShortenedPeriodIndicator(), tid)
    assert row.value_boolean is None


# --- Buyer concentration --------------------------------------------------


async def test_buyer_concentration_full_capture_equals_one(session):
    """All contracted spend goes to one supplier → max share = 1.0."""
    buyer = await _make_buyer(session, "bc-cap")
    sup = await _make_supplier(session, "bc-cap-s")
    for i in range(3):
        tid = _id("bc-cap", str(i))
        t = await _make_tender(
            session,
            tid=tid,
            buyer=buyer,
            date_published=datetime(2025, 1, 1 + i, tzinfo=UTC),
            value_amount=Decimal("100"),
        )
        await _add_award_and_contract(
            session,
            tender=t,
            supplier=sup,
            value=Decimal("100"),
            date_signed=datetime(2025, 1, 1 + i, tzinfo=UTC),
        )
    cur_id = _id("bc-cap-cur")
    await _make_tender(
        session,
        tid=cur_id,
        buyer=buyer,
        date_published=datetime(2025, 6, 1, tzinfo=UTC),
    )
    row = await _run(session, BuyerConcentrationIndicator(), cur_id)
    assert row.value_numeric is not None
    assert float(row.value_numeric) == pytest.approx(1.0, abs=1e-6)


async def test_buyer_concentration_split_two_thirds(session):
    """Spend split 2:1 across suppliers → max share ≈ 0.667."""
    buyer = await _make_buyer(session, "bc-split")
    s_dom = await _make_supplier(session, "bc-split-dom")
    s_min = await _make_supplier(session, "bc-split-min")
    for i in range(2):
        tid = _id("bc-split-dom", str(i))
        t = await _make_tender(
            session,
            tid=tid,
            buyer=buyer,
            date_published=datetime(2025, 1, 1 + i, tzinfo=UTC),
            value_amount=Decimal("100"),
        )
        await _add_award_and_contract(
            session,
            tender=t,
            supplier=s_dom,
            value=Decimal("100"),
            date_signed=datetime(2025, 1, 1 + i, tzinfo=UTC),
        )
    t = await _make_tender(
        session,
        tid=_id("bc-split-min", "0"),
        buyer=buyer,
        date_published=datetime(2025, 1, 4, tzinfo=UTC),
        value_amount=Decimal("100"),
    )
    await _add_award_and_contract(
        session,
        tender=t,
        supplier=s_min,
        value=Decimal("100"),
        date_signed=datetime(2025, 1, 4, tzinfo=UTC),
    )
    cur_id = _id("bc-split-cur")
    await _make_tender(
        session,
        tid=cur_id,
        buyer=buyer,
        date_published=datetime(2025, 6, 1, tzinfo=UTC),
    )
    row = await _run(session, BuyerConcentrationIndicator(), cur_id)
    assert row.value_numeric is not None
    assert float(row.value_numeric) == pytest.approx(2 / 3, abs=1e-3)


async def test_buyer_concentration_null_no_prior_contracts(session):
    buyer = await _make_buyer(session, "bc-empty")
    tid = _id("bc-empty")
    await _make_tender(
        session,
        tid=tid,
        buyer=buyer,
        date_published=datetime(2025, 6, 1, tzinfo=UTC),
    )
    row = await _run(session, BuyerConcentrationIndicator(), tid)
    assert row.value_numeric is None


# --- Price deviation ------------------------------------------------------


async def test_price_deviation_null_below_min_reference_size(session):
    """Five comparable tenders is well below the 30 minimum → NULL."""
    buyer = await _make_buyer(session, "pd-few")
    for i in range(5):
        await _make_tender(
            session,
            tid=_id("pd-few-ref", str(i)),
            buyer=buyer,
            value_amount=Decimal("100"),
            cpv="79950000-8",
            date_published=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=i),
        )
    cur_id = _id("pd-few-cur")
    await _make_tender(
        session,
        tid=cur_id,
        buyer=buyer,
        value_amount=Decimal("200"),
        cpv="79950000-8",
        date_published=datetime(2025, 5, 1, tzinfo=UTC),
    )
    row = await _run(session, PriceDeviationIndicator(), cur_id)
    assert row.value_numeric is None


async def test_price_deviation_positive(session):
    """35 reference tenders at value 100, current at 200 → deviation = +1.0."""
    buyer = await _make_buyer(session, "pd-pos")
    for i in range(35):
        await _make_tender(
            session,
            tid=_id("pd-pos-ref", str(i)),
            buyer=buyer,
            value_amount=Decimal("100"),
            cpv="79950000-8",
            date_published=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=i),
        )
    cur_id = _id("pd-pos-cur")
    await _make_tender(
        session,
        tid=cur_id,
        buyer=buyer,
        value_amount=Decimal("200"),
        cpv="79950000-8",
        date_published=datetime(2025, 5, 1, tzinfo=UTC),
    )
    row = await _run(session, PriceDeviationIndicator(), cur_id)
    assert row.value_numeric is not None
    assert float(row.value_numeric) == pytest.approx(1.0, abs=1e-3)


async def test_price_deviation_negative(session):
    """35 reference tenders at 100, current at 50 → deviation = −0.5."""
    buyer = await _make_buyer(session, "pd-neg")
    for i in range(35):
        await _make_tender(
            session,
            tid=_id("pd-neg-ref", str(i)),
            buyer=buyer,
            value_amount=Decimal("100"),
            cpv="79950000-8",
            date_published=datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=i),
        )
    cur_id = _id("pd-neg-cur")
    await _make_tender(
        session,
        tid=cur_id,
        buyer=buyer,
        value_amount=Decimal("50"),
        cpv="79950000-8",
        date_published=datetime(2025, 5, 1, tzinfo=UTC),
    )
    row = await _run(session, PriceDeviationIndicator(), cur_id)
    assert row.value_numeric is not None
    assert float(row.value_numeric) == pytest.approx(-0.5, abs=1e-3)


# --- All-five registration check ------------------------------------------


def test_all_five_indicators_registered_globally():
    from app.analytics.indicators import registry as global_registry

    codes = {ind.describe().code for ind in global_registry.enabled()}
    assert codes == {
        "risk.single_bidding",
        "risk.non_competitive",
        "risk.shortened_period",
        "risk.buyer_concentration",
        "risk.price_deviation",
    }
