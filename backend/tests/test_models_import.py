"""모델이 SQLAlchemy 메타데이터에 정상 등록되는지 확인."""
from app.core.database import Base
from app import models  # noqa: F401  -- 모든 모델 import 트리거


def test_all_tables_registered():
    expected = {
        "users",
        "affect_records",
        "emotion_records",
        "emotion_dictionary",
        "agent_dialogues",
        "intervention_responses",
        "safety_flags",
        "admin_settings",
    }
    actual = set(Base.metadata.tables.keys())
    missing = expected - actual
    assert not missing, f"누락된 테이블: {missing}"


def test_affect_record_has_trajectory_fields():
    """사양서 4.3.4 — 점/궤도 모드 필드 확인."""
    cols = {c.name for c in Base.metadata.tables["affect_records"].columns}
    for required in ["mode", "trajectory_points", "duration_window_minutes", "is_practice"]:
        assert required in cols, f"affect_records.{required} 누락"


def test_user_has_notification_windows():
    """사양서 8항 — 알림 시간대 3구간."""
    cols = {c.name for c in Base.metadata.tables["users"].columns}
    for w in [
        "notify_morning_start", "notify_morning_end",
        "notify_afternoon_start", "notify_afternoon_end",
        "notify_evening_start", "notify_evening_end",
    ]:
        assert w in cols
