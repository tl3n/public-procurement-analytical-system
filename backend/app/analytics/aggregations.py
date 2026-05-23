"""SQL-backed aggregations powering dashboards, rankings and reports.

Every function takes the async session and a small, explicit set of filters
(``since``/``until`` time-window, optional record limits). All bucketing and
counting happens inside PostgreSQL — Python only shapes the output into
dataclasses convenient for serialization downstream.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Contract,
    Item,
    Lot,
    ProcuringEntity,
    RiskIndicatorValue,
    Supplier,
    Tender,
)


# --- Result types -----------------------------------------------------------


@dataclass
class DistributionBucket:
    label: str
    tender_count: int
    total_value: Decimal | None


@dataclass
class TimeSeriesPoint:
    period: datetime
    tender_count: int
    total_value: Decimal | None


@dataclass
class BuyerRankRow:
    edrpou: str | None
    name: str | None
    tender_count: int
    total_value: Decimal | None


@dataclass
class SupplierRankRow:
    edrpou: str | None
    name: str | None
    contract_count: int
    total_value: Decimal | None


@dataclass
class HighRiskShare:
    total_tenders: int
    high_risk_tenders: int
    share: float


# --- Helpers ----------------------------------------------------------------


_ALLOWED_GRANULARITIES = frozenset({"day", "week", "month"})


def _apply_window(stmt, column, *, since: datetime | None, until: datetime | None):
    if since is not None:
        stmt = stmt.where(column >= since)
    if until is not None:
        stmt = stmt.where(column < until)
    return stmt


# --- Distributions ----------------------------------------------------------


async def distribution_by_procurement_type(
    session: AsyncSession,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[DistributionBucket]:
    label = func.coalesce(Tender.procurement_method_type, "unknown").label("label")
    count = func.count(Tender.id).label("n")
    total = func.sum(Tender.value_amount).label("total")
    stmt = select(label, count, total).group_by(label).order_by(count.desc())
    stmt = _apply_window(stmt, Tender.date_published, since=since, until=until)
    rows = (await session.execute(stmt)).all()
    return [
        DistributionBucket(label=r.label, tender_count=r.n, total_value=r.total)
        for r in rows
    ]


async def distribution_by_region(
    session: AsyncSession,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[DistributionBucket]:
    label = func.coalesce(ProcuringEntity.region, "unknown").label("label")
    count = func.count(Tender.id).label("n")
    total = func.sum(Tender.value_amount).label("total")
    stmt = (
        select(label, count, total)
        .join(Tender, Tender.procuring_entity_id == ProcuringEntity.id)
        .group_by(label)
        .order_by(count.desc())
    )
    stmt = _apply_window(stmt, Tender.date_published, since=since, until=until)
    rows = (await session.execute(stmt)).all()
    return [
        DistributionBucket(label=r.label, tender_count=r.n, total_value=r.total)
        for r in rows
    ]


async def distribution_by_cpv(
    session: AsyncSession,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    top: int = 20,
) -> list[DistributionBucket]:
    # Deduplicate tender×cpv tuples first so that a tender with multiple items
    # of the same CPV is not double-counted, nor is its value inflated.
    inner = (
        select(
            Item.cpv_code.label("cpv"),
            Tender.id.label("tid"),
            Tender.value_amount.label("val"),
            Tender.date_published.label("dp"),
        )
        .join(Lot, Lot.id == Item.lot_id)
        .join(Tender, Tender.id == Lot.tender_id)
        .where(Item.cpv_code.isnot(None))
        .distinct()
    )
    inner = _apply_window(inner, Tender.date_published, since=since, until=until)
    inner = inner.subquery()
    stmt = (
        select(
            inner.c.cpv.label("label"),
            func.count(inner.c.tid).label("n"),
            func.sum(inner.c.val).label("total"),
        )
        .group_by(inner.c.cpv)
        .order_by(func.count(inner.c.tid).desc())
        .limit(top)
    )
    rows = (await session.execute(stmt)).all()
    return [
        DistributionBucket(label=r.label, tender_count=r.n, total_value=r.total)
        for r in rows
    ]


# --- Time series ------------------------------------------------------------


async def procurement_volume_over_time(
    session: AsyncSession,
    *,
    granularity: str = "month",
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[TimeSeriesPoint]:
    if granularity not in _ALLOWED_GRANULARITIES:
        raise ValueError(
            f"granularity must be one of {sorted(_ALLOWED_GRANULARITIES)}, "
            f"got {granularity!r}"
        )
    period = func.date_trunc(granularity, Tender.date_published).label("period")
    stmt = (
        select(
            period,
            func.count(Tender.id).label("n"),
            func.sum(Tender.value_amount).label("total"),
        )
        .where(Tender.date_published.isnot(None))
        .group_by(period)
        .order_by(period)
    )
    stmt = _apply_window(stmt, Tender.date_published, since=since, until=until)
    rows = (await session.execute(stmt)).all()
    return [
        TimeSeriesPoint(period=r.period, tender_count=r.n, total_value=r.total)
        for r in rows
    ]


# --- Rankings ---------------------------------------------------------------


async def top_buyers(
    session: AsyncSession,
    *,
    limit: int = 10,
    by: str = "value",
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[BuyerRankRow]:
    count = func.count(Tender.id).label("n")
    total = func.sum(Tender.value_amount).label("total")
    order = total.desc().nullslast() if by == "value" else count.desc()
    stmt = (
        select(
            ProcuringEntity.edrpou,
            ProcuringEntity.name,
            count,
            total,
        )
        .join(Tender, Tender.procuring_entity_id == ProcuringEntity.id)
        .group_by(ProcuringEntity.id)
        .order_by(order)
        .limit(limit)
    )
    stmt = _apply_window(stmt, Tender.date_published, since=since, until=until)
    rows = (await session.execute(stmt)).all()
    return [
        BuyerRankRow(
            edrpou=r.edrpou,
            name=r.name,
            tender_count=r.n,
            total_value=r.total,
        )
        for r in rows
    ]


async def top_suppliers(
    session: AsyncSession,
    *,
    limit: int = 10,
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[SupplierRankRow]:
    count = func.count(Contract.id).label("n")
    total = func.sum(Contract.value_amount).label("total")
    stmt = (
        select(
            Supplier.edrpou,
            Supplier.name,
            count,
            total,
        )
        .join(Contract, Contract.supplier_id == Supplier.id)
        .group_by(Supplier.id)
        .order_by(total.desc().nullslast())
        .limit(limit)
    )
    stmt = _apply_window(stmt, Contract.date_signed, since=since, until=until)
    rows = (await session.execute(stmt)).all()
    return [
        SupplierRankRow(
            edrpou=r.edrpou,
            name=r.name,
            contract_count=r.n,
            total_value=r.total,
        )
        for r in rows
    ]


# --- High-risk share --------------------------------------------------------


async def high_risk_share(
    session: AsyncSession,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
) -> HighRiskShare:
    """Fraction of tenders that scored True on at least one boolean indicator."""
    scope = select(Tender.id)
    scope = _apply_window(scope, Tender.date_published, since=since, until=until)
    scope_subq = scope.subquery()

    total = (
        await session.execute(select(func.count()).select_from(scope_subq))
    ).scalar_one()

    high_risk = (
        await session.execute(
            select(func.count(func.distinct(RiskIndicatorValue.tender_id)))
            .where(RiskIndicatorValue.value_boolean.is_(True))
            .where(
                RiskIndicatorValue.tender_id.in_(select(scope_subq.c.id))
            )
        )
    ).scalar_one()

    share = (high_risk / total) if total else 0.0
    return HighRiskShare(
        total_tenders=int(total),
        high_risk_tenders=int(high_risk),
        share=float(share),
    )
