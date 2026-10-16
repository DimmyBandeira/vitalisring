import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/config/app_settings.dart';
import '../../../core/theme/vr_colors.dart';

/// Fases do gesto, expostas para a tela mostrar texto de apoio.
enum HoldPhase { idle, holding, released, confirmed }

/// Botão SOS de "segurar para confirmar".
/// - Evita disparo acidental (toque rápido não conta)
/// - Anel de progresso dourado + vibração a cada segundo + vibração forte ao confirmar
/// - Dois estilos: imagens do mockup ou desenho vetorial (nítido em qualquer tela)
class SosHoldButton extends StatefulWidget {
  const SosHoldButton({
    super.key,
    required this.size,
    required this.holdSeconds,
    required this.style,
    required this.onConfirmed,
    this.onPhaseChanged,
    this.onSecondsLeft,
  });

  final double size;
  final int holdSeconds;
  final SosButtonStyle style;
  final VoidCallback onConfirmed;
  final ValueChanged<HoldPhase>? onPhaseChanged;
  final ValueChanged<int>? onSecondsLeft;

  @override
  State<SosHoldButton> createState() => _SosHoldButtonState();
}

class _SosHoldButtonState extends State<SosHoldButton> with TickerProviderStateMixin {
  late final AnimationController _hold;
  late final AnimationController _breath;
  int? _pointer;
  bool _pressing = false;
  int _lastSecondsLeft = 0;

  @override
  void initState() {
    super.initState();
    _hold = AnimationController(vsync: this, duration: Duration(seconds: widget.holdSeconds))
      ..addListener(_onTick)
      ..addStatusListener(_onStatus);
    _breath = AnimationController(vsync: this, duration: const Duration(milliseconds: 2600))
      ..repeat(reverse: true);
  }

  @override
  void didUpdateWidget(SosHoldButton old) {
    super.didUpdateWidget(old);
    if (old.holdSeconds != widget.holdSeconds) {
      _hold.duration = Duration(seconds: widget.holdSeconds);
    }
  }

  void _onTick() {
    if (!_pressing) return;
    final left = (widget.holdSeconds * (1 - _hold.value)).ceil();
    if (left != _lastSecondsLeft && left > 0) {
      _lastSecondsLeft = left;
      HapticFeedback.mediumImpact();
      widget.onSecondsLeft?.call(left);
    }
  }

  void _onStatus(AnimationStatus s) {
    if (s == AnimationStatus.completed && _pressing) {
      HapticFeedback.heavyImpact();
      _pointer = null;
      setState(() => _pressing = false);
      widget.onPhaseChanged?.call(HoldPhase.confirmed);
      widget.onConfirmed();
      _hold.reset();
    }
  }

  void _down(PointerDownEvent e) {
    if (_pointer != null) return;
    _pointer = e.pointer;
    _lastSecondsLeft = widget.holdSeconds + 1;
    HapticFeedback.selectionClick();
    setState(() => _pressing = true);
    widget.onPhaseChanged?.call(HoldPhase.holding);
    _hold.forward(from: 0);
  }

  void _up(int pointer) {
    if (_pointer != pointer) return;
    _pointer = null;
    if (!_pressing) return; // já confirmou
    _hold
      ..stop()
      ..reset();
    setState(() => _pressing = false);
    widget.onPhaseChanged?.call(HoldPhase.released);
  }

  @override
  void dispose() {
    _hold.dispose();
    _breath.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.size;
    final ringPad = s * .055; // espaço entre o botão e o anel de progresso

    return Semantics(
      button: true,
      label: 'Pedir ajuda. Segure por ${widget.holdSeconds} segundos para chamar.',
      onLongPress: widget.onConfirmed, // TalkBack: toque duplo e segurar
      child: Listener(
        behavior: HitTestBehavior.opaque,
        onPointerDown: _down,
        onPointerUp: (e) => _up(e.pointer),
        onPointerCancel: (e) => _up(e.pointer),
        child: SizedBox(
          width: s + ringPad * 2,
          height: s + ringPad * 2,
          child: AnimatedBuilder(
            animation: Listenable.merge([_hold, _breath]),
            builder: (context, _) {
              final breath = Curves.easeInOut.transform(_breath.value);
              return Stack(
                alignment: Alignment.center,
                children: [
                  // Halo: respira em repouso, acende enquanto segura.
                  _Halo(
                    size: s * 1.08,
                    intensity: _pressing ? .55 + .45 * _hold.value : .25 + .2 * breath,
                  ),
                  AnimatedScale(
                    scale: _pressing ? .955 : 1,
                    duration: const Duration(milliseconds: 140),
                    curve: Curves.easeOut,
                    child: SizedBox.square(
                      dimension: s,
                      child: widget.style == SosButtonStyle.image
                          ? _ImageFace(pressed: _pressing)
                          : _VectorFace(pressed: _pressing, holdSeconds: widget.holdSeconds),
                    ),
                  ),
                  if (_pressing || _hold.value > 0)
                    SizedBox.square(
                      dimension: s + ringPad * 2,
                      child: CustomPaint(painter: _ProgressRingPainter(_hold.value)),
                    ),
                ],
              );
            },
          ),
        ),
      ),
    );
  }
}

class _Halo extends StatelessWidget {
  const _Halo({required this.size, required this.intensity});
  final double size;
  final double intensity;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: VrColors.champagne.withValues(alpha: .35 * intensity),
              blurRadius: size * .22,
              spreadRadius: size * .01,
            ),
            BoxShadow(
              color: VrColors.critical.withValues(alpha: .35 * intensity),
              blurRadius: size * .12,
            ),
          ],
        ),
      ),
    );
  }
}

