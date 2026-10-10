# Plano de implementação — Área logada Vitalis Ring

## 1. Objetivo

Integrar o site público, a área logada e o backend do Vitalis Ring numa única
aplicação web demonstrável, mantendo o MVP atual funcionando. O sistema deverá
atender quatro papéis:

- **Cliente/família:** consulta o estado e as informações do próprio paciente.
- **Técnico Vitalis:** cadastra o cliente, cria o paciente, registra o anel e
  acompanha a ativação inicial.
- **Médico:** acompanha somente pacientes vinculados e com consentimento vigente.
- **Administrador/owner:** gerencia técnicos, demonstração e configurações.

Todo o sistema web será testado primeiro com dados sintéticos. O teste com o
anel físico será uma fase posterior e terá participação manual do usuário, que
entrará como técnico da Vitalis e fará o cadastro de um cliente novo pela própria
interface.

## 2. Estado atual confirmado

- O coletor lê BPM, SpO₂ e bateria do Colmi R10 via BLE.
- A API FastAPI recebe leituras e oferece consultas de última leitura e histórico.
- O SQLite contém a tabela `readings`.
- O dashboard Streamlit lê o banco diretamente e controla o coletor local.
- O site público está em `site/` e o build estático em `site/dist/`.
- Os GETs de leituras ainda não exigem autenticação.
- A venv da raiz está quebrada e aponta para um Python 3.12 removido.
- O Python global atual é 3.14 e não é compatível com `colmi-r02-client`.
- Movimento, queda, sono, HRV e qualidade do sinal não fazem parte dos dados
  reais coletados atualmente.

## 3. Regras de execução

### 3.1 Legenda

- `[ ]` não iniciado.
- `[~]` em execução.
- `[x]` concluído e comprovado.
- `[!]` bloqueado, com motivo registrado.

### 3.2 Ciclo obrigatório de cada fase

1. Marcar a fase como em execução.
2. Fazer a menor alteração capaz de cumprir o objetivo.
3. Rodar os testes da própria fase e a regressão das fases anteriores.
4. Fazer inspeção no navegador quando existir mudança visual ou de fluxo.
5. Registrar evidências na seção “Diário de execução”.
6. Fazer um commit para cada frente concluída e testada, mesmo que outras
   frentes da mesma fase continuem pendentes.
7. Só então marcar a fase como concluída.

Não se avança com teste obrigatório falhando. O trabalho pode continuar sem
aprovação manual entre fases, exceto nos marcos explicitamente identificados
como **PORTÃO MANUAL**.

### 3.3 Política de branch e histórico

- Branch única de trabalho: `feature/area-logada`.
- A branch comportará todas as fases e seus diversos commits.
- Cada tarefa ou frente funcional concluída e testada gera um commit próprio.
- Padrão da mensagem: `fase-N(escopo): descrição curta`.
- O agente informa após cada commit: hash curto, mensagem e testes executados.
- Commits não misturam fases nem mudanças sem relação direta.
- Não haverá commit direto em `master`, reescrita de histórico ou `git push`.

### 3.4 Separação obrigatória dos dados

| Ambiente | Dispositivo | Origem | Uso |
|---|---|---|---|
| Testes | `test-*` | fixtures temporárias | testes automatizados |
| Demonstração | `demo-*` | gerador sintético | apresentação e testes web |
| Real | `ring-01` ou serial cadastrado | coletor BLE | teste físico autorizado |

O banco de testes nunca poderá apontar para o banco real. Toda tela que exibir
paciente sintético mostrará “Dados fictícios — demonstração”.

## 4. Arquitetura prevista

```text
Navegador
   │
   ▼
FastAPI ── site público (/)
   ├────── autenticação (/login)
   ├────── área logada (/app)
   ├────── área técnica (/app/tecnico)
   ├────── área médica (/app/medico)
   └────── API protegida (/readings/*)
                    │
                    ▼
              SQLite/PostgreSQL
                    ▲
                    │
       coletor sintético ou collector.py
                    ▲
                    │ BLE, somente na fase física
                 Colmi R10
```

O navegador não será descrito como responsável pelo pareamento BLE. O técnico
registra o dispositivo e inicia sua ativação; um coletor próximo ao anel realiza
a conexão física e envia a primeira leitura.

Estrutura de código desejada:

