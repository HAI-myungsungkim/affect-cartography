"""관리자 라우터. 사양서 5항.

PC 웹 대시보드 전용. 관리자 코드 로그인 후 진입.
모든 엔드포인트는 get_admin_user 의존성으로 보호.
"""
import csv
import io
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user
from app.core.database import get_db
from app.core.security import mask_real_name
from app.models.affect import AffectRecord
from app.models.dialogue import AgentDialogue, Speaker
from app.models.emotion import EmotionRecord
from app.models.intervention import InterventionResponse
from app.models.safety import SafetyFlag
from app.models.user import User, UserStatus
from app.schemas.admin import (
    AdminUserDetail,
    AdminUserDetailRecord,
    AdminUserListItem,
    AdminUsersResponse,
    CreateParticipantRequest,
    CreateParticipantResponse,
    DialogueAuditItem,
    FlagReviewRequest,
    SafetyFlagOut,
    UnbindDeviceResponse,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(get_admin_user)],
)


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    db: AsyncSession = Depends(get_db),
    status: Optional[str] = Query(None),
    anonymize: bool = Query(False),
):
    """전체 사용자 목록 + 응답률 등 통계."""
    stmt = select(User).order_by(User.registered_at.desc())
    if status:
        stmt = stmt.where(User.status == UserStatus(status))
    result = await db.execute(stmt)
    users = list(result.scalars().all())

    items: list[AdminUserListItem] = []
    for u in users:
        # 응답 통계
        rec_result = await db.execute(
            select(AffectRecord).where(
                AffectRecord.user_id == u.user_id,
                AffectRecord.is_practice.is_(False),
            )
        )
        records = list(rec_result.scalars().all())
        last_resp = max((r.timestamp for r in records), default=None)
        notif_records = [r for r in records if r.prompt_id]

        # 가입 일수 기반 expected (SQLite tz-naive 호환)
        if u.first_login_at:
            now = datetime.now(timezone.utc)
            fl = u.first_login_at
            if fl.tzinfo is None:
                fl = fl.replace(tzinfo=timezone.utc)
            days_since_first = (now - fl).days + 1
        else:
            days_since_first = 0
        expected = max(1, days_since_first * 3)
        response_rate = min(1.0, len(notif_records) / expected) if notif_records else 0.0

        flag_result = await db.execute(
            select(func.count(SafetyFlag.flag_id)).where(
                SafetyFlag.user_id == u.user_id
            )
        )
        flag_count = int(flag_result.scalar_one() or 0)

        items.append(AdminUserListItem(
            user_id=str(u.user_id),
            participant_code=u.participant_code,
            real_name=mask_real_name(u.real_name) if anonymize else u.real_name,
            registered_at=u.registered_at,
            first_login_at=u.first_login_at,
            last_response_at=last_resp,
            total_records=len(records),
            response_rate=round(response_rate, 3),
            safety_flag_count=flag_count,
            status=u.status.value,
            record_mode=u.record_mode.value,
            has_device_bound=u.device_id_hash is not None,
        ))

    return AdminUsersResponse(total=len(items), users=items)


