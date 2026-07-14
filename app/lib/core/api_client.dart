import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';

import 'secure_storage.dart';

/// 백엔드 API 호출용 Dio 클라이언트.
///
/// 매 요청마다:
///  - Authorization: Bearer {jwt}
///  - X-Device-Id: {device_id 평문}    ← 백엔드에서 해시 후 토큰과 대조 (사양서 엄격 바인딩)
class ApiClient {
  final Dio dio;
  final SecureStorage _storage;
  final String _deviceId;

  ApiClient._(this.dio, this._storage, this._deviceId);

  static Future<ApiClient> create({
    required SecureStorage storage,
    required String deviceId,
  }) async {
    final baseUrl = dotenv.env['API_BASE_URL'] ?? 'http://10.0.2.2:8000';

    final dio = Dio(BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: const Duration(seconds: 10),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
      validateStatus: (s) => s != null && s < 500,
    ));

    final client = ApiClient._(dio, storage, deviceId);

    dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        options.headers['X-Device-Id'] = client._deviceId;
        final token = await client._storage.getToken();
        if (token != null && token.isNotEmpty) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        handler.next(options);
      },
    ));

    return client;
  }

  // --- 인증 ---
  Future<Response<dynamic>> login({
    required String participantCode,
    required String realName,
  }) {
    return dio.post('/auth/login', data: {
      'participant_code': participantCode,
      'real_name': realName,
      'device_id': _deviceId,
    });
  }

  // --- 개발/테스트용 실험 조건 ---
  Future<Response<dynamic>> getMyConditions() =>
      dio.get('/auth/me/conditions');

  /// 보낸 필드만 갱신. null은 보내지 않음.
  Future<Response<dynamic>> updateMyConditions(Map<String, dynamic> changes) =>
      dio.patch('/auth/me/conditions', data: changes);

  Future<Response<dynamic>> health() => dio.get('/health');

  Future<Response<dynamic>> crisisResources() => dio.get('/crisis-resources');
}