```text
webapp/
  routes/
  templates/
  security/
  alerts/
  demo/
  services/
  models_app.py
static/
scripts/
tests/
docs/
```

## 5. Fases

### Fase 0 — Preparação segura do ambiente

Status: `[x]`

Objetivo: criar um ambiente reproduzível sem alterar dados existentes.

Tarefas:

- [x] Criar a branch local `feature/area-logada` sem fazer push.
- [x] Instalar ou localizar Python 3.12.
- [x] Criar uma venv fora da pasta sincronizada pelo OneDrive.
- [x] Definir `VITALIS_PYTHON` ou mecanismo equivalente documentado.
- [x] Instalar as dependências atuais e verificar importações.
- [x] Criar configuração de testes com banco temporário.
- [x] Registrar versões de Python e dependências.
- [x] Verificar que nenhum segredo do `.env` é exibido ou versionado.
- [x] Executar testes de fumaça dos módulos existentes.

Aceite:

- O interpretador usado é Python 3.11 ou 3.12.
- API, modelos e dashboard importam sem erro.
- O banco real não é modificado pelos testes.
- O build do site funciona com o novo ambiente.

### Fase 1 — Proteção da API antes de exposição pública

Status: `[x]`

Objetivo: impedir que dados de saúde sejam consultados anonimamente.

Tarefas:

- [x] Exigir API key nos GETs existentes enquanto ainda não houver sessão web.
- [x] Manter `POST /readings/bulk` compatível com o coletor.
- [x] Desativar `/docs`, `/redoc` e `/openapi.json` com
  `PUBLIC_EXPOSURE=1`.
- [x] Adicionar cabeçalhos de segurança.
- [x] Fazer a aplicação recusar exposição pública com segredos fracos ou ausentes.
- [x] Documentar que somente a porta 8000 será exposta.
- [x] Manter o Streamlit em `127.0.0.1:8501`.

Testes obrigatórios:

- Sem credencial, consultas retornam 401.
- Com API key correta, consultas continuam funcionando.
- API key inválida retorna 401 sem revelar detalhes.
- Com exposição pública, OpenAPI retorna 404.
- O contrato de `POST /readings/bulk` não muda.

### Fase 2 — Fundação da aplicação web integrada

Status: `[x]`

Objetivo: servir site, login e área logada pelo mesmo FastAPI.

Tarefas:

- [x] Criar `webapp/` e seus módulos fundamentais.
- [x] Montar recursos estáticos locais, sem CDN.
- [x] Montar `site/dist` na raiz somente depois de registrar todas as rotas.
- [x] Criar `/login`, `/app` e `/logout` inicialmente sem dados reais.
- [x] Reaproveitar os tokens visuais existentes como fonte canônica.
- [x] Criar páginas provisórias para todos os links ainda inexistentes do site.
- [x] Garantir navegação por teclado, foco visível e alvos mínimos de 48 px.
- [x] Adicionar aviso regulatório fixo às telas logadas.

Testes obrigatórios:

- Nenhum link do menu ou rodapé retorna 404.
- O botão “Entrar” abre `/login` na mesma origem.
- Recursos CSS, JS, fontes e imagens são locais.
- Uma rota de aplicação não é capturada pela montagem do site estático.
- Inspeção visual mobile e desktop aprovada.

### Fase 3 — Modelo de identidade, autorização e auditoria

Status: `[x]`

Objetivo: estabelecer papéis, vínculos e consentimentos antes dos dashboards.

Tabelas aditivas previstas:

- `users` e papéis;
- `login_tokens`;
- `sessions`;
- `patients`;
- `devices`;
- `care_links`;
- `consents`;
- `access_log`;
- `refresh_requests`;
- `alerts`, inicialmente apenas para demonstração.

Tarefas:

- [x] Definir os papéis `owner`, `technician`, `customer`, `doctor` e
  `institution`.
- [x] Implementar sessões opacas com somente hash armazenado.
- [x] Implementar expiração deslizante e limite absoluto.
- [x] Implementar CSRF e validação exata de origem.
- [x] Centralizar autorização por paciente.
- [x] Exigir vínculo ativo e consentimento vigente para acesso profissional.
- [x] Registrar acessos profissionais sem valores de saúde.
- [x] Criar matriz documentada de permissões.

Testes obrigatórios:

