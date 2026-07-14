import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import 'emotion_models.dart';

class EmotionRepository {
  final ApiClient _api;
  EmotionRepository(this._api);

  // --- 사전 방식 (레거시) ---
  Future<List<EmotionWord>> getCandidates({
    required double valence,
    required double arousal,
    int limit = 5,
  }) async {
    final r = await _api.dio.get('/emotion/candidates', queryParameters: {
      'valence': valence,
      'arousal': arousal,
      'limit': limit,
    });
    final list = (r.data['candidates'] as List<dynamic>);
    return list.map((c) => EmotionWord.fromJson(c as Map<String, dynamic>)).toList();
  }

  Future<NeighborWords> getNeighbors(String word) async {
    final r = await _api.dio.get('/emotion/neighbors',
        queryParameters: {'word': word});
    return NeighborWords.fromJson(r.data as Map<String, dynamic>);
  }

  // --- 서술형 (현재 기본) ---
  /// 자유 서술(단어/문장) + 강도로 감정 기록.
  Future<EmotionSelectResult> saveFreeText({
    required String recordId,
    required String freeText,
    required int intensity,
  }) async {
    final r = await _api.dio.post('/emotion/select', data: {
      'record_id': recordId,
      'free_text': freeText,
      'intensity': intensity,
      'exploration_path': <String>[],
    });
    if (r.statusCode != 201) {
      throw Exception('감정 기록 저장 실패: ${r.statusCode} ${r.data}');
    }
    return EmotionSelectResult.fromJson(r.data as Map<String, dynamic>);
  }

  // 사전 방식 저장 (레거시)
  Future<EmotionSelectResult> select({
    required String recordId,
    required String selectedWord,
    required int intensity,
    required List<String> explorationPath,
  }) async {
    final r = await _api.dio.post('/emotion/select', data: {
      'record_id': recordId,
      'selected_word': selectedWord,
      'intensity': intensity,
      'exploration_path': explorationPath,
    });
    if (r.statusCode != 201) {
      throw Exception('단어 선택 저장 실패: ${r.statusCode} ${r.data}');
    }
    return EmotionSelectResult.fromJson(r.data as Map<String, dynamic>);
  }
}

final emotionRepositoryProvider = Provider<EmotionRepository>((ref) {
  return EmotionRepository(ref.read(apiClientProvider));
});
