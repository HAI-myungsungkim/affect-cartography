import 'package:flutter/material.dart';

import '../../shared/theme/app_theme.dart';
import 'affect_models.dart';

/// V-A grid 위젯. 사양서 4.3.
///
/// - 정사각형 격자
/// - 가로축: 불쾌–유쾌, 세로축: 차분–활기
/// - 양 끝점에만 라벨, 내부에는 옅은 격자선만
/// - 점 모드(onPointSelected)와 궤도 모드(onTrajectoryComplete) 모두 지원
///
/// 좌표계: 위젯 내부는 (x: 0..size, y: 0..size).
/// 정동 좌표는 (v: -1..1 좌→우, a: -1..1 아래→위) — Y축 반전.
class VAGridWidget extends StatefulWidget {
  final AffectMode mode;
  final void Function(AffectPoint point)? onPointSelected;
  final void Function(List<AffectPoint> trajectory)? onTrajectoryComplete;

  /// 예시 궤적을 표시할 때 사용 (연습 세션). 사용자 입력을 막지 않음.
  final List<AffectPoint>? exampleOverlay;

  /// 외부에서 그려진 결과를 초기화하라는 신호.
  final int resetSignal;

  const VAGridWidget({
    super.key,
    required this.mode,
    this.onPointSelected,
    this.onTrajectoryComplete,
    this.exampleOverlay,
    this.resetSignal = 0,
  });

  @override
  State<VAGridWidget> createState() => _VAGridWidgetState();
}

class _VAGridWidgetState extends State<VAGridWidget> {
  AffectPoint? _singlePoint;
  final List<AffectPoint> _trajectory = [];
  DateTime? _dragStart;
  DateTime? _lastSample;
  bool _holdDetected = false;

  @override
  void didUpdateWidget(covariant VAGridWidget old) {
    super.didUpdateWidget(old);
    if (widget.resetSignal != old.resetSignal) {
      setState(() {
        _singlePoint = null;
        _trajectory.clear();
        _dragStart = null;
        _lastSample = null;
        _holdDetected = false;
      });
    }
    if (widget.mode != old.mode) {
      setState(() {
        _singlePoint = null;
        _trajectory.clear();
      });
    }
  }

  AffectPoint _localToVA(Offset local, double size, [int tMs = 0]) {
    final v = ((local.dx / size) * 2 - 1).clamp(-1.0, 1.0);
    final a = (1 - (local.dy / size) * 2).clamp(-1.0, 1.0);
    return AffectPoint(v, a, tMs);
  }

  void _handleTap(Offset local, double size) {
    if (widget.mode != AffectMode.point) return;
    final p = _localToVA(local, size);
    setState(() => _singlePoint = p);
    widget.onPointSelected?.call(p);
  }

  void _handlePanStart(Offset local, double size) {
    if (widget.mode != AffectMode.trajectory) return;
    _dragStart = DateTime.now();
    _lastSample = _dragStart;
    _holdDetected = false;
    setState(() {
      _trajectory
        ..clear()
        ..add(_localToVA(local, size, 0));
    });
  }

  void _handlePanUpdate(Offset local, double size) {
    if (widget.mode != AffectMode.trajectory) return;
    if (_dragStart == null) return;
    final now = DateTime.now();
    // 50ms 샘플링 (사양서 4.3.2)
    if (_lastSample != null && now.difference(_lastSample!).inMilliseconds < 50) {
      return;
    }
    final t = now.difference(_dragStart!).inMilliseconds;
    setState(() {
      _trajectory.add(_localToVA(local, size, t));
      _lastSample = now;
    });
  }

