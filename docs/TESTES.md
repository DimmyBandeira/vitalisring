# Evidências do portão web

## Automação

- 100 testes pytest aprovados;
- API anônima protegida, OpenAPI oculta na exposição e cabeçalhos ativos;
- sessão expirada, CSRF, rate limit, IDOR e revogação de consentimento;
- Argon2, TOTP, recuperação de uso único e auditoria profissional;
- regras puras, mensagens sem valores de saúde e canais sem envio externo;
- coletor sem concorrência, pedido idempotente, polling e timeout;
- backup SQLite consistente e sem sobrescrita.

`site/build.py` concluiu e `audit_site.py --ignore LNK-002` retornou 0 erros e
30 avisos conhecidos: dados jurídicos pendentes e número de WhatsApp de teste.
Python, dashboard e JavaScript compilaram. A varredura dos arquivos versionados
não encontrou chave privada, bearer token ou chave de API com formato de segredo.

## Navegador real

Chrome foi validado contra Uvicorn e banco temporário, sem tocar no banco real:

- família em 390×844, texto-base 18 px, sem overflow, cinco níveis, rótulo
  fictício, destinatários e detalhes recolhidos;
- técnico em 1280×800, implantações e cadastro visíveis, sem números de saúde;
- médico em 1280×800, somente paciente autorizado, detalhe com tendência,
  aviso regulatório e simulador claramente fictício;
- nenhuma folha de estilo ou script externo foi carregado pela aplicação.

A extensão de controle do Chrome bloqueia submissões POST para localhost com
`ERR_BLOCKED_BY_CLIENT`. Por isso, os POSTs de login, MFA, cadastro, consentimento,
atualização e simulador foram executados pelo cliente ASGI; as telas e
navegações GET foram verificadas no navegador real. O cadastro com hardware será
feito pelo usuário no portão manual da Fase 12.

## Limites honestos

Não foram acionados BLE real, SMTP, WhatsApp nem ngrok. As duas advertências
da suíte vêm de deprecações entre Starlette TestClient/httpx e anyio, não do
código do projeto.
