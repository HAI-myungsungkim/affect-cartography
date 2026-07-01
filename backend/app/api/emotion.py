"""감정 단어 사전 조회 + 선택 저장 라우터. 사양서 4.5, 4.6, 4.7, 4.8, 6항.

핵심 정책: 사용자에게 제시되는 단어는 반드시 emotion_dictionary 테이블에 등록된 단어만 사용.
이는 일관된 어휘 학습 경험을 보장하기 위함.
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affect import AffectRecord
from app.models.emotion import EmotionDictionary, EmotionRecord
from app.models.user import User
from app.schemas.emotion import (
    EmotionCandidatesOut,
    EmotionWordOut,
    NeighborInfo,
    NeighborWordsOut,
)
from app.schemas.emotion_select import EmotionSelectRequest, EmotionSelectResponse

router = APIRouter(prefix="/emotion", tags=["emotion"])


def _to_out(row: EmotionDictionary) -> EmotionWordOut:
    return EmotionWordOut(
        word=row.word,
        definition=row.definition,
        example=row.example,
        valence=row.valence,
        arousal=row.arousal,
        neighbors=[NeighborInfo(**n) for n in (row.neighbors or [])],
    )


def _distance(v1: float, a1: float, v2: float, a2: float) -> float:
    return ((v1 - v2) ** 2 + (a1 - a2) ** 2) ** 0.5


def intervention_for(valence: float, arousal: float) -> str:
    """사양서 4.8 분기 로직.

    - 좌상단 (불쾌-고각성, V<0 A>=0)  -> grounding (그라운딩 + 시간 거리)
    - 좌측 전반 (불쾌, V<0)           -> self_distancing (자기거리두기)
    - 우측/중립 (V>=0)                -> activation (행동활성화 if-then)
    """
    if valence < 0 and arousal >= 0:
        return "grounding"
    if valence < 0:
        return "self_distancing"
    return "activation"


@router.get("/candidates", response_model=EmotionCandidatesOut)
async def get_candidates(
    valence: float = Query(..., ge=-1.0, le=1.0),
    arousal: float = Query(..., ge=-1.0, le=1.0),
    limit: int = Query(default=5, ge=1, le=10),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """1차 후보 단어 (사양서 4.5)."""
    result = await db.execute(select(EmotionDictionary))
    all_words = result.scalars().all()
    if not all_words:
        raise HTTPException(
            status_code=503,
            detail="감정 단어 사전이 아직 시드되지 않았습니다. 관리자에게 문의해주세요",
        )

    ranked = sorted(
        all_words,
        key=lambda w: _distance(w.valence, w.arousal, valence, arousal),
    )[:limit]
    return EmotionCandidatesOut(candidates=[_to_out(w) for w in ranked])


@router.get("/neighbors", response_model=NeighborWordsOut)
async def get_neighbors(
    word: str = Query(..., max_length=32),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """선택된 단어의 인접 단어들 (사양서 4.6)."""
    result = await db.execute(
        select(EmotionDictionary).where(EmotionDictionary.word == word)
    )
    center = result.scalar_one_or_none()
    if not center:
        raise HTTPException(status_code=404, detail=f"단어를 찾을 수 없습니다: {word}")

    neighbor_names = [n["word"] for n in (center.neighbors or [])]
    result = await db.execute(
        select(EmotionDictionary).where(EmotionDictionary.word.in_(neighbor_names))
    )
    neighbor_rows = result.scalars().all()
    by_word = {n.word: n for n in neighbor_rows}
    ordered = [by_word[n] for n in neighbor_names if n in by_word]

    return NeighborWordsOut(
        center=_to_out(center),
        neighbors=[_to_out(n) for n in ordered],
    )


@router.post("/select", response_model=EmotionSelectResponse, status_code=201)
async def select_emotion(
    payload: EmotionSelectRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """사용자가 선택한 최종 감정 단어 + 강도 저장 (사양서 4.7).

    1. record_id 소유자 확인
    2. selected_word가 사전에 존재하는지 확인 (데이터 일관성)
    3. emotion_records에 저장 (record_id 1:1 제약)
    4. 정동 좌표 기반 분기 개입 유형 반환 (7단계 화면이 이걸 보고 분기)
    """
    try:
        rec_uuid = uuid.UUID(payload.record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="record_id 형식 오류")

    result = await db.execute(
        select(AffectRecord).where(
            AffectRecord.record_id == rec_uuid,
            AffectRecord.user_id == current_user.user_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다")

    # 사전 일관성 검증
    result = await db.execute(
        select(EmotionDictionary).where(EmotionDictionary.word == payload.selected_word)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"사전에 없는 단어: {payload.selected_word}",
        )

    # 1:1 제약
    result = await db.execute(
        select(EmotionRecord).where(EmotionRecord.record_id == rec_uuid)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="이 기록에 이미 감정 단어가 선택되어 있습니다",
        )

    em = EmotionRecord(
        record_id=rec_uuid,
        selected_word=payload.selected_word,
        intensity=payload.intensity,
        exploration_path=payload.exploration_path,
    )
    db.add(em)
    await db.flush()
    await db.refresh(em)

    intervention = intervention_for(record.valence, record.arousal)

    return EmotionSelectResponse(
        emotion_id=str(em.emotion_id),
        record_id=str(em.record_id),
        selected_word=em.selected_word,
        intensity=em.intensity,
        exploration_path=em.exploration_path or [],
        final_at=em.final_at,
        intervention_type=intervention,
    )


@router.get("/dictionary/stats")
async def get_dictionary_stats(
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    """사전 통계 — 디버깅/감사용."""
    result = await db.execute(select(EmotionDictionary))
    words = result.scalars().all()
    quadrants = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
    for w in words:
        if w.valence >= 0 and w.arousal >= 0:
            quadrants["q1"] += 1
        elif w.valence < 0 and w.arousal >= 0:
            quadrants["q2"] += 1
        elif w.valence < 0 and w.arousal < 0:
            quadrants["q3"] += 1
        else:
            quadrants["q4"] += 1
    return {
        "total": len(words),
        "by_quadrant": quadrants,
        "reviewed_count": sum(1 for w in words if w.reviewed_by_researcher),
    }
