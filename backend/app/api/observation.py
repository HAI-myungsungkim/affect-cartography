"""타인 관찰 기록 라우터. 실험 축1(관찰 대상)의 결과 저장."""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.observation import ObservationRecord, ObservationTarget
from app.models.affect import Quadrant, RecordSlot
from app.models.user import User
from app.schemas.affect import compute_quadrant
from app.schemas.observation import ObservationCreate, ObservationResponse

router = APIRouter(prefix="/observation", tags=["observation"])


@router.post(
    "/record",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_observation(
    payload: ObservationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """타인 관찰 정동 기록 저장. 자기 기록 전 단계(축1)에서 호출."""
    quadrant_str = compute_quadrant(payload.valence, payload.arousal)

    obs = ObservationRecord(
        user_id=current_user.user_id,
        record_date=payload.record_date,
        slot=RecordSlot(payload.slot),
        target_type=ObservationTarget(payload.target_type),
        scenario_id=payload.scenario_id,
        valence=payload.valence,
        arousal=payload.arousal,
        quadrant=Quadrant(quadrant_str),
        emotion_word=payload.emotion_word,
    )
    db.add(obs)
    await db.flush()
    await db.refresh(obs)

    return ObservationResponse(
        observation_id=str(obs.observation_id),
        user_id=str(obs.user_id),
        timestamp=obs.timestamp,
        record_date=obs.record_date,
        slot=obs.slot.value,
        target_type=obs.target_type.value,
        scenario_id=obs.scenario_id,
        valence=obs.valence,
        arousal=obs.arousal,
        quadrant=obs.quadrant.value,
        emotion_word=obs.emotion_word,
    )
