"""분기 개입 프롬프트 텍스트 — 사양서 4.8.

각 정동 사분면에 따른 마이크로 개입 메시지를 동적 생성.
실명({user_name})은 호명에 사용되며 저장 시에는 마스킹됨.
"""
from typing import Literal


InterventionType = Literal["self_distancing", "grounding", "activation"]


def build_intervention_prompt(
    intervention_type: InterventionType,
    user_name: str,
) -> dict:
    """사양서 4.8 — 사분면 기반 마이크로 개입 메시지.

    좌하단/좌측 (불쾌 일반) → self_distancing
    좌상단 (불쾌-고각성) → grounding (그라운딩 + 시간 거리)
    우측/중립 (유쾌 일반) → activation (if-then)
    """
    name = user_name or "당신"

    if intervention_type == "self_distancing":
        return {
            "intervention_type": "self_distancing",
            "title": "잠깐, 한 걸음 떨어져 볼까요?",
            "body": (
                f"지금 {name} 씨는 어떤 상황에 있는 것 같나요?\n\n"
                "친구에게 이 상황을 설명한다면 뭐라고 할 것 같아요?"
            ),
            "placeholder": "3인칭 시점으로 짧게 적어보세요...",
            "allow_skip": True,
        }

    if intervention_type == "grounding":
        return {
            "intervention_type": "grounding",
            "title": "지금, 여기로 돌아오기",
            "body": (
                "지금 호흡을 천천히 세 번 해보세요.\n"
                "들이쉬고 — 잠시 멈추고 — 내쉬고.\n\n"
                f"5분 뒤의 {name} 씨는 지금 이 순간을 어떻게 볼까요?"
            ),
            "placeholder": "떠오르는 한 줄을 적어보세요...",
            "allow_skip": True,
        }

    if intervention_type == "activation":
        return {
            "intervention_type": "activation",
            "title": "작게 한 가지",
            "body": (
                "지금 이 상태에서 작게 한 가지 시작해본다면?\n\n"
                "'만약 [상황]이 되면, 나는 [구체적 행동]을 하겠다'\n"
                "이런 형태로 한 줄 적어보세요."
            ),
            "placeholder": "예: 만약 점심을 다 먹으면, 5분 산책을 하겠다",
            "allow_skip": True,
        }

    # Fallback (이론상 도달 안 함)
    return {
        "intervention_type": "self_distancing",
        "title": "잠깐 멈춰가기",
        "body": "지금 느낌을 한 문장으로 표현해본다면?",
        "placeholder": "편하게 적어보세요",
        "allow_skip": True,
    }
