/// 알림 도메인 모델.
class TimeWindow {
  final String start; // "HH:MM"
  final String end;

  const TimeWindow({required this.start, required this.end});

  factory TimeWindow.fromJson(Map<String, dynamic> j) =>
      TimeWindow(start: j['start'] as String, end: j['end'] as String);

  Map<String, dynamic> toJson() => {'start': start, 'end': end};

  /// "HH:MM" → 분 단위 정수
  int get startMinutes => _toMinutes(start);
  int get endMinutes => _toMinutes(end);

  static int _toMinutes(String hhmm) {
    final p = hhmm.split(':');
    return int.parse(p[0]) * 60 + int.parse(p[1]);
  }
}

class NotificationSettings {
  final TimeWindow morning;
  final TimeWindow afternoon;
  final TimeWindow evening;

  const NotificationSettings({
    required this.morning,
    required this.afternoon,
    required this.evening,
  });

  factory NotificationSettings.fromJson(Map<String, dynamic> j) =>
      NotificationSettings(
        morning: TimeWindow.fromJson(j['morning'] as Map<String, dynamic>),
        afternoon: TimeWindow.fromJson(j['afternoon'] as Map<String, dynamic>),
        evening: TimeWindow.fromJson(j['evening'] as Map<String, dynamic>),
      );
}

class ScheduledPrompt {
  final String promptId;
  final String window; // morning/afternoon/evening
  final DateTime scheduledAt; // UTC

  const ScheduledPrompt({
    required this.promptId,
    required this.window,
    required this.scheduledAt,
  });

  factory ScheduledPrompt.fromJson(Map<String, dynamic> j) => ScheduledPrompt(
        promptId: j['prompt_id'] as String,
        window: j['window'] as String,
        scheduledAt: DateTime.parse(j['scheduled_at'] as String),
      );
}

class TodaySchedule {
  final String userId;
  final String date;
  final List<ScheduledPrompt> prompts;

  const TodaySchedule({
    required this.userId,
    required this.date,
    required this.prompts,
  });

  factory TodaySchedule.fromJson(Map<String, dynamic> j) => TodaySchedule(
        userId: j['user_id'] as String,
        date: j['date'] as String,
        prompts: (j['prompts'] as List<dynamic>)
            .map((p) => ScheduledPrompt.fromJson(p as Map<String, dynamic>))
            .toList(),
      );
}
