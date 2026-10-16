from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.security import get_current_admin
from app.db.base import get_db
from app.db.models import AdminUser, MeetingMinutes
from app.schemas import (
    MeetingCreate,
    MeetingDetail,
    MeetingListItem,
    MeetingListResponse,
    MeetingUpdate,
)
from app.services import meetings as meeting_service
from app.services.docx_export import DOCX_MEDIA_TYPE, build_meeting_minutes_docx

router = APIRouter(prefix="/api/meetings", tags=["meetings"])


def _to_list_item(meeting: MeetingMinutes) -> MeetingListItem:
    return MeetingListItem(
        id=meeting.id,
        meeting_date=meeting.meeting_date,
        notes_preview=meeting_service.to_preview(meeting),
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


def _to_detail(meeting: MeetingMinutes) -> MeetingDetail:
    return MeetingDetail(
        id=meeting.id,
        meeting_date=meeting.meeting_date,
        notes_html=meeting.notes_html,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
    )


@router.get("", response_model=MeetingListResponse)
def list_meetings(
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    size: int = 20,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    rows, total = meeting_service.list_meetings(
        db, search=search, date_from=date_from, date_to=date_to, page=page, size=size
    )
    return MeetingListResponse(
        items=[_to_list_item(m) for m in rows], total=total, page=page, size=size
    )


@router.get("/export")
def export_all_meetings(
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    rows = meeting_service.list_all_for_export(db, search=search, date_from=date_from, date_to=date_to)
    content = build_meeting_minutes_docx([(m.meeting_date, m.notes_html) for m in rows])
    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": 'attachment; filename="svmss_meeting_minutes.docx"'},
    )


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    return _to_detail(meeting_service.get_meeting(db, meeting_id))


@router.get("/{meeting_id}/export")
def export_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
):
    meeting = meeting_service.get_meeting(db, meeting_id)
    content = build_meeting_minutes_docx([(meeting.meeting_date, meeting.notes_html)])
    filename = f"svmss_meeting_{meeting.meeting_date.isoformat()}.docx"
    return Response(
        content=content,
        media_type=DOCX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=MeetingDetail, status_code=status.HTTP_201_CREATED)
def create_meeting(
    body: MeetingCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    meeting = meeting_service.create_meeting(
        db, admin_id=admin.id, meeting_date=body.meeting_date, notes_html=body.notes_html
    )
    return _to_detail(meeting)


@router.put("/{meeting_id}", response_model=MeetingDetail)
def update_meeting(
    meeting_id: int,
    body: MeetingUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    meeting = meeting_service.update_meeting(
        db,
        admin_id=admin.id,
        meeting_id=meeting_id,
        meeting_date=body.meeting_date,
        notes_html=body.notes_html,
    )
    return _to_detail(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(get_current_admin),
):
    meeting_service.delete_meeting(db, admin_id=admin.id, meeting_id=meeting_id)