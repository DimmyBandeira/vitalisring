// Cloudflare Pages Function: POST /api/lista-de-espera
// Grava inscrições da lista de espera no D1 (binding "DB").
// Sem binding configurado, responde 503: a coleta só é ligada depois que a
// Política de Privacidade estiver publicada (ver docs/DEPLOY_CLOUDFLARE.md).
// Nunca registra em log nome, telefone ou e-mail.

export const CONSENT_VERSION = "2026-10-10";
export const OBJECTIVES = ["familia", "profissional", "instituicao", "pessoal"];
const MAX_BODY_BYTES = 10_000;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function normalizePhone(raw) {
  const digits = String(raw || "").replace(/\D/g, "");
  const local = digits.length === 13 && digits.startsWith("55") ? digits.slice(2) : digits;
  // DDD (11–99) + celular com nono dígito
  return /^[1-9][1-9]9\d{8}$/.test(local) ? local : null;
}

export function validate(fields) {
  const errors = {};
  const name = String(fields.nome || "").trim().replace(/\s+/g, " ");
  const email = String(fields.email || "").trim().toLowerCase();
  const whatsapp = normalizePhone(fields.whatsapp);
  const objective = String(fields.objetivo || "");
  if (name.length < 3 || name.length > 120 || !name.includes(" ")) errors.nome = "Informe seu nome completo.";
  if (!whatsapp) errors.whatsapp = "Informe um celular com DDD, por exemplo (21) 98765-4321.";
  if (email.length > 254 || !EMAIL_RE.test(email)) errors.email = "Informe um e-mail válido.";
  if (!OBJECTIVES.includes(objective)) errors.objetivo = "Escolha o seu principal objetivo.";
  if (!fields.consentimento) errors.consentimento = "É preciso concordar com a Política de Privacidade.";
  return { errors, data: { name, email, whatsapp, objective } };
}

function wantsJson(request) {
  return (request.headers.get("Accept") || "").includes("application/json");
}

function reply(request, status, body) {
  if (wantsJson(request)) {
    return new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store" },
    });
  }
  if (body.ok) {
    return new Response(null, { status: 303, headers: { Location: "/obrigado/", "Cache-Control": "no-store" } });
  }
  const msg = body.message || "Não foi possível registrar sua inscrição.";
  const html = `<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="robots" content="noindex"><title>Inscrição não concluída | Vitalis Ring</title><p>${msg}</p><p><a href="/lista-de-espera/#formulario">Voltar ao formulário</a></p></html>`;
  return new Response(html, { status, headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" } });
}

export async function handleWaitlist(request, env) {
  const origin = request.headers.get("Origin");
  if (origin && new URL(origin).host !== new URL(request.url).host) {
    return reply(request, 403, { ok: false, message: "Origem não permitida." });
  }
  if (Number(request.headers.get("Content-Length") || 0) > MAX_BODY_BYTES) {
    return reply(request, 413, { ok: false, message: "Envio muito grande." });
  }
  let form;
  try {
    form = await request.formData();
  } catch {
    return reply(request, 400, { ok: false, message: "Formulário inválido." });
  }
  const fields = Object.fromEntries(form.entries());

  // honeypot: robôs preenchem o campo oculto; respondemos sucesso sem gravar
  if (String(fields.website || "").trim()) return reply(request, 200, { ok: true });

  const { errors, data } = validate(fields);
  if (Object.keys(errors).length) {
    return reply(request, 422, { ok: false, message: "Revise os campos destacados.", errors });
  }
  if (!env || !env.DB) {
    return reply(request, 503, { ok: false, message: "As inscrições ainda não estão abertas. Tente novamente em breve." });
  }

  const now = new Date().toISOString();
  try {
    // e-mail repetido não gera erro nem revela se já estava inscrito
    await env.DB.prepare(
      "INSERT INTO waitlist (created_at, name, whatsapp, email, objective, consent_version, consent_at, source) " +
        "VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8) ON CONFLICT(email) DO NOTHING"
    )
      .bind(now, data.name, data.whatsapp, data.email, data.objective, CONSENT_VERSION, now, "site")
      .run();
  } catch {
    console.error("waitlist: falha ao gravar inscrição");
    return reply(request, 500, { ok: false, message: "Não foi possível registrar agora. Tente novamente em instantes." });
  }
  return reply(request, 200, { ok: true });
}

export const onRequestPost = ({ request, env }) => handleWaitlist(request, env);
