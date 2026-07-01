"""안전 플래그. 자살/자해/위기 키워드 탐지 시 발급. 사양서 7항, 10항."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, String, Text, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FlagType(str, PyEnum):
    SUICIDE_IDEATION = "suicide_ideation"
    SELF_HARM = "self_harm"
    SEVERE_DISTRESS = "severe_distress"
    OTHER = "other"


class SafetyFlag(Base):
    __tablename__ = "safety_flags"

    flag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    # 대화 중 발급된 경우 해당 affect record 참조
    record_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("affect_records.record_id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    flag_type: Mapped[FlagType] = mapped_column(
  	  Enum(
    	    FlagType,
     	   name="flag_type",
     	   values_callable=lambda x: [e.value for e in x],
  	  ),
  	  nullable=False,
	)
    # 트리거된 메시지 발췌 (감사용)
    trigger_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 매칭된 키워드 (정규식 1차 필터 결과)
    matched_keywords: Mapped[str | None] = mapped_column(String(256), nullable=True)

    raised_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
