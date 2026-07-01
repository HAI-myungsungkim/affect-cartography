import 'package:flutter_test/flutter_test.dart';
import 'package:affect_cartography/features/affect/affect_models.dart';

void main() {
  group('AffectPoint', () {
    test('toJson 직렬화', () {
      const p = AffectPoint(-0.4, 0.2, 350);
      expect(p.toJson(), {'v': -0.4, 'a': 0.2, 't': 350});
    });

    test('기본 t는 0', () {
      const p = AffectPoint(0.1, 0.2);
      expect(p.tMs, 0);
    });
  });

  group('AffectMode', () {
    test('apiValue 매핑', () {
      expect(AffectMode.point.apiValue, 'point');
      expect(AffectMode.trajectory.apiValue, 'trajectory');
    });

    test('labelKo 한국어 라벨', () {
      expect(AffectMode.point.labelKo, '점 모드');
      expect(AffectMode.trajectory.labelKo, '궤도 모드');
    });
  });

  group('practiceScenarios (사양서 4.3.3)', () {
    test('정확히 3개의 시나리오', () {
      expect(practiceScenarios.length, 3);
    });

    test('첫 시나리오 — 발표/긴장 → 후련+들뜸 (3점 궤적)', () {
      final s = practiceScenarios[0];
      expect(s.expectedKind, TrajectoryInputKind.drawn);
      expect(s.examplePath.length, 3);
      expect(s.examplePath.last.valence, greaterThan(0)); // 끝점은 유쾌
      expect(s.examplePath.last.arousal, greaterThan(0)); // 끝점은 고각성
    });

    test('두 번째 시나리오 — 잔잔함은 단일 점', () {
      final s = practiceScenarios[1];
      expect(s.expectedKind, TrajectoryInputKind.pointHold);
      expect(s.examplePath.length, 1);
    });

    test('세 번째 시나리오 — 우상→좌하 대각', () {
      final s = practiceScenarios[2];
      expect(s.examplePath.first.valence, greaterThan(0));
      expect(s.examplePath.first.arousal, greaterThan(0));
      expect(s.examplePath.last.valence, lessThan(0));
      expect(s.examplePath.last.arousal, lessThan(0));
    });
  });
}