  void _handlePanEnd(double size) {
    if (widget.mode != AffectMode.trajectory) return;
    if (_dragStart == null || _trajectory.isEmpty) return;

    final start = _trajectory.first;
    final last = _trajectory.last;
    final distance = ((last.valence - start.valence).abs() +
        (last.arousal - start.arousal).abs());
    final duration = DateTime.now().difference(_dragStart!);

    // 길게 눌러 점 처리: 0.5초 이상 + 거의 안 움직임
    if (duration.inMilliseconds >= 500 && distance < 0.05 && _trajectory.length > 1) {
      _holdDetected = true;
      setState(() {
        _trajectory
          ..clear()
          ..add(AffectPoint(start.valence, start.arousal, 0));
      });
    }

    widget.onTrajectoryComplete?.call(List.unmodifiable(_trajectory));
    _dragStart = null;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final size = c.maxWidth < c.maxHeight ? c.maxWidth : c.maxHeight;
      return SizedBox(
        width: size,
        height: size,
        child: GestureDetector(
          onTapUp: (d) => _handleTap(d.localPosition, size),
          onPanStart: (d) => _handlePanStart(d.localPosition, size),
          onPanUpdate: (d) => _handlePanUpdate(d.localPosition, size),
          onPanEnd: (_) => _handlePanEnd(size),
          child: CustomPaint(
            painter: _VAGridPainter(
              singlePoint: _singlePoint,
              trajectory: _trajectory,
              exampleOverlay: widget.exampleOverlay,
              holdDetected: _holdDetected,
              isDark: Theme.of(context).brightness == Brightness.dark,
            ),
          ),
        ),
      );
    });
  }
}

class _VAGridPainter extends CustomPainter {
  final AffectPoint? singlePoint;
  final List<AffectPoint> trajectory;
  final List<AffectPoint>? exampleOverlay;
  final bool holdDetected;
  final bool isDark;

  _VAGridPainter({
    required this.singlePoint,
    required this.trajectory,
    required this.exampleOverlay,
    required this.holdDetected,
    required this.isDark,
  });

  Offset _vaToOffset(AffectPoint p, Size s) {
    final x = ((p.valence + 1) / 2) * s.width;
    final y = (1 - (p.arousal + 1) / 2) * s.height;
    return Offset(x, y);
  }

