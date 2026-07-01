import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import 'emotion_models.dart';
import 'emotion_repository.dart';

/// 사양서 4.5 + 4.6 + 4.7 통합 화면.
///
/// 3개 페이즈:
///   1) 1차 후보 (정동 좌표 인근 5개 + "여기 없어요")
///   2) 인접 단어 탐색 (중앙 단어 + 4방향 인접)
///   3) 강도 1~5 선택
class EmotionSelectScreen extends ConsumerStatefulWidget {
  final String recordId;
  final double valence;
  final double arousal;

  const EmotionSelectScreen({
    super.key,
    required this.recordId,
    required this.valence,
    required this.arousal,
  });

  @override
  ConsumerState<EmotionSelectScreen> createState() => _EmotionSelectScreenState();
}

enum _Phase { candidates, explore, intensity }

class _EmotionSelectScreenState extends ConsumerState<EmotionSelectScreen> {
  _Phase _phase = _Phase.candidates;
  bool _loading = false;
  String? _error;

  // 1차 후보
  List<EmotionWord> _candidates = [];

  // 인접 탐색
  NeighborWords? _current;
  final List<String> _explorationPath = []; // 거쳐온 단어들

  // 강도
  int? _intensity;

  @override
  void initState() {
    super.initState();
    _loadCandidates();
  }

  Future<void> _loadCandidates() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final list = await ref.read(emotionRepositoryProvider).getCandidates(
            valence: widget.valence,
            arousal: widget.arousal,
            limit: 5,
          );
      if (!mounted) return;
      setState(() {
        _candidates = list;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  Future<void> _pickCandidate(EmotionWord w) async {
    setState(() => _explorationPath.add(w.word));
    await _loadNeighbors(w.word);
  }

  Future<void> _pickNeighbor(EmotionWord w) async {
    setState(() => _explorationPath.add(w.word));
    await _loadNeighbors(w.word);
  }

  Future<void> _loadNeighbors(String word) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final n = await ref.read(emotionRepositoryProvider).getNeighbors(word);
      if (!mounted) return;
      setState(() {
        _current = n;
        _phase = _Phase.explore;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
    }
  }

  void _confirmThisWord() {
    setState(() => _phase = _Phase.intensity);
  }

  Future<void> _submitIntensity(int i) async {
    if (_current == null) return;
    setState(() {
      _intensity = i;
      _loading = true;
      _error = null;
    });
    try {
      final result = await ref.read(emotionRepositoryProvider).select(
            recordId: widget.recordId,
            selectedWord: _current!.center.word,
            intensity: i,
            explorationPath: _explorationPath,
          );
      if (!mounted) return;
      // 7단계 분기 개입 화면으로
      context.go('/intervention/${widget.recordId}');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '$e';
        _loading = false;
      });
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
        title: Text(_titleForPhase()),
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _ErrorView(message: _error!, onRetry: () {
                    if (_phase == _Phase.candidates) {
                      _loadCandidates();
                    }
                  })
                : _buildBody(),
      ),
    );
  }

  String _titleForPhase() {
    switch (_phase) {
      case _Phase.candidates:
        return '지금 느낌과 가까운 단어';
      case _Phase.explore:
        return '단어 살펴보기';
      case _Phase.intensity:
        return '강도';
    }
  }

  Widget _buildBody() {
    switch (_phase) {
      case _Phase.candidates:
        return _CandidatesView(
          candidates: _candidates,
          onPick: _pickCandidate,
          onNoneFit: () {
            // "여기 없어요" — 인접 탐색의 시작점으로 첫 후보를 사용
            if (_candidates.isNotEmpty) {
              _pickCandidate(_candidates.first);
            }
          },
        );
      case _Phase.explore:
        return _ExploreView(
          data: _current!,
          path: _explorationPath,
          onPickNeighbor: _pickNeighbor,
          onConfirm: _confirmThisWord,
        );
      case _Phase.intensity:
        return _IntensityView(
          word: _current!.center.word,
          onSelect: _submitIntensity,
        );
    }
  }
}

// === 1차 후보 ===

class _CandidatesView extends StatelessWidget {
  final List<EmotionWord> candidates;
  final ValueChanged<EmotionWord> onPick;
  final VoidCallback onNoneFit;

  const _CandidatesView({
    required this.candidates,
    required this.onPick,
    required this.onNoneFit,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      children: [
        Text(
          '지금 느낌과 가장 가까운 단어를 골라주세요',
          style: TextStyle(
            fontSize: 14,
            color: AppColors.textSecondary,
            height: 1.5,
          ),
        ),
        const SizedBox(height: 20),
        for (final w in candidates) ...[
          _WordButton(word: w, onTap: () => onPick(w)),
          const SizedBox(height: 10),
        ],
        const SizedBox(height: 8),
        OutlinedButton(
          onPressed: onNoneFit,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(52),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
          child: const Text('여기 없어요'),
        ),
      ],
    );
  }
}

