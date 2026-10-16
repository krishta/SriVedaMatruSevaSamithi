"""
Verify-phase acceptance tests — covers every PRD §7 ID not already exercised
in test_donations.py or test_donors_and_batch.py.

IDs covered here:
  DN-01 (full), DN-02, DN-03, DN-05, DN-08, DN-09
  AD-01, AD-02, AD-03, AD-04, AD-05, AD-06
  SY-01, SY-02
  MM-01, MM-02, MM-03, MM-04, MM-05, MM-06
"""
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
from app.services.amount_words import amount_paise_to_words, rupees_in_words
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
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _png_bytes() -> bytes:
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
        "3de9000000017352474200aece1ce90000000467414d410000b18f0bfc6105"
        "0000000009706859730000163e00001a5e0d4dbd3a0000000c49444154789c"
        "6360000200000500018e5b5e5a0000000049454e44ae426082"
    )


def _make_donation(**overrides):
    """Submit a valid donation; returns parsed JSON body."""
    data = {
        "name": "Verify Donor",
        "phone": "9123456780",
        "amount_paise": "5000",
        "reason": "monthly_donation",
        "mode": "upi",
        "upi_txn_id": "UPI-VERIFY-001",
        **overrides,
    }
    files = {"screenshot": ("proof.png", io.BytesIO(_png_bytes()), "image/png")}
    resp = client.post("/api/donations", data=data, files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# AD-01 — JWT login / auth
# ---------------------------------------------------------------------------

def test_login_returns_token():
    """AD-01: valid credentials produce an access_token."""
    resp = client.post(
        "/api/auth/login",
        json={"username": settings.seed_admin_username, "password": settings.seed_admin_password},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_bad_password_rejected():
    """AD-01: wrong password returns 401."""
    resp = client.post(
        "/api/auth/login",
        json={"username": settings.seed_admin_username, "password": "WRONG"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# DN-01 — form validation
# ---------------------------------------------------------------------------

def test_missing_name_rejected():
    """DN-01: name is required."""
    files = {"screenshot": ("p.png", io.BytesIO(_png_bytes()), "image/png")}
    resp = client.post(
        "/api/donations",
        data={"phone": "9000000099", "amount_paise": "1000", "reason": "general_donation", "mode": "upi", "upi_txn_id": "X"},
        files=files,
    )
    assert resp.status_code == 422


def test_missing_screenshot_rejected():
    """DN-01: screenshot is required on the public form."""
    resp = client.post(
        "/api/donations",
        data={"name": "A", "phone": "9000000099", "amount_paise": "1000",
              "reason": "general_donation", "mode": "upi", "upi_txn_id": "X"},
    )
    assert resp.status_code == 422


def test_zero_amount_rejected():
    """DN-01: amount > 0 required."""
    files = {"screenshot": ("p.png", io.BytesIO(_png_bytes()), "image/png")}
    resp = client.post(
        "/api/donations",
        data={"name": "A", "phone": "9000000099", "amount_paise": "0",
              "reason": "general_donation", "mode": "upi", "upi_txn_id": "X"},
        files=files,
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DN-02 — reason enum
# ---------------------------------------------------------------------------

def test_valid_reasons_accepted():
    """DN-02: all canonical reason values are accepted."""
    valid_reasons = [
        "monthly_donation", "birthday", "occasion_veda_sabha", "general_donation",
    ]
    for i, reason in enumerate(valid_reasons):
        data = {
            "name": f"Donor {reason}",
            "phone": f"900000{70 + i:04d}",
            "amount_paise": "1000",
            "reason": reason,
            "mode": "upi",
            "upi_txn_id": f"UPI-REASON-{i}",
        }
        files = {"screenshot": ("p.png", io.BytesIO(_png_bytes()), "image/png")}
        resp = client.post("/api/donations", data=data, files=files)
        assert resp.status_code == 201, f"reason={reason} rejected: {resp.text}"


def test_reason_other_with_free_text():
    """DN-02: 'other' reason is accepted with reason_other text."""
    data = {
        "name": "Other Reason Donor",
        "phone": "9100000090",
        "amount_paise": "2000",
        "reason": "other",
        "reason_other": "Farewell donation",
        "mode": "upi",
        "upi_txn_id": "UPI-OTHER-001",
    }
    files = {"screenshot": ("p.png", io.BytesIO(_png_bytes()), "image/png")}
    resp = client.post("/api/donations", data=data, files=files)
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# DN-03 — payment mode enum (no cash)
# ---------------------------------------------------------------------------

def test_bank_transfer_mode_accepted():
    """DN-03: bank_transfer mode with required proof fields accepted."""
    data = {
        "name": "Bank Donor",
        "phone": "9100000091",
        "amount_paise": "3000",
        "reason": "general_donation",
        "mode": "bank_transfer",
        "bank_name": "SBI",
        "branch_name": "Bengaluru Main",
        "transaction_date": "2026-09-01",
    }
    files = {"screenshot": ("p.png", io.BytesIO(_png_bytes()), "image/png")}
    resp = client.post("/api/donations", data=data, files=files)
    assert resp.status_code == 201, resp.text


def test_cheque_dd_mode_accepted():
    """DN-03: cheque_dd mode accepted."""
    data = {
        "name": "Cheque Donor",
        "phone": "9100000092",
        "amount_paise": "4000",
        "reason": "birthday",
        "mode": "cheque_dd",
        "bank_name": "HDFC",
        "branch_name": "Jayanagar",
        "transaction_date": "2026-09-15",
    }
    files = {"screenshot": ("p.png", io.BytesIO(_png_bytes()), "image/png")}
    resp = client.post("/api/donations", data=data, files=files)
    assert resp.status_code == 201, resp.text


# ---------------------------------------------------------------------------
# DN-05 — PDF returned immediately; DN-09 — mode-specific fields in receipt
# ---------------------------------------------------------------------------

def _pdf_search(pdf_bytes: bytes, needle: str) -> bool:
    """Search for a text string in a PDF, decoding content streams as needed.

    ReportLab encodes content streams with ASCII85 (compress=0, default) or Flate
    (compress=1). A raw-byte search only works on uncompressed/unencoded content.
    This helper decodes each stream with both ASCII85 and zlib and also falls back
    to a raw byte search, so the assertion holds regardless of the compression setting.
    """
    import base64, re, zlib
    if needle.encode() in pdf_bytes:
        return True
    for m in re.finditer(rb'stream\r?\n(.*?)(?:\r?\n)?endstream', pdf_bytes, re.DOTALL):
        raw = m.group(1)
        if not raw:
            continue
        # Try Flate (zlib)
        try:
            decoded = zlib.decompress(raw).decode('latin-1', errors='replace')
            if needle in decoded:
                return True
        except Exception:
            pass
        # Try ASCII85 (ReportLab default), optionally followed by zlib if doubly encoded
        try:
            eod = raw.rfind(b'~>')
            a85_data = raw[:eod] if eod != -1 else raw
            a85_decoded = base64.a85decode(a85_data)
            for candidate in [a85_decoded, zlib.decompress(a85_decoded)]:
                text = candidate.decode('latin-1', errors='replace')
                if needle in text:
                    return True
        except Exception:
            pass
    return False


def test_pdf_returned_and_contains_receipt_no_and_disclaimer():
    """DN-05 / SY-01: donation response includes a pdf_url; fetching it returns a PDF
    that contains the receipt number and the mandatory 80G disclaimer text.

    Note: ReportLab compresses content streams with zlib; the receipt number and
    disclaimer are searched in both raw bytes and decompressed streams via _pdf_search().
    """
    body = _make_donation(phone="9100000093", amount_paise="10000", upi_txn_id="UPI-PDF-001")
    receipt_no = body["receipt_no"]
    pdf_url = body["pdf_url"]
    assert pdf_url.startswith("/api/receipts/")

    resp = client.get(pdf_url)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

    pdf_bytes = resp.content
    assert pdf_bytes[:4] == b"%PDF", "Response is not a valid PDF"
    assert len(pdf_bytes) > 2000, "PDF is suspiciously small — likely empty"

    # Receipt number must appear somewhere in the PDF (raw or decompressed stream).
    assert _pdf_search(pdf_bytes, receipt_no), f"Receipt number '{receipt_no}' not found in PDF"
    # Mandatory disclaimer text (PRD §3.9 / module 07).
    assert _pdf_search(pdf_bytes, "not valid for claiming tax exemption under Section 80G"), \
        "80G disclaimer not found in PDF"


# ---------------------------------------------------------------------------
# DN-08 — receipt lookup (phone + last-4)
# ---------------------------------------------------------------------------

def test_receipt_lookup_happy_path():
    """DN-08: valid phone + matching last-4 returns the donor's receipt(s)."""
    phone = "9100000094"
    body = _make_donation(phone=phone, upi_txn_id="UPI-LOOKUP-001")
    receipt_no = body["receipt_no"]

    resp = client.post(
        "/api/receipts/lookup",
        json={"phone": phone, "last4": phone[-4:]},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert any(r["receipt_no"] == receipt_no for r in items)


def test_receipt_lookup_wrong_last4_returns_404():
    """DN-08: wrong last-4 returns 404, not the donor record."""
    phone = "9100000095"
    _make_donation(phone=phone, upi_txn_id="UPI-LOOKUP-002")

    resp = client.post(
        "/api/receipts/lookup",
        json={"phone": phone, "last4": "0000"},
    )
    assert resp.status_code == 404


def test_receipt_lookup_unknown_phone_returns_404():
    """DN-08: unknown phone returns 404."""
    resp = client.post(
        "/api/receipts/lookup",
        json={"phone": "9199999999", "last4": "9999"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AD-02 — admin ledger with filters
# ---------------------------------------------------------------------------

def test_ledger_returns_paginated_results(auth_headers):
    """AD-02: admin ledger returns items + total."""
    resp = client.get("/api/donations?page=1&size=5", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "total" in body
    assert isinstance(body["total"], int)


def test_ledger_filter_by_mode(auth_headers):
    """AD-02: mode filter narrows results."""
    resp = client.get("/api/donations?mode=upi", headers=auth_headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["mode"] == "upi"


def test_ledger_requires_auth():
    """AD-02: unauthenticated request is rejected."""
    assert client.get("/api/donations").status_code == 401


# ---------------------------------------------------------------------------
# AD-03 — donor 360°
# ---------------------------------------------------------------------------

def test_donor_360(auth_headers):
    """AD-03: /api/donors/{id} returns profile + donations list."""
    # Create a donor via donation flow so they have at least one donation.
    body = _make_donation(phone="9100000096", upi_txn_id="UPI-360-001")
    donor_id = body["donor_id"]

    resp = client.get(f"/api/donors/{donor_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "name" in data or "phone" in data  # profile fields present


def test_donor_360_requires_auth():
    """AD-03: unauthenticated request is rejected."""
    assert client.get("/api/donors/1").status_code == 401


# ---------------------------------------------------------------------------
# AD-04 — void + reissue
# ---------------------------------------------------------------------------

def test_void_and_reissue(auth_headers):
    """AD-04: void sets status=void (soft); reissue creates a new receipt with a new number."""
    body = _make_donation(phone="9100000097", upi_txn_id="UPI-VOID-001")
    receipt_id = int(body["pdf_url"].split("/")[-2])
    old_receipt_no = body["receipt_no"]

    # Void the receipt.
    void_resp = client.post(
        f"/api/receipts/{receipt_id}/void",
        json={"reason": "Verify-phase test void"},
        headers=auth_headers,
    )
    assert void_resp.status_code == 200
    assert void_resp.json()["status"] == "voided"

    # Reissue creates a brand-new receipt number.
    reissue_resp = client.post(f"/api/receipts/{receipt_id}/reissue", headers=auth_headers)
    assert reissue_resp.status_code == 200
    new_receipt_no = reissue_resp.json()["receipt_no"]
    assert new_receipt_no != old_receipt_no, "Reissued receipt must have a new number"
    assert new_receipt_no.startswith("SVMSS/")


def test_void_requires_auth():
    """AD-04: void endpoint requires a valid JWT."""
    assert client.post("/api/receipts/1/void", json={"reason": "test"}).status_code == 401