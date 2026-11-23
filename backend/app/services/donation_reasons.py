import json
import re
import unicodedata
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import Engine, insert, inspect, select, text
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Donation, DonationReason, DonationReasonSnapshot

DEFAULT_DONATION_REASONS = (
    ("monthly_donation", "Monthly Donation", True),
    ("birthday", "Birthday", False),
    ("occasion_veda_sabha", "Occasion / Veda Sabha", False),
    ("telangana_veda_sabhalu_2026", "2026 Telangana Veda Sabhalu", False),
    ("general_donation", "General Donation", False),
    ("other", "Other", True),
)
DEFAULT_REASON_LABELS = {code: label for code, label, _ in DEFAULT_DONATION_REASONS}


def upgrade_donation_reason_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table(DonationReason.__tablename__):
        return
    columns = {column["name"] for column in inspector.get_columns(DonationReason.__tablename__)}
    if "id" in columns:
        return

    with engine.begin() as connection:
        legacy_rows = connection.execute(
            text("SELECT * FROM donation_reasons ORDER BY code")
        ).mappings().all()
        connection.exec_driver_sql(
            "ALTER TABLE donation_reasons RENAME TO donation_reasons_legacy"
        )
        connection.exec_driver_sql("DROP TABLE donation_reasons_legacy")
        DonationReason.__table__.create(connection)

        migrated_rows = []
        for reason_id, row in enumerate(legacy_rows, start=1):
            code = row["code"]
            values = {
                "id": reason_id,
                "code": code,
                "label": row["label"],
                "is_active": row.get("is_active", True),
                "is_system": row.get("is_system", code in {"monthly_donation", "other"}),
            }
            for timestamp in ("created_at", "updated_at"):
                value = row.get(timestamp)
                if isinstance(value, str):
                    value = datetime.fromisoformat(value)
                if value is not None:
                    values[timestamp] = value
            migrated_rows.append(values)
        if migrated_rows:
            connection.execute(insert(DonationReason), migrated_rows)


def reason_label_for_donation(donation: Donation) -> str:
    if donation.reason == "other" and donation.reason_other:
        return donation.reason_other
    if donation.reason_label_snapshot:
        return donation.reason_label_snapshot.label
    return DEFAULT_REASON_LABELS.get(donation.reason, donation.reason)


def ensure_donation_reasons(db: Session) -> None:
    for code, label, is_system in DEFAULT_DONATION_REASONS:
        if db.scalar(select(DonationReason).where(DonationReason.code == code)) is None:
            db.add(
                DonationReason(
                    code=code,
                    label=label,
                    is_active=True,
                    is_system=is_system,
                )
            )
    db.flush()

    for donation in db.scalars(
        select(Donation).where(~Donation.reason_label_snapshot.has())
    ):
        reason = db.scalar(
            select(DonationReason).where(DonationReason.code == donation.reason)
        )
        label = reason.label if reason else donation.reason
        donation.reason_label_snapshot = DonationReasonSnapshot(
            label=label[:120],
        )
    db.flush()


def get_active_reason(db: Session, code: str) -> DonationReason:
    reason = db.scalar(select(DonationReason).where(DonationReason.code == code))
    if reason is None or not reason.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid or inactive donation reason")
    return reason


def _validate_label(db: Session, label: str, exclude_code: str | None = None) -> str:
    normalized = label.strip()
    if not normalized:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Reason label cannot be empty")
    for reason in db.scalars(
        select(DonationReason).where(
            DonationReason.is_active.is_(True),
            DonationReason.code != (exclude_code or ""),
        )
    ):
        if reason.label.casefold() == normalized.casefold():
            raise HTTPException(status.HTTP_409_CONFLICT, "An active reason with this label already exists")
    return normalized


def create_donation_reason(db: Session, label: str, admin_id: int) -> DonationReason:
    normalized = _validate_label(db, label)
    slug = unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", slug.lower()).strip("_") or "reason"
    base = f"custom_{slug}"[:30].rstrip("_")
    code = base
    suffix = 2
    while db.scalar(select(DonationReason.id).where(DonationReason.code == code)) is not None:
        ending = f"_{suffix}"
        code = f"{base[:30 - len(ending)]}{ending}"
        suffix += 1

    reason = DonationReason(code=code, label=normalized, is_active=True, is_system=False)
    db.add(reason)
    db.flush()
    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="donation_reason.create",
            entity_type="donation_reason",
            entity_id=reason.id,
            detail_json=json.dumps({"code": code, "label": normalized}),
        )
    )
    db.commit()
    db.refresh(reason)
    return reason


def update_donation_reason(db: Session, code: str, label: str, admin_id: int) -> DonationReason:
    reason = db.scalar(select(DonationReason).where(DonationReason.code == code))
    if reason is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donation reason not found")
    if not reason.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Archived reasons cannot be edited")
    if reason.is_system:
        raise HTTPException(status.HTTP_409_CONFLICT, "System donation reasons cannot be edited")

    normalized = _validate_label(db, label, exclude_code=code)
    old_label = reason.label
    reason.label = normalized
    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="donation_reason.update",
            entity_type="donation_reason",
            entity_id=reason.id,
            detail_json=json.dumps(
                {"code": code, "old_label": old_label, "new_label": normalized}
            ),
        )
    )
    db.commit()
    db.refresh(reason)
    return reason


def archive_donation_reason(db: Session, code: str, admin_id: int) -> None:
    reason = db.scalar(select(DonationReason).where(DonationReason.code == code))
    if reason is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donation reason not found")
    if reason.is_system:
        raise HTTPException(status.HTTP_409_CONFLICT, "System donation reasons cannot be archived")
    if not reason.is_active:
        return
    reason.is_active = False
    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="donation_reason.archive",
            entity_type="donation_reason",
            entity_id=reason.id,
            detail_json=json.dumps({"code": code, "label": reason.label}),
        )
    )
    db.commit()


def activate_donation_reason(db: Session, code: str, admin_id: int) -> DonationReason:
    reason = db.scalar(select(DonationReason).where(DonationReason.code == code))
    if reason is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donation reason not found")
    if reason.is_active:
        return reason
    _validate_label(db, reason.label)
    reason.is_active = True
    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action="donation_reason.activate",
            entity_type="donation_reason",
            entity_id=reason.id,
            detail_json=json.dumps({"code": code, "label": reason.label}),
        )
    )
    db.commit()
    db.refresh(reason)
    return reason
