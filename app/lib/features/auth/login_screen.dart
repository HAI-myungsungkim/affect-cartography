import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import 'login_controller.dart';
import 'login_state.dart';

/// 사양서 4.1 — 피험자 코드 + 실명 → 디바이스 바인딩.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _codeCtl = TextEditingController();
  final _nameCtl = TextEditingController();
  final _formKey = GlobalKey<FormState>();

  @override
  void dispose() {
    _codeCtl.dispose();
    _nameCtl.dispose();
    super.dispose();
  }

  bool get _canSubmit =>
      _codeCtl.text.trim().isNotEmpty && _nameCtl.text.trim().isNotEmpty;

  void _onSubmit() {
    if (!_formKey.currentState!.validate()) return;
    ref.read(loginControllerProvider.notifier).submit(
          participantCode: _codeCtl.text,
          realName: _nameCtl.text,
        );
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(loginControllerProvider);

    ref.listen<LoginState>(loginControllerProvider, (prev, next) {
      if (next is LoginSuccess) {
        context.go('/home');
      }
    });

    final isLoading = state is LoginLoading;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24),
          child: Form(
            key: _formKey,
            onChanged: () => setState(() {}),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 80),
                Text(
                  'Affect Cartography',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(height: 12),
                Text(
                  'KAIST 학생 정신건강 연구',
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: AppColors.textSecondary,
                      ),
                ),
                const SizedBox(height: 56),
                TextFormField(
                  controller: _codeCtl,
                  decoration: const InputDecoration(
                    labelText: '피험자 코드',
                    hintText: '예: P001',
                  ),
                  textInputAction: TextInputAction.next,
                  autocorrect: false,
                  enableSuggestions: false,
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? '피험자 코드를 입력해주세요' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _nameCtl,
                  decoration: const InputDecoration(
                    labelText: '실명',
                    hintText: '연구 동의서에 기재된 이름과 동일하게',
                  ),
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) {
                    if (_canSubmit) _onSubmit();
                  },
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? '실명을 입력해주세요' : null,
                ),
                const SizedBox(height: 28),
                ElevatedButton(
                  onPressed: (_canSubmit && !isLoading) ? _onSubmit : null,
                  child: isLoading
                      ? const SizedBox(
                          width: 22,
                          height: 22,
                          child: CircularProgressIndicator(
                            color: Colors.white,
                            strokeWidth: 2.5,
                          ),
                        )
                      : const Text('시작하기'),
                ),
                const SizedBox(height: 16),
                if (state is LoginError)
                  _ErrorBanner(error: state)
                else
                  const SizedBox(height: 60),
                const Spacer(),
                Center(
                  child: TextButton(
                    onPressed: () {
                      // TODO(10단계): 관리자 코드 입력 화면으로 이동
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(
                            '관리자 기능은 PC 웹 대시보드를 이용해주세요.',
                          ),
                          duration: Duration(seconds: 3),
                        ),
                      );
                    },
                    child: Text(
                      '관리자 접근',
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 13,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  final LoginError error;
  const _ErrorBanner({required this.error});

  @override
  Widget build(BuildContext context) {
    final isDeviceMismatch = error.kind == LoginErrorKind.deviceMismatch;
    final isNetwork = error.kind == LoginErrorKind.network;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDeviceMismatch
            ? const Color(0xFFFFF4E6)
            : const Color(0xFFFDECEC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDeviceMismatch
              ? const Color(0xFFE6A23C)
              : const Color(0xFFE57373),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            isDeviceMismatch
                ? Icons.devices_other
                : isNetwork
                    ? Icons.wifi_off
                    : Icons.error_outline,
            color: isDeviceMismatch
                ? const Color(0xFFE6A23C)
                : const Color(0xFFC0392B),
            size: 22,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  error.message,
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (isDeviceMismatch) ...[
                  const SizedBox(height: 8),
                  Text(
                    '기기 변경이 필요하다면 연구진에게 연락해주세요.\n'
                    '관리자가 디바이스 바인딩을 해제해야 다른 기기에서 로그인할 수 있습니다.',
                    style: TextStyle(
                      fontSize: 12.5,
                      color: AppColors.textSecondary,
                      height: 1.4,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}
