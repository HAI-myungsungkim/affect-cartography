import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import 'local_notification_service.dart';
import 'notification_models.dart';
import 'notification_repository.dart';

/// 사양서 8항 — 알림 시간대 설정 화면.
/// 시간대 3구간 구조는 고정. 각 구간의 시각만 조정 가능.
class NotificationSettingsScreen extends ConsumerStatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  ConsumerState<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends ConsumerState<NotificationSettingsScreen> {
  NotificationSettings? _settings;
  bool _loading = true;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final s = await ref.read(notificationRepositoryProvider).getSettings();
      if (!mounted) return;
      setState(() {
        _settings = s;
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

  Future<TimeOfDay?> _pickTime(TimeOfDay initial) {
    return showTimePicker(
      context: context,
      initialTime: initial,
      builder: (context, child) {
        return MediaQuery(
          data: MediaQuery.of(context).copyWith(alwaysUse24HourFormat: true),
          child: child!,
        );
      },
    );
  }

  Future<void> _editWindow(String windowName) async {
    if (_settings == null) return;
    final current = switch (windowName) {
      'morning' => _settings!.morning,
      'afternoon' => _settings!.afternoon,
      _ => _settings!.evening,
    };

    final startTOD = await _pickTime(_parseTOD(current.start));
    if (startTOD == null) return;
    final endTOD = await _pickTime(_parseTOD(current.end));
    if (endTOD == null) return;

    final startStr = _formatTOD(startTOD);
    final endStr = _formatTOD(endTOD);

    if (TimeWindow(start: startStr, end: endStr).endMinutes <=
        TimeWindow(start: startStr, end: endStr).startMinutes) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('끝 시간은 시작 시간보다 뒤여야 합니다.')),
      );
      return;
    }

    setState(() => _saving = true);
    try {
      final updated = await ref.read(notificationRepositoryProvider).updateSettings(
            morning: windowName == 'morning'
                ? TimeWindow(start: startStr, end: endStr)
                : null,
            afternoon: windowName == 'afternoon'
                ? TimeWindow(start: startStr, end: endStr)
                : null,
            evening: windowName == 'evening'
                ? TimeWindow(start: startStr, end: endStr)
                : null,
          );
      if (!mounted) return;
      setState(() {
        _settings = updated;
        _saving = false;
      });
      // 시간대 변경 시 오늘의 스케줄 재등록
      await _rescheduleToday();
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('저장 실패: $e')),
      );
    }
  }

  Future<void> _rescheduleToday() async {
    try {
      final schedule =
          await ref.read(notificationRepositoryProvider).getTodaySchedule();
      await LocalNotificationService.scheduleToday(schedule);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('알림 일정이 업데이트되었어요 (${schedule.prompts.length}건)')),
      );
    } catch (e) {
      // 알림 등록 실패는 silent (개발 중에는 발생할 수 있음)
      debugPrint('알림 재등록 실패: $e');
    }
  }

  TimeOfDay _parseTOD(String hhmm) {
    final p = hhmm.split(':');
    return TimeOfDay(hour: int.parse(p[0]), minute: int.parse(p[1]));
  }

  String _formatTOD(TimeOfDay t) =>
      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
        title: const Text('알림 시간대'),
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : _buildBody(),
    );
  }

  Widget _buildBody() {
    final s = _settings!;
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      children: [
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: AppColors.accentBeige.withOpacity(0.4),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              const Icon(Icons.info_outline, size: 18,
                  color: AppColors.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '하루 3번, 각 시간대 내 무작위 시점에 알림이 옵니다.\n'
                  '구간 시각만 조정할 수 있어요.',
                  style: TextStyle(
                      fontSize: 12.5,
                      color: AppColors.textPrimary,
                      height: 1.5),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),
        _WindowTile(
          icon: Icons.wb_sunny_outlined,
          label: '아침',
          window: s.morning,
          onEdit: _saving ? null : () => _editWindow('morning'),
        ),
        const SizedBox(height: 8),
        _WindowTile(
          icon: Icons.wb_cloudy_outlined,
          label: '오후',
          window: s.afternoon,
          onEdit: _saving ? null : () => _editWindow('afternoon'),
        ),
        const SizedBox(height: 8),
        _WindowTile(
          icon: Icons.nightlight_outlined,
          label: '저녁',
          window: s.evening,
          onEdit: _saving ? null : () => _editWindow('evening'),
        ),
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: _saving ? null : _rescheduleToday,
          icon: const Icon(Icons.refresh),
          label: const Text('오늘 알림 다시 등록'),
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
            ),
          ),
        ),
      ],
    );
  }
}

class _WindowTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final TimeWindow window;
  final VoidCallback? onEdit;

  const _WindowTile({
    required this.icon,
    required this.label,
    required this.window,
    required this.onEdit,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onEdit,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppColors.primary, size: 22),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label,
                      style: const TextStyle(
                          fontSize: 14, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 4),
                  Text(
                    '${window.start} – ${window.end}',
                    style: TextStyle(
                        fontSize: 16,
                        color: AppColors.textSecondary,
                        fontFeatures: const [FontFeature.tabularFigures()]),
                  ),
                ],
              ),
            ),
            const Icon(Icons.edit_outlined,
                size: 18, color: AppColors.textSecondary),
          ],
        ),
      ),
    );
  }
}
