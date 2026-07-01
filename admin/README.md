# Affect Cartography 관리자 대시보드

KAIST 정신건강 파일럿 연구용 관리 콘솔 (Next.js 14 + Tailwind CSS).

PC 브라우저 전용.

## 빠른 실행

### 1. 의존성 설치
```bash
cd admin
npm install
```

### 2. 환경 변수
```bash
cp .env.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000  (기본값)
```

### 3. 백엔드 먼저 기동
프로젝트 루트의 `backend/` 디렉토리에서 `docker-compose up -d`

### 4. 개발 서버
```bash
npm run dev
# → http://localhost:3000
```

### 5. 로그인
- 관리자 코드는 백엔드 `.env`의 `ADMIN_CODE` 값
- 기본값: `change-me` (운영 전 반드시 변경)

## 페이지

| 경로 | 설명 |
|---|---|
| `/login` | 관리자 코드 로그인 |
| `/users` | 사용자 목록, 코드 발급, 응답률·플래그 한눈에 |
| `/users/[id]` | 사용자 상세 — 모든 기록 + 감정 + 개입 + 디바이스 해제 |
| `/safety` | 안전 플래그 목록, 검토 처리 |
| `/audit` | 대화 감사 — 최근 LLM 응답 표본 검토 |
| `/export` | CSV / JSON 다운로드 (익명화 옵션) |

## 운영 배포 시 추가 작업

### IP 화이트리스트
NCP/리버스 프록시에서 KAIST 캠퍼스 또는 연구실 IP만 허용:
```nginx
location /admin/ {
  allow 143.248.0.0/16;  # KAIST 예시
  deny all;
  proxy_pass http://localhost:3000;
}
```

### 2단계 인증 (2FA)
파일럿에서는 강력한 관리자 코드 + IP 제한으로 충분.
운영 확장 시 TOTP(Google Authenticator 등) 추가 권장.

### HTTPS
프로덕션 빌드:
```bash
npm run build
npm start  # 또는 PM2/systemd로 영구화
```

ALB 또는 nginx 앞에 SSL 인증서 (Let's Encrypt) 부착.

### 환경 변수 (운영)
```bash
NEXT_PUBLIC_API_BASE_URL=https://api.affect-cartography.kaist.ac.kr
```

## 디자인 가이드

- 색상: 사양서 11항 기준 다크 블루(#2C3E50), 차콜(#34495E)
- Tailwind 커스텀: `primary`, `accent.sage`, `accent.beige`
- 다크 모드: `prefers-color-scheme` 기반 (CSS 변수)
