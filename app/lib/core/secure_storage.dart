import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// JWT 토큰·디바이스 ID 등 민감 데이터를 OS 보안 저장소(iOS Keychain / Android EncryptedSharedPreferences)에 보관.
class SecureStorage {
  static const _opts = AndroidOptions(encryptedSharedPreferences: true);
  static const _storage = FlutterSecureStorage(aOptions: _opts);

  // 키
  static const _kToken = 'jwt_access_token';
  static const _kDeviceId = 'device_id';
  static const _kUserId = 'user_id';
  static const _kParticipantCode = 'participant_code';
  static const _kRealName = 'real_name';
  static const _kRecordMode = 'record_mode';
  static const _kTrajPracticeDone = 'trajectory_practice_done';
  // 실험 조건 축 (로그인 응답 / 조건 변경 시 갱신)
  static const _kObservationMode = 'observation_mode';
  static const _kEmotionTiming = 'emotion_timing';
  static const _kAgentMode = 'agent_mode';
  static const _kEducationEnabled = 'education_enabled';

  Future<void> saveLogin({
    required String token,
    required String userId,
    required String participantCode,
    required String realName,
    required String recordMode,
    required bool trajectoryPracticeDone,
    required String observationMode,
    required String emotionTiming,
    required String agentMode,
    required bool educationEnabled,
  }) async {
    await _storage.write(key: _kToken, value: token);
    await _storage.write(key: _kUserId, value: userId);
    await _storage.write(key: _kParticipantCode, value: participantCode);
    await _storage.write(key: _kRealName, value: realName);
    await _storage.write(key: _kRecordMode, value: recordMode);
    await _storage.write(
      key: _kTrajPracticeDone,
      value: trajectoryPracticeDone.toString(),
    );
    await saveConditions(
      recordMode: recordMode,
      observationMode: observationMode,
      emotionTiming: emotionTiming,
      agentMode: agentMode,
      educationEnabled: educationEnabled,
    );
  }

  /// 실험 조건 축만 갱신 (개발자 설정 화면에서 변경 후 로컬 반영).
  Future<void> saveConditions({
    required String recordMode,
    required String observationMode,
    required String emotionTiming,
    required String agentMode,
    required bool educationEnabled,
  }) async {
    await _storage.write(key: _kRecordMode, value: recordMode);
    await _storage.write(key: _kObservationMode, value: observationMode);
    await _storage.write(key: _kEmotionTiming, value: emotionTiming);
    await _storage.write(key: _kAgentMode, value: agentMode);
    await _storage.write(
      key: _kEducationEnabled,
      value: educationEnabled.toString(),
    );
  }

  Future<String?> getToken() => _storage.read(key: _kToken);
  Future<String?> getUserId() => _storage.read(key: _kUserId);
  Future<String?> getRealName() => _storage.read(key: _kRealName);
  Future<String?> getParticipantCode() =>
      _storage.read(key: _kParticipantCode);
  Future<String?> getRecordMode() => _storage.read(key: _kRecordMode);

  Future<bool> getTrajectoryPracticeDone() async {
    final v = await _storage.read(key: _kTrajPracticeDone);
    return v == 'true';
  }

  // 실험 조건 축 조회 (기본값은 각 축의 '없음/대조군' 값)
  Future<String> getObservationMode() async =>
      await _storage.read(key: _kObservationMode) ?? 'self_only';
  Future<String> getEmotionTiming() async =>
      await _storage.read(key: _kEmotionTiming) ?? 'immediate';
  Future<String> getAgentMode() async =>
      await _storage.read(key: _kAgentMode) ?? 'none';
  Future<bool> getEducationEnabled() async =>
      (await _storage.read(key: _kEducationEnabled)) == 'true';

  /// 디바이스 ID — 한 번 생성하면 절대 변경되지 않아야 함 (엄격 바인딩 정책).
  Future<String?> getDeviceId() => _storage.read(key: _kDeviceId);

  Future<void> setDeviceId(String id) =>
      _storage.write(key: _kDeviceId, value: id);

  /// 로그아웃 시 토큰만 삭제. 디바이스 ID는 보존 (재로그인 시 동일 ID 필요).
  Future<void> clearAuth() async {
    await _storage.delete(key: _kToken);
    await _storage.delete(key: _kUserId);
    await _storage.delete(key: _kParticipantCode);
    await _storage.delete(key: _kRealName);
    await _storage.delete(key: _kRecordMode);
    await _storage.delete(key: _kTrajPracticeDone);
    await _storage.delete(key: _kObservationMode);
    await _storage.delete(key: _kEmotionTiming);
    await _storage.delete(key: _kAgentMode);
    await _storage.delete(key: _kEducationEnabled);
  }

  Future<bool> hasValidSession() async {
    final t = await getToken();
    return t != null && t.isNotEmpty;
  }
}
