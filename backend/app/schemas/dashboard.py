"""대시보드 응답 스키마. 사양서 4.9."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class TrajectoryPointOut(BaseModel):
    v: float
    a: float
    t: int


class AffectPointOut(BaseModel):
    """대시보드 정동 궤적 탭의 한 항목. 점 모드 + 궤도 모드 통합."""
    record_id: str
    timestamp: datetime
    valence: float
    arousal: float
    quadrant: str
    mode: Literal["point", "trajectory"]
    # 궤도 모드일 때만 채워짐
    trajectory_points: list[TrajectoryPointOut] | None = None
    # 같은 시점에 선택된 감정 단어 (겹쳐보기 토글용)
    emotion_word: str | None = None
    intensity: int | None = None


class EmotionTimelineItem(BaseModel):
    """감정 기록 탭의 한 항목."""
    record_id: str
    timestamp: datetime
    word: str
    intensity: int
    valence: float
    arousal: float
    quadrant: str


class DashboardSummary(BaseModel):
    """대시보드 상단 요약."""
    total_records: int
    response_rate: float  # 0.0 ~ 1.0
    days_active: int
    safety_flag_count: int  # 자기 알림용 (위기 표현 발생 횟수)


class DashboardData(BaseModel):
    summary: DashboardSummary
    affect_points: list[AffectPointOut]  # 정동 궤적 탭
    emotion_timeline: list[EmotionTimelineItem]  # 감정 기록 탭
