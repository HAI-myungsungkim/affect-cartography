import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../shared/theme/app_theme.dart';
import 'affect_models.dart';
import 'affect_repository.dart';
import 'practice_session_screen.dart';
import 'va_grid_widget.dart';

/// 사양서 4.3 정동 기록 화면.
/// 사용자 설정 모드(point/trajectory)에 따라 인터랙션 분기.
/// 궤도 모드 + 연습 미완료 시 자동으로 연습 세션 진입(4.3.3).
class AffectRecordScreen extends ConsumerStatefulWidget {
  /// 알림 탭으로 진입한 경우 전달되는 prompt_id (응답률 계산용).
  final String? promptId;
  const AffectRecordScreen({super.key, this.promptId});

  @override
  ConsumerState<AffectRecordScreen> createState() => _AffectRecordScreenState();
}

class _AffectRecordScreenState extends ConsumerState<AffectRecordScreen> {
  AffectMode _mode = AffectMode.point;
  AffectPoint? _selectedPoint;
  List<AffectPoint> _trajectory = [];
  int _resetSignal = 0;
  bool _saving = false;
  late final DateTime _startedAt;

  @override
  void initState() {
    super.initState();
    _startedAt = DateTime.now();
    _loadModeAndMaybeStartPractice();
  }

  Future<void> _loadModeAndMaybeStartPractice() async {
    final storage = ref.read(secureStorageProvider);
    final modeStr = await storage.getRecordMode();
    final practiceDone = await storage.getTrajectoryPracticeDone();

    if (!mounted) return;
    setState(() {
      _mode = modeStr == 'trajectory' ? AffectMode.trajectory : AffectMode.point;
    });

    if (_mode == AffectMode.trajectory && !practiceDone) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _runPractice());
    }
  }

  Future<void> _runPractice() async {
    final result = await Navigator.of(context).push<bool>(
      MaterialPageRoute(builder: (_) => const PracticeSessionScreen()),
    );
    if (result == true) {
      await ref.read(affectRepositoryProvider).markPracticeDone();
    }
  }

  bool get _canProceed {
    if (_mode == AffectMode.point) return _selectedPoint != null;
    return _trajectory.length >= 2 || (_trajectory.length == 1);
  }

  AffectPoint get _endPoint {
    if (_mode == AffectMode.point) return _selectedPoint!;
    return _trajectory.last;
  }

  Future<void> _save() async {
    if (!_canProceed || _saving) return;
    setState(() => _saving = true);
    final latency = DateTime.now().difference(_startedAt).inMilliseconds;
    try {
      final recordId = await ref.read(affectRepositoryProvider).saveRecord(
            mode: _mode,
            endPoint: _endPoint,
            trajectory: _mode == AffectMode.trajectory ? _trajectory : null,
            responseLatencyMs: latency,
            promptId: widget.promptId,
          );
      if (!mounted) return;
      // 저장 완료 → 에이전트 대화 화면으로 자동 다음 단계 진행 (좌표 전달)
      context.go(
        '/dialogue/$recordId?v=${_endPoint.valence}&a=${_endPoint.arousal}',
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('저장 실패: $e')),
      );
    }
  }

  void _redo() {
    setState(() {
      _selectedPoint = null;
      _trajectory = [];
      _resetSignal++;
    });
  }

  Future<void> _toggleMode() async {
    final next = _mode == AffectMode.point ? AffectMode.trajectory : AffectMode.point;
    await ref.read(affectRepositoryProvider).setRecordMode(next.apiValue);
    setState(() {
      _mode = next;
      _selectedPoint = null;
      _trajectory = [];
      _resetSignal++;
    });
    // 궤도 모드로 처음 전환했고 연습 미완료라면 진입
    final practiceDone =
        await ref.read(secureStorageProvider).getTrajectoryPracticeDone();
    if (next == AffectMode.trajectory && !practiceDone && mounted) {
      _runPractice();
    }
  }

  @override
  Widget build(BuildContext context) {
    final guide = _mode == AffectMode.point
        ? '지금 이 순간의 느낌을 가장 잘 나타내는\n위치에 점을 찍어보세요'
        : '지난 3시간 동안 마음의 흐름을\n그려보세요';

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.go('/home'),
        ),
        actions: [
          TextButton.icon(
            onPressed: _toggleMode,
            icon: Icon(_mode == AffectMode.point
                ? Icons.timeline
                : Icons.radio_button_checked),
            label: Text(_mode == AffectMode.point ? '궤도 모드' : '점 모드'),
            style: TextButton.styleFrom(foregroundColor: AppColors.primary),
          ),
        ],
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
          child: Column(
            children: [
              Text(
                guide,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: AppColors.textSecondary,
                      height: 1.4,
                    ),
              ),
              const SizedBox(height: 16),
              Expanded(
                child: Center(
                  child: AspectRatio(
                    aspectRatio: 1,
                    child: VAGridWidget(
                      mode: _mode,
                      resetSignal: _resetSignal,
                      onPointSelected: (p) => setState(() => _selectedPoint = p),
                      onTrajectoryComplete: (pts) =>
                          setState(() => _trajectory = pts),
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              if (_canProceed) ...[
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: _saving ? null : _redo,
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(52),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: const Text('다시 그리기'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      flex: 2,
                      child: ElevatedButton(
                        onPressed: _saving ? null : _save,
                        child: _saving
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  color: Colors.white,
                                  strokeWidth: 2.5,
                                ),
                              )
                            : Text(_mode == AffectMode.point ? '다음' : '이대로 진행'),
                      ),
                    ),
                  ],
                ),
              ] else
                const SizedBox(height: 52),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }
}
