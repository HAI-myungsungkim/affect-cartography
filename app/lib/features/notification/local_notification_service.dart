import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import 'notification_models.dart';

/// 사양서 8항 — 로컬 알림.
///
/// 백엔드에서 받은 오늘의 스케줄을 OS 알림 큐에 등록.
/// 첫 알림 미응답 시 15분 후 1회 재알림.
class LocalNotificationService {
  static final _plugin = FlutterLocalNotificationsPlugin();
  static bool _initialized = false;

  /// 사용자가 알림 탭 시 진입한 prompt_id. 라우터 측에서 listen.
  static final ValueNotifier<String?> launchedPromptId = ValueNotifier(null);

  /// 앱 시작 시 1회 호출.
  static Future<void> initialize() async {
    if (_initialized) return;

    tzdata.initializeTimeZones();
    tz.setLocalLocation(tz.getLocation('Asia/Seoul'));

    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _plugin.initialize(
      settings,
      onDidReceiveNotificationResponse: (response) {
        launchedPromptId.value = response.payload;
      },
    );

    // 앱이 알림 탭으로 시작된 경우
    final details = await _plugin.getNotificationAppLaunchDetails();
    if (details?.didNotificationLaunchApp == true) {
      launchedPromptId.value = details?.notificationResponse?.payload;
    }

    _initialized = true;
  }

  /// 알림 권한 요청. iOS는 명시적, Android 13+는 시스템 다이얼로그.
  static Future<bool> requestPermissions() async {
    final ios = _plugin.resolvePlatformSpecificImplementation<
        IOSFlutterLocalNotificationsPlugin>();
    if (ios != null) {
      final granted = await ios.requestPermissions(
        alert: true, badge: true, sound: true,
      );
      return granted ?? false;
    }
    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    if (android != null) {
      final granted = await android.requestNotificationsPermission();
      return granted ?? false;
    }
    return true;
  }

  /// 오늘의 알림 등록 (기존 예약 모두 취소 후 새로).
  /// 각 알림에 15분 뒤 재알림 함께 예약.
  static Future<void> scheduleToday(TodaySchedule schedule) async {
    await _plugin.cancelAll();
    final now = DateTime.now().toUtc();

    var notifId = 1000;
    for (final p in schedule.prompts) {
      if (p.scheduledAt.isAfter(now)) {
        await _scheduleOne(
          id: notifId++,
          when: p.scheduledAt,
          promptId: p.promptId,
          window: p.window,
        );
        await _scheduleOne(
          id: notifId++,
          when: p.scheduledAt.add(const Duration(minutes: 15)),
          promptId: p.promptId,
          window: p.window,
          isReminder: true,
        );
      }
    }
  }

  static Future<void> _scheduleOne({
    required int id,
    required DateTime when,
    required String promptId,
    required String window,
    bool isReminder = false,
  }) async {
    final title = isReminder ? '잠깐, 아까 못 봤다면' : '지금 어떤 느낌인가요?';
    final body = isReminder
        ? '여전히 시간이 된다면 30초만 마음을 들여다보아요.'
        : _bodyForWindow(window);

    const androidDetails = AndroidNotificationDetails(
      'affect_records',
      '정동 기록 알림',
      channelDescription: 'KAIST 정신건강 연구 알림',
      importance: Importance.high,
      priority: Priority.high,
    );
    const iosDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await _plugin.zonedSchedule(
      id,
      title,
      body,
      tz.TZDateTime.from(when, tz.local),
      details,
      payload: promptId,
      androidScheduleMode: AndroidScheduleMode.exactAllowWhileIdle,
      uiLocalNotificationDateInterpretation:
          UILocalNotificationDateInterpretation.absoluteTime,
    );
  }

  static String _bodyForWindow(String w) {
    switch (w) {
      case 'morning':
        return '하루를 시작하는 마음 한 점을 찍어봐요.';
      case 'afternoon':
        return '오후의 마음은 어디쯤 와 있나요?';
      case 'evening':
        return '오늘의 마음을 잠시 정리해봐요.';
      default:
        return '지금 어떤 느낌인지 잠시 들여다봐요.';
    }
  }

  /// 디버그용: 현재 OS 알림 큐에 예약된 알림 수.
  static Future<int> pendingCount() async {
    final list = await _plugin.pendingNotificationRequests();
    return list.length;
  }
}
