"""분기 개입 라우터. 사양서 4.8."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.api.emotion import intervention_for
from app.core.database import get_db
from app.models.affect import AffectRecord
from app.models.intervention import InterventionResponse, InterventionType
from app.models.user import User
from app.schemas.intervention import (
    InterventionPromptOut,
    InterventionResponseCreate,
    InterventionResponseOut,
)
from app.services.intervention_prompts import build_intervention_prompt

router = APIRouter(prefix="/intervention", tags=["intervention"])


async def _load_record(
    db: AsyncSession, record_id: str, user: User
) -> AffectRecord:
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="record_id 형식 오류")
    result = await db.execute(
        select(AffectRecord).where(
            AffectRecord.record_id == rec_uuid,
            AffectRecord.user_id == user.user_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다")
    return record


@router.get("/prompt", response_model=InterventionPromptOut)
async def get_prompt(
    record_id: str = Query(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """정동 좌표 기반 개입 프롬프트 텍스트 반환.

    클라이언트는 6단계 단어 선택 응답의 intervention_type을 그대로 사용해도 되고,
    이 엔드포인트로 새로 가져와도 된다 (실명이 동적으로 치환됨).
    """
    record = await _load_record(db, record_id, current_user)
    itype = intervention_for(record.valence, record.arousal)
    prompt = build_intervention_prompt(itype, current_user.real_name)
    return InterventionPromptOut(**prompt)


@router.post(
    "/response",
    response_model=InterventionResponseOut,
    status_code=201,
)
async def create_intervention_response(
    payload: InterventionResponseCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """개입 응답 저장. 사용자가 텍스트를 적었거나 "읽었어요"만 누른 경우 모두 처리.

    - intervention_type은 사양서 4.8 규칙(좌표 → 유형)과 일치해야 함 (서버에서 재검증)
    - user_response_text=None이면 "건너뛰기" 또는 "읽었어요"로 간주
    """
    record = await _load_record(db, payload.record_id, current_user)

    # 정합성 재검증: 클라이언트가 보낸 intervention_type이 좌표에 맞는지
    expected = intervention_for(record.valence, record.arousal)
    if payload.intervention_type != expected:
        raise HTTPException(
            status_code=400,
            detail=(
                f"좌표(v={record.valence}, a={record.arousal})에 맞지 않는 "
                f"intervention_type: {payload.intervention_type} (기대값 {expected})"
            ),
        )

    # 중복 응답 차단 (record_id에 이미 응답이 있는지)
    result = await db.execute(
        select(InterventionResponse).where(
            InterventionResponse.record_id == record.record_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="이 기록에 이미 개입 응답이 저장되어 있습니다",
        )

    resp = InterventionResponse(
        record_id=record.record_id,
        intervention_type=InterventionType(payload.intervention_type),
        user_response_text=payload.user_response_text,
    )
    db.add(resp)
    await db.flush()
    await db.refresh(resp)

    return InterventionResponseOut(
        response_id=str(resp.response_id),
        record_id=str(resp.record_id),
        intervention_type=resp.intervention_type.value,
        user_response_text=resp.user_response_text,
        completed_at=resp.completed_at,
    )
