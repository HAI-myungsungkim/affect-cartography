import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../shared/theme/app_theme.dart';
import '../notification/local_notification_service.dart';
import '../notification/notification_repository.dart';

/// 사양서 4.2 메인 홈.
/// (3단계 정동 기록 화면이 완성되기 전에는 "지금 기록하기" 버튼이 스텁으로 동작)
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  String? _realName;
  // TODO(3단계): 실제 오늘의 응답 상태를 백엔드에서 가져온다
  final int _todayResponseCount = 0;
  final int _todayTargetCount = 3;

  @override
  void initState() {
    super.initState();
    _loadUser();
    _registerTodayNotifications();
  }

  /// 홈 진입 시 오늘의 알림 일정을 OS 에 등록 (세션당 1회).
  Future<void> _registerTodayNotifications() async {
    try {
      await LocalNotificationService.requestPermissions();
      final schedule = await ref
          .read(notificationRepositoryProvider)
          .getTodaySchedule();
      await LocalNotificationService.scheduleToday(schedule);
    } catch (e) {
      // 알림 등록 실패 silent (네트워크 없는 상황 등)
    }
  }

  Future<void> _loadUser() async {
    final name = await ref.read(secureStorageProvider).getRealName();
    if (mounted) setState(() => _realName = name);
  }

  String _today() {
    final n = DateTime.now();
    return '${n.year}년 ${n.month}월 ${n.day}일';
  }

  /// 실험 축1(관찰 대상)에 따라 시작점 분기.
  /// self_only → 바로 정동 기록 / recall·scenario → 관찰 화면 먼저.
  /// 항상 최신값을 쓰도록 서버에서 조건을 조회한다(로컬 캐시 동기화 문제 방지).
  Future<void> _startRecording() async {
    String obsMode = 'self_only';
    try {
      final resp = await ref.read(apiClientProvider).getMyConditions();
      if (resp.statusCode == 200) {
        obsMode = (resp.data['observation_mode'] as String?) ?? 'self_only';
        // 로컬 캐시도 갱신 (다른 화면이 참조)
        await ref.read(secureStorageProvider).saveConditions(
              recordMode: resp.data['record_mode'] as String,
              observationMode: resp.data['observation_mode'] as String,
              emotionTiming: resp.data['emotion_timing'] as String,
              agentMode: resp.data['agent_mode'] as String,
              educationEnabled: resp.data['education_enabled'] as bool,
            );
      }
    } catch (_) {
      // 실패 시 로컬 캐시 폴백
      obsMode = await ref.read(secureStorageProvider).getObservationMode();
    }
    if (!mounted) return;
    if (obsMode == 'recall_other' || obsMode == 'scenario_other') {
      context.go('/observation?mode=$obsMode');
    } else {
      context.go('/record');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Affect Cartography',
          style: TextStyle(fontSize: 16, color: AppColors.textSecondary),
        ),
      ),
      drawer: const _AppDrawer(),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '안녕하세요, ${_realName ?? ""} 님',
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 6),
              Text(
                _today(),
                style: TextStyle(color: AppColors.textSecondary, fontSize: 14),
              ),
              const SizedBox(height: 32),
              _StatusCard(
                completed: _todayResponseCount,
                target: _todayTargetCount,
              ),
              const SizedBox(height: 32),
              ElevatedButton(
                onPressed: _startRecording,
                child: const Text('지금 기록하기'),
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => context.go('/dashboard'),
                style: OutlinedButton.styleFrom(
                  minimumSize: const Size.fromHeight(56),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                child: const Text('대시보드 보기'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusCard extends StatelessWidget {
  final int completed;
  final int target;
  const _StatusCard({required this.completed, required this.target});

  @override
  Widget build(BuildContext context) {
    final ratio = target == 0 ? 0.0 : completed / target;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.accentBeige.withOpacity(0.4),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '오늘의 기록',
            style: TextStyle(
              color: AppColors.textSecondary,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$completed',
                style: const TextStyle(
                  fontSize: 36,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primary,
                ),
              ),
              Text(
                ' / $target 회 완료',
                style: TextStyle(
                  fontSize: 16,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: ratio,
              minHeight: 6,
              backgroundColor: Colors.white,
              valueColor: const AlwaysStoppedAnimation(AppColors.accentSage),
            ),
          ),
        ],
      ),
    );
  }
}

class _AppDrawer extends ConsumerWidget {
  const _AppDrawer();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Drawer(
      child: SafeArea(
        child: ListView(
          children: [
            const SizedBox(height: 12),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Text(
                '메뉴',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: AppColors.textSecondary,
                    ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.notifications_outlined),
              title: const Text('알림 시간대'),
              onTap: () {
                Navigator.pop(context);
                context.push('/notification-settings');
              },
            ),
            ListTile(
              leading: const Icon(Icons.help_outline),
              title: const Text('안내말'),
              onTap: () => Navigator.pop(context),
            ),
            ListTile(
              leading: const Icon(Icons.contact_phone),
              title: const Text('연구진 연락처'),
              onTap: () => Navigator.pop(context),
            ),
            const Divider(),
            // ⚠️ 개발/테스트 전용. 실제 실험 배포 시 이 항목을 숨긴다.
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
              child: Text(
                '개발 도구',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: AppColors.textSecondary,
                  fontSize: 13,
                ),
              ),
            ),
            ListTile(
              leading: const Icon(Icons.tune),
              title: const Text('개발자 설정 · 실험 조건'),
              subtitle: const Text('축을 바꿔 각 흐름 테스트',
                  style: TextStyle(fontSize: 12)),
              onTap: () {
                Navigator.pop(context);
                context.push('/dev-settings');
              },
            ),
            const Divider(),
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
              child: Text(
                '위기 자원',
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: AppColors.error,
                  fontSize: 13,
                ),
              ),
            ),
            const _CrisisResourceTile(
              name: '자살예방상담전화',
              phone: '1393',
              hours: '24시간',
            ),
            const _CrisisResourceTile(
              name: 'KAIST 학생상담센터',
              phone: '042-350-2181',
              hours: '평일 09:00~18:00',
            ),
            const _CrisisResourceTile(
              name: '정신건강복지센터',
              phone: '1577-0199',
              hours: '24시간',
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.logout, color: AppColors.error),
              title: const Text(
                '로그아웃',
                style: TextStyle(color: AppColors.error),
              ),
              onTap: () async {
                await ref.read(secureStorageProvider).clearAuth();
                if (context.mounted) context.go('/login');
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _CrisisResourceTile extends StatelessWidget {
  final String name;
  final String phone;
  final String hours;
  const _CrisisResourceTile({
    required this.name,
    required this.phone,
    required this.hours,
  });

  @override
  Widget build(BuildContext context) {
    return ListTile(
      dense: true,
      title: Text(name, style: const TextStyle(fontSize: 14)),
      subtitle: Text(
        '$phone · $hours',
        style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
      ),
      trailing: const Icon(Icons.phone, size: 18, color: AppColors.primary),
      onTap: () {
        // 실제로는 url_launcher로 tel: 링크 호출. 의존성 추가는 후속 단계에서.
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$name: $phone')),
        );
      },
    );
  }
}
