import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../core/services_scope.dart';
import '../../core/theme/vr_colors.dart';
import '../../ui/painters.dart';
import 'sos_controller.dart';

/// Tela cheia após confirmar o SOS. Estados: enviando → enviado | falhou → cancelado.
class SosScreen extends StatefulWidget {
  const SosScreen({super.key});

  static Route<bool> route() => PageRouteBuilder<bool>(
        opaque: true,
        transitionDuration: const Duration(milliseconds: 380),
        pageBuilder: (_, __, ___) => const SosScreen(),
        transitionsBuilder: (_, a, __, child) => FadeTransition(
          opacity: a,
          child: ScaleTransition(
            scale: Tween(begin: 1.04, end: 1.0).animate(CurvedAnimation(parent: a, curve: Curves.easeOut)),
            child: child,
          ),
        ),
      );

  @override
  State<SosScreen> createState() => _SosScreenState();
}

class _SosScreenState extends State<SosScreen> with SingleTickerProviderStateMixin {
  SosController? _ctrl;
  late final AnimationController _pulse =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1400))..repeat();

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_ctrl != null) return;
    final services = ServicesScope.of(context);
    _ctrl = SosController(
      gateway: services.alert,
      deviceId: services.settings.deviceId,
      ring: services.ring.current,
    )..addListener(_onChange);
    // Dispara após o primeiro frame para não notificar durante o build.
    WidgetsBinding.instance.addPostFrameCallback((_) => _ctrl?.send());
  }

  void _onChange() {
    final c = _ctrl!;
    if (c.stage == SosStage.sent) HapticFeedback.heavyImpact();
    if (c.stage == SosStage.cancelled) {
      Navigator.of(context).pop(true);
      return;
    }
    setState(() {});
  }

  @override
  void dispose() {
    _ctrl?.removeListener(_onChange);
    _ctrl?.dispose();
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _confirmCancel() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: VrColors.card,
        title: const Text('Cancelar o pedido de ajuda?', style: TextStyle(fontSize: 24)),
        content: const Text(
          'Seus contatos serão avisados de que está tudo bem.',
          style: TextStyle(fontSize: 19, color: VrColors.inkSoft),
        ),
        actionsPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        actions: [
          _DialogButton(label: 'NÃO', onTap: () => Navigator.pop(ctx, false)),
          _DialogButton(label: 'SIM, ESTOU BEM', primary: true, onTap: () => Navigator.pop(ctx, true)),
        ],
      ),
    );
    if (ok == true) await _ctrl!.cancel();
  }

  void _emergencyCall() {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: VrColors.card,
        title: const Text('Ligar para o SAMU (192)', style: TextStyle(fontSize: 22)),
        content: const Text(
          'Versão de demonstração: a ligação não é feita.\n'
          'Na versão final este botão abre o discador com 192.',
          style: TextStyle(fontSize: 18, color: VrColors.inkSoft),
        ),
        actions: [_DialogButton(label: 'ENTENDI', primary: true, onTap: () => Navigator.pop(ctx))],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final c = _ctrl!;
    final busy = c.stage == SosStage.sending || c.stage == SosStage.cancelling;

    final (Color tone, IconData icon, String title, String body) = switch (c.stage) {
      SosStage.sending => (
          VrColors.criticalBright,
          Icons.campaign_rounded,
          'Chamando ajuda…',
          'Fique calmo. Estamos avisando seus contatos.',
        ),
      SosStage.sent => (
          VrColors.ok,
          Icons.check_rounded,
          'Ajuda a caminho',
          c.receipt!.notified.isEmpty
              ? 'Seu pedido foi recebido.'
              : 'Avisamos:\n${c.receipt!.notified.join('\n')}',
        ),
      SosStage.failed => (
          VrColors.warn,
          Icons.wifi_off_rounded,
          'Não conseguimos enviar',
          'Vamos tentar de novo em ${c.retryIn} s.',
        ),
      SosStage.cancelling || SosStage.cancelled => (
          VrColors.gold,
          Icons.hourglass_top_rounded,
          'Cancelando…',
          'Avisando que está tudo bem.',
        ),
    };

    return PopScope(
      canPop: !busy,
      child: Scaffold(
        body: CustomPaint(
          painter: const BackdropPainter(glowCenter: Offset(.5, .32), glowStrength: .6),
          child: SafeArea(
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 480),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(24, 32, 24, 24),
                  child: Column(
                    children: [
                      const Spacer(flex: 2),
                      _StatusBadge(
                        pulse: _pulse,
                        tone: tone,
                        icon: icon,
                        animate: c.stage == SosStage.sending,
                      ),
                      const SizedBox(height: 36),
                      Semantics(
                        liveRegion: true,
                        child: Text(
                          title,
                          textAlign: TextAlign.center,
                          style: const TextStyle(fontSize: 34, fontWeight: FontWeight.w700, color: VrColors.ink),
                        ),
                      ),
                      const SizedBox(height: 14),
                      Text(
                        body,
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 21, height: 1.45, color: VrColors.inkSoft),
                      ),
                      if (c.stage == SosStage.sent && c.sentAt != null) ...[
                        const SizedBox(height: 10),
                        Text(
                          'Enviado às ${_hhmm(c.sentAt!)}',
                          style: TextStyle(fontSize: 17, color: VrColors.gold.withValues(alpha: .9)),
                        ),
                      ],
                      const Spacer(flex: 3),
                      ..._actions(c),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _actions(SosController c) {
    switch (c.stage) {
      case SosStage.sending:
      case SosStage.cancelling:
      case SosStage.cancelled:
        return const [SizedBox(height: 72)];
      case SosStage.failed:
        return [
          _BigButton(label: 'TENTAR DE NOVO AGORA', primary: true, onTap: c.send),
          const SizedBox(height: 14),
          _BigButton(label: 'LIGAR PARA O SAMU (192)', icon: Icons.call_rounded, onTap: _emergencyCall),
        ];
      case SosStage.sent:
        return [
          _BigButton(label: 'ESTOU BEM — CANCELAR', onTap: _confirmCancel),
          const SizedBox(height: 14),
          _BigButton(
            label: 'VOLTAR AO INÍCIO',
            primary: true,
            onTap: () => Navigator.of(context).pop(false),
          ),
        ];
    }
  }

  static String _hhmm(DateTime t) =>
      '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.pulse, required this.tone, required this.icon, required this.animate});
  final Animation<double> pulse;
  final Color tone;
  final IconData icon;
  final bool animate;

  @override
  Widget build(BuildContext context) {
    const d = 150.0;
    return SizedBox.square(
      dimension: d * 1.9,
      child: AnimatedBuilder(
        animation: pulse,
        builder: (context, _) {
          return Stack(
            alignment: Alignment.center,
            children: [
              if (animate)
                for (final offset in const [0.0, .5])
                  Builder(builder: (_) {
                    final t = (pulse.value + offset) % 1;
                    return Container(
                      width: d * (1 + .9 * t),
                      height: d * (1 + .9 * t),
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(color: tone.withValues(alpha: (1 - t) * .6), width: 3),
                      ),
                    );
                  }),
              AnimatedContainer(
                duration: const Duration(milliseconds: 350),
                width: d,
                height: d,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: tone.withValues(alpha: .16),
                  border: Border.all(color: tone, width: 4),
                  boxShadow: [BoxShadow(color: tone.withValues(alpha: .45), blurRadius: 40)],
                ),
                child: AnimatedSwitcher(
                  duration: const Duration(milliseconds: 250),
                  transitionBuilder: (child, a) => ScaleTransition(scale: a, child: child),
                  child: Icon(icon, key: ValueKey(icon), size: 76, color: tone),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _BigButton extends StatelessWidget {
  const _BigButton({required this.label, required this.onTap, this.primary = false, this.icon});
  final String label;
  final VoidCallback onTap;
  final bool primary;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final style = primary
        ? FilledButton.styleFrom(
            backgroundColor: VrColors.gold,
            foregroundColor: VrColors.surface,
            minimumSize: const Size.fromHeight(68),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
            textStyle: const TextStyle(fontFamily: 'Atkinson', fontSize: 20, fontWeight: FontWeight.w700),
          )
        : OutlinedButton.styleFrom(
            foregroundColor: VrColors.ink,
            minimumSize: const Size.fromHeight(68),
            side: const BorderSide(color: VrColors.gold, width: 2),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(999)),
            textStyle: const TextStyle(fontFamily: 'Atkinson', fontSize: 20, fontWeight: FontWeight.w700),
          );
    final child = Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        if (icon != null) ...[Icon(icon, size: 26), const SizedBox(width: 10)],
        Flexible(child: Text(label, textAlign: TextAlign.center)),
      ],
    );
    return primary
        ? FilledButton(onPressed: onTap, style: style, child: child)
        : OutlinedButton(onPressed: onTap, style: style, child: child);
  }
}

class _DialogButton extends StatelessWidget {
  const _DialogButton({required this.label, required this.onTap, this.primary = false});
  final String label;
  final VoidCallback onTap;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    return TextButton(
      onPressed: onTap,
      style: TextButton.styleFrom(
        minimumSize: const Size(88, 56),
        foregroundColor: primary ? VrColors.gold : VrColors.inkSoft,
        textStyle: const TextStyle(fontFamily: 'Atkinson', fontSize: 19, fontWeight: FontWeight.w700),
      ),
      child: Text(label),
    );
  }
}
