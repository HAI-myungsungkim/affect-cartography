"""감정 기록 저장 스키마."""
from datetime import datetime
from pydantic import BaseModel, Field, model_validator


class EmotionSelectRequest(BaseModel):
    """감정 기록 요청. 서술형(free_text) 우선, 사전 방식(selected_word)도 허용.

    - 서술형: free_text + intensity (권장)
    - 사전 방식(레거시): selected_word + intensity + exploration_path
    둘 중 하나는 반드시 있어야 한다.
    """
    record_id: str
    free_text: str | None = Field(default=None, max_length=2000)
    selected_word: str | None = Field(default=None, max_length=128)
    intensity: int = Field(..., ge=1, le=5)
    exploration_path: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def at_least_one_input(self) -> "EmotionSelectRequest":
        has_free = self.free_text is not None and self.free_text.strip() != ""
        has_word = self.selected_word is not None and self.selected_word.strip() != ""
        if not has_free and not has_word:
            raise ValueError("free_text 또는 selected_word 중 하나는 입력해야 합니다")
        return self


class EmotionSelectResponse(BaseModel):
    emotion_id: str
    record_id: str
    free_text: str | None
    selected_word: str | None
    intensity: int
    exploration_path: list[str]
    final_at: datetime
    # 개입 유형. 앱은 참고 보고 다음 화면을 결정.
    intervention_type: str  # self_distancing / grounding / activation
