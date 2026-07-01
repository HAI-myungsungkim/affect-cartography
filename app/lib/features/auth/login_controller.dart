import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/secure_storage.dart';
import '../../core/api_client.dart';
import 'login_state.dart';

class LoginController extends StateNotifier<LoginState> {
  final ApiClient _api;
  final SecureStorage _storage;

  LoginController(this._api, this._storage) : super(const LoginIdle());

  Future<void> submit({
    required String participantCode,
    required String realName,
  }) async {
    state = const LoginLoading();
    try {
      final resp = await _api.login(
        participantCode: participantCode.trim(),
        realName: realName.trim(),
      );

      // 백엔드는 4xx도 응답 본문을 돌려주도록 validateStatus 설정됨.
      if (resp.statusCode == 200) {
        final data = resp.data as Map<String, dynamic>;
        await _storage.saveLogin(
          token: data['access_token'] as String,
          userId: data['user_id'] as String,
          participantCode: data['participant_code'] as String,
          realName: data['real_name'] as String,
          recordMode: data['record_mode'] as String,
          trajectoryPracticeDone:
              data['trajectory_practice_done'] as bool? ?? false,
        );
        state = LoginSuccess(
          firstLogin: data['first_login'] as bool? ?? false,
          realName: data['real_name'] as String,
        );
        return;
      }

      // 4xx 에러 분기
      final detail = resp.data is Map ? resp.data['detail'] : null;
      if (detail is Map) {
        final code = detail['code'] as String?;
        final msg = detail['message'] as String? ?? '로그인 실패';
        state = _mapError(code, msg);
      } else {
        state = LoginError(LoginErrorKind.unknown, detail?.toString() ?? '로그인 실패');
      }
    } on DioException catch (e) {
      if (e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.connectionError) {
        state = const LoginError(
            LoginErrorKind.network, '서버에 연결할 수 없습니다. 네트워크 상태를 확인해주세요');
      } else {
        state = LoginError(LoginErrorKind.unknown, e.message ?? '알 수 없는 오류');
      }
    } catch (e) {
      state = LoginError(LoginErrorKind.unknown, e.toString());
    }
  }

  LoginError _mapError(String? code, String msg) {
    switch (code) {
      case 'code_not_registered':
        return LoginError(LoginErrorKind.codeNotRegistered, msg);
      case 'device_mismatch':
        return LoginError(LoginErrorKind.deviceMismatch, msg);
      case 'user_dropped':
        return LoginError(LoginErrorKind.userDropped, msg);
      default:
        return LoginError(LoginErrorKind.unknown, msg);
    }
  }

  void reset() => state = const LoginIdle();
}

final loginControllerProvider =
    StateNotifierProvider<LoginController, LoginState>((ref) {
  return LoginController(
    ref.read(apiClientProvider),
    ref.read(secureStorageProvider),
  );
});
