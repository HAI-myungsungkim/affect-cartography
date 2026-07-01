import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import 'agent_models.dart';

class AgentRepository {
  final ApiClient _api;
  AgentRepository(this._api);

  /// 한 턴 진행. userMessage가 null이면 첫 턴(에이전트가 먼저).
  Future<TurnResult> postTurn({
    required String recordId,
    String? userMessage,
  }) async {
    final resp = await _api.dio.post('/agent/dialogue/turn', data: {
      'record_id': recordId,
      if (userMessage != null) 'user_message': userMessage,
    });
    if (resp.statusCode != 200) {
      throw Exception('대화 턴 실패: ${resp.statusCode} ${resp.data}');
    }
    return TurnResult.fromJson(resp.data as Map<String, dynamic>);
  }
}

final agentRepositoryProvider = Provider<AgentRepository>((ref) {
  return AgentRepository(ref.read(apiClientProvider));
});