class _WordButton extends StatelessWidget {
  final EmotionWord word;
  final VoidCallback onTap;
  const _WordButton({required this.word, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              word.word,
              style: const TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              word.definition,
              style: TextStyle(
                fontSize: 13,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// === 인접 탐색 ===

class _ExploreView extends StatelessWidget {
  final NeighborWords data;
  final List<String> path;
  final ValueChanged<EmotionWord> onPickNeighbor;
  final VoidCallback onConfirm;

  const _ExploreView({
    required this.data,
    required this.path,
    required this.onPickNeighbor,
    required this.onConfirm,
  });

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      children: [
        if (path.length > 1) ...[
          Wrap(
            spacing: 6,
            children: [
              for (var i = 0; i < path.length; i++) ...[
                Text(
                  path[i],
                  style: TextStyle(
                    fontSize: 12,
                    color: i == path.length - 1
                        ? AppColors.primary
                        : AppColors.textSecondary,
                    fontWeight: i == path.length - 1
                        ? FontWeight.w600
                        : FontWeight.w400,
                  ),
                ),
                if (i < path.length - 1)
                  Text('→',
                      style: TextStyle(
                          fontSize: 12, color: AppColors.textSecondary)),
              ],
            ],
          ),
          const SizedBox(height: 16),
        ],
        // 중앙 단어 카드
        Container(
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.accentSage.withOpacity(0.25),
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              Text(
                data.center.word,
                style: const TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primary,
                ),
              ),
              const SizedBox(height: 10),
              Text(
                data.center.definition,
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 13.5, height: 1.5),
              ),
              const SizedBox(height: 8),
              Text(
                '"${data.center.example}"',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 12.5,
                  fontStyle: FontStyle.italic,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        Text(
          '이 단어와 비슷한 다른 표현들',
          style: TextStyle(
            fontSize: 13,
            color: AppColors.textSecondary,
          ),
        ),
        const SizedBox(height: 10),
        for (var i = 0; i < data.neighbors.length; i++) ...[
          _NeighborButton(
            word: data.neighbors[i],
            direction: data.center.neighbors.length > i
                ? data.center.neighbors[i].direction
                : '',
            onTap: () => onPickNeighbor(data.neighbors[i]),
          ),
          const SizedBox(height: 8),
        ],
        const SizedBox(height: 16),
        ElevatedButton(
          onPressed: onConfirm,
          child: Text('"${data.center.word}"(으)로 결정'),
        ),
      ],
    );
  }
}

class _NeighborButton extends StatelessWidget {
  final EmotionWord word;
  final String direction;
  final VoidCallback onTap;
  const _NeighborButton({
    required this.word,
    required this.direction,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    word.word,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  if (direction.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      direction,
                      style: TextStyle(
                        fontSize: 12,
                        color: AppColors.accentSage,
                      ),
                    ),
                  ],
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: AppColors.textSecondary),
          ],
        ),
      ),
    );
  }
}

// === 강도 ===

class _IntensityView extends StatelessWidget {
  final String word;
  final ValueChanged<int> onSelect;
  const _IntensityView({required this.word, required this.onSelect});

  static const _labels = ['아주 약함', '약함', '보통', '강함', '아주 강함'];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: AppColors.accentSage.withOpacity(0.25),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              children: [
                Text(
                  word,
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: AppColors.primary,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  '이 감정의 강도는?',
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 40),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              for (var i = 1; i <= 5; i++)
                _IntensityButton(
                  value: i,
                  label: _labels[i - 1],
                  onTap: () => onSelect(i),
                ),
            ],
          ),
          const SizedBox(height: 20),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text('아주 약함',
                    style: TextStyle(
                        fontSize: 11, color: AppColors.textSecondary)),
                Text('아주 강함',
                    style: TextStyle(
                        fontSize: 11, color: AppColors.textSecondary)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _IntensityButton extends StatelessWidget {
  final int value;
  final String label;
  final VoidCallback onTap;
  const _IntensityButton({
    required this.value,
    required this.label,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 56,
        height: 56,
        decoration: BoxDecoration(
          color: AppColors.primary,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Text(
          '$value',
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w700,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline, color: AppColors.error, size: 36),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: onRetry, child: const Text('다시 시도')),
          ],
        ),
      ),
    );
  }
}
