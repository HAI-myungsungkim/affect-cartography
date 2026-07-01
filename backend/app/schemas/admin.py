"""관리자 대시보드용 스키마."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AdminUserListItem(BaseModel):
    """관리자 메인 — 사용자 목록 한 행."""
    user_id: str
    participant_code: str
    real_name: str  # 익명화 옵션 시 마스킹됨
    registered_at: datetime
    first_login_at: datetime | None
    last_response_at: datetime | None
    total_records: int
    response_rate: float
    safety_flag_count: int
    status: str  # active / dropped / completed
    record_mode: str
    has_device_bound: bool


class AdminUsersResponse(BaseModel):
    total: int
    users: list[AdminUserListItem]


class AdminUserDetailRecord(BaseModel):
    """사용자 상세 페이지 — 한 기록 + 결합된 모든 데이터."""
    record_id: str
    timestamp: datetime
    valence: float
    arousal: float
    quadrant: str
    mode: str
    is_practice: bool
    trajectory_points: list[dict] | None = None
    emotion_word: str | None = None
    intensity: int | None = None
    exploration_path: list[str] | None = None
    intervention_type: str | None = None
    intervention_text: str | None = None
    dialogue_turns: int = 0  # 대화 턴 수


class AdminUserDetail(BaseModel):
    user_id: str
    participant_code: str
    real_name: str
    registered_at: datetime
    status: str
    record_mode: str
    summary: dict  # total_records, response_rate, etc.
    records: list[AdminUserDetailRecord]


class CreateParticipantRequest(BaseModel):
    participant_code: str = Field(..., min_length=2, max_length=32)
    real_name: str = Field(default="", max_length=64)


class CreateParticipantResponse(BaseModel):
    user_id: str
    participant_code: str
    real_name: str
    registered_at: datetime


class UnbindDeviceResponse(BaseModel):
    user_id: str
    participant_code: str
    message: str


class SafetyFlagOut(BaseModel):
    flag_id: str
    user_id: str
    participant_code: str
    real_name: str
    flag_type: str
    trigger_text: str | None
    matched_keywords: str | None
    raised_at: datetime
    reviewed_by: str | None
    reviewed_at: datetime | None


class DialogueAuditItem(BaseModel):
    """대화 감사 페이지 — 무작위 표본 한 건."""
    record_id: str
    participant_code: str
    quadrant: str
    valence: float
    arousal: float
    timestamp: datetime
    turns: list[dict]  # [{turn_index, speaker, message_text, timestamp}]
    flagged: bool


ExportFormat = Literal["csv", "json"]


class FlagReviewRequest(BaseModel):
    reviewed_by: str = Field(..., max_length=64)
    note: str | None = Field(default=None, max_length=500)