- IDOR por URL, formulário e chamada HTMX é negado.
- Cliente não acessa outro paciente.
- Técnico acessa somente o necessário para implantação e suporte autorizado.
- Médico sem vínculo ou com consentimento vencido recebe 403.
- Acesso autorizado do profissional produz registro de auditoria.
- Logs não contêm valores de BPM, SpO₂ ou tokens.

### Fase 4 — Login do cliente e consentimento

Status: `[x]`

Objetivo: permitir acesso B2C sem senha.

Tarefas:

- [x] Solicitação de link mágico por e-mail com resposta sempre neutra.
- [x] Código alternativo de seis dígitos utilizável em outro aparelho.
- [x] Token forte, uso único, validade de 15 minutos e somente hash no banco.
- [x] Rate limit por IP e identificador normalizado.
- [x] Mailer abstrato com implementações `console` e SMTP.
- [x] Mostrar acesso de demonstração na tela somente para contas sintéticas.
- [x] Impedir `DEMO_MODE=1` em produção.
- [x] Exibir consentimento no primeiro acesso.
- [x] Implementar logout e revogação da sessão.

Testes obrigatórios:

- Usuário existente e inexistente recebem a mesma resposta pública.
- Token expirado, reutilizado ou adulterado é rejeitado.
- Código incorreto respeita o limite de tentativas.
- Logout invalida a sessão no servidor.
- Dados reais nunca fazem o link mágico aparecer na tela.

### Fase 5 — Área do técnico e cadastro de novo cliente

Status: `[x]`

Objetivo: implementar o fluxo que será usado posteriormente com o anel físico.

Fluxo esperado:

1. Técnico entra em `/app/tecnico`.
2. Cadastra o responsável/cliente.
3. Cadastra a pessoa monitorada.
4. Registra um anel por identificador público/serial.
5. Associa o dispositivo ao paciente.
6. Gera o convite de acesso do cliente.
7. Inicia a ativação e acompanha o estado “aguardando primeira leitura”.
8. O coletor sintético ou físico envia uma leitura.
9. A tela muda para “dispositivo ativo” sem recarregamento destrutivo.

Tarefas:

- [x] Criar acesso isolado do técnico sintético; o acesso real provisionado pelo
  owner receberá autenticação forte na Fase 7, antes do portão físico.
- [x] Criar assistente de cadastro em etapas.
- [x] Validar duplicidade de e-mail, paciente e dispositivo.
- [x] Implementar associação e desassociação auditada de dispositivo.
- [x] Implementar convite ao cliente sem expor credenciais.
- [x] Criar coletor sintético para concluir a ativação em testes.
- [x] Exibir claramente se a origem é sintética ou física.
- [x] Não permitir que o técnico consulte históricos fora de uma finalidade de
  suporte autorizada e auditada.

Testes obrigatórios:

- Fluxo ponta a ponta no navegador com novo cliente e `demo-*`.
- Dispositivo duplicado não pode ser associado a dois pacientes ativos.
- Falha durante o assistente não cria cadastro parcial inconsistente.
- Um técnico comum não cria owner nem eleva o próprio papel.
- A primeira leitura sintética ativa o dispositivo correto.

### Fase 6 — Área da família

Status: `[x]`

Objetivo: entregar uma experiência simples e calma para o cliente.

Tarefas:

- [x] Cartão principal do dia com a escala de cinco níveis.
- [x] Horário relativo da última leitura.
- [x] Estado do dispositivo e da última comunicação do coletor.
- [x] Linha do tempo de avisos demonstrativos.
- [x] “Atualizar agora” com acompanhamento do pedido.
- [x] Detalhes numéricos somente em uma seção explícita.
- [x] Gestão de pessoas autorizadas e consentimentos.
- [x] Mobile-first, texto base de 18 px e modo de movimento reduzido.

Testes obrigatórios:

- Fluxo familiar completo em viewport de celular.
- Usuário só vê pacientes sob sua responsabilidade.
- Dado fictício permanece rotulado em todas as parciais HTMX.
- Datas UTC são exibidas em `America/Sao_Paulo`.
- Ausência de dados e dispositivo offline têm estados claros e não alarmistas.

### Fase 7 — Login forte e console médico

Status: `[x]`

Objetivo: permitir acesso profissional com autenticação reforçada.

Tarefas:

