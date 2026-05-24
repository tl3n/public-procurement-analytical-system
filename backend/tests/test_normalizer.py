"""Tests for normalizer + persistence using a real Prozorro tender fixture."""

import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import func, select

from app.collector import crawler
from app.collector.normalizer import persist_tender
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

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "tender_sample.json"


@pytest.fixture
def tender_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text())["data"]


async def _count(session, model) -> int:
    result = await session.execute(select(func.count()).select_from(model))
    return result.scalar_one()


async def test_persist_creates_all_child_rows(session, tender_data):
    await persist_tender(session, tender_data)
    await session.commit()

    # Fixture: lot-less tender, 1 item, 2 bids (different suppliers), 1 award,
    # 1 contract, 0 complaints, 10 tender-level documents.
    assert await _count(session, Tender) == 1
    assert await _count(session, Lot) == 1
    assert await _count(session, Item) == 1
    assert await _count(session, Bid) == 2
    assert await _count(session, Award) == 1
    assert await _count(session, Contract) == 1
    assert await _count(session, Complaint) == 0
    assert await _count(session, Document) == 10
    assert await _count(session, ProcuringEntity) == 1
    assert await _count(session, Supplier) == 2


async def test_tender_top_level_fields_are_mapped(session, tender_data):
    await persist_tender(session, tender_data)
    await session.commit()

    tender = await session.get(Tender, tender_data["id"])
    assert tender is not None
    assert tender.tender_id_human == tender_data["tenderID"]
    assert tender.procurement_method == "open"
    assert tender.procurement_method_type == "aboveThresholdUA"
    assert tender.status == "active.awarded"
    assert float(tender.value_amount) == tender_data["value"]["amount"]
    assert tender.value_currency == "UAH"
    # Original document preserved verbatim.
    assert tender.raw_data is not None
    assert tender.raw_data["id"] == tender_data["id"]
    # Synthetic lot uses the tender id.
    lot = await session.get(Lot, tender_data["id"])
    assert lot is not None and lot.tender_id == tender_data["id"]


async def test_persist_is_idempotent(session, tender_data):
    """A second persist of the same JSON must not duplicate any rows."""
    await persist_tender(session, tender_data)
    await session.commit()
    await persist_tender(session, tender_data)
    await session.commit()

    assert await _count(session, Tender) == 1
    assert await _count(session, Lot) == 1
    assert await _count(session, Item) == 1
    assert await _count(session, Bid) == 2
    assert await _count(session, Award) == 1
    assert await _count(session, Contract) == 1
    assert await _count(session, Document) == 10
    assert await _count(session, ProcuringEntity) == 1
    assert await _count(session, Supplier) == 2


async def test_persist_dedupes_repeated_child_ids(session, tender_data):
    """Source data sometimes repeats an id (a re-uploaded document under the
    same id). The normalizer must keep only the last occurrence rather than
    raising on a PK collision."""
    # Mirror the real-world failure seen during the first live scheduler run.
    revised = dict(tender_data["documents"][0])
    revised["title"] = "duplicate-revision"
    payload = dict(tender_data)
    payload["documents"] = list(tender_data["documents"]) + [revised]

    await persist_tender(session, payload)
    await session.commit()

    # No PK violation; row count matches unique ids (i.e. original 10).
    assert await _count(session, Document) == len(tender_data["documents"])
    # The last occurrence is the one persisted.
    doc_row = await session.get(Document, revised["id"])
    assert doc_row is not None
    assert doc_row.title == "duplicate-revision"


