"""사용자(피험자) 모델."""
import uuid
from datetime import datetime, time
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Time, Integer, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    DROPPED = "dropped"
    COMPLETED = "completed"


class RecordMode(str, PyEnum):
    """사용자별 기본 기록 모드. 사양서 4.3.1."""
    POINT = "point"
    TRAJECTORY = "trajectory"


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

    # 알림 시간대 3구간 — 사양서 8항. 각 구간 시작/끝.
    notify_morning_start: Mapped[time] = mapped_column(Time, default=time(9, 0))
    notify_morning_end: Mapped[time] = mapped_column(Time, default=time(12, 0))
    notify_afternoon_start: Mapped[time] = mapped_column(Time, default=time(13, 0))
    notify_afternoon_end: Mapped[time] = mapped_column(Time, default=time(17, 0))
    notify_evening_start: Mapped[time] = mapped_column(Time, default=time(19, 0))
    notify_evening_end: Mapped[time] = mapped_column(Time, default=time(22, 0))

    # 사용자 설정 기록 모드 (점/궤도)
    record_mode: Mapped[RecordMode] = mapped_column(
    	Enum(
  	      RecordMode,
  	      name="record_mode",
  	      values_callable=lambda x: [e.value for e in x],
  	  ),
   	 default=RecordMode.POINT,
	)
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
