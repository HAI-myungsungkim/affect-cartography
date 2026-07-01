"""인증 라우터 — 사용자/관리자 로그인. 사양서 4.1."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_device_id
from app.models.user import User, UserStatus
from app.schemas.auth import (
    AdminLoginRequest,
    LoginErrorCode,
    LoginRequest,
    LoginResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """사용자 로그인. 엄격 디바이스 바인딩 정책.
    
    - 코드가 미등록 → 401 + code_not_registered
    - 첫 로그인 → 디바이스 ID 바인딩, 토큰 발급
    - 같은 기기 재진입 → 토큰 재발급
    - 다른 기기 진입 → 401 + device_mismatch (관리자 수동 해제만 가능)
    """
    result = await db.execute(
        select(User).where(User.participant_code == req.participant_code)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": LoginErrorCode.CODE_NOT_REGISTERED,
                "message": "등록되지 않은 코드입니다",
            },
        )

    if user.status == UserStatus.DROPPED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": LoginErrorCode.USER_DROPPED,
                "message": "연구 참여가 종료된 계정입니다",
            },
        )

    incoming_hash = hash_device_id(req.device_id)
    first_login = False

    if user.device_id_hash is None:
        # 첫 로그인 — 디바이스 바인딩
        user.device_id_hash = incoming_hash
        user.first_login_at = datetime.now(timezone.utc)
        first_login = True
        await db.flush()
    elif user.device_id_hash != incoming_hash:
        # 다른 기기 — 엄격 정책: 무조건 차단
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": LoginErrorCode.DEVICE_MISMATCH,
                "message": "이 코드는 다른 기기에 등록되어 있습니다. 연구진에게 문의하세요",
            },
        )

    # 실명 업데이트 (첫 로그인 시 비어있을 수 있음 — 관리자가 코드만 발급한 경우)
    if first_login or not user.real_name:
        user.real_name = req.real_name

    token = create_access_token(
        subject=str(user.user_id),
        device_id=incoming_hash,
        is_admin=False,
    )

    return LoginResponse(
        access_token=token,
        user_id=str(user.user_id),
        participant_code=user.participant_code,
        real_name=user.real_name,
        record_mode=user.record_mode.value,
        trajectory_practice_done=user.trajectory_practice_done,
        first_login=first_login,
    )


@router.post("/admin/login")
async def admin_login(req: AdminLoginRequest):
    """관리자 로그인. 사양서 4.1 하단.
    
    PC 웹 대시보드용. 모바일에서는 일부 읽기 기능만 제공.
    """
    if req.admin_code != settings.admin_code:
        raise HTTPException(status_code=401, detail="관리자 코드가 올바르지 않습니다")

    token = create_access_token(
        subject="admin",
        device_id=hash_device_id(req.device_id),
        is_admin=True,
    )
    return {"access_token": token, "token_type": "bearer", "is_admin": True}
