# Área técnica — implantação de clientes e dispositivos

## Fluxo entregue

1. Técnico autenticado abre `/app/tecnico`.
2. Cadastra responsável, pessoa monitorada e dispositivo numa única operação.
3. O sistema cria o vínculo familiar e deixa o dispositivo em
   “Aguardando primeira leitura”.
4. Para `demo-*`, o técnico recebe um convite sintético e pode simular a
   primeira leitura.
5. Para dispositivo físico, a conexão continua dependendo do coletor próximo
   ao anel; o navegador não é apresentado como responsável pelo BLE.
6. Associação, ativação e desassociação ficam auditadas.

Falhas de validação ou duplicidade executam rollback e não deixam cliente,
paciente ou dispositivo parcial. Desassociar não apaga leituras existentes.

## Limites de acesso

A área técnica não oferece histórico de BPM ou SpO₂. Consultas de suporte que
envolvam um paciente exigem vínculo e consentimento conforme
`docs/PERMISSOES.md`.

Nesta fase, somente o técnico sintético pode usar link mágico na demonstração.
O acesso técnico real será provisionado pelo owner com autenticação forte na
Fase 7, antes do teste com o anel físico na Fase 12.
