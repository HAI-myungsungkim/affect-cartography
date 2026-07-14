"""개발용 DB 초기화 — 모델에서 직접 테이블 생성 (create_all).

개발 초기 단계에서 alembic 마이그레이션 대신 사용한다.
SQLAlchemy가 enum을 checkfirst로 처리하므로 중복 타입 충돌이 없다.

⚠️ 배포 전 복귀 지점:
    실제 참가자 데이터가 쌓이기 시작하면 이 방식을 버리고 alembic으로
    돌아가야 한다. (컬럼 추가 시 데이터 보존이 필요하기 때문)
    그때는 docker-compose.yml의 command를 다시 'alembic upgrade head'로
    바꾸고, alembic/versions의 마이그레이션을 최신 모델 기준으로 재생성한다.
"""
import asyncio

from app.core.database import Base, engine
# 모든 모델을 import 해야 metadata에 등록됨
from app import models  # noqa: F401


async def init() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[init_db] 모든 테이블 생성 완료 (create_all)")


if __name__ == "__main__":
    asyncio.run(init())
