"""사양서 11단계 — 위기 키워드 20개 전수 검증 시나리오.

운영 배포 전 100% 통과해야 함. 한 개라도 놓치면 배포 차단.
"""
from app.models.safety import FlagType
from app.services.crisis_keywords import detect_crisis


# 20개 시나리오. 실제 한국어 사용자가 쓸 법한 다양한 변형 포함.
CRISIS_TEST_CASES = [
    # 자살 사고 — 직접 표현 (12개)
    ("자살하고 싶어요", FlagType.SUICIDE_IDEATION),
    ("그냥 자살할까봐 무서워", FlagType.SUICIDE_IDEATION),
    ("자살하려고 약을 모았어", FlagType.SUICIDE_IDEATION),
    ("죽고 싶다는 생각이 자꾸 들어", FlagType.SUICIDE_IDEATION),
    ("죽어 버리고 싶어", FlagType.SUICIDE_IDEATION),
    ("이렇게 살 바엔 끝내고 싶어", FlagType.SUICIDE_IDEATION),
    ("그냥 사라지고 싶어", FlagType.SUICIDE_IDEATION),
    ("세상에서 없어졌으면 좋겠어", FlagType.SUICIDE_IDEATION),
    ("목숨을 끊고 싶다는 생각", FlagType.SUICIDE_IDEATION),
    ("수면제를 다 먹어버릴까", FlagType.SUICIDE_IDEATION),
    ("극단적 선택을 고민하고 있어", FlagType.SUICIDE_IDEATION),
    ("투신하면 어떨까 싶어", FlagType.SUICIDE_IDEATION),
    # 자해 (4개)
    ("자해를 했어요", FlagType.SELF_HARM),
    ("칼로 그어버리고 싶어요", FlagType.SELF_HARM),
    ("손목을 긋는 상상을 자주 해", FlagType.SELF_HARM),
    ("내 몸을 다치게 하고 싶어", FlagType.SELF_HARM),
    # 심한 절망 — 명시적 위기 표현은 아니지만 즉각 검토 필요 (4개)
    ("살 가치가 없는 것 같아", FlagType.SEVERE_DISTRESS),
    ("내가 없는 게 모두에게 낫겠지", FlagType.SEVERE_DISTRESS),
    ("더는 못 하겠어 정말", FlagType.SEVERE_DISTRESS),
    ("이젠 버틸 수가 없어", FlagType.SEVERE_DISTRESS),
]


def test_crisis_20_all_detected():
    """20개 전부 detect_crisis가 None이 아니어야 함 (False Negative 0)."""
    misses = []
    for text, expected_type in CRISIS_TEST_CASES:
        result = detect_crisis(text)
        if result is None:
            misses.append(text)
    assert not misses, (
        f"위기 표현 누락 (운영 배포 차단): {misses}"
    )


def test_crisis_20_correct_type():
    """20개 모두 올바른 카테고리로 분류."""
    wrong = []
    for text, expected_type in CRISIS_TEST_CASES:
        result = detect_crisis(text)
        if result is None or result.flag_type != expected_type:
            wrong.append((text, expected_type.value,
                          result.flag_type.value if result else "MISS"))
    assert not wrong, f"카테고리 오분류: {wrong}"


def test_crisis_keywords_preserved_in_match():
    """매칭 키워드가 모두 보존되어 감사 로그에 남는지."""
    for text, _ in CRISIS_TEST_CASES:
        result = detect_crisis(text)
        assert result is not None
        assert len(result.matched_keywords) > 0, (
            f"'{text}'에서 matched_keywords 비어있음"
        )


# 정상 표현 false positive 검증 — 일상 표현은 통과해야 함
NORMAL_CASES = [
    "오늘 발표 잘 끝나서 기쁘다",
    "배가 너무 고파서 죽겠다",  # 관용 표현
    "시험 망쳐서 너무 힘들어",
    "친구랑 다투고 짜증나",
    "이번 학기 진짜 빡셌어",
    "잠을 못 자서 피곤해",
    "공부하기 싫다 정말",
    "이거 진짜 어려워서 미치겠어",  # 관용
]


def test_normal_messages_not_flagged():
    """일상 표현은 위기로 잡히지 않아야 함 (False Positive 0)."""
    fp = []
    for text in NORMAL_CASES:
        result = detect_crisis(text)
        if result is not None:
            fp.append((text, result.flag_type.value))
    assert not fp, f"False positive 발생 (사용자 경험 저해): {fp}"
