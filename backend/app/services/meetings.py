import json
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, MeetingMinutes
from app.services.docx_export import html_to_plain_text


def _audit(db: Session, admin_id: int, action: str, meeting: MeetingMinutes, detail: dict) -> None:
    db.add(
        AuditLog(
            actor_admin_id=admin_id,
            action=action,
            entity_type="meeting_minutes",
            entity_id=meeting.id,
            detail_json=json.dumps(detail, default=str),
        )
    )


def _query(
    *,
    search: str | None,
    date_from: date | None,
    date_to: date | None,
):
    q = select(MeetingMinutes).where(MeetingMinutes.is_active.is_(True))
    if search:
        q = q.where(MeetingMinutes.notes_html.ilike(f"%{search}%"))
    if date_from:
        q = q.where(MeetingMinutes.meeting_date >= date_from)
    if date_to:
        q = q.where(MeetingMinutes.meeting_date <= date_to)
    return q


def list_meetings(
    db: Session,
    *,
    search: str | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    size: int,
) -> tuple[list[MeetingMinutes], int]:
    q = _query(search=search, date_from=date_from, date_to=date_to)
    total = db.execute(select(func.count()).select_from(q.subquery())).scalar_one()
    rows = (
        db.execute(
            q.order_by(MeetingMinutes.meeting_date.desc(), MeetingMinutes.id.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        .scalars()
        .all()
    )
    return list(rows), total


def list_all_for_export(
    db: Session,
    *,
    search: str | None,
    date_from: date | None,
    date_to: date | None,
) -> list[MeetingMinutes]:
    q = _query(search=search, date_from=date_from, date_to=date_to)
    rows = (
        db.execute(q.order_by(MeetingMinutes.meeting_date.asc(), MeetingMinutes.id.asc()).limit(1000))
        .scalars()
        .all()
    )
    return list(rows)


def get_meeting(db: Session, meeting_id: int) -> MeetingMinutes:
    meeting = db.get(MeetingMinutes, meeting_id)
    if not meeting or not meeting.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")
    return meeting


def create_meeting(
    db: Session, *, admin_id: int, meeting_date: date, notes_html: str
) -> MeetingMinutes:
    meeting = MeetingMinutes(meeting_date=meeting_date, notes_html=notes_html, is_active=True)
    db.add(meeting)
    db.flush()
    _audit(db, admin_id, "meeting.create", meeting, {"meeting_date": meeting_date})
    db.commit()
    db.refresh(meeting)
    return meeting


def update_meeting(
    db: Session, *, admin_id: int, meeting_id: int, meeting_date: date, notes_html: str
) -> MeetingMinutes:
    meeting = get_meeting(db, meeting_id)
    before = {"meeting_date": meeting.meeting_date}
    meeting.meeting_date = meeting_date
    meeting.notes_html = notes_html
    _audit(
        db,
        admin_id,
        "meeting.update",
        meeting,
        {"before": before, "after": {"meeting_date": meeting_date}},
    )
    db.commit()
    db.refresh(meeting)
    return meeting


def delete_meeting(db: Session, *, admin_id: int, meeting_id: int) -> None:
    meeting = get_meeting(db, meeting_id)
    meeting.is_active = False
    _audit(db, admin_id, "meeting.delete", meeting, {"meeting_date": meeting.meeting_date})
    db.commit()


def to_preview(meeting: MeetingMinutes, *, max_length: int = 140) -> str:
    return html_to_plain_text(meeting.notes_html, max_length=max_length)