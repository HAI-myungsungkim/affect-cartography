"""위기 키워드 1차 필터 단위 테스트.

사양서 7항 + 10항 안전 절차의 핵심 — 100% 탐지 보장 필요.
"""
from app.models.safety import FlagType
from app.services.crisis_keywords import detect_crisis


# --- 자살 사고 (가장 중요) ---

def test_detect_explicit_suicide():
    assert detect_crisis("나 자살하고 싶어").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("자살할 거야").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("자살하려고 해").flag_type == FlagType.SUICIDE_IDEATION


def test_detect_die_wish():
    assert detect_crisis("죽고 싶다").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("그냥 죽고싶어").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("죽어 버리고 싶어").flag_type == FlagType.SUICIDE_IDEATION


def test_detect_end_life():
    assert detect_crisis("이제 끝내고 싶어").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("끝내고싶다").flag_type == FlagType.SUICIDE_IDEATION


def test_detect_disappear():
    assert detect_crisis("사라지고 싶어").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("세상에서 없어졌으면").flag_type == FlagType.SUICIDE_IDEATION


def test_detect_method_mentions():
    assert detect_crisis("수면제 다 먹으면 어떨까").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("목매고 싶다").flag_type == FlagType.SUICIDE_IDEATION
    assert detect_crisis("투신하고 싶어").flag_type == FlagType.SUICIDE_IDEATION


# --- 자해 ---

def test_detect_self_harm():
    assert detect_crisis("자해했어").flag_type == FlagType.SELF_HARM
    assert detect_crisis("칼로 그어버리고 싶어").flag_type == FlagType.SELF_HARM
    assert detect_crisis("손목을 긋고 싶다").flag_type == FlagType.SELF_HARM


# --- 심한 절망 ---

def test_detect_severe_distress():
    assert detect_crisis("살 가치가 없어").flag_type == FlagType.SEVERE_DISTRESS
    assert detect_crisis("더는 못 하겠어").flag_type == FlagType.SEVERE_DISTRESS
    assert detect_crisis("버틸 수가 없다").flag_type == FlagType.SEVERE_DISTRESS


# --- 우선순위: 자살 > 자해 > 절망 ---

def test_priority_suicide_over_distress():
    # 두 카테고리 동시 매칭 → 더 심각한 쪽
    r = detect_crisis("죽고 싶고 더는 못 하겠어")
    assert r.flag_type == FlagType.SUICIDE_IDEATION
    # 매칭된 키워드는 모두 보존
    assert len(r.matched_keywords) >= 2


# --- False negative 방지: 위장된 표현 ---

def test_detect_with_spaces():
    """띄어쓰기 변형도 잡아야 함."""
    assert detect_crisis("죽  고  싶  어") is not None or \
        detect_crisis("죽 고 싶다") is not None or \
        detect_crisis("죽고싶어").flag_type == FlagType.SUICIDE_IDEATION


# --- False positive 검사: 일상 표현은 통과 ---

def test_normal_messages_pass():
    assert detect_crisis("오늘 발표 잘 끝나서 기쁘다") is None
    assert detect_crisis("시험 기간이라 좀 지쳐") is None
    assert detect_crisis("친구랑 다투고 짜증나") is None
    assert detect_crisis("배가 너무 고파서 죽겠다") is None  # 관용 표현 — '죽겠'은 패턴에 안 들어감


def test_empty_input():
    assert detect_crisis("") is None
    assert detect_crisis(None) is None


def test_matched_keywords_recorded():
    """매칭된 키워드가 감사 로그용으로 보존되는지."""
    r = detect_crisis("자살하고 싶어")
    assert r is not None
    assert len(r.matched_keywords) > 0
    assert any("자살" in kw for kw in r.matched_keywords)
