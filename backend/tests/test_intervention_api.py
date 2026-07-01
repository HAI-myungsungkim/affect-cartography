"""분기 개입 API 테스트. 사양서 4.8."""
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
from app.services.intervention_prompts import build_intervention_prompt


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


# --- 프롬프트 빌더 단위 테스트 ---

def test_self_distancing_prompt_includes_name():
    p = build_intervention_prompt("self_distancing", "철수")
    assert "철수" in p["body"]
    assert "한 걸음 떨어져" in p["title"]
    assert "친구에게" in p["body"]


def test_grounding_prompt_includes_breathing():
    p = build_intervention_prompt("grounding", "영희")
    assert "호흡" in p["body"]
    assert "5분 뒤" in p["body"]
    assert "영희" in p["body"]


def test_activation_prompt_is_if_then():
    p = build_intervention_prompt("activation", "민수")
    assert "만약" in p["body"]
    assert "[상황]" in p["body"] or "구체적 행동" in p["body"]


def test_prompt_handles_empty_name():
    p = build_intervention_prompt("self_distancing", "")
    assert "당신" in p["body"]  # 기본값 fallback


# --- API 통합 ---

@pytest.mark.asyncio
async def test_get_prompt_q3_self_distancing(setup):
    """Q3 좌표 → self_distancing 프롬프트, 실명 포함."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]
    r = await ac.get("/intervention/prompt", params={"record_id": rid})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["intervention_type"] == "self_distancing"
    assert "테스터" in data["body"]
    assert data["allow_skip"] is True


@pytest.mark.asyncio
async def test_get_prompt_q2_grounding(setup):
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.5, "arousal": 0.6,
    })
    rid = r.json()["record_id"]
    r = await ac.get("/intervention/prompt", params={"record_id": rid})
    data = r.json()
    assert data["intervention_type"] == "grounding"
    assert "호흡" in data["body"]


@pytest.mark.asyncio
async def test_get_prompt_q1_activation(setup):
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.5, "arousal": 0.5,
    })
    rid = r.json()["record_id"]
    r = await ac.get("/intervention/prompt", params={"record_id": rid})
    data = r.json()
    assert data["intervention_type"] == "activation"
    assert "만약" in data["body"]


@pytest.mark.asyncio
async def test_save_response_with_text(setup):
    """사용자가 텍스트로 응답."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/intervention/response", json={
        "record_id": rid,
        "intervention_type": "self_distancing",
        "user_response_text": "친구에게 설명한다면 '많이 지쳤구나'라고 할 것 같다",
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["intervention_type"] == "self_distancing"
    assert "친구에게" in data["user_response_text"]


@pytest.mark.asyncio
async def test_save_response_text_optional(setup):
    """'읽었어요'/건너뛰기 — user_response_text 없이도 저장."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/intervention/response", json={
        "record_id": rid, "intervention_type": "self_distancing",
    })
    assert r.status_code == 201
    assert r.json()["user_response_text"] is None


@pytest.mark.asyncio
async def test_mismatched_type_rejected(setup):
    """Q3 좌표인데 activation을 보내면 400."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/intervention/response", json={
        "record_id": rid, "intervention_type": "activation",
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_double_response_rejected(setup):
    """같은 record_id 두 번째 저장 → 409."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": -0.4, "arousal": -0.2,
    })
    rid = r.json()["record_id"]

    r1 = await ac.post("/intervention/response", json={
        "record_id": rid, "intervention_type": "self_distancing",
        "user_response_text": "첫 응답",
    })
    assert r1.status_code == 201

    r2 = await ac.post("/intervention/response", json={
        "record_id": rid, "intervention_type": "self_distancing",
        "user_response_text": "두 번째 시도",
    })
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_invalid_intervention_type_422(setup):
    """잘못된 enum → Pydantic 422."""
    ac = setup
    r = await ac.post("/affect/record", json={
        "mode": "point", "valence": 0.5, "arousal": 0.5,
    })
    rid = r.json()["record_id"]
    r = await ac.post("/intervention/response", json={
        "record_id": rid, "intervention_type": "magic_intervention",
    })
    assert r.status_code == 422
