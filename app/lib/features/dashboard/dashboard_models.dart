/// 대시보드 도메인 모델.
import '../affect/affect_models.dart';

class DashboardSummary {
  final int totalRecords;
  final double responseRate;
  final int daysActive;
  final int safetyFlagCount;

  const DashboardSummary({
    required this.totalRecords,
    required this.responseRate,
    required this.daysActive,
    required this.safetyFlagCount,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> j) =>
      DashboardSummary(
        totalRecords: j['total_records'] as int,
        responseRate: (j['response_rate'] as num).toDouble(),
        daysActive: j['days_active'] as int,
        safetyFlagCount: j['safety_flag_count'] as int? ?? 0,
      );
}

class AffectPointHistory {
  final String recordId;
  final DateTime timestamp;
  final double valence;
  final double arousal;
  final String quadrant;
  final String mode; // 'point' | 'trajectory'
  final List<AffectPoint>? trajectory;
  final String? emotionWord;
  final int? intensity;

  const AffectPointHistory({
    required this.recordId,
    required this.timestamp,
    required this.valence,
    required this.arousal,
    required this.quadrant,
    required this.mode,
    this.trajectory,
    this.emotionWord,
    this.intensity,
  });

  factory AffectPointHistory.fromJson(Map<String, dynamic> j) {
    final tp = j['trajectory_points'] as List<dynamic>?;
    return AffectPointHistory(
      recordId: j['record_id'] as String,
      timestamp: DateTime.parse(j['timestamp'] as String),
      valence: (j['valence'] as num).toDouble(),
      arousal: (j['arousal'] as num).toDouble(),
      quadrant: j['quadrant'] as String,
      mode: j['mode'] as String,
      trajectory: tp == null
          ? null
          : tp.map((p) {
              final m = p as Map<String, dynamic>;
              return AffectPoint(
                (m['v'] as num).toDouble(),
                (m['a'] as num).toDouble(),
                (m['t'] as num).toInt(),
              );
            }).toList(),
      emotionWord: j['emotion_word'] as String?,
      intensity: j['intensity'] as int?,
    );
  }
}

class EmotionTimelineItem {
  final String recordId;
  final DateTime timestamp;
  final String word;
  final int intensity;
  final double valence;
  final double arousal;
  final String quadrant;

  const EmotionTimelineItem({
    required this.recordId,
    required this.timestamp,
    required this.word,
    required this.intensity,
    required this.valence,
    required this.arousal,
    required this.quadrant,
  });

  factory EmotionTimelineItem.fromJson(Map<String, dynamic> j) =>
      EmotionTimelineItem(
        recordId: j['record_id'] as String,
        timestamp: DateTime.parse(j['timestamp'] as String),
        word: j['word'] as String,
        intensity: j['intensity'] as int,
        valence: (j['valence'] as num).toDouble(),
        arousal: (j['arousal'] as num).toDouble(),
        quadrant: j['quadrant'] as String,
      );
}

class DashboardData {
  final DashboardSummary summary;
  final List<AffectPointHistory> affectPoints;
  final List<EmotionTimelineItem> emotionTimeline;

  const DashboardData({
    required this.summary,
    required this.affectPoints,
    required this.emotionTimeline,
  });

  factory DashboardData.fromJson(Map<String, dynamic> j) => DashboardData(
        summary: DashboardSummary.fromJson(j['summary'] as Map<String, dynamic>),
        affectPoints: (j['affect_points'] as List<dynamic>)
            .map((p) => AffectPointHistory.fromJson(p as Map<String, dynamic>))
            .toList(),
        emotionTimeline: (j['emotion_timeline'] as List<dynamic>)
            .map((e) => EmotionTimelineItem.fromJson(e as Map<String, dynamic>))
            .toList(),
      );
}
