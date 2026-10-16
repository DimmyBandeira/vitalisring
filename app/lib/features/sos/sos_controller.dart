import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../domain/ports.dart';
import '../../domain/ring_snapshot.dart';

enum SosStage { sending, sent, failed, cancelling, cancelled }

/// Máquina de estados do pedido de ajuda. Sem dependência de UI.
class SosController extends ChangeNotifier {
  SosController({
    required AlertGateway gateway,
    required this.deviceId,
    this.ring,
    this.autoRetryAfter = const Duration(seconds: 10),
  }) : _gateway = gateway;

  final AlertGateway _gateway;
  final String deviceId;
  final RingSnapshot? ring;
  final Duration autoRetryAfter;

  SosStage _stage = SosStage.sending;
  SosReceipt? _receipt;
  String? _error;
  DateTime? _sentAt;
  int _attempts = 0;
  int _retryIn = 0;
  Timer? _retryTimer;
  bool _disposed = false;

  SosStage get stage => _stage;
  SosReceipt? get receipt => _receipt;
  String? get error => _error;
  DateTime? get sentAt => _sentAt;
  int get attempts => _attempts;
  int get retryIn => _retryIn;

  Future<void> send() async {
    _retryTimer?.cancel();
    _set(SosStage.sending);
    _attempts++;
    try {
      final r = await _gateway.sendSos(SosRequest(
        deviceId: deviceId,
        triggeredAt: DateTime.now(),
        ring: ring,
      ));
      if (_disposed) return;
      _receipt = r;
      _sentAt = DateTime.now();
      _error = null;
      _set(SosStage.sent);
    } on SosException catch (e) {
      if (_disposed) return;
      _error = e.message;
      _set(SosStage.failed);
      _scheduleRetry();
    }
  }

  void _scheduleRetry() {
    _retryIn = autoRetryAfter.inSeconds;
    _retryTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      _retryIn--;
      if (_retryIn <= 0) {
        t.cancel();
        send();
      } else {
        notifyListeners();
      }
    });
  }

  Future<void> cancel() async {
    _retryTimer?.cancel();
    final id = _receipt?.alertId;
    _set(SosStage.cancelling);
    if (id != null) {
      try {
        await _gateway.cancel(id, reason: 'user_ok');
      } catch (_) {
        // Cancelamento é melhor-esforço; o backend deve expirar o alerta.
      }
    }
    if (!_disposed) _set(SosStage.cancelled);
  }

  void _set(SosStage s) {
    _stage = s;
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _retryTimer?.cancel();
    super.dispose();
  }
}
