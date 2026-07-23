import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import CustomerReference
from app.synthetic.generator import known_customer_ids


@pytest.fixture()
def client():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with TestingSessionLocal() as seed_db:
            for cid in known_customer_ids():
                seed_db.add(CustomerReference(customer_id=cid))
            await seed_db.commit()

    asyncio.run(_setup())

    async def override_get_db():
        async with TestingSessionLocal() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_trigger_run_with_synthetic_data(client):
    resp = client.post(
        "/runs/trigger", params={"row_count": 20, "failure_rate": 0.0, "seed": 1, "use_llm": False}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] == 20
    assert data["status"] == "completed"
    assert data["clean_first_pass"] == 20


def test_trigger_run_with_isolated_failure_mode(client):
    resp = client.post(
        "/runs/trigger",
        params={
            "row_count": 10,
            "failure_rate": 1.0,
            "failure_mode": "invalid_foreign_key",
            "seed": 1,
            "use_llm": False,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["quarantined"] == 10
    assert data["healed"] == 0


def test_trigger_run_with_csv_upload(client):
    csv_text = (
        "order_id,customer_id,order_date,amount,currency,status\n"
        "ORD-000001,CUST-0001,2026-01-01,49.99,USD,pending\n"
    )
    files = {"file": ("batch.csv", csv_text, "text/csv")}
    resp = client.post("/runs/trigger", files=files, params={"use_llm": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] == 1
    assert data["clean_first_pass"] == 1


def test_list_and_get_run(client):
    trigger_resp = client.post(
        "/runs/trigger", params={"row_count": 5, "failure_rate": 0.0, "seed": 1, "use_llm": False}
    )
    run_id = trigger_resp.json()["id"]

    list_resp = client.get("/runs")
    assert list_resp.status_code == 200
    page = list_resp.json()
    assert page["total"] == 1
    assert any(r["id"] == run_id for r in page["items"])

    get_resp = client.get(f"/runs/{run_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == run_id


def test_runs_pagination(client):
    ids = []
    for i in range(5):
        resp = client.post(
            "/runs/trigger", params={"row_count": 1, "failure_rate": 0.0, "seed": i, "use_llm": False}
        )
        ids.append(resp.json()["id"])
    newest_first = list(reversed(ids))

    page1 = client.get("/runs", params={"limit": 2, "offset": 0}).json()
    assert page1["total"] == 5
    assert [r["id"] for r in page1["items"]] == newest_first[0:2]

    page2 = client.get("/runs", params={"limit": 2, "offset": 2}).json()
    assert page2["total"] == 5
    assert [r["id"] for r in page2["items"]] == newest_first[2:4]

    assert {r["id"] for r in page1["items"]} & {r["id"] for r in page2["items"]} == set()


def test_get_run_audit_trail(client):
    trigger_resp = client.post(
        "/runs/trigger",
        params={
            "row_count": 3,
            "failure_rate": 1.0,
            "failure_mode": "invalid_foreign_key",
            "seed": 1,
            "use_llm": False,
        },
    )
    run_id = trigger_resp.json()["id"]

    resp = client.get(f"/runs/{run_id}/audit")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 3
    assert len({e["row_identifier"] for e in entries}) == 3
    assert all(e["run_id"] == run_id for e in entries)
    assert all(e["outcome"] == "no_fix" for e in entries)
    assert all(e["transform_chosen"] is None for e in entries)


def test_get_run_audit_trail_missing_run_404(client):
    resp = client.get("/runs/999999/audit")
    assert resp.status_code == 404


def test_get_missing_run_404(client):
    resp = client.get("/runs/999999")
    assert resp.status_code == 404


def test_quarantine_list_and_resolve_flow(client):
    trigger_resp = client.post(
        "/runs/trigger",
        params={
            "row_count": 5,
            "failure_rate": 1.0,
            "failure_mode": "invalid_foreign_key",
            "seed": 1,
            "use_llm": False,
        },
    )
    run_id = trigger_resp.json()["id"]

    list_resp = client.get("/quarantine", params={"run_id": run_id})
    assert list_resp.status_code == 200
    page = list_resp.json()
    assert page["total"] == 5
    rows = page["items"]
    assert len(rows) == 5
    assert all(r["resolved"] is False for r in rows)

    quarantine_id = rows[0]["id"]
    get_resp = client.get(f"/quarantine/{quarantine_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["error_type"] == "invalid_foreign_key"

    resolve_resp = client.post(f"/quarantine/{quarantine_id}/resolve")
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["resolved"] is True

    unresolved_resp = client.get("/quarantine", params={"run_id": run_id, "resolved": False})
    unresolved_page = unresolved_resp.json()
    assert unresolved_page["total"] == 4
    assert len(unresolved_page["items"]) == 4


def test_quarantine_pagination(client):
    trigger_resp = client.post(
        "/runs/trigger",
        params={
            "row_count": 5,
            "failure_rate": 1.0,
            "failure_mode": "invalid_foreign_key",
            "seed": 1,
            "use_llm": False,
        },
    )
    run_id = trigger_resp.json()["id"]

    page1 = client.get("/quarantine", params={"run_id": run_id, "limit": 2, "offset": 0}).json()
    assert page1["total"] == 5
    assert len(page1["items"]) == 2

    page2 = client.get("/quarantine", params={"run_id": run_id, "limit": 2, "offset": 2}).json()
    assert page2["total"] == 5
    assert len(page2["items"]) == 2

    page3 = client.get("/quarantine", params={"run_id": run_id, "limit": 2, "offset": 4}).json()
    assert page3["total"] == 5
    assert len(page3["items"]) == 1

    ids_seen = {r["id"] for p in (page1, page2, page3) for r in p["items"]}
    assert len(ids_seen) == 5


def test_resolve_missing_quarantine_row_404(client):
    resp = client.post("/quarantine/999999/resolve")
    assert resp.status_code == 404


def test_stats_endpoint_reflects_runs(client):
    client.post("/runs/trigger", params={"row_count": 10, "failure_rate": 0.0, "seed": 1, "use_llm": False})
    client.post(
        "/runs/trigger",
        params={
            "row_count": 5,
            "failure_rate": 1.0,
            "failure_mode": "invalid_foreign_key",
            "seed": 2,
            "use_llm": False,
        },
    )

    resp = client.get("/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_runs"] == 2
    assert data["total_rows_processed"] == 15
    assert data["total_quarantined"] == 5
    assert len(data["heal_rate_over_time"]) == 2
    assert data["error_type_totals"] == {"invalid_foreign_key": 5}
