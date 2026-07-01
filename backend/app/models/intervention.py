"""분기 개입 응답. 사양서 4.8."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Text, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InterventionType(str, PyEnum):
    """정동 좌표 기반 분기.
    
    SELF_DISTANCING: 좌하단/좌측 — 자기거리두기 (3인칭 시점)
    GROUNDING: 좌상단 — 그라운딩 + 시간적 거리두기
    ACTIVATION: 우측/중립 — 행동활성화 (if-then)
    """
    SELF_DISTANCING = "self_distancing"
    GROUNDING = "grounding"
    ACTIVATION = "activation"


class InterventionResponse(Base):
    __tablename__ = "intervention_responses"

    response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("affect_records.record_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    intervention_type: Mapped[InterventionType] = mapped_column(
 	   Enum(
   	     InterventionType,
    	    name="intervention_type",
   	     values_callable=lambda x: [e.value for e in x],
 	   ),
  	  nullable=False,
	)
    # 사용자가 입력한 응답. 건너뛴 경우 null.
    user_response_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