- [x] Senha com Argon2.
- [x] MFA TOTP obrigatório.
- [x] Configuração inicial por QR SVG local.
- [x] Códigos de recuperação de uso único armazenados como hash.
- [x] Lista de pacientes vinculados por prioridade demonstrativa.
- [x] Detalhe do paciente com tendência, leituras e auditoria.
- [x] Fluxo de “Atualizar agora” por solicitação assíncrona.

Testes obrigatórios:

- Senha ou TOTP incorretos não criam sessão.
- Código de recuperação não pode ser reutilizado.
- Médico não vinculado não localiza nem acessa paciente.
- Consentimento revogado interrompe o acesso imediatamente.
- Visualização autorizada gera `access_log`.

### Fase 8 — Atualização sob demanda e coletor compartilhado

Status: `[x]`

Objetivo: integrar solicitações web ao coletor sem criar concorrência BLE.

Tarefas:

- [x] Extrair o controle de PID para módulo compartilhado sem quebrar Streamlit.
- [x] Impedir duas coletas BLE simultâneas.
- [x] Registrar `refresh_request` com estado e expiração.
- [x] Fazer polling HTMX sem incluir dado de saúde na URL.
- [x] Responder em poucos segundos no modo sintético.
- [x] Preparar timeout de 120 segundos para o anel físico.
- [x] Separar modo local de uma futura arquitetura com coletor remoto.

Testes obrigatórios:

- Duplo clique cria no máximo uma solicitação ativa.
- Paciente sintético recebe nova leitura no dispositivo correto.
- Timeout mostra “sem resposta do anel”, sem gerar alerta clínico.
- Coletor já ativo não recebe um segundo processo concorrente.
- Dashboard Streamlit continua iniciando e controlando o coletor.

### Fase 9 — Simulador e regras demonstrativas

Status: `[x]`

Objetivo: demonstrar a escala e as mensagens sem afirmar validação clínica.

Tarefas:

- [x] Implementar regras como funções puras e configuráveis.
- [x] Incluir no simulador estado, duração, movimento e qualidade sintética.
- [x] Manter limiares em arquivo único com aviso de validação pendente.
- [x] Mostrar a regra acionada em linguagem simples.
- [x] Gerar prévia exata de WhatsApp e e-mail sem números de saúde.
- [x] Restringir regras automáticas a dados sintéticos.
- [x] Não apresentar movimento, sono, queda, HRV ou qualidade como leitura real.

Testes obrigatórios:

- Testes de tabela cobrem limites e durações.
- Leituras sem qualidade suficiente não geram conclusão indevida.
- Toda mensagem externa está sem números de saúde.
- `ring-01` não dispara envio automático.
- A UI exibe “simulação” e “limiares ainda não validados”.

### Fase 10 — Canais de notificação

Status: `[x]`

Objetivo: preparar canais atrás de uma abstração segura.

Tarefas:

- [x] Criar interface `Notifier`.
- [x] Implementar console seguro e pré-visualização.
- [x] Implementar SMTP opcional.
- [x] Implementar adaptador opcional para WhatsApp Cloud API.
- [x] Exigir opt-in específico e canal verificado.
- [x] Manter envio real desligado por padrão.
- [x] Implementar idempotência e histórico sem conteúdo sensível.

Testes obrigatórios:

- Mocks comprovam seleção correta do canal.
- Sem configuração, nenhum envio externo ocorre.
- Sem consentimento, nenhum canal é acionado.
- Retentativas não duplicam uma mesma notificação.
- Logs registram resultado técnico, não conteúdo de saúde.

### Fase 11 — Endurecimento e testes completos da web

Status: `[x]`

Objetivo: validar todo o sistema antes de usar hardware ou ngrok.

Cobertura obrigatória:

- [x] Testes unitários de regras, sessões, CSRF e permissões.
- [x] Testes de integração das rotas e do banco.
- [x] Testes ponta a ponta no navegador para família, técnico e médico.
- [x] Testes de IDOR, rate limit e expiração.
- [x] Teste de ausência de segredos e saúde nos logs.
- [x] Auditoria do site sem links quebrados.
- [x] Inspeção visual em celular e desktop.
- [x] Regressão da API, coletor e dashboard Streamlit.
- [x] Documentação de backup e recuperação do banco.

Aceite:

