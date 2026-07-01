# Firebase / 푸시 알림 설정 가이드

⚠️ **이 작업은 사용자(연구진)가 직접 수행해야 합니다.**

현재 9단계까지 구현된 알림은 **로컬 알림** (앱이 백그라운드에 있을 때까지만 작동)입니다.
백엔드에서 푸시를 보내려면 Firebase Cloud Messaging (FCM, Android) + Apple Push Notification service (APNs, iOS) 설정이 필요합니다.

**언제 필요한가**: 실제 피험자에게 배포하기 전. 로컬 개발/베타 테스트에서는 로컬 알림만으로도 충분합니다.

---

## 1. Firebase 프로젝트 생성 (5분, 무료)

1. https://console.firebase.google.com 접속, Google 계정 로그인
2. **프로젝트 추가** → 이름: `affect-cartography-pilot` (또는 원하는 이름)
3. Google Analytics는 **비활성화** (연구 윤리상 추가 추적 불필요)
4. 프로젝트 생성 완료

---

## 2. Android 앱 추가

1. Firebase 콘솔 프로젝트 메인 → Android 아이콘 클릭
2. **패키지 이름**: `com.example.affect_cartography` (또는 `app/android/app/build.gradle`의 `applicationId`와 일치)
3. **SHA-1 인증서 지문** (선택, 운영 시 권장):
   ```bash
   cd app/android
   ./gradlew signingReport
   ```
4. **google-services.json** 다운로드
5. 파일을 다음 경로에 배치:
   ```
   app/android/app/google-services.json
   ```
6. `app/android/build.gradle`에 추가:
   ```gradle
   buildscript {
     dependencies {
       classpath 'com.google.gms:google-services:4.4.2'
     }
   }
   ```
7. `app/android/app/build.gradle` 맨 아래에 추가:
   ```gradle
   apply plugin: 'com.google.gms.google-services'
   ```

---

## 3. iOS 앱 추가

1. Firebase 콘솔에서 iOS 아이콘 클릭
2. **Bundle ID**: `com.example.affectCartography` (또는 Xcode의 Bundle ID와 일치)
3. **GoogleService-Info.plist** 다운로드
4. Xcode에서 `app/ios/Runner.xcworkspace` 열기
5. Runner 폴더 위에 plist 파일을 **드래그 앤 드롭** (반드시 "Copy items if needed" 체크)
6. **APNs 인증 키** 추가 (Apple Developer 계정 필요, $99/년):
   - Apple Developer → Keys → "+" → APNs 활성화 → 키 다운로드 (.p8)
   - Firebase 콘솔 → 프로젝트 설정 → 클라우드 메시징 → APNs 인증 키 업로드

---

## 4. Flutter 의존성 추가

`app/pubspec.yaml`에 다음 추가:
```yaml
dependencies:
  firebase_core: ^3.6.0
  firebase_messaging: ^15.1.3
```

```bash
flutter pub get
cd ios && pod install && cd ..
```

---

## 5. 코드 통합

`app/lib/main.dart`에서 Firebase 초기화:
```dart
import 'package:firebase_core/firebase_core.dart';
import 'firebase_options.dart';   // FlutterFire CLI로 생성

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  // ... 기존 코드
}
```

`firebase_options.dart` 자동 생성:
```bash
dart pub global activate flutterfire_cli
flutterfire configure --project=affect-cartography-pilot
```

---

## 6. 백엔드에 FCM 서비스 계정 키 추가

1. Firebase 콘솔 → 프로젝트 설정 → **서비스 계정** 탭
2. **새 비공개 키 생성** → JSON 파일 다운로드
3. 백엔드 환경변수에 추가:
   ```
   GOOGLE_APPLICATION_CREDENTIALS=/secure/path/to/firebase-key.json
   ```
4. 절대 git에 커밋하지 말 것 (`.gitignore`에 추가)

---

## 7. 디바이스 토큰 등록 흐름 (이후 11단계 통합 테스트에서)

```
Flutter 앱 시작 → FCM 토큰 가져오기 → 백엔드에 POST /notification/register-device
백엔드: users 테이블에 fcm_token 컬럼 저장
백엔드 cron: 각 시간대 시점에 해당 사용자 fcm_token으로 FCM API 호출
```

이 통합은 11단계(통합 테스트)에서 진행되며, 그 전까지는 로컬 알림만으로 운영 가능합니다.

---

## 진행 체크리스트

배포 전 사용자(연구진)가 확인할 것:

- [ ] Firebase 프로젝트 생성
- [ ] `google-services.json` 받아서 `app/android/app/`에 배치
- [ ] `GoogleService-Info.plist` 받아서 Xcode로 Runner에 추가
- [ ] Apple Developer 계정 + APNs 키 ($99/년 필요)
- [ ] Firebase 서비스 계정 키 (.json)를 백엔드 서버에 안전하게 배치
- [ ] `firebase_core`, `firebase_messaging` 의존성 추가
- [ ] FCM 토큰 등록 엔드포인트 통합 (11단계에서)

**현재 단계(9단계)에서는 위 작업 없이도 로컬 알림이 정상 작동합니다.**
실제 배포 시 위 절차를 따라 푸시 통합을 완료하면 됩니다.
