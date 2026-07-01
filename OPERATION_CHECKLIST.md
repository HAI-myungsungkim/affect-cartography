# 운영 배포 체크리스트 — Affect Cartography Pilot

**연구진/관리자가 실제 피험자 모집 전에 따라가야 하는 순차 체크리스트.**

각 항목은 IRB 안전 + 데이터 무결성 + 시스템 안정성 보장에 필수입니다.

---

## A. 출시 전 (IRB 승인 직후, 첫 피험자 모집 1주 전)

### A-1. 보안 자격증명 발급
- [ ] **JWT 시크릿** 생성: `openssl rand -hex 32` → 백엔드 `.env`의 `JWT_SECRET`
- [ ] **관리자 코드** 생성: `openssl rand -hex 16` → `.env`의 `ADMIN_CODE`
  - 기본값 `change-me`로 절대 운영 금지
  - 강한 무작위 문자열로 변경
- [ ] **소금값** 생성: `openssl rand -hex 16` → `.env`의 `ADMIN_CODE_SALT`
- [ ] **데이터베이스 비밀번호** 강한 무작위로 변경

### A-2. OpenAI 운영 키 + ZDR
- [ ] OpenAI Platform에서 운영 API 키 발급 (개발용과 분리)
- [ ] **Zero Data Retention** 신청
  - URL: https://openai.com/policies/api-data-usage-policies
  - Organization Owner가 이메일로 신청 (보통 1~3일 소요)
  - 승인 회신을 IRB 자료에 첨부
- [ ] `.env`의 `OPENAI_API_KEY`에 운영 키 설정
- [ ] `OPENAI_ZERO_DATA_RETENTION=true` 확인

### A-3. NCP 배포
- [ ] NCP 콘솔에서 다음 리소스 생성:
  - [ ] VPC + Subnet (Public/Private 분리)
  - [ ] Server 인스턴스 (Standard 2vCPU 4GB Ubuntu 22.04)
  - [ ] Cloud DB for PostgreSQL 15 (HA, 자동 백업 1일, 7일 보관)
  - [ ] Object Storage 버킷 (다운로드 파일 저장)
  - [ ] Application LB + SSL 인증서
- [ ] 도메인 + DNS A 레코드 → ALB
- [ ] 보안 그룹(ACG):
  - [ ] Server 22번 포트는 **관리자 IP만**
  - [ ] Server 8000번 포트는 **ALB에서만**
  - [ ] DB 5432는 **Server에서만**
- [ ] Cloud DB의 at-rest 암호화(KMS) **활성화 확인**
- [ ] HTTPS만 허용 (HTTP → HTTPS 리다이렉트)

### A-4. 백엔드 마이그레이션 + 시드
- [ ] `alembic upgrade head` (스키마 생성)
- [ ] `python -m scripts.seed_users` (피험자 코드 P001~P020 시드)
- [ ] `python -m scripts.seed_emotion_dictionary --reset --reviewed` (감정 사전 시드)
  - ⚠️ **연구진이 검수한 사전 파일로 시드**해야 함 (사양서 6항)
- [ ] `/health` 응답 확인: `curl https://api.<your-domain>/health`

### A-5. 관리자 대시보드 배포
- [ ] `admin/.env.local`에 `NEXT_PUBLIC_API_BASE_URL=https://api.<your-domain>` 설정
- [ ] `npm run build && npm start`
- [ ] 또는 Vercel/NCP에 배포
- [ ] **IP 화이트리스트** 적용 (nginx/ALB 설정)
  - KAIST 캠퍼스 또는 연구실 고정 IP만
- [ ] 관리자 코드로 로그인 테스트

### A-6. 운영 시점 검증 항목
- [ ] `pytest tests/` → 131/131 통과 (운영 직전 한 번 더)
- [ ] 위기 키워드 20개 시뮬레이션: `pytest tests/test_crisis_20_keywords.py`
- [ ] 다운로드 정합성: `pytest tests/test_export_integrity.py`

---

## B. 피험자 모집 단계

### B-1. 모집 공고 시
- [ ] IRB 승인서 사본 보관
- [ ] 디지털 동의서 → 자필 서명 또는 전자 서명 시스템 (별도 도구)
- [ ] **모집 공고에 다음 명시**:
  - 4주 파일럿 연구
  - 하루 3회 알림
  - LLM 기반 대화 포함
  - 데이터 보존 6개월 후 익명화
  - 위기 자원(1393, KAIST 학생상담센터)
  - 연구 종료 절차

