// Testes da Pages Function da lista de espera. Rodar: node --test tests/js/
import { test } from "node:test";
import assert from "node:assert/strict";
import { handleWaitlist, normalizePhone, validate } from "../../site/functions/api/lista-de-espera.js";

const URL_BASE = "https://vitalisring.com.br/api/lista-de-espera";
const VALID = {
  nome: "Maria Souza",
  whatsapp: "(21) 98765-4321",
  email: "Maria@Exemplo.com.br",
  objetivo: "familia",
  consentimento: "on",
};

function fakeDb({ fail = false } = {}) {
  const calls = [];
  return {
    calls,
    prepare(sql) {
      return {
        bind(...args) {
          return {
            async run() {
              if (fail) throw new Error("d1 down");
              calls.push({ sql, args });
              return { success: true };
            },
          };
        },
      };
    },
  };
}

function post(fields, { json = true, origin = "https://vitalisring.com.br" } = {}) {
  const body = new FormData();
  for (const [k, v] of Object.entries(fields)) body.append(k, v);
  const headers = { Accept: json ? "application/json" : "text/html" };
  if (origin) headers.Origin = origin;
  return new Request(URL_BASE, { method: "POST", body, headers });
}

test("normaliza celular brasileiro com DDD e nono dígito", () => {
  assert.equal(normalizePhone("(21) 98765-4321"), "21987654321");
  assert.equal(normalizePhone("+55 11 91234-5678"), "11912345678");
  assert.equal(normalizePhone("(21) 3876-5432"), null);
  assert.equal(normalizePhone("98765-4321"), null);
});

test("validação exige nome completo, objetivo válido e consentimento", () => {
  const { errors } = validate({ nome: "Maria", whatsapp: "x", email: "a@b", objetivo: "outro" });
  assert.deepEqual(Object.keys(errors).sort(), ["consentimento", "email", "nome", "objetivo", "whatsapp"]);
});

test("inscrição válida grava dados normalizados e versão do consentimento", async () => {
  const DB = fakeDb();
  const res = await handleWaitlist(post(VALID), { DB });
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { ok: true });
  assert.equal(DB.calls.length, 1);
  const [, name, whatsapp, email, objective, consentVersion] = DB.calls[0].args;
  assert.deepEqual([name, whatsapp, email, objective], ["Maria Souza", "21987654321", "maria@exemplo.com.br", "familia"]);
  assert.match(consentVersion, /^\d{4}-\d{2}-\d{2}$/);
  assert.match(DB.calls[0].sql, /ON CONFLICT\(email\) DO NOTHING/);
});

test("sem JavaScript, sucesso redireciona para a página de obrigado", async () => {
  const res = await handleWaitlist(post(VALID, { json: false }), { DB: fakeDb() });
  assert.equal(res.status, 303);
  assert.equal(res.headers.get("Location"), "/obrigado/");
});

test("campos inválidos retornam 422 sem gravar", async () => {
  const DB = fakeDb();
  const res = await handleWaitlist(post({ ...VALID, consentimento: "" }), { DB });
  assert.equal(res.status, 422);
  assert.ok((await res.json()).errors.consentimento);
  assert.equal(DB.calls.length, 0);
});

test("honeypot preenchido finge sucesso e não grava", async () => {
  const DB = fakeDb();
  const res = await handleWaitlist(post({ ...VALID, website: "spam.example" }), { DB });
  assert.equal(res.status, 200);
  assert.equal(DB.calls.length, 0);
});

test("origem de outro site é recusada", async () => {
  const DB = fakeDb();
  const res = await handleWaitlist(post(VALID, { origin: "https://ataque.example" }), { DB });
  assert.equal(res.status, 403);
  assert.equal(DB.calls.length, 0);
});

test("sem banco configurado a coleta fica fechada (503)", async () => {
  const res = await handleWaitlist(post(VALID), {});
  assert.equal(res.status, 503);
});

test("falha do banco não vaza dados pessoais no log", async () => {
  const logged = [];
  const original = console.error;
  console.error = (...args) => logged.push(args.join(" "));
  try {
    const res = await handleWaitlist(post(VALID), { DB: fakeDb({ fail: true }) });
    assert.equal(res.status, 500);
  } finally {
    console.error = original;
  }
  const text = logged.join(" ");
  for (const secret of ["Maria", "21987654321", "exemplo.com.br"]) assert.ok(!text.includes(secret));
});
