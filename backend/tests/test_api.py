"""Tests for the FastAPI REST API."""

import csv
import hashlib
import io
import json as jsonlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import app
from app.models import (
    Award,
    Bid,
    Contract,
    Item,
    Lot,
    ProcuringEntity,
    RiskIndicatorValue,
    Supplier,
    Tender,
)

UTC = timezone.utc


def _id(*parts: str) -> str:
    return hashlib.sha256("/".join(parts).encode()).hexdigest()[:32]


# --- Fixtures --------------------------------------------------------------


@pytest_asyncio.fixture
async def client(session):
    async def _override_session():
        yield session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded(session) -> dict:
    """A small heterogeneous dataset shared by most API tests."""
    kyiv = ProcuringEntity(edrpou="buy-kyiv", name="Buyer Kyiv", region="Київ")
    lviv = ProcuringEntity(
        edrpou="buy-lviv", name="Buyer Lviv", region="Львівська область"
    )
    session.add_all([kyiv, lviv])
    sup_a = Supplier(edrpou="sup-a", name="Supplier A")
    sup_b = Supplier(edrpou="sup-b", name="Supplier B")
    session.add_all([sup_a, sup_b])
    await session.flush()

    tenders: dict[str, Tender] = {}

    def make_tender(key, buyer, *, type_, status, value, dp, cpv=None):
        tid = _id("api-test", key)
        t = Tender(
            id=tid,
            procuring_entity_id=buyer.id,
            procurement_method="open",
            procurement_method_type=type_,
            status=status,
            value_amount=value,
            value_currency="UAH",
            date_published=dp,
            title=f"Tender {key}",
        )
        session.add(t)
        session.add(
            Lot(id=tid, tender_id=tid, value_amount=value, value_currency="UAH")
        )
        tenders[key] = t
        if cpv:
            session.add(Item(id=_id("item", tid), lot_id=tid, cpv_code=cpv))
        return t

    # 3 Kyiv tenders + 1 Lviv tender, varied types and dates.
    make_tender(
        "k1", kyiv,
        type_="aboveThresholdUA", status="complete",
        value=Decimal("100"), dp=datetime(2025, 1, 10, tzinfo=UTC),
        cpv="79950000-8",
    )
    make_tender(
        "k2", kyiv,
        type_="aboveThresholdUA", status="active.tendering",
        value=Decimal("250"), dp=datetime(2025, 2, 15, tzinfo=UTC),
        cpv="79950000-8",
    )
    make_tender(
        "k3", kyiv,
        type_="negotiation", status="complete",
        value=Decimal("80"), dp=datetime(2025, 2, 20, tzinfo=UTC),
        cpv="33100000-1",
    )
    make_tender(
        "l1", lviv,
        type_="aboveThresholdUA", status="complete",
        value=Decimal("400"), dp=datetime(2025, 3, 5, tzinfo=UTC),
        cpv="33100000-1",
    )
    await session.flush()

    # One contract on l1 to supplier A.
    aw_id = _id("aw", tenders["l1"].id)
    cn_id = _id("ct", tenders["l1"].id)
    session.add(
        Award(
            id=aw_id,
            lot_id=tenders["l1"].id,
            supplier_id=sup_a.id,
            status="active",
            value_amount=Decimal("400"),
        )
    )
    await session.flush()
    session.add(
        Contract(
            id=cn_id,
            award_id=aw_id,
            supplier_id=sup_a.id,
            status="active",
            value_amount=Decimal("400"),
            value_currency="UAH",
            date_signed=datetime(2025, 3, 7, tzinfo=UTC),
        )
    )

    # Some risk indicator rows so /statistics/indicators returns meaningful data.
    session.add_all(
        [
            RiskIndicatorValue(
                tender_id=tenders["k1"].id,
                indicator_code="risk.single_bidding",
                value_boolean=True,
            ),
            RiskIndicatorValue(
                tender_id=tenders["k1"].id,
                indicator_code="risk.non_competitive",
                value_boolean=False,
            ),
            RiskIndicatorValue(
                tender_id=tenders["k3"].id,
                indicator_code="risk.non_competitive",
                value_boolean=True,
            ),
        ]
    )
    await session.commit()
    return {
        "kyiv": kyiv, "lviv": lviv, "sup_a": sup_a, "sup_b": sup_b,
        "tenders": tenders,
    }


# --- OpenAPI ---------------------------------------------------------------


async def test_openapi_schema_is_served(client):
    r = await client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"]
    # All expected paths are present.
    paths = schema["paths"]
    for expected in [
        "/tenders",
        "/tenders/{tender_id}",
        "/dashboard",
        "/statistics/rankings",
        "/statistics/indicators",
        "/export/tenders.csv",
        "/export/tenders.json",
        "/admin/recompute",
    ]:
        assert expected in paths, f"missing path {expected}"


# --- Tender list -----------------------------------------------------------


async def test_list_tenders_returns_data(client, seeded):
    r = await client.get("/tenders")
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == 4
    # Default ordering: newest first.
    dates = [row["date_published"] for row in body["data"]]
    assert dates == sorted(dates, reverse=True)


