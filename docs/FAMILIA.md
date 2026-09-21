# Área da família

## Experiência entregue

A rota `/app` mostra somente a pessoa vinculada ao usuário autenticado. O
cartão principal combina ícone, texto e cor nos cinco níveis visuais:

- Tudo em ordem (`ok`);
- Para saber (`info`);
- Vale observar (`warn`);
- Importante (`alert`);
- Precisa de você agora (`critical`).

O painel não calcula limiares clínicos nesta fase. Um aviso aberto já
persistido define o nível; sem aviso, somente a atualidade da comunicação
diferencia “Tudo em ordem” de “Para saber”. As regras demonstrativas entram na
Fase 9 e precisam ser validadas antes de qualquer uso real.

Horários permanecem UTC ingênuo no banco e são exibidos em
`America/Sao_Paulo`. BPM, SpO₂ e bateria ficam recolhidos em “Ver detalhes das
estimativas”. Dados sintéticos recebem o rótulo “Dados fictícios — demonstração”.

## Atualização e dispositivo

“Atualizar agora” cria um `refresh_request` de 120 segundos. Para dispositivo
sintético, a leitura é criada imediatamente e o pedido termina como `completed`.
Para dispositivo físico, o pedido permanece `pending`; disparo protegido do
coletor e polling HTMX pertencem à Fase 8.

O painel diferencia dispositivo ativo, simulador e estado do coletor físico
lido de `ring_status.json`. Arquivo ausente ou inválido resulta em mensagem
calma de falta de comunicação, sem alegar problema clínico.

## Destinatários e segurança

O responsável pode autorizar ou revogar avisos somente para uma pessoa que já
possua `care_link` ativo com o mesmo paciente. A operação exige sessão, CSRF,
origem válida e autorização sobre o paciente. Concessão e revogação ficam em
`access_log`, sem valores de saúde.

## Evidências da fase

- 68 testes automatizados aprovados, incluindo IDOR, fusos, cinco níveis,
  atualização sintética, consentimento e estados sem dados/offline;
- navegador Chrome em 390×844: texto-base 18 px, sem overflow horizontal,
  detalhes fechados por padrão e expansão validada;
- o POST de atualização foi comprovado pelo cliente ASGI, pois o Chrome
  controlado bloqueia POST para localhost (`ERR_BLOCKED_BY_CLIENT`).
