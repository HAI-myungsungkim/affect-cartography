/// 분기 개입 도메인 모델.
class InterventionPrompt {
  final String interventionType;
  final String title;
  final String body;
  final String placeholder;
  final bool allowSkip;

  const InterventionPrompt({
    required this.interventionType,
    required this.title,
    required this.body,
    required this.placeholder,
    required this.allowSkip,
  });

  factory InterventionPrompt.fromJson(Map<String, dynamic> j) =>
      InterventionPrompt(
        interventionType: j['intervention_type'] as String,
        title: j['title'] as String,
        body: j['body'] as String,
        placeholder: j['placeholder'] as String,
        allowSkip: j['allow_skip'] as bool? ?? true,
      );
}
