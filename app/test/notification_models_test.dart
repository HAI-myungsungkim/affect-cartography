import 'package:flutter_test/flutter_test.dart';
import 'package:affect_cartography/features/notification/notification_models.dart';

void main() {
  group('TimeWindow', () {
    test('HH:MM → 분 변환', () {
      const w = TimeWindow(start: '09:30', end: '12:15');
      expect(w.startMinutes, 9 * 60 + 30);
      expect(w.endMinutes, 12 * 60 + 15);
    });

    test('JSON 라운드트립', () {
      const w = TimeWindow(start: '09:00', end: '12:00');
      final j = w.toJson();
      expect(j['start'], '09:00');
      expect(j['end'], '12:00');
      final back = TimeWindow.fromJson(j);
      expect(back.start, '09:00');
      expect(back.end, '12:00');
    });
  });

  group('NotificationSettings.fromJson', () {
    test('3구간 모두 파싱', () {
      final s = NotificationSettings.fromJson({
        'morning': {'start': '09:00', 'end': '12:00'},
        'afternoon': {'start': '13:00', 'end': '17:00'},
        'evening': {'start': '19:00', 'end': '22:00'},
      });
      expect(s.morning.start, '09:00');
      expect(s.afternoon.end, '17:00');
      expect(s.evening.start, '19:00');
    });
  });

  group('TodaySchedule.fromJson', () {
    test('3개 prompt 파싱 + 시간 UTC 보존', () {
      final s = TodaySchedule.fromJson({
        'user_id': 'u1',
        'date': '2026-06-30',
        'prompts': [
          {
            'prompt_id': 'pid-1',
            'window': 'morning',
            'scheduled_at': '2026-06-30T01:00:00Z',
          },
          {
            'prompt_id': 'pid-2',
            'window': 'afternoon',
            'scheduled_at': '2026-06-30T06:00:00Z',
          },
          {
            'prompt_id': 'pid-3',
            'window': 'evening',
            'scheduled_at': '2026-06-30T11:00:00Z',
          },
        ],
      });
      expect(s.prompts.length, 3);
      expect(s.prompts[0].window, 'morning');
      expect(s.prompts[0].scheduledAt.isUtc, true);
    });
  });
}
