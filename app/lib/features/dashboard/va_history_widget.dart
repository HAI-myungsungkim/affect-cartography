import 'package:flutter/material.dart';

import '../../shared/theme/app_theme.dart';
import 'dashboard_models.dart';

/// 사양서 4.9 — 정동 궤적 탭의 핵심 시각화.
///
/// V-A grid 위에:
///   - 점 모드: 동그란 점
///   - 궤도 모드: 짧은 곡선 (시작점 옅음 → 끝점 진함)
///   - 오래된 기록일수록 전체적으로 옅어짐 (시간 fade)
///   - 겹쳐보기 ON: 각 점/궤도 옆에 감정 단어 라벨 표시
class VAHistoryWidget extends StatelessWidget {
  final List<AffectPointHistory> points;
  final bool showEmotionLabels;

  const VAHistoryWidget({
    super.key,
    required this.points,
    this.showEmotionLabels = false,
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final size = c.maxWidth < c.maxHeight ? c.maxWidth : c.maxHeight;
      return SizedBox(
        width: size,
        height: size,
        child: CustomPaint(
          painter: _VAHistoryPainter(
            points: points,
            showEmotionLabels: showEmotionLabels,
            isDark: Theme.of(context).brightness == Brightness.dark,
          ),
        ),
      );
    });
  }
}

class _VAHistoryPainter extends CustomPainter {
  final List<AffectPointHistory> points;
  final bool showEmotionLabels;
  final bool isDark;

  _VAHistoryPainter({
    required this.points,
    required this.showEmotionLabels,
    required this.isDark,
  });

  Offset _vaToOffset(double v, double a, Size s) {
    final x = ((v + 1) / 2) * s.width;
    final y = (1 - (a + 1) / 2) * s.height;
    return Offset(x, y);
  }

  @override
  void paint(Canvas canvas, Size s) {
    // 배경 + 격자
    final bg = Paint()
      ..color = isDark ? AppColors.darkSurface : Colors.white
      ..style = PaintingStyle.fill;
    final rrect = RRect.fromRectAndRadius(
      Rect.fromLTWH(0, 0, s.width, s.height),
      const Radius.circular(16),
    );
    canvas.drawRRect(rrect, bg);

    final gridPaint = Paint()
      ..color = (isDark ? Colors.white24 : Colors.black12)
      ..strokeWidth = 1;
    for (var i = 1; i < 4; i++) {
      final dx = s.width * i / 4;
      final dy = s.height * i / 4;
      canvas.drawLine(Offset(dx, 0), Offset(dx, s.height), gridPaint);
      canvas.drawLine(Offset(0, dy), Offset(s.width, dy), gridPaint);
    }
    final centerPaint = Paint()
      ..color = (isDark ? Colors.white38 : Colors.black26)
      ..strokeWidth = 1.2;
    canvas.drawLine(Offset(s.width / 2, 0),
        Offset(s.width / 2, s.height), centerPaint);
    canvas.drawLine(Offset(0, s.height / 2),
        Offset(s.width, s.height / 2), centerPaint);

    // 끝점 라벨
    final textColor = isDark ? AppColors.textOnDark : AppColors.textSecondary;
    _label(canvas, '활기', Offset(s.width / 2, 8), textColor, anchorTop: true);
    _label(canvas, '차분', Offset(s.width / 2, s.height - 20), textColor);
    _label(canvas, '불쾌', Offset(20, s.height / 2 - 8), textColor);
    _label(canvas, '유쾌', Offset(s.width - 20, s.height / 2 - 8), textColor);

    if (points.isEmpty) {
      _emptyMessage(canvas, s);
      return;
    }

    // 시간 fade: 가장 오래된 = 0.25, 가장 최근 = 1.0
    final n = points.length;
    for (var i = 0; i < n; i++) {
      final p = points[i];
      final ageFade = n == 1 ? 1.0 : (0.25 + 0.75 * (i / (n - 1)));

      if (p.mode == 'trajectory' && p.trajectory != null) {
        _drawTrajectory(canvas, s, p, ageFade);
      } else {
        _drawPoint(canvas, s, p, ageFade);
      }

      if (showEmotionLabels && p.emotionWord != null) {
        _drawEmotionLabel(canvas, s, p, ageFade);
      }
    }

    // 점/궤도 사이 연한 연결선 (시간 순)
    if (n >= 2) {
      final connPaint = Paint()
        ..color = AppColors.primary.withOpacity(0.15)
        ..strokeWidth = 1
        ..style = PaintingStyle.stroke;
      Offset? prev;
      for (final p in points) {
        final cur = _vaToOffset(p.valence, p.arousal, s);
        if (prev != null) {
          canvas.drawLine(prev, cur, connPaint);
        }
        prev = cur;
      }
    }
  }

