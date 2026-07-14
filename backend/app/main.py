"""FastAPI 애플리케이션 진입점."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    admin, affect, agent, auth, dashboard, emotion, health,
    intervention, notification, observation,
)
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 초기화 작업 (필요 시 DB 연결 확인 등)
    yield
    # 종료 시 정리 작업


app = FastAPI(
    title=settings.app_name,
    description=(
        "KAIST 학생 정신건강 파일럿 연구용 API. "
        "정동(affect) → 감정 단어 분화 훈련 및 마이크로 개입."
    ),
    version="0.1.0",
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
    lifespan=lifespan,
)

# CORS — 관리자 대시보드(Next.js) 및 Flutter 앱 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(affect.router)
app.include_router(observation.router)
app.include_router(emotion.router)
app.include_router(agent.router)
app.include_router(intervention.router)
app.include_router(dashboard.router)
app.include_router(notification.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs" if settings.app_debug else "disabled",
    }
