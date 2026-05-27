"""Statistics endpoints — rankings and per-indicator report."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import aggregations
from app.analytics.indicators import registry
from app.analytics.indicators.composite import CRI_DESCRIPTION
from app.analytics.statistics import (
    decompose_time_series,
    pearson_correlation,
    spearman_correlation,
)
from app.api.schemas import (
    BuyerRankOut,
    ConcentrationBucketOut,
    ConcentrationResponse,
    CorrelationResponse,
    DecompositionPointOut,
    DecompositionResponse,
    DistributionBucketOut,
    DistributionsResponse,
    IndicatorReportResponse,
    IndicatorReportRow,
    RankingsResponse,
    SupplierRankOut,
)
from app.cache import Cache, get_cache
from app.db import get_session
from app.models import Bid, Lot, RiskIndicatorValue

router = APIRouter(prefix="/statistics", tags=["statistics"])


def _rankings_cache_key(limit: int, since: datetime | None, until: datetime | None) -> str:
    return (
        f"rankings:v1:limit={limit}"
        f":since={since.isoformat() if since else ''}"
        f":until={until.isoformat() if until else ''}"
    )


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    limit: int = Query(default=10, ge=1, le=100),
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
):
    key = _rankings_cache_key(limit, since, until)
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    buyer_rows = await aggregations.top_buyers(
        session, limit=limit, by="value", since=since, until=until
    )
    supplier_rows = await aggregations.top_suppliers(
        session, limit=limit, since=since, until=until
    )
    response = RankingsResponse(
        buyers=[
            BuyerRankOut(
                edrpou=r.edrpou,
                name=r.name,
                tender_count=r.tender_count,
                total_value=r.total_value,
            )
            for r in buyer_rows
        ],
        suppliers=[
            SupplierRankOut(
                edrpou=r.edrpou,
                name=r.name,
                contract_count=r.contract_count,
                total_value=r.total_value,
            )
            for r in supplier_rows
        ],
    )
    await cache.set_json(key, response.model_dump(mode="json"))
    return response


def _distributions_cache_key(since: datetime | None, until: datetime | None) -> str:
    return (
        "distributions:v1"
        f":since={since.isoformat() if since else ''}"
        f":until={until.isoformat() if until else ''}"
    )


@router.get("/distributions", response_model=DistributionsResponse)
async def get_distributions(
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
):
    """Top CPV codes and buyer regions by tender count within the time window."""
    key = _distributions_cache_key(since, until)
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    cpv_buckets = await aggregations.distribution_by_cpv(
        session, since=since, until=until
    )
    region_buckets = await aggregations.distribution_by_region(
        session, since=since, until=until
    )
    response = DistributionsResponse(
        by_cpv=[
            DistributionBucketOut(
                label=b.label,
                tender_count=b.tender_count,
                total_value=b.total_value,
            )
            for b in cpv_buckets
        ],
        by_region=[
            DistributionBucketOut(
                label=b.label,
                tender_count=b.tender_count,
                total_value=b.total_value,
            )
            for b in region_buckets
        ],
    )
    await cache.set_json(key, response.model_dump(mode="json"))
    return response


@router.get("/indicators", response_model=IndicatorReportResponse)
async def get_indicator_report(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
):
    """Per-indicator counts of True / False / NULL outcomes."""
    # v2: includes the composite CRI row alongside the five base indicators.
    key = "indicators:v2"
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    # Aggregate per indicator code: total rows, True count, False count, NULL
    # count, average numeric.
    is_true = case((RiskIndicatorValue.value_boolean.is_(True), 1))
    is_false = case((RiskIndicatorValue.value_boolean.is_(False), 1))
    is_null = case(
        (
            and_(
                RiskIndicatorValue.value_boolean.is_(None),
                RiskIndicatorValue.value_numeric.is_(None),
            ),
            1,
        )
    )
    stmt = (
        select(
            RiskIndicatorValue.indicator_code.label("code"),
            func.count().label("total"),
            func.count(is_true).label("n_true"),
            func.count(is_false).label("n_false"),
            func.count(is_null).label("n_null"),
            func.avg(RiskIndicatorValue.value_numeric).label("avg_numeric"),
        )
        .group_by(RiskIndicatorValue.indicator_code)
    )
    rows = (await session.execute(stmt)).all()
    counts = {r.code: r for r in rows}

    # Compose the response in registry order so the UI gets a stable shape.
    # The composite CRI is appended at the end so the base indicators come
    # first and the synthetic summary closes the report.
    descriptions = [ind.describe() for ind in registry.enabled()]
    descriptions.append(CRI_DESCRIPTION)

    indicators: list[IndicatorReportRow] = []
    for desc in descriptions:
        r = counts.get(desc.code)
        indicators.append(
            IndicatorReportRow(
                code=desc.code,
                name=desc.name,
                value_type=desc.value_type,
                count_total=int(r.total) if r else 0,
                count_true=int(r.n_true) if r else 0,
                count_false=int(r.n_false) if r else 0,
                count_null=int(r.n_null) if r else 0,
                avg_numeric=(
                    float(r.avg_numeric) if r and r.avg_numeric is not None else None
                ),
            )
        )
    response = IndicatorReportResponse(indicators=indicators)
    await cache.set_json(key, response.model_dump(mode="json"))
    return response


# --- Concentration ----------------------------------------------------------


def _concentration_cache_key(
    since: datetime | None, until: datetime | None
) -> str:
    return (
        "concentration:v1"
        f":since={since.isoformat() if since else ''}"
        f":until={until.isoformat() if until else ''}"
    )


@router.get("/concentration", response_model=ConcentrationResponse)
async def get_concentration(
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
):
    """HHI and Gini market-concentration metrics for the top CPV codes."""
    key = _concentration_cache_key(since, until)
    cached = await cache.get_json(key)
    if cached is not None:
        return cached

    rows = await aggregations.market_concentration_by_cpv(
        session, since=since, until=until
    )
    response = ConcentrationResponse(
        rows=[
            ConcentrationBucketOut(
                cpv=r.cpv,
                hhi=r.hhi,
                gini=r.gini,
                supplier_count=r.supplier_count,
                total_value=r.total_value,
            )
            for r in rows
        ]
    )
    await cache.set_json(key, response.model_dump(mode="json"))
    return response


# --- Correlation ------------------------------------------------------------

_CORR_CACHE_KEY = "correlation:v1"


def _correlation_strength(r: float | None) -> str:
    if r is None:
        return "Недостатньо даних"
    a = abs(r)
    if a < 0.1:
        return "Практично відсутня"
    if a < 0.3:
        return "Слабка"
    if a < 0.5:
        return "Помірна"
    if a < 0.7:
        return "Значна"
    return "Сильна"


@router.get("/correlation", response_model=CorrelationResponse)
async def get_correlation(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
):
    """Pearson and Spearman correlation between bid count and price deviation."""
    cached = await cache.get_json(_CORR_CACHE_KEY)
    if cached is not None:
        return cached

    # Bid count per tender (summed across all lots).
    bid_count_sq = (
        select(
            Lot.tender_id,
            func.count(Bid.id).label("bid_count"),
        )
        .join(Bid, Bid.lot_id == Lot.id)
        .group_by(Lot.tender_id)
        .subquery()
    )

    stmt = (
        select(
            bid_count_sq.c.bid_count,
            RiskIndicatorValue.value_numeric,
        )
        .join(
            RiskIndicatorValue,
            RiskIndicatorValue.tender_id == bid_count_sq.c.tender_id,
        )
        .where(RiskIndicatorValue.indicator_code == "risk.price_deviation")
        .where(RiskIndicatorValue.value_numeric.isnot(None))
    )
    rows = (await session.execute(stmt)).all()

    bid_counts = [float(r.bid_count) for r in rows]
    deviations = [float(r.value_numeric) for r in rows]

    pearson = pearson_correlation(bid_counts, deviations)
    spearman = spearman_correlation(bid_counts, deviations)

    response = CorrelationResponse(
        pearson=pearson,
        spearman=spearman,
        n_pairs=len(rows),
        strength=_correlation_strength(pearson),
    )
    await cache.set_json(_CORR_CACHE_KEY, response.model_dump(mode="json"))
    return response


# --- Decomposition ----------------------------------------------------------

_DECOMP_CACHE_KEY = "decomposition:v1"


@router.get("/decomposition", response_model=DecompositionResponse)
async def get_decomposition(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
):
    """Additive seasonal decomposition of the monthly procurement volume."""
    cached = await cache.get_json(_DECOMP_CACHE_KEY)
    if cached is not None:
        return cached

    points = await aggregations.procurement_volume_over_time(
        session, granularity="month"
    )
    observed = [float(p.tender_count) for p in points]
    decomp = decompose_time_series(observed, period=12)

    has_decomp = bool(decomp["trend"])
    result_points: list[DecompositionPointOut] = []
    for i, p in enumerate(points):
        result_points.append(
            DecompositionPointOut(
                period=p.period,
                observed=observed[i],
                trend=decomp["trend"][i] if has_decomp else None,
                seasonal=decomp["seasonal"][i] if has_decomp else None,
                resid=decomp["resid"][i] if has_decomp else None,
            )
        )

    response = DecompositionResponse(points=result_points)
    await cache.set_json(_DECOMP_CACHE_KEY, response.model_dump(mode="json"))
    return response
