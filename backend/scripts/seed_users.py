"""파일럿 사용자 시드 — 관리자가 발급한 피험자 코드를 미리 등록.

사용법:
    python -m scripts.seed_users

IRB 승인 전에는 더미 코드만 생성 (P001~P020).
실명은 비워두고 첫 로그인 시 사용자가 직접 입력.
"""
import asyncio

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserStatus, RecordMode


DUMMY_CODES = [f"P{i:03d}" for i in range(1, 21)]


async def seed():
    async with AsyncSessionLocal() as db:
        for code in DUMMY_CODES:
            existing = await db.execute(
                select(User).where(User.participant_code == code)
            )
            if existing.scalar_one_or_none():
                print(f"  [skip] {code} 이미 존재")
                continue
            user = User(
                participant_code=code,
                real_name="",  # 첫 로그인 시 사용자가 입력
                device_id_hash=None,
                record_mode=RecordMode.POINT,
                status=UserStatus.ACTIVE,
            )
            db.add(user)
            print(f"  [add ] {code}")
        await db.commit()
    print(f"\n총 {len(DUMMY_CODES)}개 더미 피험자 코드 시드 완료.")


if __name__ == "__main__":
    asyncio.run(seed())
