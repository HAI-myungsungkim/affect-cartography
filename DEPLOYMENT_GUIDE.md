# 배포 및 운용 가이드 — 개발 PC에서 피험자 스마트폰까지

이 문서는 개발된 백엔드와 Flutter 앱을 **실제 KAIST 학생 피험자의 스마트폰에 설치하고 연구를 운용**하는 전 과정을 다룬다.

문서 구조는 다음 5단계이다.
1. 개발자 PC에서의 로컬 동작 확인
2. KAIST 캠퍼스 Wi-Fi 환경에서의 사내 베타 테스트
3. NCP(네이버 클라우드)에 백엔드 배포
4. 피험자 스마트폰에 앱 설치 (Android / iOS)
5. 실험 운용 워크플로우 (모집 → 코드 발급 → 데이터 회수 → IRB 보고)

---

## 1. 개발자 PC에서 로컬 동작 확인

### 1-1. 백엔드 기동 (Docker 권장)

```bash
cd backend
cp .env.example .env
# .env 에서 OPENAI_API_KEY, ADMIN_CODE, JWT_SECRET 등 채우기
docker-compose up -d
docker exec affect_app python -m scripts.seed_users   # P001~P020 더미 코드 시드
```

확인:
- http://localhost:8000/docs → Swagger UI에서 `/auth/login` 호출 가능
- http://localhost:8000/crisis-resources → 1393 등 위기 자원 응답

### 1-2. Flutter 앱 기동 (Android 에뮬레이터)

```bash
cd app
cp .env.example .env
# .env 의 API_BASE_URL은 기본값 http://10.0.2.2:8000 (Android 에뮬레이터→호스트 PC)
flutter pub get
flutter run
```

iOS 시뮬레이터에서는 `.env`의 `API_BASE_URL`을 `http://localhost:8000`으로 변경.

**확인 시나리오**:
1. 첫 화면 = 로그인 화면 (피험자 코드 P001, 실명 "테스터" 입력)
2. "시작하기" → 홈 화면 ("안녕하세요, 테스터 님" 표시)
3. 앱을 완전히 종료 후 재실행 → 로그인 화면을 건너뛰고 바로 홈 (디바이스 바인딩 + JWT 보존 확인)
4. 다른 에뮬레이터/기기에서 동일 코드(P001)로 시도 → "이 코드는 다른 기기에 등록되어 있습니다" 오류 (엄격 바인딩 정상 동작)

---

## 2. KAIST 캠퍼스 Wi-Fi 환경에서의 사내 베타 테스트

연구실 PC를 백엔드 서버로 쓰고, 같은 Wi-Fi에 연결된 실기기에서 테스트하는 단계.

### 2-1. PC의 LAN IP 확인
- macOS/Linux: `ifconfig | grep inet`
- Windows: `ipconfig`
- 예: `192.168.0.42`

### 2-2. 백엔드를 LAN에 노출
```bash
# docker-compose.yml은 이미 0.0.0.0 바인딩되어 있음
# PC 방화벽에서 8000 포트 인바운드 허용 필요
```

### 2-3. Flutter 앱의 `.env` 수정
```env
API_BASE_URL=http://192.168.0.42:8000
```

### 2-4. 실기기에서 빌드
```bash
# Android 기기를 USB 연결 + 개발자 모드 + USB 디버깅 활성화
flutter devices                   # 기기 확인
flutter run -d <device_id>        # 디버그 빌드
# 또는 APK 생성
flutter build apk --debug
# build/app/outputs/flutter-apk/app-debug.apk 가 생성됨 → 직접 설치
```

**주의**: 실기기에서 HTTP 백엔드 호출 시 Android `usesCleartextTraffic="true"` 설정 필요 (PLATFORM_SETUP.md 참고). 운영 배포 시 반드시 HTTPS로 전환.

---

## 3. NCP(네이버 클라우드)에 백엔드 배포

### 3-1. NCP 리소스 생성 체크리스트

| 리소스 | 권장 사양 | 비고 |
|---|---|---|
| **VPC + Subnet** | Public/Private 분리 | DB와 Redis는 Private |
| **Server** | Standard 2vCPU 4GB (파일럿 규모) | Ubuntu 22.04 LTS |
| **Cloud DB for PostgreSQL** | 15 버전, HA off (파일럿) | 자동 백업 1일 1회, 7일 보관 |
| **Object Storage** | 1개 버킷 (`affect-export`) | 다운로드 CSV/JSON 임시 저장 |
| **Load Balancer (ALB)** | HTTPS 종단 | SSL 인증서는 NCP Certificate Manager |
| **Cloud Insight** | API 5xx, DB 연결 수, CPU 알람 | 임계치 초과 시 SMS/이메일 |

### 3-2. 도메인 + SSL

1. 도메인 발급(예: `api.affect-cartography.kaist.ac.kr`)
2. NCP Global DNS에 A 레코드 → ALB Public IP
3. NCP Certificate Manager에서 무료 SSL 발급 → ALB에 부착

### 3-3. Server 인스턴스 초기 셋업

```bash
ssh ncloud@<server-ip>
sudo apt update && sudo apt install -y docker.io docker-compose-plugin git
sudo usermod -aG docker $USER && newgrp docker

git clone <your-repo> affect-cartography
cd affect-cartography/backend

# .env 작성 — DATABASE_URL은 NCP Cloud DB의 Private 엔드포인트로
cat > .env <<EOF
DATABASE_URL=postgresql+asyncpg://affect_user:STRONG_PASS@<cloud-db-private-host>:5432/affect_cartography
DATABASE_URL_SYNC=postgresql://affect_user:STRONG_PASS@<cloud-db-private-host>:5432/affect_cartography
JWT_SECRET=$(openssl rand -hex 32)
OPENAI_API_KEY=sk-...
OPENAI_ZERO_DATA_RETENTION=true
ADMIN_CODE=$(openssl rand -hex 16)
ADMIN_CODE_SALT=$(openssl rand -hex 16)
REDIS_URL=redis://redis:6379/0
CORS_ORIGINS=https://admin.affect-cartography.kaist.ac.kr
APP_ENV=production
APP_DEBUG=false
EOF
chmod 600 .env

# Cloud DB는 외부에 있으므로 docker-compose의 postgres 서비스는 제거하고 app·redis만 실행
docker compose up -d app redis
docker compose exec app alembic upgrade head
docker compose exec app python -m scripts.seed_users   # 또는 관리자가 실제 코드 발급
```

### 3-4. ALB → Server 8000 포트 매핑
- ALB 리스너: HTTPS 443
- Target Group: Server 인스턴스 8000 포트
- Health Check: `/health` 경로 200 응답

### 3-5. 보안 그룹(ACG) 규칙
- Server: 22(관리자 IP만), 8000(ALB만)
- Cloud DB: 5432(Server만)
- ALB: 443(0.0.0.0/0), 80(redirect → 443)

### 3-6. 운영 환경 동작 확인
```bash
curl https://api.affect-cartography.kaist.ac.kr/health
# {"status":"ok","app":"Affect Cartography API","env":"production"}
```

---

## 4. 피험자 스마트폰에 앱 설치

파일럿 단계에서는 정식 스토어 심사 없이 배포하는 방법을 권장한다.

### 4-1. Flutter 앱 `.env` (운영용)

```env
API_BASE_URL=https://api.affect-cartography.kaist.ac.kr
APP_ENV=production
```

### 4-2. Android — Google Play 내부 테스트 트랙 (권장)

**준비물**: Google Play Console 계정($25 1회)

```bash
cd app
# 키스토어 생성 (최초 1회)
keytool -genkey -v -keystore ~/affect-release.jks \
    -keyalg RSA -keysize 2048 -validity 10000 -alias affect

# android/key.properties 작성
cat > android/key.properties <<EOF
storeFile=/home/<user>/affect-release.jks
storePassword=...
keyAlias=affect
keyPassword=...
EOF

# release AAB 빌드
flutter build appbundle --release
# build/app/outputs/bundle/release/app-release.aab
```

**Play Console에서**:
1. 새 앱 만들기 → 비공개 앱
2. 내부 테스트 트랙 생성 → AAB 업로드
3. 테스터 목록에 피험자 Gmail 추가
4. 피험자에게 옵트인 링크 전송 → 피험자가 링크 클릭 후 Play 스토어에서 설치

**대안 (Play Console 없이)**: APK 직접 배포
```bash
flutter build apk --release
# app-release.apk 를 카카오톡/이메일/QR로 전달 → 피험자가 "출처를 알 수 없는 앱 설치" 허용 후 설치
```

### 4-3. iOS — TestFlight (필수, 사이드로딩 불가)

**준비물**: Apple Developer Program 계정($99/년)

```bash
cd app/ios
# Xcode에서 Runner.xcworkspace 열기
# Signing & Capabilities → Team 선택, Bundle ID 고유하게 설정
flutter build ipa --release
# build/ios/ipa/affect_cartography.ipa
```

1. Xcode 또는 Transporter로 App Store Connect에 IPA 업로드
2. TestFlight 탭 → 빌드 처리 대기 (5~30분)
3. 내부 테스터(최대 100명) 또는 외부 테스터(최대 10,000명, Apple 베타 심사 필요) 추가
4. 피험자에게 TestFlight 초대 이메일 자동 발송
5. 피험자가 App Store에서 TestFlight 앱 설치 → 초대 수락 → 본 앱 설치

### 4-4. 설치 후 피험자가 해야 할 일

1. 앱 첫 실행 → 알림 권한 허용
2. 연구진이 발급한 **피험자 코드** + **실명** 입력 → "시작하기"
3. 디바이스 바인딩 완료 (이후 자동 로그인)

---

## 5. 실험 운용 워크플로우

### 5-1. 피험자 모집 → 코드 발급 단계

```
[온라인 모집공고]
        ↓
[참여 의사 표명] (Google Form 등)
        ↓
[연구진 1차 스크리닝]
        ↓
[IRB 동의서 서면/디지털 서명]
        ↓
[관리자 대시보드 (10단계)에서 피험자 코드 발급]
   예: P021 → 김철수
        ↓
[피험자에게 안내]
  - 코드: P021
  - 실명을 입력하라는 안내
  - 앱 설치 링크 (Play 내부 테스트 / TestFlight)
        ↓
[피험자 앱 설치 + 첫 로그인 = 디바이스 바인딩 완료]
```

### 5-2. 4주 운용 기간 중

| 시점 | 작업 | 도구 |
|---|---|---|
| 매일 | 알림 발송 확인, 응답률 모니터링 | 관리자 대시보드 / NCP Cloud Insight |
| 매일 | 안전 플래그 검토 (자살/자해 키워드 감지) | `GET /admin/safety/flags` |
| 주 1회 | 대화 감사 — 부적절한 LLM 응답 표본 검토 | 관리자 대시보드 "대화 감사" |
| 주 1회 | 디바이스 변경 요청 처리 | `POST /admin/device/unbind` |
| 필요 시 | 공지 송출 (앱 햄버거 메뉴) | `POST /admin/notification/schedule` |

### 5-3. 위기 상황 대응 프로토콜

자살/자해 키워드가 감지되어 `safety_flag`가 발급된 경우:

1. **즉시 (자동)**: 앱이 사용자에게 "지금 많이 힘드신 것 같아요. 1393으로 연락해주세요" 메시지 표시 + 대화 종료
2. **수 분 이내 (운영자)**: 알람 수신 → 관리자 대시보드에서 해당 사용자 확인
3. **24시간 이내 (연구진)**: 피험자에게 직접 연락하여 안부 확인 + KAIST 학생상담센터 연계 권유
4. **사후 (IRB 보고)**: 위기 사례 발생 보고서 작성 → IRB에 보고

### 5-4. 데이터 회수 (4주 종료 시)

```
관리자 대시보드 → "데이터 다운로드"
  ├─ structured_data.csv (정동·감정·강도·개입 응답)
  ├─ dialogues.json (LLM 대화 로그)
  └─ 익명화 토글 ON → 실명을 P021 코드로 자동 치환
```

다운로드된 자료를 분석 환경(예: 연구실 PC의 R/Python)으로 이전한다.

### 5-5. 연구 종료 후 데이터 보존 정책

- 사양서 10항에 따라 **6개월 보관 후 익명화 분석셋만 유지, 원자료 삭제**
- 삭제 절차:
  ```bash
  # NCP Cloud DB에서
  TRUNCATE TABLE agent_dialogues;
  UPDATE users SET real_name = NULL, device_id_hash = NULL;
  ```
- 삭제 완료 후 IRB에 종료 보고서 제출

---

## 6. 자주 묻는 운영 이슈

| 증상 | 원인 | 해결 |
|---|---|---|
| 피험자가 "등록되지 않은 코드" 오류 | 관리자가 아직 코드 발급 안 함, 또는 오타 | 관리자 대시보드에서 코드 발급 확인 |
| 피험자가 "이 코드는 다른 기기에 등록되어 있습니다" | 앱 재설치 또는 기기 변경 | `POST /admin/device/unbind` 호출 후 사용자에게 재로그인 안내 |
| 알림이 오지 않음 | iOS 알림 권한 거부 / Android 배터리 최적화 | 피험자에게 시스템 설정에서 권한 확인 안내 |
| OpenAI API 429 (rate limit) | 동시 사용자 폭증 | OpenAI Tier 상향 또는 백오프 로직 적용 |
| 백엔드 5xx 빈발 | DB 연결 풀 고갈 / 메모리 부족 | Server 인스턴스 사양 상향 |

---

## 7. 보안·법적 체크리스트 (배포 전 최종 확인)

- [ ] IRB 승인서 사본 보관
- [ ] 디지털 동의서가 실제 첫 로그인 흐름에 포함되어 있는가 (IRB 승인 후 추가 구현 필요)
- [ ] OpenAI **Zero Data Retention** 옵션이 실제 활성화되어 있는가 (Organization settings 확인)
- [ ] NCP Cloud DB의 at-rest 암호화(KMS)가 활성화되어 있는가
- [ ] 관리자 대시보드 IP 화이트리스트 적용 (KAIST 캠퍼스 IP 또는 연구실 고정 IP)
- [ ] 관리자 2FA(TOTP) 설정 완료
- [ ] 정기 백업 복원 테스트 1회 이상 완료
- [ ] 위기 자원(1393, KAIST 상담센터) 안내가 모든 화면에서 2탭 이내 접근 가능
