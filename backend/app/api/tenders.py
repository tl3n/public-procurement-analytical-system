"""Tender search and detail endpoints."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api._helpers import (
    apply_tender_filters,
    decode_cursor,
    encode_cursor,
    tender_to_detail,
    tender_to_summary,
)
from app.api.schemas import TenderDetail, TenderListResponse
from app.db import get_session
from app.models import Award, Bid, Lot, Tender

router = APIRouter(prefix="/tenders", tags=["tenders"])


@router.get("", response_model=TenderListResponse)
async def list_tenders(
    procuring_entity_id: UUID | None = None,
    supplier_id: UUID | None = None,
    cpv: str | None = None,
    region: str | None = None,
    procurement_method_type: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    value_min: Decimal | None = None,
    value_max: Decimal | None = None,
    indicator_true: list[str] | None = Query(default=None),
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> TenderListResponse:
    """List tenders with filters and keyset pagination.

    Ordered by ``(date_published DESC, id DESC)``. The cursor encodes the last
    seen ``(date_published, id)`` pair so the next page resumes exactly where
    the previous one stopped, without scanning skipped rows.
    """
    stmt = (
        select(Tender)
        .options(selectinload(Tender.procuring_entity))
        .where(Tender.date_published.isnot(None))
    )
    stmt = apply_tender_filters(
        stmt,
        procuring_entity_id=procuring_entity_id,
        supplier_id=supplier_id,
        cpv=cpv,
        region=region,
        procurement_method_type=procurement_method_type,
        status=status,
        date_from=date_from,
        date_to=date_to,
        value_min=value_min,
        value_max=value_max,
        indicator_true=indicator_true,
    )
    if cursor:
        try:
            cur_date, cur_id = decode_cursor(cursor)
        except ValueError as exc:
            raise HTTPException(400, detail=str(exc)) from exc
        stmt = stmt.where(
            tuple_(Tender.date_published, Tender.id) < (cur_date, cur_id)
        )
    stmt = stmt.order_by(
        Tender.date_published.desc(), Tender.id.desc()
    ).limit(limit + 1)

    tenders = (await session.execute(stmt)).scalars().all()
    has_more = len(tenders) > limit
    page = tenders[:limit]
    next_cursor = (
        encode_cursor(page[-1].date_published, page[-1].id)
        if has_more and page
        else None
    )
    return TenderListResponse(
        data=[tender_to_summary(t) for t in page],
        next_cursor=next_cursor,
    )


@router.get("/{tender_id}", response_model=TenderDetail)
async def get_tender(
    tender_id: str,
    session: AsyncSession = Depends(get_session),
) -> TenderDetail:
    """Return one tender with its lots, bids, awards, contracts and indicators."""
    stmt = (
        select(Tender)
        .options(
            selectinload(Tender.procuring_entity),
            selectinload(Tender.risk_indicator_values),
            selectinload(Tender.lots).selectinload(Lot.items),
            selectinload(Tender.lots)
            .selectinload(Lot.bids)
            .selectinload(Bid.supplier),
            selectinload(Tender.lots)
            .selectinload(Lot.awards)
            .selectinload(Award.supplier),
            selectinload(Tender.lots)
            .selectinload(Lot.awards)
            .selectinload(Award.contract),
        )
        .where(Tender.id == tender_id)
    )
    tender = (await session.execute(stmt)).scalar_one_or_none()
    if tender is None:
        raise HTTPException(404, detail=f"tender {tender_id!r} not found")
    return tender_to_detail(tender)
