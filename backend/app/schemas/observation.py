"""타인 관찰 기록 스키마. 실험 축1."""
from datetime import datetime, date
from typing import Literal

from pydantic import BaseModel, Field


class ObservationCreate(BaseModel):
    """타인 관찰 정동 기록 생성 요청."""
    record_date: date
    slot: Literal["morning", "afternoon", "evening"]
    target_type: Literal["recall_other", "scenario_other"]
    scenario_id: str | None = Field(default=None, max_length=64)
    valence: float = Field(..., ge=-1.0, le=1.0)
    arousal: float = Field(..., ge=-1.0, le=1.0)
    emotion_word: str | None = Field(default=None, max_length=64)


class ObservationResponse(BaseModel):
    observation_id: str
    user_id: str
    timestamp: datetime
    record_date: date
    slot: str
    target_type: str
    scenario_id: str | None
    valence: float
    arousal: float
    quadrant: str
    emotion_word: str | None

    class Config:
        from_attributes = True