async def test_list_tenders_filter_by_buyer(client, seeded):
    kyiv_id = str(seeded["kyiv"].id)
    r = await client.get(f"/tenders?procuring_entity_id={kyiv_id}")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) == 3
    assert all(row["buyer_edrpou"] == "buy-kyiv" for row in rows)


async def test_list_tenders_filter_by_cpv(client, seeded):
    r = await client.get("/tenders?cpv=33100000-1")
    rows = r.json()["data"]
    assert len(rows) == 2
    assert {row["id"] for row in rows} == {
        seeded["tenders"]["k3"].id,
        seeded["tenders"]["l1"].id,
    }


async def test_list_tenders_pagination_with_cursor(client, seeded):
    r = await client.get("/tenders?limit=2")
    body = r.json()
    assert len(body["data"]) == 2
    assert body["next_cursor"] is not None
    r2 = await client.get(f"/tenders?limit=2&cursor={body['next_cursor']}")
    body2 = r2.json()
    assert len(body2["data"]) == 2
    # No overlap between pages.
    ids_page1 = {row["id"] for row in body["data"]}
    ids_page2 = {row["id"] for row in body2["data"]}
    assert ids_page1.isdisjoint(ids_page2)
    assert body2["next_cursor"] is None


async def test_list_tenders_invalid_cursor_returns_400(client, seeded):
    r = await client.get("/tenders?cursor=not-base64-at-all")
    assert r.status_code == 400


# --- Tender detail ---------------------------------------------------------


async def test_get_tender_detail_with_relations(client, seeded):
    tid = seeded["tenders"]["l1"].id
    r = await client.get(f"/tenders/{tid}")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == tid
    assert body["buyer_region"] == "Львівська область"
    assert len(body["lots"]) == 1
    assert len(body["contracts"]) == 1
    assert body["contracts"][0]["supplier_edrpou"] == "sup-a"


async def test_get_tender_returns_404_for_unknown(client, seeded):
    r = await client.get("/tenders/" + "0" * 32)
    assert r.status_code == 404


# --- Dashboard -------------------------------------------------------------


async def test_dashboard_returns_kpis_and_distribution(client, seeded):
    r = await client.get("/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert body["kpis"]["total_tenders"] == 4
    assert body["kpis"]["active_tenders"] == 1
    # Top-risk tenders ordered by number of True flags.
    top_risk_ids = [row["id"] for row in body["top_risk_tenders"]]
    assert seeded["tenders"]["k1"].id in top_risk_ids
    assert seeded["tenders"]["k3"].id in top_risk_ids
    # Distribution buckets present.
    buckets = body["procurement_type_distribution"]
    by_label = {b["label"]: b["tender_count"] for b in buckets}
    assert by_label["aboveThresholdUA"] == 3
    assert by_label["negotiation"] == 1
    # Monthly volume series — 4 tenders fall into 3 months (Jan/Feb/Mar 2025).
    months = {p["period"][:7] for p in body["volume_over_time"]}
    assert months == {"2025-01", "2025-02", "2025-03"}


# --- Statistics ------------------------------------------------------------


async def test_statistics_rankings(client, seeded):
    r = await client.get("/statistics/rankings")
    assert r.status_code == 200
    body = r.json()
    # Kyiv has 3 tenders totaling 430; Lviv has 1 of 400.
    by_buyer = {row["edrpou"]: row for row in body["buyers"]}
    assert by_buyer["buy-kyiv"]["tender_count"] == 3
    # Supplier A appears via the one contract on l1.
    by_supplier = {row["edrpou"]: row for row in body["suppliers"]}
    assert by_supplier["sup-a"]["contract_count"] == 1


async def test_statistics_indicators_summary(client, seeded):
    r = await client.get("/statistics/indicators")
    assert r.status_code == 200
    by_code = {row["code"]: row for row in r.json()["indicators"]}
    # Two True flags total: one for single_bidding, one for non_competitive.
    assert by_code["risk.single_bidding"]["count_true"] == 1
    assert by_code["risk.non_competitive"]["count_true"] == 1
    assert by_code["risk.non_competitive"]["count_false"] == 1
    # An indicator with no rows is still listed (registry order).
    assert by_code["risk.shortened_period"]["count_total"] == 0


# --- Exports ---------------------------------------------------------------


async def test_export_csv(client, seeded):
    r = await client.get("/export/tenders.csv")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    reader = csv.DictReader(io.StringIO(r.text))
    rows = list(reader)
    assert len(rows) == 4
    assert "tenderID" in reader.fieldnames
    assert any(row["buyer_edrpou"] == "buy-kyiv" for row in rows)


async def test_export_json(client, seeded):
    r = await client.get("/export/tenders.json")
    assert r.status_code == 200
    rows = jsonlib.loads(r.text)
    assert len(rows) == 4
    edrpous = {row["buyer_edrpou"] for row in rows}
    assert {"buy-kyiv", "buy-lviv"} <= edrpous


async def test_export_csv_respects_filters(client, seeded):
    r = await client.get("/export/tenders.csv?cpv=33100000-1")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 2


# --- Admin -----------------------------------------------------------------


async def test_admin_recompute(client, seeded):
    r = await client.post("/admin/recompute")
    assert r.status_code == 200
    body = r.json()
    # Four tenders → all processed; no error response.
    assert body["tenders_processed"] == 4
    assert body["bulk_rows_inserted"] >= 0
