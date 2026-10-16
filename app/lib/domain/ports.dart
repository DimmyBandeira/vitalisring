import 'ring_snapshot.dart';

/// Porta de entrada do anel. Implementações:
/// - [MockRingGateway]  — simulação controlável (design/demos)
/// - [ApiRingGateway]   — lê a API FastAPI do projeto (`GET /readings/latest`)
/// - [BleRingGateway]   — etapa 2: Colmi R10 direto via BLE no celular
abstract interface class RingGateway {
  Stream<RingSnapshot> get snapshots;
  RingSnapshot get current;
  Future<void> start();
  Future<void> dispose();
}

class SosRequest {
  const SosRequest({
    required this.deviceId,
    required this.triggeredAt,
    this.source = 'app_button',
    this.ring,
  });

  final String deviceId;
  final DateTime triggeredAt;

  /// `app_button` hoje; no futuro `ring_fall`, `ring_hr_out_of_range`...
  final String source;
  final RingSnapshot? ring;

  Map<String, dynamic> toJson() => {
        'device_id': deviceId,
        'triggered_at': triggeredAt.toUtc().toIso8601String(),
        'source': source,
        if (ring != null)
          'ring': {
            'battery': ring!.batteryPercent,
            'heart_rate': ring!.heartRate,
            'spo2': ring!.spo2,
            'link': ring!.link.name,
          },
      };
}

class SosReceipt {
  const SosReceipt({required this.alertId, this.notified = const []});
  final String alertId;

  /// Nomes de quem foi avisado (vem do backend). Exibido na tela de confirmação.
  final List<String> notified;
}

class SosException implements Exception {
  const SosException(this.message);
  final String message;
  @override
  String toString() => 'SosException: $message';
}

/// Porta de saída do alerta. Implementações: mock e HTTP (`POST /alerts/sos`).
abstract interface class AlertGateway {
  Future<SosReceipt> sendSos(SosRequest request);
  Future<void> cancel(String alertId, {required String reason});
}
