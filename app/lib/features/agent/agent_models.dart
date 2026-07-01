/// 에이전트 대화 도메인 모델.
enum Speaker { user, agent }

class DialogueTurn {
  final int turnIndex;
  final Speaker speaker;
  final String text;
  final DateTime timestamp;

  const DialogueTurn({
    required this.turnIndex,
    required this.speaker,
    required this.text,
    required this.timestamp,
  });
}

class TurnResult {
  final int turnIndex;
  final String agentMessage;
  final bool isFinal;
  final bool safetyFlagRaised;
  final String? crisisFlagType;

  const TurnResult({
    required this.turnIndex,
    required this.agentMessage,
    required this.isFinal,
    required this.safetyFlagRaised,
    this.crisisFlagType,
  });

  factory TurnResult.fromJson(Map<String, dynamic> json) => TurnResult(
        turnIndex: json['turn_index'] as int,
        agentMessage: json['agent_message'] as String,
        isFinal: json['is_final'] as bool? ?? false,
        safetyFlagRaised: json['safety_flag_raised'] as bool? ?? false,
        crisisFlagType: json['crisis_flag_type'] as String?,
      );
}
