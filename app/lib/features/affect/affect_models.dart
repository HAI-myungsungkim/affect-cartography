/// 정동 기록 도메인 모델.
class AffectPoint {
  final double valence;
  final double arousal;
  final int tMs;

  const AffectPoint(this.valence, this.arousal, [this.tMs = 0]);

  Map<String, dynamic> toJson() => {'v': valence, 'a': arousal, 't': tMs};
}

enum AffectMode { point, trajectory }

extension AffectModeX on AffectMode {
  String get apiValue => this == AffectMode.point ? 'point' : 'trajectory';
  String get labelKo => this == AffectMode.point ? '점 모드' : '궤도 모드';
}

/// 사양서 4.3.2의 세 입력 패턴.
enum TrajectoryInputKind {
  none,           // 입력 전
  pointHold,      // 길게 눌러 단일 점
  drawn,          // 드래그로 궤적
}

/// 4.3.3 — 연습 세션 시나리오.
class PracticeScenario {
  final String description;
  final List<AffectPoint> examplePath;
  final String hint;
  final TrajectoryInputKind expectedKind;

  const PracticeScenario({
    required this.description,
    required this.examplePath,
    required this.hint,
    required this.expectedKind,
  });
}

/// 사양서 4.3.3 — 3개 예시.
const practiceScenarios = <PracticeScenario>[
  PracticeScenario(
    description: '수업 시작 전에는 평소처럼 차분했는데, 발표를 하면서 점점 긴장이 올라왔어요. '
        '끝나고는 좀 후련했지만 여전히 들떠 있는 상태예요.',
    examplePath: [
      AffectPoint(0.0, 0.0, 0),       // 중앙
      AffectPoint(-0.5, 0.6, 200),    // 좌상 (긴장)
      AffectPoint(0.5, 0.5, 400),     // 우상 (후련+들뜸)
    ],
    hint: '이런 식으로 그려볼 수 있어요',
    expectedKind: TrajectoryInputKind.drawn,
  ),
  PracticeScenario(
    description: '하루 종일 별 일 없이 잔잔했어요.',
    examplePath: [AffectPoint(0.0, -0.1, 0)],
    hint: '큰 변화가 없을 때는 이렇게 한 점으로도 충분해요',
    expectedKind: TrajectoryInputKind.pointHold,
  ),
  PracticeScenario(
    description: '아침에는 기분이 좋았는데, 점심쯤 안 좋은 소식을 듣고 가라앉았어요.',
    examplePath: [
      AffectPoint(0.6, 0.4, 0),       // 우상
      AffectPoint(-0.5, -0.4, 400),   // 좌하 (가라앉음)
    ],
    hint: '대각선 변화도 자연스럽게 표현됩니다',
    expectedKind: TrajectoryInputKind.drawn,
  ),
];
