# Login do cliente — Vitalis Ring

## Fluxo

1. A pessoa informa o e-mail em `/login`.
2. A resposta pública é sempre neutra.
3. Para uma conta B2C ativa, o sistema cria:
   - link com token aleatório, válido por 15 minutos e uso único;
   - código numérico de seis dígitos com o mesmo prazo;
   - somente os hashes são persistidos.
4. O acesso cria uma sessão opaca revogável.
5. No primeiro acesso, a pessoa precisa aceitar o consentimento vigente.
6. Logout revoga a sessão no servidor e remove os cookies.

## Demonstração

Com `DEMO_MODE=1`, uma conta marcada `is_demo` recebe na tela um cartão
“Modo demonstração — link de acesso”. Esse cartão nunca aparece para contas
reais. `ENV=prod` recusa iniciar com o modo de demonstração ligado.

## E-mail

`MAILER=console` é o padrão seguro de desenvolvimento. Ele não imprime e-mail,
token, código ou link nos logs. Como consequência, uma conta real precisa de
SMTP configurado para receber o acesso.

Para SMTP:

```text
MAILER=smtp
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
MAIL_FROM=
```

Para configurar sem colocar a credencial no histórico do terminal, execute:

```powershell
& $env:VITALIS_PYTHON -m tools.configure_smtp
```

No Gmail, use uma senha de aplicativo da conta com verificação em duas etapas;
nunca use a senha normal. A ferramenta grava a configuração somente no `.env`,
que é ignorado pelo Git. Reinicie a API depois da alteração. A autenticação
SMTP e a entrega real ainda precisam ser comprovadas com a conta escolhida.

## Cookies

- `vr_session`: `HttpOnly`, `SameSite=Lax`; `Secure` em HTTPS e fora de dev/test.
- `vr_csrf`: token CSRF legível pelo frontend, `SameSite=Lax`; não autentica.
- `vr_login_csrf`: hash HttpOnly temporário usado antes da sessão.

POSTs exigem token CSRF e correspondência exata com `PUBLIC_BASE_URL`.
