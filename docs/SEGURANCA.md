# Segurança operacional — Vitalis Ring

## Exposição pública

O modo público é ativado com:

```text
PUBLIC_EXPOSURE=1
```

Nesse modo, a aplicação:

- recusa uma `API_KEY` com menos de 32 caracteres;
- desativa `/docs`, `/redoc` e `/openapi.json`;
- protege respostas com cabeçalhos defensivos;
- marca respostas de `/readings/*` como `Cache-Control: no-store`.

As próximas fases acrescentarão sessões, CSRF e autorização por paciente. Até
essas fases terminarem, a aplicação não deve ser publicada, mesmo que esta
proteção inicial esteja ativa.

## Portas

- FastAPI: `127.0.0.1:8000` — será a única porta encaminhada pelo ngrok.
- Streamlit: `127.0.0.1:8501` — ferramenta local legada, nunca exposta.
- SQLite — arquivo local, sem porta de rede.

O dashboard Streamlit lê o banco diretamente e não depende dos GETs HTTP agora
protegidos. O coletor continua autenticando seu POST com `X-API-Key`.

## Comandos locais seguros

```powershell
$env:VITALIS_PYTHON = 'C:\Users\drb-d\.virtualenvs\vitalis-ring\Scripts\python.exe'
& $env:VITALIS_PYTHON -m uvicorn api:app --host 127.0.0.1 --port 8000
& $env:VITALIS_PYTHON -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

Não use `--host 0.0.0.0` na demonstração local. O túnel deve apontar para a
porta 8000 ligada ao loopback; nunca para a porta 8501.
