"""에이전트 대화 로그. 사양서 4.4."""
import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Integer, Text, Enum, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Speaker(str, PyEnum):
    USER = "user"
    AGENT = "agent"


class AgentDialogue(Base):
    __tablename__ = "agent_dialogues"

    dialogue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("affect_records.record_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    turn_index: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker: Mapped[Speaker] = mapped_column(
  	  Enum(
   	     Speaker,
   	     name="speaker",
   	     values_callable=lambda x: [e.value for e in x],
 	   ),
 	   nullable=False,
	)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
