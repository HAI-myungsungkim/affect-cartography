"""감정 기록 + 한국어 감정 단어 사전."""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, ForeignKey, func
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB

_JSON = JSONB().with_variant(JSON(), "sqlite")
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class EmotionRecord(Base):
    """사용자가 남긴 최종 감정 + 강도. 사양서 4.7.

    두 가지 입력 방식을 모두 지원:
      - 서술형(현재 기본): free_text에 자유 서술(단어/문장) + intensity
      - 사전 기반(레거시): selected_word에 사전 단어 + exploration_path
    감정에는 true value가 없다는 연구 철학에 따라 서술형을 우선한다.
    """
    __tablename__ = "emotion_records"

    emotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("affect_records.record_id", ondelete="CASCADE"),
        nullable=False, index=True, unique=True,  # 1:1 with affect record
    )
    # 서술형 자유 입력 (단어/문장 모두). 감정입자도·표현능력 분석용.
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 레거시 사전 방식 단어 (서술형에서는 free_text 요약을 넣거나 비움)
    selected_word: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )
    intensity: Mapped[int] = mapped_column(Integer, nullable=False)  # 1~5

    # 사전 방식에서 거쳐온 단어 경로 (서술형에서는 빈 배열)
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
    # 리뷰 메타
    reviewed_by_researcher: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String(32), default="gpt-4o-draft")
