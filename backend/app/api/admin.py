"""Admin-only operations (no auth yet — wire authn before exposing publicly)."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.batch import recompute_all
from app.api.schemas import RecomputeResponse
from app.db import get_session

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/recompute", response_model=RecomputeResponse)
async def trigger_recompute(
    session: AsyncSession = Depends(get_session),
) -> RecomputeResponse:
    """Re-run every indicator across every tender. May take a long time."""
    result = await recompute_all(session)
    return RecomputeResponse(
        tenders_processed=result["tenders_processed"],
        bulk_rows_inserted=result["bulk_rows_inserted"],
    )
