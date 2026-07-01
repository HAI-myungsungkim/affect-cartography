"""JWT 토큰 생성/검증 및 디바이스 ID 해시."""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(
    subject: str,
    device_id: str,
    is_admin: bool = False,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """JWT 액세스 토큰 생성. subject=user_id, device_id 바인딩."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "device_id": device_id,
        "is_admin": is_admin,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[dict]:
    """JWT 토큰 디코드. 만료/위변조 시 None."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def hash_device_id(device_id: str) -> str:
    """디바이스 ID는 평문 저장하지 않고 SHA-256 해시."""
    salted = f"{device_id}:{settings.admin_code_salt}"
    return hashlib.sha256(salted.encode("utf-8")).hexdigest()


def mask_real_name(name: str) -> str:
    """실명 마스킹: '김철수' → '김○○', '이영' → '이○'."""
    if not name:
        return ""
    if len(name) <= 1:
        return name
    return name[0] + "○" * (len(name) - 1)
