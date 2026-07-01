import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../shared/theme/app_theme.dart';
import 'affect_models.dart';
import 'va_grid_widget.dart';

/// 사양서 4.3.3 — 궤도 모드 연습 세션.
/// 3개 시나리오를 차례로 안내. 사용자가 직접 그려본 후 예시 궤적을 함께 표시.
class PracticeSessionScreen extends ConsumerStatefulWidget {
  const PracticeSessionScreen({super.key});

  @override
  ConsumerState<PracticeSessionScreen> createState() =>
      _PracticeSessionScreenState();
}

class _PracticeSessionScreenState extends ConsumerState<PracticeSessionScreen> {
  int _index = 0;
  bool _showExample = false;
  int _resetSignal = 0;
  List<AffectPoint> _userInput = [];

  PracticeScenario get _current => practiceScenarios[_index];

  void _next() {
    if (_index >= practiceScenarios.length - 1) {
      Navigator.of(context).pop(true);
      return;
    }
    setState(() {
      _index++;
      _showExample = false;
      _userInput = [];
      _resetSignal++;
    });
  }

  void _skip() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('건너뛰시겠어요?'),
        content: const Text('나중에 설정에서 다시 시도할 수 있어요.'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('계속하기'),
          ),
          TextButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              Navigator.of(context).pop(false);
            },
            child: const Text('건너뛰기'),
          ),
        ],
      ),
    );
  }

  void _showExampleTrajectory() {
    setState(() => _showExample = true);
  }

  @override
  Widget build(BuildContext context) {
    final isLast = _index == practiceScenarios.length - 1;
    final hasInput = _userInput.isNotEmpty;

    return Scaffold(
      appBar: AppBar(
        title: Text('연습 ${_index + 1} / ${practiceScenarios.length}'),
        actions: [
          TextButton(
            onPressed: _skip,
            child: const Text('건너뛰기'),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          child: Column(
            children: [
              if (_index == 0)
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: AppColors.accentBeige.withOpacity(0.4),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    '궤도 모드는 처음이시군요. 잠깐 같이 연습해볼까요?',
                    style: TextStyle(
                      color: AppColors.textPrimary,
                      fontSize: 13.5,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              const SizedBox(height: 12),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: const Color(0xFFE5E7EB)),
                ),
                child: Text(
                  _current.description,
                  style: const TextStyle(fontSize: 14, height: 1.5),
                ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: Center(
                  child: AspectRatio(
                    aspectRatio: 1,
                    child: VAGridWidget(
                      mode: AffectMode.trajectory,
                      resetSignal: _resetSignal,
                      exampleOverlay:
                          _showExample ? _current.examplePath : null,
                      onTrajectoryComplete: (pts) =>
                          setState(() => _userInput = pts),
                    ),
                  ),
                ),
              ),
              if (_showExample) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.accentSage.withOpacity(0.25),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.lightbulb_outline,
                          color: AppColors.accentSage),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _current.hint,
                          style: const TextStyle(fontSize: 13, height: 1.4),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 14),
              if (!_showExample)
                ElevatedButton(
                  onPressed: hasInput ? _showExampleTrajectory : null,
                  child: const Text('예시 궤적 보기'),
                )
              else
                ElevatedButton(
                  onPressed: _next,
                  child: Text(isLast ? '연습 마치기' : '다음 예시'),
                ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}
