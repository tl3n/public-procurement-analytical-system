"""Streaming export endpoints — CSV and JSON dumps of filtered tenders.

Both formats apply the same filters as the tender list endpoint but skip
pagination so callers can dump an entire result set. The response is built
incrementally with ``session.stream`` so the server never holds the whole
result in memory.
"""

import csv
import io
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api._helpers import apply_tender_filters
from app.db import get_session
from app.models import Tender

router = APIRouter(prefix="/export", tags=["export"])

_CSV_FIELDS = [
    "id",
    "tenderID",
    "title",
    "procurement_method",
    "procurement_method_type",
    "status",
    "value_amount",
    "value_currency",
    "date_published",
    "buyer_edrpou",
    "buyer_name",
    "buyer_region",
]


def _row_dict(t: Tender) -> dict[str, str | None]:
    pe = t.procuring_entity
    return {
        "id": t.id,
        "tenderID": t.tender_id_human,
        "title": t.title,
        "procurement_method": t.procurement_method,
        "procurement_method_type": t.procurement_method_type,
        "status": t.status,
        "value_amount": str(t.value_amount) if t.value_amount is not None else None,
        "value_currency": t.value_currency,
        "date_published": (
            t.date_published.isoformat() if t.date_published else None
        ),
        "buyer_edrpou": pe.edrpou if pe else None,
        "buyer_name": pe.name if pe else None,
        "buyer_region": pe.region if pe else None,
    }


def _filtered_statement(**filters):
    stmt = (
        select(Tender)
        .options(selectinload(Tender.procuring_entity))
        .where(Tender.date_published.isnot(None))
    )
    stmt = apply_tender_filters(stmt, **filters)
    return stmt.order_by(Tender.date_published.desc(), Tender.id.desc())


def _common_filters(
    procuring_entity_id: UUID | None = None,
    supplier_id: UUID | None = None,
    cpv: str | None = None,
    region: str | None = None,
    procurement_method_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    value_min: Decimal | None = None,
    value_max: Decimal | None = None,
) -> dict:
    return dict(
        procuring_entity_id=procuring_entity_id,
        supplier_id=supplier_id,
        cpv=cpv,
        region=region,
        procurement_method_type=procurement_method_type,
        date_from=date_from,
        date_to=date_to,
        value_min=value_min,
        value_max=value_max,
    )


@router.get("/tenders.csv")
async def export_tenders_csv(
    filters: dict = Depends(_common_filters),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    stmt = _filtered_statement(**filters).execution_options(yield_per=200)

    async def generate():
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()

        async for (t,) in await session.stream(stmt):
            writer.writerow(_row_dict(t))
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=tenders.csv"},
    )


@router.get("/tenders.json")
async def export_tenders_json(
    filters: dict = Depends(_common_filters),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    stmt = _filtered_statement(**filters).execution_options(yield_per=200)

    async def generate():
        yield "["
        first = True
        async for (t,) in await session.stream(stmt):
            chunk = json.dumps(_row_dict(t), ensure_ascii=False)
            yield chunk if first else "," + chunk
            first = False
        yield "]"

    return StreamingResponse(
        generate(),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=tenders.json"},
    )
