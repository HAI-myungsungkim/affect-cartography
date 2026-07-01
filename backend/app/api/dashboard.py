"""대시보드 라우터. 사양서 4.9.

사용자 자신의 누적 데이터만 반환 (다른 사용자 데이터 조회 불가).
"""
from datetime import datetime, timezone, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affect import AffectRecord
from app.models.emotion import EmotionRecord
from app.models.safety import SafetyFlag
from app.models.user import User
from app.schemas.dashboard import (
    AffectPointOut,
    DashboardData,
    DashboardSummary,
    EmotionTimelineItem,
    TrajectoryPointOut,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/me", response_model=DashboardData)
async def get_my_dashboard(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=28, ge=1, le=180, description="조회 기간 (일)"),
    include_practice: bool = Query(default=False),
):
    """본인 대시보드 데이터 통합 조회.

    - summary: 응답률 등 요약
    - affect_points: V-A grid에 표시할 점/궤도 (오래된 것부터 시간순)
    - emotion_timeline: 감정 단어 + 강도 시계열
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # 정동 기록 + 같은 record의 감정 기록을 JOIN 로딩하지 않고
    # 두 번 쿼리해서 in-memory로 결합 (테이블 작아서 간단함)
    stmt = (
        select(AffectRecord)
        .where(
            AffectRecord.user_id == current_user.user_id,
            AffectRecord.timestamp >= since,
        )
        .order_by(AffectRecord.timestamp.asc())
    )
    if not include_practice:
        stmt = stmt.where(AffectRecord.is_practice.is_(False))
    result = await db.execute(stmt)
    affects = list(result.scalars().all())

    # record_id → emotion lookup
    if affects:
        rec_ids = [a.record_id for a in affects]
        result = await db.execute(
            select(EmotionRecord).where(EmotionRecord.record_id.in_(rec_ids))
        )
        emotions = {e.record_id: e for e in result.scalars().all()}
    else:
        emotions = {}

    # affect_points 구성 (겹쳐보기용으로 emotion 정보 결합)
    affect_points: list[AffectPointOut] = []
    emotion_timeline: list[EmotionTimelineItem] = []
    for a in affects:
        em = emotions.get(a.record_id)
        affect_points.append(AffectPointOut(
            record_id=str(a.record_id),
            timestamp=a.timestamp,
            valence=a.valence,
            arousal=a.arousal,
            quadrant=a.quadrant.value,
            mode=a.mode.value,
            trajectory_points=(
                [TrajectoryPointOut(**p) for p in a.trajectory_points]
                if a.trajectory_points else None
            ),
            emotion_word=em.selected_word if em else None,
            intensity=em.intensity if em else None,
        ))
        if em:
            emotion_timeline.append(EmotionTimelineItem(
                record_id=str(a.record_id),
                timestamp=a.timestamp,
                word=em.selected_word,
                intensity=em.intensity,
                valence=a.valence,
                arousal=a.arousal,
                quadrant=a.quadrant.value,
            ))

    # summary 계산
    # 응답률: 사용자가 응답한 기록 수 / (28일 × 3회 = 84). 운영에서는 실제 발송 알림 수 기준.
    expected_total = days * 3
    response_rate = min(1.0, len(affects) / expected_total) if expected_total > 0 else 0.0
    days_active = len({a.timestamp.date() for a in affects})

    result = await db.execute(
        select(func.count(SafetyFlag.flag_id)).where(
            SafetyFlag.user_id == current_user.user_id,
            SafetyFlag.raised_at >= since,
        )
    )
    flag_count = int(result.scalar_one() or 0)

    summary = DashboardSummary(
        total_records=len(affects),
        response_rate=round(response_rate, 3),
        days_active=days_active,
        safety_flag_count=flag_count,
    )

    return DashboardData(
        summary=summary,
        affect_points=affect_points,
        emotion_timeline=emotion_timeline,
    )
