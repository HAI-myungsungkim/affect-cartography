"""사양서 11단계 — 다운로드 자료 ↔ DB 원본 100% 정합성 검증.

CSV/JSON 다운로드 결과가 DB와 모든 필드에서 일치해야 한다.
사양서 5항 + IRB 데이터 신뢰성 핵심 요구사항.
"""
import csv
import io
import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.database import Base, get_db
from app.core.config import settings
from app.main import app
from app.models.affect import AffectRecord
from app.models.dialogue import AgentDialogue
from app.models.emotion import EmotionDictionary, EmotionRecord
from app.models.user import User, UserStatus, RecordMode
from app.services.llm_client import MockLLMClient, set_llm_client


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
DICT_PATH = Path(__file__).parent.parent / "data" / "emotion_dictionary_v0.json"


@pytest_asyncio.fixture
async def populated_setup():
    """다양한 모드 + 사분면의 기록을 갖춘 fixture."""
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
        s.add(User(participant_code="P002", real_name="이영희",
                   device_id_hash=None, record_mode=RecordMode.POINT,
                   status=UserStatus.ACTIVE))
        for w in dd["words"]:
            s.add(EmotionDictionary(
                word=w["word"], definition=w["definition"], example=w["example"],
                valence=w["valence"], arousal=w["arousal"],
                neighbors=w["neighbors"], source=dd["version"],
            ))
        await s.commit()

    set_llm_client(MockLLMClient(["응답"] * 10))

    # P001로 3개 기록 (점/궤도/연습)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/auth/login", json={
            "participant_code": "P001", "real_name": "김철수",
            "device_id": "device-export-p1",
        })
        ac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        ac.headers["X-Device-Id"] = "device-export-p1"

        # 기록 1: 점 모드 Q3 + 감정 + 개입
        r = await ac.post("/affect/record", json={
            "mode": "point", "valence": -0.4, "arousal": -0.2,
            "response_latency_ms": 3500, "prompt_id": "morning-001",
        })
        rid = r.json()["record_id"]
        await ac.post("/agent/dialogue/turn", json={"record_id": rid})
        await ac.post("/agent/dialogue/turn", json={
            "record_id": rid, "user_message": "답답해요",
        })
        await ac.post("/emotion/select", json={
            "record_id": rid, "selected_word": "답답하다", "intensity": 3,
            "exploration_path": ["답답하다"],
        })
        await ac.post("/intervention/response", json={
            "record_id": rid, "intervention_type": "self_distancing",
            "user_response_text": "친구한테 말한다면 ...",
        })

        # 기록 2: 궤도 모드 Q1
        await ac.post("/affect/record", json={
            "mode": "trajectory", "valence": 0.6, "arousal": 0.5,
            "trajectory_points": [
                {"v": -0.1, "a": 0.0, "t": 0},
                {"v": 0.6, "a": 0.5, "t": 300},
            ],
        })

        # 기록 3: 연습 세션
        await ac.post("/affect/record", json={
            "mode": "point", "valence": 0.0, "arousal": 0.0,
            "is_practice": True,
        })

    # 관리자 클라이언트
    async with AsyncClient(transport=transport, base_url="http://t") as admin_ac:
        r = await admin_ac.post("/auth/admin/login", json={
            "admin_code": settings.admin_code,
            "device_id": "admin-export-001",
        })
        admin_ac.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        yield admin_ac, SL

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_csv_row_count_matches_db(populated_setup):
    """CSV 데이터 행 수 == DB 정동 기록 수."""
    admin_ac, SL = populated_setup
    r = await admin_ac.get("/admin/export/csv?anonymize=false")
    assert r.status_code == 200

    reader = csv.DictReader(io.StringIO(r.text))
    csv_rows = list(reader)

    async with SL() as s:
        result = await s.execute(select(AffectRecord))
        db_records = list(result.scalars().all())

    assert len(csv_rows) == len(db_records), (
        f"CSV {len(csv_rows)} != DB {len(db_records)}"
    )


