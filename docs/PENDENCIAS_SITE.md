# Pendências do site público — Fase 1

Levantamento de 2026-10-10, depois das páginas Famílias, Médicos,
Instituições, Como Funciona e Lista de Espera. Itens a tratar em uma próxima
frente.

## Páginas ainda em placeholder ("em preparação", `noindex`)

Todas usam `templates/coming_soon.html` e estão listadas em
`COMING_SOON_PAGES` (`site/build.py`).

| Página | Rota | Onde aparece hoje |
|---|---|---|
| Perguntas frequentes | `/perguntas-frequentes/` | menu móvel, rodapé (Navegar), home |
| Segurança e privacidade | `/seguranca-e-privacidade/` | rodapé (Navegar), home |
| Agendar demonstração | `/agendar-demonstracao/` | rodapé (Participar), CTAs de Médicos e Instituições |
| Programa piloto para médicos | `/programa-piloto-medicos/` | rodapé (Participar) |
| Contato | `/contato/` | rodapé (Participar e links legais) |
| Termos de Uso | `/termos-de-uso/` | rodapé (links legais) |
| Política de Privacidade | `/politica-de-privacidade/` | rodapé (links legais), consentimento da Lista de Espera |
| Política de Cookies | `/politica-de-cookies/` | rodapé (links legais) |

Prioridade sugerida: **Política de Privacidade** primeiro (bloqueia a ativação
do D1 da lista de espera), depois **Agendar demonstração** (destino dos CTAs
B2B) e **Contato**.

## Rodapé (`templates/base.html`)

- O texto "Este site institucional não recebe dados pessoais nem informações
  de saúde" deixa de ser verdadeiro quando o D1 da lista de espera for ligado.
  Ajustar junto com a Política de Privacidade.
- Faltam identificação da empresa: razão social, CNPJ, endereço e e-mail de
  contato (dados ainda não definidos).
- Botão "Falar no WhatsApp" só aparece com `WHATSAPP_NUMBER` configurado; hoje
  não está definido no Cloudflare (o número do README é de teste).
- Links "Contato", "Termos de Uso", "Política de Privacidade" e "Política de
  Cookies" apontam para placeholders (tabela acima).

## Cabeçalho

- "Sistema em breve" no lugar de "Entrar": depende da Fase 2 (URL segura da
  área logada).

## Lista de espera

- Coleta desligada até: Política de Privacidade publicada → D1
  `vitalis-lista-espera` criado → binding `DB` no projeto Pages → novo deploy
  (passo a passo em `DEPLOY_CLOUDFLARE.md`).
- Limitação de taxa (Rate Limiting/Turnstile) e confirmação automática por
  WhatsApp/e-mail ainda não implementadas.

## Outros

- Imagens da página Famílias ainda nos JPG originais (~5,6 MB); converter para
  WebP como nas demais páginas.
- E-mail do domínio (`contato@vitalisring.com.br`) sem MX; configurar o
  encaminhamento da Cloudflare quando o endereço for definido.
- Revisão jurídica da copy de todas as páginas continua necessária (o auditor
  automático não substitui).
