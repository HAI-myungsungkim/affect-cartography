"""감정 단어 선택 결과 저장 스키마."""
from datetime import datetime

from pydantic import BaseModel, Field


class EmotionSelectRequest(BaseModel):
    """사양서 4.7 — 최종 단어 + 강도 + 탐색 경로."""
    record_id: str
    selected_word: str = Field(..., max_length=32)
    intensity: int = Field(..., ge=1, le=5)
    # 사용자가 거쳐온 단어 경로 ["답답하다", "막막하다", "무력하다"]
    exploration_path: list[str] = Field(default_factory=list)


class EmotionSelectResponse(BaseModel):
    emotion_id: str
    record_id: str
    selected_word: str
    intensity: int
    exploration_path: list[str]
    final_at: datetime
    # 7단계 분기 개입 안내 — 클라이언트는 이걸 보고 다음 화면을 결정
    intervention_type: str  # self_distancing / grounding / activation
