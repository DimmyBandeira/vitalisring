import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/theme/vr_colors.dart';

/// Fundo do mockup: preto quente, brilho atrás do botão e dois fios dourados.
class BackdropPainter extends CustomPainter {
  const BackdropPainter({required this.glowCenter, this.glowStrength = 1});

  /// Centro do brilho em fração da tela (0..1).
  final Offset glowCenter;
  final double glowStrength;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;

    canvas.drawRect(
      rect,
      Paint()
        ..shader = const LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Color(0xFF15110D), VrColors.background, Color(0xFF0A0908)],
          stops: [0, .55, 1],
        ).createShader(rect),
    );

    final c = Offset(size.width * glowCenter.dx, size.height * glowCenter.dy);
    final r = size.width * .75;
    canvas.drawCircle(
      c,
      r,
      Paint()
        ..shader = RadialGradient(
          colors: [
            VrColors.champagne.withValues(alpha: .20 * glowStrength),
            const Color(0xFF7A1A12).withValues(alpha: .10 * glowStrength),
            Colors.transparent,
          ],
          stops: const [0, .45, 1],
        ).createShader(Rect.fromCircle(center: c, radius: r)),
    );

    // Fios dourados — topo-esquerdo e base-direita, como no mockup.
    _arc(
      canvas,
      Rect.fromCircle(center: Offset(size.width * 1.05, size.height * .02), radius: size.width * .95),
      math.pi * .62,
      math.pi * .36,
      size,
    );
    _arc(
      canvas,
      Rect.fromCircle(center: Offset(-size.width * .05, size.height * 1.0), radius: size.width * 1.0),
      math.pi * 1.58, // ângulos positivos: SweepGradient exige 0 ≤ start < end
      math.pi * .34,
      size,
    );
  }

  void _arc(Canvas canvas, Rect oval, double start, double sweep, Size size) {
    final shader = SweepGradient(
      center: Alignment.center,
      startAngle: start,
      endAngle: start + sweep,
      colors: [
        Colors.transparent,
        VrColors.champagne.withValues(alpha: .55),
        Colors.transparent,
      ],
      stops: const [0, .55, 1],
    ).createShader(oval);

    canvas.drawArc(
      oval,
      start,
      sweep,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.4
        ..strokeCap = StrokeCap.round
        ..shader = shader,
    );
  }

  @override
  bool shouldRepaint(BackdropPainter old) =>
      old.glowCenter != glowCenter || old.glowStrength != glowStrength;
}

/// Símbolo da marca (anel + linha de ECG), traduzido de `simbolo-champagne.svg`.
class BrandSymbolPainter extends CustomPainter {
  const BrandSymbolPainter({this.color = VrColors.gold});
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    // viewBox 168x188 com translate(-18,-26) no SVG original.
    final s = math.min(size.width / 168, size.height / 188);
    canvas
      ..save()
      ..translate((size.width - 168 * s) / 2, (size.height - 188 * s) / 2)
      ..scale(s)
      ..translate(-18, -26);

    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    canvas
      ..save()
      ..translate(92, 120)
      ..rotate(4 * math.pi / 180)
      ..translate(-92, -120);
    canvas.drawOval(
      Rect.fromCenter(center: const Offset(92, 120), width: 116, height: 168),
      stroke..strokeWidth = 5.6,
    );
    final crescent = Path()
      ..moveTo(107.70, 37.34)
      ..arcToPoint(const Offset(107.70, 202.66),
          radius: const Radius.elliptical(58, 84), largeArc: true, clockwise: true)
      ..arcToPoint(const Offset(107.70, 37.34),
          radius: const Radius.elliptical(58, 84), largeArc: false, clockwise: false)
      ..close();
    canvas.drawPath(crescent, Paint()..color = color);
    canvas.restore();

    const pts = [
      Offset(47, 124), Offset(68, 124), Offset(74.5, 112.5), Offset(81.5, 135),
      Offset(91.5, 86), Offset(102.5, 157), Offset(111.5, 117.5), Offset(117.5, 128),
      Offset(123.5, 124), Offset(139, 124),
    ];
    final ecg = Path()..moveTo(pts.first.dx, pts.first.dy);
    for (final p in pts.skip(1)) {
      ecg.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(ecg, stroke..strokeWidth = 4.2);
    canvas.restore();
  }

  @override
  bool shouldRepaint(BrandSymbolPainter old) => old.color != color;
}

/// Bateria vertical do mockup, com nível e raio quando carregando.
class BatteryIconPainter extends CustomPainter {
  const BatteryIconPainter({required this.level, required this.color, this.charging = false});

  /// 0..1 — null desenha só o contorno.
  final double? level;
  final Color color;
  final bool charging;

  @override
  void paint(Canvas canvas, Size size) {
    final w = size.width, h = size.height;
    final capH = h * .09;
    final body = RRect.fromRectAndRadius(
      Rect.fromLTWH(1.5, capH + 1.5, w - 3, h - capH - 3),
      Radius.circular(w * .2),
    );
    final cap = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * .3, 0, w * .4, capH + 2),
      Radius.circular(w * .08),
    );

    final outline = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 3;
    canvas
      ..drawRRect(body, outline)
      ..drawRRect(cap, Paint()..color = color);

    final lv = level;
    if (lv != null && lv > 0) {
      final inner = body.deflate(5);
      final fillH = inner.height * lv.clamp(0.0, 1.0);
      canvas.save();
      canvas.clipRRect(inner);
      canvas.drawRect(
        Rect.fromLTRB(inner.left, inner.bottom - fillH, inner.right, inner.bottom),
        Paint()..color = color.withValues(alpha: .85),
      );
      canvas.restore();
    }

    if (charging) {
      final cx = w / 2, cy = capH + (h - capH) / 2;
      final bolt = Path()
        ..moveTo(cx + w * .08, cy - h * .22)
        ..lineTo(cx - w * .2, cy + h * .03)
        ..lineTo(cx, cy + h * .03)
        ..lineTo(cx - w * .08, cy + h * .22)
        ..lineTo(cx + w * .2, cy - h * .03)
        ..lineTo(cx, cy - h * .03)
        ..close();
      canvas.drawPath(bolt, Paint()..color = VrColors.surface);
      canvas.drawPath(
        bolt,
        Paint()
          ..color = VrColors.ink
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5
          ..strokeJoin = StrokeJoin.round,
      );
    }
  }

  @override
  bool shouldRepaint(BatteryIconPainter old) =>
      old.level != level || old.color != color || old.charging != charging;
}
