import 'package:flutter_test/flutter_test.dart';
import 'package:affect_cartography/features/dashboard/dashboard_models.dart';

void main() {
  group('DashboardData.fromJson', () {
    test('빈 대시보드', () {
      final d = DashboardData.fromJson({
        'summary': {
          'total_records': 0,
          'response_rate': 0.0,
          'days_active': 0,
          'safety_flag_count': 0,
        },
        'affect_points': [],
        'emotion_timeline': [],
      });
      expect(d.summary.totalRecords, 0);
      expect(d.affectPoints, isEmpty);
      expect(d.emotionTimeline, isEmpty);
    });

    test('점 모드 + 감정 단어 포함', () {
      final d = DashboardData.fromJson({
        'summary': {
          'total_records': 1,
          'response_rate': 0.5,
          'days_active': 1,
          'safety_flag_count': 0,
        },
        'affect_points': [
          {
            'record_id': 'rec-1',
            'timestamp': '2026-06-30T10:00:00Z',
            'valence': -0.4,
            'arousal': -0.2,
            'quadrant': 'q3',
            'mode': 'point',
            'emotion_word': '답답하다',
            'intensity': 3,
          },
        ],
        'emotion_timeline': [
          {
            'record_id': 'rec-1',
            'timestamp': '2026-06-30T10:00:00Z',
            'word': '답답하다',
            'intensity': 3,
            'valence': -0.4,
            'arousal': -0.2,
            'quadrant': 'q3',
          },
        ],
      });
      expect(d.summary.responseRate, 0.5);
      expect(d.affectPoints.length, 1);
      expect(d.affectPoints[0].mode, 'point');
      expect(d.affectPoints[0].emotionWord, '답답하다');
      expect(d.affectPoints[0].intensity, 3);
      expect(d.affectPoints[0].trajectory, isNull);
      expect(d.emotionTimeline.length, 1);
      expect(d.emotionTimeline[0].word, '답답하다');
    });

    test('궤도 모드 — trajectory_points 파싱', () {
      final d = DashboardData.fromJson({
        'summary': {
          'total_records': 1,
          'response_rate': 0.5,
          'days_active': 1,
          'safety_flag_count': 0,
        },
        'affect_points': [
          {
            'record_id': 'rec-2',
            'timestamp': '2026-06-30T10:00:00Z',
            'valence': 0.5,
            'arousal': 0.3,
            'quadrant': 'q1',
            'mode': 'trajectory',
            'trajectory_points': [
              {'v': -0.2, 'a': -0.1, 't': 0},
              {'v': 0.5, 'a': 0.3, 't': 200},
            ],
          },
        ],
        'emotion_timeline': [],
      });
      final p = d.affectPoints[0];
      expect(p.mode, 'trajectory');
      expect(p.trajectory, isNotNull);
      expect(p.trajectory!.length, 2);
      expect(p.trajectory![0].valence, -0.2);
      expect(p.trajectory![1].tMs, 200);
    });
  });
}
