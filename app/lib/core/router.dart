import 'package:go_router/go_router.dart';

import 'package:flutter/foundation.dart';

import '../features/affect/affect_record_screen.dart';
import '../features/agent/agent_dialogue_screen.dart';
import '../features/auth/login_screen.dart';
import '../features/dashboard/dashboard_screen.dart';
import '../features/dev/dev_settings_screen.dart';
import '../features/emotion/emotion_select_screen.dart';
import '../features/home/home_screen.dart';
import '../features/intervention/done_screen.dart';
import '../features/intervention/intervention_screen.dart';
import '../features/notification/local_notification_service.dart';
import '../features/notification/notification_settings_screen.dart';
import 'secure_storage.dart';

/// 라우터. 토큰 보유 여부에 따라 /login ↔ /home redirect.
GoRouter buildRouter(SecureStorage storage) {
  final router = GoRouter(
    initialLocation: '/login',
    redirect: (context, state) async {
      final hasSession = await storage.hasValidSession();
      final goingToLogin = state.matchedLocation == '/login';

      if (!hasSession && !goingToLogin) return '/login';
      if (hasSession && goingToLogin) return '/home';
      return null;
    },
    refreshListenable: LocalNotificationService.launchedPromptId,
    routes: [
      GoRoute(
        path: '/login',
        builder: (_, __) => const LoginScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (_, __) => const HomeScreen(),
      ),
      GoRoute(
        path: '/record',
        builder: (_, state) {
          final promptId = state.uri.queryParameters['prompt_id'];
          return AffectRecordScreen(promptId: promptId);
        },
      ),
      GoRoute(
        path: '/dialogue/:recordId',
        builder: (_, state) {
          final p = state.uri.queryParameters;
          return AgentDialogueScreen(
            recordId: state.pathParameters['recordId']!,
            valence: double.tryParse(p['v'] ?? '0'),
            arousal: double.tryParse(p['a'] ?? '0'),
          );
        },
      ),
      GoRoute(
        path: '/emotion/:recordId',
        builder: (_, state) {
          final p = state.uri.queryParameters;
          return EmotionSelectScreen(
            recordId: state.pathParameters['recordId']!,
            valence: double.tryParse(p['v'] ?? '0') ?? 0,
            arousal: double.tryParse(p['a'] ?? '0') ?? 0,
          );
        },
      ),
      GoRoute(
        path: '/intervention/:recordId',
        builder: (_, state) => InterventionScreen(
          recordId: state.pathParameters['recordId']!,
        ),
      ),
      GoRoute(
        path: '/done',
        builder: (_, __) => const DoneScreen(),
      ),
      GoRoute(
        path: '/dashboard',
        builder: (_, __) => const DashboardScreen(),
      ),
      GoRoute(
        path: '/notification-settings',
        builder: (_, __) => const NotificationSettingsScreen(),
      ),
      GoRoute(
        path: '/dev-settings',
        builder: (_, __) => const DevSettingsScreen(),
      ),
    ],
  );

  // 알림 탭으로 들어온 경우 자동으로 정동 기록 화면으로 이동.
  LocalNotificationService.launchedPromptId.addListener(() {
    final promptId = LocalNotificationService.launchedPromptId.value;
    if (promptId != null) {
      debugPrint('알림 탭 진입: $promptId');
      router.go('/record?prompt_id=$promptId');
      LocalNotificationService.launchedPromptId.value = null;
    }
  });

  return router;
}
