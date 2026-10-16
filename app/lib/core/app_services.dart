import 'package:flutter/foundation.dart';

import '../data/alert/alert_gateways.dart';
import '../data/ring/api_ring_gateway.dart';
import '../data/ring/ble_ring_gateway.dart';
import '../data/ring/mock_ring_gateway.dart';
import '../domain/ports.dart';
import 'config/app_settings.dart';

/// Composição de dependências. Troca os gateways quando Ajustes muda a fonte,
/// sem que as telas precisem saber de onde vem o dado.
class AppServices extends ChangeNotifier {
  AppServices._(this._settings);

  static Future<AppServices> bootstrap() async {
    final s = AppServices._(await AppSettings.load());
    await s._buildGateways();
    return s;
  }

  AppSettings _settings;
  late RingGateway _ring;
  late AlertGateway _alert;

  AppSettings get settings => _settings;
  RingGateway get ring => _ring;
  AlertGateway get alert => _alert;

  Future<void> _buildGateways() async {
    final s = _settings;
    _ring = switch (s.ringSource) {
      RingSource.mock => MockRingGateway(
          link: s.mockLink,
          battery: s.mockBattery,
          charging: s.mockCharging,
        ),
      RingSource.api => ApiRingGateway(
          baseUrl: s.apiBaseUrl,
          deviceId: s.deviceId,
          apiKey: s.apiKey,
        ),
      RingSource.ble => BleRingGateway(address: '30:36:44:34:F5:06'),
    };
    _alert = switch (s.alertSource) {
      AlertSource.mock => MockAlertGateway(fail: s.mockSosFails),
      AlertSource.http => HttpAlertGateway(baseUrl: s.apiBaseUrl, apiKey: s.apiKey),
    };
    await _ring.start();
  }

  Future<void> update(AppSettings next) async {
    final prev = _settings;
    _settings = next;
    await next.save();

    if (prev.needsGatewayRebuild(next)) {
      final old = _ring;
      await _buildGateways();
      await old.dispose();
    } else {
      // Ajustes "ao vivo" da simulação sem reiniciar a busca.
      final r = _ring;
      if (r is MockRingGateway) {
        r.applyScenario(link: next.mockLink, battery: next.mockBattery, charging: next.mockCharging);
      }
      if (next.alertSource == AlertSource.mock) _alert = MockAlertGateway(fail: next.mockSosFails);
    }
    notifyListeners();
  }

  Future<void> resetAll() async {
    await AppSettings.reset();
    await update(AppSettings.defaults);
  }

  @override
  void dispose() {
    _ring.dispose();
    super.dispose();
  }
}
