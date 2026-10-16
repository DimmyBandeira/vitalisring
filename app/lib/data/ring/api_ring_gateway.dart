import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../domain/ports.dart';
import '../../domain/ring_snapshot.dart';

/// Lê o estado do anel pela API FastAPI já existente no repositório
/// (`GET /readings/latest?device_id=...`). O collector.py grava a cada ~60 s,
/// então "conectado" = última leitura com menos de [staleAfter].
///
/// Resposta esperada:
/// `{"heart_rate": {"value": 78, "timestamp": "..."}, "spo2": {...}, "battery": {...}}`
class ApiRingGateway implements RingGateway {
  ApiRingGateway({
    required this.baseUrl,
    required this.deviceId,
    this.apiKey = '',
    this.pollEvery = const Duration(seconds: 15),
    this.staleAfter = const Duration(minutes: 3),
    http.Client? client,
  }) : _http = client ?? http.Client();

  final String baseUrl;
  final String deviceId;
  final String apiKey;
  final Duration pollEvery;
  final Duration staleAfter;
  final http.Client _http;

  final _ctrl = StreamController<RingSnapshot>.broadcast();
  RingSnapshot _current = RingSnapshot.initial;
  Timer? _timer;
  bool _disposed = false;

  @override
  Stream<RingSnapshot> get snapshots => _ctrl.stream;

  @override
  RingSnapshot get current => _current;

  @override
  Future<void> start() async {
    _emit(RingSnapshot.initial);
    await _poll();
    _timer = Timer.periodic(pollEvery, (_) => _poll());
  }

  Future<void> _poll() async {
    if (_disposed) return;
    final uri = Uri.parse(baseUrl).replace(
      path: '${Uri.parse(baseUrl).path.replaceAll(RegExp(r'/$'), '')}/readings/latest',
      queryParameters: {'device_id': deviceId},
    );
    try {
      final res = await _http.get(uri, headers: {
        if (apiKey.isNotEmpty) 'X-API-Key': apiKey,
      }).timeout(const Duration(seconds: 8));

      if (res.statusCode != 200) {
        _emit(_current.copyWith(link: RingLink.disconnected, detail: 'HTTP ${res.statusCode}'));
        return;
      }
      _emit(_parse(jsonDecode(res.body) as Map<String, dynamic>));
    } catch (e) {
      _emit(_current.copyWith(link: RingLink.disconnected, detail: 'API inacessível: $e'));
    }
  }

  RingSnapshot _parse(Map<String, dynamic> body) {
    int? val(String k) => (body[k]?['value'] as num?)?.round();
    DateTime? ts(String k) {
      final raw = body[k]?['timestamp'] as String?;
      if (raw == null) return null;
      // A API grava UTC sem fuso (naive). Tratar como UTC.
      final hasTz = raw.endsWith('Z') || RegExp(r'[+-]\d\d:\d\d$').hasMatch(raw);
      return DateTime.tryParse(hasTz ? raw : '${raw}Z')?.toLocal();
    }

    final stamps = [ts('heart_rate'), ts('spo2'), ts('battery')].whereType<DateTime>().toList()
      ..sort();
    final latest = stamps.isEmpty ? null : stamps.last;
    final fresh = latest != null && DateTime.now().difference(latest) < staleAfter;

    return RingSnapshot(
      link: fresh ? RingLink.connected : RingLink.disconnected,
      batteryPercent: val('battery'),
      heartRate: val('heart_rate'),
      spo2: val('spo2'),
      updatedAt: latest,
      detail: latest == null ? 'Sem leituras para $deviceId' : null,
    );
  }

  void _emit(RingSnapshot s) {
    _current = s;
    if (!_ctrl.isClosed) _ctrl.add(s);
  }

  @override
  Future<void> dispose() async {
    _disposed = true;
    _timer?.cancel();
    _http.close();
    await _ctrl.close();
  }
}
