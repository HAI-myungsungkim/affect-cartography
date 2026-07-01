import 'dart:io';
import 'dart:math';

import 'package:device_info_plus/device_info_plus.dart';

import 'secure_storage.dart';

/// 디바이스 ID 생성 및 영속 — 엄격 바인딩 정책의 클라이언트 측 핵심.
///
/// 정책:
///  - 처음 앱 실행 시 1회 생성, Secure Storage에 영속 저장.
///  - 이후 변경 절대 금지. 앱 삭제·재설치 시에는 새 ID가 발급되어 다른 기기로 간주됨 → 연구진 수동 해제 필요.
///  - OS 식별자(androidId, iOS identifierForVendor)를 결합해 단말 교체 가능성을 줄임.
class DeviceIdService {
  final SecureStorage _storage;
  DeviceIdService(this._storage);

  Future<String> getOrCreate() async {
    final existing = await _storage.getDeviceId();
    if (existing != null && existing.isNotEmpty) return existing;

    final newId = await _generate();
    await _storage.setDeviceId(newId);
    return newId;
  }

  Future<String> _generate() async {
    final info = DeviceInfoPlugin();
    String osPart;
    try {
      if (Platform.isAndroid) {
        final a = await info.androidInfo;
        osPart = 'and-${a.id}-${a.model}'.replaceAll(' ', '_');
      } else if (Platform.isIOS) {
        final i = await info.iosInfo;
        osPart = 'ios-${i.identifierForVendor ?? "unknown"}';
      } else {
        osPart = 'other-${DateTime.now().millisecondsSinceEpoch}';
      }
    } catch (_) {
      osPart = 'fallback';
    }

    // OS 식별자 + 무작위 부분을 결합하여 충돌 방지
    final rnd = Random.secure();
    final randPart = List<int>.generate(16, (_) => rnd.nextInt(256))
        .map((b) => b.toRadixString(16).padLeft(2, '0'))
        .join();
    return '$osPart-$randPart';
  }
}
