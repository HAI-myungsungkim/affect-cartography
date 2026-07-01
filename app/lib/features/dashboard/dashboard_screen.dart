import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import 'dashboard_models.dart';
import 'dashboard_repository.dart';
import 'va_history_widget.dart';

/// 사양서 4.9 대시보드 화면.
///
/// 상단 요약 + 2개 탭 (정동 궤적 / 감정 기록) + 겹쳐보기 토글.
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabCtl;
  DashboardData? _data;
  bool _loading = true;
  String? _error;
  bool _showOverlay = false;

  @override
  void initState() {
    super.initState();
    _tabCtl = TabController(length: 2, vsync: this);
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await ref.read(dashboardRepositoryProvider).fetchMyDashboard();
      if (!mounted) return;
      setState(() {
        _data = d;
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

  @override
  void dispose() {
    _tabCtl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
        title: const Text('나의 기록'),
        actions: [
          if (_tabCtl.index == 0 && _data != null)
            IconButton(
              icon: Icon(_showOverlay
                  ? Icons.label_off
                  : Icons.label_outline),
              tooltip: '정동 + 감정 겹쳐보기',
              onPressed: () => setState(() => _showOverlay = !_showOverlay),
            ),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _load,
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? _ErrorView(message: _error!, onRetry: _load)
              : _buildBody(),
    );
  }

  Widget _buildBody() {
    final d = _data!;
    return Column(
      children: [
        _SummaryCard(summary: d.summary),
        TabBar(
          controller: _tabCtl,
          onTap: (_) => setState(() {}),
          labelColor: AppColors.primary,
          unselectedLabelColor: AppColors.textSecondary,
          indicatorColor: AppColors.primary,
          tabs: const [
            Tab(text: '정동 궤적'),
            Tab(text: '감정 기록'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabCtl,
            children: [
              _AffectTab(
                points: d.affectPoints,
                showOverlay: _showOverlay,
              ),
              _EmotionTab(items: d.emotionTimeline),
            ],
          ),
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  final DashboardSummary summary;
  const _SummaryCard({required this.summary});

  @override
  Widget build(BuildContext context) {
    final pct = (summary.responseRate * 100).round();
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppColors.accentBeige.withOpacity(0.4),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('누적 응답률',
                    style: TextStyle(
                        fontSize: 12, color: AppColors.textSecondary)),
                const SizedBox(height: 4),
                Text('$pct%',
                    style: const TextStyle(
                        fontSize: 32,
                        fontWeight: FontWeight.w700,
                        color: AppColors.primary)),
              ],
            ),
          ),
          Container(
              width: 1, height: 40, color: const Color(0xFFE5E7EB)),
          const SizedBox(width: 16),
          _SummaryStat(label: '총 기록', value: '${summary.totalRecords}'),
          const SizedBox(width: 16),
          _SummaryStat(label: '활동일', value: '${summary.daysActive}'),
        ],
      ),
    );
  }
}

class _SummaryStat extends StatelessWidget {
  final String label;
  final String value;
  const _SummaryStat({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(label,
            style: TextStyle(
                fontSize: 11, color: AppColors.textSecondary)),
        const SizedBox(height: 4),
        Text(value,
            style: const TextStyle(
                fontSize: 20, fontWeight: FontWeight.w600)),
      ],
    );
  }
}

