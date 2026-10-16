import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../core/config/app_settings.dart';
import '../../core/services_scope.dart';
import '../../core/theme/vr_colors.dart';
import '../../domain/ring_snapshot.dart';
import '../home/widgets/status_widgets.dart';

/// Área do cuidador/desenvolvedor: fontes de dados, cenários de simulação e aparência.
/// Acesso: segurar a marca "VITALIS RING" por 2 s na tela inicial.
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  late final TextEditingController _url;
  late final TextEditingController _key;
  late final TextEditingController _device;
  bool _init = false;
  String? _testResult;
  bool _testing = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_init) return;
    _init = true;
    final s = ServicesScope.of(context).settings;
    _url = TextEditingController(text: s.apiBaseUrl);
    _key = TextEditingController(text: s.apiKey);
    _device = TextEditingController(text: s.deviceId);
  }

  @override
  void dispose() {
    _url.dispose();
    _key.dispose();
    _device.dispose();
    super.dispose();
  }

  Future<void> _apply(AppSettings Function(AppSettings) change) async {
    final services = ServicesScope.of(context);
    await services.update(change(services.settings));
  }

  Future<void> _saveApi() async {
    FocusScope.of(context).unfocus();
    await _apply((s) => s.copyWith(
          apiBaseUrl: _url.text.trim(),
          apiKey: _key.text.trim(),
          deviceId: _device.text.trim().isEmpty ? 'ring-01' : _device.text.trim(),
        ));
    if (mounted) _snack('Conexão salva');
  }

  Future<void> _testApi() async {
    setState(() {
      _testing = true;
      _testResult = null;
    });
    final base = _url.text.trim().replaceAll(RegExp(r'/$'), '');
    String result;
    try {
      final res = await http.get(Uri.parse('$base/health')).timeout(const Duration(seconds: 6));
      result = res.statusCode == 200 ? 'OK — API respondeu: ${res.body}' : 'HTTP ${res.statusCode}';
    } catch (e) {
      result = 'Falhou: $e';
    }
    if (!mounted) return;
    setState(() {
      _testing = false;
      _testResult = result;
    });
  }

  void _snack(String msg) =>
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));

  @override
  Widget build(BuildContext context) {
    final services = ServicesScope.of(context);
    final s = services.settings;
    final snap = services.ring.current;

    return Scaffold(
      backgroundColor: VrColors.surface,
      appBar: AppBar(title: const Text('Ajustes do cuidador')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(20, 8, 20, 40),
        children: [
          const _Section('Aparência'),
          const _Label('Botão de ajuda'),
          _Segments<SosButtonStyle>(
            value: s.buttonStyle,
            items: const {SosButtonStyle.image: 'Imagem (mockup)', SosButtonStyle.vector: 'Desenhado'},
            onChanged: (v) => _apply((x) => x.copyWith(buttonStyle: v)),
          ),
          const SizedBox(height: 14),
          const _Label('Tempo segurando para chamar'),
          _Segments<int>(
            value: s.holdSeconds,
            items: const {2: '2 s', 3: '3 s', 5: '5 s'},
            onChanged: (v) => _apply((x) => x.copyWith(holdSeconds: v)),
          ),
          if (s.buttonStyle == SosButtonStyle.image && s.holdSeconds != 3)
            const _Note('A imagem diz "3 segundos". Use o botão desenhado para o texto acompanhar.'),
          SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text('Mostrar coração e oxigênio na tela inicial'),
            value: s.showVitals,
            onChanged: (v) => _apply((x) => x.copyWith(showVitals: v)),
          ),

          const _Section('Dados do anel'),
          _Segments<RingSource>(
            value: s.ringSource,
            items: const {
              RingSource.mock: 'Simulação',
              RingSource.api: 'API do PC',
              RingSource.ble: 'BLE direto',
            },
            onChanged: (v) => _apply((x) => x.copyWith(ringSource: v)),
          ),
          _Note(switch (s.ringSource) {
            RingSource.mock => 'Valores simulados — use os controles abaixo para ver cada estado.',
            RingSource.api => 'Lê GET /readings/latest do servidor configurado abaixo, a cada 15 s.',
            RingSource.ble => 'Etapa 2: conexão Bluetooth direta com o Colmi R10 (ainda não ativa).',
          }),
          _Diag(snapshot: snap),

          if (s.ringSource == RingSource.mock) ...[
            const _Section('Simulação'),
            const _Label('Estado do anel'),
            _Segments<RingLink>(
              value: s.mockLink,
              items: const {
                RingLink.connected: 'Conectado',
                RingLink.searching: 'Procurando',
                RingLink.disconnected: 'Desconectado',
              },
              onChanged: (v) => _apply((x) => x.copyWith(mockLink: v)),
            ),
            const SizedBox(height: 14),
            _Label('Bateria: ${s.mockBattery}%'),
            Slider(
              value: s.mockBattery.toDouble(),
              min: 0,
              max: 100,
              divisions: 20,
              label: '${s.mockBattery}%',
              onChanged: (v) => _apply((x) => x.copyWith(mockBattery: v.round())),
            ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Anel carregando'),
              value: s.mockCharging,
              onChanged: (v) => _apply((x) => x.copyWith(mockCharging: v)),
            ),
          ],

          const _Section('Envio do pedido de ajuda'),
          _Segments<AlertSource>(
            value: s.alertSource,
            items: const {AlertSource.mock: 'Simulado', AlertSource.http: 'Servidor'},
            onChanged: (v) => _apply((x) => x.copyWith(alertSource: v)),
          ),
          _Note(s.alertSource == AlertSource.mock
              ? 'Nada é enviado. Simula ~2 s de envio e contatos fictícios.'
              : 'POST /alerts/sos no servidor abaixo (endpoint ainda a criar no api.py).'),
          if (s.alertSource == AlertSource.mock)
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: const Text('Simular falha de envio'),
              subtitle: const Text('Para ver a tela de erro e a nova tentativa'),
              value: s.mockSosFails,
              onChanged: (v) => _apply((x) => x.copyWith(mockSosFails: v)),
            ),

          const _Section('Servidor (API)'),
          TextField(
            controller: _url,
            keyboardType: TextInputType.url,
            decoration: const InputDecoration(labelText: 'Endereço', hintText: 'http://192.168.0.10:8000'),
          ),
          const SizedBox(height: 12),
          TextField(controller: _device, decoration: const InputDecoration(labelText: 'ID do anel (device_id)')),
          const SizedBox(height: 12),
          TextField(
            controller: _key,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Chave da API (X-API-Key)'),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  onPressed: _testing ? null : _testApi,
                  child: Text(_testing ? 'Testando…' : 'Testar conexão'),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(child: FilledButton(onPressed: _saveApi, child: const Text('Salvar'))),
            ],
          ),
          if (_testResult != null) _Note(_testResult!),
          const _Note(
            'No celular, use o IP do PC na rede Wi-Fi (não "localhost") e suba a API com '
            '--host 0.0.0.0. Tráfego HTTP sem TLS está liberado só nesta versão de teste.',
          ),

          const SizedBox(height: 28),
          TextButton(
            onPressed: () async {
              await services.resetAll();
              if (!context.mounted) return;
              final d = services.settings;
              _url.text = d.apiBaseUrl;
              _key.text = d.apiKey;
              _device.text = d.deviceId;
              _snack('Ajustes restaurados');
            },
            child: const Text('Restaurar padrão', style: TextStyle(color: VrColors.inkSoft)),
          ),
          const Center(
            child: Text('Vitalis Ring · app do idoso · v0.1 (teste)',
                style: TextStyle(fontSize: 14, color: VrColors.inkSoft)),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 26, bottom: 10),
        child: Text(
          text.toUpperCase(),
          style: const TextStyle(fontSize: 15, letterSpacing: 2, fontWeight: FontWeight.w700, color: VrColors.gold),
        ),
      );
}

