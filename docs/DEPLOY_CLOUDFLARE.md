# Publicação do site na Cloudflare Pages

Esta publicação corresponde somente à Fase 1. Ela não envia o FastAPI, o
SQLite, o coletor BLE nem dados do anel para a Cloudflare.

## Configuração do projeto Pages

- Repositório: `DimmyBandeira/vitalisring`
- Branch de produção inicial: `feature/area-logada`
- Diretório raiz: `site`
- Comando de build: `python -m pip install -r requirements.txt && python build.py`
- Diretório de saída: `dist`

Variáveis opcionais:

- `SITE_URL`: URL canônica alternativa. Sem ela, todos os builds usam o domínio
  definitivo `https://vitalisring.com.br`.
- `APP_URL`: deixar ausente na Fase 1. Como a Cloudflare fornece `CF_PAGES=1`, o
  acesso ao sistema ficará oculto até o backend da Fase 2 ter uma URL segura.
- `WHATSAPP_NUMBER`: número aprovado para publicação. Sem essa variável, os
  botões de WhatsApp não são publicados.

## Validação local

```powershell
Set-Location site
python -m pip install -r requirements.txt
python build.py
python tools/audit_site.py --dist ./dist
```

Depois do primeiro deploy, conferir a URL pública em desktop e celular, os
cabeçalhos definidos em `_headers`, o `robots.txt`, o `sitemap.xml` e todos os
links internos.

## Implantação vigente

- Data da primeira implantação: 2026-10-10
- Projeto Pages: `vitalisring`
- URL pública definitiva: `https://vitalisring.com.br`
- URL técnica do Pages: `https://vitalisring.pages.dev`
- Branch de produção: `feature/area-logada`
- Resultado inicial: implantação concluída e resposta `200 OK` por HTTPS

Foram conferidos os cabeçalhos de segurança, as 14 páginas públicas, o menu
móvel em 390 x 844, a ausência de overflow horizontal e o console do navegador.
A aprovação visual pelo usuário continua pendente antes do encerramento da
Fase 1.

Em 2026-10-10, a zona DNS foi ativada no plano Free com os nameservers
`kareem.ns.cloudflare.com` e `nicole.ns.cloudflare.com`. O domínio raiz foi
associado ao Pages por CNAME flattening e respondeu `200 OK` por HTTPS. A
aprovação visual do usuário continua pendente antes do encerramento da Fase 1.

## Lista de espera (Pages Function + D1)

O formulário de `/lista-de-espera/` envia para `POST /api/lista-de-espera`,
implementado em `site/functions/api/lista-de-espera.js`. A função valida
origem, honeypot, campos e consentimento e grava no banco D1 ligado pelo
binding `DB`. **Sem esse binding, a função responde 503 e nada é gravado** —
é o interruptor da coleta.

Pré-requisito: publicar a Política de Privacidade definitiva (finalidade,
base legal, retenção, operadores e canal de exclusão) antes de ligar o
binding. Hoje `/politica-de-privacidade/` ainda é um placeholder.

Ativação (painel da Cloudflare, plano gratuito):

1. **Storage & Databases → D1 → Create database**, nome `vitalis-lista-espera`.
2. Na aba **Console** do banco, colar e executar o conteúdo de
   `site/db/lista_espera.sql`.
3. **Workers & Pages → vitalisring → Settings → Bindings → Add → D1 database**:
   nome da variável `DB`, banco `vitalis-lista-espera`, ambiente Production.
4. Fazer um novo deploy (push ou "Retry deployment"); bindings só valem a
   partir da próxima implantação.
5. Testar uma inscrição real e conferir no Console:
   `SELECT id, created_at, objective FROM waitlist ORDER BY id DESC LIMIT 5;`

Operação:

- exportar inscrições pelo Console do D1 ou com
  `npx wrangler d1 export vitalis-lista-espera --remote --output=lista.sql`
  (arquivo com dados pessoais: não versionar);
- pedido de exclusão: `DELETE FROM waitlist WHERE email = '...';`;
- e-mail repetido não gera erro nem revela inscrição anterior;
- a função não registra nome, telefone ou e-mail em log;
- pendências: limitação de taxa (regra de Rate Limiting da Cloudflare ou
  Turnstile) e confirmação automática por WhatsApp/e-mail, que dependem dos
  canais de notificação da Fase 2.

Testes: `node --test tests/js/lista-de-espera.test.mjs`, também executado pela
suíte `pytest` via `tests/test_waitlist_function.py`.
