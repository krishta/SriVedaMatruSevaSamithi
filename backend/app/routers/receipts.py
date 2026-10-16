import io

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models import AdminUser, Donor, Receipt
from app.schemas import ReceiptLookupItem, ReceiptLookupRequest, VoidRequest
from app.services.donations import normalize_phone, reissue_receipt, void_receipt
from app.services.storage import receipt_storage

router = APIRouter(prefix="/api/receipts", tags=["receipts"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/lookup", response_model=list[ReceiptLookupItem])
@limiter.limit("20/hour")
def lookup_receipts(request: Request, body: ReceiptLookupRequest, db: Session = Depends(get_db)):
    phone = normalize_phone(body.phone)
    if phone[-4:] != body.last4:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No matching donor found")

    donor = db.execute(select(Donor).where(Donor.phone == phone)).scalar_one_or_none()
    if not donor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No matching donor found")

    results = []
    for donation in donor.donations:
        if donation.receipt:
            results.append(
                ReceiptLookupItem(
                    receipt_no=donation.receipt.receipt_no,
                    amount_paise=donation.amount_paise,
                    reason=donation.reason_other if donation.reason == "other" else donation.reason,
                    status=donation.status,
                    issued_at=donation.receipt.issued_at,
                    pdf_url=f"/api/receipts/{donation.receipt.id}/pdf",
                )
            )
    return results


@router.get("/{receipt_id}/pdf")
def get_receipt_pdf(receipt_id: int, db: Session = Depends(get_db)):
    receipt = db.get(Receipt, receipt_id)
    if not receipt or not receipt.pdf_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    content = receipt_storage.read(receipt.pdf_path)
    return StreamingResponse(
        io.BytesIO(content),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={receipt.receipt_no.replace('/', '_')}.pdf"},
    )


@router.post("/{receipt_id}/void")
def void(
    receipt_id: int,
    body: VoidRequest,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    void_receipt(db, receipt, body.reason, admin.id)
    return {"status": "voided", "receipt_no": receipt.receipt_no}


@router.post("/{receipt_id}/reissue")
def reissue(
    receipt_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    receipt = db.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    new_receipt = reissue_receipt(db, receipt, admin.id)
    return {"status": "reissued", "receipt_no": new_receipt.receipt_no, "receipt_id": new_receipt.id}