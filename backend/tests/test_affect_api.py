"""정동 기록 API 테스트 — 점 모드 / 궤도 모드 / 사분면 분류."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, UserStatus, RecordMode
from app.schemas.affect import compute_quadrant


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def authed_client():
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
        s.add(User(
            participant_code="P001", real_name="",
            device_id_hash=None, record_mode=RecordMode.POINT,
            status=UserStatus.ACTIVE,
        ))
        await s.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 로그인하여 JWT 획득
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


# --- compute_quadrant 단위 테스트 ---

def test_quadrant_q1_pleasant_high():
    assert compute_quadrant(0.5, 0.5) == "q1"
    assert compute_quadrant(0.0, 0.0) == "q1"  # 경계는 q1


def test_quadrant_q2_unpleasant_high():
    assert compute_quadrant(-0.3, 0.7) == "q2"


def test_quadrant_q3_unpleasant_low():
    assert compute_quadrant(-0.6, -0.4) == "q3"


def test_quadrant_q4_pleasant_low():
    assert compute_quadrant(0.4, -0.2) == "q4"


# --- API 통합 테스트 ---

@pytest.mark.asyncio
async def test_create_point_record(authed_client):
    r = await authed_client.post("/affect/record", json={
        "mode": "point",
        "valence": -0.4,
        "arousal": -0.2,
        "response_latency_ms": 3500,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["mode"] == "point"
    assert data["quadrant"] == "q3"
    assert data["valence"] == -0.4
    assert data["is_practice"] is False


@pytest.mark.asyncio
async def test_create_trajectory_record(authed_client):
    """궤도 모드 — 좌상단에서 우상단으로 이동."""
    r = await authed_client.post("/affect/record", json={
        "mode": "trajectory",
        "valence": 0.6,    # 끝점
        "arousal": 0.5,
        "trajectory_points": [
            {"v": -0.5, "a": 0.3, "t": 0},
            {"v": -0.2, "a": 0.5, "t": 200},
            {"v": 0.3, "a": 0.6, "t": 400},
            {"v": 0.6, "a": 0.5, "t": 600},
        ],
        "duration_window_minutes": 180,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["mode"] == "trajectory"
    assert data["quadrant"] == "q1"  # 끝점 기준


@pytest.mark.asyncio
async def test_trajectory_endpoint_mismatch_rejected(authed_client):
    """궤도 모드에서 valence/arousal이 끝점과 불일치하면 422."""
    r = await authed_client.post("/affect/record", json={
        "mode": "trajectory",
        "valence": 0.9,  # 끝점과 다름
        "arousal": 0.5,
        "trajectory_points": [
            {"v": 0.0, "a": 0.0, "t": 0},
            {"v": 0.6, "a": 0.5, "t": 100},
        ],
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_point_mode_with_trajectory_rejected(authed_client):
    r = await authed_client.post("/affect/record", json={
        "mode": "point",
        "valence": 0.2, "arousal": 0.1,
        "trajectory_points": [
            {"v": 0.0, "a": 0.0, "t": 0},
            {"v": 0.2, "a": 0.1, "t": 100},
        ],
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_valence_out_of_range_rejected(authed_client):
    r = await authed_client.post("/affect/record", json={
        "mode": "point",
        "valence": 1.5, "arousal": 0.0,
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_practice_session_saved(authed_client):
    """연습 세션 — is_practice=true로 저장, list 기본 조회에서 제외."""
    r = await authed_client.post("/affect/record", json={
        "mode": "point",
        "valence": 0.1, "arousal": 0.2,
        "is_practice": True,
    })
    assert r.status_code == 201
    assert r.json()["is_practice"] is True

    # 일반 조회 — 연습 세션은 제외
    r2 = await authed_client.get("/affect/records")
    assert r2.status_code == 200
    assert all(rec["is_practice"] is False for rec in r2.json())

    # include_practice=true 시 포함
    r3 = await authed_client.get("/affect/records?include_practice=true")
    assert any(rec["is_practice"] is True for rec in r3.json())


@pytest.mark.asyncio
async def test_update_record_mode(authed_client):
    r = await authed_client.post(
        "/affect/settings/record-mode",
        params={"mode": "trajectory"},
    )
    assert r.status_code == 200
    assert r.json()["record_mode"] == "trajectory"


@pytest.mark.asyncio
async def test_mark_practice_done(authed_client):
    r = await authed_client.post("/affect/settings/practice-done")
    assert r.status_code == 200
    assert r.json()["trajectory_practice_done"] is True


@pytest.mark.asyncio
async def test_unauthorized_without_device_header(authed_client):
    """X-Device-Id 없는 요청은 401."""
    del authed_client.headers["X-Device-Id"]
    r = await authed_client.post("/affect/record", json={
        "mode": "point", "valence": 0.0, "arousal": 0.0,
    })
    assert r.status_code == 401