@router.get("/users/{user_id}", response_model=AdminUserDetail)
async def get_user_detail(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    anonymize: bool = Query(False),
):
    """사용자 상세 — 모든 기록 + 감정 + 개입 + 대화 결합."""
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id 형식 오류")

    result = await db.execute(select(User).where(User.user_id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    # 정동 기록
    result = await db.execute(
        select(AffectRecord)
        .where(AffectRecord.user_id == uid)
        .order_by(desc(AffectRecord.timestamp))
    )
    records = list(result.scalars().all())
    rec_ids = [r.record_id for r in records]

    # 감정 + 개입 + 대화 모두 결합
    emotions, interventions, dialogue_counts = {}, {}, {}
    if rec_ids:
        r = await db.execute(
            select(EmotionRecord).where(EmotionRecord.record_id.in_(rec_ids))
        )
        emotions = {e.record_id: e for e in r.scalars().all()}

        r = await db.execute(
            select(InterventionResponse).where(
                InterventionResponse.record_id.in_(rec_ids)
            )
        )
        interventions = {i.record_id: i for i in r.scalars().all()}

        r = await db.execute(
            select(AgentDialogue.record_id, func.count(AgentDialogue.dialogue_id))
            .where(AgentDialogue.record_id.in_(rec_ids))
            .group_by(AgentDialogue.record_id)
        )
        dialogue_counts = {row[0]: row[1] for row in r.all()}

    detail_records = []
    for r in records:
        em = emotions.get(r.record_id)
        iv = interventions.get(r.record_id)
        detail_records.append(AdminUserDetailRecord(
            record_id=str(r.record_id),
            timestamp=r.timestamp,
            valence=r.valence,
            arousal=r.arousal,
            quadrant=r.quadrant.value,
            mode=r.mode.value,
            is_practice=r.is_practice,
            trajectory_points=r.trajectory_points,
            emotion_word=em.selected_word if em else None,
            intensity=em.intensity if em else None,
            exploration_path=em.exploration_path if em else None,
            intervention_type=iv.intervention_type.value if iv else None,
            intervention_text=iv.user_response_text if iv else None,
            dialogue_turns=dialogue_counts.get(r.record_id, 0),
        ))

    notif_count = sum(1 for r in records if r.prompt_id and not r.is_practice)
    if user.first_login_at:
        now = datetime.now(timezone.utc)
        fl = user.first_login_at
        if fl.tzinfo is None:
            fl = fl.replace(tzinfo=timezone.utc)
        days_since = (now - fl).days + 1
    else:
        days_since = 0
    expected = max(1, days_since * 3)

    summary = {
        "total_records": len(records),
        "notification_responses": notif_count,
        "response_rate": round(min(1.0, notif_count / expected), 3),
        "days_active": len({r.timestamp.date() for r in records}),
    }

    return AdminUserDetail(
        user_id=str(user.user_id),
        participant_code=user.participant_code,
        real_name=mask_real_name(user.real_name) if anonymize else user.real_name,
        registered_at=user.registered_at,
        status=user.status.value,
        record_mode=user.record_mode.value,
        summary=summary,
        records=detail_records,
    )


@router.post("/users", response_model=CreateParticipantResponse, status_code=201)
async def create_participant(
    payload: CreateParticipantRequest,
    db: AsyncSession = Depends(get_db),
):
    """새 피험자 코드 발급. 사양서 5항."""
    result = await db.execute(
        select(User).where(User.participant_code == payload.participant_code)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"이미 사용 중인 코드: {payload.participant_code}",
        )

    user = User(
        participant_code=payload.participant_code,
        real_name=payload.real_name,
        device_id_hash=None,
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    return CreateParticipantResponse(
        user_id=str(user.user_id),
        participant_code=user.participant_code,
        real_name=user.real_name,
        registered_at=user.registered_at,
    )


@router.post("/users/{user_id}/unbind-device", response_model=UnbindDeviceResponse)
async def unbind_device(
    user_id: str,
    db: AsyncSession = Depends(get_db),
):
    """디바이스 바인딩 해제. 사양서 4.1, 5항.

    피험자가 기기를 바꾼 경우 관리자가 수동 해제 → 다음 로그인 시 새 기기에 재바인딩.
    """
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="user_id 형식 오류")
    result = await db.execute(select(User).where(User.user_id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다")

    user.device_id_hash = None
    await db.flush()
    return UnbindDeviceResponse(
        user_id=str(user.user_id),
        participant_code=user.participant_code,
        message="디바이스 바인딩이 해제되었습니다. 사용자는 새 기기에서 로그인할 수 있습니다.",
    )


@router.get("/safety-flags", response_model=list[SafetyFlagOut])
async def list_safety_flags(
    db: AsyncSession = Depends(get_db),
    unreviewed_only: bool = Query(False),
    limit: int = Query(100, le=500),
):
    """안전 플래그 목록. 사양서 10항.

    위기 키워드 감지 시 발급된 플래그 — 관리자가 사후 검토.
    """
    stmt = select(SafetyFlag).order_by(SafetyFlag.raised_at.desc()).limit(limit)
    if unreviewed_only:
        stmt = stmt.where(SafetyFlag.reviewed_at.is_(None))
    result = await db.execute(stmt)
    flags = list(result.scalars().all())

    # 사용자 정보 조인
    user_ids = list({f.user_id for f in flags})
    users_map = {}
    if user_ids:
        r = await db.execute(select(User).where(User.user_id.in_(user_ids)))
        users_map = {u.user_id: u for u in r.scalars().all()}

    return [
        SafetyFlagOut(
            flag_id=str(f.flag_id),
            user_id=str(f.user_id),
            participant_code=users_map.get(f.user_id).participant_code if f.user_id in users_map else "?",
            real_name=users_map.get(f.user_id).real_name if f.user_id in users_map else "?",
            flag_type=f.flag_type.value,
            trigger_text=f.trigger_text,
            matched_keywords=f.matched_keywords,
            raised_at=f.raised_at,
            reviewed_by=f.reviewed_by,
            reviewed_at=f.reviewed_at,
        )
        for f in flags
    ]


@router.post("/safety-flags/{flag_id}/review")
async def review_flag(
    flag_id: str,
    payload: FlagReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """안전 플래그 검토 완료 표시."""
    try:
        fid = uuid.UUID(flag_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="flag_id 형식 오류")
    result = await db.execute(select(SafetyFlag).where(SafetyFlag.flag_id == fid))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="플래그를 찾을 수 없습니다")
    flag.reviewed_by = payload.reviewed_by
    flag.reviewed_at = datetime.now(timezone.utc)
    await db.flush()
    return {"flag_id": str(flag.flag_id), "reviewed_by": flag.reviewed_by}


@router.get("/dialogues/audit", response_model=list[DialogueAuditItem])
async def audit_dialogues(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, le=100),
    days: int = Query(7, ge=1, le=90),
):
    """대화 감사 페이지 — 최근 N일 무작위 대화 표본.

    사양서 5항. 부적절한 LLM 응답 식별 + 안전 플래그와 교차 검토.
    """
    since = datetime.now(timezone.utc) - timedelta(days=days)
    # 최근 기록 중 대화가 있는 것
    stmt = (
        select(AffectRecord)
        .where(AffectRecord.timestamp >= since)
        .order_by(func.random() if hasattr(func, "random") else AffectRecord.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = list(result.scalars().all())

    items = []
    for r in records:
        # 대화 가져오기
        dr = await db.execute(
            select(AgentDialogue)
            .where(AgentDialogue.record_id == r.record_id)
            .order_by(AgentDialogue.turn_index)
        )
        turns = list(dr.scalars().all())
        if not turns:
            continue  # 대화 없는 기록은 제외

        # 사용자 조회
        ur = await db.execute(select(User).where(User.user_id == r.user_id))
        user = ur.scalar_one_or_none()

        # safety flag 있는지
        fr = await db.execute(
            select(SafetyFlag).where(SafetyFlag.record_id == r.record_id)
        )
        flagged = fr.scalar_one_or_none() is not None

        items.append(DialogueAuditItem(
            record_id=str(r.record_id),
            participant_code=user.participant_code if user else "?",
            quadrant=r.quadrant.value,
            valence=r.valence,
            arousal=r.arousal,
            timestamp=r.timestamp,
            turns=[{
                "turn_index": t.turn_index,
                "speaker": t.speaker.value,
                "message_text": t.message_text,
                "timestamp": t.timestamp.isoformat(),
            } for t in turns],
            flagged=flagged,
        ))

    return items


@router.get("/export/csv")
async def export_csv(
    db: AsyncSession = Depends(get_db),
    anonymize: bool = Query(True),
):
    """구조화 측정 자료 CSV 다운로드. 사양서 5항.

    정동 좌표, 감정 단어, 강도, 응답 시간, 분기 개입 응답 통합 CSV.
    """
    result = await db.execute(select(AffectRecord).order_by(AffectRecord.timestamp))
    records = list(result.scalars().all())

    # 결합용 lookup
    if records:
        rec_ids = [r.record_id for r in records]
        er = await db.execute(
            select(EmotionRecord).where(EmotionRecord.record_id.in_(rec_ids))
        )
        emotions = {e.record_id: e for e in er.scalars().all()}
        ir = await db.execute(
            select(InterventionResponse).where(
                InterventionResponse.record_id.in_(rec_ids)
            )
        )
        interventions = {i.record_id: i for i in ir.scalars().all()}
        uids = list({r.user_id for r in records})
        ur = await db.execute(select(User).where(User.user_id.in_(uids)))
        users = {u.user_id: u for u in ur.scalars().all()}
    else:
        emotions, interventions, users = {}, {}, {}

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "participant_code", "real_name", "record_id", "timestamp",
        "valence", "arousal", "quadrant", "mode", "is_practice",
        "duration_window_minutes", "response_latency_ms", "prompt_id",
        "selected_word", "intensity", "exploration_path",
        "intervention_type", "intervention_text",
    ])
    for r in records:
        u = users.get(r.user_id)
        name = mask_real_name(u.real_name) if (u and anonymize) else (u.real_name if u else "")
        em = emotions.get(r.record_id)
        iv = interventions.get(r.record_id)
        writer.writerow([
            u.participant_code if u else "",
            name,
            str(r.record_id),
            r.timestamp.isoformat(),
            r.valence, r.arousal, r.quadrant.value, r.mode.value,
            r.is_practice, r.duration_window_minutes,
            r.response_latency_ms or "", r.prompt_id or "",
            em.selected_word if em else "",
            em.intensity if em else "",
            "|".join(em.exploration_path) if em and em.exploration_path else "",
            iv.intervention_type.value if iv else "",
            iv.user_response_text if iv else "",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=affect_data_{datetime.now().strftime('%Y%m%d')}.csv",
        },
    )


@router.get("/export/dialogues.json")
async def export_dialogues(
    db: AsyncSession = Depends(get_db),
    anonymize: bool = Query(True),
):
    """대화 로그 JSON 다운로드. 사양서 5항."""
    result = await db.execute(
        select(AgentDialogue).order_by(AgentDialogue.record_id, AgentDialogue.turn_index)
    )
    turns = list(result.scalars().all())

    # 기록 + 사용자 lookup
    rec_ids = list({t.record_id for t in turns})
    if rec_ids:
        rr = await db.execute(select(AffectRecord).where(AffectRecord.record_id.in_(rec_ids)))
        records_map = {r.record_id: r for r in rr.scalars().all()}
        uids = list({r.user_id for r in records_map.values()})
        ur = await db.execute(select(User).where(User.user_id.in_(uids)))
        users_map = {u.user_id: u for u in ur.scalars().all()}
    else:
        records_map, users_map = {}, {}

    # 기록 단위로 그룹핑
    by_record = {}
    for t in turns:
        by_record.setdefault(t.record_id, []).append({
            "turn_index": t.turn_index,
            "speaker": t.speaker.value,
            "message_text": t.message_text,
            "timestamp": t.timestamp.isoformat(),
        })

    export = []
    for rid, ts in by_record.items():
        rec = records_map.get(rid)
        user = users_map.get(rec.user_id) if rec else None
        export.append({
            "participant_code": user.participant_code if user else None,
            "real_name": (mask_real_name(user.real_name) if (user and anonymize)
                          else (user.real_name if user else None)),
            "record_id": str(rid),
            "valence": rec.valence if rec else None,
            "arousal": rec.arousal if rec else None,
            "quadrant": rec.quadrant.value if rec else None,
            "timestamp": rec.timestamp.isoformat() if rec else None,
            "turns": ts,
        })

    body = json.dumps(export, ensure_ascii=False, indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=dialogues_{datetime.now().strftime('%Y%m%d')}.json",
        },
    )
