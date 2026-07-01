"""분기 개입 응답 저장 스키마. 사양서 4.8."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


InterventionType = Literal["self_distancing", "grounding", "activation"]


class InterventionResponseCreate(BaseModel):
    record_id: str
    intervention_type: InterventionType
    # 사용자가 텍스트로 응답했는지, 그냥 "읽었어요"만 눌렀는지
    user_response_text: str | None = Field(default=None, max_length=2000)


class InterventionResponseOut(BaseModel):
    response_id: str
    record_id: str
    intervention_type: str
    user_response_text: str | None
    completed_at: datetime


class InterventionPromptOut(BaseModel):
    """프론트가 GET으로 받아서 화면에 표시할 프롬프트 텍스트.
    
    사용자의 실명을 포함한 동적 치환 결과를 반환한다.
    """
    intervention_type: str
    title: str
    body: str
    placeholder: str  # 입력 필드 힌트
    allow_skip: bool = True
