from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.db.models import AdminUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

ALGORITHM = "HS256"

# bcrypt has a hard 72-byte input limit (enforced strictly since bcrypt>=4.1) — truncate rather
# than error, matching the widely-used convention for this limit.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    truncated = plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(truncated, hashed.encode("utf-8"))


def _create_token(subject: str, ttl: timedelta, token_type: str) -> str:
    expire = datetime.now(timezone.utc) + ttl
    payload = {"sub": subject, "type": token_type, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def create_access_token(username: str) -> str:
    return _create_token(username, timedelta(minutes=settings.jwt_access_ttl_min), "access")


def create_refresh_token(username: str) -> str:
    return _create_token(username, timedelta(days=settings.jwt_refresh_ttl_days), "refresh")


def decode_token(token: str, expected_type: str) -> str:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    if payload.get("type") != expected_type:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")
    username = payload.get("sub")
    if not username:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token")
    return username


def get_current_admin(
    token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> AdminUser:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    username = decode_token(token, "access")
    admin = db.query(AdminUser).filter(AdminUser.username == username).first()
    if not admin:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admin not found")
    return admin