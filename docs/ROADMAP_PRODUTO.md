# Roadmap do produto — Vitalis Ring

Este é o roteiro macro vigente do produto. O plano técnico anterior em
`PLANO_IMPLEMENTACAO.md` permanece como histórico e detalhamento da aplicação web.
Uma fase nova só começa depois que os critérios obrigatórios da anterior forem
comprovados.

## Fase 1 — Site institucional no ar

Status: `[~]`

Objetivo: publicar o site institucional estático na Cloudflare, separado do
sistema logado e sem dados pessoais ou de saúde.

Escopo:

- Cloudflare Pages conectado ao GitHub;
- build restrito a `site/` e publicação de `site/dist/`;
- URL HTTPS `*.pages.dev` e, depois, domínio próprio;
- cabeçalhos de segurança e cache para ativos versionados;
- nenhuma API, banco SQLite, coletor BLE ou credencial na hospedagem;
- botão de login indisponível até a Fase 2 ter uma URL segura.

Aceite:

- build e auditoria estão verdes;
- navegação mobile e desktop está aprovada;
- links e recursos estáticos não retornam 404;
- HTTPS e cabeçalhos foram conferidos na URL pública;
- nenhum segredo, banco ou dado do anel foi publicado.

Evidência parcial em 2026-10-10:

- projeto `vitalisring` criado no Cloudflare Pages gratuito e conectado ao
  repositório `DimmyBandeira/vitalisring`;
- produção configurada a partir da branch `feature/area-logada`, com raiz
  `site`, build por `python build.py` e saída em `site/dist`;
- primeira implantação disponível em `https://vitalisring.pages.dev`;
- 14 páginas públicas navegadas sem 404;
- resposta pública `200 OK` por HTTPS, com CSP, `X-Frame-Options: DENY`,
  `X-Content-Type-Options: nosniff`, `Permissions-Policy` e
  `Referrer-Policy` conferidos;
- viewport móvel 390 x 844 sem overflow horizontal, menu móvel funcional e
  console do navegador sem erros ou avisos;
- domínio `vitalisring.com.br` ativado no plano Free, associado ao Pages e
  respondendo `200 OK` por HTTPS; nameservers confirmados nos resolvedores
  públicos da Cloudflare e do Google;
- pendente: revisão visual do usuário e ajustes solicitados. A fase permanece
  em andamento até essa aprovação.

## Fase 2 — Sistema web e alertas por e-mail simulados

Status: `[ ]`

Objetivo: integrar site, área logada e backend usando apenas pacientes e leituras
sintéticas claramente identificadas.

Escopo previsto:

- decidir hospedagem persistente do backend e do banco;
- revisar a autenticação profissional sem depender do TOTP atual;
- usar provedor transacional de e-mail com diagnóstico operacional seguro;
- validar login, consentimento, permissões e alertas ponta a ponta;
- manter valores de saúde fora das mensagens externas;
- não conectar o anel físico nesta fase.

Aceite: fluxo completo com dados `demo-*`, entrega real de e-mail comprovada e
testes negativos de autorização aprovados.

## Fase 3 — Aplicativo celular como coletor dos anéis

Status: `[ ]`

Objetivo: criar um aplicativo que se comunica por BLE com o anel e envia leituras
ao backend quando autorizado.

Escopo previsto:

- protótipo Android primeiro; avaliar iOS depois;
- cadastro seguro do dispositivo e pareamento assistido;
- fila local, reenvio e sincronização quando a internet voltar;
- funcionamento em segundo plano dentro das limitações do sistema operacional;
- credencial individual e revogável por instalação;
- consentimento e separação entre dispositivos reais e demonstração.

Aceite: leitura real identificada, sincronização sem duplicidade e recuperação
após perda de BLE ou internet.

## Fase 4 — Gateway residencial e sensor de 61 GHz

Status: `[ ]`

Objetivo: operar a coleta em casa sem depender continuamente do celular.

Arquitetura prevista:

- PC ou Raspberry Pi como primeira referência de gateway BLE;
- ESP32 somente após prova de compatibilidade com o protocolo do anel;
- radar de 61 GHz como sensor ambiental complementar de presença e movimento;
- o gateway lê o anel; o radar não lê o anel;
- buffer local, atualização remota assinada e diagnóstico sem dados sensíveis.

Aceite: operação prolongada, reconexão automática, dados corretamente atribuídos
e funcionamento seguro durante indisponibilidade da internet.

## Fase 5 — Localização da pessoa no ambiente

Status: `[ ]`

Objetivo: pesquisar e validar uma forma confiável de associar uma pessoa a uma
posição ou zona dentro do cômodo.

Restrições conhecidas:

- RSSI de Bluetooth varia com corpo, paredes, móveis e orientação, portanto não
  será tratado antecipadamente como localização precisa;
- radar de 61 GHz pode observar pessoas, mas não identifica sozinho qual delas
  usa determinado anel;
- o protótipo comparará zonas BLE, fusão com radar e, se necessário, UWB.

Aceite: erro e taxa de identificação medidos em cenário real antes de qualquer
promessa de produto ou automação de alerta.
