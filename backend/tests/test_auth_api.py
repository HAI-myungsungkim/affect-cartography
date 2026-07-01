"""인증 API 통합 테스트 — SQLite 인메모리로 빠르게 검증.

엄격 디바이스 바인딩 정책 검증 (사양서 4.1):
1. 첫 로그인 → 디바이스 바인딩 성공
2. 같은 기기 재진입 → 성공
3. 다른 기기 진입 → 401 device_mismatch
4. 미등록 코드 → 401 code_not_registered
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.main import app
from app.models.user import User, UserStatus, RecordMode


# SQLite 인메모리 — 빠른 테스트용 (Postgres-specific 타입은 SQLAlchemy가 호환 처리)
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session():
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
    # 시드: P001 코드 등록
    async with SessionLocal() as s:
        s.add(User(
            participant_code="P001",
            real_name="",
            device_id_hash=None,
            record_mode=RecordMode.POINT,
            status=UserStatus.ACTIVE,
        ))
        await s.commit()
    yield
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_first_login_binds_device(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P001",
            "real_name": "김철수",
            "device_id": "device-aaa-111",
        })
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["first_login"] is True
        assert data["real_name"] == "김철수"
        assert "access_token" in data


@pytest.mark.asyncio
async def test_same_device_relogin_ok(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "device-aaa-111",
        })
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "device-aaa-111",
        })
        assert r.status_code == 200
        assert r.json()["first_login"] is False


@pytest.mark.asyncio
async def test_different_device_blocked(db_session):
    """엄격 바인딩 정책 핵심 검증."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "device-aaa-111",
        })
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "device-bbb-222",
        })
        assert r.status_code == 401
        detail = r.json()["detail"]
        assert detail["code"] == "device_mismatch"


@pytest.mark.asyncio
async def test_unregistered_code(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P999", "real_name": "김철수",
            "device_id": "device-aaa-111",
        })
        assert r.status_code == 401
        assert r.json()["detail"]["code"] == "code_not_registered"


@pytest.mark.asyncio
async def test_health_endpoint(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_crisis_resources_endpoint(db_session):
    """위기 자원이 항상 노출되는지 — 1393 포함 확인."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        r = await ac.get("/crisis-resources")
        assert r.status_code == 200
        phones = [res["phone"] for res in r.json()["resources"]]
        assert "1393" in phones
