"""사양서 11단계 — 통합 종단 시나리오 자동화.

전체 사용자 흐름 (로그인 → 정동 → 대화 → 단어 → 강도 → 개입) end-to-end + 동시 다수 사용자.
"""
import asyncio
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
from app.services.llm_client import MockLLMClient, set_llm_client


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
DICT_PATH = Path(__file__).parent.parent / "data" / "emotion_dictionary_v0.json"


@pytest_asyncio.fixture
async def multi_user_setup():
    """10명의 피험자 (P001~P010) 사전 등록."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    SL = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def odb():
        async with SL() as s:
            try: yield s; await s.commit()
            except Exception: await s.rollback(); raise

    app.dependency_overrides[get_db] = odb

    dd = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    async with SL() as s:
        for i in range(1, 11):
            s.add(User(participant_code=f"P{i:03d}", real_name="",
                       device_id_hash=None, record_mode=RecordMode.POINT,
                       status=UserStatus.ACTIVE))
        for w in dd["words"]:
            s.add(EmotionDictionary(
                word=w["word"], definition=w["definition"], example=w["example"],
                valence=w["valence"], arousal=w["arousal"],
                neighbors=w["neighbors"], source=dd["version"]))
        await s.commit()

    set_llm_client(MockLLMClient(["응답"] * 50))

    yield SL

    app.dependency_overrides.clear()
    await engine.dispose()


async def _one_full_cycle(participant_code: str):
    """한 사용자가 로그인 → 완전한 한 사이클 → 결과 반환."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        # 로그인
        r = await ac.post("/auth/login", json={
            "participant_code": participant_code,
            "real_name": f"user-{participant_code}",
            "device_id": f"device-{participant_code}",
        })
        if r.status_code != 200:
            return {"code": participant_code, "ok": False, "stage": "login"}
        ac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac.headers["X-Device-Id"] = f"device-{participant_code}"

        # 정동 기록 (Q3)
        r = await ac.post("/affect/record", json={
            "mode": "point", "valence": -0.4, "arousal": -0.2,
        })
        if r.status_code != 201:
            return {"code": participant_code, "ok": False, "stage": "record"}
        rid = r.json()["record_id"]

        # 에이전트 대화 2턴
        await ac.post("/agent/dialogue/turn", json={"record_id": rid})
        await ac.post("/agent/dialogue/turn", json={
            "record_id": rid, "user_message": "답답해요",
        })

        # 단어 선택
        r = await ac.post("/emotion/select", json={
            "record_id": rid, "selected_word": "답답하다", "intensity": 3,
            "exploration_path": ["답답하다"],
        })
        if r.status_code != 201:
            return {"code": participant_code, "ok": False, "stage": "emotion"}

        # 개입
        r = await ac.post("/intervention/response", json={
            "record_id": rid, "intervention_type": "self_distancing",
            "user_response_text": "친구한테 ...",
        })
        if r.status_code != 201:
            return {"code": participant_code, "ok": False, "stage": "intervention"}

        return {"code": participant_code, "ok": True}


@pytest.mark.asyncio
async def test_concurrent_10_users_full_cycle(multi_user_setup):
    """10명이 동시에 완전한 한 사이클을 수행."""
    results = await asyncio.gather(*[
        _one_full_cycle(f"P{i:03d}") for i in range(1, 11)
    ])
    failed = [r for r in results if not r["ok"]]
    assert not failed, f"실패한 사용자: {failed}"


