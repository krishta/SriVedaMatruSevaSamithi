from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Donor(Base):
    __tablename__ = "donors"
    id: Mapped[int] = mapped_column(primary_key=True)
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Soft delete: removing a donor from the master list must never orphan their issued
    # receipts (module 07 — receipts are immutable historical records).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    donations: Mapped[list["Donation"]] = relationship(back_populates="donor")


class Donation(Base):
    __tablename__ = "donations"
    id: Mapped[int] = mapped_column(primary_key=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.id"), index=True)
    amount_paise: Mapped[int]
    reason: Mapped[str] = mapped_column(String(30))
    reason_other: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mode: Mapped[str] = mapped_column(String(20))
    # Populated conditionally depending on `mode` (module 04) — all nullable, only one
    # group is expected to be filled per donation.
    upi_txn_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bank_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Optional for admin batch-generated receipts; still required on the public donor form.
    screenshot_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="issued")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    donor: Mapped["Donor"] = relationship(back_populates="donations")
    receipt: Mapped["Receipt"] = relationship(back_populates="donation", uselist=False)


class Receipt(Base):
    __tablename__ = "receipts"
    id: Mapped[int] = mapped_column(primary_key=True)
    # Not unique — a voided receipt can have a reissued successor for the same donation
    # (module 02 invariant 3). At most one non-voided receipt per donation is enforced at
    # the service layer (void_receipt / reissue_receipt), not by a DB unique constraint.
    donation_id: Mapped[int] = mapped_column(ForeignKey("donations.id"), index=True)
    receipt_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    period: Mapped[str] = mapped_column(String(7))  # "YYYY-MM", e.g. "2026-09"
    sequence_no: Mapped[int]
    pdf_path: Mapped[str] = mapped_column(String(500))
    issued_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    voided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)
    reissue_of_receipt_id: Mapped[int | None] = mapped_column(
        ForeignKey("receipts.id"), nullable=True
    )

    donation: Mapped["Donation"] = relationship(back_populates="receipt")


class PeriodCounter(Base):
    """Row-locked per-calendar-month sequence allocator (PRD SY-01) — key is "YYYY-MM"."""

    __tablename__ = "period_counters"
    period: Mapped[str] = mapped_column(String(7), primary_key=True)
    next_seq: Mapped[int] = mapped_column(default=1)


class AdminUser(Base):
    __tablename__ = "admin_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_admin_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int]
    detail_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NgoSettings(Base):
    __tablename__ = "ngo_settings"
    __table_args__ = (UniqueConstraint("id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="Sri Veda Matru Seva Samiti")
    address: Mapped[str] = mapped_column(Text)
    upi_id: Mapped[str] = mapped_column(String(100))
    bank_details_json: Mapped[str] = mapped_column(Text)
    logo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    reg_80g_number: Mapped[str | None] = mapped_column(String(60), nullable=True)


class MeetingMinutes(Base):
    """Admin-logged monthly meeting notes (rich-text HTML from the admin's editor)."""

    __tablename__ = "meeting_minutes"
    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_date: Mapped[date] = mapped_column(Date, index=True)
    notes_html: Mapped[str] = mapped_column(Text)
    # Soft delete, consistent with the donor master list (module 07 audit trail).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )