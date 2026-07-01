# Affect Cartography Pilot — Flutter App (2단계)

KAIST 학생 정신건강 파일럿 연구용 모바일 앱.

## 현재 상태: 2단계 완료 ✅

- Flutter 프로젝트 구조 (Riverpod + go_router + Dio)
- 디바이스 ID 영속화 (`flutter_secure_storage` + `device_info_plus`)
- JWT 자동 저장 및 매 요청 `X-Device-Id` 헤더 주입
- 로그인 화면 (피험자 코드 + 실명 + 검증 + 에러 분기)
- 메인 홈 화면 (인사 + 오늘의 응답 상태 카드 + 햄버거 메뉴)
- **위기 자원 메뉴 항상 노출** (1393 / KAIST 상담센터 / 1577-0199)
- 다크모드 (시스템 설정 따름)
- Pretendard 계열 한국어 폰트 (Noto Sans KR via google_fonts)

## 빠른 실행

### 의존성 설치
```bash
flutter pub get
```

### 환경 변수 설정
```bash
cp .env.example .env
# 안드로이드 에뮬레이터: API_BASE_URL=http://10.0.2.2:8000 (기본값)
# iOS 시뮬레이터:        API_BASE_URL=http://localhost:8000
# 실기기:                API_BASE_URL=http://<PC의 LAN IP>:8000
```

### 백엔드 먼저 기동
프로젝트 루트의 `backend/` 디렉터리에서 `docker-compose up -d`

### 앱 실행
```bash
flutter run
```

### 테스트
```bash
flutter test
```

## 디렉토리 구조

```
app/
├── lib/
│   ├── main.dart
│   ├── core/
│   │   ├── api_client.dart          # Dio + JWT/디바이스 헤더 인터셉터
│   │   ├── device_id_service.dart   # 디바이스 ID 1회 생성 + 영속
│   │   ├── secure_storage.dart      # 토큰/디바이스 ID 보안 저장
│   │   ├── providers.dart           # Riverpod providers
│   │   └── router.dart              # go_router + 세션 redirect
│   ├── features/
│   │   ├── auth/
│   │   │   ├── login_screen.dart
│   │   │   ├── login_controller.dart
│   │   │   └── login_state.dart
│   │   └── home/
│   │       └── home_screen.dart     # 햄버거 메뉴에 위기 자원 포함
│   └── shared/theme/app_theme.dart  # 사양서 11항 컬러
├── test/
│   └── login_screen_test.dart       # 위젯 테스트
├── pubspec.yaml
├── .env.example
└── PLATFORM_SETUP.md                # Android/iOS 권한 + Info.plist 설정
```

## 핵심 동작 검증 시나리오

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | P001 + "테스터" 입력 → 시작하기 | 홈 화면 진입, "안녕하세요, 테스터 님" |
| 2 | 앱 종료 후 재실행 | 로그인 화면 스킵, 바로 홈 |
| 3 | 다른 에뮬레이터에서 P001 시도 | "이 코드는 다른 기기에 등록되어 있습니다" 오렌지 배너 |
| 4 | P999 (미등록 코드) 시도 | "등록되지 않은 코드입니다" 빨간 배너 |
| 5 | 백엔드 미기동 상태 시도 | "서버에 연결할 수 없습니다" Wi-Fi 아이콘 배너 |
| 6 | 햄버거 메뉴 → 위기 자원 | 1393 / KAIST 상담센터 / 1577-0199 항상 표시 |
| 7 | 햄버거 메뉴 → 로그아웃 | 토큰 삭제 후 로그인 화면, 디바이스 ID는 보존 |

## 보안·정책 반영 사항

- **디바이스 ID는 OS Keychain/EncryptedSharedPreferences에 보관**, 앱 데이터 영역 단순 SharedPreferences 사용 X
- 디바이스 ID = `OS 식별자 + 무작위 16바이트 hex` 결합 → 단말 교체로 인한 충돌 최소화
- JWT는 Authorization 헤더, 디바이스 ID는 `X-Device-Id` 헤더 — 백엔드가 둘을 교차 검증
- 로그아웃 시 토큰만 삭제, **디바이스 ID는 보존** (재로그인 시 동일 디바이스로 인정되어야 함)

## 다음 단계 (3단계)

- V-A grid 위젯 (CustomPaint 기반)
- 점 모드: 탭으로 단일 좌표 기록
- 궤도 모드: 50ms 샘플링 드래그 + 그라데이션 렌더링
- 처음 궤도 모드 활성화 시 자동 연습 세션 (3개 예시)
- 좌표 → 사분면 분류 → 백엔드 `POST /affect/record` 전송
