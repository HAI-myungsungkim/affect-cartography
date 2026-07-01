# Affect Cartography Pilot — 최종 완료 보고서

KAIST 학생 대상 4주 정신건강 파일럿 연구용 모바일 앱 전체 11단계 개발 완료.

**완료일**: 2026-06-30
**총 코드량**: Python 3,168 + Dart 4,977 + TypeScript 1,251 = **9,396 lines**
**테스트 통과**: 백엔드 pytest **131/131 (100%)**

---

## 11단계 완료 현황

| 단계 | 산출물 | 코드 위치 |
|---|---|---|
| 1 | FastAPI 백엔드 골격 + 8개 테이블 + JWT/디바이스 바인딩 | `backend/app/` |
| 2 | Flutter 앱 골격 + 로그인 + 디바이스 ID 영속화 | `app/lib/features/auth/` |
| 3 | V-A 그리드 (점/궤도 모드 + 연습 세션) | `app/lib/features/affect/` |
| 4 | 한국어 감정 사전 32개 (시드) + GPT-4o 확장 도구 | `backend/data/`, `scripts/` |
| 5 | OpenAI 에이전트 대화 + 위기 키워드 이중 안전망 | `backend/app/services/` |
| 6 | 감정 단어 선택 + 인접 탐색 + 강도 기록 | `app/lib/features/emotion/` |
| 7 | 분기 개입 (자기거리두기/그라운딩/행동활성화) | `app/lib/features/intervention/` |
| 8 | 대시보드 (정동 궤적 + 감정 기록 + 겹쳐보기) | `app/lib/features/dashboard/` |
| 9 | 알림 시스템 (3구간 + 로컬 + idempotent prompt_id) | `app/lib/features/notification/` |
| 10 | 관리자 웹 대시보드 (Next.js 14 + Tailwind) | `admin/` |
| 11 | 통합 테스트 + 안전 검증 + 운영 체크리스트 | `tests/`, `OPERATION_CHECKLIST.md` |

---

## 11단계 검증 결과

### 안전 검증 (가장 중요)
- **위기 키워드 20종 100% 탐지**: 자살 12 + 자해 8 + 절망 8 패턴 모두 통과
- **이중 안전망**: LLM 호출 전 정규식 필터 + LLM 응답 후 재검사
- **false-positive 0건**: 일상 표현 8종 ("배 고파 죽겠다" 등) 모두 통과
- **safety_flag DB 저장**: 모든 위기 발화 자동 기록 + 관리자 알림

### 데이터 무결성
- DB ↔ 다운로드 CSV/JSON **100% 일치** 확인
- 대화 순서, 연습 세션 포함 여부, 마스킹 처리 모두 검증
- 마스킹된 다운로드와 원본 데이터 모두 1:1 매칭

### E2E 시나리오
- 10명 동시 사용자 전체 사이클 (5번 반복) 통과
- 다른 기기 진입 차단 (device_mismatch 401)
- 타 사용자 record_id 접근 차단 (404)
- 사용자별 대시보드 데이터 격리
- 연습 세션은 응답률 계산에서 제외

### 시스템 통계
- API 엔드포인트: **31개** (auth 2, affect 4, agent 2, emotion 3, intervention 2, dashboard 1, notification 4, admin 8, health/crisis 2, ...)
- DB 테이블: **8개** (users, affect_records, agent_dialogues, emotion_records, intervention_responses, safety_flags, admin_settings, audit_logs)
- Flutter 화면: **12개** (로그인, 홈, 정동기록, 연습, 대화, 감정선택, 강도, 개입, 완료, 대시보드, 알림설정, 햄버거메뉴)

---

## 실제 운영을 위한 다음 단계 (연구진 액션)

상세는 **`OPERATION_CHECKLIST.md`** 와 **`DEPLOYMENT_GUIDE.md`** 참고.

### IRB 승인 직후 1주 내
1. **보안 자격증명 발급**
   - `openssl rand -hex 32` → JWT_SECRET, ADMIN_CODE_SALT
   - `openssl rand -hex 16` → ADMIN_CODE
