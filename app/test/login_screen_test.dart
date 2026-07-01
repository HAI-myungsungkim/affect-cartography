import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:affect_cartography/features/auth/login_screen.dart';
import 'package:affect_cartography/features/auth/login_controller.dart';
import 'package:affect_cartography/features/auth/login_state.dart';

/// 화면 위젯 단위 테스트.
/// 실제 백엔드 호출 없이 LoginController를 fake로 교체해 UI 로직만 검증.
class FakeLoginController extends LoginController {
  FakeLoginController() : super(_FakeApi(), _FakeStorage());

  LoginState? lastResultToEmit;

  @override
  Future<void> submit({
    required String participantCode,
    required String realName,
  }) async {
    state = const LoginLoading();
    await Future.delayed(const Duration(milliseconds: 10));
    if (lastResultToEmit != null) state = lastResultToEmit!;
  }
}

class _FakeApi {
  // dummy — never used (FakeLoginController overrides submit)
  noSuchMethod(Invocation _) => null;
}

class _FakeStorage {
  noSuchMethod(Invocation _) => null;
}

void main() {
  testWidgets('두 필드가 비어있으면 "시작하기" 비활성', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(home: const LoginScreen()),
      ),
    );

    final btn = find.widgetWithText(ElevatedButton, '시작하기');
    expect(btn, findsOneWidget);
    final ElevatedButton button = tester.widget(btn);
    expect(button.onPressed, isNull);
  });

  testWidgets('두 필드 입력 후 버튼 활성화', (tester) async {
    await tester.pumpWidget(
      ProviderScope(child: MaterialApp(home: const LoginScreen())),
    );

    await tester.enterText(find.byType(TextFormField).at(0), 'P001');
    await tester.enterText(find.byType(TextFormField).at(1), '김철수');
    await tester.pump();

    final btn = find.widgetWithText(ElevatedButton, '시작하기');
    final ElevatedButton button = tester.widget(btn);
    expect(button.onPressed, isNotNull);
  });
}
