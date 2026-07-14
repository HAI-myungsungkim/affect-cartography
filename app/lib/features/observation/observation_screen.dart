import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import '../affect/affect_models.dart';
import '../affect/va_grid_widget.dart';
import 'observation_repository.dart';

/// 실험 축1 — 타인 관찰 화면.
///
/// 정동 기록 '전에' 타인의 정동을 먼저 관찰·기록해, 자기 기록에
/// 객관적 시선을 반영하도록 유도한다.
///  - recall_other  : 주변 실제 인물을 떠올려 관찰
///  - scenario_other: 앱이 제시하는 시나리오 인물을 관찰
/// 저장 후 자기 정동 기록(/record)으로 넘어간다.
class ObservationScreen extends ConsumerStatefulWidget {
  final String mode; // recall_other / scenario_other
  const ObservationScreen({super.key, required this.mode});

  @override
  ConsumerState<ObservationScreen> createState() => _ObservationScreenState();
}

class _ObservationScreenState extends ConsumerState<ObservationScreen> {
  AffectPoint? _point;
  int _resetSignal = 0;
  bool _saving = false;
  final _wordCtl = TextEditingController();

  // 시나리오 모드일 때 선택된 시나리오 (기본: 첫 번째)
  late ObservationScenario _scenario = observationScenarios.first;

  bool get _isScenario => widget.mode == 'scenario_other';

  @override
  void dispose() {
    _wordCtl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_point == null || _saving) return;
    setState(() => _saving = true);
    try {
      await ref.read(observationRepositoryProvider).save(
            targetType: widget.mode,
            scenarioId: _isScenario ? _scenario.id : null,
            valence: _point!.valence,
            arousal: _point!.arousal,
            emotionWord: _wordCtl.text.trim(),
          );
      if (!mounted) return;
      // 관찰 완료 → 자기 정동 기록으로
      context.go('/record');
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('저장 실패: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.go('/home'),
        ),
        title: const Text('먼저, 다른 사람을 관찰해보세요'),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _buildPrompt(context),
              const SizedBox(height: 16),
              Text(
                '그 사람의 정동은 어디쯤일까요? 격자를 눌러 표시해보세요.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 13.5,
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 12),
              AspectRatio(
                aspectRatio: 1,
                child: VAGridWidget(
                  mode: AffectMode.point,
                  resetSignal: _resetSignal,
                  onPointSelected: (p) => setState(() => _point = p),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _wordCtl,
                decoration: InputDecoration(
                  labelText: '그 사람의 감정 (선택)',
                  hintText: '떠오르는 단어가 있다면',
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              ElevatedButton(
                onPressed: (_point != null && !_saving) ? _save : null,
                child: _saving
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(
                            color: Colors.white, strokeWidth: 2.5),
                      )
                    : const Text('관찰 완료 · 내 기록으로'),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildPrompt(BuildContext context) {
    if (_isScenario) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // 시나리오 선택 (여러 개 중 하나)
          SizedBox(
            height: 36,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: observationScenarios.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final s = observationScenarios[i];
                final selected = s.id == _scenario.id;
                return ChoiceChip(
                  label: Text(s.title),
                  selected: selected,
                  onSelected: (_) => setState(() {
                    _scenario = s;
                    _point = null;
                    _resetSignal++;
                    _wordCtl.clear();
                  }),
                );
              },
            ),
          ),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.accentBeige.withOpacity(0.4),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              _scenario.body,
              style: const TextStyle(fontSize: 14.5, height: 1.6),
            ),
          ),
        ],
      );
    }
    // recall_other 안내 멘트
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.accentBeige.withOpacity(0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        '오늘 마주친 사람 중 한 명을 떠올려보세요. '
        '가족, 친구, 혹은 스쳐 지나간 낯선 사람도 좋아요.\n\n'
        '그 사람의 표정과 몸짓을 잠시 그려보고, '
        '그 사람이 지금 어떤 상태일지 상상해보세요.',
        style: const TextStyle(fontSize: 14.5, height: 1.6),
      ),
    );
  }
}