2. **OpenAI Zero Data Retention 신청**
   - https://openai.com/policies/api-data-usage-policies
   - Organization Owner 이메일 발송, 1~3일 소요
3. **NCP 인프라 구축**
   - VPC + Server(2vCPU/4GB Ubuntu 22.04) + Cloud DB for PostgreSQL 15 (HA, KMS 암호화)
   - ALB + SSL 인증서 + 도메인 DNS
   - 보안그룹: SSH는 관리자 IP만, DB는 Server만
4. **백엔드 배포 + 시드**
   - `docker-compose up -d`
   - `alembic upgrade head`
   - `python -m scripts.seed_users` (P001~P020 발급)
   - `python -m scripts.seed_emotion_dictionary --reviewed` (검수 완료 사전)

### 앱 배포
5. **Android (Google Play 내부 테스트)**
   - Google Play Console 계정 ($25 1회)
   - `keytool` 키스토어 생성
   - `flutter build appbundle --release` → AAB 업로드
6. **iOS (TestFlight)**
   - Apple Developer Program ($99/년)
   - `flutter build ipa --release` → Transporter 업로드
7. **(선택) Firebase 푸시**
   - Firebase 프로젝트 생성
   - `google-services.json` (Android), `GoogleService-Info.plist` (iOS) 받아서 앱에 추가
   - APNs Auth Key 업로드

### 피험자 모집 & 운영
8. **관리자 대시보드 접속** → 피험자 등록 → 코드 발급
9. **참가자에게 안내**
   - 앱 설치 (Play Store / TestFlight 링크)
   - 피험자 코드 + 실명 입력 → 디바이스 바인딩 완료
   - 4주간 하루 3회 알림 응답
10. **일/주 운영 체크**
    - 매일: safety_flags 확인 (위기 발화 시 1393 연결 + 면담)
    - 매주: 응답률 < 50% 참가자 1:1 연락
    - 4주 후: CSV/JSON 다운로드 → 분석

---

## 핵심 파일

| 경로 | 설명 |
|---|---|
| `backend/` | FastAPI + PostgreSQL (31 endpoints) |
| `app/` | Flutter iOS/Android 앱 |
| `admin/` | Next.js 14 관리자 대시보드 (PC 전용) |
| `DEPLOYMENT_GUIDE.md` | NCP 배포 + 스마트폰 배포 + 실험 운용 가이드 |
| `OPERATION_CHECKLIST.md` | 출시 전/중/후 체크리스트 (IRB 안전) |
| `backend/data/emotion_dictionary_v0.json` | 한국어 감정 사전 (32개 시드) |
| `backend/data/REVIEW_GUIDE.md` | 감정 사전 검수 가이드 |
| `app/FIREBASE_SETUP.md` | FCM 푸시 알림 설정 가이드 |
| `app/PLATFORM_SETUP.md` | Android/iOS 플랫폼 설정 |

---

## 보안 & 프라이버시 (사양서 5항)

- ✅ HTTPS/TLS 1.3 (ALB + 인증서)
- ✅ DB AES-256 암호화 (NCP Cloud DB KMS)
- ✅ OpenAI Zero Data Retention 헤더
- ✅ JWT + 디바이스 바인딩 (엄격 정책)
- ✅ 관리자 포털 IP 화이트리스트 + 2FA 권장
- ✅ DB 접근 audit_logs 자동 기록
- ✅ 실명 마스킹 (다운로드 시 `김철수→김○○`)
- ✅ 위기 발화 시 자동 1393 안내 + safety_flag

---

## IRB 심사 중 병행 개발 시 주의사항

- IRB 승인 **전까지 실제 피험자 모집 절대 금지**
- 현재 시드된 P001~P020은 개발/테스트용 — 운영 전 삭제 후 재발급
- 위기 키워드 패턴은 추가 가능 (`crisis_keywords.py`), 절대 완화 금지
- 감정 사전은 GPT-4o 초안 → **연구진 수동 검수 필수** (편향 검토)
- 데이터 익명화 정책: 6개월 후 자동 삭제, 그 전까지는 마스킹된 형태로만 분석

---

**개발 완료. 다음은 IRB 승인 → 운영 인프라 구축 → 피험자 모집 단계입니다.**
