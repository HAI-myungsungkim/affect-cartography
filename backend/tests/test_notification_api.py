"""알림 API 테스트. 사양서 8항."""
from datetime import date, time

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, UserStatus, RecordMode
from app.services.notification_scheduler import (
    build_daily_schedule,
    random_time_in_window,
)


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def setup():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    async with SessionLocal() as s:
        s.add(User(participant_code="P001", real_name="",
                   device_id_hash=None, record_mode=RecordMode.POINT,
                   status=UserStatus.ACTIVE))
        await s.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "테스터",
            "device_id": "device-test-001",
        })
        token = r.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        ac.headers["X-Device-Id"] = "device-test-001"
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


# --- 스케줄러 단위 테스트 ---

def test_random_time_in_window_within_range():
    """무작위 시각이 항상 윈도우 내."""
    for seed in range(50):
        t = random_time_in_window(time(9, 0), time(12, 0), seed)
        assert time(9, 0) <= t < time(12, 0)


def test_random_time_deterministic():
    """같은 seed → 같은 결과."""
    t1 = random_time_in_window(time(9, 0), time(12, 0), 42)
    t2 = random_time_in_window(time(9, 0), time(12, 0), 42)
    assert t1 == t2


def test_random_time_different_seeds():
    """다른 seed → 충분히 분산."""
    results = {random_time_in_window(time(9, 0), time(12, 0), s) for s in range(20)}
    assert len(results) > 5  # 최소 25% 분산


def test_daily_schedule_creates_three_prompts():
    """하루 3개의 알림."""
    s = build_daily_schedule(
        user_id="user-1",
        target_date=date(2026, 6, 30),
        morning_start=time(9, 0), morning_end=time(12, 0),
        afternoon_start=time(13, 0), afternoon_end=time(17, 0),
        evening_start=time(19, 0), evening_end=time(22, 0),
    )
    assert len(s) == 3
    windows = {p["window"] for p in s}
    assert windows == {"morning", "afternoon", "evening"}


def test_daily_schedule_deterministic():
    """같은 사용자 + 같은 날짜 → 같은 prompt_id."""
    args = dict(
        user_id="user-1", target_date=date(2026, 6, 30),
        morning_start=time(9, 0), morning_end=time(12, 0),
        afternoon_start=time(13, 0), afternoon_end=time(17, 0),
        evening_start=time(19, 0), evening_end=time(22, 0),
    )
    s1 = build_daily_schedule(**args)
    s2 = build_daily_schedule(**args)
    assert [p["prompt_id"] for p in s1] == [p["prompt_id"] for p in s2]


def test_daily_schedule_different_users():
    """다른 사용자 → 다른 prompt_id."""
    args = dict(
        target_date=date(2026, 6, 30),
        morning_start=time(9, 0), morning_end=time(12, 0),
        afternoon_start=time(13, 0), afternoon_end=time(17, 0),
        evening_start=time(19, 0), evening_end=time(22, 0),
    )
    s1 = build_daily_schedule(user_id="user-1", **args)
    s2 = build_daily_schedule(user_id="user-2", **args)
    assert s1[0]["prompt_id"] != s2[0]["prompt_id"]


# --- API ---

@pytest.mark.asyncio
async def test_get_default_settings(setup):
    """기본 시간대 3구간 (09-12, 13-17, 19-22)."""
    ac = setup
    r = await ac.get("/notification/settings")
    assert r.status_code == 200
    d = r.json()
    assert d["morning"]["start"] == "09:00"
    assert d["morning"]["end"] == "12:00"
    assert d["afternoon"]["start"] == "13:00"
    assert d["afternoon"]["end"] == "17:00"
    assert d["evening"]["start"] == "19:00"
    assert d["evening"]["end"] == "22:00"


@pytest.mark.asyncio
async def test_update_morning_only(setup):
    """일부 윈도우만 업데이트."""
    ac = setup
    r = await ac.put("/notification/settings", json={
        "morning": {"start": "08:00", "end": "11:00"}
    })
    assert r.status_code == 200
    d = r.json()
    assert d["morning"]["start"] == "08:00"
    assert d["morning"]["end"] == "11:00"
    # 다른 윈도우는 그대로
    assert d["afternoon"]["start"] == "13:00"


@pytest.mark.asyncio
async def test_invalid_time_format_rejected(setup):
    ac = setup
    r = await ac.put("/notification/settings", json={
        "morning": {"start": "25:00", "end": "11:00"}  # 25시는 없음
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_end_before_start_rejected(setup):
    ac = setup
    r = await ac.put("/notification/settings", json={
        "morning": {"start": "12:00", "end": "09:00"}
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_get_today_schedule_3_prompts(setup):
    """오늘 스케줄 → 3개 prompt."""
    ac = setup
    r = await ac.get("/notification/today")
    assert r.status_code == 200
    d = r.json()
    assert len(d["prompts"]) == 3
    windows = [p["window"] for p in d["prompts"]]
    assert windows == ["morning", "afternoon", "evening"]
    # prompt_id가 모두 유효한 UUID 형태
    for p in d["prompts"]:
        assert len(p["prompt_id"]) == 36  # uuid 길이


@pytest.mark.asyncio
async def test_today_schedule_deterministic_repeat(setup):
    """같은 사용자가 두 번 호출해도 같은 prompt_id."""
    ac = setup
    r1 = await ac.get("/notification/today")
    r2 = await ac.get("/notification/today")
    ids1 = [p["prompt_id"] for p in r1.json()["prompts"]]
    ids2 = [p["prompt_id"] for p in r2.json()["prompts"]]
    assert ids1 == ids2


@pytest.mark.asyncio
async def test_response_rate_distinguishes_notif_vs_spontaneous(setup):
    """prompt_id 있는 기록 = 알림 응답, 없는 기록 = 자발 기록."""
    ac = setup
    # 알림 응답
    await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.0, "arousal": 0.0,
        "prompt_id": "morning-prompt-abc",
    })
    # 자발 기록
    await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.1, "arousal": 0.1,
    })

    r = await ac.get("/notification/response-rate?days=1")
    d = r.json()
    assert d["notification_responses"] == 1
    assert d["spontaneous_responses"] == 1
    assert d["total_responses"] == 2


@pytest.mark.asyncio
async def test_notification_requires_auth(setup):
    ac = setup
    del ac.headers["X-Device-Id"]
    r = await ac.get("/notification/today")
    assert r.status_code == 401
