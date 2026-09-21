# Ambiente de desenvolvimento — Vitalis Ring

## Python suportado

O coletor BLE depende de `colmi-r02-client`, que requer Python `>=3.11,<3.13`.
O ambiente validado neste computador usa:

```text
Python 3.12.7
C:\Users\drb-d\.virtualenvs\vitalis-ring
```

A venv fica fora do OneDrive para evitar sincronização de milhares de arquivos,
travamentos e caminhos inconsistentes. A pasta `venv/` antiga na raiz não deve
ser usada nem apagada automaticamente; ela pode conter estado que pertence ao
usuário.

## Abrir uma sessão PowerShell

Na raiz do repositório:

```powershell
$env:VITALIS_PYTHON = 'C:\Users\drb-d\.virtualenvs\vitalis-ring\Scripts\python.exe'
& $env:VITALIS_PYTHON --version
```

Não use apenas `python`, `pip`, `uvicorn` ou `streamlit`: o PATH contém Python
3.14 e pode voltar a conter executáveis do Anaconda.

## Instalação

Ambiente de execução:

```powershell
& $env:VITALIS_PYTHON -m pip install -r requirements.txt
```

Ambiente de desenvolvimento e testes:

```powershell
& $env:VITALIS_PYTHON -m pip install -r requirements-dev.txt
```

## Comandos básicos

```powershell
# Testes automatizados
& $env:VITALIS_PYTHON -m pytest

# Build e auditoria do site
& $env:VITALIS_PYTHON site\build.py
& $env:VITALIS_PYTHON site\tools\audit_site.py --dist site\dist --ignore LNK-002

# API local
& $env:VITALIS_PYTHON -m uvicorn api:app --host 127.0.0.1 --port 8000

# Dashboard local; nunca publicar esta porta no ngrok
& $env:VITALIS_PYTHON -m streamlit run dashboard.py --server.address 127.0.0.1 --server.port 8501
```

## Isolamento dos testes

`tests/conftest.py` define um `DATABASE_URL` temporário antes de importar os
módulos do projeto. Também fornece credenciais e endereço BLE exclusivamente de
teste. Essas configurações têm precedência sobre `.env` durante o pytest.

Se um teste precisar acessar um banco persistente, ele deve criar um arquivo em
`tmp_path`. Testes nunca devem remover, alterar ou se conectar a
`ring_data.sqlite`.
