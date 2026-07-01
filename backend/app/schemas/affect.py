"""정동 기록 관련 Pydantic 스키마."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class TrajectoryPoint(BaseModel):
    """궤도 모드의 좌표 시퀀스 한 점. 사양서 4.3.2."""
    v: float = Field(..., ge=-1.0, le=1.0, description="valence")
    a: float = Field(..., ge=-1.0, le=1.0, description="arousal")
    t: int = Field(..., ge=0, description="시작점 기준 ms 오프셋")


class AffectRecordCreate(BaseModel):
    """정동 기록 생성 요청. 점/궤도 모드 통합."""
    mode: Literal["point", "trajectory"] = "point"
    valence: float = Field(..., ge=-1.0, le=1.0)
    arousal: float = Field(..., ge=-1.0, le=1.0)
    # 궤도 모드 전용
    trajectory_points: list[TrajectoryPoint] | None = None
    duration_window_minutes: int = Field(default=180, ge=1, le=1440)
    is_practice: bool = False
    # 메타
    response_latency_ms: int | None = Field(default=None, ge=0)
    prompt_id: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def validate_mode_consistency(self) -> "AffectRecordCreate":
        if self.mode == "trajectory":
            if not self.trajectory_points or len(self.trajectory_points) < 2:
                raise ValueError(
                    "궤도 모드는 trajectory_points에 최소 2개 좌표가 필요합니다"
                )
            # 끝점이 valence/arousal과 일치하는지 확인 (사양서: 끝점=현재 정동)
            last = self.trajectory_points[-1]
            if abs(last.v - self.valence) > 1e-6 or abs(last.a - self.arousal) > 1e-6:
                raise ValueError(
                    "궤도 모드에서 valence/arousal은 trajectory_points의 끝점과 일치해야 합니다"
                )
        else:  # point
            if self.trajectory_points:
                raise ValueError("점 모드에서는 trajectory_points를 보내지 않습니다")
        return self


class AffectRecordResponse(BaseModel):
    record_id: str
    user_id: str
    timestamp: datetime
    valence: float
    arousal: float
    quadrant: str
    mode: str
    duration_window_minutes: int
    is_practice: bool

    class Config:
        from_attributes = True


def compute_quadrant(valence: float, arousal: float) -> str:
    """V-A 좌표를 4사분면으로 분류. 사양서 affect.py Quadrant 정의 참고.
    
    경계(=0)는 양의 사분면에 포함.
    """
    if valence >= 0 and arousal >= 0:
        return "q1"  # 유쾌-고각성
    if valence < 0 and arousal >= 0:
        return "q2"  # 불쾌-고각성
    if valence < 0 and arousal < 0:
        return "q3"  # 불쾌-저각성
    return "q4"  # 유쾌-저각성
