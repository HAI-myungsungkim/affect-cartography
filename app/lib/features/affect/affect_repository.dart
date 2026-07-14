import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import 'affect_models.dart';

class AffectRepository {
  final ApiClient _api;
  AffectRepository(this._api);

  /// 현재 시각을 하루 3슬롯으로 분류.
  /// 자정~11:59 → morning / 12:00~17:59 → afternoon / 18:00~ → evening
  static String currentSlot([DateTime? now]) {
    final h = (now ?? DateTime.now()).hour;
    if (h < 12) return 'morning';
    if (h < 18) return 'afternoon';
    return 'evening';
  }

  /// 오늘 날짜를 YYYY-MM-DD 문자열로 (백엔드 Date 필드용).
  static String today([DateTime? now]) {
    final d = now ?? DateTime.now();
    final m = d.month.toString().padLeft(2, '0');
    final day = d.day.toString().padLeft(2, '0');
    return '${d.year}-$m-$day';
  }

  /// 점 모드 또는 궤도 모드 통합 저장.
  /// 백엔드: POST /affect/record
  Future<String> saveRecord({
    required AffectMode mode,
    required AffectPoint endPoint,
    List<AffectPoint>? trajectory,
    int durationWindowMinutes = 180,
    bool isPractice = false,
    int? responseLatencyMs,
    String? promptId,
  }) async {
    final now = DateTime.now();
    // promptId가 빈 문자열이면 null로 처리 (알림 탭 진입)
    final body = <String, dynamic>{
      'mode': mode.apiValue,
      'valence': endPoint.valence,
      'arousal': endPoint.arousal,
      'record_date': today(now),
      'slot': currentSlot(now),
      'duration_window_minutes': durationWindowMinutes,
      'is_practice': isPractice,
      if (responseLatencyMs != null) 'response_latency_ms': responseLatencyMs,
      if (promptId != null) 'prompt_id': promptId,
    };
    if (mode == AffectMode.trajectory && trajectory != null && trajectory.length >= 2) {
      body['trajectory_points'] = trajectory.map((p) => p.toJson()).toList();
    }

    final resp = await _api.dio.post('/affect/record', data: body);
    if (resp.statusCode != 201) {
      throw DioException(
        requestOptions: resp.requestOptions,
        response: resp,
        message: '정동 기록 저장 실패 (${resp.statusCode})',
      );
    }
    return resp.data['record_id'] as String;
  }

  Future<void> setRecordMode(String mode) async {
    await _api.dio.post('/affect/settings/record-mode', queryParameters: {'mode': mode});
  }

  Future<void> markPracticeDone() async {
    await _api.dio.post('/affect/settings/practice-done');
  }
}

final affectRepositoryProvider = Provider<AffectRepository>((ref) {
  return AffectRepository(ref.read(apiClientProvider));
});