class _ImageFace extends StatelessWidget {
  const _ImageFace({required this.pressed});
  final bool pressed;

  @override
  Widget build(BuildContext context) {
    // Duas camadas sobrepostas: troca instantânea sem "piscar".
    return Stack(
      fit: StackFit.expand,
      children: [
        Image.asset('assets/images/sos_normal.png', fit: BoxFit.contain, gaplessPlayback: true),
        AnimatedOpacity(
          opacity: pressed ? 1 : 0,
          duration: const Duration(milliseconds: 90),
          child: Image.asset('assets/images/sos_pressed.png',
              fit: BoxFit.contain, gaplessPlayback: true),
        ),
      ],
    );
  }
}

/// Versão desenhada: aro metálico + cúpula vermelha + texto dinâmico.
class _VectorFace extends StatelessWidget {
  const _VectorFace({required this.pressed, required this.holdSeconds});
  final bool pressed;
  final int holdSeconds;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, c) {
      final s = c.maxWidth;
      return Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(size: Size.square(s), painter: _DomePainter(pressed: pressed)),
          Padding(
            padding: EdgeInsets.symmetric(horizontal: s * .16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                FittedBox(
                  child: Text(
                    'PEDIR AJUDA',
                    style: TextStyle(
                      fontSize: s * .115,
                      fontWeight: FontWeight.w700,
                      letterSpacing: .5,
                      color: const Color(0xFFF4D6A2),
                      shadows: const [Shadow(color: Color(0x99000000), blurRadius: 6, offset: Offset(0, 2))],
                    ),
                  ),
                ),
                SizedBox(height: s * .03),
                Text(
                  'SEGURE $holdSeconds SEGUNDOS\nPRA CHAMAR',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: s * .062,
                    height: 1.35,
                    fontWeight: FontWeight.w700,
                    color: Colors.white.withValues(alpha: .92),
                    shadows: const [Shadow(color: Color(0x99000000), blurRadius: 4, offset: Offset(0, 1))],
                  ),
                ),
              ],
            ),
          ),
        ],
      );
    });
  }
}

class _DomePainter extends CustomPainter {
  const _DomePainter({required this.pressed});
  final bool pressed;

  @override
  void paint(Canvas canvas, Size size) {
    final c = size.center(Offset.zero);
    final r = size.width / 2;

    // Sombra projetada
    canvas.drawCircle(
      c.translate(0, r * .04),
      r * .98,
      Paint()
        ..color = Colors.black.withValues(alpha: .6)
        ..maskFilter = MaskFilter.blur(BlurStyle.normal, r * .06),
    );

    // Aro metálico (bronze ↔ champagne)
    final bezel = Rect.fromCircle(center: c, radius: r);
    canvas.drawCircle(
      c,
      r,
      Paint()
        ..shader = const SweepGradient(
          colors: [
            Color(0xFF6F4E08), Color(0xFFE9C987), Color(0xFF94680C), Color(0xFFF6E2B3),
            Color(0xFF7A560B), Color(0xFFD9B26A), Color(0xFF6F4E08),
          ],
        ).createShader(bezel),
    );
    // Sulco escuro entre aro e cúpula
    canvas.drawCircle(c, r * .885, Paint()..color = const Color(0xFF1A0B07));

    // Cúpula vermelha
    final domeR = r * .855;
    final dome = Rect.fromCircle(center: c, radius: domeR);
    canvas.drawCircle(
      c,
      domeR,
      Paint()
        ..shader = RadialGradient(
          center: const Alignment(0, -.35),
          radius: 1.0,
          colors: pressed
              ? const [Color(0xFFA3221B), Color(0xFF6C110D), Color(0xFF3E0806)]
              : const [Color(0xFFD6352B), Color(0xFF9B1C15), Color(0xFF560C08)],
          stops: const [0, .6, 1],
        ).createShader(dome),
    );

    // Sombra interna quando pressionado
    if (pressed) {
      canvas.drawCircle(
        c,
        domeR,
        Paint()
          ..shader = RadialGradient(
            colors: [Colors.transparent, Colors.black.withValues(alpha: .45)],
            stops: const [.7, 1],
          ).createShader(dome),
      );
    }

    // Reflexo de vidro no topo
    final gloss = Rect.fromCenter(
      center: c.translate(0, -domeR * .52),
      width: domeR * 1.35,
      height: domeR * .62,
    );
    canvas.drawOval(
      gloss,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [Colors.white.withValues(alpha: pressed ? .10 : .26), Colors.transparent],
        ).createShader(gloss),
    );
  }

  @override
  bool shouldRepaint(_DomePainter old) => old.pressed != pressed;
}

class _ProgressRingPainter extends CustomPainter {
  const _ProgressRingPainter(this.value);
  final double value;

  @override
  void paint(Canvas canvas, Size size) {
    final rect = Offset.zero & size;
    final ring = rect.deflate(4);
    const start = -math.pi / 2;
    final sweep = 2 * math.pi * value;

    canvas.drawArc(
      ring,
      0,
      2 * math.pi,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 5
        ..color = VrColors.champagne.withValues(alpha: .15),
    );
    if (value <= 0) return;

    // Brilho
    canvas.drawArc(
      ring,
      start,
      sweep,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 10
        ..strokeCap = StrokeCap.round
        ..color = VrColors.champagne.withValues(alpha: .35)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 6),
    );
    // Traço principal
    canvas.drawArc(
      ring,
      start,
      sweep,
      false,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 5
        ..strokeCap = StrokeCap.round
        ..color = const Color(0xFFFFDE9F),
    );
  }

  @override
  bool shouldRepaint(_ProgressRingPainter old) => old.value != value;
}
