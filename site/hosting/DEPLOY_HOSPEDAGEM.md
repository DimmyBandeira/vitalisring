# Publicação do site público — hospedagem estática (Hostinger / cPanel)

O site é **estático**: pasta `dist/` com HTML por rota. Qualquer hospedagem com Apache/LiteSpeed serve. **Não precisa de Node no servidor.**

> Observação: a Hostinger usa painel próprio (hPanel) em vez de cPanel, mas o fluxo é o mesmo (Gerenciador de Arquivos/FTP + `.htaccess`). Confirme no plano contratado: (1) `.htaccess` habilitado, (2) SSL gratuito, (3) data center no Brasil ou latência aceitável. Para a área logada e a API você precisará de um **VPS separado** (não use hospedagem compartilhada para o FastAPI).

## 1. Domínio e DNS
- Domínio `vitalisring.com.br` registrado por você no Registro.br.
- **Opção A (simples):** apontar os nameservers para a hospedagem e gerenciar o DNS lá.
- **Opção B (recomendada):** usar **Cloudflare (plano gratuito)** como DNS/CDN na frente: ganha cache global, proteção básica e Turnstile. Nesse caso, em *SSL/TLS* escolha **Full (strict)** — o modo "Flexible" cria loop de redirecionamento com o `.htaccess`.
- Registros previstos:
  | Nome | Tipo | Destino |
  |---|---|---|
  | `@` (vitalisring.com.br) | A | IP da hospedagem do site |
  | `www` | CNAME | `vitalisring.com.br` (o `.htaccess` redireciona para o domínio sem `www`) |
  | `app` | A | IP do VPS (FastAPI + Jinja + HTMX) — outra etapa |
- **E-mail transacional** (confirmação de cadastro): use um provedor de envio e configure **SPF, DKIM e DMARC** no DNS, com remetente `nao-responda@vitalisring.com.br`. Sem isso, os e-mails de confirmação caem no spam.

## 2. Ambientes
- **Homologação:** `staging.vitalisring.com.br` com **senha (Basic Auth) e `noindex`**. As pré-visualizações do Atoms são públicas; não deixe versões de teste indexáveis.
- **Produção:** `vitalisring.com.br`.

## 3. Publicar
1. No Atoms/GitHub: `npm ci && npm run build` → gera `dist/`.
2. `python tools/audit_site.py --dist ./dist` → corrija os ERROS (use `prompts/12_prompts_de_correcao.md`).
3. Ative **SSL gratuito** (AutoSSL/Let's Encrypt) e confirme HTTPS funcionando.
4. Envie **o conteúdo** de `dist/` (não a pasta `dist`) para `public_html/` (Gerenciador de Arquivos ou FTP).
5. Copie `hosting/htaccess.txt` para `public_html/.htaccess` (renomeie para `.htaccess`).
6. Teste no navegador: `http://` → vira `https://`; `www` → vira o domínio sem `www`; uma URL inexistente mostra sua `404.html`.
7. **Auditoria ao vivo (sem JavaScript):**
   `python tools/audit_site.py --live https://vitalisring.com.br`
8. Depois de estável, ative o **HSTS** no `.htaccess` (linha comentada).

## 4. Antes de abrir ao público
- `python tools/audit_site.py --dist ./dist --production --allow-host challenges.cloudflare.com` (ajuste `--allow-host` conforme o que o site realmente carrega) deve terminar **sem erros**: todos os `[PENDENTE…]` resolvidos, número de WhatsApp de teste trocado, textos legais publicados.
- **Google Search Console:** verifique o domínio por registro TXT no DNS e envie `https://vitalisring.com.br/sitemap.xml`. Faça isso **somente** quando o site estiver liberado.
- Confirme que `robots.txt` não bloqueia o site e que `/obrigado/` e `/confirmado/` seguem com `noindex`.

## 5. Atualizações
Publique sempre por `dist/` novo + auditoria. Arquivos em `/assets/` têm hash no nome (cache longo); o HTML não fica em cache (`no-cache`), então mudanças aparecem na hora.
