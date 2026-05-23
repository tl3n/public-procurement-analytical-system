"""Statistics endpoints — rankings and per-indicator report."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import aggregations
from app.analytics.indicators import registry
from app.api.schemas import (
    BuyerRankOut,
    IndicatorReportResponse,
    IndicatorReportRow,
    RankingsResponse,
    SupplierRankOut,
)
from app.db import get_session
from app.models import RiskIndicatorValue

router = APIRouter(prefix="/statistics", tags=["statistics"])


@router.get("/rankings", response_model=RankingsResponse)
async def get_rankings(
    limit: int = Query(default=10, ge=1, le=100),
    since: datetime | None = None,
    until: datetime | None = None,
    session: AsyncSession = Depends(get_session),
) -> RankingsResponse:
    """Top buyers (by total tender value) and top suppliers (by contract value)."""
    buyer_rows = await aggregations.top_buyers(
        session, limit=limit, by="value", since=since, until=until
    )
    supplier_rows = await aggregations.top_suppliers(
        session, limit=limit, since=since, until=until
    )
    return RankingsResponse(
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


@router.get("/indicators", response_model=IndicatorReportResponse)
async def get_indicator_report(
    session: AsyncSession = Depends(get_session),
) -> IndicatorReportResponse:
    """Per-indicator counts of True / False / NULL outcomes."""
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
    return IndicatorReportResponse(indicators=indicators)
