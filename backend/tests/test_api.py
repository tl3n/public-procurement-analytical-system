"""Tests for the FastAPI REST API.

The ``seeded`` dataset is built by the shared fixture in ``conftest.py``.
"""

import csv
import io
import json as jsonlib

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db import get_session
from app.main import app


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
        "/statistics/distributions",
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
    # Monthly volume series — 4 tenders fall into 3 months (Jan/Feb/Mar 2026).
    months = {p["period"][:7] for p in body["volume_over_time"]}
    assert months == {"2026-01", "2026-02", "2026-03"}


# --- Statistics ------------------------------------------------------------


async def test_statistics_distributions(client, seeded):
    r = await client.get("/statistics/distributions")
    assert r.status_code == 200
    body = r.json()
    cpv_by_label = {b["label"]: b for b in body["by_cpv"]}
    # Two tenders per CPV in the seeded fixture.
    assert cpv_by_label["79950000-8"]["tender_count"] == 2
    assert cpv_by_label["33100000-1"]["tender_count"] == 2
    region_by_label = {b["label"]: b for b in body["by_region"]}
    assert region_by_label["Київ"]["tender_count"] == 3
    assert region_by_label["Львівська область"]["tender_count"] == 1


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


# --- Extended filter / pagination coverage --------------------------------


async def test_list_tenders_filter_by_procurement_method_type(client, seeded):
    r = await client.get("/tenders?procurement_method_type=negotiation")
    rows = r.json()["data"]
    assert len(rows) == 1
    assert rows[0]["id"] == seeded["tenders"]["k3"].id


async def test_list_tenders_filter_by_region(client, seeded):
    r = await client.get("/tenders?region=Київ")
    rows = r.json()["data"]
    assert {row["buyer_edrpou"] for row in rows} == {"buy-kyiv"}
    assert len(rows) == 3


async def test_list_tenders_filter_by_date_range(client, seeded):
    r = await client.get(
        "/tenders?date_from=2026-02-01T00:00:00Z&date_to=2026-03-01T00:00:00Z"
    )
    rows = r.json()["data"]
    # k2 (Feb 15) and k3 (Feb 20) fall inside the window; k1 (Jan) and l1 (Mar) don't.
    assert {row["id"] for row in rows} == {
        seeded["tenders"]["k2"].id,
        seeded["tenders"]["k3"].id,
    }


async def test_list_tenders_filter_by_value_range(client, seeded):
    r = await client.get("/tenders?value_min=200&value_max=400")
    rows = r.json()["data"]
    # k2 (250) and l1 (400) match; k1 (100) and k3 (80) don't.
    assert {row["id"] for row in rows} == {
        seeded["tenders"]["k2"].id,
        seeded["tenders"]["l1"].id,
    }


async def test_list_tenders_filter_by_supplier(client, seeded):
    """Supplier filter exercises the Bid-join branch in apply_tender_filters.

    The seeded dataset has awards (linked to suppliers) but no bids, so the
    expected result is an empty list — what matters is that the filter branch
    runs and the join compiles correctly.
    """
    sup_a_id = str(seeded["sup_a"].id)
    r = await client.get(f"/tenders?supplier_id={sup_a_id}")
    assert r.status_code == 200
    assert r.json()["data"] == []


async def test_list_tenders_pagination_round_trip(client, seeded):
    r = await client.get("/tenders?limit=2")
    page1 = r.json()
    assert len(page1["data"]) == 2
    cursor = page1["next_cursor"]
    assert cursor

    r2 = await client.get(f"/tenders?limit=2&cursor={cursor}")
    page2 = r2.json()
    assert len(page2["data"]) == 2
    assert page2["next_cursor"] is None  # only 4 tenders total

    # The two pages must be disjoint and together cover all 4 ids.
    all_ids = {row["id"] for row in page1["data"] + page2["data"]}
    assert len(all_ids) == 4


async def test_export_csv_with_value_filter(client, seeded):
    r = await client.get("/export/tenders.csv?value_min=200")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    # k2 (250) and l1 (400) match.
    assert len(rows) == 2


async def test_export_json_has_attachment_header(client, seeded):
    r = await client.get("/export/tenders.json")
    assert r.headers["content-disposition"].startswith("attachment;")


async def test_list_tenders_filter_by_status(client, seeded):
    """Only the explicit `status` is returned (k2 is active.tendering)."""
    r = await client.get("/tenders?status=active.tendering")
    rows = r.json()["data"]
    assert {row["id"] for row in rows} == {seeded["tenders"]["k2"].id}


async def test_list_tenders_filter_by_single_indicator_true(client, seeded):
    """k1 has risk.single_bidding=True in the seeded data; nothing else does."""
    r = await client.get("/tenders?indicator_true=risk.single_bidding")
    rows = r.json()["data"]
    assert {row["id"] for row in rows} == {seeded["tenders"]["k1"].id}


async def test_list_tenders_filter_by_multiple_indicators_is_and(client, seeded):
    """Multiple indicator_true values combine with AND — no seeded tender has
    both single_bidding and non_competitive flagged, so the result is empty."""
    r = await client.get(
        "/tenders"
        "?indicator_true=risk.single_bidding"
        "&indicator_true=risk.non_competitive"
    )
    assert r.json()["data"] == []