  void _drawPoint(Canvas canvas, Size s, AffectPointHistory p, double fade) {
    final pos = _vaToOffset(p.valence, p.arousal, s);
    final paint = Paint()
      ..color = AppColors.primary.withOpacity(fade)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(pos, 7, paint);
    canvas.drawCircle(
      pos, 12,
      Paint()
        ..color = AppColors.primary.withOpacity(fade * 0.15)
        ..style = PaintingStyle.fill,
    );
  }

  void _drawTrajectory(
      Canvas canvas, Size s, AffectPointHistory p, double ageFade) {
    final pts = p.trajectory!;
    if (pts.length < 2) {
      _drawPoint(canvas, s, p, ageFade);
      return;
    }
    for (var i = 0; i < pts.length - 1; i++) {
      final p1 = _vaToOffset(pts[i].valence, pts[i].arousal, s);
      final p2 = _vaToOffset(pts[i + 1].valence, pts[i + 1].arousal, s);
      // 궤도 내부 그라데이션: 시작 옅음 → 끝 진함
      final innerT = (i + 1) / pts.length;
      final opacity = ageFade * (0.3 + 0.7 * innerT);
      final paint = Paint()
        ..color = AppColors.primary.withOpacity(opacity)
        ..strokeWidth = 3
        ..strokeCap = StrokeCap.round
        ..style = PaintingStyle.stroke;
      canvas.drawLine(p1, p2, paint);
    }
    // 끝점 강조
    canvas.drawCircle(
      _vaToOffset(p.valence, p.arousal, s),
      6,
      Paint()..color = AppColors.primary.withOpacity(ageFade),
    );
  }

  void _drawEmotionLabel(
      Canvas canvas, Size s, AffectPointHistory p, double fade) {
    final pos = _vaToOffset(p.valence, p.arousal, s);
    final tp = TextPainter(
      text: TextSpan(
        text: p.emotionWord!,
        style: TextStyle(
          color: AppColors.primary.withOpacity(fade),
          fontSize: 11,
          fontWeight: FontWeight.w600,
          backgroundColor: (isDark
                  ? AppColors.darkSurface
                  : Colors.white)
              .withOpacity(0.85),
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    // 점에서 약간 오른쪽 위로 띄움. 화면 밖으로 나가지 않도록 보정.
    var dx = pos.dx + 10;
    var dy = pos.dy - 14;
    if (dx + tp.width > s.width - 4) dx = pos.dx - tp.width - 10;
    if (dy < 4) dy = pos.dy + 10;
    tp.paint(canvas, Offset(dx, dy));
  }

  void _label(Canvas canvas, String text, Offset center, Color color,
      {bool anchorTop = false}) {
    final tp = TextPainter(
      text: TextSpan(
          text: text,
          style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.w500)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas,
        Offset(center.dx - tp.width / 2,
            anchorTop ? center.dy : center.dy - tp.height / 2));
  }

  void _emptyMessage(Canvas canvas, Size s) {
    final tp = TextPainter(
      text: TextSpan(
        text: '아직 기록이 없어요',
        style: TextStyle(
            color: AppColors.textSecondary.withOpacity(0.7),
            fontSize: 13),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(canvas,
        Offset((s.width - tp.width) / 2, (s.height - tp.height) / 2));
  }

  @override
  bool shouldRepaint(covariant _VAHistoryPainter old) =>
      old.points != points || old.showEmotionLabels != showEmotionLabels;
}
