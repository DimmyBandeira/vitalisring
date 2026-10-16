/// Estado do anel visto pelo app — independente de onde vem (mock, API, BLE).
enum RingLink {
  /// Procurando/conectando.
  searching,

  /// Dados frescos chegando.
  connected,

  /// Sem dados recentes / fora de alcance.
  disconnected,
}

class RingSnapshot {
  const RingSnapshot({
    required this.link,
    this.batteryPercent,
    this.charging = false,
    this.heartRate,
    this.spo2,
    this.updatedAt,
    this.detail,
  });

  final RingLink link;
  final int? batteryPercent;
  final bool charging;
  final int? heartRate;
  final int? spo2;
  final DateTime? updatedAt;

  /// Texto técnico opcional (erro de rede etc.). Só aparece em Ajustes.
  final String? detail;

  static const initial = RingSnapshot(link: RingLink.searching);

  bool get lowBattery => (batteryPercent ?? 100) <= 20 && !charging;

  RingSnapshot copyWith({
    RingLink? link,
    int? batteryPercent,
    bool? charging,
    int? heartRate,
    int? spo2,
    DateTime? updatedAt,
    String? detail,
  }) {
    return RingSnapshot(
      link: link ?? this.link,
      batteryPercent: batteryPercent ?? this.batteryPercent,
      charging: charging ?? this.charging,
      heartRate: heartRate ?? this.heartRate,
      spo2: spo2 ?? this.spo2,
      updatedAt: updatedAt ?? this.updatedAt,
      detail: detail,
    );
  }
}
