import logging
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.db.models import Donor, Receipt

logger = logging.getLogger(__name__)


class NotificationChannel(Protocol):
    def send_receipt(self, donor: Donor, receipt: Receipt, pdf_path: Path) -> bool: ...


class EmailChannel:
    """Best-effort SMTP delivery — failure is logged, never raised to the caller (PRD DN-06)."""

    def send_receipt(self, donor: Donor, receipt: Receipt, pdf_path: Path) -> bool:
        """Returns True only if the message was actually accepted by the SMTP server."""
        if not donor.email:
            return False
        try:
            import smtplib
            from email.mime.application import MIMEApplication
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart()
            msg["Subject"] = f"Your donation receipt {receipt.receipt_no}"
            msg["From"] = settings.smtp_from
            msg["To"] = donor.email
            msg.attach(
                MIMEText(
                    f"Dear {donor.name},\n\nThank you for your donation. "
                    f"Please find your acknowledgement receipt ({receipt.receipt_no}) attached.\n\n"
                    "— Sri Veda Matru Seva Samiti"
                )
            )
            with open(pdf_path, "rb") as fh:
                part = MIMEApplication(fh.read(), _subtype="pdf")
                part.add_header(
                    "Content-Disposition", "attachment", filename=f"{receipt.receipt_no}.pdf"
                )
                msg.attach(part)

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
            return True
        except Exception:
            logger.exception("Best-effort receipt email failed for donation receipt %s", receipt.receipt_no)
            return False


# Only EmailChannel is implemented today. Adding SMS/WhatsApp Business API later is a new
# NotificationChannel implementation, not a rewrite (module 06).
notification_channels: list[NotificationChannel] = [EmailChannel()]


def send_receipt_notifications(donor: Donor, receipt: Receipt, pdf_path: Path) -> bool:
    delivered = False
    for channel in notification_channels:
        if channel.send_receipt(donor, receipt, pdf_path):
            delivered = True
    return delivered