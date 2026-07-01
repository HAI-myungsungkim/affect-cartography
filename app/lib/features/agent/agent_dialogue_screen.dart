import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../shared/theme/app_theme.dart';
import 'agent_models.dart';
import 'agent_repository.dart';

/// 사양서 4.4 에이전트 대화 화면.
class AgentDialogueScreen extends ConsumerStatefulWidget {
  final String recordId;
  /// 감정 선택 화면으로 넘길 때 정동 좌표를 전달하기 위해.
  final double? valence;
  final double? arousal;
  const AgentDialogueScreen({
    super.key,
    required this.recordId,
    this.valence,
    this.arousal,
  });

  @override
  ConsumerState<AgentDialogueScreen> createState() =>
      _AgentDialogueScreenState();
}

class _AgentDialogueScreenState extends ConsumerState<AgentDialogueScreen> {
  final _scrollCtl = ScrollController();
  final _inputCtl = TextEditingController();
  final List<_LocalTurn> _messages = [];
  bool _waiting = false;
  bool _finished = false;
  bool _crisisRaised = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _kickoff());
  }

  Future<void> _kickoff() async {
    await _sendTurn(userMessage: null);
  }

  Future<void> _sendTurn({String? userMessage}) async {
    if (_waiting || _finished) return;

    if (userMessage != null) {
      setState(() {
        _messages.add(_LocalTurn(
          speaker: Speaker.user,
          text: userMessage,
        ));
        _waiting = true;
      });
      _scrollToBottom();
    } else {
      setState(() => _waiting = true);
    }

    try {
      final result = await ref.read(agentRepositoryProvider).postTurn(
            recordId: widget.recordId,
            userMessage: userMessage,
          );
      if (!mounted) return;
      setState(() {
        _messages.add(_LocalTurn(
          speaker: Speaker.agent,
          text: result.agentMessage,
        ));
        _waiting = false;
        _finished = result.isFinal;
        _crisisRaised = result.safetyFlagRaised;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _waiting = false;
        _messages.add(_LocalTurn(
          speaker: Speaker.agent,
          text: '연결에 잠시 문제가 있어요. 다시 시도해주세요.',
          isError: true,
        ));
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtl.hasClients) {
        _scrollCtl.animateTo(
          _scrollCtl.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _submitInput() {
    final text = _inputCtl.text.trim();
    if (text.isEmpty) return;
    _inputCtl.clear();
    _sendTurn(userMessage: text);
  }

  void _proceedToNextStep() {
    if (_crisisRaised) {
      context.go('/home');
      return;
    }
    // 감정 단어 선택 화면으로
    final v = widget.valence ?? 0;
    final a = widget.arousal ?? 0;
    context.go('/emotion/${widget.recordId}?v=$v&a=$a');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('잠시 이야기를 나눠봐요'),
        leading: IconButton(
          icon: const Icon(Icons.close),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: ListView.builder(
                controller: _scrollCtl,
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
                itemCount: _messages.length + (_waiting ? 1 : 0),
                itemBuilder: (context, i) {
                  if (i == _messages.length && _waiting) {
                    return const _TypingBubble();
                  }
                  return _MessageBubble(turn: _messages[i]);
                },
              ),
            ),
            if (_crisisRaised) const _CrisisCard(),
            if (_finished)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                child: ElevatedButton(
                  onPressed: _proceedToNextStep,
                  child: Text(_crisisRaised ? '홈으로 돌아가기' : '다음 단계로'),
                ),
              )
            else
              _InputBar(
                controller: _inputCtl,
                enabled: !_waiting,
                onSubmit: _submitInput,
              ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _scrollCtl.dispose();
    _inputCtl.dispose();
    super.dispose();
  }
}

class _LocalTurn {
  final Speaker speaker;
  final String text;
  final bool isError;
  _LocalTurn({required this.speaker, required this.text, this.isError = false});
}

class _MessageBubble extends StatelessWidget {
  final _LocalTurn turn;
  const _MessageBubble({required this.turn});

  @override
  Widget build(BuildContext context) {
    final isUser = turn.speaker == Speaker.user;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (!isUser) ...[
            CircleAvatar(
              radius: 14,
              backgroundColor: AppColors.accentSage.withOpacity(0.5),
              child: const Icon(Icons.spa,
                  size: 16, color: AppColors.primary),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(
                  horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: turn.isError
                    ? const Color(0xFFFDECEC)
                    : isUser
                        ? AppColors.primary
                        : (Theme.of(context).brightness == Brightness.dark
                            ? AppColors.darkSurface
                            : const Color(0xFFF1F1EE)),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(16),
                  topRight: const Radius.circular(16),
                  bottomLeft: Radius.circular(isUser ? 16 : 4),
                  bottomRight: Radius.circular(isUser ? 4 : 16),
                ),
              ),
              child: Text(
                turn.text,
                style: TextStyle(
                  fontSize: 14.5,
                  height: 1.5,
                  color: isUser
                      ? Colors.white
                      : Theme.of(context).textTheme.bodyMedium?.color,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TypingBubble extends StatelessWidget {
  const _TypingBubble();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: AppColors.accentSage.withOpacity(0.5),
            child: const Icon(Icons.spa, size: 16, color: AppColors.primary),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
            decoration: BoxDecoration(
              color: Theme.of(context).brightness == Brightness.dark
                  ? AppColors.darkSurface
                  : const Color(0xFFF1F1EE),
              borderRadius: BorderRadius.circular(16),
            ),
            child: const SizedBox(
              width: 28,
              height: 14,
              child: _Dots(),
            ),
          ),
        ],
      ),
    );
  }
}

class _Dots extends StatefulWidget {
  const _Dots();

  @override
  State<_Dots> createState() => _DotsState();
}

class _DotsState extends State<_Dots> with SingleTickerProviderStateMixin {
  late final AnimationController _ctl;

  @override
  void initState() {
    super.initState();
    _ctl = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    )..repeat();
  }

  @override
  void dispose() {
    _ctl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _ctl,
      builder: (_, __) {
        return Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: List.generate(3, (i) {
            final phase = (_ctl.value + i * 0.2) % 1.0;
            final opacity = (phase < 0.5 ? phase * 2 : (1 - phase) * 2)
                .clamp(0.3, 1.0);
            return Opacity(
              opacity: opacity,
              child: Container(
                width: 6,
                height: 6,
                decoration: BoxDecoration(
                  color: AppColors.textSecondary,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            );
          }),
        );
      },
    );
  }
}

class _InputBar extends StatelessWidget {
  final TextEditingController controller;
  final bool enabled;
  final VoidCallback onSubmit;

  const _InputBar({
    required this.controller,
    required this.enabled,
    required this.onSubmit,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 12),
      decoration: BoxDecoration(
        color: Theme.of(context).scaffoldBackgroundColor,
        border: Border(top: BorderSide(color: const Color(0xFFE5E7EB))),
      ),
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: controller,
              enabled: enabled,
              minLines: 1,
              maxLines: 4,
              textInputAction: TextInputAction.send,
              onSubmitted: (_) => onSubmit(),
              decoration: const InputDecoration(
                hintText: '편하게 적어주세요',
                contentPadding:
                    EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton(
            onPressed: enabled ? onSubmit : null,
            icon: const Icon(Icons.send_rounded),
            color: AppColors.primary,
            iconSize: 26,
          ),
        ],
      ),
    );
  }
}

/// 위기 표현 감지 시 채팅 하단에 노출되는 자원 카드.
class _CrisisCard extends StatelessWidget {
  const _CrisisCard();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 8),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFFFFF4E6),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE6A23C)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.favorite, color: Color(0xFFE6A23C), size: 20),
            const SizedBox(width: 8),
            Text(
              '도움이 필요하신가요?',
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: Color(0xFF8E5A1F),
              ),
            ),
          ]),
          const SizedBox(height: 10),
          _ResourceLine(name: '자살예방상담전화', phone: '1393', hours: '24시간'),
          _ResourceLine(
              name: 'KAIST 학생상담센터',
              phone: '042-350-2181',
              hours: '평일 09:00–18:00'),
          _ResourceLine(
              name: '정신건강복지센터', phone: '1577-0199', hours: '24시간'),
        ],
      ),
    );
  }
}

class _ResourceLine extends StatelessWidget {
  final String name;
  final String phone;
  final String hours;
  const _ResourceLine({
    required this.name,
    required this.phone,
    required this.hours,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: 4),
      child: Row(
        children: [
          Expanded(
            child: Text(
              name,
              style: const TextStyle(
                  fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
          Text(
            phone,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: AppColors.primary,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            hours,
            style: TextStyle(fontSize: 11, color: AppColors.textSecondary),
          ),
        ],
      ),
    );
  }
}
