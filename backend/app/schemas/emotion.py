"""감정 단어 사전 관련 Pydantic 스키마."""
from pydantic import BaseModel, Field


class NeighborInfo(BaseModel):
    word: str
    direction: str
    delta_v: float
    delta_a: float


class EmotionWordOut(BaseModel):
    word: str
    definition: str
    example: str
    valence: float
    arousal: float
    neighbors: list[NeighborInfo] = Field(default_factory=list)


class EmotionCandidatesOut(BaseModel):
    """1차 후보 단어 (사양서 4.5)."""
    candidates: list[EmotionWordOut]


class NeighborWordsOut(BaseModel):
    """선택된 단어 + 인접 단어 (사양서 4.6)."""
    center: EmotionWordOut
    neighbors: list[EmotionWordOut]
