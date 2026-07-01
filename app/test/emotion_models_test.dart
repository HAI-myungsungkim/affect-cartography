import 'package:flutter_test/flutter_test.dart';
import 'package:affect_cartography/features/emotion/emotion_models.dart';

void main() {
  group('EmotionWord.fromJson', () {
    test('인접 단어 포함 파싱', () {
      final w = EmotionWord.fromJson({
        'word': '답답하다',
        'definition': '마음이 막힌 듯 무겁고 풀리지 않는 느낌',
        'example': '이야기할 사람이 없을 때 가슴이 답답해진다.',
        'valence': -0.4,
        'arousal': -0.2,
        'neighbors': [
          {'word': '막막하다', 'direction': '더 무겁다면', 'delta_v': -0.1, 'delta_a': -0.1},
          {'word': '지친다', 'direction': '더 가라앉아있다면', 'delta_v': -0.1, 'delta_a': -0.3},
        ],
      });
      expect(w.word, '답답하다');
      expect(w.valence, -0.4);
      expect(w.neighbors.length, 2);
      expect(w.neighbors[0].word, '막막하다');
      expect(w.neighbors[0].direction, '더 무겁다면');
    });

    test('neighbors 없어도 파싱 가능', () {
      final w = EmotionWord.fromJson({
        'word': '차분하다',
        'definition': '잔잔한 상태',
        'example': '심호흡을 했다',
        'valence': 0.3,
        'arousal': -0.4,
      });
      expect(w.neighbors, isEmpty);
    });
  });

  group('EmotionSelectResult.fromJson', () {
    test('분기 개입 타입 — self_distancing (Q3)', () {
      final r = EmotionSelectResult.fromJson({
        'emotion_id': 'abc',
        'selected_word': '답답하다',
        'intensity': 3,
        'intervention_type': 'self_distancing',
      });
      expect(r.interventionType, 'self_distancing');
    });

    test('분기 개입 타입 — grounding (Q2)', () {
      final r = EmotionSelectResult.fromJson({
        'emotion_id': 'abc',
        'selected_word': '긴장된다',
        'intensity': 4,
        'intervention_type': 'grounding',
      });
      expect(r.interventionType, 'grounding');
    });

    test('분기 개입 타입 — activation (Q1/Q4)', () {
      final r = EmotionSelectResult.fromJson({
        'emotion_id': 'abc',
        'selected_word': '설렌다',
        'intensity': 4,
        'intervention_type': 'activation',
      });
      expect(r.interventionType, 'activation');
    });
  });
}
