from datetime import date, datetime

from pydantic import BaseModel, Field, field_serializer


# ---- Donations ----
class DonationCreateResponse(BaseModel):
    donation_id: int
    donor_id: int
    receipt_no: str
    pdf_url: str
    email_sent: bool


class DonationListItem(BaseModel):
    id: int
    donor_id: int
    donor_name: str
    donor_phone: str
    amount_paise: int
    reason: str
    reason_other: str | None
    mode: str
    status: str
    receipt_id: int | None
    receipt_no: str | None
    created_at: datetime

    @field_serializer("amount_paise")
    def _serialize_amount(self, v: int) -> int:
        return v

    class Config:
        from_attributes = True


class DonationListResponse(BaseModel):
    items: list[DonationListItem]
    total: int
    page: int
    size: int


# ---- Receipts ----
class ReceiptLookupRequest(BaseModel):
    phone: str = Field(min_length=10, max_length=15)
    last4: str = Field(min_length=4, max_length=4)


class ReceiptLookupItem(BaseModel):
    receipt_no: str
    amount_paise: int
    reason: str
    status: str
    issued_at: datetime
    pdf_url: str


class VoidRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


# ---- Donors ----
class DonorDonationItem(BaseModel):
    id: int
    amount_paise: int
    reason: str
    status: str
    receipt_no: str | None
    created_at: datetime


class DonorDetailResponse(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None
    address: str | None
    lifetime_total_paise: int
    donations: list[DonorDonationItem]


class DonorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=10, max_length=15)
    email: str | None = None
    address: str | None = None


class DonorUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=10, max_length=15)
    email: str | None = None
    address: str | None = None


class DonorListItem(BaseModel):
    id: int
    name: str
    phone: str
    email: str | None
    address: str | None
    created_at: datetime


class DonorListResponse(BaseModel):
    items: list[DonorListItem]
    total: int
    page: int
    size: int


# ---- Batch receipt generation ----
class BatchReceiptItem(BaseModel):
    donor_id: int
    amount_paise: int = Field(gt=0)
    mode: str
    reason: str = "monthly_donation"
    reason_other: str | None = None
    upi_txn_id: str | None = None
    bank_name: str | None = None
    branch_name: str | None = None
    transaction_date: date | None = None


class BatchReceiptResultItem(BaseModel):
    donor_id: int
    donor_name: str
    status: str  # "generated" | "failed"
    receipt_no: str | None = None
    receipt_id: int | None = None
    pdf_url: str | None = None
    email_sent: bool = False
    error: str | None = None


class BatchReceiptResponse(BaseModel):
    period: str
    generated: int
    failed: int
    results: list[BatchReceiptResultItem]


# ---- Monthly meeting minutes ----
class MeetingCreate(BaseModel):
    meeting_date: date
    notes_html: str = Field(min_length=1)


class MeetingUpdate(MeetingCreate):
    pass


class MeetingListItem(BaseModel):
    id: int
    meeting_date: date
    notes_preview: str
    created_at: datetime
    updated_at: datetime


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]
    total: int
    page: int
    size: int


class MeetingDetail(BaseModel):
    id: int
    meeting_date: date
    notes_html: str
    created_at: datetime
    updated_at: datetime


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---- NGO settings ----
class NgoSettingsPublic(BaseModel):
    name: str
    address: str
    upi_id: str
    bank_details: dict
    logo_url: str | None


class NgoSettingsAdmin(NgoSettingsPublic):
    reg_80g_number: str | None


class NgoSettingsUpdate(BaseModel):
    name: str
    address: str
    upi_id: str
    bank_details: dict
    reg_80g_number: str | None = None