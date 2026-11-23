import io
import json
import logging
import re
import unicodedata
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.core.config import settings
from app.db.models import Donation, Donor, NgoSettings, Receipt
from app.services.amount_words import amount_paise_to_words, format_inr_ascii
from app.services.donation_reasons import reason_label_for_donation
from app.services.storage import receipt_storage

logger = logging.getLogger(__name__)

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
LOGO_BOX_CM = 2.2  # square logo box, top-left of the receipt

_MODE_LABELS = {
    "upi": "UPI",
    "bank_transfer": "Bank Transfer",
    "cheque_dd": "Cheque / DD",
}

DISCLAIMER = (
    "This is a computer-generated acknowledgement of donation and no signature is required.",
    "This receipt is not valid for claiming tax exemption under Section 80G.",
)

_BRAND_ORANGE = HexColor("#c46a1b")
_PALE_ORANGE = HexColor("#fff6ec")
_INK = HexColor("#27231f")


def _draw_image(c: canvas.Canvas, path: Path, x: float, y: float, height: float) -> float:
    image = ImageReader(str(path))
    image_width, image_height = image.getSize()
    width = height * image_width / image_height
    c.drawImage(image, x, y, width=width, height=height, mask="auto")
    return width


def _draw_centered_image(
    c: canvas.Canvas, path: Path, center_x: float, y: float, height: float
) -> None:
    image = ImageReader(str(path))
    image_width, image_height = image.getSize()
    width = height * image_width / image_height
    c.drawImage(image, center_x - width / 2, y, width=width, height=height, mask="auto")


