import io
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.db.base import Base, engine
from app.main import app
from scripts.seed import run as seed_run

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=engine)
    seed_run()
    yield


@pytest.fixture(scope="module")
def auth_headers():
    resp = client.post(
        "/api/auth/login",
        json={
            "username": settings.seed_admin_username,
            "password": settings.seed_admin_password,
        },
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _png_bytes() -> bytes:
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "3de9000000017352474200aece1ce90000000467414d410000b18f0bfc6105"
        "0000000009706859730000163e00001a5e0d4dbd3a0000000c49444154789c"
        "6360000200000500018e5b5e5a0000000049454e44ae426082"
    )


def test_donor_crud_requires_auth():
    assert client.get("/api/donors").status_code == 401
    assert client.post("/api/donors", json={"name": "X", "phone": "9000000001"}).status_code == 401


def test_donor_crud_roundtrip(auth_headers):
    created = client.post(
        "/api/donors",
        headers=auth_headers,
        json={"name": "Batch Test Donor", "phone": "9000000011", "email": None, "address": None},
    )
    assert created.status_code == 201, created.text
    donor_id = created.json()["id"]

    listed = client.get("/api/donors?search=Batch Test", headers=auth_headers)
    assert listed.status_code == 200
    assert any(d["id"] == donor_id for d in listed.json()["items"])

    updated = client.put(
        f"/api/donors/{donor_id}",
        headers=auth_headers,
        json={
            "name": "Batch Test Donor Renamed",
            "phone": "9000000011",
            "email": "batch@example.com",
            "address": "Bengaluru",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Batch Test Donor Renamed"

    assert client.delete(f"/api/donors/{donor_id}", headers=auth_headers).status_code == 204
    after = client.get("/api/donors?search=Batch Test", headers=auth_headers)
    assert not any(d["id"] == donor_id for d in after.json()["items"])

    # Soft delete: the record survives and re-adding the phone reactivates it.
    assert client.get(f"/api/donors/{donor_id}", headers=auth_headers).status_code == 200
    readded = client.post(
        "/api/donors",
        headers=auth_headers,
        json={"name": "Batch Test Donor", "phone": "9000000011", "email": None, "address": None},
    )
    assert readded.status_code == 201
    assert readded.json()["id"] == donor_id


def test_duplicate_active_phone_rejected(auth_headers):
    payload = {"name": "Dup One", "phone": "9000000022", "email": None, "address": None}
    assert client.post("/api/donors", headers=auth_headers, json=payload).status_code == 201
    assert client.post("/api/donors", headers=auth_headers, json=payload).status_code == 409


def test_batch_numbers_against_selected_period_and_isolates_failures(auth_headers):
    donor = client.post(
        "/api/donors",
        headers=auth_headers,
        json={"name": "Batch Period Donor", "phone": "9000000033", "email": None, "address": None},
    ).json()

    items = [
        {
            "donor_id": donor["id"],
            "amount_paise": 50000,
            "mode": "upi",
            "reason": "monthly_donation",
            "upi_txn_id": "UPI-TEST-1",
        },
        # Missing upi_txn_id -> this row alone must fail.
        {
            "donor_id": donor["id"],
            "amount_paise": 50000,
            "mode": "upi",
            "reason": "monthly_donation",
        },
    ]
    resp = client.post(
        "/api/donations/batch",
        headers=auth_headers,
        data={"period": "2026-03", "items": json.dumps(items)},
        files={f"screenshot_{donor['id']}": ("proof.png", io.BytesIO(_png_bytes()), "image/png")},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["generated"] == 1, body
    assert body["failed"] == 1, body
    generated = next(r for r in body["results"] if r["status"] == "generated")
    assert generated["receipt_no"].startswith("SVMSS/2026/03/")


def test_batch_rejects_bad_period(auth_headers):
    resp = client.post(
        "/api/donations/batch",
        headers=auth_headers,
        data={"period": "March-2026", "items": json.dumps([])},
    )
    assert resp.status_code == 422


def test_batch_requires_auth():
    resp = client.post(
        "/api/donations/batch", data={"period": "2026-03", "items": json.dumps([])}
    )
    assert resp.status_code == 401
