"""에이전트 대화 관련 스키마."""
from datetime import datetime

from pydantic import BaseModel, Field


class DialogueTurnRequest(BaseModel):
    record_id: str = Field(..., description="해당 정동 기록의 record_id")
    user_message: str | None = Field(
        default=None,
        max_length=2000,
        description="사용자 메시지. None이면 첫 턴(에이전트가 먼저 시작).",
    )


class DialogueTurnResponse(BaseModel):
    turn_index: int
    agent_message: str
    is_final: bool = False  # 최대 턴 도달 또는 위기 감지
    safety_flag_raised: bool = False
    crisis_flag_type: str | None = None  # suicide_ideation / self_harm / severe_distress


class DialogueHistoryItem(BaseModel):
    turn_index: int
    speaker: str
    message_text: str
    timestamp: datetime

    class Config:
        from_attributes = True


class DialogueHistoryResponse(BaseModel):
    record_id: str
    turns: list[DialogueHistoryItem]
