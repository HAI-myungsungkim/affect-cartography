/// 감정 단어 사전 도메인 모델 (사전 방식 — 레거시, 관리자/분석용으로 유지).
class NeighborInfo {
  final String word;
  final String direction;
  final double deltaV;
  final double deltaA;
  const NeighborInfo({
    required this.word,
    required this.direction,
    required this.deltaV,
    required this.deltaA,
  });
  factory NeighborInfo.fromJson(Map<String, dynamic> j) => NeighborInfo(
        word: j['word'] as String,
        direction: j['direction'] as String,
        deltaV: (j['delta_v'] as num).toDouble(),
        deltaA: (j['delta_a'] as num).toDouble(),
      );
}

class EmotionWord {
  final String word;
  final String definition;
  final String example;
  final double valence;
  final double arousal;
  final List<NeighborInfo> neighbors;
  const EmotionWord({
    required this.word,
    required this.definition,
    required this.example,
    required this.valence,
    required this.arousal,
    this.neighbors = const [],
  });
  factory EmotionWord.fromJson(Map<String, dynamic> j) => EmotionWord(
        word: j['word'] as String,
        definition: j['definition'] as String,
        example: j['example'] as String,
        valence: (j['valence'] as num).toDouble(),
        arousal: (j['arousal'] as num).toDouble(),
        neighbors: (j['neighbors'] as List<dynamic>? ?? [])
            .map((n) => NeighborInfo.fromJson(n as Map<String, dynamic>))
            .toList(),
      );
}

class NeighborWords {
  final EmotionWord center;
  final List<EmotionWord> neighbors;
  const NeighborWords({required this.center, required this.neighbors});
  factory NeighborWords.fromJson(Map<String, dynamic> j) => NeighborWords(
        center: EmotionWord.fromJson(j['center'] as Map<String, dynamic>),
        neighbors: (j['neighbors'] as List<dynamic>)
            .map((n) => EmotionWord.fromJson(n as Map<String, dynamic>))
            .toList(),
      );
}

/// 감정 기록 저장 결과. 서술형/사전 방식 공통.
class EmotionSelectResult {
  final String emotionId;
  final String? freeText;
  final String? selectedWord;
  final int intensity;
  final String interventionType; // self_distancing / grounding / activation
  const EmotionSelectResult({
    required this.emotionId,
    required this.freeText,
    required this.selectedWord,
    required this.intensity,
    required this.interventionType,
  });
  factory EmotionSelectResult.fromJson(Map<String, dynamic> j) =>
      EmotionSelectResult(
        emotionId: j['emotion_id'] as String,
        freeText: j['free_text'] as String?,
        selectedWord: j['selected_word'] as String?,
        intensity: j['intensity'] as int,
        interventionType: j['intervention_type'] as String,
      );
}
