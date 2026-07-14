"""사용자(피험자) 모델."""
import uuid
from datetime import datetime, time
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Time, Integer, Boolean, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    DROPPED = "dropped"
    COMPLETED = "completed"


class RecordMode(str, PyEnum):
    """사용자별 기본 기록 모드. 사양서 4.3.1. (실험 축2: 정동 형태)"""
    POINT = "point"
    TRAJECTORY = "trajectory"


class ObservationMode(str, PyEnum):
    """실험 축1: 관찰 대상.

    self_only      : 자기 정동/감정만 기록 (대조군)
    recall_other   : 주변 실제 인물을 떠올려 관찰 기록 후 자기 기록
    scenario_other : 앱 내 시나리오 인물을 관찰 기록 후 자기 기록
    """
    SELF_ONLY = "self_only"
    RECALL_OTHER = "recall_other"
    SCENARIO_OTHER = "scenario_other"


class EmotionTiming(str, PyEnum):
    """실험 축3: 감정 기록 시점.

    immediate : 정동 기록 직후 같은 슬롯의 감정을 바로 기록 (대조군)
    delayed   : 정동 기록 후, 직전 슬롯의 정동을 다시 보고 그때의 감정을 기록
                (정동과 감정 기록이 한 슬롯씩 밀림)
    """
    IMMEDIATE = "immediate"
    DELAYED = "delayed"


class AgentMode(str, PyEnum):
    """실험 축4: Agent 개입.

    none    : 정동 기록 후 바로 감정 기록 (대조군)
    enabled : 감정 기록 전 AI 에이전트와 상황/신체/환경을 대화
    """
    NONE = "none"
    ENABLED = "enabled"


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # 피험자 코드 (예: P001) — 연구진이 발급
    participant_code: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    # 실명 — LLM 호출 시에만 평문 사용, 저장은 평문이지만 AES-256 at-rest로 보호
    real_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # 디바이스 ID — SHA-256 해시 저장. 엄격 바인딩 정책.
    device_id_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, index=True
    )

    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    first_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 알림 시간대 3구간 — 사양서 8항. 각 구간 시작/끝
    notify_morning_start: Mapped[time] = mapped_column(Time, default=time(9, 0))
    notify_morning_end: Mapped[time] = mapped_column(Time, default=time(12, 0))
    notify_afternoon_start: Mapped[time] = mapped_column(Time, default=time(13, 0))
    notify_afternoon_end: Mapped[time] = mapped_column(Time, default=time(17, 0))
    notify_evening_start: Mapped[time] = mapped_column(Time, default=time(19, 0))
    notify_evening_end: Mapped[time] = mapped_column(Time, default=time(22, 0))

    # ---- 실험 조건 배정 (관리자가 참가자별로 배정, 블라인드) ----
    # 축2: 정동 기록 형태 (점/궤도)
    record_mode: Mapped[RecordMode] = mapped_column(
        Enum(
            RecordMode,
            name="record_mode",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=RecordMode.POINT,
    )
    # 축1: 관찰 대상
    observation_mode: Mapped[ObservationMode] = mapped_column(
        Enum(
            ObservationMode,
            name="observation_mode",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=ObservationMode.SELF_ONLY,
    )
    # 축3: 감정 기록 시점
    emotion_timing: Mapped[EmotionTiming] = mapped_column(
        Enum(
            EmotionTiming,
            name="emotion_timing",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=EmotionTiming.IMMEDIATE,
    )
    # 축4: Agent 개입
    agent_mode: Mapped[AgentMode] = mapped_column(
        Enum(
            AgentMode,
            name="agent_mode",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AgentMode.NONE,
    )
    # 교육자료 노출 여부 (특정 피험자에게만 홈에서 열람 허용)
    education_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # 궤도 모드 연습 세션 완료 여부
    trajectory_practice_done: Mapped[bool] = mapped_column(default=False)

    study_phase: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=UserStatus.ACTIVE,
    )
