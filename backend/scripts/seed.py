"""Seeds NgoSettings (placeholder values), the first AdminUser, and the current period counter.

Run with: python -m scripts.seed   (from the backend/ directory, venv active)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base, SessionLocal, engine
from app.db.models import AdminUser, NgoSettings, PeriodCounter
from app.services.period import current_period


def run() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        logo_abs_path = Path(__file__).resolve().parent.parent / settings.ngo_logo_path
        bundled_logo = settings.ngo_logo_path if logo_abs_path.exists() else None

        existing_ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one_or_none()
        if not existing_ngo:
            db.add(
                NgoSettings(
                    id=1,
                    name=settings.ngo_name,
                    address=settings.ngo_address,
                    upi_id=settings.ngo_upi_id,
                    bank_details_json=json.dumps(
                        {
                            "account_name": settings.ngo_bank_account_name,
                            "account_no": settings.ngo_bank_account_no,
                            "ifsc": settings.ngo_bank_ifsc,
                            "bank": settings.ngo_bank_name,
                        }
                    ),
                    logo_path=bundled_logo,
                    reg_80g_number=None,
                )
            )
            print("Seeded NgoSettings — TBD placeholder values, update via /admin/settings before go-live.")
        elif bundled_logo and existing_ngo.logo_path != bundled_logo:
            # Keeps the bundled logo file as the source of truth; harmless while there's no
            # logo-upload feature in /admin/settings yet.
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