- Toda a suíte automatizada está verde.
- Todos os fluxos principais foram executados num navegador real.
- Não há dependência CDN nem requisição inesperada de terceiros.
- A demonstração sintética funciona sem o anel físico.

### Fase 12 — PORTÃO MANUAL: ativação com o anel físico

Status: `[~]`

Esta fase só começa quando o usuário estiver com o anel por perto e autorizar o
teste. Nenhuma etapa anterior depende dela.

Roteiro manual:

1. Iniciar API e coletor no ambiente Python 3.12 validado.
2. O usuário abre o login e entra como técnico da Vitalis.
3. Cadastra um cliente novo pela interface.
4. Cadastra a pessoa monitorada e aceita os consentimentos aplicáveis.
5. Registra e associa o Colmi R10 ao paciente.
6. Coloca o anel em condição de conexão e inicia a ativação.
7. O coletor local encontra o endereço BLE configurado.
8. Uma leitura real de BPM, SpO₂ ou bateria chega à API.
9. A interface mostra a primeira comunicação e o horário correto.
10. Cliente entra pelo convite e vê seus próprios dados.

Evidências necessárias:

- [ ] Log técnico de sucesso sem valores de saúde nem segredo.
- [ ] Registro da leitura no banco para o dispositivo correto.
- [ ] Tela técnica muda de “aguardando” para “ativo”.
- [ ] Cliente correto acessa; outro cliente recebe 403.
- [ ] Repetição da coleta não cria processo concorrente.
- [ ] Falha de BLE produz mensagem recuperável e permite nova tentativa.

Se o anel estiver indisponível, a fase permanece pendente; isso não invalida os
testes web nem autoriza substituir a evidência física por dados sintéticos.

### Fase 13 — Demonstração pública pela Cloudflare

Status: `[ ]`

Objetivo: expor somente a aplicação segura pela Cloudflare, mantendo o coletor
BLE e o banco fora da borda pública.

Tarefas:

- [ ] Confirmar que as fases 1 a 11 estão concluídas.
- [ ] Gerar site com `SITE_URL` e `APP_URL` públicos.
- [ ] Semear apenas dados fictícios identificados.
- [ ] Subir Uvicorn em `127.0.0.1:8000` com proxy configurado.
- [ ] Expor somente a porta 8000 pelo Cloudflare Tunnel.
- [ ] Manter Streamlit e banco fora do túnel.
- [ ] Executar novamente os testes de exposição pela URL pública.
- [ ] Documentar como iniciar e encerrar túnel, servidor e sessões de
  demonstração.

Testes obrigatórios:

- URL pública usa HTTPS.
- Login, cookies, CSRF e redirecionamentos funcionam atrás do proxy.
- `/docs`, `/redoc` e `/openapi.json` retornam 404.
- Consultas anônimas de leituras retornam 401.
- Nenhum link do site escapa da origem esperada.
- Somente pacientes fictícios aparecem na apresentação padrão.

## 6. Matriz resumida de testes

| Camada | Ferramenta prevista | O que comprova |
|---|---|---|
| Unitária | pytest | regras, tokens, permissões e serviços puros |
| Integração | pytest + cliente ASGI | rotas, banco, sessões, CSRF e autorização |
| Navegador | Playwright ou automação equivalente | fluxos reais, HTMX, cookies e responsividade |
| Visual | capturas mobile/desktop | layout, acessibilidade e estados vazios |
| Regressão | testes de contrato | API, coletor e Streamlit preservados |
| Hardware | roteiro manual assistido | BLE e primeira leitura do Colmi R10 |
| Exposição | cliente HTTP + navegador | comportamento real através do Cloudflare Tunnel |

Mocks comprovam a lógica de integração, mas não comprovam entrega real por SMTP,
WhatsApp nem leitura BLE. Essas diferenças devem aparecer no relatório final.

## 7. Decisões que permanecem fora do escopo imediato

- Validação clínica dos limiares.
- Classificação regulatória definitiva.
- Detecção real de queda, movimento, sono ou HRV.
- Operação contínua em produção.
- Migração definitiva para PostgreSQL.
- Aplicativo móvel nativo.
- Arquitetura final do coletor remoto instalado na casa do cliente.

Esses itens podem ganhar fases próprias depois da demonstração, mas não podem
ser simulados silenciosamente como se já estivessem disponíveis.

## 8. Diário de execução

