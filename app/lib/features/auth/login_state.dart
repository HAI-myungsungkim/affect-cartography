/// 로그인 화면 상태.
sealed class LoginState {
  const LoginState();
}

class LoginIdle extends LoginState {
  const LoginIdle();
}

class LoginLoading extends LoginState {
  const LoginLoading();
}

class LoginSuccess extends LoginState {
  final bool firstLogin;
  final String realName;
  const LoginSuccess({required this.firstLogin, required this.realName});
}

/// 사양서 4.1 — 두 종류의 명시적 에러를 화면에 다르게 표시한다.
enum LoginErrorKind {
  codeNotRegistered,    // "등록되지 않은 코드입니다"
  deviceMismatch,       // "이 코드는 다른 기기에 등록되어 있습니다. 연구진에게 문의하세요"
  userDropped,          // 연구 종료된 계정
  network,
  unknown,
}

class LoginError extends LoginState {
  final LoginErrorKind kind;
  final String message;
  const LoginError(this.kind, this.message);
}
