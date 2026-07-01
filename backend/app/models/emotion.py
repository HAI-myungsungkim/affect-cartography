"""감정 단어 선택 기록 + 한국어 감정 단어 사전."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, ForeignKey, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB

_JSON = JSONB().with_variant(JSON(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmotionRecord(Base):
    """사용자가 선택한 최종 감정 단어 + 강도. 사양서 4.7."""
    __tablename__ = "emotion_records"

    emotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("affect_records.record_id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True,  # 1:1 with affect record
    )
    selected_word: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)  # 1~5

    # 사용자가 거쳐온 단어 경로 ["답답하다", "막막하다", "무겁다"]
    exploration_path: Mapped[list] = mapped_column(_JSON, default=list)
    final_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class EmotionDictionary(Base):
    """한국어 감정 단어 사전. 사양서 6항. 4단계에서 GPT-4o로 초안 생성."""
    __tablename__ = "emotion_dictionary"

    word: Mapped[str] = mapped_column(String(32), primary_key=True)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[str] = mapped_column(Text, nullable=False)
    valence: Mapped[float] = mapped_column(Float, nullable=False)  # -1.0 ~ +1.0
    arousal: Mapped[float] = mapped_column(Float, nullable=False)
    # 인접 단어: [{"word": "...", "direction": "...", "delta_v": ..., "delta_a": ...}, ...]
    neighbors: Mapped[list] = mapped_column(_JSON, default=list)
    # 큐레이션 메타
    reviewed_by_researcher: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String(32), default="gpt-4o-draft")
