"""대시보드 API 테스트. 사양서 4.9."""
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.main import app
from app.models.emotion import EmotionDictionary
from app.models.user import User, UserStatus, RecordMode


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
DICT_PATH = Path(__file__).parent.parent / "data" / "emotion_dictionary_v0.json"


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

    dict_data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    async with SessionLocal() as s:
        s.add(User(participant_code="P001", real_name="",
                   device_id_hash=None, record_mode=RecordMode.POINT,
                   status=UserStatus.ACTIVE))
        for w in dict_data["words"]:
            s.add(EmotionDictionary(
                word=w["word"], definition=w["definition"], example=w["example"],
                valence=w["valence"], arousal=w["arousal"],
                neighbors=w["neighbors"], source=dict_data["version"],
            ))
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


@pytest.mark.asyncio
async def test_empty_dashboard(setup):
    """기록 없는 사용자 → 빈 배열, 응답률 0."""
    ac = setup
    r = await ac.get("/dashboard/me")
    assert r.status_code == 200
    d = r.json()
    assert d["summary"]["total_records"] == 0
    assert d["summary"]["response_rate"] == 0.0
    assert d["affect_points"] == []
    assert d["emotion_timeline"] == []


@pytest.mark.asyncio
async def test_dashboard_with_records(setup):
    """정동 기록 + 감정 선택 둘 다 있으면 결합되어 나옴."""
    ac = setup
    # 3개 기록 생성
    rids = []
    for v, a in [(-0.4, -0.2), (0.5, 0.5), (-0.3, 0.6)]:
        r = await ac.post("/affect/record", json={
            "mode": "point", "valence": v, "arousal": a,
        })
        rids.append(r.json()["record_id"])

    # 2개에만 감정 선택
    await ac.post("/emotion/select", json={
        "record_id": rids[0], "selected_word": "답답하다", "intensity": 3,
        "exploration_path": ["답답하다"],
    })
    await ac.post("/emotion/select", json={
        "record_id": rids[1], "selected_word": "설렌다", "intensity": 4,
        "exploration_path": ["설렌다"],
    })

    r = await ac.get("/dashboard/me")
    d = r.json()
    assert d["summary"]["total_records"] == 3
    assert d["summary"]["days_active"] == 1
    # affect_points는 3개 (감정 선택 안 한 것도 표시됨)
    assert len(d["affect_points"]) == 3
    # emotion_timeline은 2개 (감정 선택된 것만)
    assert len(d["emotion_timeline"]) == 2

    # 시간순 정렬 확인
    timestamps = [p["timestamp"] for p in d["affect_points"]]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_dashboard_overlay_data(setup):
    """겹쳐보기: affect_point에 emotion_word가 포함되는지."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]
    await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "답답하다", "intensity": 3,
        "exploration_path": ["답답하다"],
    })

    r = await ac.get("/dashboard/me")
    point = r.json()["affect_points"][0]
    assert point["emotion_word"] == "답답하다"
    assert point["intensity"] == 3


@pytest.mark.asyncio
async def test_dashboard_trajectory_mode(setup):
    """궤도 모드 기록은 trajectory_points 배열까지 반환."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "trajectory",
        "valence": 0.5,
        "arousal": 0.3,
        "trajectory_points": [
            {"v": -0.2, "a": -0.1, "t": 0},
            {"v": 0.1, "a": 0.2, "t": 200},
            {"v": 0.5, "a": 0.3, "t": 400},
        ],
    })
    rid = r.json()["record_id"]

    r = await ac.get("/dashboard/me")
    points = r.json()["affect_points"]
    assert len(points) == 1
    assert points[0]["mode"] == "trajectory"
    assert points[0]["trajectory_points"] is not None
    assert len(points[0]["trajectory_points"]) == 3


@pytest.mark.asyncio
async def test_dashboard_practice_excluded_by_default(setup):
    """is_practice=true 기록은 기본 대시보드에서 제외."""
    ac = setup
    await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.0, "arousal": 0.0,
        "is_practice": True,
    })
    await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })

    r = await ac.get("/dashboard/me")
    assert r.json()["summary"]["total_records"] == 1

    r2 = await ac.get("/dashboard/me?include_practice=true")
    assert r2.json()["summary"]["total_records"] == 2


@pytest.mark.asyncio
async def test_dashboard_response_rate_calc(setup):
    """응답률 = 기록수 / (days * 3)."""
    ac = setup
    # 1일 기간으로 3개 기록 → 100%
    for _ in range(3):
        await ac.post("/affect/record", json={
            "mode": "point", "valence": 0.0, "arousal": 0.0,
        })
    r = await ac.get("/dashboard/me?days=1")
    assert r.json()["summary"]["response_rate"] == 1.0


@pytest.mark.asyncio
async def test_dashboard_requires_auth(setup):
    ac = setup
    del ac.headers["X-Device-Id"]
    r = await ac.get("/dashboard/me")
    assert r.status_code == 401
