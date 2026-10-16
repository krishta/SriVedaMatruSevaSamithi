#!/usr/bin/env python3
"""Recreate admin user with the password currently configured in .env / settings."""
from app.core.config import settings
from app.db.base import SessionLocal
from app.db.models import AdminUser
from app.core.security import hash_password
from sqlalchemy import select

db = SessionLocal()
try:
    existing = db.execute(
        select(AdminUser).where(AdminUser.username == settings.seed_admin_username)
    ).scalar_one_or_none()
    if existing:
        existing.password_hash = hash_password(settings.seed_admin_password)
        db.commit()
        print(f"✓ Reset password for '{settings.seed_admin_username}' to match .env")
    else:
        db.add(
            AdminUser(
                username=settings.seed_admin_username,
                password_hash=hash_password(settings.seed_admin_password),
            )
        )
        db.commit()
        print(f"✓ Created admin user '{settings.seed_admin_username}'")
finally:
    db.close()