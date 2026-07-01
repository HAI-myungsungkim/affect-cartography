import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/api_client.dart';
import 'core/device_id_service.dart';
import 'core/providers.dart';
import 'core/router.dart';
import 'core/secure_storage.dart';
import 'features/notification/local_notification_service.dart';
import 'shared/theme/app_theme.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');

  // 디바이스 ID 생성/조회 — 앱 첫 실행 시 1회만 생성됨.
  final storage = SecureStorage();
  final deviceId = await DeviceIdService(storage).getOrCreate();

  // 로컬 알림 초기화 (timezone 데이터 + 알림 채널)
  await LocalNotificationService.initialize();

  // ApiClient는 비동기 초기화가 필요하므로 main에서 만들어 override 주입.
  final apiClient = await ApiClient.create(
    storage: storage,
    deviceId: deviceId,
  );

  runApp(
    ProviderScope(
      overrides: [
        secureStorageProvider.overrideWithValue(storage),
        apiClientProvider.overrideWithValue(apiClient),
      ],
      child: AffectCartographyApp(storage: storage),
    ),
  );
}

class AffectCartographyApp extends StatelessWidget {
  final SecureStorage storage;
  const AffectCartographyApp({super.key, required this.storage});

  @override
  Widget build(BuildContext context) {
    final router = buildRouter(storage);
    return MaterialApp.router(
      title: 'Affect Cartography',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light(),
      darkTheme: AppTheme.dark(),
      themeMode: ThemeMode.system,
      routerConfig: router,
    );
  }
}
