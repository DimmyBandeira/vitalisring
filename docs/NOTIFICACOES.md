# Canais de notificação

`webapp/alerts/channels.py` define a interface `Notifier` e os adaptadores
console, SMTP e WhatsApp Cloud API. O envio externo nasce desligado:
`NOTIFICATION_SEND_ENABLED=0` produz somente uma prévia segura no console, sem
destinatário nem conteúdo nos logs.

Um canal somente é considerado quando existe `NotificationPreference` para o
usuário e paciente, com `opted_in=true` e `verified_at` preenchido. SMTP exige
`SMTP_HOST` e `MAIL_FROM`; WhatsApp exige `WHATSAPP_TOKEN` e
`WHATSAPP_PHONE_ID`. A ausência de configuração nunca tenta rede.

Cada entrega usa uma chave formada pelo evento, destinatário e canal. A tabela
`notification_attempts` torna retentativas idempotentes e armazena somente
estado, canal e código técnico de erro. Corpo da mensagem, valores de saúde,
token e destino não entram no histórico ou log.

Os testes usam notificadores falsos; nenhum SMTP ou WhatsApp real foi acionado.
Envio real continuará desabilitado na demonstração até haver credenciais,
canal verificado e opt-in explícito.
