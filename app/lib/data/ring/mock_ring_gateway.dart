import 'dart:async';
import 'dart:math';

import '../../domain/ports.dart';
import '../../domain/ring_snapshot.dart';

/// Simula o anel para validar o design de todos os estados sem hardware.
/// O cenário (link, bateria, carregando) vem de Ajustes e pode mudar ao vivo.
class MockRingGateway implements RingGateway {
  MockRingGateway({
    required RingLink link,
    required int battery,
    required bool charging,
  })  : _link = link,
        _battery = battery,
        _charging = charging;

  RingLink _link;
  int _battery;
  bool _charging;

  final _rng = Random();
  final _ctrl = StreamController<RingSnapshot>.broadcast();
  RingSnapshot _current = RingSnapshot.initial;
  Timer? _tick;
  Timer? _boot;

  @override
  Stream<RingSnapshot> get snapshots => _ctrl.stream;

  @override
  RingSnapshot get current => _current;

  @override
  Future<void> start() async {
    _emit(RingSnapshot.initial);
    // Simula ~1,5 s de busca/conexão ao abrir o app.
    _boot = Timer(const Duration(milliseconds: 1500), () {
      _publish();
      _tick = Timer.periodic(const Duration(seconds: 4), (_) => _publish());
    });
  }

  /// Atualiza o cenário sem recriar o gateway (usado por Ajustes).
  void applyScenario({required RingLink link, required int battery, required bool charging}) {
    _link = link;
    _battery = battery;
    _charging = charging;
    if (_boot?.isActive ?? false) return;
    _publish();
  }

  void _publish() {
    final connected = _link == RingLink.connected;
    _emit(RingSnapshot(
      link: _link,
      batteryPercent: _battery,
      charging: _charging,
      heartRate: connected ? 72 + _rng.nextInt(9) : _current.heartRate,
      spo2: connected ? 96 + _rng.nextInt(3) : _current.spo2,
      updatedAt: connected ? DateTime.now() : _current.updatedAt,
      detail: 'simulação',
    ));
  }

  void _emit(RingSnapshot s) {
    _current = s;
    if (!_ctrl.isClosed) _ctrl.add(s);
  }

  @override
  Future<void> dispose() async {
    _boot?.cancel();
    _tick?.cancel();
    await _ctrl.close();
  }
}
