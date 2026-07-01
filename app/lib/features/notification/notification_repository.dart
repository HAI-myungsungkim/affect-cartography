import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import 'notification_models.dart';

class NotificationRepository {
  final ApiClient _api;
  NotificationRepository(this._api);

  Future<NotificationSettings> getSettings() async {
    final r = await _api.dio.get('/notification/settings');
    return NotificationSettings.fromJson(r.data as Map<String, dynamic>);
  }

  Future<NotificationSettings> updateSettings({
    TimeWindow? morning,
    TimeWindow? afternoon,
    TimeWindow? evening,
  }) async {
    final body = <String, dynamic>{};
    if (morning != null) body['morning'] = morning.toJson();
    if (afternoon != null) body['afternoon'] = afternoon.toJson();
    if (evening != null) body['evening'] = evening.toJson();
    final r = await _api.dio.put('/notification/settings', data: body);
    return NotificationSettings.fromJson(r.data as Map<String, dynamic>);
  }

  Future<TodaySchedule> getTodaySchedule() async {
    final r = await _api.dio.get('/notification/today');
    return TodaySchedule.fromJson(r.data as Map<String, dynamic>);
  }
}

final notificationRepositoryProvider = Provider<NotificationRepository>((ref) {
  return NotificationRepository(ref.read(apiClientProvider));
});
