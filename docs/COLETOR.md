# Coletor compartilhado e atualização sob demanda

`collector_control.py` é a única camada que inicia ou encerra `collector.py`.
O dashboard Streamlit e a aplicação web usam o mesmo `collector.pid`, o mesmo
Python (`sys.executable`) e uma trava atômica `refresh.lock`. Uma coleta contínua
bloqueia `--once`; uma leitura pontual ativa bloqueia outra leitura e também o
início do loop.

Na web, `refresh_requests` é o contrato entre interface e coletor. A rota de
status exige sessão e autorização do paciente. O HTMX consulta somente o UUID do
pedido a cada três segundos; nenhum valor de saúde aparece na URL. Uma leitura
posterior ao pedido conclui a operação. Após 120 segundos, a interface mostra
“Sem resposta do anel” sem criar alerta clínico.

O modo sintético escreve no dispositivo `demo-*` correto e conclui imediatamente.
O modo físico atual é local: FastAPI e BLE rodam no mesmo Windows. Uma futura
instalação remota deve consumir o mesmo contrato de pedidos, sem expor BLE ao
navegador e sem substituir silenciosamente esta trava por processos concorrentes.

Evidências: compilação de `dashboard.py` e `collector_control.py`; 76 testes
automatizados; processo contínuo bloqueia `--once`; duplo clique mantém um pedido
ativo; sintético atualiza o device correto; timeout não gera alerta.
