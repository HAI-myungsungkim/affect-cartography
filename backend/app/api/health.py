"""헬스체크 + 위기 자원 안내. 항상 노출."""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
    }


@router.get("/crisis-resources")
async def crisis_resources():
    """위기 자원 — 햄버거 메뉴 등에서 항상 접근 가능. 사양서 4.2, 4.10."""
    return {
        "resources": [
            {
                "name": "자살예방상담전화",
                "phone": settings.crisis_hotline,
                "available": "24시간",
            },
            {
                "name": "KAIST 학생상담센터",
                "phone": settings.kaist_counseling,
                "available": "평일 09:00–18:00",
            },
            {
                "name": "정신건강복지센터",
                "phone": "1577-0199",
                "available": "24시간",
            },
        ]
    }
