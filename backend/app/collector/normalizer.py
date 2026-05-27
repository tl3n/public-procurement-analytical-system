"""Normalize and persist a Prozorro tender.

A raw tender object from the API is a deeply nested JSON document. Storing it
as-is would make every analytical query a JSONB traversal, which is slow even
with a GIN index. Instead we flatten the structure into the relational tables
defined in ``app.models`` while keeping the original document in ``tenders.raw_data``
for arbitrary later analysis.

Two correctness properties matter:

* **Idempotency.** The same tender JSON can arrive many times (every modification
  re-emits the full current state). Persisting it twice must not duplicate rows.
  Achieved with an upsert on the tender itself and a replace strategy for its
  children (lots, items, bids, awards, contracts, complaints, documents).

* **Transactionality.** A tender plus its children is one logical unit; partial
  writes would skew analytics. The whole operation runs in a single transaction
  scoped by the caller's session.commit() / session.rollback().
"""

import hashlib
import logging
from collections.abc import Iterable
from typing import TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collector.schemas import AddressIn, OrganizationIn, TenderIn
from app.models import (
    Award,
    Bid,
    Complaint,
    Contract,
    Document,
    Item,
    Lot,
    ProcuringEntity,
    Supplier,
    Tender,
)

log = logging.getLogger(__name__)

_T = TypeVar("_T")


def _dedupe_by_id(items: Iterable[_T]) -> list[_T]:
    """Drop earlier occurrences of any repeated ``.id``, keeping the last.

    Real-world Prozorro records occasionally list the same child id twice — most
    commonly a re-uploaded document under the original id. The latest entry is
    treated as the authoritative version.
    """
    seen: dict[str, _T] = {}
    for it in items:
        seen[it.id] = it  # type: ignore[attr-defined]
    return list(seen.values())


def _format_address(addr: AddressIn | None) -> str | None:
    if addr is None:
        return None
    parts = [addr.streetAddress, addr.locality, addr.region, addr.countryName]
    formatted = ", ".join(p for p in parts if p)
    return formatted or None


def _hash_id(*parts: str) -> str:
    """Synthesize a 32-character identifier from input components."""
    return hashlib.sha256("/".join(parts).encode("utf-8")).hexdigest()[:32]


