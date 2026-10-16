# Vitalis Ring — app do idoso (Flutter)

Tela única: status do anel, botão **Pedir ajuda** (segurar 3 s) e bateria do anel.
Fase atual: **design funcionando** com dados simulados; integrações já plugáveis.

## Como obter o APK

Todo push em `app/**` dispara `.github/workflows/app-build.yml`:

- **APK**: aba *Releases* do GitHub → `app-v0.1.N` → baixar no celular e instalar.
- **Prévia web** (opcional): GitHub Pages, se *Settings → Pages → Source* = *GitHub Actions*.

Build local (Flutter stable instalado):

```bash
cd app
flutter create . --org br.com.dsaweb --project-name vitalis_ring --platforms android,web
flutter pub get && dart run flutter_launcher_icons
flutter run            # ou: flutter build apk --release
```

## Ajustes do cuidador

Na tela inicial, **segure a marca "VITALIS RING" por 2 s**. Ali dá para:

- alternar o botão entre **imagem do mockup** e **versão desenhada**;
- simular estados do anel (conectado / procurando / desconectado, bateria, carregando);
- simular falha no envio do SOS;
- apontar para a **API do PC** (`GET /readings/latest`) e testar a conexão.

## Arquitetura

```
lib/
  domain/        RingSnapshot + portas RingGateway / AlertGateway (sem Flutter)
  data/ring/     mock · api (FastAPI do repo) · ble (etapa 2, stub)
  data/alert/    mock · http (POST /alerts/sos — contrato proposto)
  core/          AppSettings (persistido) · AppServices (troca gateways) · tema
  features/      home · sos (máquina de estados) · settings
```

Trocar a fonte de dados não toca nas telas: só um novo `RingGateway`/`AlertGateway`.

### Contrato proposto para o backend (a criar no `api.py`)

| Método | Rota | Corpo | Resposta |
|---|---|---|---|
| POST | `/alerts/sos` | `{device_id, triggered_at, source, ring:{battery, heart_rate, spo2, link}}` | `201 {alert_id, notified:[...]}` |
| POST | `/alerts/{id}/cancel` | `{reason}` | `200` |

## Pendências conhecidas (teste → produção)

- `usesCleartextTraffic=true` só para falar com a API local em HTTP. Produção: HTTPS (Tailscale/Cloudflare Tunnel já previstos).
- Chave da API em `SharedPreferences`; produção: Keystore/token por usuário (LGPD — dado de saúde).
- APK assinado com chave de debug; para distribuição, keystore próprio.
- Botão "Ligar para o SAMU" mostra aviso de demonstração (não disca).
