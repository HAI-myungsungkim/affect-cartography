"""에이전트 대화 라우터. 사양서 4.4, 7항.

흐름:
  1. 사용자 메시지 → 위기 키워드 1차 필터
     - 매칭 시: safety_flag 즉시 발급 + CRISIS_RESPONSE 출력 + 대화 종료
     - 미매칭: LLM 호출로 진행
  2. LLM 응답 → 위기 키워드 재확인 (LLM이 자살/자해 단어를 직접 생성하지 않는지 안전망)
  3. DB에 user+agent 턴 저장
  4. 최대 4턴 도달 시 is_final=True
"""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.affect import AffectRecord
from app.models.dialogue import AgentDialogue, Speaker
from app.models.safety import SafetyFlag
from app.models.user import User
from app.schemas.dialogue import (
    DialogueHistoryItem,
    DialogueHistoryResponse,
    DialogueTurnRequest,
    DialogueTurnResponse,
)
from app.services.agent_prompt import build_system_prompt, opening_hint_for_quadrant
from app.services.crisis_keywords import CRISIS_RESPONSE, detect_crisis
from app.services.llm_client import get_llm_client

router = APIRouter(prefix="/agent", tags=["agent"])

MAX_TURNS = 4  # 사양서 4.4: 2~4턴 제한


async def _load_record_for_user(
    db: AsyncSession, record_id: str, user: User
) -> AffectRecord:
    try:
        rec_uuid = uuid.UUID(record_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="record_id 형식 오류")
    result = await db.execute(
        select(AffectRecord).where(
            AffectRecord.record_id == rec_uuid,
            AffectRecord.user_id == user.user_id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="해당 기록을 찾을 수 없습니다")
    return record


async def _load_history(
    db: AsyncSession, record_id: uuid.UUID
) -> list[AgentDialogue]:
    result = await db.execute(
        select(AgentDialogue)
        .where(AgentDialogue.record_id == record_id)
        .order_by(AgentDialogue.turn_index)
    )
    return list(result.scalars().all())


@router.post("/dialogue/turn", response_model=DialogueTurnResponse)
async def dialogue_turn(
    payload: DialogueTurnRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """한 턴 진행. user_message 없이 호출하면 첫 턴(에이전트가 먼저 말함)."""
    record = await _load_record_for_user(db, payload.record_id, current_user)
    history = await _load_history(db, record.record_id)

    # 현재 다음 turn_index 계산 (사용자 또는 에이전트 메시지 모두 카운트)
    next_user_turn = len([h for h in history if h.speaker == Speaker.USER])
    next_agent_turn = len([h for h in history if h.speaker == Speaker.AGENT])

    # --- 1. 사용자 메시지 위기 키워드 1차 검사 ---
    if payload.user_message:
        crisis = detect_crisis(payload.user_message)

        # 사용자 메시지를 먼저 저장
        db.add(AgentDialogue(
            record_id=record.record_id,
            turn_index=next_user_turn,
            speaker=Speaker.USER,
            message_text=payload.user_message,
        ))
        await db.flush()

        if crisis:
            # 안전 플래그 발급
            db.add(SafetyFlag(
                user_id=current_user.user_id,
                record_id=record.record_id,
                flag_type=crisis.flag_type,
                trigger_text=payload.user_message[:500],
                matched_keywords=",".join(crisis.matched_keywords)[:256],
            ))
            # 표준 위기 응답
            db.add(AgentDialogue(
                record_id=record.record_id,
                turn_index=next_agent_turn,
                speaker=Speaker.AGENT,
                message_text=CRISIS_RESPONSE,
            ))
            await db.flush()
            return DialogueTurnResponse(
                turn_index=next_agent_turn,
                agent_message=CRISIS_RESPONSE,
                is_final=True,
                safety_flag_raised=True,
                crisis_flag_type=crisis.flag_type.value,
            )

    # --- 2. LLM 호출 ---
    system_prompt = build_system_prompt(
        user_name=current_user.real_name,
        valence=record.valence,
        arousal=record.arousal,
        quadrant=record.quadrant.value,
        turn_index=next_agent_turn + 1,
    )

    # OpenAI message 형식으로 변환 + 현재 사용자 메시지 추가
    messages = []
    for h in history:
        messages.append({
            "role": "user" if h.speaker == Speaker.USER else "assistant",
            "content": h.message_text,
        })
    if payload.user_message:
        messages.append({"role": "user", "content": payload.user_message})
    else:
        # 첫 턴 — 사용자 메시지가 없으므로 명시적으로 시작 요청
        hint = opening_hint_for_quadrant(record.quadrant.value)
        messages.append({
            "role": "user",
            "content": f"[연구진 안내: 대화를 시작해주세요. 톤 힌트: {hint}]",
        })

    try:
        agent_text = await get_llm_client().complete(system_prompt, messages)
    except RuntimeError as e:
        # LLM 실패 시 fallback — 사용자 흐름이 막히지 않도록
        agent_text = opening_hint_for_quadrant(record.quadrant.value)

    # --- 3. LLM 응답 위기 키워드 안전망 (LLM이 부적절 표현 생성하지 않는지) ---
    llm_crisis = detect_crisis(agent_text)
    if llm_crisis:
        # LLM이 위기 표현 생성 → 표준 응답으로 교체 + 안전 플래그
        agent_text = CRISIS_RESPONSE
        db.add(SafetyFlag(
            user_id=current_user.user_id,
            record_id=record.record_id,
            flag_type=llm_crisis.flag_type,
            trigger_text=f"[LLM_OUTPUT] {agent_text[:400]}",
            matched_keywords=",".join(llm_crisis.matched_keywords)[:256],
        ))

    # --- 4. 에이전트 응답 저장 ---
    db.add(AgentDialogue(
        record_id=record.record_id,
        turn_index=next_agent_turn,
        speaker=Speaker.AGENT,
        message_text=agent_text,
    ))
    await db.flush()

    # 다음 턴 가능 여부
    new_agent_turn_count = next_agent_turn + 1
    is_final = new_agent_turn_count >= MAX_TURNS

    return DialogueTurnResponse(
        turn_index=next_agent_turn,
        agent_message=agent_text,
        is_final=is_final,
        safety_flag_raised=False,
    )


@router.get("/dialogue/{record_id}", response_model=DialogueHistoryResponse)
async def get_dialogue_history(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """대화 이력 조회. 8단계 대시보드에서도 사용."""
    record = await _load_record_for_user(db, record_id, current_user)
    history = await _load_history(db, record.record_id)
    return DialogueHistoryResponse(
        record_id=record_id,
        turns=[
            DialogueHistoryItem(
                turn_index=h.turn_index,
                speaker=h.speaker.value,
                message_text=h.message_text,
                timestamp=h.timestamp,
            )
            for h in history
        ],
    )