async def test_run_sync_integrates_crawler_and_normalizer(session, tender_data):
    """End-to-end: feed yields one summary, detail endpoint returns the fixture."""
    tender_id = tender_data["id"]
    pages = {
        "p0": {
            "data": [
                {"id": tender_id, "dateModified": tender_data["dateModified"]}
            ],
            "next_page": {"offset": "p1"},
        },
        "p1": {"data": []},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(f"/tenders/{tender_id}"):
            return httpx.Response(200, json={"data": tender_data})
        offset = request.url.params.get("offset") or "p0"
        return httpx.Response(200, json=pages.get(offset, {"data": []}))

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        result = await crawler.run_sync(
            client,
            session,
            base_url="https://example.test/api",
            initial_offset="p0",
        )

    assert result == {"processed": 1, "failed": 0}
    assert await _count(session, Tender) == 1
    assert await _count(session, Bid) == 2


# --- Edge cases ------------------------------------------------------------


import hashlib  # noqa: E402  — used only by the helpers below


def _id(*parts: str) -> str:
    return hashlib.sha256("/".join(parts).encode()).hexdigest()[:32]


def _minimal_tender(**overrides) -> dict:
    """Build a tender payload with all the required scaffolding pre-filled."""
    base = {
        "id": _id("edge", "default"),
        "tenderID": "UA-EDGE-DEFAULT",
        "procurementMethod": "open",
        "procurementMethodType": "aboveThresholdUA",
        "status": "complete",
        "datePublished": "2026-01-01T00:00:00+00:00",
        "value": {"amount": 1000.0, "currency": "UAH"},
        "procuringEntity": {
            "identifier": {"id": "buy-edge", "legalName": "Edge Buyer"},
            "name": "Edge Buyer",
        },
        "lots": [],
        "items": [],
        "bids": [],
        "awards": [],
        "contracts": [],
        "complaints": [],
        "documents": [],
    }
    base.update(overrides)
    return base


async def test_persist_tender_with_explicit_lots(session):
    """Tender with explicit lots — items/bids/awards anchor to their relatedLot."""
    lot1 = _id("edge", "lot1")
    lot2 = _id("edge", "lot2")
    payload = _minimal_tender(
        id=_id("edge", "with-lots"),
        lots=[
            {
                "id": lot1,
                "title": "Lot A",
                "value": {"amount": 600.0, "currency": "UAH"},
            },
            {
                "id": lot2,
                "title": "Lot B",
                "value": {"amount": 400.0, "currency": "UAH"},
            },
        ],
        items=[
            {
                "id": _id("edge", "item1"),
                "description": "for lot A",
                "classification": {"id": "11111111-1"},
                "relatedLot": lot1,
            },
            {
                "id": _id("edge", "item2"),
                "description": "for lot B",
                "classification": {"id": "22222222-2"},
                "relatedLot": lot2,
            },
        ],
    )

    await persist_tender(session, payload)
    await session.commit()

    lots = (await session.execute(select(Lot))).scalars().all()
    assert {l.id for l in lots} == {lot1, lot2}
    items = (await session.execute(select(Item))).scalars().all()
    by_lot = {it.lot_id: it.cpv_code for it in items}
    assert by_lot[lot1] == "11111111-1"
    assert by_lot[lot2] == "22222222-2"


async def test_persist_bid_with_lot_values_produces_one_row_per_lot(session):
    """A multi-lot bid (lotValues with N entries) yields N bid rows.

    The synthesized id keeps each row unique even though the source bid id is
    shared across lots — see _hash_id in the normalizer.
    """
    lot1 = _id("edge", "ml-lot1")
    lot2 = _id("edge", "ml-lot2")
    bid_id = _id("edge", "ml-bid")
    payload = _minimal_tender(
        id=_id("edge", "multi-lot-bid"),
        lots=[{"id": lot1}, {"id": lot2}],
        bids=[
            {
                "id": bid_id,
                "status": "active",
                "lotValues": [
                    {"relatedLot": lot1, "value": {"amount": 100, "currency": "UAH"}},
                    {"relatedLot": lot2, "value": {"amount": 200, "currency": "UAH"}},
                ],
                "tenderers": [
                    {
                        "identifier": {"id": "sup-edge"},
                        "name": "Edge Supplier",
                    }
                ],
            }
        ],
    )

    await persist_tender(session, payload)
    await session.commit()

    bids = (await session.execute(select(Bid).order_by(Bid.lot_id))).scalars().all()
    assert len(bids) == 2
    by_lot = {b.lot_id: float(b.value_amount) for b in bids}
    assert by_lot[lot1] == 100.0
    assert by_lot[lot2] == 200.0
    # Both rows reference the same supplier (find-or-create by edrpou).
    assert await _count(session, Supplier) == 1


async def test_persist_tender_handles_missing_procuring_entity(session):
    """Synthesizes a placeholder ProcuringEntity when the API omits the field."""
    payload = _minimal_tender(
        id=_id("edge", "no-pe"),
        procuringEntity=None,
    )

    await persist_tender(session, payload)
    await session.commit()

    tender = await session.get(Tender, payload["id"])
    assert tender is not None
    assert tender.procuring_entity_id is not None
    pe = await session.get(ProcuringEntity, tender.procuring_entity_id)
    assert pe is not None
    # No edrpou or name when the source has none.
    assert pe.edrpou is None
    assert pe.name is None


async def test_persist_tender_handles_missing_optional_top_level_fields(session):
    """Title, description, value and tenderPeriod are all optional."""
    payload = _minimal_tender(
        id=_id("edge", "minimal"),
        title=None,
        description=None,
        value=None,
        tenderPeriod=None,
        datePublished=None,
    )

    await persist_tender(session, payload)
    await session.commit()

    tender = await session.get(Tender, payload["id"])
    assert tender is not None
    assert tender.title is None
    assert tender.value_amount is None
    assert tender.value_currency is None
    assert tender.date_published is None
    assert tender.tender_period_start is None
    # The synthetic lot is still created.
    assert await _count(session, Lot) == 1


async def test_persist_bid_without_tenderers_has_null_supplier(session):
    """A bid with no `tenderers` array yields a bid row with supplier_id=NULL."""
    payload = _minimal_tender(
        id=_id("edge", "anon-bid"),
        bids=[
            {
                "id": _id("edge", "bid-anon"),
                "status": "active",
                "value": {"amount": 1.0, "currency": "UAH"},
                # No "tenderers" key.
            }
        ],
    )

    await persist_tender(session, payload)
    await session.commit()

    bid = (await session.execute(select(Bid))).scalars().one()
    assert bid.supplier_id is None
    assert await _count(session, Supplier) == 0
