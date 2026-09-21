# Matriz de permissões — Vitalis Ring

## Regra principal

Autenticação não concede acesso automático a um paciente. Toda operação recebe
um `patient_id` e passa pela política central de autorização.

| Papel | Condição para acessar paciente | Auditoria obrigatória |
|---|---|---|
| `owner` | Conta ativa; acesso administrativo excepcional | Ações administrativas serão auditadas nas rotas próprias |
| `customer` | `care_link` ativo com o paciente | Não para simples consulta própria |
| `technician` | `care_link` técnico ativo e consentimento vigente | Sim |
| `doctor` | `care_link` profissional ativo e consentimento vigente | Sim |
| `institution` | `care_link` institucional ativo e consentimento vigente | Sim |

Um vínculo é inválido quando está desativado, ainda não começou ou já terminou.
Um consentimento é inválido quando está revogado, expirado ou não possui estado
`active`.

## Princípio do técnico

O técnico pode cadastrar cliente, paciente e dispositivo nas fases de ativação,
mas isso não lhe dá acesso permanente ao histórico de saúde. Qualquer consulta
de suporte vinculada a um paciente exige autorização vigente e gera
`access_log`.

## Auditoria

O registro contém somente metadados operacionais:

- usuário e paciente;
- ação e finalidade;
- horário;
- identificador da requisição;
- hash do IP, quando disponível.

Valores de BPM, SpO₂, bateria, conteúdo de mensagens, cookies, tokens e segredos
nunca entram no `access_log`.

## Defesa contra IDOR

A aplicação nunca confia no identificador enviado pelo navegador. A mesma
política é aplicada a:

- parâmetros de URL;
- campos de formulário adulterados;
- requisições HTMX;
- chamadas internas futuras.

Os testes automatizados trocam o `patient_id` por outro identificador válido e
confirmam resposta 403. POSTs de navegador exigem também token CSRF e origem
exata configurada em `PUBLIC_BASE_URL`.
