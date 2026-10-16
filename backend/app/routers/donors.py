from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models import AdminUser, Donor
from app.schemas import (
    DonorCreate,
    DonorDetailResponse,
    DonorDonationItem,
    DonorListItem,
    DonorListResponse,
    DonorUpdate,
)
from app.services import donors as donor_service
from app.services.donations import normalize_phone

router = APIRouter(prefix="/api/donors", tags=["donors"])


def _to_list_item(donor: Donor) -> DonorListItem:
    return DonorListItem(
        id=donor.id,
        name=donor.name,
        phone=donor.phone,
        email=donor.email,
        address=donor.address,
        created_at=donor.created_at,
    )


@router.get("", response_model=DonorListResponse)
def list_donors(
    search: str | None = None,
    page: int = 1,
    size: int = 50,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    rows, total = donor_service.list_donors(db, search=search, page=page, size=size)
    return DonorListResponse(
        items=[_to_list_item(d) for d in rows], total=total, page=page, size=size
    )


@router.post("", response_model=DonorListItem, status_code=status.HTTP_201_CREATED)
def create_donor(
    body: DonorCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    donor = donor_service.create_donor(
        db,
        admin_id=admin.id,
        name=body.name,
        phone=normalize_phone(body.phone),
        email=body.email,
        address=body.address,
    )
    return _to_list_item(donor)


@router.put("/{donor_id}", response_model=DonorListItem)
def update_donor(
    donor_id: int,
    body: DonorUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    donor = donor_service.update_donor(
        db,
        admin_id=admin.id,
        donor_id=donor_id,
        name=body.name,
        phone=normalize_phone(body.phone),
        email=body.email,
        address=body.address,
    )
    return _to_list_item(donor)


@router.delete("/{donor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_donor(
    donor_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    donor_service.delete_donor(db, admin_id=admin.id, donor_id=donor_id)


@router.get("/{donor_id}", response_model=DonorDetailResponse)
def get_donor(
    donor_id: int, db: Session = Depends(get_db), _admin: AdminUser = Depends(get_current_admin)
):
    donor = db.get(Donor, donor_id)
    if not donor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Donor not found")

    lifetime_total = sum(d.amount_paise for d in donor.donations if d.status == "issued")
    donations = [
        DonorDonationItem(
            id=d.id,
            amount_paise=d.amount_paise,
            reason=d.reason_other if d.reason == "other" else d.reason,
            status=d.status,
            receipt_no=d.receipt.receipt_no if d.receipt else None,
            created_at=d.created_at,
        )
        for d in sorted(donor.donations, key=lambda x: x.created_at, reverse=True)
    ]
    return DonorDetailResponse(
        id=donor.id,
        name=donor.name,
        phone=donor.phone,
        email=donor.email,
        address=donor.address,
        lifetime_total_paise=lifetime_total,
        donations=donations,
    )