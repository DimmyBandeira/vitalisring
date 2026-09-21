# AGENTS.md — Vitalis Ring

Este arquivo orienta qualquer agente que trabalhe neste repositório. O plano
de execução oficial está em `docs/PLANO_IMPLEMENTACAO.md`.

## Antes de alterar qualquer arquivo

1. Leia integralmente `CLAUDE.md` e `docs/PLANO_IMPLEMENTACAO.md`.
2. Confira `git status -sb` e preserve alterações que já pertençam ao usuário.
3. Identifique a fase ativa no plano. Trabalhe somente nela e nas correções
   necessárias para que seus critérios de aceite passem.
4. Não inicie uma fase dependente enquanto a anterior estiver com teste
   obrigatório falhando.
5. Não faça `git push`. Commits locais só são permitidos quando a fase pedir e
   todos os seus testes obrigatórios estiverem verdes.

## Branch e commits

- Todo o desenvolvimento das 14 fases ocorre na branch local
  `feature/area-logada`.
- Nunca implemente ou faça commit diretamente em `master`.
- A branch é única para o projeto, mas deve conter vários commits pequenos.
- Cada frente/tarefa concluída e testada dentro de uma fase recebe seu próprio
  commit. Não espere terminar a fase inteira para registrar frentes independentes.
- Não misture em um commit alterações de fases diferentes nem correções sem
  relação entre si.
- Use mensagens no formato `fase-N(escopo): descrição curta`, por exemplo:
  `fase-1(api): proteger consultas de leituras`.
- Antes de cada commit, rode os testes proporcionais à frente alterada e a
  regressão relevante. Um commit não pode ser usado para esconder teste falhando.
- Depois do commit, informe ao usuário o hash curto, a mensagem e os testes
  executados. O histórico Git é o registro canônico dos hashes.
- Não use `--amend`, rebase, squash ou force push sem pedido explícito do usuário.
- Nunca faça push; a publicação da branch pertence ao usuário.

## Princípios do projeto

- Evolua o MVP incrementalmente; não reescreva o coletor, a API ou o dashboard
  Streamlit sem necessidade comprovada.
- Preserve os contratos existentes de `POST /readings/bulk`,
  `GET /readings/latest` e `GET /readings/history`.
- Código novo da área logada deve ficar principalmente em `webapp/`.
- `api.py` deve permanecer pequeno: configuração do FastAPI, inclusão de
  routers, proteção dos endpoints existentes e montagem do site estático.
- Use o mesmo `Base` e a mesma configuração de banco de `models.py`. Mudanças de
  esquema devem ser aditivas até existir uma estratégia formal de migração.
- Nunca apague ou sobrescreva leituras, bancos, imagens ou arquivos do usuário.
- Nunca inclua `.env`, chaves, tokens, senhas, códigos TOTP, dados pessoais ou
  dados de saúde em commits, URLs ou logs.

## Ambiente Python

- A integração `colmi-r02-client` exige Python `>=3.11,<3.13`.
- A venv existente na raiz está quebrada e não deve ser considerada válida.
- O Python global 3.14 não deve ser usado para o coletor.
- O plano prevê uma venv fora do OneDrive. Depois que ela existir, use o
  interpretador indicado por `VITALIS_PYTHON`; não dependa do `python` da PATH.
- Testes devem usar banco temporário e configuração própria. Não execute testes
  destrutivos contra `ring_data.sqlite`.

## Dados reais e dados sintéticos

- `ring-01` representa o dispositivo real já conhecido pelo projeto.
- `demo-01` e demais identificadores `demo-*` contêm somente dados sintéticos.
- Dados sintéticos devem aparecer na interface com o rótulo visível
  **“Dados fictícios — demonstração”**.
- Movimento, queda, sono, HRV e qualidade do sinal ainda não são fornecidos pelo
  coletor real. Podem existir no simulador, mas não podem ser apresentados como
  medições reais do Colmi R10.
- Até haver validação clínica e regulatória documentada, regras de alerta rodam
  apenas em simulação e não enviam alertas automáticos sobre `ring-01`.

## Cadastro e ativação de um anel

- O técnico da Vitalis cadastra o cliente, cria o paciente e registra o
  dispositivo pela área logada.
- Registrar/vincular um dispositivo no sistema não é o mesmo que conectar por
  Bluetooth.
- A conexão BLE é responsabilidade de um coletor executado próximo ao anel.
- Todo o fluxo web deve funcionar primeiro com um coletor/dispositivo sintético.
- A fase de hardware exige participação do usuário e não pode ser marcada como
  aprovada sem evidência de uma leitura produzida pelo anel físico.

## Segurança e privacidade

- Autorize cada acesso ao paciente; estar autenticado, sozinho, não concede
  acesso a qualquer `device_id`.
- Profissional ou instituição só acessa paciente com vínculo ativo e
  consentimento vigente.
- Registre auditoria de acessos sem registrar valores de saúde.
- Todo POST originado do navegador exige proteção CSRF e validação de origem.
- Cookies de sessão: `HttpOnly`, `SameSite=Lax` e `Secure`, exceto no modo de
  desenvolvimento servido explicitamente por HTTP local.
- Tokens de login, sessões e códigos de recuperação devem ser aleatórios,
  revogáveis e armazenados somente como hash.
- Respostas de solicitação de login devem ser neutras para evitar enumeração de
  usuários.
- Quando `PUBLIC_EXPOSURE=1`, documentação OpenAPI deve estar desativada e a
  aplicação deve recusar configuração insegura.

## Linguagem do produto

- Use “estimativa”, “avisa quando algo sai do padrão” e “informações para
  conversar com o médico”.
- Não use alegações como “diagnostica”, “detecta doença”, “previne”, “salva
  vidas” ou “clinicamente validado”.
- Mensagens externas nunca levam números de saúde. Exemplo:
  “Maria: vale observar. Abra o app.”
- Telas logadas devem exibir o aviso:
  “Estimativas automáticas. Pode conter erros. Não substitui avaliação médica.
  Em emergência, ligue 192 (SAMU).”

## Qualidade e testes

- Cada fase deve produzir evidência objetiva dos comandos executados e dos
  critérios de aceite.
- Use testes unitários para regras e segurança, testes de integração para banco
  e rotas e testes ponta a ponta no navegador para os fluxos principais.
- Teste autorização negativa: usuário sem vínculo, consentimento vencido,
  acesso cruzado por ID e alteração manual de URL.
- Não afirme que BLE, WhatsApp ou SMTP foram testados se apenas mocks foram
  usados.
- Não avance escondendo testes quebrados com `skip`, `xfail` ou captura ampla de
  exceções. Exceções justificadas devem ser documentadas no plano.

## Encerramento de cada fase

1. Rode os testes definidos para a fase.
2. Registre no plano a data, os comandos e o resultado resumido.
3. Atualize somente os marcadores realmente comprovados.
4. Liste riscos e pendências descobertos.
5. Faça um commit local da frente concluída usando o padrão definido em
   “Branch e commits”. Nunca faça push.
