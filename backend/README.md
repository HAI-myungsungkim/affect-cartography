# Affect Cartography Pilot — Backend (1단계)

KAIST 학생 정신건강 파일럿 연구용 FastAPI 백엔드.

## 현재 상태: 1단계 완료 ✅

- FastAPI + PostgreSQL 골격 구축
- 전체 8개 테이블 ORM 모델 (점/궤도 모드 지원 포함)
- JWT + 디바이스 ID **엄격** 바인딩 인증
- 사용자/관리자 로그인 API
- 위기 자원 엔드포인트 (1393, KAIST 상담센터)
- Alembic 초기 마이그레이션
- 15개 테스트 전부 통과

## 빠른 실행

### 로컬 (Docker)
```bash
cp .env.example .env
docker-compose up -d
# 초기 마이그레이션은 컨테이너 시작 시 자동 실행
docker exec affect_app python -m scripts.seed_users
```

API 문서: http://localhost:8000/docs

### 로컬 (Python 직접 실행)
```bash
pip install -r requirements.txt
cp .env.example .env
# PostgreSQL 별도 실행 후
alembic upgrade head
python -m scripts.seed_users
uvicorn app.main:app --reload
```

### 테스트
```bash
pytest tests/ -v
```

## 디렉토리 구조

```
backend/
├── app/
│   ├── api/          # 라우터 (auth, health, ...)
│   ├── core/         # config, database, security
│   ├── models/       # SQLAlchemy ORM 모델 (8개 테이블)
│   ├── schemas/      # Pydantic 요청/응답
│   └── main.py       # FastAPI 진입점
├── alembic/          # DB 마이그레이션
├── scripts/          # 시드 스크립트
├── tests/            # pytest
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## 데이터 모델 (8개 테이블)

| 테이블 | 역할 | 사양서 |
|---|---|---|
| `users` | 피험자, 디바이스 바인딩, 알림 시간대 3구간 | 9항 |
| `affect_records` | 정동 좌표 + **점/궤도 모드 통합** | 4.3.4 |
| `emotion_records` | 최종 감정 단어 + 강도 + 탐색 경로 | 4.7 |
| `emotion_dictionary` | 한국어 감정 단어 사전 (60~80개) | 6항 |
| `agent_dialogues` | LLM 대화 턴 로그 | 4.4 |
| `intervention_responses` | 분기 개입 응답 | 4.8 |
| `safety_flags` | 자살/자해 키워드 안전 플래그 | 10항 |
| `admin_settings` | 공지, 알림 정책 키-값 | 5항 |

## 핵심 보안 정책

- **엄격 디바이스 바인딩**: 첫 로그인 시 device_id 바인딩, 다른 기기 진입은 무조건 401, 관리자 수동 해제만 가능
- **디바이스 ID는 SHA-256 해시 저장** (평문 X)
- **JWT 토큰에 device_id 포함**, 매 요청 헤더 `X-Device-Id`와 이중 검증
- **실명 마스킹** 헬퍼: `김철수 → 김○○` (다운로드 시 익명화 옵션)
- OpenAI **Zero Data Retention** 옵션 설정 가능

## 다음 단계

→ **2단계**: Flutter 앱 골격 + 로그인 화면 + 디바이스 ID 바인딩
→ **3단계**: V-A grid 정동 기록 (점 + 궤도 모드)
