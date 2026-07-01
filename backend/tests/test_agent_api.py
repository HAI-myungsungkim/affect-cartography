"""에이전트 대화 API 통합 테스트.

핵심 검증:
  - 첫 턴 (사용자 메시지 없이) → LLM이 시작 메시지 생성
  - 일반 사용자 메시지 → 사용자/에이전트 메시지 모두 DB 저장
  - 위기 키워드 입력 → safety_flag 발급 + 표준 응답 + is_final=True
  - LLM이 위기 표현 출력 → 안전망으로 차단
  - 최대 4턴
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.main import app
from app.models.affect import AffectRecord
from app.models.dialogue import AgentDialogue
from app.models.safety import SafetyFlag, FlagType
from app.models.user import User, UserStatus, RecordMode
from app.services.llm_client import MockLLMClient, set_llm_client


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

    mock = MockLLMClient([
        "지금 몸에서 어떤 느낌이 가장 먼저 느껴지나요?",
        "그렇게 느끼는 데에는 그럴 만한 이유가 있을 것 같아요.",
        "그 느낌을 어떤 단어로 부르고 싶으신가요?",
        "잘 들어주셔서 고마워요.",
    ])
    set_llm_client(mock)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "테스터",
            "device_id": "device-test-001",
        })
        token = r.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        ac.headers["X-Device-Id"] = "device-test-001"

        # 정동 기록 미리 생성 (Q3 좌하단)
        r = await ac.post("/affect/record", json={
            "mode": "point", "valence": -0.4, "arousal": -0.2,
        })
        record_id = r.json()["record_id"]

        yield ac, record_id, SessionLocal, mock

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_first_turn_without_user_message(setup):
    """첫 턴 — 사용자 메시지 없이 호출 → 에이전트가 시작."""
    ac, record_id, _, mock = setup
    r = await ac.post("/agent/dialogue/turn", json={"record_id": record_id})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["turn_index"] == 0
    assert data["agent_message"]  # 비어있지 않음
    assert data["is_final"] is False
    assert data["safety_flag_raised"] is False
    # LLM이 정확히 1번 호출됨
    assert len(mock.calls) == 1


@pytest.mark.asyncio
async def test_user_message_triggers_llm(setup):
    """사용자 메시지 → LLM 호출 → 응답 저장."""
    ac, record_id, SessionLocal, mock = setup
    # 첫 턴
    await ac.post("/agent/dialogue/turn", json={"record_id": record_id})
    # 두 번째 턴 (사용자 응답)
    r = await ac.post("/agent/dialogue/turn", json={
        "record_id": record_id,
        "user_message": "가슴이 좀 무거운 느낌이에요",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["agent_message"]
    assert data["safety_flag_raised"] is False

    # DB에 4개 메시지 (agent, user, user-message, agent-response)
    async with SessionLocal() as s:
        result = await s.execute(select(AgentDialogue))
        rows = result.scalars().all()
        speakers = [r.speaker.value for r in rows]
        # 첫 턴 agent + 두 번째 사용자 + 두 번째 agent = 최소 3개
        assert speakers.count("agent") >= 2
        assert speakers.count("user") >= 1


@pytest.mark.asyncio
async def test_crisis_keyword_immediate_block(setup):
    """위기 키워드 → safety_flag 발급 + 표준 응답 + is_final=True. LLM 호출되지 않아야 함."""
    ac, record_id, SessionLocal, mock = setup
    initial_calls = len(mock.calls)

    r = await ac.post("/agent/dialogue/turn", json={
        "record_id": record_id,
        "user_message": "자살하고 싶어요",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["safety_flag_raised"] is True
    assert data["crisis_flag_type"] == "suicide_ideation"
    assert data["is_final"] is True
    # 표준 응답 — 1393 포함
    assert "1393" in data["agent_message"]

    # LLM 호출되지 않음 (위기 시 즉시 차단)
    assert len(mock.calls) == initial_calls

    # safety_flag DB에 기록됨
    async with SessionLocal() as s:
        result = await s.execute(select(SafetyFlag))
        flags = result.scalars().all()
        assert len(flags) == 1
        assert flags[0].flag_type == FlagType.SUICIDE_IDEATION
        assert flags[0].matched_keywords  # 매칭 키워드 보존


@pytest.mark.asyncio
async def test_self_harm_detected(setup):
    ac, record_id, _, _ = setup
    r = await ac.post("/agent/dialogue/turn", json={
        "record_id": record_id,
        "user_message": "그냥 자해를 했어요",
    })
    assert r.status_code == 200
    assert r.json()["crisis_flag_type"] == "self_harm"
    assert "1393" in r.json()["agent_message"]


@pytest.mark.asyncio
async def test_llm_output_with_crisis_keyword_replaced(setup):
    """LLM이 위기 표현을 생성하더라도 안전망으로 차단되어 표준 응답으로 교체."""
    ac, record_id, SessionLocal, _ = setup
    # LLM이 위험한 응답을 내도록 mock 교체
    set_llm_client(MockLLMClient(["당신은 자살하고 싶은 거군요"]))

    r = await ac.post("/agent/dialogue/turn", json={"record_id": record_id})
    assert r.status_code == 200
    data = r.json()
    # LLM 출력이 그대로 사용자에게 가지 않음 — 표준 응답으로 교체
    assert "1393" in data["agent_message"]
    # LLM 출력 안전망에 의해 safety_flag도 발급됨
    async with SessionLocal() as s:
        result = await s.execute(select(SafetyFlag))
        flags = result.scalars().all()
        assert len(flags) >= 1


@pytest.mark.asyncio
async def test_max_turns_marks_final(setup):
    """4턴 도달 시 is_final=True."""
    ac, record_id, _, _ = setup
    # 4개 에이전트 응답을 받을 때까지 반복
    for i in range(4):
        r = await ac.post("/agent/dialogue/turn", json={
            "record_id": record_id,
            "user_message": f"메시지 {i}" if i > 0 else None,
        })
        data = r.json()
    assert data["is_final"] is True


@pytest.mark.asyncio
async def test_dialogue_history(setup):
    """대화 이력 조회."""
    ac, record_id, _, _ = setup
    await ac.post("/agent/dialogue/turn", json={"record_id": record_id})
    await ac.post("/agent/dialogue/turn", json={
        "record_id": record_id, "user_message": "조금 답답해요",
    })

    r = await ac.get(f"/agent/dialogue/{record_id}")
    assert r.status_code == 200
    data = r.json()
    assert len(data["turns"]) >= 3  # agent + user + agent
    assert data["turns"][0]["turn_index"] == 0


@pytest.mark.asyncio
async def test_other_users_record_forbidden(setup):
    """다른 사용자의 record_id로 대화 시도 → 404."""
    ac, _, _, _ = setup
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = await ac.post("/agent/dialogue/turn", json={
        "record_id": fake_id, "user_message": "안녕",
    })
    assert r.status_code == 404