Cada entrada deve usar este formato:

```text
Data/hora:
Fase:
Alterações:
Comandos executados:
Resultados:
Evidências:
Pendências/riscos:
Próximo passo:
```

As entradas abaixo registram somente fases e frentes comprovadas por testes.

### 2026-09-21 — Fase 0 concluída

```text
Data/hora: 2026-09-21
Fase: 0 — Preparação segura do ambiente
Alterações: branch de trabalho; política de commits; Python 3.12.7 em venv
externa; documentação do ambiente; pytest isolado; build e auditor compatíveis
com Windows/OneDrive.
Comandos executados: pip install -r requirements.txt; pip check; compileall;
dois builds consecutivos; audit_site.py; pytest.
Resultados: pip check sem dependências quebradas; imports corretos; build
idempotente; auditor com 0 erros e 4 avisos de conteúdo pendente; 2 testes
passaram usando SQLite temporário, removido corretamente no encerramento.
Evidências: commits 32204a6 e e0e4dd2; saída dos comandos nesta execução; banco
temporário com prefixo vitalis-pytest-.
Pendências/riscos: api.py usa o evento startup depreciado do FastAPI; será
tratado quando a aplicação for estruturada, sem afetar os testes atuais.
Próximo passo: Fase 1 — proteção da API antes de exposição pública.
```

### 2026-09-21 — Fase 1 concluída

```text
Data/hora: 2026-09-21
Fase: 1 — Proteção da API antes de exposição pública
Alterações: autenticação por X-API-Key nos GETs; contrato do POST preservado;
OpenAPI desativado no modo público; validação de chave; cabeçalhos defensivos;
no-store em leituras; ciclo de vida FastAPI atualizado; runbook de portas.
Comandos executados: pytest; compileall; git diff --check.
Resultados: 11 testes passaram; GET anônimo retorna 401; API key válida retorna
200; POST legado retorna 200; documentação retorna 404 em PUBLIC_EXPOSURE=1;
cabeçalhos e rejeição de chave fraca confirmados.
Evidências: commits 18a3533 e e65fd5b.
Pendências/riscos: avisos de compatibilidade do TestClient e uso legado de
datetime.utcnow; não afetam o aceite e serão tratados nas fases de fundação.
Próximo passo: Fase 2 — fundação da aplicação web integrada.
```

### 2026-09-21 — Fase 2 concluída

```text
Data/hora: 2026-09-21
Fase: 2 — Fundação da aplicação web integrada
Alterações: site, login e área logada servidos pelo mesmo FastAPI; montagem das
rotas antes do site estático; templates Jinja; tokens visuais compartilhados;
HTMX 2.0.9 local; 13 páginas provisórias noindex; 404 personalizado.
Comandos executados: dois builds; audit_site.py; pytest; compileall; node
--check; inspeção no Chrome em desktop e viewport 390x844.
Resultados: 28 testes passaram; auditor com 0 erros e 30 avisos conhecidos de
conteúdo pendente; nenhum link retorna 404; nenhum recurso externo na área
logada; corpo 18 px; controles de 48 px ou mais; sem overflow horizontal;
nenhum erro ou aviso no console do navegador.
Evidências: commits 5780c11 e 8a0350c; SHA-256 do HTMX registrado em
static/vendor/README.md.
Pendências/riscos: login ainda é uma tela estrutural sem envio de dados, por
decisão da fase; conteúdo jurídico e número de WhatsApp continuam pendentes.
Próximo passo: Fase 3 — identidade, autorização e auditoria.
```

### 2026-09-21 — Fase 3 concluída

```text
Data/hora: 2026-09-21
Fase: 3 — Modelo de identidade, autorização e auditoria
Alterações: 10 tabelas aditivas; dispositivos separados de readings; foreign
keys SQLite; sessões opacas com hash; expiração deslizante/absoluta; CSRF por
token e origem; autorização central; consentimento; auditoria sem sinais vitais.
Comandos executados: pytest completo; compile/imports nas regressões anteriores;
git diff --check.
Resultados: 41 testes passaram; tabela readings preservada; unicidade e FKs
comprovadas; IDOR negado em URL, formulário adulterado e HTMX; cliente isolado;
técnico, médico e instituição exigem consentimento; revogação bloqueia acesso;
sessão expirada retorna 401; acesso profissional gera log anonimizado.
Evidências: commits 155820c, 80f336c, d4ab75c e b7dc182.
Pendências/riscos: cookies só serão emitidos pelo fluxo de login da Fase 4;
segredo TOTP já possui campo reservado para conteúdo cifrado, mas MFA pertence à
Fase 7.
Próximo passo: Fase 4 — login do cliente e consentimento inicial.
```

