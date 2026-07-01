"""알림 발송 스케줄 생성 — 사양서 8항.

각 시간대(09-12, 13-17, 19-22 등)에서 무작위 한 시점을 선택해 발송 일정 생성.
사용자별 + 날짜별로 결정적(deterministic)인 시드를 사용해 재요청해도 같은 결과.
"""
from __future__ import annotations

import hashlib
import random
import uuid
from datetime import date, datetime, time, timezone, timedelta
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")


def _user_date_seed(user_id: str, d: date) -> int:
    """사용자 ID + 날짜 → 결정적 시드."""
    key = f"{user_id}:{d.isoformat()}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:12], 16)


def random_time_in_window(
    window_start: time,
    window_end: time,
    seed: int,
) -> time:
    """[start, end) 범위 내 무작위 시각. seed로 결정적."""
    rng = random.Random(seed)
    start_minutes = window_start.hour * 60 + window_start.minute
    end_minutes = window_end.hour * 60 + window_end.minute
    if end_minutes <= start_minutes:
        return window_start
    chosen = rng.randrange(start_minutes, end_minutes)
    return time(chosen // 60, chosen % 60)


def build_daily_schedule(
    user_id: str,
    target_date: date,
    morning_start: time,
    morning_end: time,
    afternoon_start: time,
    afternoon_end: time,
    evening_start: time,
    evening_end: time,
    tz: ZoneInfo = KST,
) -> list[dict]:
    """하루치 3건 알림 발송 스케줄 생성.
    
    반환: [{prompt_id, window, scheduled_at(UTC datetime)}, ...]
    """
    base_seed = _user_date_seed(user_id, target_date)
    schedule = []

    for idx, (window_name, ws, we) in enumerate([
        ("morning", morning_start, morning_end),
        ("afternoon", afternoon_start, afternoon_end),
        ("evening", evening_start, evening_end),
    ]):
        t = random_time_in_window(ws, we, base_seed + idx)
        # 사용자 로컬(KST) 기준 datetime → UTC 변환
        local_dt = datetime.combine(target_date, t, tzinfo=tz)
        utc_dt = local_dt.astimezone(timezone.utc)

        # prompt_id: 결정적이지만 사용자 + 날짜 + 윈도우로 고유
        pid_seed = f"{user_id}:{target_date.isoformat()}:{window_name}"
        prompt_id = str(uuid.uuid5(uuid.NAMESPACE_OID, pid_seed))

        schedule.append({
            "prompt_id": prompt_id,
            "window": window_name,
            "scheduled_at": utc_dt,
        })

    return schedule
