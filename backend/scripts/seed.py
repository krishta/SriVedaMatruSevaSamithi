"""Seeds NgoSettings (placeholder values), the first AdminUser, and the current period counter.

Run with: python -m scripts.seed   (from the backend/ directory, venv active)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import (
    DEFAULT_NGO_ADDRESS,
    DEFAULT_NGO_BANK_ACCOUNT_NO,
    DEFAULT_NGO_BANK_BRANCH,
    DEFAULT_NGO_BANK_IFSC,
    DEFAULT_NGO_BANK_NAME,
    DEFAULT_NGO_UPI_ID,
    settings,
)
from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine
from app.db.models import AdminUser, NgoSettings, PeriodCounter
from app.services.period import current_period


def _configured_or_default(value: str, placeholder: str, default: str) -> str:
    return default if value.strip() in {"", "TBD", placeholder} else value


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        logo_abs_path = Path(__file__).resolve().parent.parent / settings.ngo_logo_path
        bundled_logo = settings.ngo_logo_path if logo_abs_path.exists() else None
        ngo_address = _configured_or_default(
            settings.ngo_address, "TBD_registered_address", DEFAULT_NGO_ADDRESS
        )
        ngo_upi_id = _configured_or_default(settings.ngo_upi_id, "TBD@upi", DEFAULT_NGO_UPI_ID)
        bank_defaults = {
            "account_name": _configured_or_default(settings.ngo_bank_account_name, "TBD", ""),
            "account_no": _configured_or_default(
                settings.ngo_bank_account_no, "TBD", DEFAULT_NGO_BANK_ACCOUNT_NO
            ),
            "ifsc": _configured_or_default(settings.ngo_bank_ifsc, "TBD", DEFAULT_NGO_BANK_IFSC),
            "bank": _configured_or_default(settings.ngo_bank_name, "TBD", DEFAULT_NGO_BANK_NAME),
            "branch": _configured_or_default(
                settings.ngo_bank_branch, "TBD", DEFAULT_NGO_BANK_BRANCH
            ),
        }

        existing_ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one_or_none()
        if not existing_ngo:
            db.add(
                NgoSettings(
                    id=1,
                    name=settings.ngo_name,
                    address=ngo_address,
                    upi_id=ngo_upi_id,
                    bank_details_json=json.dumps(bank_defaults),
                    logo_path=bundled_logo,
                    reg_80g_number=None,
                )
            )
            print("Seeded NgoSettings with the configured organization and bank details.")
        else:
            if existing_ngo.address in ("TBD_registered_address", "TBD"):
                existing_ngo.address = ngo_address
            if existing_ngo.upi_id in ("TBD@upi", "TBD"):
                existing_ngo.upi_id = ngo_upi_id

            bank_details = json.loads(existing_ngo.bank_details_json)
            for key, value in bank_defaults.items():
                if bank_details.get(key) in (None, "", "TBD"):
                    bank_details[key] = value
            existing_ngo.bank_details_json = json.dumps(bank_details)

            if bundled_logo and existing_ngo.logo_path != bundled_logo:
                # The bundled logo remains the source of truth until logo uploads are supported.
                existing_ngo.logo_path = bundled_logo
                print(f"Synced logo_path onto existing NgoSettings row -> {bundled_logo}")

        if not db.execute(
            select(AdminUser).where(AdminUser.username == settings.seed_admin_username)
        ).scalar_one_or_none():
            db.add(
                AdminUser(
                    username=settings.seed_admin_username,
                    password_hash=hash_password(settings.seed_admin_password),
                )
            )
            print(
                f"Seeded AdminUser '{settings.seed_admin_username}' — "
                "rotate the placeholder password immediately after first login."
            )

        period = current_period()
        if not db.execute(
            select(PeriodCounter).where(PeriodCounter.period == period)
        ).scalar_one_or_none():
            db.add(PeriodCounter(period=period, next_seq=1))
            print(f"Seeded PeriodCounter for {period}.")

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()