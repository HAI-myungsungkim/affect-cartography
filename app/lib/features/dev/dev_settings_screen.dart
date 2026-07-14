import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/providers.dart';
import '../../shared/theme/app_theme.dart';

/// 개발/테스트용 실험 조건 설정 화면.
///
/// 로그인한 테스트 계정이 실험 축 5개를 직접 바꿔 각 흐름을 반복 확인한다.
/// 블라인드 없이 동료 공유용. 저장하면 백엔드와 로컬 저장소 양쪽이 갱신된다.
///
/// ⚠️ 배포 전 복귀 지점: 실제 실험에서는 이 화면을 홈 메뉴에서 숨기고,
/// 조건 배정은 관리자 웹에서만 하도록 전환한다.
class DevSettingsScreen extends ConsumerStatefulWidget {
  const DevSettingsScreen({super.key});

  @override
  ConsumerState<DevSettingsScreen> createState() => _DevSettingsScreenState();
}

/// 축 하나의 정의: 저장 키, 화면 제목, (값 → 라벨) 목록.
class _Axis {
  final String key; // 백엔드 필드명
  final String title;
  final String description;
  final List<({String value, String label})> options;
  const _Axis(this.key, this.title, this.description, this.options);
}

const _axes = <_Axis>[
  _Axis('observation_mode', '축1 · 관찰 대상',
      '자기만 기록할지, 타인을 먼저 관찰할지', [
    (value: 'self_only', label: '자기만 기록 (대조군)'),
    (value: 'recall_other', label: '주변 인물 회상 관찰'),
    (value: 'scenario_other', label: '앱 내 시나리오 관찰'),
  ]),
  _Axis('record_mode', '축2 · 정동 기록 형태',
      '순간의 점 vs 변화의 궤도', [
    (value: 'point', label: '점 (순간)'),
    (value: 'trajectory', label: '궤도 (변화)'),
  ]),
  _Axis('emotion_timing', '축3 · 감정 기록 시점',
      '정동 직후 바로 vs 직전 슬롯을 나중에', [
    (value: 'immediate', label: '즉시 (대조군)'),
    (value: 'delayed', label: '시간차 (한 슬롯 밀림)'),
  ]),
  _Axis('agent_mode', '축4 · Agent 개입',
      '바로 감정 기록 vs AI와 대화 후 기록', [
    (value: 'none', label: '없음 (대조군)'),
    (value: 'enabled', label: 'AI 대화 개입'),
  ]),
];

class _DevSettingsScreenState extends ConsumerState<DevSettingsScreen> {
  // 현재 선택값
  final Map<String, String> _selected = {};
  bool _educationEnabled = false;
  bool _loading = true;
  bool _saving = false;
  String? _participantCode;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    // 로컬 저장소에서 현재 조건을 읽어 초기값으로 (서버와 동기화된 상태)
    final storage = ref.read(secureStorageProvider);
    _participantCode = await storage.getParticipantCode();
    _selected['observation_mode'] = await storage.getObservationMode();
    _selected['record_mode'] = await storage.getRecordMode() ?? 'point';
    _selected['emotion_timing'] = await storage.getEmotionTiming();
    _selected['agent_mode'] = await storage.getAgentMode();
    _educationEnabled = await storage.getEducationEnabled();
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _save({bool thenRecord = false}) async {
    setState(() => _saving = true);
    final api = ref.read(apiClientProvider);
    final storage = ref.read(secureStorageProvider);
    try {
      final resp = await api.updateMyConditions({
        ..._selected,
        'education_enabled': _educationEnabled,
      });
      if (resp.statusCode == 200) {
        final d = resp.data as Map<String, dynamic>;
        // 로컬 저장소도 서버 응답 기준으로 갱신
        await storage.saveConditions(
          recordMode: d['record_mode'] as String,
          observationMode: d['observation_mode'] as String,
          emotionTiming: d['emotion_timing'] as String,
          agentMode: d['agent_mode'] as String,
          educationEnabled: d['education_enabled'] as bool,
        );
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('조건 저장 완료')),
        );
        if (thenRecord && mounted) {
          context.go('/record');
        }
      } else {
        final msg = resp.data is Map ? '${resp.data['detail']}' : '저장 실패';
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('저장 실패: $msg')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('오류: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
    }
    return Scaffold(
      appBar: AppBar(title: const Text('개발자 설정 · 실험 조건')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          children: [
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.accentBeige.withOpacity(0.4),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '테스트 계정 ${_participantCode ?? ""} · 각 축을 바꾸고 저장하면 '
                '기록 흐름이 그 조건대로 바뀝니다. (블라인드 없음)',
                style: TextStyle(
                  fontSize: 13,
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
            ),
            const SizedBox(height: 20),
            for (final axis in _axes) ...[
              _AxisSelector(
                axis: axis,
                value: _selected[axis.key]!,
                onChanged: (v) => setState(() => _selected[axis.key] = v),
              ),
              const SizedBox(height: 18),
            ],
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('교육자료 노출',
                  style: TextStyle(fontWeight: FontWeight.w600)),
              subtitle: Text('홈에서 정동·감정 교육 카드 열람',
                  style: TextStyle(
                      fontSize: 12.5, color: AppColors.textSecondary)),
              value: _educationEnabled,
              onChanged: (v) => setState(() => _educationEnabled = v),
            ),
            const SizedBox(height: 28),
            ElevatedButton(
              onPressed: _saving ? null : () => _save(thenRecord: true),
              child: _saving
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(
                          color: Colors.white, strokeWidth: 2.5),
                    )
                  : const Text('저장하고 지금 기록하기'),
            ),
            const SizedBox(height: 12),
            OutlinedButton(
              onPressed: _saving ? null : () => _save(thenRecord: false),
              style: OutlinedButton.styleFrom(
                minimumSize: const Size.fromHeight(56),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              child: const Text('저장만 하기'),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}

class _AxisSelector extends StatelessWidget {
  final _Axis axis;
  final String value;
  final ValueChanged<String> onChanged;
  const _AxisSelector({
    required this.axis,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(axis.title,
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700)),
        const SizedBox(height: 2),
        Text(axis.description,
            style:
                TextStyle(fontSize: 12.5, color: AppColors.textSecondary)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 14),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.black12),
            borderRadius: BorderRadius.circular(12),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: value,
              isExpanded: true,
              items: [
                for (final o in axis.options)
                  DropdownMenuItem(value: o.value, child: Text(o.label)),
              ],
              onChanged: (v) {
                if (v != null) onChanged(v);
              },
            ),
          ),
        ),
      ],
    );
  }
}
