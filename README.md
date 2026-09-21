# MVP — Painel de Sinais Vitais do Anel Colmi R02

Coleta batimentos (BPM) e SPO2 do anel via BLE, envia pra um servidor central,
e mostra num painel em Streamlit com visão ao vivo + histórico.

Testado com a lib [`colmi_r02_client`](https://github.com/tahnok/colmi_r02_client) v0.x.

## Como funciona

```
[Anel] --BLE--> collector.py (roda em casa, perto do anel)
                     |  HTTPS POST /readings/bulk
                     v
              api.py (FastAPI, roda no servidor)
                     |
                 SQLite/Postgres
                     |
              dashboard.py (Streamlit, mesmo servidor)
                     |
        acessível de casa e do consultório (via navegador)
```

## 1. Achar o endereço do anel

Em casa, com o anel por perto:

```bash
pip install colmi-r02-client
colmi_r02_util scan
```

Anote o endereço (ex: `70:CB:0D:D0:34:1C`).

## 2. Subir o servidor (API + dashboard)

Isso roda no servidor central — pode ser um VPS, uma máquina no consultório, etc.

```bash
cd server
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edite .env e defina uma API_KEY forte

export $(cat .env | xargs)
uvicorn api:app --host 0.0.0.0 --port 8000
```

Em outro terminal, no mesmo servidor:

```bash
cd server
source venv/bin/activate
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0
```

Acesse `http://<ip-do-servidor>:8501`.

## 3. Rodar o coletor (em casa, perto do anel)

```bash
cd collector
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edite .env: RING_ADDRESS (do passo 1), API_URL (endereço do servidor), API_KEY (igual ao do servidor)

export $(cat .env | xargs)
python collector.py
```

Ele fica rodando em loop, lendo o anel e mandando pro servidor.

## 4. Levar isso pro consultório com segurança

Pra "espelhar" o dado de casa pro consultório sem abrir portas na internet,
a forma mais simples e segura é usar um túnel privado:

- **[Tailscale](https://tailscale.com/)** (mais fácil): instala em casa e no servidor,
  cria uma rede privada entre eles, sem precisar mexer em roteador/firewall.
- **Cloudflare Tunnel**: parecido, mais indicado se o servidor já é um domínio seu.

Isso evita expor a API/dashboard diretamente pra internet — importante já que é dado de saúde.

## O que o MVP cobre

- ✅ BPM e SPO2 em tempo real (leitura pontual periódica)
- ✅ Histórico de batimentos (o anel guarda sozinho, sincronizamos)
- ✅ Buffer local no coletor se a rede cair (reenvia depois)
- ✅ Autenticação simples por API key
- ⚠️ Histórico de SPO2 contínuo **ainda não existe** na lib (só leitura pontual em tempo real) — é uma limitação do reverse engineering do protocolo, não do nosso código
- ⚠️ Sono e "stress" também não são suportados pela lib ainda

## Próximos passos sugeridos (pós-MVP)

1. Trocar SQLite por Postgres se for mais de um paciente/anel
2. HTTPS de verdade no servidor (Caddy/nginx com Let's Encrypt, ou Cloudflare Tunnel já resolve isso)
3. Alertas (ex: BPM fora da faixa) — dá pra adicionar um webhook simples na API
4. Autenticação de usuário no dashboard (hoje qualquer um com acesso à rede vê o painel)
5. Se for uso clínico real, revisar com alguém de compliance/LGPD sobre consentimento e retenção de dados