  @override
  void paint(Canvas canvas, Size s) {
    final bg = Paint()
      ..color = isDark ? AppColors.darkSurface : Colors.white
      ..style = PaintingStyle.fill;
    final rrect = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, 0, s.width, s.height),
      const Radius.circular(16),
    );
    canvas.drawRRect(rrect, bg);

    // 격자 — 내부 점선 (사양서: 옅은 격자선만)
    final gridPaint = Paint()
      ..color = (isDark ? Colors.white24 : Colors.black12)
      ..strokeWidth = 1;
    for (var i = 1; i < 4; i++) {
      final dx = s.width * i / 4;
      final dy = s.height * i / 4;
      canvas.drawLine(Offset(dx, 0), Offset(dx, s.height), gridPaint);
      canvas.drawLine(Offset(0, dy), Offset(s.width, dy), gridPaint);
    }

    // 중심선 (조금 더 진하게)
    final centerPaint = Paint()
      ..color = (isDark ? Colors.white38 : Colors.black26)
      ..strokeWidth = 1.2;
    canvas.drawLine(
      Offset(s.width / 2, 0),
      Offset(s.width / 2, s.height),
      centerPaint,
    );
    canvas.drawLine(
      Offset(0, s.height / 2),
      Offset(s.width, s.height / 2),
      centerPaint,
    );

    // 양 끝점 라벨
    final textColor = isDark ? AppColors.textOnDark : AppColors.textSecondary;
    _drawLabel(canvas, '활기', Offset(s.width / 2, 8), textColor, anchorTop: true);
    _drawLabel(canvas, '차분', Offset(s.width / 2, s.height - 20), textColor);
    _drawLabel(canvas, '불쾌', Offset(20, s.height / 2 - 8), textColor);
    _drawLabel(canvas, '유쾌', Offset(s.width - 20, s.height / 2 - 8), textColor);

    // 예시 궤적 (연습 세션) — 옅은 색으로 먼저
    if (exampleOverlay != null && exampleOverlay!.isNotEmpty) {
      _paintTrajectory(canvas, s, exampleOverlay!,
          baseColor: AppColors.accentSage, baseWidth: 3, dashed: true);
    }

    // 실제 입력 궤적
    if (trajectory.isNotEmpty) {
      _paintTrajectory(canvas, s, trajectory,
          baseColor: AppColors.primary, baseWidth: 4);
    }

    // 점 모드 / 길게 눌러 점 처리된 경우의 단일 점
    final showSingle = singlePoint ?? (
        holdDetected && trajectory.isNotEmpty ? trajectory.first : null);
    if (showSingle != null) {
      final pos = _vaToOffset(showSingle, s);
      final paint = Paint()..color = AppColors.primary;
      canvas.drawCircle(pos, 12, paint..style = PaintingStyle.fill);
      canvas.drawCircle(
        pos, 18,
        Paint()
          ..color = AppColors.primary.withOpacity(0.18)
          ..style = PaintingStyle.fill,
      );
    }
  }

  /// 시작점은 옅고 끝점은 진한 그라데이션 (사양서 4.3.2). 4.3.5 대시보드도 동일.
  void _paintTrajectory(
    Canvas canvas,
    Size s,
    List<AffectPoint> pts, {
    required Color baseColor,
    required double baseWidth,
    bool dashed = false,
  }) {
    if (pts.length < 2) {
      // 단일 점도 표시
      if (pts.length == 1) {
        canvas.drawCircle(
          _vaToOffset(pts.first, s),
          10,
          Paint()..color = baseColor,
        );
      }
      return;
    }
    for (var i = 0; i < pts.length - 1; i++) {
      final p1 = _vaToOffset(pts[i], s);
      final p2 = _vaToOffset(pts[i + 1], s);
      final t = (i + 1) / pts.length; // 0..1, 끝쪽일수록 진해짐
      final opacity = 0.25 + 0.75 * t;
      final paint = Paint()
        ..color = baseColor.withOpacity(opacity)
        ..strokeWidth = baseWidth
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;
      if (dashed) {
        _drawDashedLine(canvas, p1, p2, paint);
      } else {
        canvas.drawLine(p1, p2, paint);
      }
    }
    // 끝점 강조
    canvas.drawCircle(
      _vaToOffset(pts.last, s),
      8,
      Paint()..color = baseColor,
    );
    // 시작점은 옅은 링
    canvas.drawCircle(
      _vaToOffset(pts.first, s),
      6,
      Paint()
        ..color = baseColor.withOpacity(0.4)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2,
    );
  }

  void _drawDashedLine(Canvas canvas, Offset a, Offset b, Paint paint) {
    const dash = 6.0;
    const gap = 4.0;
    final total = (b - a).distance;
    final dir = (b - a) / total;
    var dist = 0.0;
    while (dist < total) {
      final start = a + dir * dist;
      final end = a + dir * (dist + dash).clamp(0, total);
      canvas.drawLine(start, end, paint);
      dist += dash + gap;
    }
  }

  void _drawLabel(Canvas canvas, String text, Offset center, Color color,
      {bool anchorTop = false}) {
    final tp = TextPainter(
      text: TextSpan(
        text: text,
        style: TextStyle(
          color: color,
          fontSize: 12,
          fontWeight: FontWeight.w500,
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(
      canvas,
      Offset(
        center.dx - tp.width / 2,
        anchorTop ? center.dy : center.dy - tp.height / 2,
      ),
    );
  }

  @override
  bool shouldRepaint(covariant _VAGridPainter old) {
    return old.singlePoint != singlePoint ||
        old.trajectory != trajectory ||
        old.exampleOverlay != exampleOverlay ||
        old.holdDetected != holdDetected;
  }
}
