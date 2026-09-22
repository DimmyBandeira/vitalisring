# Acesso profissional e console médico

## Autenticação

O acesso começa em `/profissional/login` e exige senha com hash Argon2. Depois
da senha, um desafio opaco, armazenado apenas como hash, vale cinco minutos e
aceita no máximo cinco tentativas de segundo fator. O passo de senha também é
limitado por IP e e-mail.

No primeiro acesso, o sistema gera um segredo TOTP, cifra-o com uma chave
derivada de `SESSION_SECRET` e monta o QR como SVG local. A ativação exige um
código TOTP válido. Em seguida, oito códigos de recuperação aparecem uma única
vez; o banco guarda somente hashes, e cada código é invalidado ao ser usado.

Trocar `SESSION_SECRET` invalida sessões e impede decifrar segredos TOTP já
provisionados. Uma rotação futura deve incluir reprovisionamento controlado.

## Autorização do console

`/app/medico` lista apenas pacientes com `care_link` ativo e consentimento
vigente. A lista usa a prioridade visual dos avisos demonstrativos. O detalhe
mostra tendência em SVG, leituras recentes e o comando “Atualizar agora”.

Cada abertura autorizada de detalhe grava `view_patient` em `access_log`, sem
valores de saúde. Paciente não vinculado ou com consentimento revogado retorna
403 imediatamente, inclusive para uma sessão que já estava aberta.

O comando de atualização já cria/reutiliza `refresh_request`. A execução
assíncrona do coletor físico, trava de concorrência, polling HTMX e timeout
visual de 120 segundos pertencem à Fase 8.

## Evidências

- 72 testes aprovados na suíte completa;
- senha ou TOTP incorretos não criam sessão;
- código de recuperação não pode ser reutilizado;
- segredo TOTP não fica em texto puro no banco;
- QR SVG é gerado sem serviço externo;
- IDOR, revogação imediata e auditoria do detalhe foram testados.
