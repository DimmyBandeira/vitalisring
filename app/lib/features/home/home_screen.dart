import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../core/services_scope.dart';
import '../../core/theme/vr_colors.dart';
import '../../domain/ring_snapshot.dart';
import '../../ui/painters.dart';
import '../settings/settings_screen.dart';
import '../sos/sos_screen.dart';
import 'widgets/sos_hold_button.dart';
import 'widgets/status_widgets.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  HoldPhase _phase = HoldPhase.idle;
  int _secondsLeft = 0;
  Timer? _hintTimer;

  void _onPhase(HoldPhase p) {
    _hintTimer?.cancel();
    setState(() => _phase = p);
    if (p == HoldPhase.released) {
      // Mensagem de "segure mais" some sozinha.
      _hintTimer = Timer(const Duration(seconds: 3), () {
        if (mounted) setState(() => _phase = HoldPhase.idle);
      });
    }
  }

  Future<void> _openSos() async {
    final cancelled = await Navigator.of(context).push(SosScreen.route());
    if (!mounted) return;
    setState(() => _phase = HoldPhase.idle);
    if (cancelled == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: VrColors.card,
          content: Text('Pedido cancelado. Que bom que está tudo bem.',
              style: TextStyle(fontSize: 18, color: VrColors.ink)),
        ),
      );
    }
  }

  void _openSettings() {
    Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen()));
  }

  @override
  void dispose() {
    _hintTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final services = ServicesScope.of(context);
    final settings = services.settings;
    final ring = services.ring;

    return Scaffold(
      body: StreamBuilder<RingSnapshot>(
        // key força reassinatura quando a fonte de dados muda em Ajustes.
        key: ValueKey(ring),
        stream: ring.snapshots,
        initialData: ring.current,
        builder: (context, snap) {
          final s = snap.data ?? RingSnapshot.initial;
          return CustomPaint(
            painter: BackdropPainter(
              glowCenter: const Offset(.5, .45),
              glowStrength: _phase == HoldPhase.holding ? 1.4 : 1,
            ),
            child: SafeArea(
              child: Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 480),
                  child: LayoutBuilder(builder: (context, box) {
                    // Botão o maior possível sem empurrar os cards para fora da tela.
                    // reserved = altura de tudo que não é o botão; 1.12 = anel de progresso.
                    final reserved = settings.showVitals ? 500.0 : 410.0;
                    final button = math.min(
                      box.maxWidth * .78,
                      math.max(200.0, (box.maxHeight - reserved) / 1.12),
                    );

                    return Padding(
                      padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                      child: Column(
                        children: [
                          BrandHeader(onSecretOpen: _openSettings),
                          const SizedBox(height: 14),
                          ConnectionChip(link: s.link),
                          const Spacer(),
                          SosHoldButton(
                            size: button,
                            holdSeconds: settings.holdSeconds,
                            style: settings.buttonStyle,
                            onConfirmed: _openSos,
                            onPhaseChanged: _onPhase,
                            onSecondsLeft: (v) => setState(() => _secondsLeft = v),
                          ),
                          SizedBox(height: 64, child: Center(child: _hint(settings.holdSeconds))),
                          const Spacer(),
                          BatteryCard(snapshot: s),
                          if (settings.showVitals) ...[
                            const SizedBox(height: 12),
                            VitalsStrip(snapshot: s),
                          ],
                        ],
                      ),
                    );
                  }),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _hint(int holdSeconds) {
    final Widget child = switch (_phase) {
      HoldPhase.holding => Text.rich(
          TextSpan(children: [
            const TextSpan(text: 'Continue segurando…  '),
            TextSpan(
              text: '$_secondsLeft',
              style: const TextStyle(fontSize: 34, color: Color(0xFFFFDE9F)),
            ),
          ]),
          key: const ValueKey('holding'),
          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: VrColors.ink),
        ),
      HoldPhase.released => Text(
          'Segure por $holdSeconds segundos\npara chamar ajuda',
          key: const ValueKey('released'),
          textAlign: TextAlign.center,
          style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700, color: VrColors.goldLight),
        ),
      _ => const SizedBox.shrink(key: ValueKey('idle')),
    };
    return Semantics(
      liveRegion: true,
      child: AnimatedSwitcher(duration: const Duration(milliseconds: 200), child: child),
    );
  }
}
