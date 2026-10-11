-- Tabela da lista de espera (Cloudflare D1).
-- Aplicar com: npx wrangler d1 execute vitalis-lista-espera --remote --file=site/db/lista_espera.sql
CREATE TABLE IF NOT EXISTS waitlist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  name TEXT NOT NULL,
  whatsapp TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  objective TEXT NOT NULL CHECK (objective IN ('familia', 'profissional', 'instituicao', 'pessoal')),
  consent_version TEXT NOT NULL,
  consent_at TEXT NOT NULL,
  source TEXT
);
