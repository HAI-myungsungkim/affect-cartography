"""정동 기록 라우터. 사양서 4.3 / 4.3.4."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affect import AffectRecord, Quadrant, RecordModeAffect, RecordSlot
from app.models.user import User, RecordMode
from app.schemas.affect import (
    AffectRecordCreate,
    AffectRecordResponse,
    compute_quadrant,
)

router = APIRouter(prefix="/affect", tags=["affect"])


@router.post(
    "/record",
    response_model=AffectRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_affect_record(
    payload: AffectRecordCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """정동 기록 생성. 점 모드 / 궤도 모드 통합 처리.

    - 점 모드: valence, arousal 단일 좌표 저장
    - 궤도 모드: trajectory_points 시퀀스 + 끝점을 valence/arousal로 저장
    - 연습 세션(is_practice=true)도 동일하게 저장하되 분석 시 제외 가능
    """
    quadrant_str = compute_quadrant(payload.valence, payload.arousal)

    record = AffectRecord(
        user_id=current_user.user_id,
        record_date=payload.record_date,
        slot=RecordSlot(payload.slot),
        valence=payload.valence,
        arousal=payload.arousal,
        quadrant=Quadrant(quadrant_str),
        mode=RecordModeAffect(payload.mode),
        trajectory_points=(
            [p.model_dump() for p in payload.trajectory_points]
            if payload.trajectory_points
            else None
        ),
        duration_window_minutes=payload.duration_window_minutes,
        is_practice=payload.is_practice,
        response_latency_ms=payload.response_latency_ms,
        prompt_id=payload.prompt_id,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    return AffectRecordResponse(
        record_id=str(record.record_id),
        user_id=str(record.user_id),
        timestamp=record.timestamp,
        record_date=record.record_date,
        slot=record.slot.value,
        valence=record.valence,
        arousal=record.arousal,
        quadrant=record.quadrant.value,
        mode=record.mode.value,
        duration_window_minutes=record.duration_window_minutes,
        is_practice=record.is_practice,
    )


@router.get("/records", response_model=list[AffectRecordResponse])
async def list_my_records(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, le=200),
    include_practice: bool = Query(default=False),
):
    """내 정동 기록 목록 (최신순). 대시보드(8단계) 미리보기."""
    stmt = select(AffectRecord).where(AffectRecord.user_id == current_user.user_id)
    if not include_practice:
        stmt = stmt.where(AffectRecord.is_practice.is_(False))
    stmt = stmt.order_by(desc(AffectRecord.timestamp)).limit(limit)
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [
        AffectRecordResponse(
            record_id=str(r.record_id),
            user_id=str(r.user_id),
            timestamp=r.timestamp,
            record_date=r.record_date,
            slot=r.slot.value,
            valence=r.valence,
            arousal=r.arousal,
            quadrant=r.quadrant.value,
            mode=r.mode.value,
            duration_window_minutes=r.duration_window_minutes,
            is_practice=r.is_practice,
        )
        for r in records
    ]


@router.post("/settings/record-mode")
async def update_record_mode(
    mode: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """사용자 기본 기록 모드 전환. 사양서 4.3.6.

    이전 기록은 원래 모드 그대로 보존됨.
    """
    if mode not in ("point", "trajectory"):
        raise HTTPException(status_code=400, detail="mode는 'point' 또는 'trajectory'여야 합니다")
    current_user.record_mode = RecordMode(mode)
    await db.flush()
    return {"record_mode": mode}


@router.post("/settings/practice-done")
async def mark_practice_done(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """궤도 모드 연습 세션 완료 표시. 사양서 4.3.3."""
    current_user.trajectory_practice_done = True
    await db.flush()
    return {"trajectory_practice_done": True}
