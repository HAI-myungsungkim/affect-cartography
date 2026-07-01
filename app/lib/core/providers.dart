import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_client.dart';
import 'device_id_service.dart';
import 'secure_storage.dart';

/// 앱 전체에 주입되는 Riverpod provider들.
///
/// `apiClientProvider`는 비동기 초기화가 필요하므로 main()에서 미리 만든 인스턴스를
/// `overrideWithValue`로 주입한다.

final secureStorageProvider = Provider<SecureStorage>((ref) => SecureStorage());

final deviceIdServiceProvider = Provider<DeviceIdService>(
  (ref) => DeviceIdService(ref.read(secureStorageProvider)),
);

/// main()에서 override
final apiClientProvider = Provider<ApiClient>(
  (ref) => throw UnimplementedError('apiClientProvider must be overridden'),
);

/// 현재 로그인 여부 (앱 시작 시 1회 평가)
final sessionProvider = FutureProvider<bool>((ref) async {
  final storage = ref.read(secureStorageProvider);
  return storage.hasValidSession();
});
