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
