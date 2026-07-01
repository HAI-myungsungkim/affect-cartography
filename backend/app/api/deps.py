"""FastAPI 공통 의존성 — 현재 사용자, 관리자 권한 등."""
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import decode_access_token, hash_device_id
from app.models.user import User

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    x_device_id: Annotated[str | None, Header(alias="X-Device-Id")] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT + 디바이스 ID 이중 검증. 엄격 바인딩 정책 강제."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 필요합니다",
        )
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 토큰입니다",
        )
    user_id = payload.get("sub")
    token_device = payload.get("device_id")
    if not user_id or not token_device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰 형식 오류",
        )

    # 디바이스 ID 헤더 강제 검증 (엄격 바인딩)
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="디바이스 식별자가 필요합니다",
        )
    if hash_device_id(x_device_id) != token_device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이 토큰은 다른 기기에 바인딩되어 있습니다",
        )

    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="토큰 형식 오류")
    result = await db.execute(select(User).where(User.user_id == user_uuid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="사용자를 찾을 수 없습니다",
        )
    # DB에 저장된 device_id_hash와도 재확인
    if user.device_id_hash != hash_device_id(x_device_id):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이 코드는 다른 기기에 등록되어 있습니다. 연구진에게 문의하세요",
        )
    return user


async def get_admin_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    """관리자 전용 의존성. is_admin=true 토큰만 통과."""
    if not credentials:
        raise HTTPException(status_code=401, detail="관리자 인증이 필요합니다")
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("is_admin"):
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다")
    return payload
