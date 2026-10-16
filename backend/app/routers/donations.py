import csv
import io
import json
import re
from datetime import date, datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models import AdminUser, Donation, Donor, Receipt
from app.schemas import (
    BatchReceiptItem,
    BatchReceiptResponse,
    DonationCreateResponse,
    DonationListItem,
    DonationListResponse,
)
from app.services.batch_receipts import generate_batch_receipts
from app.services.donations import create_donation

router = APIRouter(prefix="/api/donations", tags=["donations"])
limiter = Limiter(key_func=get_remote_address)


@router.post("", response_model=DonationCreateResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
async def submit_donation(
    request: Request,  # required first positional arg for slowapi
    name: str = Form(...),
    phone: str = Form(...),
    email: str | None = Form(None),
    address: str | None = Form(None),
    amount_paise: int = Form(...),
    reason: str = Form(...),
    reason_other: str | None = Form(None),
    mode: str = Form(...),
    upi_txn_id: str | None = Form(None),
    bank_name: str | None = Form(None),
    branch_name: str | None = Form(None),
    transaction_date: date | None = Form(None),
    screenshot: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    donation, receipt, email_sent = create_donation(
        db,
        name=name,
        phone=phone,
        email=email,
        address=address,
        amount_paise=amount_paise,
        reason=reason,
        reason_other=reason_other,
        mode=mode,
        upi_txn_id=upi_txn_id,
        bank_name=bank_name,
        branch_name=branch_name,
        transaction_date=transaction_date,
        screenshot=screenshot,
    )
    return DonationCreateResponse(
        donation_id=donation.id,
        donor_id=donation.donor_id,
        receipt_no=receipt.receipt_no,
        pdf_url=f"/api/receipts/{receipt.id}/pdf",
        email_sent=email_sent,
    )


@router.post("/batch", response_model=BatchReceiptResponse, status_code=status.HTTP_201_CREATED)
async def batch_generate_receipts(
    request: Request,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    """Month-end bulk issuance (PRD AD-08).

    multipart/form-data:
      - `period`: "YYYY-MM"
      - `items`:  JSON array of BatchReceiptItem
      - `screenshot_<donor_id>`: optional file per donor
    """
    form = await request.form()

    period = str(form.get("period") or "")
    if not re.fullmatch(r"\d{4}-\d{2}", period) or not 1 <= int(period[5:]) <= 12:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "period must be in YYYY-MM format")

    raw_items = form.get("items")
    if not raw_items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "items is required")
    try:
        parsed = json.loads(str(raw_items))
        items = [BatchReceiptItem(**row) for row in parsed]
    except (ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid items payload: {exc}")
    if not items:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Select at least one donor")

    screenshots: dict[int, tuple[str, bytes]] = {}
    for item in items:
        # Read each upload at most once — a second read() on the same handle returns b"".
        if item.donor_id in screenshots:
            continue
        upload = form.get(f"screenshot_{item.donor_id}")
        if isinstance(upload, StarletteUploadFile):
            await upload.seek(0)
            screenshots[item.donor_id] = (upload.filename or "upload.bin", await upload.read())

    results = generate_batch_receipts(
        db, admin_id=admin.id, period=period, items=items, screenshots=screenshots
    )
    return BatchReceiptResponse(
        period=period,
        generated=sum(1 for r in results if r.status == "generated"),
        failed=sum(1 for r in results if r.status == "failed"),
        results=results,
    )


@router.get("", response_model=DonationListResponse)
def list_donations(
    search: str | None = None,
    reason: str | None = None,
    mode: str | None = None,
    status_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    q = select(Donation, Donor).join(Donor, Donation.donor_id == Donor.id)
    if search:
        like = f"%{search}%"
        q = q.where((Donor.name.ilike(like)) | (Donor.phone.ilike(like)))
    if reason:
        q = q.where(Donation.reason == reason)
    if mode:
        q = q.where(Donation.mode == mode)
    if status_filter:
        q = q.where(Donation.status == status_filter)
    if date_from:
        q = q.where(Donation.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.where(Donation.created_at <= datetime.combine(date_to, datetime.max.time()))

    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    rows = db.execute(
        q.order_by(Donation.created_at.desc(), Donation.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    items = [
        DonationListItem(
            id=d.id,
            donor_id=donor.id,
            donor_name=donor.name,
            donor_phone=donor.phone,
            amount_paise=d.amount_paise,
            reason=d.reason,
            reason_other=d.reason_other,
            mode=d.mode,
            status=d.status,
            receipt_id=d.receipt.id if d.receipt else None,
            receipt_no=d.receipt.receipt_no if d.receipt else None,
            created_at=d.created_at,
        )
        for d, donor in rows
    ]
    return DonationListResponse(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_donations_csv(
    search: str | None = None,
    reason: str | None = None,
    mode: str | None = None,
    status_filter: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    q = (
        select(Donation, Donor, Receipt)
        .join(Donor, Donation.donor_id == Donor.id)
        .outerjoin(Receipt, Receipt.donation_id == Donation.id)
    )
    if search:
        like = f"%{search}%"
        q = q.where((Donor.name.ilike(like)) | (Donor.phone.ilike(like)))
    if reason:
        q = q.where(Donation.reason == reason)
    if mode:
        q = q.where(Donation.mode == mode)
    if status_filter:
        q = q.where(Donation.status == status_filter)
    if date_from:
        q = q.where(Donation.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.where(Donation.created_at <= datetime.combine(date_to, datetime.max.time()))

    rows = db.execute(q.order_by(Donation.created_at.desc())).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Date", "Donor", "Phone", "Amount (INR)", "Reason", "Mode", "Status", "Receipt No"]
    )
    for d, donor, receipt in rows:
        writer.writerow(
            [
                d.created_at.strftime("%Y-%m-%d"),
                donor.name,
                donor.phone,
                f"{d.amount_paise / 100:.2f}",
                d.reason_other if d.reason == "other" else d.reason,
                d.mode,
                d.status,
                receipt.receipt_no if receipt else "",
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=svmss_donations.csv"},
    )


@router.get("/{donation_id}/screenshot")
def get_screenshot(
    donation_id: int, db: Session = Depends(get_db), _admin: AdminUser = Depends(get_current_admin)
):
    donation = db.get(Donation, donation_id)
    if not donation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donation not found")
    from app.services.storage import upload_storage

    content = upload_storage.read(donation.screenshot_path)
    return StreamingResponse(io.BytesIO(content), media_type="application/octet-stream")