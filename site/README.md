# Vitalis Ring — site público (gerador estático)

Site 100% estático: **Python + Jinja2** geram `dist/<rota>/index.html` (HTML real por rota, sem JavaScript para renderizar).
JS próprio ~1,4 KB gzip; CSS ~6,6 KB gzip; sem bibliotecas; **zero requisições externas** (fontes locais).

## Estrutura
```
build.py            gerador (python build.py -> dist/)
templates/          base.html (SEO, cabeçalho, rodapé, cookies) · home.html · 404.html · ring.svg.html
static/css/site.css camada de layout (usa design/tokens.css)
static/js/site.js   menu, revelação, demonstração Dia/Noite, cookies
static/hero/        (opcional) anel-hero-1200.webp e anel-hero-720.webp — se existirem, substituem o anel SVG
design/             tokens.css, fontes woff2 (OFL), kit de logo
tools/audit_site.py auditor de SEO técnico + copy regulatória + pendências
hosting/            htaccess.txt (vira .htaccess) · DEPLOY_HOSPEDAGEM.md
dist/               saída pronta para subir em public_html/
```

## Uso
```
pip install jinja2
python build.py
python tools/audit_site.py --dist ./dist --ignore LNK-002    # LNK-002: páginas internas ainda não construídas (fase 2)
```
Variáveis opcionais: `SITE_URL`, `APP_URL`, `WHATSAPP_NUMBER`, `WHATSAPP_MESSAGE`.
Sem `WHATSAPP_NUMBER`, nenhum botão de WhatsApp é publicado.

Na Cloudflare Pages, configure a raiz como `site`, o comando de build como
`python -m pip install -r requirements.txt && python build.py` e a saída como
`dist`. No ambiente Pages (`CF_PAGES=1`), sem `APP_URL`, o site informa que o
sistema estará disponível em breve em vez de criar um link quebrado para
`/login`. O build integrado local preserva `/login` na mesma origem.

## Anel do hero (imagem ou SVG)
Hoje o hero usa `static/hero/anel-hero-1200.webp` e `-720.webp` (recorte com transparência do PNG enviado; original em `static/hero/original/`). Para voltar ao anel SVG dourado: `HERO=svg python build.py` (ou apague os .webp).

## Trocar o anel ilustrativo por uma imagem
Gere a imagem com o Prompt I, exporte `anel-hero-1200.webp` e `anel-hero-720.webp` e coloque em `static/hero/`. O build passa a usar a imagem (com o mesmo disco de luz, linha de pulso e legendas). Ajuste as posições das legendas em `home.html` se a imagem tiver outro enquadramento.

## Estado (fase 1)
- **Pronto:** Home completa, 404, sitemap.xml, robots.txt, favicons, manifest, JSON-LD (Organization + WebSite), aviso e preferências de cookies.
- **Fase 2 (pendente):** páginas internas (famílias, médicos, instituições, como funciona, segurança, FAQ), formulários (contrato em `api`), páginas de conversão, obrigado/confirmado, legais.
- **Pendências de conteúdo:** todos os `[PENDENTE…]` (razão social, CNPJ, endereço, e-mail de contato, DPO, design final do anel).
- Antes de publicar: `python tools/audit_site.py --dist ./dist --production` deve passar sem erros.
