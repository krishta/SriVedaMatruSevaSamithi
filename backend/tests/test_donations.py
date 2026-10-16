import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base, engine
from app.main import app
from scripts.seed import run as seed_run


@pytest.fixture(scope="module", autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=engine)
    seed_run()
    yield


client = TestClient(app)


def _fake_png_bytes() -> bytes:
    # Minimal valid PNG header + IHDR so filetype.guess() detects image/png.
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "3de9000000017352474200aece1ce90000000467414d410000b18f0bfc6105"
        "0000000009706859730000163e00001a5e0d4dbd3a0000000c49444154789c"
        "6360000200000500018e5b5e5a0000000049454e44ae426082"
    )


def test_submit_donation_creates_sequential_receipt():
    files = {"screenshot": ("proof.png", io.BytesIO(_fake_png_bytes()), "image/png")}
    data = {
        "name": "Test Donor",
        "phone": "9876543210",
        "amount_paise": "10000",
        "reason": "general_donation",
        "mode": "upi",
        "upi_txn_id": "UPI123456789",
    }
    resp = client.post("/api/donations", data=data, files=files)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["receipt_no"].startswith("SVMSS/")
    assert body["pdf_url"].startswith("/api/receipts/")


def test_donation_rejects_zero_amount():
    files = {"screenshot": ("proof.png", io.BytesIO(_fake_png_bytes()), "image/png")}
    data = {
        "name": "Test Donor",
        "phone": "9876543210",
        "amount_paise": "0",
        "reason": "general_donation",
        "mode": "upi",
    }
    resp = client.post("/api/donations", data=data, files=files)
    assert resp.status_code == 422


def test_admin_ledger_requires_auth():
    resp = client.get("/api/donations")
    assert resp.status_code == 401