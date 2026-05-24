"""Statistics endpoints — rankings and per-indicator report."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import aggregations
from app.analytics.indicators import registry
from app.api.schemas import (
    BuyerRankOut,
    DistributionBucketOut,
    DistributionsResponse,
    IndicatorReportResponse,
    IndicatorReportRow,
    RankingsResponse,
    SupplierRankOut,
)
from app.cache import Cache, get_cache
from app.db import get_session
from app.models import RiskIndicatorValue

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
    key = "indicators:v1"
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
    indicators: list[IndicatorReportRow] = []
    for ind in registry.enabled():
        desc = ind.describe()
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
