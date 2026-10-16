import 'package:shared_preferences/shared_preferences.dart';

import '../../domain/ring_snapshot.dart';

enum RingSource { mock, api, ble }

enum AlertSource { mock, http }

enum SosButtonStyle { image, vector }

/// Configuração persistida. Valores iniciais podem vir do build:
/// `flutter build apk --dart-define=API_BASE_URL=http://10.0.0.5:8000 --dart-define=API_KEY=...`
class AppSettings {
  const AppSettings({
    required this.ringSource,
    required this.alertSource,
    required this.apiBaseUrl,
    required this.apiKey,
    required this.deviceId,
    required this.buttonStyle,
    required this.showVitals,
    required this.mockLink,
    required this.mockBattery,
    required this.mockCharging,
    required this.mockSosFails,
    required this.holdSeconds,
  });

  final RingSource ringSource;
  final AlertSource alertSource;
  final String apiBaseUrl;
  final String apiKey;
  final String deviceId;
  final SosButtonStyle buttonStyle;
  final bool showVitals;

  // Cenário da simulação (para testar design de todos os estados).
  final RingLink mockLink;
  final int mockBattery;
  final bool mockCharging;
  final bool mockSosFails;

  final int holdSeconds;

  static const _envBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://192.168.0.10:8000',
  );
  static const _envApiKey = String.fromEnvironment('API_KEY');
  static const _envDeviceId = String.fromEnvironment('DEVICE_ID', defaultValue: 'ring-01');

  static const defaults = AppSettings(
    ringSource: RingSource.mock,
    alertSource: AlertSource.mock,
    apiBaseUrl: _envBaseUrl,
    apiKey: _envApiKey,
    deviceId: _envDeviceId,
    buttonStyle: SosButtonStyle.image,
    showVitals: false, // fiel ao mockup; liga em Ajustes
    mockLink: RingLink.connected,
    mockBattery: 85,
    mockCharging: false,
    mockSosFails: false,
    holdSeconds: 3,
  );

  AppSettings copyWith({
    RingSource? ringSource,
    AlertSource? alertSource,
    String? apiBaseUrl,
    String? apiKey,
    String? deviceId,
    SosButtonStyle? buttonStyle,
    bool? showVitals,
    RingLink? mockLink,
    int? mockBattery,
    bool? mockCharging,
    bool? mockSosFails,
    int? holdSeconds,
  }) {
    return AppSettings(
      ringSource: ringSource ?? this.ringSource,
      alertSource: alertSource ?? this.alertSource,
      apiBaseUrl: apiBaseUrl ?? this.apiBaseUrl,
      apiKey: apiKey ?? this.apiKey,
      deviceId: deviceId ?? this.deviceId,
      buttonStyle: buttonStyle ?? this.buttonStyle,
      showVitals: showVitals ?? this.showVitals,
      mockLink: mockLink ?? this.mockLink,
      mockBattery: mockBattery ?? this.mockBattery,
      mockCharging: mockCharging ?? this.mockCharging,
      mockSosFails: mockSosFails ?? this.mockSosFails,
      holdSeconds: holdSeconds ?? this.holdSeconds,
    );
  }

  /// Mudou algo que exige recriar os gateways?
  bool needsGatewayRebuild(AppSettings other) =>
      ringSource != other.ringSource ||
      alertSource != other.alertSource ||
      apiBaseUrl != other.apiBaseUrl ||
      apiKey != other.apiKey ||
      deviceId != other.deviceId;

  // ---------------------------------------------------------------- storage
  static const _p = 'vr.';

  static T _enum<T extends Enum>(List<T> values, String? name, T fallback) =>
      values.firstWhere((v) => v.name == name, orElse: () => fallback);

  static Future<AppSettings> load() async {
    final sp = await SharedPreferences.getInstance();
    const d = defaults;
    return AppSettings(
      ringSource: _enum(RingSource.values, sp.getString('${_p}ringSource'), d.ringSource),
      alertSource: _enum(AlertSource.values, sp.getString('${_p}alertSource'), d.alertSource),
      apiBaseUrl: sp.getString('${_p}apiBaseUrl') ?? d.apiBaseUrl,
      apiKey: sp.getString('${_p}apiKey') ?? d.apiKey,
      deviceId: sp.getString('${_p}deviceId') ?? d.deviceId,
      buttonStyle: _enum(SosButtonStyle.values, sp.getString('${_p}buttonStyle'), d.buttonStyle),
      showVitals: sp.getBool('${_p}showVitals') ?? d.showVitals,
      mockLink: _enum(RingLink.values, sp.getString('${_p}mockLink'), d.mockLink),
      mockBattery: sp.getInt('${_p}mockBattery') ?? d.mockBattery,
      mockCharging: sp.getBool('${_p}mockCharging') ?? d.mockCharging,
      mockSosFails: sp.getBool('${_p}mockSosFails') ?? d.mockSosFails,
      holdSeconds: sp.getInt('${_p}holdSeconds') ?? d.holdSeconds,
    );
  }

  Future<void> save() async {
    final sp = await SharedPreferences.getInstance();
    await Future.wait([
      sp.setString('${_p}ringSource', ringSource.name),
      sp.setString('${_p}alertSource', alertSource.name),
      sp.setString('${_p}apiBaseUrl', apiBaseUrl),
      // Observação LGPD/segurança: em produção a chave vai para armazenamento
      // seguro (Keystore) ou é substituída por token do usuário. Aqui é teste.
      sp.setString('${_p}apiKey', apiKey),
      sp.setString('${_p}deviceId', deviceId),
      sp.setString('${_p}buttonStyle', buttonStyle.name),
      sp.setBool('${_p}showVitals', showVitals),
      sp.setString('${_p}mockLink', mockLink.name),
      sp.setInt('${_p}mockBattery', mockBattery),
      sp.setBool('${_p}mockCharging', mockCharging),
      sp.setBool('${_p}mockSosFails', mockSosFails),
      sp.setInt('${_p}holdSeconds', holdSeconds),
    ]);
  }

  static Future<void> reset() async {
    final sp = await SharedPreferences.getInstance();
    for (final k in sp.getKeys().where((k) => k.startsWith(_p)).toList()) {
      await sp.remove(k);
    }
  }
}
