from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models import AdminUser, DonationReason
from app.schemas import DonationReasonCreate, DonationReasonItem, DonationReasonUpdate
from app.services.donation_reasons import (
    archive_donation_reason,
    activate_donation_reason,
    create_donation_reason,
    update_donation_reason,
)

router = APIRouter(prefix="/api/donation-reasons", tags=["donation reasons"])


@router.get("", response_model=list[DonationReasonItem])
def list_active_reasons(db: Session = Depends(get_db)):
    return db.scalars(
        select(DonationReason)
        .where(DonationReason.is_active.is_(True))
        .order_by(DonationReason.label)
    ).all()


@router.get("/admin", response_model=list[DonationReasonItem])
def list_all_reasons(
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    return db.scalars(select(DonationReason).order_by(DonationReason.label)).all()


@router.post("", response_model=DonationReasonItem, status_code=status.HTTP_201_CREATED)
def create_reason(
    body: DonationReasonCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return create_donation_reason(db, body.label, admin.id)


@router.put("/{code}", response_model=DonationReasonItem)
def update_reason(
    code: str,
    body: DonationReasonUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return update_donation_reason(db, code, body.label, admin.id)


@router.delete("/{code}", status_code=status.HTTP_204_NO_CONTENT)
def archive_reason(
    code: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    archive_donation_reason(db, code, admin.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{code}/activate", response_model=DonationReasonItem)
def activate_reason(
    code: str,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    return activate_donation_reason(db, code, admin.id)
