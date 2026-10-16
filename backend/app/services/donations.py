import json
import re
from datetime import date, datetime, timezone
from pathlib import Path

import filetype
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import AuditLog, Donation, Donor, NgoSettings, PeriodCounter, Receipt
from app.services.period import current_period
from app.services.notifications import send_receipt_notifications
from app.services.pdf import render_receipt_pdf
from app.services.storage import receipt_storage, upload_storage

ALLOWED_MIME = {"image/jpeg", "image/png", "application/pdf"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

VALID_REASONS = {
    "monthly_donation",
    "birthday",
    "occasion_veda_sabha",
    "general_donation",
    "other",
}
# "cash" removed (PRD DN-03 update) — every mode now leaves a verifiable trail.
VALID_MODES = {"upi", "bank_transfer", "cheque_dd"}

# Which modes require which conditional proof fields (PRD DN-09).
MODE_FIELD_GROUPS = {"upi": {"upi"}, "bank_like": {"bank_transfer", "cheque_dd"}}


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("91") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+91{digits}"
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid Indian phone number")


def validate_upload_content(content: bytes) -> str:
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "File exceeds 5MB limit")
    kind = filetype.guess(content)
    mime = kind.mime if kind else None
    if mime not in ALLOWED_MIME:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Only JPEG/PNG/PDF screenshots are accepted"
        )
    return mime


def _get_or_create_donor(db: Session, phone: str, name: str, email: str | None, address: str | None) -> Donor:
    donor = db.execute(select(Donor).where(Donor.phone == phone)).scalar_one_or_none()
    if donor:
        # Keep the donor record fresh with whatever was submitted this time (PRD: donor is
        # keyed by phone, but people's name/email/address can legitimately change or have
        # been mistyped previously) — previously this silently kept the *first-ever* name.
        donor.name = name
        donor.email = email
        donor.address = address
        donor.is_active = True
        return donor
    donor = Donor(phone=phone, name=name, email=email, address=address, is_active=True)
    db.add(donor)
    db.flush()
    return donor


def _allocate_receipt_no(db: Session, period: str | None = None) -> tuple[str, str, int]:
    """Atomic per-calendar-month sequence allocation (module 02 invariant 1).

    Format: SVMSS/YYYY/MM/000005 — the running number never resets mid-month and is never
    reused, even across voids (module 02 invariant 2). `period` ("YYYY-MM") lets an admin
    batch back-date receipts to the donation month; defaults to the current month.
    """
    period = period or current_period()
    counter = db.execute(
        select(PeriodCounter).where(PeriodCounter.period == period).with_for_update()
    ).scalar_one_or_none()
    if counter is None:
        counter = PeriodCounter(period=period, next_seq=1)
        db.add(counter)
        db.flush()
    seq = counter.next_seq
    counter.next_seq = seq + 1
    year, month = period.split("-")
    receipt_no = f"SVMSS/{year}/{month}/{seq:06d}"
    return receipt_no, period, seq


def validate_payment_fields(
    *,
    reason: str,
    reason_other: str | None,
    mode: str,
    upi_txn_id: str | None,
    bank_name: str | None,
    branch_name: str | None,
    transaction_date: date | None,
) -> None:
    """Shared reason/mode validation for both the public form and admin batch generation."""
    if reason not in VALID_REASONS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid donation reason")
    if reason == "other" and not reason_other:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "reason_other is required when reason=other")
    if mode not in VALID_MODES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid payment mode")
    if mode == "upi" and not upi_txn_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "upi_txn_id is required when mode=upi")
    if mode in ("bank_transfer", "cheque_dd"):
        if not bank_name or not branch_name or not transaction_date:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "bank_name, branch_name and transaction_date are required for bank_transfer/cheque_dd",
            )


