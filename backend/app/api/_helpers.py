"""Shared helpers for the REST API — filters, cursors, ORM→DTO conversion."""

import base64
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.sql import Select

from app.api.schemas import (
    AwardOut,
    BidOut,
    ContractOut,
    ItemOut,
    LotOut,
    RiskIndicatorValueOut,
    TenderDetail,
    TenderSummary,
)
from app.models import Bid, Item, Lot, ProcuringEntity, Tender


# --- Keyset cursor ---------------------------------------------------------


def encode_cursor(date_published: datetime, tender_id: str) -> str:
    payload = {"d": date_published.isoformat(), "i": tender_id}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return datetime.fromisoformat(payload["d"]), payload["i"]
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid cursor: {cursor!r}") from exc


# --- Filter application ----------------------------------------------------


def apply_tender_filters(
    stmt: Select,
    *,
    procuring_entity_id: UUID | None = None,
    supplier_id: UUID | None = None,
    cpv: str | None = None,
    region: str | None = None,
    procurement_method_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    value_min: Decimal | None = None,
    value_max: Decimal | None = None,
) -> Select:
    """Apply the shared tender-search filters to ``stmt`` (a ``select(Tender)``)."""
    if procuring_entity_id is not None:
        stmt = stmt.where(Tender.procuring_entity_id == procuring_entity_id)
    if procurement_method_type is not None:
        stmt = stmt.where(Tender.procurement_method_type == procurement_method_type)
    if date_from is not None:
        stmt = stmt.where(Tender.date_published >= date_from)
    if date_to is not None:
        stmt = stmt.where(Tender.date_published < date_to)
    if value_min is not None:
        stmt = stmt.where(Tender.value_amount >= value_min)
    if value_max is not None:
        stmt = stmt.where(Tender.value_amount <= value_max)
    if region is not None:
        stmt = stmt.where(
            Tender.procuring_entity.has(ProcuringEntity.region == region)
        )
    if cpv is not None:
        stmt = stmt.where(
            Tender.id.in_(
                select(Lot.tender_id)
                .join(Item, Item.lot_id == Lot.id)
                .where(Item.cpv_code == cpv)
            )
        )
    if supplier_id is not None:
        stmt = stmt.where(
            Tender.id.in_(
                select(Lot.tender_id)
                .join(Bid, Bid.lot_id == Lot.id)
                .where(Bid.supplier_id == supplier_id)
            )
        )
    return stmt


# --- ORM → DTO conversion --------------------------------------------------


def tender_to_summary(t: Tender) -> TenderSummary:
    pe = t.procuring_entity
    return TenderSummary(
        id=t.id,
        tender_id_human=t.tender_id_human,
        title=t.title,
        procurement_method=t.procurement_method,
        procurement_method_type=t.procurement_method_type,
        status=t.status,
        value_amount=t.value_amount,
        value_currency=t.value_currency,
        date_published=t.date_published,
        buyer_edrpou=pe.edrpou if pe else None,
        buyer_name=pe.name if pe else None,
    )


def _bid_to_out(b) -> BidOut:
    sup = b.supplier
    return BidOut(
        id=b.id,
        status=b.status,
        value_amount=b.value_amount,
        value_currency=b.value_currency,
        date=b.date,
        supplier_edrpou=sup.edrpou if sup else None,
        supplier_name=sup.name if sup else None,
    )


def _award_to_out(a) -> AwardOut:
    sup = a.supplier
    return AwardOut(
        id=a.id,
        status=a.status,
        value_amount=a.value_amount,
        value_currency=a.value_currency,
        date=a.date,
        supplier_edrpou=sup.edrpou if sup else None,
        supplier_name=sup.name if sup else None,
    )


def _contract_to_out(c) -> ContractOut:
    sup = c.supplier
    return ContractOut(
        id=c.id,
        status=c.status,
        value_amount=c.value_amount,
        value_currency=c.value_currency,
        date_signed=c.date_signed,
        supplier_edrpou=sup.edrpou if sup else None,
        supplier_name=sup.name if sup else None,
    )


def _item_to_out(it) -> ItemOut:
    return ItemOut(
        id=it.id,
        description=it.description,
        cpv_code=it.cpv_code,
        quantity=it.quantity,
        unit=it.unit,
    )


def _lot_to_out(lot) -> LotOut:
    return LotOut(
        id=lot.id,
        title=lot.title,
        description=lot.description,
        status=lot.status,
        value_amount=lot.value_amount,
        value_currency=lot.value_currency,
        items=[_item_to_out(it) for it in lot.items],
        bids=[_bid_to_out(b) for b in lot.bids],
        awards=[_award_to_out(a) for a in lot.awards],
    )


def tender_to_detail(t: Tender) -> TenderDetail:
    pe = t.procuring_entity
    contracts = [
        _contract_to_out(a.contract)
        for lot in t.lots
        for a in lot.awards
        if a.contract is not None
    ]
    risk_rows = [
        RiskIndicatorValueOut(
            indicator_code=r.indicator_code,
            value_boolean=r.value_boolean,
            value_numeric=r.value_numeric,
            computed_at=r.computed_at,
        )
        for r in t.risk_indicator_values
    ]
    return TenderDetail(
        id=t.id,
        tender_id_human=t.tender_id_human,
        title=t.title,
        description=t.description,
        procurement_method=t.procurement_method,
        procurement_method_type=t.procurement_method_type,
        status=t.status,
        value_amount=t.value_amount,
        value_currency=t.value_currency,
        date_published=t.date_published,
        tender_period_start=t.tender_period_start,
        tender_period_end=t.tender_period_end,
        buyer_edrpou=pe.edrpou if pe else None,
        buyer_name=pe.name if pe else None,
        buyer_region=pe.region if pe else None,
        lots=[_lot_to_out(lot) for lot in t.lots],
        contracts=contracts,
        risk_indicator_values=risk_rows,
    )
