import io
from collections import defaultdict
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models import (
    AdminUser,
    Donation,
    DonationReason,
    DonationReasonSnapshot,
    Donor,
    Receipt,
)
from app.schemas import DonationReportRequest
from app.services.donation_reasons import reason_label_for_donation

router = APIRouter(prefix="/api/reports", tags=["reports"])

REPORT_TYPES = {
    "reason_period",
    "monthly_donations",
    "donor_summary",
    "payment_reconciliation",
    "receipt_register",
}
REPORT_COLUMNS = {
    "donor_name": "Donor name",
    "donation_date": "Donation received date",
    "receipt_date": "Receipt issue date",
    "reason": "Reason",
    "amount": "Amount (INR)",
    "payment_mode": "Payment method",
    "donation_status": "Donation status",
    "receipt_no": "Receipt number",
    "phone": "Phone",
    "email": "Email",
    "address": "Address",
    "reason_detail": "Reason details",
}
REQUIRED_COLUMNS = {"donor_name", "donation_date", "receipt_date", "reason", "amount"}


def _safe_excel_string(value: str) -> str:
    if value.startswith(("=", "+", "-", "@")):
        return f"'{value}"
    return value


def _append_sheet(workbook: Workbook, title: str, headers: list[str], rows: list[list]):
    sheet = workbook.create_sheet(title)
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="B3661F")
    for row in rows:
        sheet.append([_safe_excel_string(value) if isinstance(value, str) else value for value in row])
    sheet.freeze_panes = "A2"
    if sheet.max_row > 1:
        sheet.auto_filter.ref = sheet.dimensions
    for index, header in enumerate(headers, 1):
        values = [str(sheet.cell(row, index).value or "") for row in range(1, min(sheet.max_row, 100) + 1)]
        sheet.column_dimensions[get_column_letter(index)].width = min(max(map(len, values)) + 2, 36)
    return sheet


def _summary_rows(report_type: str, records: list[dict]) -> tuple[list[str], list[list]]:
    if report_type == "reason_period":
        groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for record in records:
            groups[record["reason"]][0] += 1
            groups[record["reason"]][1] += record["amount_paise"]
        rows = [[reason, values[0], values[1] / 100] for reason, values in sorted(groups.items())]
        return ["Reason", "Donation count", "Total amount (INR)"], rows

    if report_type == "monthly_donations":
        groups: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for record in records:
            donation_date = record["donation_date"]
            month = donation_date.strftime("%Y-%m") if donation_date else ""
            groups[(month, record["donor_name"])][0] += 1
            groups[(month, record["donor_name"])][1] += record["amount_paise"]
        rows = [
            [month, donor_name, values[0], values[1] / 100]
            for (month, donor_name), values in sorted(groups.items())
        ]
        return ["Month", "Donor name", "Donation count", "Total amount (INR)"], rows

    if report_type == "donor_summary":
        groups: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
        for record in records:
            key = (record["donor_name"], record["phone"])
            groups[key][0] += 1
            groups[key][1] += record["amount_paise"]
        rows = [
            [name, phone, values[0], values[1] / 100]
            for (name, phone), values in sorted(groups.items())
        ]
        return ["Donor name", "Phone", "Donation count", "Total amount (INR)"], rows

    if report_type == "payment_reconciliation":
        groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for record in records:
            groups[record["payment_mode"]][0] += 1
            groups[record["payment_mode"]][1] += record["amount_paise"]
        rows = [
            [mode, values[0], values[1] / 100]
            for mode, values in sorted(groups.items())
        ]
        return ["Payment method", "Donation count", "Total amount (INR)"], rows

    groups: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for record in records:
        groups[record["donation_status"]][0] += 1
        groups[record["donation_status"]][1] += record["amount_paise"]
    rows = [
        [receipt_status, values[0], values[1] / 100]
        for receipt_status, values in sorted(groups.items())
    ]
    return ["Receipt status", "Receipt count", "Total amount (INR)"], rows


def _date_filters(query, request: DonationReportRequest):
    if request.date_from and request.date_to and request.date_from > request.date_to:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "date_from must be on or before date_to",
        )
    if request.date_from:
        query = query.where(
            Donation.created_at >= datetime.combine(request.date_from, time.min)
        )
    if request.date_to:
        query = query.where(
            Donation.created_at <= datetime.combine(request.date_to, time.max)
        )
    return query