@pytest.mark.asyncio
async def test_device_binding_isolation_across_users(multi_user_setup):
    """사용자 A의 토큰을 사용자 B의 디바이스 ID로 사용 시도 → 차단."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "A",
            "device_id": "device-A",
        })
        token_a = r.json()["access_token"]

    # P001의 토큰으로 P002의 device ID 사용 시도
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        ac.headers["Authorization"] = f"Bearer {token_a}"
        ac.headers["X-Device-Id"] = "device-B-ATTACKER"  # 다른 기기
        r = await ac.post("/affect/record", json={
            "mode": "point", "valence": 0, "arousal": 0,
        })
        assert r.status_code == 401, "디바이스 바인딩 우회 가능 — 보안 결함"


@pytest.mark.asyncio
async def test_different_users_data_isolated(multi_user_setup):
    """A가 만든 record_id를 B가 접근 시도 → 404 (소유권 검증)."""
    # A 로그인 + 기록
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "A",
            "device_id": "device-A-isolation",
        })
        ac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac.headers["X-Device-Id"] = "device-A-isolation"
        r = await ac.post("/affect/record", json={
            "mode": "point", "valence": -0.4, "arousal": -0.2,
        })
        a_record_id = r.json()["record_id"]

    # B 로그인 후 A의 record_id에 대화 시도
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P002", "real_name": "B",
            "device_id": "device-B-isolation",
        })
        ac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac.headers["X-Device-Id"] = "device-B-isolation"
        r = await ac.post("/agent/dialogue/turn", json={
            "record_id": a_record_id, "user_message": "안녕",
        })
        assert r.status_code == 404, "다른 사용자 record_id 접근 가능 — 데이터 격리 결함"

        r = await ac.post("/emotion/select", json={
            "record_id": a_record_id, "selected_word": "답답하다", "intensity": 3,
        })
        assert r.status_code == 404

        r = await ac.post("/intervention/response", json={
            "record_id": a_record_id, "intervention_type": "self_distancing",
        })
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_isolation_per_user(multi_user_setup):
    """사용자별 대시보드는 본인 데이터만 보여줘야 함."""
    transport = ASGITransport(app=app)
    # A가 3개 기록 생성
    async with AsyncClient(transport=transport, base_url="http://t") as ac_a:
        r = await ac_a.post("/auth/login", json={
            "participant_code": "P001", "real_name": "A",
            "device_id": "device-dash-A",
        })
        ac_a.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac_a.headers["X-Device-Id"] = "device-dash-A"
        for _ in range(3):
            await ac_a.post("/affect/record", json={
                "mode": "point", "valence": -0.4, "arousal": -0.2,
            })

    # B가 1개 기록 생성
    async with AsyncClient(transport=transport, base_url="http://t") as ac_b:
        r = await ac_b.post("/auth/login", json={
            "participant_code": "P002", "real_name": "B",
            "device_id": "device-dash-B",
        })
        ac_b.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac_b.headers["X-Device-Id"] = "device-dash-B"
        await ac_b.post("/affect/record", json={
            "mode": "point", "valence": 0.3, "arousal": 0.4,
        })

        # B의 대시보드 → 1개만
        r = await ac_b.get("/dashboard/me")
        assert r.json()["summary"]["total_records"] == 1, "B의 대시보드에 A 데이터가 섞임"

    # A의 대시보드 → 3개
    async with AsyncClient(transport=transport, base_url="http://t") as ac_a:
        r = await ac_a.post("/auth/login", json={
            "participant_code": "P001", "real_name": "A",
            "device_id": "device-dash-A",
        })
        ac_a.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac_a.headers["X-Device-Id"] = "device-dash-A"
        r = await ac_a.get("/dashboard/me")
        assert r.json()["summary"]["total_records"] == 3


@pytest.mark.asyncio
async def test_practice_session_excluded_from_response_rate(multi_user_setup):
    """연습 세션은 응답률 계산에서 제외."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "A",
            "device_id": "device-practice-ex",
        })
        ac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac.headers["X-Device-Id"] = "device-practice-ex"

        # 연습 3개 + 실제 알림 응답 1개
        for _ in range(3):
            await ac.post("/affect/record", json={
                "mode": "point", "valence": 0, "arousal": 0,
                "is_practice": True,
            })
        await ac.post("/affect/record", json={
            "mode": "point", "valence": -0.4, "arousal": -0.2,
            "prompt_id": "real-prompt-id",
        })

        r = await ac.get("/notification/response-rate?days=1")
        d = r.json()
        # 연습 세션은 제외, 실제 알림 응답만 카운트
        assert d["notification_responses"] == 1
