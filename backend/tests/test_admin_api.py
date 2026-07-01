"""관리자 API 테스트. 사양서 5항."""
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app
from app.models.emotion import EmotionDictionary
from app.models.user import User, UserStatus, RecordMode


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
DICT_PATH = Path(__file__).parent.parent / "data" / "emotion_dictionary_v0.json"


@pytest_asyncio.fixture
async def admin_client():
    """관리자 인증 + 사용자 1명 + 사전 시드."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SL = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def odb():
        async with SL() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = odb

    dd = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    async with SL() as s:
        s.add(User(participant_code="P001", real_name="김철수",
                   device_id_hash=None, record_mode=RecordMode.POINT,
                   status=UserStatus.ACTIVE))
        for w in dd["words"]:
            s.add(EmotionDictionary(
                word=w["word"], definition=w["definition"], example=w["example"],
                valence=w["valence"], arousal=w["arousal"],
                neighbors=w["neighbors"], source=dd["version"],
            ))
        await s.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 관리자 로그인
        r = await ac.post("/auth/admin/login", json={
            "admin_code": settings.admin_code,
            "device_id": "admin-device-001",
        })
        token = r.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac

    app.dependency_overrides.clear()
    await engine.dispose()


# --- 사용자 관리 ---

@pytest.mark.asyncio
async def test_list_users(admin_client):
    r = await admin_client.get("/admin/users")
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert any(u["participant_code"] == "P001" for u in d["users"])


@pytest.mark.asyncio
async def test_list_users_anonymized(admin_client):
    r = await admin_client.get("/admin/users?anonymize=true")
    user = next(u for u in r.json()["users"] if u["participant_code"] == "P001")
    assert user["real_name"] == "김○○"  # 마스킹됨


@pytest.mark.asyncio
async def test_create_participant(admin_client):
    r = await admin_client.post("/admin/users", json={
        "participant_code": "P099", "real_name": "신규자",
    })
    assert r.status_code == 201
    assert r.json()["participant_code"] == "P099"


@pytest.mark.asyncio
async def test_duplicate_participant_rejected(admin_client):
    r = await admin_client.post("/admin/users", json={
        "participant_code": "P001", "real_name": "다른이름",
    })
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_unbind_device(admin_client):
    # 먼저 사용자가 로그인하여 디바이스 바인딩
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as user_ac:
        await user_ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "user-device-aaa",
        })

    # 사용자 ID 조회
    r = await admin_client.get("/admin/users")
    user_id = next(u for u in r.json()["users"]
                   if u["participant_code"] == "P001")["user_id"]

    # 디바이스 해제
    r = await admin_client.post(f"/admin/users/{user_id}/unbind-device")
    assert r.status_code == 200
    assert "해제" in r.json()["message"]

    # 이제 다른 기기로 로그인 가능
    async with AsyncClient(transport=transport, base_url="http://test") as user_ac:
        r = await user_ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "user-device-bbb",
        })
        assert r.status_code == 200  # 성공


@pytest.mark.asyncio
async def test_user_detail_with_records(admin_client):
    """사용자 기록이 있을 때 상세 페이지에 모두 결합되어 나오는지."""
    # 일반 사용자 로그인 + 기록 생성
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as uac:
        r = await uac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "user-detail-device",
        })
        uac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        uac.headers["X-Device-Id"] = "user-detail-device"
        r = await uac.post("/affect/record", json={
            "mode": "point", "valence": -0.4, "arousal": -0.2,
        })
        rid = r.json()["record_id"]
        await uac.post("/emotion/select", json={
            "record_id": rid, "selected_word": "답답하다", "intensity": 3,
            "exploration_path": ["답답하다"],
        })
        await uac.post("/intervention/response", json={
            "record_id": rid, "intervention_type": "self_distancing",
            "user_response_text": "친구한테 말한다면 ...",
        })

    # 관리자 상세 조회
    r = await admin_client.get("/admin/users")
    user_id = next(u for u in r.json()["users"]
                   if u["participant_code"] == "P001")["user_id"]
    r = await admin_client.get(f"/admin/users/{user_id}")
    assert r.status_code == 200
    d = r.json()
    assert d["summary"]["total_records"] == 1
    assert len(d["records"]) == 1
    rec = d["records"][0]
    assert rec["emotion_word"] == "답답하다"
    assert rec["intensity"] == 3
    assert rec["intervention_type"] == "self_distancing"
    assert "친구" in rec["intervention_text"]


# --- 보안 ---

@pytest.mark.asyncio
async def test_admin_endpoints_require_admin_token(admin_client):
    """관리자가 아닌 일반 토큰으로는 거부."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as uac:
        r = await uac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "user-device-zz",
        })
        user_token = r.json()["access_token"]
    
    # 일반 토큰으로 관리자 엔드포인트 시도
    transport2 = ASGITransport(app=app)
    async with AsyncClient(transport=transport2, base_url="http://test") as ac:
        ac.headers["Authorization"] = f"Bearer {user_token}"
        r = await ac.get("/admin/users")
        assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_endpoints_require_token(admin_client):
    """토큰 없이 접근 → 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/admin/users")
        assert r.status_code == 401


# --- 데이터 익스포트 ---

@pytest.mark.asyncio
async def test_export_csv(admin_client):
    """기록이 있을 때 CSV 다운로드 — 헤더 + 데이터 행."""
    # 데이터 시드
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as uac:
        r = await uac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "csv-device-001",
        })
        uac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        uac.headers["X-Device-Id"] = "csv-device-001"
        rr = await uac.post("/affect/record", json={
            "mode": "point", "valence": -0.4, "arousal": -0.2,
        })
        rid = rr.json()["record_id"]
        await uac.post("/emotion/select", json={
            "record_id": rid, "selected_word": "답답하다", "intensity": 3,
            "exploration_path": ["답답하다"],
        })

    r = await admin_client.get("/admin/export/csv")
    assert r.status_code == 200
    csv_text = r.text
    assert "participant_code" in csv_text  # 헤더
    assert "P001" in csv_text  # 데이터
    assert "답답하다" in csv_text


@pytest.mark.asyncio
async def test_export_csv_anonymized(admin_client):
    """익명화 옵션 — 원본 이름이 CSV에 없어야."""
    # 기록 생성
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as uac:
        r = await uac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "csv-anon-device",
        })
        uac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        uac.headers["X-Device-Id"] = "csv-anon-device"
        await uac.post("/affect/record", json={
            "mode": "point", "valence": 0.0, "arousal": 0.0,
        })

    r = await admin_client.get("/admin/export/csv?anonymize=true")
    assert r.status_code == 200
    # 마스킹된 형태 포함, 원본 이름 없음
    assert "김○○" in r.text
    assert "김철수" not in r.text


@pytest.mark.asyncio
async def test_export_dialogues_json(admin_client):
    """대화 로그 JSON 다운로드."""
    r = await admin_client.get("/admin/export/dialogues.json")
    assert r.status_code == 200
    # 빈 배열이라도 JSON 파싱 가능해야 함
    parsed = json.loads(r.text)
    assert isinstance(parsed, list)


# --- 안전 플래그 ---

@pytest.mark.asyncio
async def test_list_safety_flags_empty(admin_client):
    r = await admin_client.get("/admin/safety-flags")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# --- 대화 감사 ---

@pytest.mark.asyncio
async def test_audit_dialogues(admin_client):
    r = await admin_client.get("/admin/dialogues/audit?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
