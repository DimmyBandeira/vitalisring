import 'dart:async';

import '../../domain/ports.dart';
import '../../domain/ring_snapshot.dart';

/// ETAPA 2 — Colmi R10 direto no celular (sem PC/collector no meio).
///
/// Plano de implementação (porte do `colmi_r02_client` para Dart):
/// - Lib BLE: `flutter_blue_plus`
/// - Serviço UART do anel (conferir com o colmi_r02_client): 6E40FFF0-B5A3-F393-E0A9-E50E24DCCA9E
///   (RX write 6E400002-..., TX notify 6E400003-...)
/// - Pacotes de 16 bytes: [cmd, payload x14, checksum = soma & 0xFF]
/// - Comandos já validados no Python: bateria, HR tempo real, SpO2 tempo real
/// - Android: foreground service + permissões BLUETOOTH_SCAN/CONNECT,
///   e isenção de otimização de bateria para não perder a conexão em segundo plano.
///
/// Até lá, este gateway só sinaliza "procurando", para a UI já tratar o estado.
class BleRingGateway implements RingGateway {
  BleRingGateway({required this.address});

  /// Endereço do anel de teste: 30:36:44:34:F5:06 (COLMI R10_F506).
  final String address;

  final _ctrl = StreamController<RingSnapshot>.broadcast();
  RingSnapshot _current = const RingSnapshot(
    link: RingLink.searching,
    detail: 'BLE direto: disponível na etapa 2',
  );

  @override
  Stream<RingSnapshot> get snapshots => _ctrl.stream;

  @override
  RingSnapshot get current => _current;

  @override
  Future<void> start() async => _ctrl.add(_current);

  @override
  Future<void> dispose() => _ctrl.close();
}
