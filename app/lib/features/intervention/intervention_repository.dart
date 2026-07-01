import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import 'intervention_models.dart';

class InterventionRepository {
  final ApiClient _api;
  InterventionRepository(this._api);

  Future<InterventionPrompt> getPrompt(String recordId) async {
    final r = await _api.dio.get('/intervention/prompt',
        queryParameters: {'record_id': recordId});
    return InterventionPrompt.fromJson(r.data as Map<String, dynamic>);
  }

  Future<void> submitResponse({
    required String recordId,
    required String interventionType,
    String? userResponseText,
  }) async {
    final r = await _api.dio.post('/intervention/response', data: {
      'record_id': recordId,
      'intervention_type': interventionType,
      if (userResponseText != null && userResponseText.trim().isNotEmpty)
        'user_response_text': userResponseText.trim(),
    });
    if (r.statusCode != 201) {
      throw Exception('개입 응답 저장 실패: ${r.statusCode} ${r.data}');
    }
  }
}

final interventionRepositoryProvider = Provider<InterventionRepository>((ref) {
  return InterventionRepository(ref.read(apiClientProvider));
});