async def _find_or_create_procuring_entity(
    session: AsyncSession, org: OrganizationIn | None
) -> ProcuringEntity:
    edrpou = org.identifier.id if org and org.identifier else None
    if edrpou:
        result = await session.execute(
            select(ProcuringEntity).where(ProcuringEntity.edrpou == edrpou)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
    entity = ProcuringEntity(
        edrpou=edrpou,
        name=(org.identifier.legalName if org and org.identifier else None)
        or (org.name if org else None),
        region=(org.address.region if org and org.address else None),
        address=_format_address(org.address if org else None),
    )
    session.add(entity)
    await session.flush()
    return entity


async def _find_or_create_supplier(
    session: AsyncSession, org: OrganizationIn
) -> Supplier:
    edrpou = org.identifier.id if org.identifier else None
    if edrpou:
        result = await session.execute(
            select(Supplier).where(Supplier.edrpou == edrpou)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing
    supplier = Supplier(
        edrpou=edrpou,
        name=(org.identifier.legalName if org.identifier else None) or org.name,
    )
    session.add(supplier)
    await session.flush()
    return supplier


async def _delete_existing_children(session: AsyncSession, tender_id: str) -> None:
    """Drop every child row belonging to this tender — order respects FK RESTRICT."""
    lot_ids = (
        await session.scalars(select(Lot.id).where(Lot.tender_id == tender_id))
    ).all()
    if lot_ids:
        award_ids = (
            await session.scalars(select(Award.id).where(Award.lot_id.in_(lot_ids)))
        ).all()
        # contracts → awards → bids/items → lots (FKs are RESTRICT).
        if award_ids:
            await session.execute(
                delete(Contract)
                .where(Contract.award_id.in_(award_ids))
                .execution_options(synchronize_session=False)
            )
            await session.execute(
                delete(Award)
                .where(Award.lot_id.in_(lot_ids))
                .execution_options(synchronize_session=False)
            )
        await session.execute(
            delete(Bid)
            .where(Bid.lot_id.in_(lot_ids))
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(Item)
            .where(Item.lot_id.in_(lot_ids))
            .execution_options(synchronize_session=False)
        )
        await session.execute(
            delete(Lot)
            .where(Lot.id.in_(lot_ids))
            .execution_options(synchronize_session=False)
        )
    await session.execute(
        delete(Complaint)
        .where(Complaint.tender_id == tender_id)
        .execution_options(synchronize_session=False)
    )
    await session.execute(
        delete(Document)
        .where(
            Document.related_entity_type == "tender",
            Document.related_entity_id == tender_id,
        )
        .execution_options(synchronize_session=False)
    )
    # Drop any ORM identity-map references to deleted rows.
    session.expire_all()


async def persist_tender(session: AsyncSession, raw: dict) -> Tender:
    """Validate ``raw`` and persist the tender plus all children."""
    t = TenderIn.model_validate(raw)

    # Deduplicate every child collection up front. Source data occasionally
    # repeats an id (see real-world tender f35290c00cef4039aa6c12f871890772,
    # which lists two revisions of the same document under one id).
    t.lots = _dedupe_by_id(t.lots)
    t.items = _dedupe_by_id(t.items)
    t.bids = _dedupe_by_id(t.bids)
    t.awards = _dedupe_by_id(t.awards)
    t.contracts = _dedupe_by_id(t.contracts)
    t.complaints = _dedupe_by_id(t.complaints)
    t.documents = _dedupe_by_id(t.documents)

    procuring_entity = await _find_or_create_procuring_entity(
        session, t.procuringEntity
    )

    # --- Upsert the tender row.
    tender = await session.get(Tender, t.id)
    if tender is None:
        tender = Tender(id=t.id)
        session.add(tender)
    tender.tender_id_human = t.tenderID
    tender.title = t.title
    tender.description = t.description
    tender.procurement_method = t.procurementMethod
    tender.procurement_method_type = t.procurementMethodType
    tender.status = t.status
    tender.value_amount = t.value.amount if t.value else None
    tender.value_currency = t.value.currency if t.value else None
    tender.date_published = t.datePublished or (
        t.tenderPeriod.startDate if t.tenderPeriod else None
    )
    tender.tender_period_start = t.tenderPeriod.startDate if t.tenderPeriod else None
    tender.tender_period_end = t.tenderPeriod.endDate if t.tenderPeriod else None
    tender.procuring_entity_id = procuring_entity.id
    tender.source_modified_at = t.dateModified
    tender.raw_data = raw
    await session.flush()

    # --- Replace strategy for children.
    await _delete_existing_children(session, t.id)

    # --- Lots (synthetic when the tender has none).
    lot_id_map: dict[str | None, str] = {}
    if t.lots:
        for lot in t.lots:
            session.add(
                Lot(
                    id=lot.id,
                    tender_id=t.id,
                    title=lot.title,
                    description=lot.description,
                    status=lot.status,
                    value_amount=lot.value.amount if lot.value else None,
                    value_currency=lot.value.currency if lot.value else None,
                )
            )
            lot_id_map[lot.id] = lot.id
        default_lot_id = t.lots[0].id
    else:
        # Synthetic lot: same id as the tender. Distinct table — no PK clash.
        session.add(
            Lot(
                id=t.id,
                tender_id=t.id,
                value_amount=t.value.amount if t.value else None,
                value_currency=t.value.currency if t.value else None,
            )
        )
        default_lot_id = t.id
    await session.flush()

    def lot_for(related: str | None) -> str:
        return lot_id_map.get(related, default_lot_id) if related else default_lot_id

    # --- Items.
    for it in t.items:
        cpv = it.classification.id if it.classification else None
        unit = (it.unit.name or it.unit.code) if it.unit else None
        session.add(
            Item(
                id=it.id,
                lot_id=lot_for(it.relatedLot),
                description=it.description,
                cpv_code=cpv,
                quantity=it.quantity,
                unit=unit,
            )
        )

    # --- Bids. lotValues -> one row per lot; otherwise one row total.
    for bid in t.bids:
        supplier = (
            await _find_or_create_supplier(session, bid.tenderers[0])
            if bid.tenderers
            else None
        )
        if bid.lotValues:
            multi = len(bid.lotValues) > 1
            for lv in bid.lotValues:
                # Single-lot bids keep the API id; multi-lot bids get a synthesized
                # id since the API id is shared across the lot entries.
                row_id = _hash_id(bid.id, lv.relatedLot) if multi else bid.id
                session.add(
                    Bid(
                        id=row_id,
                        lot_id=lot_for(lv.relatedLot),
                        supplier_id=supplier.id if supplier else None,
                        status=bid.status,
                        value_amount=lv.value.amount if lv.value else None,
                        value_currency=lv.value.currency if lv.value else None,
                        date=bid.date,
                    )
                )
        else:
            session.add(
                Bid(
                    id=bid.id,
                    lot_id=default_lot_id,
                    supplier_id=supplier.id if supplier else None,
                    status=bid.status,
                    value_amount=bid.value.amount if bid.value else None,
                    value_currency=bid.value.currency if bid.value else None,
                    date=bid.date,
                )
            )
    await session.flush()

    # --- Awards.
    # Track each award's supplier so the contract pass can inherit it —
    # Prozorro's contract payload does not include a suppliers field,
    # the canonical source is the parent award.
    award_supplier_id: dict[str, str | None] = {}
    for a in t.awards:
        supplier = (
            await _find_or_create_supplier(session, a.suppliers[0])
            if a.suppliers
            else None
        )
        sid = supplier.id if supplier else None
        award_supplier_id[a.id] = sid
        session.add(
            Award(
                id=a.id,
                lot_id=lot_for(a.lotID),
                bid_id=a.bid_id,
                supplier_id=sid,
                status=a.status,
                value_amount=a.value.amount if a.value else None,
                value_currency=a.value.currency if a.value else None,
                date=a.date,
            )
        )
    await session.flush()

    # --- Contracts.
    for c, c_raw in zip(t.contracts, raw.get("contracts") or [], strict=False):
        # Inherit the supplier from the parent award; fall back to a
        # supplier in the contract payload if Prozorro ever populates one.
        sid = award_supplier_id.get(c.awardID) if c.awardID else None
        if sid is None and c.suppliers:
            fallback = await _find_or_create_supplier(session, c.suppliers[0])
            sid = fallback.id if fallback else None
        session.add(
            Contract(
                id=c.id,
                award_id=c.awardID,
                supplier_id=sid,
                status=c.status,
                value_amount=c.value.amount if c.value else None,
                value_currency=c.value.currency if c.value else None,
                date_signed=c.dateSigned,
                source_modified_at=c.dateModified,
                raw_data=c_raw,
            )
        )

    # --- Complaints.
    for cm in t.complaints:
        session.add(
            Complaint(
                id=cm.id,
                tender_id=t.id,
                status=cm.status,
                type=cm.type,
                title=cm.title,
                description=cm.description,
                date_submitted=cm.date,
            )
        )

    # --- Tender-level documents.
    for d in t.documents:
        session.add(
            Document(
                id=d.id,
                related_entity_type="tender",
                related_entity_id=t.id,
                title=d.title,
                url=d.url,
                format=d.format,
                date_published=d.datePublished,
            )
        )

    await session.flush()
    return tender