def issue_receipt_for_donation(
    db: Session, donor: Donor, donation: Donation, period: str | None = None
) -> tuple[Receipt, bool]:
    """Allocates a number, renders the PDF and sends notifications for an already-created
    donation. Shared by the public form and admin batch generation."""
    receipt_no, resolved_period, seq = _allocate_receipt_no(db, period)
    receipt = Receipt(
        donation_id=donation.id,
        receipt_no=receipt_no,
        period=resolved_period,
        sequence_no=seq,
        pdf_path="",  # filled in after the transaction commits
    )
    db.add(receipt)
    db.commit()
    db.refresh(donation)
    db.refresh(receipt)
    db.refresh(donor)

    # Outside the transaction: PDF render + best-effort email (never rolls back a committed donation).
    ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one()
    pdf_relative_path = render_receipt_pdf(donor, donation, receipt, ngo)
    receipt.pdf_path = pdf_relative_path
    db.commit()

    email_sent = send_receipt_notifications(
        donor, receipt, receipt_storage.absolute_path(pdf_relative_path)
    )
    return receipt, email_sent


def create_donation(
    db: Session,
    *,
    name: str,
    phone: str,
    email: str | None,
    address: str | None,
    amount_paise: int,
    reason: str,
    reason_other: str | None,
    mode: str,
    upi_txn_id: str | None,
    bank_name: str | None,
    branch_name: str | None,
    transaction_date: date | None,
    screenshot: UploadFile,
) -> tuple[Donation, Receipt, bool]:
    if amount_paise <= 0:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Amount must be greater than zero")
    validate_payment_fields(
        reason=reason,
        reason_other=reason_other,
        mode=mode,
        upi_txn_id=upi_txn_id,
        bank_name=bank_name,
        branch_name=branch_name,
        transaction_date=transaction_date,
    )

    content = screenshot.file.read()
    validate_upload_content(content)
    normalized_phone = normalize_phone(phone)

    # Single DB transaction: donor + donation + receipt-number allocation + receipt row.
    donor = _get_or_create_donor(db, normalized_phone, name, email, address)
    screenshot_path = upload_storage.save("screenshots", screenshot.filename or "upload.bin", content)

    donation = Donation(
        donor_id=donor.id,
        amount_paise=amount_paise,
        reason=reason,
        reason_other=reason_other if reason == "other" else None,
        mode=mode,
        upi_txn_id=upi_txn_id if mode == "upi" else None,
        bank_name=bank_name if mode in ("bank_transfer", "cheque_dd") else None,
        branch_name=branch_name if mode in ("bank_transfer", "cheque_dd") else None,
        transaction_date=transaction_date if mode in ("bank_transfer", "cheque_dd") else None,
        screenshot_path=screenshot_path,
        status="issued",
    )
    db.add(donation)
    db.flush()

    receipt, email_sent = issue_receipt_for_donation(db, donor, donation)
    return donation, receipt, email_sent


def void_receipt(db: Session, receipt: Receipt, reason: str, admin_id: int) -> None:
    if receipt.voided_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Receipt already voided")
    receipt.voided_at = datetime.now(timezone.utc)
    receipt.void_reason = reason
    receipt.donation.status = "void"
    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="receipt.void",
            entity_type="receipt",
            entity_id=receipt.id,
            detail_json=json.dumps({"reason": reason, "receipt_no": receipt.receipt_no}),
        )
    )
    db.commit()


def reissue_receipt(db: Session, voided_receipt: Receipt, admin_id: int) -> Receipt:
    if voided_receipt.voided_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only a voided receipt can be reissued")

    donation = voided_receipt.donation
    donor = donation.donor
    receipt_no, period, seq = _allocate_receipt_no(db)
    new_receipt = Receipt(
        donation_id=donation.id,
        receipt_no=receipt_no,
        period=period,
        sequence_no=seq,
        pdf_path="",
        reissue_of_receipt_id=voided_receipt.id,
    )
    donation.status = "issued"
    db.add(new_receipt)
    db.commit()
    db.refresh(new_receipt)

    ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one()
    pdf_relative_path = render_receipt_pdf(donor, donation, new_receipt, ngo)
    new_receipt.pdf_path = pdf_relative_path

    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="receipt.reissue",
            entity_type="receipt",
            entity_id=new_receipt.id,
            detail_json=json.dumps(
                {"reissue_of": voided_receipt.receipt_no, "new_receipt_no": receipt_no}
            ),
        )
    )
    db.commit()
    db.refresh(new_receipt)
    return new_receipt