import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../domain/ports.dart';

/// Simula o envio: ~2 s de rede, devolve contatos fictícios.
class MockAlertGateway implements AlertGateway {
  MockAlertGateway({this.fail = false});
  final bool fail;

  @override
  Future<SosReceipt> sendSos(SosRequest request) async {
    await Future<void>.delayed(const Duration(milliseconds: 1800));
    if (fail) throw const SosException('Falha simulada de rede');
    return SosReceipt(
      alertId: 'mock-${request.triggeredAt.millisecondsSinceEpoch}',
      notified: const ['Maria (filha)', 'Central Vitalis'],
    );
  }

  @override
  Future<void> cancel(String alertId, {required String reason}) async {
    await Future<void>.delayed(const Duration(milliseconds: 600));
  }
}

/// Contrato proposto para o backend (ainda não existe no api.py):
///
/// POST {base}/alerts/sos            body: SosRequest.toJson()
///   201 → {"alert_id": "...", "notified": ["Maria (filha)", ...]}
/// POST {base}/alerts/{id}/cancel    body: {"reason": "user_ok"}
///   200
///
/// O backend decide o canal (WhatsApp, SMS, ligação, central) — o app não sabe.
class HttpAlertGateway implements AlertGateway {
  HttpAlertGateway({required this.baseUrl, this.apiKey = '', http.Client? client})
      : _http = client ?? http.Client();

  final String baseUrl;
  final String apiKey;
  final http.Client _http;

  Uri _u(String path) => Uri.parse('${baseUrl.replaceAll(RegExp(r'/$'), '')}$path');

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (apiKey.isNotEmpty) 'X-API-Key': apiKey,
      };

  @override
  Future<SosReceipt> sendSos(SosRequest request) async {
    try {
      final res = await _http
          .post(_u('/alerts/sos'), headers: _headers, body: jsonEncode(request.toJson()))
          .timeout(const Duration(seconds: 10));
      if (res.statusCode != 200 && res.statusCode != 201) {
        throw SosException('Servidor respondeu ${res.statusCode}');
      }
      final body = jsonDecode(res.body) as Map<String, dynamic>;
      return SosReceipt(
        alertId: '${body['alert_id']}',
        notified: (body['notified'] as List?)?.map((e) => '$e').toList() ?? const [],
      );
    } on SosException {
      rethrow;
    } catch (e) {
      throw SosException('Sem conexão com o servidor ($e)');
    }
  }

  @override
  Future<void> cancel(String alertId, {required String reason}) async {
    await _http
        .post(_u('/alerts/$alertId/cancel'), headers: _headers, body: jsonEncode({'reason': reason}))
        .timeout(const Duration(seconds: 10));
  }
}
