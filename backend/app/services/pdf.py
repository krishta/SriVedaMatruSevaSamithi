import io
import json
import logging
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.db.models import Donation, Donor, NgoSettings, Receipt
from app.services.amount_words import amount_paise_to_words, format_inr_ascii
from app.services.storage import receipt_storage

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_BOX_CM = 2.2  # square logo box, top-left of the receipt

_REASON_LABELS = {
    "monthly_donation": "Monthly Donation",
    "birthday": "Birthday",
    "occasion_veda_sabha": "Occasion / Veda Sabha",
    "general_donation": "General Donation",
    "other": "Other",
}

_MODE_LABELS = {
    "upi": "UPI",
    "bank_transfer": "Bank Transfer",
    "cheque_dd": "Cheque / DD",
}

DISCLAIMER = (
    "This is a computer-generated acknowledgement of donation and no signature is required "
    "and is not valid for claiming tax exemption under Section 80G."
)

# Fixed columns so every field's ":" lines up, regardless of label length (Helvetica isn't
# monospace, so naive string-padding never aligns).
_LABEL_X_OFFSET = 0
_COLON_X_OFFSET = 4.6 * cm
_VALUE_X_OFFSET = _COLON_X_OFFSET + 0.3 * cm
_VALUE_WRAP_CHARS = 58


def _phone_display(phone_e164: str) -> str:
    digits = phone_e164.replace("+91", "")
    if len(digits) == 10:
        return f"+91 {digits[:5]} {digits[5:]}"
    return phone_e164


def _receipt_donor_name(name: str) -> str:
    parts = name.split()
    if parts and parts[0].casefold() in {"sri", "sri."}:
        parts = parts[1:]
    if parts and parts[-1].casefold() == "garu":
        parts = parts[:-1]
    donor_name = " ".join(parts)
    return f"Sri {donor_name} garu" if donor_name else "Sri garu"


def _wrap(text: str, width_chars: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width_chars and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_field(c: canvas.Canvas, left: float, y: float, label: str, value: str) -> float:
    """Draws one 'Label : Value' row with the colon aligned to a fixed column, wrapping long
    values onto continuation lines under the value column. Returns the y for the next field."""
    lines = _wrap(value, _VALUE_WRAP_CHARS) or [""]
    c.setFont("Helvetica", 10.5)
    c.drawString(left + _LABEL_X_OFFSET, y, label)
    c.drawString(left + _COLON_X_OFFSET, y, ":")
    c.drawString(left + _VALUE_X_OFFSET, y, lines[0])
    for extra_line in lines[1:]:
        y -= 14
        c.drawString(left + _VALUE_X_OFFSET, y, extra_line)
    return y - 18


def render_receipt_pdf(
    donor: Donor, donation: Donation, receipt: Receipt, ngo: NgoSettings
) -> str:
    """Renders the acknowledgement receipt directly via reportlab (no HTML/system deps —
    chosen over weasyprint, per module 05, because it needs no native Cairo/Pango toolchain,
    which made weasyprint unreliable behind a locked-down package mirror)."""
    bank = json.loads(ngo.bank_details_json)
    reason_display = (
        donation.reason_other
        if donation.reason == "other" and donation.reason_other
        else _REASON_LABELS.get(donation.reason, donation.reason)
    )
    mode_display = _MODE_LABELS.get(donation.mode, donation.mode)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 2 * cm
    right = width - 2 * cm
    y = height - 2 * cm

    text_left = left
    logo_path = BACKEND_ROOT / ngo.logo_path if ngo.logo_path else None
    if not logo_path or not logo_path.is_file():
        configured_logo_path = BACKEND_ROOT / settings.ngo_logo_path
        logo_path = configured_logo_path if configured_logo_path.is_file() else None
    if logo_path and logo_path.exists():
        try:
            logo_size = LOGO_BOX_CM * cm
            c.drawImage(
                ImageReader(str(logo_path)),
                left,
                y - logo_size + 0.3 * cm,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )
            text_left = left + logo_size + 0.4 * cm
        except Exception:
            logger.exception("Failed to draw NGO logo on receipt %s — continuing without it", receipt.receipt_no)

    c.setFont("Helvetica-Bold", 15)
    c.drawString(text_left, y, ngo.name)
    c.setFont("Helvetica", 9.5)
    c.drawRightString(right, y, f"Receipt No: {receipt.receipt_no}")
    y -= 14
    date_str = receipt.issued_at.strftime("%d-%b-%Y") if receipt.issued_at else ""
    c.drawRightString(right, y, f"Date: {date_str}")

    c.setFont("Helvetica", 10)
    for line in _wrap(ngo.address, 70):
        y -= 13
        c.drawString(text_left, y, line)
    y -= 13
    c.drawString(
        text_left,
        y,
        f"UPI: {ngo.upi_id} | Bank: {bank.get('account_name', '')}, A/C {bank.get('account_no', '')}, "
        f"IFSC {bank.get('ifsc', '')}, {bank.get('bank', '')}",
    )

    y -= 36
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(width / 2, y, "DONATION ACKNOWLEDGEMENT RECEIPT")

    y -= 28
    fields = [
        ("Received with thanks from", _receipt_donor_name(donor.name)),
        ("Phone", _phone_display(donor.phone)),
        ("Address", donor.address or "\u2014"),
        (
            "Amount",
            f"{format_inr_ascii(donation.amount_paise)} ({amount_paise_to_words(donation.amount_paise)})",
        ),
        ("Purpose / Reason", reason_display),
        ("Payment Mode", mode_display),
    ]
    # Mode-specific extra fields (module 04/08 — collected on the donate form).
    if donation.mode == "upi":
        fields.append(("UPI Transaction ID", donation.upi_txn_id or "\u2014"))
    elif donation.mode in ("bank_transfer", "cheque_dd"):
        date_label = "Date of Transfer" if donation.mode == "bank_transfer" else "Date of Cheque / DD"
        fields.append(("Bank Name", donation.bank_name or "\u2014"))
        fields.append(("Branch Name", donation.branch_name or "\u2014"))
        fields.append(
            (date_label, donation.transaction_date.strftime("%d-%b-%Y") if donation.transaction_date else "\u2014")
        )

    for label, value in fields:
        y = _draw_field(c, left, y, label, value)

    y -= 6
    c.line(left, y, right, y)
    y -= 14
    c.setFont("Helvetica-Oblique", 8.5)
    for line in _wrap(DISCLAIMER, 95):
        c.drawCentredString(width / 2, y, line)
        y -= 11
    y -= 3
    c.line(left, y, right, y)

    if ngo.reg_80g_number:
        y -= 16
        c.setFont("Helvetica", 9.5)
        c.drawString(
            left,
            y,
            f"80G Registration No: {ngo.reg_80g_number} \u2014 this receipt is valid for tax "
            "exemption under Section 80G.",
        )

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()

    filename_hint = f"{receipt.receipt_no.replace('/', '_')}.pdf"
    subdir = receipt.period
    return receipt_storage.save(subdir, filename_hint, pdf_bytes)