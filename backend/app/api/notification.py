"""알림 라우터. 사양서 8항.

설계:
  - 시간대 3구간 구조는 고정 (morning/afternoon/evening), 구간 내 시각만 사용자 조정 가능.
  - 백엔드는 "스케줄 생성"만 담당. 실제 발송은:
      a) 단기: Flutter가 GET /notification/today로 일정 가져와 flutter_local_notifications에 등록
      b) 장기: FCM/APNs 푸시 (디바이스 토큰 등록 후 — 9단계 끝에서 사용자 액션 필요)
  - prompt_id가 정동 기록의 prompt_id에 들어가 응답률 계산 기준이 됨.
"""
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affect import AffectRecord
from app.models.user import User
from app.schemas.notification import (
    NotificationSettings,
    NotificationSettingsUpdate,
    ScheduledPrompt,
    TimeWindow,
    TodaySchedule,
)
from app.services.notification_scheduler import build_daily_schedule

router = APIRouter(prefix="/notification", tags=["notification"])


def _time_to_str(t) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


@router.get("/settings", response_model=NotificationSettings)
async def get_settings(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """현재 사용자의 알림 시간대 3구간 설정 조회."""
    return NotificationSettings(
        morning=TimeWindow(
            start=_time_to_str(current_user.notify_morning_start),
            end=_time_to_str(current_user.notify_morning_end),
        ),
        afternoon=TimeWindow(
            start=_time_to_str(current_user.notify_afternoon_start),
            end=_time_to_str(current_user.notify_afternoon_end),
        ),
        evening=TimeWindow(
            start=_time_to_str(current_user.notify_evening_start),
            end=_time_to_str(current_user.notify_evening_end),
        ),
    )


@router.put("/settings", response_model=NotificationSettings)
async def update_settings(
    payload: NotificationSettingsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """사용자 시간대 조정. 사양서 8항: 시간대 3구간 구조는 변경 불가, 시각만 가능."""
    if payload.morning:
        s, e = payload.morning.to_time_range()
        if e <= s:
            raise HTTPException(status_code=400, detail="morning end는 start보다 뒤여야 합니다")
        current_user.notify_morning_start = s
        current_user.notify_morning_end = e
    if payload.afternoon:
        s, e = payload.afternoon.to_time_range()
        if e <= s:
            raise HTTPException(status_code=400, detail="afternoon end는 start보다 뒤여야 합니다")
        current_user.notify_afternoon_start = s
        current_user.notify_afternoon_end = e
    if payload.evening:
        s, e = payload.evening.to_time_range()
        if e <= s:
            raise HTTPException(status_code=400, detail="evening end는 start보다 뒤여야 합니다")
        current_user.notify_evening_start = s
        current_user.notify_evening_end = e

    await db.flush()

    return await get_settings(current_user)


@router.get("/today", response_model=TodaySchedule)
async def get_today_schedule(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """오늘의 발송 스케줄 — Flutter가 가져가서 로컬 알림 등록.
    
    같은 사용자/같은 날짜에 여러 번 호출해도 결정적으로 같은 prompt_id 반환.
    """
    today = datetime.now(timezone.utc).date()
    schedule = build_daily_schedule(
        user_id=str(current_user.user_id),
        target_date=today,
        morning_start=current_user.notify_morning_start,
        morning_end=current_user.notify_morning_end,
        afternoon_start=current_user.notify_afternoon_start,
        afternoon_end=current_user.notify_afternoon_end,
        evening_start=current_user.notify_evening_start,
        evening_end=current_user.notify_evening_end,
    )
    return TodaySchedule(
        user_id=str(current_user.user_id),
        date=today.isoformat(),
        prompts=[ScheduledPrompt(**p) for p in schedule],
    )


@router.get("/response-rate")
async def get_response_rate(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    days: int = 28,
):
    """응답률 계산. 사양서 8항: (응답 완료 기록 수) / (발송된 알림 수).
    
    파일럿 단순화: 발송된 알림 수 = days × 3 (가입 시점 이후 일수 제한 가능)
    """
    since = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).replace(tzinfo=timezone.utc)
    from datetime import timedelta
    since = since - timedelta(days=days)

    result = await db.execute(
        select(AffectRecord).where(
            AffectRecord.user_id == current_user.user_id,
            AffectRecord.timestamp >= since,
            AffectRecord.is_practice.is_(False),
        )
    )
    responses = list(result.scalars().all())
    # 알림 응답 (prompt_id가 있는 기록) vs 자발 기록 구분
    notif_responses = [r for r in responses if r.prompt_id]
    expected = days * 3

    return {
        "expected_prompts": expected,
        "total_responses": len(responses),
        "notification_responses": len(notif_responses),
        "spontaneous_responses": len(responses) - len(notif_responses),
        "response_rate": round(min(1.0, len(notif_responses) / expected), 3) if expected else 0.0,
        "days": days,
    }