@pytest.mark.asyncio
async def test_csv_record_ids_match_db(populated_setup):
    """CSV의 record_id 집합 == DB의 record_id 집합."""
    admin_ac, SL = populated_setup
    r = await admin_ac.get("/admin/export/csv?anonymize=false")
    csv_ids = {row["record_id"] for row in csv.DictReader(io.StringIO(r.text))}

    async with SL() as s:
        result = await s.execute(select(AffectRecord.record_id))
        db_ids = {str(rid) for (rid,) in result.all()}

    assert csv_ids == db_ids


@pytest.mark.asyncio
async def test_csv_valence_arousal_precision(populated_setup):
    """CSV의 valence/arousal이 DB와 부호·값 일치."""
    admin_ac, SL = populated_setup
    r = await admin_ac.get("/admin/export/csv?anonymize=false")
    rows = {row["record_id"]: row for row in csv.DictReader(io.StringIO(r.text))}

    async with SL() as s:
        result = await s.execute(select(AffectRecord))
        records = list(result.scalars().all())

    for db_rec in records:
        csv_row = rows[str(db_rec.record_id)]
        assert abs(float(csv_row["valence"]) - db_rec.valence) < 1e-6
        assert abs(float(csv_row["arousal"]) - db_rec.arousal) < 1e-6
        assert csv_row["quadrant"] == db_rec.quadrant.value
        assert csv_row["mode"] == db_rec.mode.value


@pytest.mark.asyncio
async def test_csv_includes_emotion_and_intervention(populated_setup):
    """감정 + 개입이 있는 기록에서 CSV에도 모두 표시."""
    admin_ac, SL = populated_setup
    r = await admin_ac.get("/admin/export/csv?anonymize=false")
    rows = list(csv.DictReader(io.StringIO(r.text)))

    # 답답하다 + self_distancing 행이 있어야
    matching = [r for r in rows if r["selected_word"] == "답답하다"]
    assert len(matching) == 1
    row = matching[0]
    assert row["intensity"] == "3"
    assert row["intervention_type"] == "self_distancing"
    assert "친구한테" in row["intervention_text"]


@pytest.mark.asyncio
async def test_csv_anonymize_masks_name(populated_setup):
    """익명화 ON 시 실명이 마스킹됨."""
    admin_ac, SL = populated_setup
    r = await admin_ac.get("/admin/export/csv?anonymize=true")
    assert "김철수" not in r.text
    assert "김○○" in r.text


@pytest.mark.asyncio
async def test_dialogues_json_matches_db_turns(populated_setup):
    """대화 JSON의 턴 수 == DB의 턴 수."""
    admin_ac, SL = populated_setup
    r = await admin_ac.get("/admin/export/dialogues.json?anonymize=false")
    export = json.loads(r.text)

    async with SL() as s:
        result = await s.execute(select(AgentDialogue))
        db_turns = list(result.scalars().all())

    json_turn_count = sum(len(item["turns"]) for item in export)
    assert json_turn_count == len(db_turns)


@pytest.mark.asyncio
async def test_dialogues_json_turn_order_preserved(populated_setup):
    """JSON 각 기록의 턴이 turn_index 순서대로."""
    admin_ac, _ = populated_setup
    r = await admin_ac.get("/admin/export/dialogues.json?anonymize=false")
    export = json.loads(r.text)

    for item in export:
        idxs = [t["turn_index"] for t in item["turns"]]
        assert idxs == sorted(idxs), f"턴 순서 오류 in {item['record_id']}"


@pytest.mark.asyncio
async def test_practice_records_included_in_export(populated_setup):
    """연습 세션 기록도 export에 포함 (is_practice 플래그로 구분 가능)."""
    admin_ac, _ = populated_setup
    r = await admin_ac.get("/admin/export/csv?anonymize=false")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    practice_rows = [row for row in rows if row["is_practice"] in ("True", "1")]
    assert len(practice_rows) == 1
