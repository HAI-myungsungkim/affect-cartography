"""인증 관련 Pydantic 스키마."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """사용자 로그인. 사양서 4.1."""
    participant_code: str = Field(..., min_length=2, max_length=32, description="피험자 코드 (예: P001)")
    real_name: str = Field(..., min_length=1, max_length=64, description="실명")
    device_id: str = Field(..., min_length=8, max_length=256, description="디바이스 고유 ID")


class AdminLoginRequest(BaseModel):
    admin_code: str = Field(..., min_length=4, max_length=128)
    device_id: str = Field(..., min_length=8, max_length=256)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    participant_code: str
    real_name: str
    # ---- 실험 조건 배정 (블라인드: 값만 내려주고 군 이름은 표시하지 않음) ----
    record_mode: str          # 축2: point / trajectory
    observation_mode: str     # 축1: self_only / recall_other / scenario_other
    emotion_timing: str       # 축3: immediate / delayed
    agent_mode: str           # 축4: none / enabled
    education_enabled: bool    # 교육자료 노출 여부
    trajectory_practice_done: bool
    first_login: bool = False


class LoginErrorCode:
    """로그인 실패 상세 코드. 사양서 4.1."""
    CODE_NOT_REGISTERED = "code_not_registered"  # 등록되지 않은 코드
    DEVICE_MISMATCH = "device_mismatch"  # 다른 기기에 바인딩됨
    USER_DROPPED = "user_dropped"  # 탈퇴/종료 상태
