# Projeto: Painel de Sinais Vitais — Anel Colmi R10

## Objetivo
MVP que coleta batimentos (BPM) e SPO2 de um anel inteligente Colmi R10 via
Bluetooth (BLE), envia pra um servidor central, e mostra num dashboard web
(Streamlit) com visão ao vivo + histórico. Uso pretendido: monitoramento que
vai de casa pra um consultório médico (dado de saúde — atenção com
segurança/privacidade, embora ainda não seja produção clínica real).

## Lib usada
[`colmi_r02_client`](https://github.com/tahnok/colmi_r02_client) — client Python
não-oficial, engenharia reversa do protocolo BLE do anel. Instalado via
`pip install colmi-r02-client`. Requer **Python >=3.11,<3.13**.

Métodos confirmados funcionando (testados com hardware real):
- `Client(RING_ADDRESS)` — context manager async, conecta via BLE
- `await ring.get_realtime_heart_rate()` -> `list[int]` (ex: `[89, 89, 87, 87, 87, 87]`)
- `await ring.get_realtime_spo2()` -> `list[int]` (ex: `[97, 97, 98, 98, 96, 96]`)
- `await ring.get_battery()` -> `BatteryInfo(battery_level: int, charging: bool)`
- `await ring.get_heart_rate_log(datetime)` -> objeto com histórico gravado pelo
  anel (pode retornar `NoData` dependendo do anel — ver Issues conhecidas abaixo)
- Outros métodos existentes na lib mas ainda não usados: `get_device_info()`,
  `blink_twice()`, `set_time()`, `get_heart_rate_log_settings()` — dá pra
  aproveitar se precisar no futuro (info de firmware, achar o anel piscando,
  configurar intervalo de log automático).

### Decisão: reconectar a cada ciclo, não manter conexão persistente

O app oficial do anel mantém conexão BLE aberta o tempo todo (por isso
responde instantâneo). Decidimos **não** fazer igual: o `collector.py` abre
conexão só na hora de ler (`async with Client(...)`) e fecha logo em seguida,
a cada ciclo. Motivo: a conexão BLE nesse anel já é instável no Windows
(`BleakDeviceNotFoundError` esporádico — ver "Issues conhecidas"); uma
conexão persistente pode morrer silenciosamente e só se descobre na próxima
tentativa de leitura de qualquer jeito, então reconectar do zero a cada ciclo
já é auto-recuperável e não tem uma "conexão zumbi" escondida. O trade-off é
que cada leitura demora ~1min (tempo de conectar + tempo do stream de HR/SPO2
tempo real), não é instantâneo como no app oficial.
Pra compensar a falta de visibilidade disso, o `collector.py` grava o
resultado de cada tentativa de conexão em `ring_status.json`
(`{"connected": bool, "checked_at": iso, "error": str|null}`), e o dashboard
mostra isso como indicador 🟢/🔴 "Anel conectado/desconectado".

## Arquitetura (decidida com o usuário)

```
[Anel R10] --BLE--> collector.py (roda perto do anel, hoje: mesmo PC do servidor)
                          |  HTTP POST /readings/bulk (X-API-Key header)
                          v
                   api.py (FastAPI, porta 8000)
                          |
                      SQLite (models.py, SQLAlchemy)
                          |
                   dashboard.py (Streamlit, porta 8501)
```

Fase atual: tudo rodando no MESMO PC Windows do usuário (dev/teste local).
Fase futura: collector fica em casa, servidor é remoto (VPS ou máquina no
consultório), conectados via Tailscale ou Cloudflare Tunnel (decidido, ainda
não implementado) — não expor a API direto pra internet.

## Estrutura de arquivos

**Nota:** a estrutura abaixo (`ring-mvp/collector/` + `ring-mvp/server/`) foi o
plano original, mas na prática o projeto ficou **flat na raiz**, com uma
**venv só** (`venv/`) contendo tudo (colmi-r02-client, httpx, fastapi,
uvicorn, sqlalchemy, streamlit, pandas, python-dotenv). Isso é intencional
pra fase atual (tudo no mesmo PC) — só voltar a separar em duas pastas/venvs
quando o collector for de fato mudar de máquina (ver "Fase futura" acima).

```
(raiz do projeto)
  README.md
  requirements.txt      # TODAS as deps (collector + server) numa venv só
  .env / .env.example   # RING_ADDRESS, API_URL, API_KEY, DEVICE_ID, intervalos
                         # (variáveis do servidor tb usam esse mesmo .env: DB_PATH/DATABASE_URL opcionais)
  collector.py           # lê BPM+SPO2+bateria a cada 60s, envia pra API,
                          # buffer local se rede cair (buffer.jsonl).
                          # `python collector.py` roda em loop contínuo;
                          # `python collector.py --once` faz uma leitura só e sai
                          # (usado pelo botão "Coletar agora" do dashboard).
                          # Grava status de conexão em ring_status.json a cada ciclo.
  scan_raw.py             # scan BLE sem filtro (ver "Issues conhecidas" abaixo)
  test_spo2.py             # teste isolado de SPO2 (endereço hardcoded, descartável)
  api.py                   # FastAPI: POST /readings/bulk, GET /readings/latest,
                            # GET /readings/history, auth por X-API-Key (só no POST)
  models.py                 # SQLAlchemy: tabela `readings` (device_id, type, value, timestamp)
                             # types em uso: heart_rate, spo2, heart_rate_log, battery
  dashboard.py               # Streamlit: métricas ao vivo (BPM/SPO2/bateria) + gráficos
                              # de histórico + painel "Controle da coleta" (Iniciar/Parar
                              # loop contínuo, Coletar agora, status 🟢/🔴 do anel).
                              # Controla collector.py via subprocess.Popen + PID em
                              # collector.pid. Auto-refresh via time.sleep + st.rerun.
  collector.pid               # (gerado em runtime) PID do collector.py quando rodando
                               # em loop contínuo via botão do dashboard. Não versionar.
  ring_status.json             # (gerado em runtime) último status de conexão BLE,
                                # lido pelo dashboard. Não versionar.
```

Todos os módulos (`api.py`, `collector.py`, `models.py`) chamam
`load_dotenv()` no topo — o `.env` na raiz é carregado automaticamente,
não precisa mais do truque manual do PowerShell pra carregar variáveis.

## Ambiente do usuário (Windows)
- Windows + PowerShell no VS Code
- **Tem Anaconda instalado**, que polui a PATH — já causou um bug real (uvicorn
  rodando do Anaconda em vez da venv do projeto). Sempre que algo "roda mas com
  comportamento esquisito", suspeitar da PATH/Anaconda primeiro. Preferir
  `.\venv\Scripts\python.exe -m <comando>` em vez de confiar no `<comando>` pelado,
  pra garantir que usa o interpretador certo.
- **Uma venv só** na raiz (`venv/`, Python 3.12, precisa ser <3.13) com todas
  as deps de collector + server juntas (ver "Estrutura de arquivos" acima).
- ~~PowerShell não usa `export $(cat .env | xargs)`~~ — **resolvido**: todos
  os módulos chamam `load_dotenv()` (lib `python-dotenv`) no topo, então o
  `.env` da raiz é carregado automaticamente ao rodar qualquer script/servidor.
  Não precisa mais carregar variável manualmente no PowerShell antes de cada
  comando.
- **Cuidado com processos `uvicorn --reload` órfãos**: já aconteceu de matar
  o processo pai do reloader e o processo *filho* (worker) continuar vivo,
  segurando a porta (aparecia em `netstat -ano` com o PID do pai morto, mas
  na real era um `multiprocessing.spawn` filho com PID diferente — ver
  `Get-CimInstance Win32_Process -Filter 'ProcessId=X' | Select ParentProcessId`
  pra achar o pai/filho certo). Se a porta 8000/8501 estiver "presa" sem
  motivo aparente, procurar processos `python.exe` extras (inclusive do
  Anaconda) antes de mudar de porta.

## Hardware confirmado
- Anel: **Colmi R10**, nome BLE `COLMI R10_F506`, endereço `30:36:44:34:F5:06`
- Firmware: `RT03CR_1.00.02_260319`
- Leituras reais testadas e funcionando: BPM ~87-89, SPO2 ~96-98%
- Conexão BLE no Windows é **intermitente** (`BleakDeviceNotFoundError`
  esporádico, resolve tentando de novo) — backend WinRT do bleak no Windows é
  conhecido por isso. O `collector.py` já devia (ou precisa) ter retry
  automático nisso; verificar se está implementado.

## Issues conhecidas do `colmi_r02_client` (upstream, no GitHub) relevantes

1. **`colmi_r02_util scan` não encontra o R10** — o filtro de nome hardcoded
   na lib (`DEVICE_NAME_PREFIXES` em `cli.py`) só tem `R01`-`R07` e uns nomes
   de marca, não inclui `R08`/`R09`/`R10`+. Por isso criamos `scan_raw.py`,
   que usa `BleakScanner.discover()` direto sem filtro. Isso é uma limitação
   da lib upstream, não do nosso código.
2. **Issue #50 — R02 not taking periodic heart rate logs**: alguns anéis não
   gravam log histórico automático (`get_heart_rate_log` retorna `NoData`
   sempre). Por isso o `collector.py` NÃO depende só disso — o polling de
   tempo real a cada 60s já constrói um histórico próprio no nosso banco,
   independente do anel gravar sozinho ou não.
3. **Issue #36 — SPo2 data**: não existe log histórico de SPO2 na lib, só
   leitura pontual em tempo real. Mesma mitigação: nosso polling periódico é
   quem cria o "histórico" de SPO2, salvando cada leitura pontual no banco.
4. **Issue #27 — Extra packets**: leituras em tempo real vêm acompanhadas de
   pacotes não documentados que a lib ignora com warning no log. Não afeta o
   funcionamento, só polui o log.
5. Sono e "stress" **não são suportados** pela lib atualmente (haveria que
   portar lógica do driver Colmi do Gadgetbridge, que é mais completo nesses
   pontos, mas está em Java/Kotlin).

## Onde paramos

**Bloqueio anterior (`KeyError: 'API_KEY'`) RESOLVIDO em 2026-08-17.** Causas
confirmadas: `.env` não carregado + `uvicorn` sendo executado do Anaconda em
vez da venv do projeto. Correção aplicada:
1. `python-dotenv` adicionado (`load_dotenv()` em `api.py`, `collector.py`,
   `models.py`) — `.env` agora carrega sozinho.
2. `.env` criado na raiz com `API_KEY` gerada via `secrets.token_urlsafe(32)`.
3. `requirements.txt` atualizado com todas as deps de server (fastapi,
   uvicorn, sqlalchemy, streamlit, pandas) — antes só tinha as do collector.
4. Achado e morto um processo `uvicorn --reload` órfão do Anaconda que estava
   segurando a porta 8000 desde a sessão anterior (ver nota sobre processos
   órfãos acima).

**MVP end-to-end validado com hardware real nessa sessão:**
`collector.py` conectou no anel, leu BPM/SPO2/bateria (ex: BPM 76, SPO2 94%,
bateria 100%), enviou via POST `/readings/bulk` (200 OK), dado confirmado em
`GET /readings/latest` e `GET /readings/history`.

**Recursos adicionados nessa sessão (2026-08-17), a pedido do usuário:**
1. Leitura de **bateria** do anel (`get_battery()`) — novo tipo `battery` na
   API/banco, métrica + aba de histórico no dashboard.
2. `collector.py --once` — leitura única (sem loop), usada pelo botão manual.
3. Painel "Controle da coleta" no dashboard: botões **Iniciar/Parar** coleta
   contínua (gerencia `collector.py` via `subprocess.Popen`, PID salvo em
   `collector.pid`) e **Coletar agora** (desabilitado enquanto o loop
   contínuo está rodando, pra não disputar BLE com ele).
4. Indicador de status **🟢 conectado / 🔴 desconectado** do anel, lido de
   `ring_status.json` (gravado pelo `collector.py` a cada tentativa de
   conexão) — ver "Decisão: reconectar a cada ciclo" acima pro racional.

Toda a lógica de start/stop de processo foi testada isoladamente (start →
detecta PID → stop → confirma morto, sem processo órfão) antes de integrar
no dashboard.

**Pendência real, não é bug:** nos últimos testes dessa sessão o anel parou
de responder (nem aparece no `scan_raw.py`) — provavelmente fora de alcance
ou em espera, não problema de código. O indicador 🔴 desconectado capturou
isso corretamente. Confirmar com o anel por perto na próxima sessão.

API (porta 8000) e dashboard (porta 8501) foram deixados rodando em
background ao final dessa sessão. **Visualização em navegador ainda não
confirmada por um humano** — não há como abrir browser a partir daqui, só
confirmei via HTTP que a página responde 200.

## Próximos passos (ordem sugerida)

1. Usuário confirmar visualmente o dashboard em `http://localhost:8501`:
   métricas (BPM/SPO2/bateria), gráficos de histórico (3 abas agora), e
   testar os botões Iniciar/Parar/Coletar agora com o anel por perto.
2. Com o anel por perto, confirmar que o indicador de status vira 🟢.
3. Decidir se a coleta contínua já fica ligada por padrão (ex: iniciar
   sozinha quando o dashboard sobe) ou só quando o usuário aperta "Iniciar".
4. Melhorias de robustez pendentes: retry automático de conexão BLE dentro
   do mesmo ciclo (hoje só reloopa no próximo ciclo de 60s e loga erro),
   considerar rodar `collector.py` como serviço/tarefa agendada do Windows
   em vez de controlado manualmente pelo dashboard.
5. Fase de deploy real: mover collector pra "casa" e servidor pra ambiente
   acessível do consultório, com Tailscale ou Cloudflare Tunnel — ainda não
   iniciado. **Nota importante:** o botão "Iniciar coleta contínua" do
   dashboard só funciona se o dashboard rodar na MESMA máquina que tem
   acesso BLE ao anel — se/quando o collector for pra "casa" e o servidor
   for remoto, esse controle via subprocess local para de fazer sentido e
   precisa virar outra coisa (endpoint na API que o collector consulta, por
   exemplo). Revisar quando essa fase começar.
6. Considerações de LGPD/segurança pra uso clínico real ainda não foram
   aprofundadas (fora do escopo do MVP técnico, mas o usuário foi avisado).
   Nota: hoje só o `POST /readings/bulk` exige `X-API-Key`; os `GET`
   (`/readings/latest`, `/readings/history`) estão abertos pra qualquer um
   com acesso à rede — sinalizado no README como pendência, não implementado.

## Como trabalhar comigo (Claude Code) neste projeto

- O usuário já testou bastante coisa manualmente com sucesso — não repetir
  passos de validação básica (BLE, sensores) sem necessidade, esses já
  funcionam.
- Sempre que sugerir comandos PowerShell, considerar o problema da
  PATH/Anaconda e preferir apontar direto pro interpretador da venv.
- Priorizar diagnosticar erros reais que aparecerem (o usuário vai colar
  tracebacks) antes de sugerir mudanças grandes de arquitetura.
- Este é um MVP, não uma migração de arquitetura — mudanças devem ser
  incrementais sobre o que já existe, a menos que o usuário peça o contrário.

## Área logada e demonstração

A arquitetura atual serve site, login e app no mesmo FastAPI: `/`, `/login`,
`/profissional/login` e `/app`. O novo código fica em `webapp/`; HTMX, CSS,
fontes e logos são locais. Família usa link/código; profissionais usam senha
Argon2 e TOTP. Toda rota de paciente exige vínculo e, para profissionais,
consentimento vigente. Acesso profissional ao detalhe gera `access_log`.

Os GETs `/readings/latest` e `/readings/history` também exigem `X-API-Key`.
Quando `PUBLIC_EXPOSURE=1`, OpenAPI fica indisponível. Somente a porta 8000
pode entrar em túnel; Streamlit deve usar `--server.address 127.0.0.1`.

Dispositivos `demo-*` recebem apenas leituras sintéticas e devem conservar o
rótulo “dados fictícios”. Regras/limiares não são clinicamente validados.
Nunca registrar valor de saúde, token, mensagem ou destino de notificação.
SMTP e WhatsApp permanecem desligados salvo configuração + opt-in verificado.

O controle de processo BLE vive em `collector_control.py` e é compartilhado
pelo Streamlit e web. Nunca iniciar um segundo coletor em paralelo. A sequência,
evidências e portões manuais estão em `docs/PLANO_IMPLEMENTACAO.md`.
