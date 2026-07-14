"""정동(affect) 기록 모델 — 점 모드 + 궤도 모드 통합."""
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Date, Float, Integer, String, Enum, Boolean, ForeignKey, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB

# Postgres에서는 JSONB, SQLite(테스트)에서는 JSON으로 대체
_JSON = JSONB().with_variant(JSON(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Quadrant(str, PyEnum):
    """V-A 평면의 4사분면. (V, A) 부호 기준.

    Q1: 유쾌-고각성 (우상단) — 흥분/기쁨
    Q2: 불쾌-고각성 (좌상단) — 분노/불안
    Q3: 불쾌-저각성 (좌하단) — 우울/피로
    Q4: 유쾌-저각성 (우하단) — 평온/만족
    """
    Q1 = "q1"  # V>0, A>0
    Q2 = "q2"  # V<0, A>0
    Q3 = "q3"  # V<0, A<0
    Q4 = "q4"  # V>0, A<0


class RecordModeAffect(str, PyEnum):
    POINT = "point"
    TRAJECTORY = "trajectory"


class RecordSlot(str, PyEnum):
    """하루 3회 기록 슬롯. 알림 시간대(오전/오후/저녁)에 대응.

    실험 축3(감정 시점)의 '한 슬롯 밀림' 흐름과, 축1(관찰) 기록을
    자기 기록과 짝짓기 위한 기준.
    """
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"


class AffectRecord(Base):
    """정동 기록. 사양서 4.3, 4.3.4."""
    __tablename__ = "affect_records"

    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # 어느 날짜/슬롯의 기록인지. 하루 3회(morning/afternoon/evening).
    # 시간차 그룹(축3)에서 직전 슬롯의 감정을 기록할 때 짝짓기 기준이 됨.
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[RecordSlot] = mapped_column(
        Enum(
            RecordSlot,
            name="record_slot",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # 점 모드: 단일 좌표. 궤도 모드: 끝점 좌표(=현재 정동).
    # 좌표는 -1.0 ~ +1.0 범위.
    valence: Mapped[float] = mapped_column(Float, nullable=False)
    arousal: Mapped[float] = mapped_column(Float, nullable=False)
    quadrant: Mapped[Quadrant] = mapped_column(
        Enum(
            Quadrant,
            name="quadrant",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    # 사양서 4.3.4 확장 필드
    mode: Mapped[RecordModeAffect] = mapped_column(
        Enum(
            RecordModeAffect,
            name="affect_mode",
            values_callable=lambda x: [e.value for e in x],
        ),
        default=RecordModeAffect.POINT,
    )
    # 궤도 모드에서 좌표 시퀀스 [{"v":-0.3,"a":0.1,"t":0}, ...] (t는 ms 오프셋)
    trajectory_points: Mapped[list | None] = mapped_column(_JSON, nullable=True)
    # 회상 시간 윈도우 분. 기본 180분 = 3시간.
    duration_window_minutes: Mapped[int] = mapped_column(Integer, default=180)
    # 연습 세션 여부. 본 분석에서 제외.
    is_practice: Mapped[bool] = mapped_column(Boolean, default=False)

    # V-A grid 표시 후 첫 탭까지의 응답 지연(ms)
    response_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 어떤 알림으로 트리거되었는지 (nullable: 자발 기록)
    prompt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
