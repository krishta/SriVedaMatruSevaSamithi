import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models import AdminUser, NgoSettings
from app.schemas import NgoSettingsAdmin, NgoSettingsPublic, NgoSettingsUpdate

router = APIRouter(prefix="/api/ngo-settings", tags=["ngo-settings"])

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


@router.get("/public", response_model=NgoSettingsPublic)
def get_public_settings(db: Session = Depends(get_db)):
    ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one()
    return NgoSettingsPublic(
        name=ngo.name,
        address=ngo.address,
        upi_id=ngo.upi_id,
        bank_details=json.loads(ngo.bank_details_json),
        logo_url="/api/ngo-settings/logo" if ngo.logo_path else None,
    )


@router.get("/logo")
def get_logo(db: Session = Depends(get_db)):
    ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one()
    if not ngo.logo_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No logo configured")
    logo_path = BACKEND_ROOT / ngo.logo_path
    if not logo_path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Logo file missing on disk")
    return FileResponse(logo_path)


@router.get("", response_model=NgoSettingsAdmin)
def get_admin_settings(
    db: Session = Depends(get_db), _admin: AdminUser = Depends(get_current_admin)
):
    ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one()
    return NgoSettingsAdmin(
        name=ngo.name,
        address=ngo.address,
        upi_id=ngo.upi_id,
        bank_details=json.loads(ngo.bank_details_json),
        logo_url="/api/ngo-settings/logo" if ngo.logo_path else None,
        reg_80g_number=ngo.reg_80g_number,
    )


@router.put("", response_model=NgoSettingsAdmin)
def update_settings(
    body: NgoSettingsUpdate,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    ngo = db.execute(select(NgoSettings).where(NgoSettings.id == 1)).scalar_one()
    ngo.name = body.name
    ngo.address = body.address
    ngo.upi_id = body.upi_id
    ngo.bank_details_json = json.dumps(body.bank_details)
    # 80G number stays null/hidden until the NGO confirms registration (01-domain-context.md).
    ngo.reg_80g_number = body.reg_80g_number
    db.commit()
    return NgoSettingsAdmin(
        name=ngo.name,
        address=ngo.address,
        upi_id=ngo.upi_id,
        bank_details=json.loads(ngo.bank_details_json),
        logo_url="/api/ngo-settings/logo" if ngo.logo_path else None,
        reg_80g_number=ngo.reg_80g_number,
    )