"""감정 단어 선택 API 테스트 — POST /emotion/select."""
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.api.emotion import intervention_for
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
        s.add(User(participant_code="P001", real_name="", device_id_hash=None,
                   record_mode=RecordMode.POINT, status=UserStatus.ACTIVE))
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


# --- 분기 개입 로직 단위 테스트 (사양서 4.8) ---

def test_intervention_grounding_for_q2():
    """좌상단 (불쾌-고각성) → 그라운딩."""
    assert intervention_for(-0.5, 0.6) == "grounding"
    assert intervention_for(-0.1, 0.1) == "grounding"


def test_intervention_self_distancing_for_q3():
    """좌하단 (불쾌-저각성) → 자기거리두기."""
    assert intervention_for(-0.4, -0.2) == "self_distancing"
    assert intervention_for(-0.8, -0.6) == "self_distancing"


def test_intervention_activation_for_q1_q4():
    """우측 (유쾌) → 행동활성화."""
    assert intervention_for(0.5, 0.5) == "activation"
    assert intervention_for(0.3, -0.4) == "activation"
    assert intervention_for(0.0, 0.0) == "activation"  # 중립도 activation


# --- API 통합 테스트 ---

@pytest.mark.asyncio
async def test_select_emotion_q3(setup):
    """Q3 좌표 → '답답하다' 선택 → 자기거리두기 개입 반환."""
    ac = setup
    # 정동 기록
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    record_id = r.json()["record_id"]

    # 단어 선택
    r = await ac.post("/emotion/select", json={
        "record_id": record_id,
        "selected_word": "답답하다",
        "intensity": 3,
        "exploration_path": ["답답하다"],
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["selected_word"] == "답답하다"
    assert data["intensity"] == 3
    assert data["intervention_type"] == "self_distancing"  # Q3 -> 자기거리두기


@pytest.mark.asyncio
async def test_select_emotion_q2_grounding(setup):
    """Q2 좌상단 → 그라운딩."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.5, "arousal": 0.6,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "긴장된다", "intensity": 4,
        "exploration_path": ["초조하다", "긴장된다"],
    })
    assert r.status_code == 201
    assert r.json()["intervention_type"] == "grounding"


@pytest.mark.asyncio
async def test_select_emotion_q1_activation(setup):
    """Q1 우상단 → 행동활성화."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.6, "arousal": 0.5,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "설렌다", "intensity": 4,
        "exploration_path": ["설렌다"],
    })
    assert r.status_code == 201
    assert r.json()["intervention_type"] == "activation"


@pytest.mark.asyncio
async def test_select_word_not_in_dictionary_rejected(setup):
    """사전에 없는 단어는 400."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.0, "arousal": 0.0,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "이상한단어", "intensity": 3,
    })
    assert r.status_code == 400
    assert "사전에 없는" in r.json()["detail"]


@pytest.mark.asyncio
async def test_intensity_out_of_range(setup):
    """강도는 1~5만 허용."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.0, "arousal": 0.0,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "차분하다", "intensity": 6,
    })
    assert r.status_code == 422  # Pydantic validation


@pytest.mark.asyncio
async def test_double_select_rejected(setup):
    """같은 record_id에 두 번 선택하면 409."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]

    r1 = await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "답답하다", "intensity": 3,
    })
    assert r1.status_code == 201

    r2 = await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "막막하다", "intensity": 4,
    })
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_exploration_path_preserved(setup):
    """사용자가 거쳐온 단어 경로가 그대로 저장."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]
    path = ["답답하다", "막막하다", "지친다", "무력하다"]
    r = await ac.post("/emotion/select", json={
        "record_id": rid, "selected_word": "무력하다", "intensity": 5,
        "exploration_path": path,
    })
    assert r.status_code == 201
    assert r.json()["exploration_path"] == path


@pytest.mark.asyncio
async def test_select_others_record_forbidden(setup):
    """다른 사용자의 record_id 접근 → 404."""
    ac = setup
    fake = "00000000-0000-0000-0000-000000000000"
    r = await ac.post("/emotion/select", json={
        "record_id": fake, "selected_word": "차분하다", "intensity": 3,
    })
    assert r.status_code == 404
