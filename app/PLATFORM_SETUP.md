# 플랫폼별 설정 가이드 (Android / iOS)

`flutter create`로 프로젝트를 만든 후, 아래 변경 사항을 각 플랫폼 폴더에 적용한다.

---

## Android

### 1. `android/app/build.gradle` — minSdk 21 이상

```gradle
android {
    defaultConfig {
        minSdkVersion 21        // flutter_secure_storage 권장
        targetSdkVersion 34
    }
}
```

### 2. `android/app/src/main/AndroidManifest.xml`

`<manifest>` 태그 내부:
```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM"/>
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
```

`<application>` 태그 속성에 (개발 중 HTTP 백엔드 사용 시):
```xml
<application
    android:usesCleartextTraffic="true"   <!-- 운영 배포 시 제거, HTTPS만 -->
    ... >
```

운영(HTTPS만 허용)에서는 `usesCleartextTraffic`를 **반드시** 제거.

---

## iOS

### 1. `ios/Runner/Info.plist`

운영에서는 ATS(App Transport Security) 기본값(HTTPS 강제)을 유지한다.
**개발 중 HTTP 백엔드 테스트가 필요한 경우에만** 아래 키 추가:

```xml
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

알림 권한 사용 설명:
```xml
<key>NSUserNotificationsUsageDescription</key>
<string>정동 기록 알림을 받기 위해 사용합니다.</string>
```

### 2. `ios/Podfile`

`platform :ios, '13.0'` 이상으로 설정 (flutter_secure_storage 요구사항).

```ruby
platform :ios, '13.0'
```

---

## 의존성 설치

```bash
cd app
flutter pub get
cd ios && pod install && cd ..    # macOS에서 iOS 빌드 시
```
