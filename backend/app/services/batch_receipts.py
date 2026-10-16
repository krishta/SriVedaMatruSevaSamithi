import json
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Donation, Donor
from app.schemas import BatchReceiptItem, BatchReceiptResultItem
from app.services.donations import (
    MODE_FIELD_GROUPS,
    issue_receipt_for_donation,
    validate_payment_fields,
    validate_upload_content,
)
from app.services.storage import upload_storage

logger = logging.getLogger(__name__)


def generate_batch_receipts(
    db: Session,
    *,
    admin_id: int,
    period: str,
    items: list[BatchReceiptItem],
    screenshots: dict[int, tuple[str, bytes]],
) -> list[BatchReceiptResultItem]:
    """Issues one receipt per selected donor for the given period ("YYYY-MM").

    Each donor is processed independently: one bad row fails only that row, so a long
    month-end batch never loses already-generated receipts.
    """
    results: list[BatchReceiptResultItem] = []

    for item in items:
        donor = db.get(Donor, item.donor_id)
        if not donor or not donor.is_active:
            results.append(
                BatchReceiptResultItem(
                    donor_id=item.donor_id,
                    donor_name="(unknown)",
                    status="failed",
                    error="Donor not found or inactive",
                )
            )
            continue

        try:
            validate_payment_fields(
                reason=item.reason,
                reason_other=item.reason_other,
                mode=item.mode,
                upi_txn_id=item.upi_txn_id,
                bank_name=item.bank_name,
                branch_name=item.branch_name,
                transaction_date=item.transaction_date,
            )

            screenshot_path = None
            if item.donor_id in screenshots:
                filename, content = screenshots[item.donor_id]
                validate_upload_content(content)
                screenshot_path = upload_storage.save("screenshots", filename or "upload.bin", content)

            is_bank_like = item.mode in MODE_FIELD_GROUPS["bank_like"]
            donation = Donation(
                donor_id=donor.id,
                amount_paise=item.amount_paise,
                reason=item.reason,
                reason_other=item.reason_other if item.reason == "other" else None,
                mode=item.mode,
                upi_txn_id=item.upi_txn_id if item.mode == "upi" else None,
                bank_name=item.bank_name if is_bank_like else None,
                branch_name=item.branch_name if is_bank_like else None,
                transaction_date=item.transaction_date if is_bank_like else None,
                screenshot_path=screenshot_path,
                status="issued",
            )
            db.add(donation)
            db.flush()

            receipt, email_sent = issue_receipt_for_donation(db, donor, donation, period=period)

            db.add(
                AuditLog(
                    actor_admin_id=admin_id,
                    action="receipt.batch_generate",
                    entity_type="receipt",
                    entity_id=receipt.id,
                    detail_json=json.dumps(
                        {"period": period, "donor_id": donor.id, "receipt_no": receipt.receipt_no}
                    ),
                )
            )
            db.commit()

            results.append(
                BatchReceiptResultItem(
                    donor_id=donor.id,
                    donor_name=donor.name,
                    status="generated",
                    receipt_no=receipt.receipt_no,
                    receipt_id=receipt.id,
                    pdf_url=f"/api/receipts/{receipt.id}/pdf",
                    email_sent=email_sent,
                )
            )
        except HTTPException as exc:
            db.rollback()
            results.append(
                BatchReceiptResultItem(
                    donor_id=donor.id,
                    donor_name=donor.name,
                    status="failed",
                    error=str(exc.detail),
                )
            )
        except Exception as exc:
            db.rollback()
            logger.exception("Batch receipt generation failed for donor %s", donor.id)
            results.append(
                BatchReceiptResultItem(
                    donor_id=donor.id,
                    donor_name=donor.name,
                    status="failed",
                    error=f"Unexpected error: {exc}",
                )
            )

    return results