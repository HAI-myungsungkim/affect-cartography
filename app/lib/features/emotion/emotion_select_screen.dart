import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import 'emotion_repository.dart';

/// 감정 기록 화면 — 서술형 (한 화면에 서술 + 강도).
///
/// 감정에는 true value가 없다는 연구 철학에 따라, 사전에서 고르는 대신
/// 지금 느끼는 감정을 자유롭게 서술(단어/문장)하고 강도(1~5)를 고른다.
/// 서술과 강도를 같은 화면에 두어, 쓰면서 강도를 함께 가늠하게 한다.
///
/// (현재 개입 단계는 비활성화 — 저장 후 완료 화면으로.
///  정동→감정 기록 자체에 집중.)
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
  ConsumerState<EmotionSelectScreen> createState() =>
      _EmotionSelectScreenState();
}

class _EmotionSelectScreenState extends ConsumerState<EmotionSelectScreen> {
  final _textCtl = TextEditingController();
  int? _intensity;
  bool _saving = false;
  String? _error;

  static const _intensityLabels = ['아주 약함', '약함', '보통', '강함', '아주 강함'];

  @override
  void dispose() {
    _textCtl.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _textCtl.text.trim().isNotEmpty && _intensity != null && !_saving;

  Future<void> _submit() async {
    if (!_canSubmit) return;
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await ref.read(emotionRepositoryProvider).saveFreeText(
            recordId: widget.recordId,
            freeText: _textCtl.text.trim(),
            intensity: _intensity!,
          );
      if (!mounted) return;
      // 개입 비활성화 — 기록 완료 화면으로
      context.go('/done');
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = '$e';
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
        title: const Text('지금 감정'),
      ),
      body: SafeArea(
        child: _saving
            ? const Center(child: CircularProgressIndicator())
            : SingleChildScrollView(
                padding:
                    const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Text(
                      '지금 느끼는 감정을 자유롭게 적어주세요.\n'
                      '한 단어여도, 문장이어도 좋아요.',
                      style: TextStyle(
                        fontSize: 14.5,
                        color: AppColors.textSecondary,
                        height: 1.5,
                      ),
                    ),
                    const SizedBox(height: 20),
                    TextField(
                      controller: _textCtl,
                      minLines: 3,
                      maxLines: 8,
                      autofocus: true,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        filled: true,
                        fillColor: Theme.of(context).colorScheme.surface,
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12),
                        ),
                        contentPadding: const EdgeInsets.all(16),
                      ),
                    ),
                    const SizedBox(height: 28),
                    Text(
                      '이 감정은 얼마나 강한가요?',
                      style: TextStyle(
                        fontSize: 14.5,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 14),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        for (var i = 1; i <= 5; i++)
                          GestureDetector(
                            onTap: () => setState(() => _intensity = i),
                            child: Container(
                              width: 56,
                              height: 56,
                              decoration: BoxDecoration(
                                color: _intensity == i
                                    ? AppColors.primary
                                    : AppColors.primary.withOpacity(0.15),
                                shape: BoxShape.circle,
                              ),
                              alignment: Alignment.center,
                              child: Text(
                                '$i',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w700,
                                  color: _intensity == i
                                      ? Colors.white
                                      : AppColors.primary,
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(_intensityLabels.first,
                            style: TextStyle(
                                fontSize: 11,
                                color: AppColors.textSecondary)),
                        Text(_intensityLabels.last,
                            style: TextStyle(
                                fontSize: 11,
                                color: AppColors.textSecondary)),
                      ],
                    ),
                    const SizedBox(height: 32),
                    if (_error != null) ...[
                      Text(_error!,
                          style: const TextStyle(
                              color: AppColors.error, fontSize: 13)),
                      const SizedBox(height: 12),
                    ],
                    ElevatedButton(
                      onPressed: _canSubmit ? _submit : null,
                      child: const Text('기록 완료'),
                    ),
                    const SizedBox(height: 20),
                  ],
                ),
              ),
      ),
    );
  }
}
