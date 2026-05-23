"""Admin-only operations (no auth yet — wire authn before exposing publicly)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.batch import recompute_all
from app.api.schemas import RecomputeResponse
from app.cache import Cache, get_cache
from app.db import get_session

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/recompute", response_model=RecomputeResponse)
async def trigger_recompute(
    session: AsyncSession = Depends(get_session),
    cache: Cache = Depends(get_cache),
) -> RecomputeResponse:
    """Re-run every indicator across every tender. May take a long time.

    Invalidates the aggregation cache so dashboards reflect the new values on
    the next request rather than waiting for the TTL to expire.
    """
    result = await recompute_all(session)
    await cache.invalidate_all()
    return RecomputeResponse(
        tenders_processed=result["tenders_processed"],
        bulk_rows_inserted=result["bulk_rows_inserted"],
    )
