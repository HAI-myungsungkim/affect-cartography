"""타인 관찰 기록 모델. 실험 축1(관찰 대상)의 결과 저장.

관찰 대상의 정동(V-A) 좌표를 남겨, 타인의 감정 상태가 자기 기록에
영향을 주는지 분석할 수 있게 한다.
"""
import uuid
from datetime import datetime, date
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Date, Float, String, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.affect import RecordSlot, Quadrant


class ObservationTarget(str, PyEnum):
    """관찰 대상의 유형.

    recall_other   : 주변 실제 인물을 떠올려 관찰
    scenario_other : 앱 내 시나리오 인물을 관찰
    """
    RECALL_OTHER = "recall_other"
    SCENARIO_OTHER = "scenario_other"


class ObservationRecord(Base):
    """타인 관찰 정동 기록. 실험 축1."""
    __tablename__ = "observation_records"

    observation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # 어느 날짜/슬롯의 기록인지 (자기 정동 기록과 짝지음)
    record_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    slot: Mapped[RecordSlot] = mapped_column(
        Enum(
            RecordSlot,
            name="record_slot",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )

    target_type: Mapped[ObservationTarget] = mapped_column(
        Enum(
            ObservationTarget,
            name="observation_target",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    # 앱 내 시나리오일 때 어떤 시나리오였는지 (recall_other면 null)
    scenario_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # 관찰한 타인의 정동 좌표 (-1.0 ~ +1.0)
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

    # 관찰한 타인의 감정 단어(선택). 자유 입력.
    emotion_word: Mapped[str | None] = mapped_column(String(64), nullable=True)