@router.post("/export")
def export_report(
    request: DonationReportRequest,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    if request.report_type not in REPORT_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unsupported report type")
    if len(set(request.columns)) != len(request.columns):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Report columns must be unique")
    invalid_columns = set(request.columns) - REPORT_COLUMNS.keys()
    if invalid_columns:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unsupported report column")
    if not REQUIRED_COLUMNS.issubset(request.columns):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Donor, both dates, reason, and amount columns are required",
        )
    if request.reason_code and request.report_type == "monthly_donations":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Monthly donations report already filters to Monthly Donation",
        )
    if request.reason_code and db.scalar(
        select(DonationReason.id).where(DonationReason.code == request.reason_code)
    ) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown donation reason")
    if db.scalar(select(func.count()).select_from(Donation)) == 0:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No donations matched the selected filters",
        )

    latest_receipt = (
        select(Receipt.donation_id, func.max(Receipt.id).label("receipt_id"))
        .group_by(Receipt.donation_id)
        .subquery()
    )
    base_query = (
        select(Donation, Donor, DonationReasonSnapshot, Receipt)
        .join(Donor, Donation.donor_id == Donor.id)
        .outerjoin(
            DonationReasonSnapshot,
            DonationReasonSnapshot.donation_id == Donation.id,
        )
        .outerjoin(latest_receipt, latest_receipt.c.donation_id == Donation.id)
        .outerjoin(Receipt, Receipt.id == latest_receipt.c.receipt_id)
    )
    if request.report_type == "monthly_donations":
        base_query = base_query.where(Donation.reason == "monthly_donation")
    elif request.reason_code:
        base_query = base_query.where(Donation.reason == request.reason_code)
    if not request.include_voided:
        base_query = base_query.where(Donation.status != "void")
    base_query = _date_filters(base_query, request)

    if request.report_type == "receipt_register":
        receipt_query = (
            select(Receipt, Donation, Donor, DonationReasonSnapshot)
            .join(Donation, Receipt.donation_id == Donation.id)
            .join(Donor, Donation.donor_id == Donor.id)
            .outerjoin(
                DonationReasonSnapshot,
                DonationReasonSnapshot.donation_id == Donation.id,
            )
        )
        if not request.include_voided:
            receipt_query = receipt_query.where(Receipt.voided_at.is_(None))
        if request.reason_code:
            receipt_query = receipt_query.where(Donation.reason == request.reason_code)
        receipt_query = _date_filters(receipt_query, request)
        result_rows = db.execute(
            receipt_query.order_by(Donation.created_at, Receipt.issued_at, Receipt.id)
        ).all()
        records = [
            _make_record(donation, donor, snapshot, receipt)
            for receipt, donation, donor, snapshot in result_rows
        ]
    else:
        result_rows = db.execute(
            base_query.order_by(Donation.created_at, Donation.id)
        ).all()
        records = [
            _make_record(donation, donor, snapshot, receipt)
            for donation, donor, snapshot, receipt in result_rows
        ]

    if not records:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No donations matched the selected filters",
        )

    workbook = Workbook()
    workbook.remove(workbook.active)
    details = [
        [
            record[column]
            if column not in {"amount"}
            else record["amount_paise"] / 100
            for column in request.columns
        ]
        for record in records
    ]
    details_sheet = _append_sheet(
        workbook,
        "Donations",
        [REPORT_COLUMNS[column] for column in request.columns],
        details,
    )
    amount_column = request.columns.index("amount") + 1
    for row in range(2, details_sheet.max_row + 1):
        details_sheet.cell(row, amount_column).number_format = "#,##0.00"

    summary_headers, summary = _summary_rows(request.report_type, records)
    summary_sheet = _append_sheet(workbook, "Summary", summary_headers, summary)
    for row in range(2, summary_sheet.max_row + 1):
        summary_sheet.cell(row, summary_sheet.max_column).number_format = "#,##0.00"

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    filename = f"svmss_{request.report_type}_{request.date_from or 'all'}_{request.date_to or 'all'}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _make_record(donation, donor, snapshot, receipt) -> dict:
    reason_label = (
        donation.reason_other
        if donation.reason == "other" and donation.reason_other
        else snapshot.label
        if snapshot
        else reason_label_for_donation(donation)
    )
    receipt_status = "void" if receipt and receipt.voided_at else "issued"
    return {
        "donor_name": donor.name,
        "donation_date": donation.created_at,
        "receipt_date": receipt.issued_at if receipt else None,
        "reason": reason_label,
        "amount": donation.amount_paise / 100,
        "amount_paise": donation.amount_paise,
        "payment_mode": donation.mode,
        "donation_status": receipt_status if receipt else donation.status,
        "receipt_no": receipt.receipt_no if receipt else "",
        "phone": donor.phone,
        "email": donor.email or "",
        "address": donor.address or "",
        "reason_detail": donation.reason_other or "",
    }
