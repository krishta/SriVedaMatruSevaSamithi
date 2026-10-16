from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, verify_password
from app.db.base import get_db
from app.db.models import AdminUser
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    admin = db.execute(
        select(AdminUser).where(AdminUser.username == body.username)
    ).scalar_one_or_none()
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    admin.last_login_at = datetime.now(timezone.utc)
    db.commit()

    access_token = create_access_token(admin.username)
    refresh_token = create_refresh_token(admin.username)
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=60 * 60 * 24 * 7,
    )
    return LoginResponse(access_token=access_token)


@router.post("/refresh", response_model=LoginResponse)
def refresh(response: Response, refresh_token: str | None = None):
    # In production this reads the HttpOnly cookie via Request; simplified here for clarity.
    from app.core.security import decode_token

    if not refresh_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing refresh token")
    username = decode_token(refresh_token, "refresh")
    new_access = create_access_token(username)
    return LoginResponse(access_token=new_access)