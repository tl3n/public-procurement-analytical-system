"""SQL-backed aggregations powering dashboards, rankings and reports.

Every function takes the async session and a small, explicit set of filters
(``since``/``until`` time-window, optional record limits). All bucketing and
counting happens inside PostgreSQL — Python only shapes the output into
dataclasses convenient for serialization downstream.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.statistics import gini as compute_gini
from app.analytics.statistics import hhi as compute_hhi
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


@dataclass
class CpvConcentrationRow:
    cpv: str
    hhi: float
    gini: float
    supplier_count: int
    total_value: Decimal | None


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


# --- Market concentration ---------------------------------------------------


async def market_concentration_by_cpv(
    session: AsyncSession,
    *,
    since: datetime | None = None,
    until: datetime | None = None,
    top: int = 15,
) -> list[CpvConcentrationRow]:
    """HHI and Gini concentration metrics per CPV code.

    For each CPV code, contract values are grouped by supplier and passed to
    hhi() / gini() from the statistics module. Only the top N codes by total
    contracted value are returned (minimum 2 suppliers required to compute
    meaningful concentration).
    """
    stmt = (
        select(
            Item.cpv_code.label("cpv"),
            Contract.supplier_id,
            func.sum(Contract.value_amount).label("total"),
        )
        .join(Award, Award.id == Contract.award_id)
        .join(Lot, Lot.id == Award.lot_id)
        .join(Tender, Tender.id == Lot.tender_id)
        .join(Item, Item.lot_id == Lot.id)
        .where(Item.cpv_code.isnot(None))
        .where(Contract.value_amount.isnot(None))
        .where(Contract.supplier_id.isnot(None))
        .group_by(Item.cpv_code, Contract.supplier_id)
    )
    if since is not None:
        stmt = stmt.where(Contract.date_signed >= since)
    if until is not None:
        stmt = stmt.where(Contract.date_signed < until)

    rows = (await session.execute(stmt)).all()

    # Aggregate supplier totals per CPV in Python.
    cpv_suppliers: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        cpv_suppliers[row.cpv].append(float(row.total))

    # Sort by total contracted value descending, then take top N.
    ranked = sorted(
        cpv_suppliers.items(),
        key=lambda kv: sum(kv[1]),
        reverse=True,
    )[:top]

    return [
        CpvConcentrationRow(
            cpv=cpv,
            hhi=compute_hhi(values),
            gini=compute_gini(values),
            supplier_count=len(values),
            total_value=Decimal(str(round(sum(values), 2))),
        )
        for cpv, values in ranked
        if len(values) >= 2
    ]