### 2026-09-21 — Fase 4 concluída

```text
Data/hora: 2026-09-21
Fase: 4 — Login do cliente e consentimento
Alterações: link mágico e código de seis dígitos; hashes de uso único; rate limit
persistente por IP/e-mail; mailer console/SMTP; cookies de sessão/CSRF;
consentimento inicial; logout revogável; cartão exclusivo para conta demo.
Comandos executados: pytest completo; inspeção visual do formulário no Chrome;
git diff --check.
Resultados: 52 testes passaram; resposta neutra; token/código não persistem em
texto; reutilização negada; código funciona em fluxo separado; CSRF e origem
estrangeira negados; cookies HttpOnly/SameSite/Secure conforme ambiente;
consentimento obrigatório; logout revoga a sessão; ENV=prod recusa DEMO_MODE.
Evidências: commits 241df26 e c7ff834.
Pendências/riscos: SMTP real não foi acionado. O Chrome controlado exibiu
ERR_BLOCKED_BY_CLIENT ao submeter POST para localhost; a tela foi inspecionada,
mas o fluxo visual completo será repetido com navegador E2E dedicado na Fase 11.
Próximo passo: Fase 5 — área do técnico e cadastro de novo cliente.
```

### 2026-09-21 — Fase 5 concluída

```text
Data/hora: 2026-09-21
Fase: 5 — Área do técnico e cadastro de novo cliente
Alterações: área técnica; cadastro transacional de cliente/paciente/dispositivo;
convite demo; estado aguardando primeira leitura; ativação sintética;
desassociação sem apagar leituras; auditoria do ciclo técnico.
Comandos executados: pytest completo; git diff --check.
Resultados: 58 testes passaram; técnico demo entra em área própria; cliente não
entra; duplicidade não deixa registros parciais; papel criado é sempre customer;
primeira leitura ativa somente o device correto; dispositivo fica exclusivo;
desassociação preserva leituras e produz access_log.
Evidências: commits 4bd58e6 e 07c3074.
Pendências/riscos: acesso técnico real e provisionamento pelo owner receberão
senha forte na Fase 7; somente contas sintéticas podem usar o atalho demo atual.
Próximo passo: Fase 6 — área da família.
```

### 2026-09-21 — Fase 6 concluída

```text
Data/hora: 2026-09-21
Fase: 6 — Área da família
Alterações: painel familiar mobile-first; escala visual de cinco níveis;
datas locais; detalhes de estimativas recolhidos; estado do dispositivo/coletor;
pedidos de atualização; destinatários com consentimento e auditoria.
Comandos executados: pytest completo; git diff --check; QA em Chrome 390x844.
Resultados: 68 testes passaram; sem overflow horizontal; texto-base de 18 px;
detalhes fechados por padrão; IDOR bloqueado; estados sem dados e offline claros.
Evidências: commits 142837b, e6a7b82 e 70b8c1a; docs/FAMILIA.md.
Pendências/riscos: regras de avaliação entram na Fase 9; coletor físico e
polling HTMX entram na Fase 8. POST no Chrome local segue bloqueado pelo cliente,
mas foi coberto pelo teste ASGI.
Próximo passo: Fase 7 — login forte e console médico.
```

### 2026-09-21 — Fase 7 concluída

```text
Data/hora: 2026-09-21
Fase: 7 — Login forte e console médico
Alterações: Argon2; desafio MFA; TOTP cifrado; QR SVG local; recuperação
de uso único; rate limit; lista priorizada; detalhe, tendência e auditoria.
Comandos executados: instalação das dependências; pytest completo;
git diff --check.
Resultados: 72 testes passaram; credenciais incorretas não criam sessão;
recuperação não reutiliza; IDOR e consentimento revogado retornam 403;
visualização autorizada produz access_log.
Evidências: commits b856789 e e007881; docs/MEDICO.md.
Pendências/riscos: execução do coletor, polling e timeout do pedido entram
na Fase 8; rotação de SESSION_SECRET exige reprovisionar TOTP.
Próximo passo: Fase 8 — atualização sob demanda e coletor compartilhado.
```