class _AffectTab extends StatelessWidget {
  final List<AffectPointHistory> points;
  final bool showOverlay;
  const _AffectTab({required this.points, required this.showOverlay});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Row(
              children: [
                Icon(showOverlay ? Icons.label : Icons.label_outline,
                    size: 14, color: AppColors.textSecondary),
                const SizedBox(width: 6),
                Text(
                  showOverlay
                      ? '감정 단어 라벨 표시 중 — 우상단 버튼으로 끄기'
                      : '우상단 라벨 아이콘으로 감정 단어 겹쳐보기',
                  style: TextStyle(
                      fontSize: 11.5, color: AppColors.textSecondary),
                ),
              ],
            ),
          ),
          AspectRatio(
            aspectRatio: 1,
            child: VAHistoryWidget(
              points: points,
              showEmotionLabels: showOverlay,
            ),
          ),
          const SizedBox(height: 16),
          if (points.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surface,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFE5E7EB)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _Legend(
                    color: AppColors.primary.withOpacity(0.25),
                    label: '오래된 기록',
                  ),
                  _Legend(
                    color: AppColors.primary,
                    label: '최근 기록',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
          ],
        ],
      ),
    );
  }
}

class _Legend extends StatelessWidget {
  final Color color;
  final String label;
  const _Legend({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Text(label,
            style: TextStyle(fontSize: 12, color: AppColors.textSecondary)),
      ],
    );
  }
}

class _EmotionTab extends StatelessWidget {
  final List<EmotionTimelineItem> items;
  const _EmotionTab({required this.items});

  String _formatTime(DateTime t) {
    final local = t.toLocal();
    final mm = local.month.toString().padLeft(2, '0');
    final dd = local.day.toString().padLeft(2, '0');
    final hh = local.hour.toString().padLeft(2, '0');
    final mi = local.minute.toString().padLeft(2, '0');
    return '$mm/$dd $hh:$mi';
  }

  Color _quadrantColor(String q) {
    switch (q) {
      case 'q1':
        return const Color(0xFFE8A87C);  // 따뜻한 황톤
      case 'q2':
        return const Color(0xFFC38D9E);  // 분홍-자주
      case 'q3':
        return const Color(0xFF6C8BAB);  // 차분한 청회색
      case 'q4':
        return AppColors.accentSage;
      default:
        return AppColors.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            '아직 선택된 감정이 없어요.\n기록을 진행하면 여기 차곡차곡 쌓입니다.',
            textAlign: TextAlign.center,
            style: TextStyle(
                color: AppColors.textSecondary, fontSize: 13, height: 1.5),
          ),
        ),
      );
    }
    // 최신순으로 표시
    final reversed = items.reversed.toList();
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: reversed.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (context, i) {
        final item = reversed[i];
        return _EmotionTile(
          item: item,
          color: _quadrantColor(item.quadrant),
          timeStr: _formatTime(item.timestamp),
        );
      },
    );
  }
}

class _EmotionTile extends StatelessWidget {
  final EmotionTimelineItem item;
  final Color color;
  final String timeStr;
  const _EmotionTile({
    required this.item,
    required this.color,
    required this.timeStr,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Row(
        children: [
          // 사분면 색 인디케이터
          Container(
            width: 4, height: 44,
            decoration: BoxDecoration(
              color: color, borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(item.word,
                    style: const TextStyle(
                        fontSize: 16, fontWeight: FontWeight.w600)),
                const SizedBox(height: 4),
                Text(timeStr,
                    style: TextStyle(
                        fontSize: 11.5, color: AppColors.textSecondary)),
              ],
            ),
          ),
          _IntensityBar(intensity: item.intensity),
        ],
      ),
    );
  }
}

class _IntensityBar extends StatelessWidget {
  final int intensity;
  const _IntensityBar({required this.intensity});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(5, (i) {
        final filled = i < intensity;
        return Container(
          margin: const EdgeInsets.symmetric(horizontal: 1.5),
          width: 6,
          height: 18,
          decoration: BoxDecoration(
            color: filled
                ? AppColors.primary
                : AppColors.primary.withOpacity(0.18),
            borderRadius: BorderRadius.circular(2),
          ),
        );
      }),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String message;
  final VoidCallback onRetry;
  const _ErrorView({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.error_outline,
                color: AppColors.error, size: 36),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(onPressed: onRetry, child: const Text('다시 시도')),
          ],
        ),
      ),
    );
  }
}
