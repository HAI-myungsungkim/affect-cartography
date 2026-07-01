import 'package:flutter_test/flutter_test.dart';
import 'package:affect_cartography/features/agent/agent_models.dart';

void main() {
  group('TurnResult.fromJson', () {
    test('일반 응답 파싱', () {
      final r = TurnResult.fromJson({
        'turn_index': 1,
        'agent_message': '어떤 느낌이 가장 먼저 느껴지나요?',
        'is_final': false,
        'safety_flag_raised': false,
      });
      expect(r.turnIndex, 1);
      expect(r.agentMessage, contains('느낌'));
      expect(r.isFinal, false);
      expect(r.safetyFlagRaised, false);
      expect(r.crisisFlagType, isNull);
    });

    test('위기 응답 파싱 — is_final + safety_flag + crisis_flag_type', () {
      final r = TurnResult.fromJson({
        'turn_index': 0,
        'agent_message': '지금 많이 힘드신 것 같아요. ... 1393 ...',
        'is_final': true,
        'safety_flag_raised': true,
        'crisis_flag_type': 'suicide_ideation',
      });
      expect(r.isFinal, true);
      expect(r.safetyFlagRaised, true);
      expect(r.crisisFlagType, 'suicide_ideation');
      expect(r.agentMessage, contains('1393'));
    });

    test('safety_flag_raised 누락 시 기본 false', () {
      final r = TurnResult.fromJson({
        'turn_index': 2,
        'agent_message': '응답',
      });
      expect(r.safetyFlagRaised, false);
      expect(r.isFinal, false);
    });
  });
}
