import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';

/// 앱 내 관찰 시나리오 (scenario_other 모드용).
/// 나중에 백엔드/관리자에서 관리할 수도 있으나, 지금은 앱에 내장.
class ObservationScenario {
  final String id;
  final String title;
  final String body;
  const ObservationScenario({
    required this.id,
    required this.title,
    required this.body,
  });
}

const observationScenarios = <ObservationScenario>[
  ObservationScenario(
    id: 'sc_bus',
    title: '버스 안의 승객',
    body: '만원 버스 맨 뒷자리, 한 사람이 창밖을 응시하고 있습니다. '
        '이어폰을 낀 채 미동도 없이 흘러가는 풍경을 바라봅니다. '
        '그 사람은 지금 어떤 상태일까요?',
  ),
  ObservationScenario(
    id: 'sc_cafe',
    title: '카페의 발표 준비',
    body: '카페 구석에서 한 사람이 노트북을 켜두고 발표 자료를 넘겨봅니다. '
        '펜을 쥐었다 놓았다 하며 입술을 살짝 깨뭅니다. '
        '그 사람의 정동은 어디쯤일까요?',
  ),
  ObservationScenario(
    id: 'sc_park',
    title: '공원의 재회',
    body: '공원 벤치에서 두 사람이 오랜만에 만난 듯 마주 앉습니다. '
        '한 사람이 활짝 웃으며 상대의 팔을 가볍게 칩니다. '
        '그 사람은 지금 어떤 마음일까요?',
  ),
];

class ObservationRepository {
  final ApiClient _api;
  ObservationRepository(this._api);

  /// 현재 시각 기준 슬롯. affect_repository와 동일 규칙.
  static String currentSlot([DateTime? now]) {
    final h = (now ?? DateTime.now()).hour;
    if (h < 12) return 'morning';
    if (h < 18) return 'afternoon';
    return 'evening';
  }

  static String today([DateTime? now]) {
    final d = now ?? DateTime.now();
    final m = d.month.toString().padLeft(2, '0');
    final day = d.day.toString().padLeft(2, '0');
    return '${d.year}-$m-$day';
  }

  /// 타인 관찰 정동 저장.
  Future<void> save({
    required String targetType, // recall_other / scenario_other
    String? scenarioId,
    required double valence,
    required double arousal,
    String? emotionWord,
  }) async {
    final now = DateTime.now();
    final resp = await _api.dio.post('/observation/record', data: {
      'record_date': today(now),
      'slot': currentSlot(now),
      'target_type': targetType,
      if (scenarioId != null) 'scenario_id': scenarioId,
      'valence': valence,
      'arousal': arousal,
      if (emotionWord != null && emotionWord.isNotEmpty)
        'emotion_word': emotionWord,
    });
    if (resp.statusCode != 201) {
      throw Exception('관찰 기록 저장 실패: ${resp.statusCode} ${resp.data}');
    }
  }
}

final observationRepositoryProvider = Provider<ObservationRepository>((ref) {
  return ObservationRepository(ref.read(apiClientProvider));
});
