"""감정 단어 사전 API 테스트."""
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
async def authed_client_with_dict():
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

    # 사용자 + 사전 시드
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


# --- 사전 데이터 자체 검증 ---

def test_dictionary_json_loads():
    """JSON 파일 자체가 유효한지."""
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    assert len(data["words"]) >= 24
    assert "version" in data


def test_all_neighbors_exist_in_dictionary():
    """모든 neighbor 단어가 사전에 존재 — 5단계 에이전트 안전성."""
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    word_set = {w["word"] for w in data["words"]}
    for w in data["words"]:
        for n in w["neighbors"]:
            assert n["word"] in word_set, (
                f"{w['word']}의 neighbor '{n['word']}'가 사전에 없음"
            )


def test_quadrant_balance():
    """각 사분면 최소 5개 단어."""
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    counts = {"q1": 0, "q2": 0, "q3": 0, "q4": 0}
    for w in data["words"]:
        v, a = w["valence"], w["arousal"]
        if v >= 0 and a >= 0:
            counts["q1"] += 1
        elif v < 0 and a >= 0:
            counts["q2"] += 1
        elif v < 0 and a < 0:
            counts["q3"] += 1
        else:
            counts["q4"] += 1
    for q, c in counts.items():
        assert c >= 5, f"{q}: {c}개 (최소 5개 필요)"


# --- API 통합 테스트 ---

@pytest.mark.asyncio
async def test_get_candidates_near_q3(authed_client_with_dict):
    """좌하단(불쾌-저각성) 좌표 → 답답하다/막막하다 등이 후보로 나옴."""
    r = await authed_client_with_dict.get(
        "/emotion/candidates", params={"valence": -0.4, "arousal": -0.2, "limit": 5}
    )
    assert r.status_code == 200, r.text
    candidates = r.json()["candidates"]
    assert len(candidates) == 5
    candidate_words = [c["word"] for c in candidates]
    # Q3 단어 중 적어도 하나는 포함
    q3_words = {"답답하다", "막막하다", "지친다", "외롭다", "슬프다", "우울하다", "무력하다"}
    assert any(w in q3_words for w in candidate_words), (
        f"Q3 단어가 후보에 없음: {candidate_words}"
    )


@pytest.mark.asyncio
async def test_get_candidates_near_q1(authed_client_with_dict):
    """우상단(유쾌-고각성) → 신난다/설렌다 등."""
    r = await authed_client_with_dict.get(
        "/emotion/candidates", params={"valence": 0.6, "arousal": 0.6}
    )
    assert r.status_code == 200
    words = [c["word"] for c in r.json()["candidates"]]
    q1_words = {"신난다", "설렌다", "벅차다", "들뜬다", "두근거린다", "감격스럽다"}
    assert any(w in q1_words for w in words)


@pytest.mark.asyncio
async def test_get_neighbors_of_답답하다(authed_client_with_dict):
    """'답답하다'의 인접 단어 4개가 모두 사전에 존재."""
    r = await authed_client_with_dict.get(
        "/emotion/neighbors", params={"word": "답답하다"}
    )
    assert r.status_code == 200
    data = r.json()
    assert data["center"]["word"] == "답답하다"
    assert len(data["neighbors"]) == 4
    for n in data["neighbors"]:
        # 각 인접 단어는 정의·예시·valence·arousal을 모두 가짐
        assert n["definition"]
        assert n["example"]
        assert -1.0 <= n["valence"] <= 1.0


@pytest.mark.asyncio
async def test_get_neighbors_unknown_word(authed_client_with_dict):
    r = await authed_client_with_dict.get(
        "/emotion/neighbors", params={"word": "존재하지않는단어"}
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_dictionary_stats(authed_client_with_dict):
    r = await authed_client_with_dict.get("/emotion/dictionary/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 24
    assert sum(data["by_quadrant"].values()) == data["total"]


@pytest.mark.asyncio
async def test_candidates_requires_auth(authed_client_with_dict):
    del authed_client_with_dict.headers["X-Device-Id"]
    r = await authed_client_with_dict.get(
        "/emotion/candidates", params={"valence": 0.0, "arousal": 0.0}
    )
    assert r.status_code == 401
