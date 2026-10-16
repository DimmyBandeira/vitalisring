import 'dart:ui' show FontFeature;

import 'package:flutter/material.dart';

import '../../../core/theme/vr_colors.dart';
import '../../../domain/ring_snapshot.dart';
import '../../../ui/painters.dart';

String timeAgo(DateTime? t) {
  if (t == null) return '';
  final d = DateTime.now().difference(t);
  if (d.inSeconds < 60) return 'agora';
  if (d.inMinutes < 60) return 'há ${d.inMinutes} min';
  if (d.inHours < 24) return 'há ${d.inHours} h';
  return 'há ${d.inDays} dia${d.inDays > 1 ? 's' : ''}';
}

const _cardRadius = 22.0;

BoxDecoration vrCardDecoration({Color? border}) => BoxDecoration(
      color: const Color(0xFF14110D).withValues(alpha: .82),
      borderRadius: BorderRadius.circular(_cardRadius),
      border: Border.all(color: border ?? VrColors.champagne.withValues(alpha: .38), width: 1.2),
      boxShadow: const [BoxShadow(color: Color(0x66000000), blurRadius: 18, offset: Offset(0, 8))],
    );

/// Marca discreta no topo. Pressionar 2 s abre Ajustes (acesso do cuidador),
/// para o idoso não entrar sem querer.
class BrandHeader extends StatelessWidget {
  const BrandHeader({super.key, required this.onSecretOpen});
  final VoidCallback onSecretOpen;

