from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel, UniqueConstraint


class Role(str, Enum):
    user = "user"
    astrologer = "astrologer"
    admin = "admin"


class ConsultType(str, Enum):
    chat = "chat"
    call = "call"


class Urgency(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True)
    password_hash: str
    role: Role = Field(default=Role.user, index=True)
    is_suspended: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    __table_args__ = (UniqueConstraint("email"),)


class IssueCategory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True)
    name: str

    __table_args__ = (UniqueConstraint("slug"),)


class Astrologer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, foreign_key="user.id")

    display_name: str
    bio: str = ""

    active_status: bool = Field(default=True, index=True)
    verified_identity: bool = Field(default=False, index=True)

    years_of_experience: int = 0
    primary_language: str = Field(default="English", index=True)

    min_budget: int = 0
    max_budget: int = 999999

    response_time_minutes: int = 30

    average_rating: float = 0.0
    complaint_rate: float = 0.0

    # “learning loop” metrics
    topic_success_rate: float = 0.0
    relevance_success_rate: float = 0.0
    clarity_success_rate: float = 0.0
    helpfulness_success_rate: float = 0.0


class AstrologerSpecialty(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    astrologer_id: int = Field(foreign_key="astrologer.id", index=True)
    issue_category_id: int = Field(foreign_key="issuecategory.id", index=True)

    __table_args__ = (UniqueConstraint("astrologer_id", "issue_category_id"),)


class AstrologerLanguage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    astrologer_id: int = Field(foreign_key="astrologer.id", index=True)
    language: str = Field(index=True)

    __table_args__ = (UniqueConstraint("astrologer_id", "language"),)


class AvailabilitySlot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    astrologer_id: int = Field(foreign_key="astrologer.id", index=True)
    start_at: datetime = Field(index=True)
    end_at: datetime
    is_booked: bool = Field(default=False, index=True)


class Intake(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    issue_category_id: int = Field(foreign_key="issuecategory.id", index=True)

    sub_issue: str = ""
    language: str = Field(default="English", index=True)
    budget_min: int = 0
    budget_max: int = 0
    consult_type: ConsultType = Field(default=ConsultType.chat, index=True)
    urgency: Urgency = Field(default=Urgency.normal, index=True)
    goal: str = ""

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    # Structured consultation form fields
    full_name: str = ""
    date_of_birth: Optional[date] = None
    day_of_birth: str = ""
    birth_time: str = ""
    birth_place: str = ""
    current_address: str = ""
    current_location: str = ""
    problem: str = ""
    preferred_system: str = ""


class SessionStatus(str, Enum):
    booked = "booked"
    completed = "completed"
    cancelled = "cancelled"


class ConsultationSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    astrologer_id: int = Field(foreign_key="astrologer.id", index=True)
    intake_id: int = Field(foreign_key="intake.id", index=True)

    consult_type: ConsultType = Field(default=ConsultType.chat, index=True)
    scheduled_at: datetime = Field(index=True)
    status: SessionStatus = Field(default=SessionStatus.booked, index=True)

    price: int = 0
    payout_processed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="consultationsession.id", index=True)

    helpfulness_score: int = Field(ge=1, le=5, default=3)
    clarity_score: int = Field(ge=1, le=5, default=3)
    relevance_score: int = Field(ge=1, le=5, default=3)

    refund_requested: bool = False
    complaint_flag: bool = False
    repeat_booking_intent: bool = False

    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("session_id"),)


class MatchScore(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    intake_id: int = Field(foreign_key="intake.id", index=True)
    astrologer_id: int = Field(foreign_key="astrologer.id", index=True)

    score: float = Field(default=0.0, index=True)
    reason: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)

    __table_args__ = (UniqueConstraint("intake_id", "astrologer_id"),)


class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True, unique=True)
    full_name: str = ""
    date_of_birth: Optional[date] = None
    birth_time: str = ""
    birth_place: str = ""
    zodiac_sign: str = "aries"
    preferred_language: str = "English"
    wallet_balance: int = Field(default=500)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    session_id: Optional[int] = Field(default=None, foreign_key="consultationsession.id", index=True)
    amount: int = 0
    status: PaymentStatus = Field(default=PaymentStatus.pending, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class KundliRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    name: str
    date_of_birth: date
    birth_time: str
    birth_place: str
    chart_json: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class KundliMatchRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    boy_name: str
    girl_name: str
    score_percent: float = 0.0
    report_json: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ReportType(str, Enum):
    kundli = "kundli"
    match = "match"
    session = "session"
    horoscope = "horoscope"
    child_astro = "child_astro"


class SavedReport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    report_type: ReportType = Field(index=True)
    title: str
    html_content: str = ""
    ref_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class ChildAstroOrder(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    child_name: str
    child_gender: str = ""
    date_of_birth: date
    birth_time: str
    birth_place: str
    country_of_residence: str = ""
    parent_name: str
    parent_email: str
    special_notes: str = ""
    status: str = Field(default="pending", index=True)  # pending, in_analysis, completed
    price_credits: int = 100
    pdf_path: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)



class ChatSender(str, Enum):
    user = "user"
    astrologer = "astrologer"


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="consultationsession.id", index=True)
    sender: ChatSender = Field(index=True)
    sender_user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    body: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SystemConfig(SQLModel, table=True):
    key: str = Field(primary_key=True)
    value: str


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    action: str
    target: str
    ip_address: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class InAppNotification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    target_role: Optional[Role] = Field(default=None, index=True)
    title: str
    body: str
    is_read: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