class _Label extends StatelessWidget {
  const _Label(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(text, style: const TextStyle(fontSize: 17, color: VrColors.ink)),
      );
}

class _Note extends StatelessWidget {
  const _Note(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Text(text, style: const TextStyle(fontSize: 15, height: 1.4, color: VrColors.inkSoft)),
      );
}

class _Segments<T> extends StatelessWidget {
  const _Segments({required this.value, required this.items, required this.onChanged});
  final T value;
  final Map<T, String> items;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: SegmentedButton<T>(
        showSelectedIcon: false,
        segments: [
          for (final e in items.entries)
            ButtonSegment<T>(value: e.key, label: Text(e.value, textAlign: TextAlign.center)),
        ],
        selected: {value},
        onSelectionChanged: (sel) => onChanged(sel.first),
        style: ButtonStyle(
          visualDensity: VisualDensity.standard,
          padding: const WidgetStatePropertyAll(EdgeInsets.symmetric(vertical: 12, horizontal: 6)),
          textStyle: const WidgetStatePropertyAll(TextStyle(fontFamily: 'Atkinson', fontSize: 15)),
          backgroundColor: WidgetStateProperty.resolveWith(
            (st) => st.contains(WidgetState.selected) ? VrColors.gold : Colors.transparent,
          ),
          foregroundColor: WidgetStateProperty.resolveWith(
            (st) => st.contains(WidgetState.selected) ? VrColors.surface : VrColors.ink,
          ),
          side: const WidgetStatePropertyAll(BorderSide(color: VrColors.line)),
        ),
      ),
    );
  }
}

class _Diag extends StatelessWidget {
  const _Diag({required this.snapshot});
  final RingSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final s = snapshot;
    final parts = [
      'link: ${s.link.name}',
      if (s.batteryPercent != null) 'bateria: ${s.batteryPercent}%',
      if (s.heartRate != null) 'bpm: ${s.heartRate}',
      if (s.spo2 != null) 'spo2: ${s.spo2}%',
      if (s.updatedAt != null) 'atualizado ${timeAgo(s.updatedAt)}',
      if (s.detail != null) s.detail!,
    ];
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: VrColors.card,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: VrColors.line),
      ),
      child: Text(parts.join(' · '),
          style: const TextStyle(fontFamily: 'monospace', fontSize: 13, color: VrColors.inkSoft)),
    );
  }
}
