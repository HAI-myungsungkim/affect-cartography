import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import 'affect_models.dart';

class AffectRepository {
  final ApiClient _api;
  AffectRepository(this._api);

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
    // promptId가 빈 문자열이면 null로 처리 (알림 외 진입)
    final body = <String, dynamic>{
      'mode': mode.apiValue,
      'valence': endPoint.valence,
      'arousal': endPoint.arousal,
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
