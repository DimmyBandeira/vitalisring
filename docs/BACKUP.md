# Backup e recuperação do SQLite

## Criar backup

Com a API configurada para o banco desejado, execute:

```powershell
& 'C:\Users\drb-d\.virtualenvs\vitalis-ring\Scripts\python.exe' scripts\backup_db.py
```

O utilitário usa a API de backup do SQLite, executa `PRAGMA integrity_check` e
recusa sobrescrever um destino. A pasta `backups/` deve ficar fora do Git e ter
controle de acesso equivalente ao banco original.

## Restaurar

1. Pare Uvicorn, Streamlit e o coletor.
2. Preserve o banco atual com um backup adicional.
3. Execute `PRAGMA integrity_check` no arquivo escolhido.
4. Copie o backup para um novo caminho; não sobrescreva o original ainda.
5. Aponte `DATABASE_URL=sqlite:///...` para a cópia restaurada.
6. Inicie somente a API e valide `/health`, login e o paciente esperado.
7. Depois da conferência, inicie o coletor. Mantenha o arquivo anterior até o
   aceite funcional.

Backups contêm dados pessoais e estimativas de saúde. Não devem ser enviados
ao GitHub, anexados a chamados nem armazenados sem criptografia e acesso restrito.