def _wrap_to_width(text: str, max_width: float, font: str, font_size: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and stringWidth(candidate, font, font_size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _draw_receipt_table(
    c: canvas.Canvas,
    left: float,
    top: float,
    width: float,
    receipt_no: str,
    issued_date: str,
    rows: list[tuple[str, str]],
) -> float:
    label_x = left + 10
    value_x = left + 155
    value_width = width - (value_x - left) - 12
    font = "Helvetica"
    font_size = 9.5
    line_height = 14
    row_top = top

    c.setStrokeColor(_BRAND_ORANGE)
    c.setLineWidth(0.8)
    c.rect(left, top - 27, width, 27, stroke=1, fill=0)
    c.setFillColor(_PALE_ORANGE)
    c.rect(left, top - 27, width, 27, stroke=0, fill=1)
    c.setStrokeColor(_BRAND_ORANGE)
    c.rect(left, top - 27, width, 27, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 9.5)
    c.setFillColor(_INK)
    c.drawString(label_x, top - 17, "Receipt No.:")
    c.setFont(font, font_size)
    c.drawString(left + 74, top - 17, receipt_no)
    date_label = "Date:"
    date_value = f"{date_label}  {issued_date}"
    c.setFont("Helvetica-Bold", 9.5)
    c.drawRightString(left + width - 10, top - 17, date_value)
    row_top -= 27

    for label, value in rows:
        lines = _wrap_to_width(value, value_width, font, font_size) or ["—"]
        row_height = max(24, len(lines) * line_height + 10)
        row_bottom = row_top - row_height
        c.setFillColor(_INK)

        text_y = row_top - (row_height - len(lines) * line_height) / 2 - 10
        c.setFont("Helvetica-Bold", font_size)
        c.drawString(label_x, text_y, label)
        c.setFont(font, font_size)
        for line in lines:
            c.drawString(value_x, text_y, line)
            text_y -= line_height

        c.setStrokeColor(HexColor("#e4cbb4"))
        c.setLineWidth(0.65)
        c.line(left, row_bottom, left + width, row_bottom)
        row_top = row_bottom

    c.setStrokeColor(_BRAND_ORANGE)
    c.setLineWidth(0.8)
    c.rect(left, row_top, width, top - row_top, stroke=1, fill=0)
    return row_top


def _phone_display(phone_e164: str) -> str:
    digits = phone_e164.replace("+91", "")
    if len(digits) == 10:
        return f"+91 {digits[:5]} {digits[5:]}"
    return phone_e164


def _receipt_donor_name(name: str) -> str:
    parts = name.split()
    if parts and parts[0].casefold() in {"sri", "sri.", "smt", "smt."}:
        parts = parts[1:]
    if parts and parts[-1].casefold() == "garu":
        parts = parts[:-1]
    donor_name = " ".join(parts)
    return f"Sri/Smt. {donor_name} garu" if donor_name else "Sri/Smt. garu"


def receipt_filename(receipt_no: str, donor_name: str) -> str:
    receipt_part = re.sub(r"[^A-Za-z0-9]+", "_", receipt_no).strip("_")
    ascii_name = (
        unicodedata.normalize("NFKD", donor_name).encode("ascii", "ignore").decode("ascii")
    )
    donor_part = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_").lower() or "donor"
    return f"{receipt_part}_{donor_part}.pdf"


def render_receipt_pdf(
    donor: Donor, donation: Donation, receipt: Receipt, ngo: NgoSettings
) -> str:
    """Renders the acknowledgement receipt directly via reportlab (no HTML/system deps —
    chosen over weasyprint, per module 05, because it needs no native Cairo/Pango toolchain,
    which made weasyprint unreliable behind a locked-down package mirror)."""
    bank = json.loads(ngo.bank_details_json)
    reason_display = reason_label_for_donation(donation)
    mode_display = _MODE_LABELS.get(donation.mode, donation.mode)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    left = 2 * cm
    right = width - 2 * cm
    y = height - 2 * cm

    header_title_y = height - 2.65 * cm
    logo_path = BACKEND_ROOT / ngo.logo_path if ngo.logo_path else None
    if not logo_path or not logo_path.is_file():
        configured_logo_path = BACKEND_ROOT / settings.ngo_logo_path
        logo_path = configured_logo_path if configured_logo_path.is_file() else None

    caption_y = height - 1.65 * cm
    caption_height = 18
    caption_assets = {
        "left": BACKEND_ROOT / "app/static/jay-jay-shankara.png",
        "om": BACKEND_ROOT / "app/static/om.png",
        "right": BACKEND_ROOT / "app/static/hara-hara-shankara.png",
    }
    content_center_x = width / 2
    if all(path.is_file() for path in caption_assets.values()):
        left_caption = ImageReader(str(caption_assets["left"]))
        left_caption_width = caption_height * left_caption.getSize()[0] / left_caption.getSize()[1]
        c.drawImage(
            left_caption,
            left,
            caption_y - caption_height / 2,
            width=left_caption_width,
            height=caption_height,
            mask="auto",
        )
        _draw_centered_image(
            c,
            caption_assets["om"],
            content_center_x,
            caption_y - caption_height / 2,
            caption_height,
        )
        right_caption = ImageReader(str(caption_assets["right"]))
        right_caption_width = caption_height * right_caption.getSize()[0] / right_caption.getSize()[1]
        c.drawImage(
            right_caption,
            right - right_caption_width,
            caption_y - caption_height / 2,
            width=right_caption_width,
            height=caption_height,
            mask="auto",
        )

    c.setFillColor(_INK)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(content_center_x, header_title_y, ngo.name)

    address_lines = [
        line
        for address_line in ngo.address.splitlines()
        for line in _wrap_to_width(address_line, width - 2 * left, "Helvetica", 9.5)
    ]
    header_line_y = header_title_y - 15
    c.setFont("Helvetica", 9.5)
    for line in address_lines:
        c.drawCentredString(content_center_x, header_line_y, line)
        header_line_y -= 12

    header_line_y -= 1
    c.drawCentredString(content_center_x, header_line_y, f"Phone: {settings.ngo_phone}")
    header_line_y -= 12
    c.setFont("Helvetica", 8)
    c.drawCentredString(
        content_center_x,
        header_line_y,
        f"Account number: {bank.get('account_no', '')}  |  Bank: {bank.get('bank', '')}",
    )
    header_line_y -= 10
    c.drawCentredString(
        content_center_x,
        header_line_y,
        f"Branch: {bank.get('branch', '')}  |  IFSC: {bank.get('ifsc', '')}",
    )
    header_line_y -= 10
    c.drawCentredString(
        content_center_x,
        header_line_y,
        f"UPI: {ngo.upi_id}",
    )
    logo_center_y = (header_title_y + header_line_y) / 2
    if logo_path and logo_path.exists():
        try:
            logo_size = LOGO_BOX_CM * cm
            c.drawImage(
                ImageReader(str(logo_path)),
                left,
                logo_center_y - logo_size / 2,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            logger.exception(
                "Failed to draw NGO logo on receipt %s — continuing without it",
                receipt.receipt_no,
            )

    c.setStrokeColor(_BRAND_ORANGE)
    c.setLineWidth(0.7)
    c.line(left, header_line_y - 12, right, header_line_y - 12)

    title_y = header_line_y - 34
    c.setFont("Helvetica-Bold", 13)
    c.setFillColor(_BRAND_ORANGE)
    c.drawCentredString(content_center_x, title_y, "DONATION ACKNOWLEDGEMENT RECEIPT")

    receipt_rows = [
        ("Donor Name", _receipt_donor_name(donor.name)),
        ("Address", donor.address or "\u2014"),
        ("Mobile Number", _phone_display(donor.phone)),
        ("Email", donor.email or "\u2014"),
        ("Towards", reason_display),
        ("Amount in Words", amount_paise_to_words(donation.amount_paise)),
        ("Amount (Rupees)", format_inr_ascii(donation.amount_paise)),
    ]
    payment_details = [mode_display]
    if donation.mode == "upi":
        transaction_id = donation.upi_txn_id or "\u2014"
        payment_details.append(f"Transaction ID: {transaction_id}")
    elif donation.mode in ("bank_transfer", "cheque_dd"):
        if donation.bank_name:
            payment_details.append(f"Bank: {donation.bank_name}")
        if donation.branch_name:
            payment_details.append(f"Branch: {donation.branch_name}")
        if donation.transaction_date:
            payment_details.append(f"Date: {donation.transaction_date:%d-%b-%Y}")
    receipt_rows.append(("Mode of Payment", "  |  ".join(payment_details)))

    table_bottom = _draw_receipt_table(
        c,
        left,
        title_y - 15,
        right - left,
        receipt.receipt_no,
        receipt.issued_at.strftime("%d-%b-%Y") if receipt.issued_at else "",
        receipt_rows,
    )

    y = table_bottom - 23
    c.setStrokeColor(_BRAND_ORANGE)
    c.setLineWidth(0.7)
    c.line(left, y, right, y)
    y -= 18
    c.setFillColor(_INK)
    c.setFont("Helvetica-Oblique", 8.5)
    for statement in DISCLAIMER:
        c.drawCentredString(width / 2, y, statement)
        y -= 11
    y -= 3
    c.setStrokeColor(_BRAND_ORANGE)
    c.line(left, y, right, y)

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()

    filename_hint = receipt_filename(receipt.receipt_no, donor.name)
    subdir = receipt.period
    return receipt_storage.save(subdir, filename_hint, pdf_bytes)