### B-2. 신청자별 절차
1. [ ] 신청자가 동의서 서명 완료
2. [ ] 관리자 대시보드 → **새 피험자 코드 발급** (예: P021)
3. [ ] 신청자에게 이메일로 전달:
   - 피험자 코드 (예: P021)
   - 앱 설치 링크 (Google Play 내부 테스트 / TestFlight)
   - 연구 안내문 + 위기 자원 카드 첨부
4. [ ] 신청자가 앱 첫 로그인 → 디바이스 자동 바인딩
5. [ ] 관리자 대시보드에서 첫 로그인 시각 확인

---

## C. 운영 중 (매일/주간)

### C-1. 매일
- [ ] **안전 플래그 검토** (관리자 대시보드 `/safety`)
  - 미검토 플래그 있으면 24시간 내 검토
  - 위기 카테고리(`suicide_ideation`/`self_harm`)는 **즉시**
- [ ] 응답률 모니터링 (`/users` 응답률 배지)
- [ ] 백엔드 서버 헬스 (NCP Cloud Insight)

### C-2. 위기 상황 발생 시 4단계 프로토콜
1. **즉시 (자동)**: 앱이 "1393" 표준 메시지 출력 + 대화 종료
2. **수 분 이내 (운영자)**: 알람 수신 → 대시보드에서 해당 사용자 확인
3. **24시간 이내 (연구진)**: 피험자에게 직접 연락 + KAIST 상담센터 연계 권유
4. **사후 (IRB)**: 위기 사례 발생 보고서 작성 → IRB 보고

### C-3. 주 1회
- [ ] **대화 감사** (관리자 대시보드 `/audit`)
  - 최근 20개 표본 검토
  - 부적절한 LLM 응답 있으면 플래그 + 기록
- [ ] 응답률 낮은 사용자 (30% 미만) → 직접 연락
- [ ] 디바이스 변경 요청 처리 (`/users/[id]` 디바이스 해제)

### C-4. 운영 이슈 트러블슈팅

| 증상 | 원인 | 해결 |
|---|---|---|
| 피험자가 "등록되지 않은 코드" | 코드 미발급 또는 오타 | 관리자 대시보드에서 발급 확인 |
| "이 코드는 다른 기기에 등록" | 앱 재설치/기기 변경 | `/users/[id]` 디바이스 바인딩 해제 |
| 알림이 안 옴 | iOS 알림 권한 거부 / Android 배터리 최적화 | 피험자에게 OS 설정 안내 |
| OpenAI 429 (rate limit) | 동시 사용자 폭증 | OpenAI Tier 상향 또는 백오프 |
| 백엔드 5xx 빈발 | DB 연결 풀 고갈 | Server 사양 상향, 풀 크기 조정 |
| 대시보드 접근 안 됨 | IP 화이트리스트 외부 | VPN 또는 화이트리스트 IP 추가 |

---

## D. 연구 종료 후

### D-1. 데이터 회수 (4주 완료 시)
- [ ] 모든 피험자에게 종료 안내 + 감사 인사
- [ ] 관리자 대시보드 `/export`에서:
  - [ ] CSV 다운로드 (익명화 ON)
  - [ ] JSON 대화 로그 다운로드 (익명화 ON)
- [ ] 다운로드 파일을 분석 환경(연구실 PC)으로 전송
- [ ] 다운로드 로그를 IRB 기록에 보관

### D-2. 데이터 분석 (다운로드 ~ 6개월)
- 익명화 데이터로 분석 진행
- 분석 결과 논문/보고서 작성
- 6개월 안에 다음 보존 정책 적용 결정

### D-3. 6개월 후 (보존 정책 적용)
- [ ] NCP Cloud DB에서:
  ```sql
  TRUNCATE TABLE agent_dialogues CASCADE;
  UPDATE users SET real_name = NULL, device_id_hash = NULL;
  ```
- [ ] 익명화된 분석셋(.csv)만 별도 백업 디스크에 보관
- [ ] 삭제 완료 보고서 → IRB에 종료 보고서 제출

---

## E. 부록 — 응급 연락처

연구 운영 중 다음 상황에서 즉시 연락:

- **피험자 위기 발생**: 자살예방상담전화 **1393**, KAIST 학생상담센터 **042-350-2181**
- **시스템 장애**: 개발팀 (별도)
- **IRB 보고**: KAIST IRB 사무국
- **OpenAI 장애**: https://status.openai.com

---

**이 체크리스트는 사양서 5/8/10/12항을 기반으로 작성되었으며, 운영 시점에 추가 항목이 발생하면 갱신해주세요.**
