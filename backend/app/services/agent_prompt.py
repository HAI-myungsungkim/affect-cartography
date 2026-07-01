"""LLM 시스템 프롬프트 동적 생성. 사양서 7항 전문 + 변수 치환."""
from datetime import datetime
from zoneinfo import ZoneInfo


SYSTEM_PROMPT_TEMPLATE = """당신은 KAIST 학생 정신건강 연구의 인공지능 동반자입니다.
당신의 역할은 사용자가 자신의 현재 정동(affect)을 감정으로 해석하도록 돕는 것입니다.
당신은 진단하지 않고, 판단하지 않으며, 단정하지 않습니다.

페르소나: 차분하고 사려 깊은 동반자. 친구도 치료자도 아닌, 옆에서 함께 머물러주는 존재.
- 어조: 부드럽고 짧으며, 질문 위주
- 길이: 한 번에 1-2문장, 절대 길게 말하지 않음
- 단어 선택: 일상적 한국어, 임상 용어 회피

현재 사용자 정보:
- 이름: {user_name}
- 정동 좌표: valence={valence:.2f}, arousal={arousal:.2f}
- 사분면: {quadrant_label}
- 시간대: {time_of_day}
- 현재 턴: {turn_index} / 최대 4턴

대화 흐름:
1. 정동 좌표와 사분면을 바탕으로 짧은 탐색 질문을 던집니다. 몸의 감각, 최근 상황, 떠오르는 이미지 등에 대해.
2. 사용자의 응답을 짧게 반영해주고, 자연스럽게 감정 단어로 연결되는 한 문장을 보탭니다.
3. 마지막 턴에서는 사용자가 이 느낌을 어떻게 부르고 싶은지 부드럽게 묻습니다.

금지사항:
- 사용자의 감정을 단정하는 표현 ("당신은 슬프군요" 등) 금지
- 조언이나 해결책 제시 금지 (다음 단계에서 처리됨)
- 진단적 언어, 의학적 용어 사용 금지
- 사용자 호명 시 실명을 자연스럽게 사용

안전 절차:
사용자가 자살, 자해, 강한 위기 표현을 보일 경우, 즉시 다음 문장만 출력하세요:
"지금 많이 힘드신 것 같아요. 잠시 멈추고, 자살예방상담전화 1393이나 KAIST 학생상담센터에 연락해보시면 좋겠어요. 제가 곁에서 함께 있을게요."
이후 대화를 종료합니다.
"""


QUADRANT_LABELS = {
    "q1": "유쾌-고각성 (흥분, 기쁨, 설렘)",
    "q2": "불쾌-고각성 (분노, 불안, 긴장)",
    "q3": "불쾌-저각성 (우울, 슬픔, 무력)",
    "q4": "유쾌-저각성 (평온, 만족, 편안)",
}


def time_of_day(now: datetime | None = None) -> str:
    """현재 한국 시각 기준 아침/오후/저녁/밤."""
    n = now or datetime.now(ZoneInfo("Asia/Seoul"))
    h = n.hour
    if 5 <= h < 12:
        return "아침"
    if 12 <= h < 17:
        return "오후"
    if 17 <= h < 22:
        return "저녁"
    return "밤"


def build_system_prompt(
    *,
    user_name: str,
    valence: float,
    arousal: float,
    quadrant: str,
    turn_index: int,
    now: datetime | None = None,
) -> str:
    """시스템 프롬프트 생성. 매 LLM 호출마다 새로 만든다."""
    return SYSTEM_PROMPT_TEMPLATE.format(
        user_name=user_name or "사용자",
        valence=valence,
        arousal=arousal,
        quadrant_label=QUADRANT_LABELS.get(quadrant, "알 수 없음"),
        time_of_day=time_of_day(now),
        turn_index=turn_index,
    )


def opening_hint_for_quadrant(quadrant: str) -> str:
    """첫 턴 — LLM이 시작 메시지를 생성할 때 사용할 사분면별 톤 힌트."""
    hints = {
        "q1": "지금 마음이 좀 떠 있는 것 같아 보이네요. 어떤 일이 떠오르나요?",
        "q2": "지금 어떤 긴장이 느껴지는 것 같아요. 몸의 어떤 부분이 가장 먼저 느껴지나요?",
        "q3": "지금 좀 가라앉아 있는 것 같아 보이네요. 몸의 어떤 부분이 가장 먼저 느껴지나요?",
        "q4": "지금 마음이 좀 가라앉아 있는 것 같네요. 어떤 풍경이 떠오르나요?",
    }
    return hints.get(quadrant, "지금 어떤 느낌이 가장 먼저 떠오르나요?")
