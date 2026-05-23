"""Dashboard endpoint — KPIs + type distribution + top-risk tenders."""

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics import aggregations
from app.api._helpers import tender_to_summary
from app.api.schemas import (
    DashboardKpis,
    DashboardResponse,
    DistributionBucketOut,
    HighRiskShareOut,
)
from app.cache import Cache, get_cache
from app.db import get_session
from app.models import RiskIndicatorValue, Tender

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_CACHE_KEY = "dashboard:v1"


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
):
    cached = await cache.get_json(_CACHE_KEY)
    if cached is not None:
        return cached

    total_tenders = (
        await session.execute(select(func.count()).select_from(Tender))
    ).scalar_one()
    total_value = (
        await session.execute(select(func.sum(Tender.value_amount)))
    ).scalar_one()
    active_tenders = (
        await session.execute(
            select(func.count())
            .select_from(Tender)
            .where(Tender.status.like("active%"))
        )
    ).scalar_one()
    kpis = DashboardKpis(
        total_tenders=int(total_tenders),
        total_value=total_value,
        active_tenders=int(active_tenders),
    )

    type_buckets = await aggregations.distribution_by_procurement_type(session)
    type_distribution = [
        DistributionBucketOut(
            label=b.label,
            tender_count=b.tender_count,
            total_value=b.total_value,
        )
        for b in type_buckets
    ]

    high_risk = await aggregations.high_risk_share(session)
    high_risk_share = HighRiskShareOut(
        total_tenders=high_risk.total_tenders,
        high_risk_tenders=high_risk.high_risk_tenders,
        share=high_risk.share,
    )

    # Top-risk tenders: most boolean indicators flagged True, then most recent.
    risk_count = func.count(
        case((RiskIndicatorValue.value_boolean.is_(True), 1))
    ).label("rc")
    stmt = (
        select(Tender, risk_count)
        .options(selectinload(Tender.procuring_entity))
        .outerjoin(
            RiskIndicatorValue, RiskIndicatorValue.tender_id == Tender.id
        )
        .group_by(Tender.id)
        .having(risk_count > 0)
        .order_by(risk_count.desc(), Tender.date_published.desc().nullslast())
        .limit(10)
    )
    rows = (await session.execute(stmt)).all()
    top_risk = [tender_to_summary(row[0]) for row in rows]

    response = DashboardResponse(
        kpis=kpis,
        procurement_type_distribution=type_distribution,
        top_risk_tenders=top_risk,
        high_risk_share=high_risk_share,
    )
    await cache.set_json(_CACHE_KEY, response.model_dump(mode="json"))
    return response
