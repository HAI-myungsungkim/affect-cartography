import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api_client.dart';
import '../../core/providers.dart';
import 'dashboard_models.dart';

class DashboardRepository {
  final ApiClient _api;
  DashboardRepository(this._api);

  Future<DashboardData> fetchMyDashboard({int days = 28}) async {
    final r = await _api.dio.get('/dashboard/me',
        queryParameters: {'days': days});
    return DashboardData.fromJson(r.data as Map<String, dynamic>);
  }
}

final dashboardRepositoryProvider = Provider<DashboardRepository>((ref) {
  return DashboardRepository(ref.read(apiClientProvider));
});
