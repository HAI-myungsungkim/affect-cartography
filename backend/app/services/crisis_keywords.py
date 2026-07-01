"""위기 표현 1차 정규식 필터.

설계 원칙:
  - LLM 호출 전에 정규식으로 먼저 걸러서 즉시 차단 (LLM이 부적절 응답 생성하지 않도록)
  - false positive를 두려워하지 말고 보수적으로 탐지 (놓치는 것보다 안전)
  - 매칭된 패턴을 safety_flag.matched_keywords에 기록해서 사후 감사 가능

키워드 출처: KAIST 학생상담센터 + 한국형 자살위험성 평가도구 보편 표현
"""
import re
from dataclasses import dataclass

from app.models.safety import FlagType


@dataclass
class CrisisMatch:
    flag_type: FlagType
    matched_keywords: list[str]


# 자살 사고 — 가장 명시적인 표현부터
SUICIDE_PATTERNS = [
    r"자살(하|할|하고|하려|해야|해버)",
    r"죽고\s*싶",
    r"죽어\s*버리",
    r"끝내고\s*싶",
    r"사라지고\s*싶",
    r"세상에서\s*없",
    r"목숨을\s*끊",
    r"목매",
    r"투신",
    r"수면제\S*\s*(다|모두|전부)",
    r"수면제\S*\s*먹",  # 수면제를 다 먹어/먹어버릴 등
    r"극단적\s*선택",
    r"안락사",
]

# 자해 — 자살과 구분, 다만 둘 다 즉시 개입 대상
SELF_HARM_PATTERNS = [
    r"자해",
    r"칼로\s*긋",
    r"칼로\s*그어",
    r"손목\s*그",
    r"손목을\s*긋",
    r"손목을\s*그어",
    r"피가\s*날\s*때까지",
    r"내\s*몸을\s*다치",
    r"나를\s*해치",
    r"벽에\s*머리\s*박",
]

# 심한 절망 — 자살/자해 직접 표현은 아니지만 즉각 검토 필요
SEVERE_DISTRESS_PATTERNS = [
    r"살\s*가치가\s*없",
    r"내가\s*없는\s*게\s*\S*\s*\S*\s*낫",
    r"내가\s*없어야",
    r"내가\s*사라지면\s*다\s*편",
    r"아무\s*의미\s*없",
    r"버틸\s*수가\s*없",
    r"더는\s*못\s*하겠",
    r"포기하고\s*싶",
    r"숨을\s*쉴\s*수가\s*없",
    r"견딜\s*수가\s*없",
]

_SUICIDE_RE = [re.compile(p) for p in SUICIDE_PATTERNS]
_SELF_HARM_RE = [re.compile(p) for p in SELF_HARM_PATTERNS]
_DISTRESS_RE = [re.compile(p) for p in SEVERE_DISTRESS_PATTERNS]


def detect_crisis(text: str) -> CrisisMatch | None:
    """1차 정규식 필터.
    
    여러 카테고리가 동시 매칭되면 우선순위: suicide > self_harm > distress.
    매칭이 없으면 None.
    """
    if not text:
        return None
    normalized = text.replace("\n", " ").strip()

    matched_suicide: list[str] = []
    matched_self_harm: list[str] = []
    matched_distress: list[str] = []

    for r in _SUICIDE_RE:
        m = r.search(normalized)
        if m:
            matched_suicide.append(m.group(0))

    for r in _SELF_HARM_RE:
        m = r.search(normalized)
        if m:
            matched_self_harm.append(m.group(0))

    for r in _DISTRESS_RE:
        m = r.search(normalized)
        if m:
            matched_distress.append(m.group(0))

    if matched_suicide:
        return CrisisMatch(
            flag_type=FlagType.SUICIDE_IDEATION,
            matched_keywords=matched_suicide + matched_self_harm + matched_distress,
        )
    if matched_self_harm:
        return CrisisMatch(
            flag_type=FlagType.SELF_HARM,
            matched_keywords=matched_self_harm + matched_distress,
        )
    if matched_distress:
        return CrisisMatch(
            flag_type=FlagType.SEVERE_DISTRESS,
            matched_keywords=matched_distress,
        )
    return None


# 사용자가 위기 표현을 보일 때 에이전트가 즉시 출력할 표준 메시지 (사양서 7항).
CRISIS_RESPONSE = (
    "지금 많이 힘드신 것 같아요. 잠시 멈추고, "
    "자살예방상담전화 1393이나 KAIST 학생상담센터에 연락해보시면 좋겠어요. "
    "제가 곁에서 함께 있을게요."
)
