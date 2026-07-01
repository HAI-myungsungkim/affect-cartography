# Affect Cartography Pilot

KAIST 학생 대상 4주 정신건강 파일럿 연구용 모바일 앱.

사용자가 자신의 감정을 말하기 전에 **정동(affect)을 2차원 좌표(valence × arousal)로 먼저 기록**하고, AI 에이전트와의 짧은 대화를 거쳐 감정 단어로 해석하도록 돕는다. 이 과정에서 자기거리두기(self-distancing) 또는 행동활성화(behavioral activation) 마이크로 개입을 받는다.

> 단순 기분 기록 앱이 아닌, **emotion granularity 훈련을 위한 교육적 도구**.

## 디렉토리 구조

```
affect-cartography/
├── backend/           # FastAPI + PostgreSQL — 1단계 완료
├── app/               # Flutter (iOS/Android) — 2단계 완료
├── README.md          # ← 이 파일
└── DEPLOYMENT_GUIDE.md  # 실제 피험자 스마트폰까지의 배포·운용 가이드
```

## 개발 진행 상황

| 단계 | 내용 | 상태 |
|---|---|---|
| 1 | 백엔드 골격 (FastAPI + PostgreSQL + 8개 테이블 + JWT/디바이스 바인딩) | ✅ 완료 |
| 2 | Flutter 앱 골격 + 로그인 화면 + 디바이스 ID 영속화 | ✅ 완료 |
| 3 | V-A grid 정동 기록 (점 모드 + 궤도 모드 + 연습 세션) | ✅ 완료 |
| 4 | 한국어 감정 단어 사전 (시드 32개 + GPT-4o 확장 도구) | ✅ 완료 |
| 5 | OpenAI 에이전트 대화 (시스템 프롬프트 + 위기 키워드 탐지) | ✅ 완료 |
| 6 | 감정 단어 선택 + 인접 단어 탐색 + 강도 기록 | ✅ 완료 |
| 7 | 분기 개입 (자기거리두기 / 그라운딩 / 행동활성화) | ✅ 완료 |
| 8 | 대시보드 (정동 궤적 + 감정 기록 + 겹쳐보기) | ✅ 완료 |
| 9 | 알림 시스템 (시간대 3구간 + 로컬 알림, FCM은 별도 설정) | ✅ 완료 |
| 10 | 관리자 웹 대시보드 (Next.js) | ✅ 완료 |
| 11 | 통합 테스트 + 안전 절차 검증 + 운영 체크리스트 | ✅ 완료 |

**🎉 전체 11단계 개발 완료 (2026-06-30)**

- 백엔드 테스트: **131 passed** (FastAPI 31 endpoints, 8 tables)
- Python: ~3,168 lines / Dart: ~4,977 lines / TypeScript: ~1,251 lines
- 위기 키워드 20종 100% 탐지, 데이터 무결성 검증, E2E 통합 시나리오 통과

## 빠른 시작

### 1. 백엔드 기동
```bash
cd backend
cp .env.example .env
docker-compose up -d
docker exec affect_app python -m scripts.seed_users
# → http://localhost:8000/docs
```

### 2. 앱 실행
```bash
cd app
cp .env.example .env
flutter pub get
flutter run
```

### 3. 검증
- 피험자 코드 `P001` + 임의 실명 입력 → 홈 화면 진입
- 자세한 검증 시나리오는 각 디렉토리의 README.md 참고

## 실제 운용을 위한 가이드

**[📘 DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** 에 다음 5단계가 모두 정리되어 있다.

1. 개발자 PC에서의 로컬 동작 확인
2. KAIST 캠퍼스 Wi-Fi 환경 사내 베타 테스트
3. **NCP(네이버 클라우드)에 백엔드 배포** (VPC, Cloud DB, ALB+SSL, 보안 그룹)
4. **피험자 스마트폰에 앱 설치** (Android: Play 내부 테스트 / iOS: TestFlight)
5. **실험 운용 워크플로우** (모집 → 코드 발급 → 데이터 회수 → IRB 보고)

위기 상황 대응 프로토콜, 데이터 보존·삭제 절차, 운영 이슈 트러블슈팅, 최종 보안 체크리스트 포함.

## 사양서 준수

- 사양서 11개 섹션 전부 반영
- 점 모드 / 궤도 모드 이원화 (4.3.1~4.3.6) — DB 스키마 완료, UI는 3단계에서
- 엄격 디바이스 바인딩 정책 (사용자 결정)
- 위기 자원(1393, KAIST 상담센터, 1577-0199) 햄버거 메뉴 상시 노출
- OpenAI Zero Data Retention 옵션 환경변수 분리
- 실명 마스킹 헬퍼 (`김철수 → 김○○`)

## 라이선스 / IRB

본 프로젝트는 KAIST IRB **심사 중**이며, 승인 전에는 실제 피험자 모집·실명 수집·실제 데이터 저장이 금지된다. 개발은 더미 데이터(P001~P020)로 진행한다.
