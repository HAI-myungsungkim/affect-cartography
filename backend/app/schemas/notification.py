"""알림 설정 스키마. 사양서 8항."""
from datetime import datetime, time

from pydantic import BaseModel, Field, field_validator


class TimeWindow(BaseModel):
    """알림 발송 시간대 한 구간."""
    start: str = Field(..., description="HH:MM 형식")
    end: str = Field(..., description="HH:MM 형식")

    @field_validator("start", "end")
    @classmethod
    def _valid_format(cls, v: str) -> str:
        try:
            h, m = v.split(":")
            hi, mi = int(h), int(m)
            if not (0 <= hi <= 23 and 0 <= mi <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("HH:MM 형식이어야 합니다 (예: 09:00)")
        return v

    def to_time_range(self) -> tuple[time, time]:
        sh, sm = map(int, self.start.split(":"))
        eh, em = map(int, self.end.split(":"))
        return time(sh, sm), time(eh, em)


class NotificationSettings(BaseModel):
    """사용자 알림 시간대 3구간."""
    morning: TimeWindow
    afternoon: TimeWindow
    evening: TimeWindow


class NotificationSettingsUpdate(BaseModel):
    """일부만 업데이트 가능."""
    morning: TimeWindow | None = None
    afternoon: TimeWindow | None = None
    evening: TimeWindow | None = None


class ScheduledPrompt(BaseModel):
    """오늘 발송될 알림 한 건."""
    prompt_id: str
    window: str  # morning / afternoon / evening
    scheduled_at: datetime  # 사용자 로컬 시각 기준 발송 예정 UTC


class TodaySchedule(BaseModel):
    """오늘의 알림 발송 스케줄 (Flutter가 가져가서 로컬 알림 등록)."""
    user_id: str
    date: str  # YYYY-MM-DD
    prompts: list[ScheduledPrompt]


class PromptAck(BaseModel):
    """알림에 응답했음을 표시 (응답률 계산용)."""
    prompt_id: str
    responded_at: datetime
