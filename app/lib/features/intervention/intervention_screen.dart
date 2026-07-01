import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import 'intervention_models.dart';
import 'intervention_repository.dart';

/// 사양서 4.8 — 분기 개입 화면.
/// 자기거리두기 / 그라운딩 / 행동활성화 셋 중 하나가 표시됨.
class InterventionScreen extends ConsumerStatefulWidget {
  final String recordId;
  const InterventionScreen({super.key, required this.recordId});

  @override
  ConsumerState<InterventionScreen> createState() => _InterventionScreenState();
}

class _InterventionScreenState extends ConsumerState<InterventionScreen> {
  InterventionPrompt? _prompt;
  bool _loading = true;
  bool _saving = false;
  String? _error;
  final _inputCtl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _loadPrompt();
  }

  Future<void> _loadPrompt() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final p = await ref.read(interventionRepositoryProvider).getPrompt(widget.recordId);
      if (!mounted) return;
      setState(() {
        _prompt = p;
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

  Future<void> _submit({required bool withText}) async {
    if (_prompt == null || _saving) return;
    setState(() => _saving = true);
    try {
      await ref.read(interventionRepositoryProvider).submitResponse(
            recordId: widget.recordId,
            interventionType: _prompt!.interventionType,
            userResponseText: withText ? _inputCtl.text : null,
          );
      if (!mounted) return;
      // 기록 완료 화면으로
      context.go('/done');
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('저장 실패: $e')),
      );
    }
  }

  IconData _iconFor(String type) {
    switch (type) {
      case 'grounding':
        return Icons.air;
      case 'activation':
        return Icons.directions_walk;
      default:
        return Icons.psychology_alt;
    }
  }

  Color _accentFor(String type) {
    switch (type) {
      case 'grounding':
        return AppColors.accentSage;
      case 'activation':
        return AppColors.accentBeige;
      default:
        return AppColors.accentSage;
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
      ),
      body: SafeArea(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? _ErrorView(message: _error!, onRetry: _loadPrompt)
                : _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    final p = _prompt!;
    final hasText = _inputCtl.text.trim().isNotEmpty;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: _accentFor(p.interventionType).withOpacity(0.35),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Column(
                      children: [
                        Icon(_iconFor(p.interventionType),
                            size: 36, color: AppColors.primary),
                        const SizedBox(height: 12),
                        Text(
                          p.title,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.w700,
                            color: AppColors.primary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 20),
                  Text(
                    p.body,
                    style: const TextStyle(fontSize: 15.5, height: 1.6),
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _inputCtl,
                    minLines: 3,
                    maxLines: 6,
                    onChanged: (_) => setState(() {}),
                    decoration: InputDecoration(
                      hintText: p.placeholder,
                      contentPadding: const EdgeInsets.all(16),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (hasText)
            ElevatedButton(
              onPressed: _saving ? null : () => _submit(withText: true),
              child: _saving
                  ? const SizedBox(
                      width: 22, height: 22,
                      child: CircularProgressIndicator(
                        color: Colors.white, strokeWidth: 2.5),
                    )
                  : const Text('이대로 저장하기'),
            )
          else ...[
            ElevatedButton(
              onPressed: _saving ? null : () => _submit(withText: false),
              child: const Text('읽었어요'),
            ),
            if (p.allowSkip) ...[
              const SizedBox(height: 8),
              TextButton(
                onPressed: _saving ? null : () => _submit(withText: false),
                child: Text(
                  '건너뛰기',
                  style: TextStyle(color: AppColors.textSecondary),
                ),
              ),
            ],
          ],
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _inputCtl.dispose();
    super.dispose();
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
            const Icon(Icons.error_outline,
                color: AppColors.error, size: 36),
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
