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

- `SITE_URL`: URL canônica do domínio definitivo. Sem ela, builds do Pages usam
  `https://vitalisring.pages.dev`; builds locais usam
  `https://vitalisring.com.br`.
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
- URL pública: `https://vitalisring.pages.dev`
- Branch de produção: `feature/area-logada`
- Resultado inicial: implantação concluída e resposta `200 OK` por HTTPS

Foram conferidos os cabeçalhos de segurança, as 14 páginas públicas, o menu
móvel em 390 x 844, a ausência de overflow horizontal e o console do navegador.
A aprovação visual pelo usuário e a associação do domínio próprio continuam
pendentes antes do encerramento da Fase 1.
