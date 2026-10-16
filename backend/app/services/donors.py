import json
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, Donation, Donor


def _audit(db: Session, admin_id: int, action: str, donor: Donor, detail: dict) -> None:
    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action=action,
            entity_type="donor",
            entity_id=donor.id,
            detail_json=json.dumps(detail),
        )
    )


def list_donors(
    db: Session, *, search: str | None, page: int, size: int
) -> tuple[list[Donor], int]:
    last_deletion_at = (
        select(func.max(AuditLog.created_at))
        .where(
            AuditLog.entity_type == "donor",
            AuditLog.entity_id == Donor.id,
            AuditLog.action == "donor.delete",
        )
        .correlate(Donor)
        .scalar_subquery()
    )
    has_issued_donation_since_deletion = (
        select(Donation.id)
        .where(
            Donation.donor_id == Donor.id,
            Donation.status == "issued",
            Donation.created_at > func.coalesce(last_deletion_at, datetime.min),
        )
        .exists()
    )
    q = select(Donor).where(
        or_(Donor.is_active.is_(True), has_issued_donation_since_deletion)
    )
    if search:
        like = f"%{search}%"
        q = q.where(or_(Donor.name.ilike(like), Donor.phone.ilike(like)))
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    rows = db.execute(
        q.order_by(Donor.name).offset((page - 1) * size).limit(size)
    ).scalars().all()
    return list(rows), total


def create_donor(
    db: Session,
    *,
    admin_id: int,
    name: str,
    phone: str,
    email: str | None,
    address: str | None,
) -> Donor:
    existing = db.execute(select(Donor).where(Donor.phone == phone)).scalar_one_or_none()
    if existing:
        if existing.is_active:
            raise HTTPException(status.HTTP_409_CONFLICT, "A donor with this phone number already exists")
        # Reactivate a previously removed donor rather than violating the unique phone index.
        existing.is_active = True
        existing.name = name
        existing.email = email
        existing.address = address
        _audit(db, admin_id, "donor.reactivate", existing, {"phone": phone, "name": name})
        db.commit()
        db.refresh(existing)
        return existing

    donor = Donor(name=name, phone=phone, email=email, address=address, is_active=True)
    db.add(donor)
    db.flush()
    _audit(db, admin_id, "donor.create", donor, {"phone": phone, "name": name})
    db.commit()
    db.refresh(donor)
    return donor


def update_donor(
    db: Session,
    *,
    admin_id: int,
    donor_id: int,
    name: str,
    phone: str,
    email: str | None,
    address: str | None,
) -> Donor:
    donor = db.get(Donor, donor_id)
    if not donor or not donor.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found")

    clash = db.execute(
        select(Donor).where(Donor.phone == phone, Donor.id != donor_id)
    ).scalar_one_or_none()
    if clash:
        raise HTTPException(status.HTTP_409_CONFLICT, "Another donor already uses this phone number")

    before = {"name": donor.name, "phone": donor.phone, "email": donor.email, "address": donor.address}
    donor.name = name
    donor.phone = phone
    donor.email = email
    donor.address = address
    _audit(
        db,
        admin_id,
        "donor.update",
        donor,
        {"before": before, "after": {"name": name, "phone": phone, "email": email, "address": address}},
    )
    db.commit()
    db.refresh(donor)
    return donor


def delete_donor(db: Session, *, admin_id: int, donor_id: int) -> None:
    """Soft delete — issued receipts must remain intact and attributable (module 07)."""
    donor = db.get(Donor, donor_id)
    if not donor or not donor.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found")
    donor.is_active = False
    _audit(db, admin_id, "donor.delete", donor, {"phone": donor.phone, "name": donor.name})
    db.commit()