### 2026-09-21 — Fase 8 concluída

```text
Data/hora: 2026-09-21
Fase: 8 — Atualização sob demanda e coletor compartilhado
Alterações: controle de processo compartilhado; trava BLE atômica; pedido
idempotente; polling HTMX; conclusão por leitura nova; timeout de 120 segundos.
Comandos executados: py_compile do dashboard/controle; pytest; git diff --check.
Resultados: 76 testes passaram; duplo clique mantém um pedido ativo; coletor
contínuo bloqueia --once; timeout informa sem resposta e não cria alerta.
Evidências: commits 2049ed8 e 616b951; docs/COLETOR.md.
Pendências/riscos: BLE físico permanece reservado ao portão manual da Fase 12.
Próximo passo: Fase 9 — simulador e regras demonstrativas.
```

### 2026-09-21 — Fase 9 concluída

```text
Data/hora: 2026-09-21
Fase: 9 — Simulador e regras demonstrativas
Alterações: funções puras; limiares centralizados; bloqueio de dado real;
simulador profissional; explicação simples e prévias sem valores de saúde.
Comandos executados: pytest completo; git diff --check.
Resultados: 96 testes passaram; limites e durações cobertos; baixa qualidade
não conclui; UI explicita simulação e validação clínica pendente.
Evidências: commits acaaf2b e dfc77da; docs/SIMULADOR.md.
Pendências/riscos: regras não possuem validação clínica e permanecem demo-only.
Próximo passo: Fase 10 — canais de notificação.
```

### 2026-09-22 — Fase 10 concluída

```text
Data/hora: 2026-09-22
Fase: 10 — Canais de notificação
Alterações: Notifier; console seguro; SMTP/WhatsApp opcionais; opt-in e
verificação; chave idempotente; histórico técnico sem conteúdo sensível.
Comandos executados: pytest completo; git diff --check.
Resultados: 99 testes passaram; mocks selecionam o canal; sem opt-in nada é
acionado; retentativa não duplica; logs omitem nome, destino e mensagem.
Evidências: commit 6d95d2e; docs/NOTIFICACOES.md.
Pendências/riscos: envio real não foi testado nem habilitado.
Próximo passo: Fase 11 — endurecimento e testes completos da web.
```

### 2026-09-22 — Fase 11 concluída

```text
Data/hora: 2026-09-22
Fase: 11 — Endurecimento e testes completos da web
Alterações: backup verificado; README/CLAUDE atualizados; regressões,
auditoria, varredura de segredos e QA visual dos três perfis.
Comandos executados: pytest; build/audit do site; py_compile; node --check;
secret scan; Uvicorn temporário; Chrome em 390x844 e 1280x800.
Resultados: 100 testes; auditor 0 erros/30 avisos conhecidos; scan limpo;
sem CDN no app; sem overflow; perfis e escopos corretos no navegador.
Evidências: commit 85b647b; docs/TESTES.md e docs/BACKUP.md.
Pendências/riscos: Chrome controlado bloqueou POST localhost; POSTs foram
cobertos por ASGI. BLE, SMTP, WhatsApp e ngrok não foram acionados.
Próximo passo: Fase 12 — portão manual com o anel e o usuário.
```

### 2026-09-25 — Fase 12 em andamento: configuração segura de e-mail

```text
Data/hora: 2026-09-25
Fase: 12 — portão manual com o anel e o usuário
Alterações: assistente interativo para SMTP no .env ignorado pelo Git;
validação de entradas; gravação atômica; TLS com contexto seguro; instruções
para senha de aplicativo do Gmail.
Comandos executados: py_compile; pytest focado; pytest completo.
Resultados: 12 testes focados e 111 testes totais passaram; um aviso de
depreciação conhecido do TestClient permaneceu sem impacto.
Evidências: testes da atualização sem duplicidade e rejeição de valores
inválidos; credencial não passa pela linha de comando nem pelo Git.
Pendências/riscos: autenticação e entrega SMTP reais dependem da senha de
aplicativo informada localmente pelo usuário; BLE físico segue sem nova evidência.
Próximo passo: configurar a conta local, reiniciar a API e comprovar o recebimento
do link de login antes de validar o console médico.
```
