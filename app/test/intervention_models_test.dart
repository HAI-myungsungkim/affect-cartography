import 'package:flutter_test/flutter_test.dart';
import 'package:affect_cartography/features/intervention/intervention_models.dart';

void main() {
  group('InterventionPrompt.fromJson', () {
    test('self_distancing 파싱', () {
      final p = InterventionPrompt.fromJson({
        'intervention_type': 'self_distancing',
        'title': '잠깐, 한 걸음 떨어져 볼까요?',
        'body': '지금 철수 씨는 어떤 상황에 있는 것 같나요?',
        'placeholder': '3인칭 시점으로...',
        'allow_skip': true,
      });
      expect(p.interventionType, 'self_distancing');
      expect(p.title, contains('한 걸음'));
      expect(p.body, contains('철수'));
      expect(p.allowSkip, true);
    });

    test('grounding 파싱', () {
      final p = InterventionPrompt.fromJson({
        'intervention_type': 'grounding',
        'title': '지금, 여기로 돌아오기',
        'body': '호흡을 천천히 세 번',
        'placeholder': '한 줄',
      });
      expect(p.interventionType, 'grounding');
      expect(p.body, contains('호흡'));
    });

    test('activation 파싱 — if-then 형식', () {
      final p = InterventionPrompt.fromJson({
        'intervention_type': 'activation',
        'title': '작게 한 가지',
        'body': '만약 [상황]이 되면, 나는 [구체적 행동]을 하겠다',
        'placeholder': '만약 점심을 다 먹으면...',
      });
      expect(p.body, contains('만약'));
    });
  });
}