  @override
  Widget build(BuildContext context) {
    return _LongHold(
      duration: const Duration(seconds: 2),
      onFire: onSecretOpen,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const SizedBox(
              width: 22,
              height: 25,
              child: CustomPaint(painter: BrandSymbolPainter()),
            ),
            const SizedBox(width: 10),
            Text(
              'VITALIS RING',
              style: TextStyle(
                fontFamily: 'Cormorant',
                fontWeight: FontWeight.w600,
                fontSize: 20,
                letterSpacing: 4.4,
                color: VrColors.gold.withValues(alpha: .9),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LongHold extends StatefulWidget {
  const _LongHold({required this.duration, required this.onFire, required this.child});
  final Duration duration;
  final VoidCallback onFire;
  final Widget child;

  @override
  State<_LongHold> createState() => _LongHoldState();
}

class _LongHoldState extends State<_LongHold> {
  DateTime? _down;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onLongPressStart: (_) => _down = DateTime.now(),
      onLongPressEnd: (_) {
        final d = _down;
        _down = null;
        if (d != null && DateTime.now().difference(d) + kLongPressTimeout >= widget.duration) {
          widget.onFire();
        }
      },
      child: widget.child,
    );
  }
}

/// Pílula "CONECTADO AO ANEL" e variações.
class ConnectionChip extends StatefulWidget {
  const ConnectionChip({super.key, required this.link});
  final RingLink link;

  @override
  State<ConnectionChip> createState() => _ConnectionChipState();
}

class _ConnectionChipState extends State<ConnectionChip> with SingleTickerProviderStateMixin {
  late final AnimationController _pulse =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1100))
        ..repeat(reverse: true);

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final (color, label, hint) = switch (widget.link) {
      RingLink.connected => (VrColors.ok, 'CONECTADO AO ANEL', null),
      RingLink.searching => (VrColors.warn, 'PROCURANDO O ANEL…', 'Mantenha o anel perto do celular'),
      RingLink.disconnected => (VrColors.criticalBright, 'ANEL DESCONECTADO', 'Aproxime o anel do celular'),
    };
    final pulsing = widget.link != RingLink.connected;

    return Semantics(
      liveRegion: true,
      label: hint == null ? label : '$label. $hint',
      excludeSemantics: true,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 16),
        decoration: vrCardDecoration().copyWith(
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: (widget.link == RingLink.connected ? VrColors.champagne : color)
                .withValues(alpha: .45),
            width: 1.2,
          ),
        ),
        child: Row(
          children: [
            AnimatedBuilder(
              animation: _pulse,
              builder: (context, _) {
                final glow = pulsing ? .35 + .65 * _pulse.value : 1.0;
                return Container(
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: color,
                    boxShadow: [
                      BoxShadow(color: color.withValues(alpha: .7 * glow), blurRadius: 12, spreadRadius: 1),
                    ],
                  ),
                );
              },
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  FittedBox(
                    fit: BoxFit.scaleDown,
                    alignment: Alignment.centerLeft,
                    child: Text(
                      label,
                      style: const TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.w700,
                        letterSpacing: .6,
                        color: VrColors.ink,
                      ),
                    ),
                  ),
                  if (hint != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(hint, style: const TextStyle(fontSize: 16, color: VrColors.inkSoft)),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Card "Bateria do Anel: 85%" com ícone vertical.
class BatteryCard extends StatelessWidget {
  const BatteryCard({super.key, required this.snapshot});
  final RingSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final pct = snapshot.batteryPercent;
    final stale = snapshot.link != RingLink.connected && pct != null;
    final low = snapshot.lowBattery;
    final accent = low ? VrColors.warn : VrColors.gold;

    final String? note = switch ((low, snapshot.charging, stale)) {
      (_, true, _) => 'Carregando',
      (true, _, _) => 'Carregue o anel hoje',
      (_, _, true) => 'Última leitura ${timeAgo(snapshot.updatedAt)}',
      _ => null,
    };

    return Semantics(
      label: pct == null
          ? 'Bateria do anel: sem informação'
          : 'Bateria do anel: $pct por cento${note != null ? '. $note' : ''}',
      excludeSemantics: true,
      child: Container(
        padding: const EdgeInsets.fromLTRB(26, 22, 22, 22),
        decoration: vrCardDecoration(border: low ? VrColors.warn.withValues(alpha: .6) : null),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Bateria do Anel:',
                    style: TextStyle(fontSize: 19, color: VrColors.gold.withValues(alpha: .95)),
                  ),
                  const SizedBox(height: 4),
                  TweenAnimationBuilder<double>(
                    tween: Tween(end: (pct ?? 0).toDouble()),
                    duration: const Duration(milliseconds: 700),
                    curve: Curves.easeOutCubic,
                    builder: (context, v, _) => Text(
                      pct == null ? '--' : '${v.round()}%',
                      style: TextStyle(
                        fontSize: 46,
                        height: 1.05,
                        fontWeight: FontWeight.w700,
                        color: low ? VrColors.warn : VrColors.ink,
                        fontFeatures: const [FontFeature.tabularFigures()],
                      ),
                    ),
                  ),
                  if (note != null) ...[
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        if (low && !snapshot.charging) ...[
                          const Icon(Icons.warning_amber_rounded, color: VrColors.warn, size: 20),
                          const SizedBox(width: 6),
                        ],
                        Flexible(
                          child: Text(
                            note,
                            style: TextStyle(
                              fontSize: 17,
                              color: low ? VrColors.warn : VrColors.inkSoft,
                              fontWeight: low ? FontWeight.w700 : FontWeight.w400,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            SizedBox(
              width: 46,
              height: 70,
              child: CustomPaint(
                painter: BatteryIconPainter(
                  level: pct == null ? null : pct / 100,
                  color: accent,
                  charging: snapshot.charging,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Linha compacta de sinais vitais (opcional, liga/desliga em Ajustes).
class VitalsStrip extends StatelessWidget {
  const VitalsStrip({super.key, required this.snapshot});
  final RingSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final dim = snapshot.link != RingLink.connected;
    return Opacity(
      opacity: dim ? .55 : 1,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: vrCardDecoration(),
        child: Row(
          children: [
            Expanded(
              child: _Vital(
                icon: Icons.favorite_rounded,
                iconColor: const Color(0xFFE5534B),
                label: 'Coração',
                value: snapshot.heartRate?.toString() ?? '--',
                unit: 'bpm',
              ),
            ),
            Container(width: 1, height: 44, color: VrColors.line),
            Expanded(
              child: _Vital(
                icon: Icons.water_drop_rounded,
                iconColor: const Color(0xFF5AA9E6),
                label: 'Oxigênio',
                value: snapshot.spo2?.toString() ?? '--',
                unit: '%',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Vital extends StatelessWidget {
  const _Vital({
    required this.icon,
    required this.iconColor,
    required this.label,
    required this.value,
    required this.unit,
  });
  final IconData icon;
  final Color iconColor;
  final String label;
  final String value;
  final String unit;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '$label: $value $unit',
      excludeSemantics: true,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, color: iconColor, size: 26),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label, style: const TextStyle(fontSize: 15, color: VrColors.inkSoft)),
              Text.rich(
                TextSpan(children: [
                  TextSpan(
                    text: value,
                    style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w700, color: VrColors.ink),
                  ),
                  TextSpan(text: ' $unit', style: const TextStyle(fontSize: 16, color: VrColors.inkSoft)),
                ]),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
