#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_site.py — Auditoria do site público do Vitalis Ring.

Verifica, SEM executar JavaScript (como faz um crawler simples):
  * SEO técnico: HTML com conteúdo real, title/description únicos, canonical correto,
    H1 único, Open Graph, sitemap.xml, robots.txt, 404, links internos, JSON-LD.
  * Recursos externos indevidos (Google Fonts, CDNs, scripts de gerador, pixels).
  * Copy regulatória (ANVISA/CDC/LGPD): termos clínicos, alegações proibidas, números
    inventados, depoimentos, aval de entidades, status regulatório, venda na fase 0.
  * Avisos obrigatórios no rodapé (erros, não substitui avaliação médica, 192).
  * Marcadores [PENDENTE ...] e número de WhatsApp de teste.

Uso:
  python audit_site.py --dist ./dist                       # audita a pasta de build
  python audit_site.py --dist ./dist --production          # modo pré-publicação (bloqueante)
  python audit_site.py --live https://vitalisring.com.br   # audita o site publicado (sem JS)
  python audit_site.py --dist ./dist --json audit_report.json

Código de saída: 0 = sem ERROS; 1 = há ERROS; 2 = uso incorreto.
Somente biblioteca padrão do Python 3.9+.
Este auditor é uma rede de segurança: NÃO substitui a revisão jurídica/regulatória.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from html.parser import HTMLParser

ERROR, WARN = "ERRO", "AVISO"

DEFAULT_SITE = "https://vitalisring.com.br"
TEST_NUMBERS = ["5521981918090", "21981918090", "(21) 98191-8090", "21 98191-8090", "21 981918090"]
GENERATOR_FINGERPRINTS = ["lovable", "gptengineer", "gpteng.co", "atoms.dev", "mgx.dev", "bolt.new", "v0.dev"]
FORBIDDEN_JSONLD = {"MedicalWebPage", "MedicalDevice", "MedicalCondition", "MedicalProcedure", "Drug",
                    "Physician", "MedicalOrganization", "MedicalTest", "MedicalTherapy"}
RESOURCE_RELS = {"stylesheet", "preload", "modulepreload", "prefetch", "icon", "shortcut", "apple-touch-icon",
                 "manifest", "preconnect", "dns-prefetch", "mask-icon"}
SKIP_TAGS = {"script", "style", "noscript", "template", "svg", "head"}
DEFAULT_NOINDEX = [
    "/obrigado/", "/confirmado/", "/para-familias/", "/para-medicos/",
    "/para-instituicoes/", "/perguntas-frequentes/",
    "/seguranca-e-privacidade/",
    "/agendar-demonstracao/", "/programa-piloto-medicos/", "/contato/",
    "/termos-de-uso/", "/politica-de-privacidade/", "/politica-de-cookies/",
]


# ----------------------------------------------------------------------------- parser
class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lang = None
        self.title = ""
        self._in_title = False
        self.metas = []            # dicts
        self.links = []            # dicts
        self.h1 = 0
        self.imgs = []
        self.anchors = []
        self.resources = []        # (tag, url)
        self.jsonld = []
        self._jsonld_buf = None
        self.forms = []            # dicts
        self._form = None
        self.text = []
        self.alts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v if v is not None else "") for k, v in attrs}
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
            rels = set((a.get("rel") or "").lower().split())
            if rels & RESOURCE_RELS and a.get("href"):
                self.resources.append(("link[" + (a.get("rel") or "") + "]", a["href"]))
        elif tag == "h1":
            self.h1 += 1
        elif tag == "img":
            self.imgs.append(a)
            if a.get("src"):
                self.resources.append(("img", a["src"]))
            for u in re.findall(r"(\S+)(?:\s+[\d.]+[wx])?(?:,|$)", a.get("srcset", "")):
                if u and not u[0].isdigit():
                    self.resources.append(("img[srcset]", u))
            if "alt" in a and a["alt"].strip():
                self.alts.append(a["alt"])
        elif tag == "a":
            self.anchors.append(a)
        elif tag == "script":
            if a.get("src"):
                self.resources.append(("script", a["src"]))
            if (a.get("type") or "").lower() == "application/ld+json":
                self._jsonld_buf = []
        elif tag in ("iframe", "source", "video", "audio", "embed") and a.get("src"):
            self.resources.append((tag, a["src"]))
        elif tag == "form":
            self._form = {"action": a.get("action", ""), "method": (a.get("method") or "").lower(), "inputs": [], "has_button": False}
            self.forms.append(self._form)
        elif tag == "input" and self._form is not None:
            self._form["inputs"].append(a)
        if tag in SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._jsonld_buf is not None:
            self.jsonld.append("".join(self._jsonld_buf))
            self._jsonld_buf = None
        if tag == "form":
            self._form = None
        if tag in SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._jsonld_buf is not None:
            self._jsonld_buf.append(data)
        elif self._skip == 0:
            self.text.append(data)

    # -------- helpers
    def meta(self, key, value_attr="content"):
        for m in self.metas:
            if (m.get("name") or m.get("property") or m.get("http-equiv") or "").lower() == key.lower():
                return m.get(value_attr)
        return None

    def link(self, rel):
        for l in self.links:
            if rel in (l.get("rel") or "").lower().split():
                return l.get("href")
        return None

    def visible_text(self):
        return re.sub(r"\s+", " ", " ".join(self.text)).strip()


# ----------------------------------------------------------------------------- copy lint
def negated(text, start):
    window = text[max(0, start - 32):start].lower()
    return any(w in window for w in ("não ", "nao ", "sem ", "nem ", "jamais", "nunca "))


# (código, severidade, regex, mensagem, respeita_negacao, sensível_a_caixa)
COPY_RULES = [
    ("MED-001", ERROR, r"\b(bradicardia|taquicardia|hipoxemia|hip[oó]xia|arritmia|fibrila[cç][aã]o|infarto|avc|acidente vascular|apneia|sepse|pneumonia|insufici[eê]ncia card[ií]aca|embolia|dpoc|hipertens[aã]o|diabetes|c[aâ]ncer|covid)\b",
     "Condição clínica citada: linguagem de finalidade médica (ANVISA). Reescrever em termos de bem-estar/variação do padrão.", False, False),
    ("CLM-001", ERROR, r"diagn[oó]stic", "Alegação de diagnóstico (só é aceitável em negação: 'não faz diagnóstico').", True, False),
    ("CLM-002", WARN, r"\bdetect(a|am|ar|ando|amos|e|em)\b", "'detecta' pode alegar detecção clínica. Confirmar que não se refere a condição de saúde.", False, False),
    ("CLM-003", ERROR, r"\b(previne|previnem|prevenir)\b|preven[cç][aã]o de (doen|infarto|avc|queda)", "Alegação de prevenção de doença/evento.", True, False),
    ("CLM-004", ERROR, r"clinicamente\s+(validad|comprovad|testad|aprovad)", "Alegação de validação clínica sem estudo.", False, False),
    ("CLM-005", ERROR, r"salv(a|ar|amos|ou|am)\s+vidas?", "Promessa 'salva vidas'.", False, False),
    ("CLM-006", ERROR, r"precis[aã]o\s+m[eé]dica|grau\s+m[eé]dico|padr[aã]o\s+m[eé]dico|qualidade\s+hospitalar", "Alegação de precisão/grau médico.", False, False),
    ("CLM-007", ERROR, r"\bsubstitu(i|em|ir|ímos)\b", "'substitui' só é aceitável em negação ('não substitui avaliação médica').", True, False),
    ("CLM-008", ERROR, r"american heart association|european society of cardiology|sociedade brasileira de cardiologia|american thoracic society|american academy of sleep medicine", "Nome de entidade como aval. Usar 'inspirado em boas práticas', sem citar a entidade.", False, False),
    ("CLM-009", ERROR, r"(aprovad|registrad|certificad|homologad|regularizad|autorizad)[oa]s?\s+(pel[oa]\s+|na\s+|no\s+|junto\s+[aà]\s+)?(anvisa|fda|anatel|inmetro|iso|ce)\b|certifica[cç][aã]o\s+iso|\biso\s?\d{4,5}\b", "Alegação de status regulatório/certificação. Só publicar com comprovação e aprovação jurídica.", False, False),
    ("CLM-010", WARN, r"\banvisa\b", "Menção à ANVISA: revisão jurídica obrigatória.", False, False),
    ("CLM-011", ERROR, r"\bmilhares\b|\bmilh[oõ]es\b|\bmais de \d|\d\s*\+(?!\d)|\bl[ií]der\b|n[uú]mero\s?1\b|\bn[ºo]\s?1\b|premiad|melhor do (brasil|mundo)", "Métrica/superlativo não comprovado.", False, False),
    ("CLM-012", ERROR, r"\d+([.,]\d+)?\s?%", "Número percentual: proibido sem fonte aprovada (risco CDC art. 37).", False, False),
    ("CLM-013", ERROR, r"(\bia\b|intelig[eê]ncia artificial)[^.]{0,50}(detect|diagnostic|prev[eê]|prevem)", "Alegação de IA que detecta/diagnostica/prevê.", False, False),
    ("CLM-014", WARN, r"24\s?h(oras)?\b|24\s?/\s?7|tempo real|vinte e quatro horas", "Promessa de monitoramento contínuo/tempo real: implica expectativa de resposta e responsabilidade.", False, False),
    ("CLM-015", ERROR, r"depoimento|hist[oó]rias? de clientes|clientes (satisfeitos|reais)|quem (j[aá] )?usa (recomenda|aprova)", "Depoimento/prova social: não usar pessoas ou casos fictícios.", False, False),
    ("CLM-016", ERROR, r"criptografia militar|100\s?%\s?seguro|totalmente seguro|invulner|[àa] prova de (hack|ataque|invas)", "Promessa absoluta de segurança.", False, False),
    ("CLM-017", WARN, r"(dados|servidores?)\s+(armazenados\s+)?(no|em)\s+brasil", "Afirmação sobre localização dos dados: só manter se verdadeira e contratada.", False, False),
    ("COM-001", ERROR, r"\b(compre|comprar|adquira|adquirir|carrinho|checkout|frete|parcele|parcelamos)\b|r\$\s?\d", "Fase 0 (pré-lançamento): sem venda/preço.", False, False),
    ("COM-002", WARN, r"dispon[ií]vel\s+(a partir|em)\s+\w+|lan[cç]amento\s+(previsto|em|dia)", "Possível promessa de data/disponibilidade.", False, False),
]
COPY_RULES_CASE = [
    ("CLM-008b", ERROR, r"\b(AHA|ESC|ATS|AASM)\b", "Sigla de entidade científica como aval.", False),
    ("CLM-015b", WARN, r"\bDr\.?a?\.?\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-zà-ú]+", "Nome de médico: precisa ser real, identificado e autorizado.", False),
]
COMPILED = [(c, s, re.compile(p, re.I | re.U), m, n) for c, s, p, m, n, _ in COPY_RULES]
COMPILED_CASE = [(c, s, re.compile(p, re.U), m, n) for c, s, p, m, n in COPY_RULES_CASE]

REQUIRED_DISCLAIMERS = [
    ("DISC-001", r"pode conter erros", "Aviso 'pode conter erros' ausente."),
    ("DISC-002", r"n[aã]o substitui\s+(a\s+)?avalia[cç][aã]o\s+m[eé]dica", "Aviso 'não substitui avaliação médica' ausente."),
    ("DISC-003", r"\b192\b", "Aviso de emergência (192) ausente."),
]


# ----------------------------------------------------------------------------- utils
def route_of(rel):
    rel = rel.replace(os.sep, "/")
    if rel == "404.html":
        return "/404.html"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    if rel == "index.html":
        return "/"
    if rel.endswith(".html"):
        return "/" + rel[:-5] + "/"
    return "/" + rel


def norm_url(u):
    p = urllib.parse.urlsplit(u)
    path = p.path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return f"{p.scheme}://{p.netloc}{path}".lower()


def host_of(u):
    return urllib.parse.urlsplit(u).netloc.lower()


class Report:
    def __init__(self, ignore):
        self.items = []
        self.ignore = set(ignore)

    def add(self, sev, where, code, msg):
        if code in self.ignore:
            return
        self.items.append({"severity": sev, "where": where, "code": code, "message": msg})

    def counts(self):
        e = sum(1 for i in self.items if i["severity"] == ERROR)
        w = sum(1 for i in self.items if i["severity"] == WARN)
        return e, w


# ----------------------------------------------------------------------------- análise de uma página
def analyze(html, route, args, rep, site_host, seen, is_live=False):
    p = Page()
    try:
        p.feed(html)
    except Exception as exc:  # HTML muito quebrado
        rep.add(ERROR, route, "HTML-000", f"HTML inválido para o parser: {exc}")
        return p

    noindex_expected = route in args.noindex or route == "/404.html"
    robots = (p.meta("robots") or "").lower()
    has_noindex = "noindex" in robots
    text = p.visible_text()

    # --- conteúdo real (detecta shell de SPA)
    min_chars = args.min_chars if not noindex_expected else 30
    if len(text) < min_chars:
        rep.add(ERROR, route, "SEO-001",
                f"Só {len(text)} caracteres de texto no HTML (mín. {min_chars}). Provável página renderizada apenas no navegador (SPA sem pré-renderização).")

    if not (p.lang or "").lower().startswith("pt-br"):
        rep.add(ERROR, route, "SEO-002", f'<html lang> deve ser "pt-BR" (encontrado: {p.lang!r}).')

    # --- indexação
    if noindex_expected and not has_noindex and route != "/404.html":
        rep.add(ERROR, route, "SEO-003", "Página deveria ter <meta name=robots content=noindex>.")
    if not noindex_expected and has_noindex:
        rep.add(ERROR, route, "SEO-004", "Página indexável com noindex (bloqueia o Google).")

    # --- title / description
    title = re.sub(r"\s+", " ", p.title).strip()
    desc = (p.meta("description") or "").strip()
    if not title:
        rep.add(ERROR, route, "SEO-010", "<title> ausente.")
    else:
        if not 10 <= len(title) <= 65:
            rep.add(WARN, route, "SEO-011", f"<title> com {len(title)} caracteres (ideal 10–65).")
        seen["title"][title].append(route)
    if not desc:
        if not noindex_expected:
            rep.add(ERROR, route, "SEO-012", "meta description ausente.")
    else:
        if not 50 <= len(desc) <= 165:
            rep.add(WARN, route, "SEO-013", f"meta description com {len(desc)} caracteres (ideal 50–165).")
        seen["desc"][desc].append(route)
    if p.meta("keywords"):
        rep.add(WARN, route, "SEO-014", "meta keywords é obsoleta (ignorada pelo Google); remover.")

    # --- canonical
    canon = p.link("canonical")
    if not noindex_expected:
        if not canon:
            rep.add(ERROR, route, "SEO-020", "link rel=canonical ausente.")
        else:
            if not canon.startswith("http"):
                rep.add(ERROR, route, "SEO-021", f"canonical deve ser URL absoluta (encontrado: {canon}).")
            elif host_of(canon) != site_host:
                rep.add(ERROR, route, "SEO-022", f"canonical aponta para OUTRO domínio: {canon}")
            else:
                expected = norm_url(args.site_url.rstrip("/") + route)
                if norm_url(canon) != expected:
                    rep.add(ERROR, route, "SEO-023", f"canonical ({canon}) difere da URL da página ({expected}).")

    # --- H1
    if p.h1 != 1 and not (route == "/404.html" and p.h1 >= 1):
        rep.add(ERROR, route, "SEO-030", f"Deve haver exatamente 1 <h1> (encontrados: {p.h1}).")

    # --- Open Graph / Twitter
    if not noindex_expected:
        for k in ("og:title", "og:description", "og:image", "og:url", "og:type"):
            if not p.meta(k):
                rep.add(WARN, route, "SEO-040", f"Meta {k} ausente.")
        if not p.meta("twitter:card"):
            rep.add(WARN, route, "SEO-041", "Meta twitter:card ausente.")
        for k in ("og:image", "twitter:image", "og:url"):
            v = p.meta(k)
            if v and v.startswith("http") and host_of(v) != site_host:
                rep.add(ERROR, route, "SEO-042", f"{k} aponta para outro domínio: {v}")
        ogu, canon_ = p.meta("og:url"), canon
        if ogu and canon_ and norm_url(ogu) != norm_url(canon_):
            rep.add(WARN, route, "SEO-043", "og:url difere do canonical.")

    # --- imagens
    for im in p.imgs:
        if "alt" not in im:
            rep.add(ERROR, route, "IMG-001", f"<img> sem atributo alt: {im.get('src', '')[:80]}")
        if not (im.get("width") and im.get("height")) and not im.get("src", "").startswith("data:"):
            rep.add(WARN, route, "IMG-002", f"<img> sem width/height (risco de CLS): {im.get('src', '')[:80]}")

    # --- recursos externos / conteúdo misto / impressões digitais de gerador
    allowed = {site_host, "www." + site_host, ""} | {h.lower() for h in args.allow_host}
    for tag, url in p.resources:
        u = url.strip()
        if u.startswith("data:") or u.startswith("blob:"):
            continue
        if u.startswith("http://"):
            rep.add(ERROR, route, "RES-001", f"Conteúdo misto (http): {tag} {u[:90]}")
        h = host_of(u) if (u.startswith("http") or u.startswith("//")) else ""
        if u.startswith("//"):
            h = urllib.parse.urlsplit("https:" + u).netloc.lower()
        if h and h not in allowed:
            sev = WARN if tag.startswith("link[preconnect") or tag.startswith("link[dns-prefetch") else ERROR
            rep.add(sev, route, "RES-002", f"Recurso externo não permitido ({tag}): {u[:100]}")
    for f in p.forms:
        act = f["action"].strip()
        if act.startswith("http"):
            h = host_of(act)
            if h not in allowed and h not in {x.lower() for x in args.allow_form_host}:
                rep.add(ERROR, route, "RES-003", f"Formulário envia dados para host não previsto: {act}")
    low = html.lower()
    hits = [fp for fp in GENERATOR_FINGERPRINTS if fp in low]
    if hits:
        in_res = any(fp in (u or "").lower() for _, u in p.resources for fp in hits)
        rep.add(ERROR if in_res else WARN, route, "GEN-001",
                f"Vestígio de ferramenta geradora no HTML: {', '.join(hits)} (metadado ou script herdado).")

    # --- links
    for a in p.anchors:
        if (a.get("target") or "").lower() == "_blank" and "noopener" not in (a.get("rel") or "").lower():
            rep.add(WARN, route, "LNK-001", f"target=_blank sem rel=noopener: {a.get('href', '')[:80]}")

    # --- JSON-LD
    types = set()
    for raw in p.jsonld:
        try:
            data = json.loads(raw)
        except Exception as exc:
            rep.add(ERROR, route, "LD-001", f"JSON-LD inválido: {exc}")
            continue
        stack = [data]
        while stack:
            d = stack.pop()
            if isinstance(d, list):
                stack.extend(d)
            elif isinstance(d, dict):
                t = d.get("@type")
                for tt in (t if isinstance(t, list) else [t]):
                    if tt:
                        types.add(tt)
                stack.extend(v for v in d.values() if isinstance(v, (dict, list)))
    bad = types & FORBIDDEN_JSONLD
    if bad:
        rep.add(ERROR, route, "LD-002", f"JSON-LD com tipo médico proibido: {sorted(bad)} (sugere finalidade médica).")
    if "Product" in types:
        rep.add(WARN, route, "LD-003", "Schema Product: não declarar oferta/preço/disponibilidade na fase 0.")
    if route == "/" and "Organization" not in types:
        rep.add(WARN, route, "LD-004", "Home sem JSON-LD Organization.")

    # --- formulários (ignora <form method=dialog>, que é só interface)
    real_forms = [f for f in p.forms if f.get("method") != "dialog"]
    for f in real_forms:
        names = [(i.get("name") or "").lower() for i in f["inputs"]]
        consent = [i for i in f["inputs"] if (i.get("type") or "").lower() == "checkbox" and "required" in i]
        if not consent:
            rep.add(WARN, route, "FRM-001", "Formulário sem checkbox de consentimento obrigatório.")
        if "website" not in names:
            rep.add(WARN, route, "FRM-002", "Formulário sem campo honeypot (name='website').")
        if any(i.get("type", "").lower() == "checkbox" and "checked" in i for i in f["inputs"]):
            rep.add(ERROR, route, "FRM-003", "Checkbox de consentimento pré-marcado (LGPD exige ação afirmativa).")
    if real_forms and not any("politica-de-privacidade" in (a.get("href") or "") for a in p.anchors):
        rep.add(WARN, route, "FRM-004", "Página com formulário sem link para a Política de Privacidade.")

    # --- copy (texto visível + alt + title + description)
    scan = " ".join([text, " ".join(p.alts), title, desc])
    if not is_live or True:
        for code, sev, rx, msg, neg in COMPILED:
            for m in rx.finditer(scan):
                if neg and negated(scan, m.start()):
                    continue
                ctx = scan[max(0, m.start() - 35): m.end() + 35].replace("\n", " ")
                rep.add(sev, route, code, f"{msg}  …{ctx}…")
                break
        for code, sev, rx, msg, neg in COMPILED_CASE:
            m = rx.search(scan)
            if m:
                ctx = scan[max(0, m.start() - 35): m.end() + 35]
                rep.add(sev, route, code, f"{msg}  …{ctx}…")
    if not noindex_expected and route != "/404.html":
        for code, rx, msg in REQUIRED_DISCLAIMERS:
            if not re.search(rx, text, re.I):
                rep.add(ERROR, route, code, msg)

    # --- pendências e número de teste
    pend = re.findall(r"\[PENDENTE[^\]]*\]", text)
    if pend:
        rep.add(ERROR if args.production else WARN, route, "PEND-001",
                f"{len(pend)} marcador(es) [PENDENTE…]: " + "; ".join(sorted(set(pend))[:4]) + ("…" if len(set(pend)) > 4 else ""))
    for n in TEST_NUMBERS:
        if n in html:
            rep.add(ERROR if args.production else WARN, route, "PEND-002", f"Número de WhatsApp de TESTE presente ({n}).")
            break
    return p


# ----------------------------------------------------------------------------- modo dist
def audit_dist(args, rep):
    dist = os.path.abspath(args.dist)
    if not os.path.isdir(dist):
        print(f"Pasta não encontrada: {dist}", file=sys.stderr)
        sys.exit(2)
    site_host = host_of(args.site_url)
    seen = {"title": defaultdict(list), "desc": defaultdict(list)}
    routes = {}
    for root, _, files in os.walk(dist):
        for fn in files:
            if fn.endswith(".html"):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, dist)
                routes[route_of(rel)] = full

    if not routes:
        rep.add(ERROR, "(site)", "SITE-000", "Nenhum arquivo .html encontrado no dist.")
        return routes, {}
    pages = {}
    for route, full in sorted(routes.items()):
        with open(full, encoding="utf-8", errors="replace") as f:
            html = f.read()
        pages[route] = analyze(html, route, args, rep, site_host, seen)

    for kind, code, label in (("title", "SEO-015", "<title>"), ("desc", "SEO-016", "meta description")):
        for val, rs in seen[kind].items():
            if len(rs) > 1:
                rep.add(ERROR, ", ".join(rs), code, f"{label} DUPLICADO em {len(rs)} páginas: '{val[:70]}'")

    # links internos
    def exists(path):
        path = urllib.parse.unquote(path)
        cands = [os.path.join(dist, path.lstrip("/"))]
        if path.endswith("/") or path == "":
            cands = [os.path.join(dist, path.lstrip("/"), "index.html")]
        else:
            cands += [os.path.join(dist, path.lstrip("/"), "index.html"), os.path.join(dist, path.lstrip("/") + ".html")]
        return any(os.path.isfile(c) for c in cands)

    for route, pg in pages.items():
        base = args.site_url.rstrip("/") + route
        for a in pg.anchors:
            href = (a.get("href") or "").strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#", "sms:")):
                continue
            absu = urllib.parse.urljoin(base, href)
            pu = urllib.parse.urlsplit(absu)
            if pu.netloc.lower() in (site_host, "www." + site_host):
                if not exists(pu.path or "/") and (pu.path or "/") not in args.allow_route:
                    rep.add(ERROR, route, "LNK-002", f"Link interno quebrado: {href}")
        for tag, url in pg.resources:
            if url.startswith("/") and not url.startswith("//"):
                if not os.path.isfile(os.path.join(dist, urllib.parse.unquote(urllib.parse.urlsplit(url).path).lstrip("/"))):
                    rep.add(ERROR, route, "RES-004", f"Arquivo referenciado não existe no dist ({tag}): {url[:90]}")

    # sitemap / robots / 404
    indexable = sorted(r for r in routes if r not in args.noindex and r != "/404.html"
                       and "noindex" not in (pages[r].meta("robots") or "").lower())
    sm = os.path.join(dist, "sitemap.xml")
    if not os.path.isfile(sm):
        rep.add(ERROR, "(site)", "MAP-001", "sitemap.xml ausente.")
    else:
        xml = open(sm, encoding="utf-8", errors="replace").read()
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", xml, re.S)
        locn = {norm_url(u) for u in locs}
        for r in indexable:
            if norm_url(args.site_url.rstrip("/") + r) not in locn:
                rep.add(ERROR, "(sitemap)", "MAP-002", f"Rota indexável fora do sitemap: {r}")
        for u in locs:
            if host_of(u) != site_host:
                rep.add(ERROR, "(sitemap)", "MAP-003", f"URL no sitemap com host errado: {u}")
            path = urllib.parse.urlsplit(u).path or "/"
            rr = path if path.endswith("/") else path + "/"
            if rr in args.noindex or path in args.noindex:
                rep.add(ERROR, "(sitemap)", "MAP-004", f"URL noindex presente no sitemap: {u}")
        if len(locs) != len(set(locs)):
            rep.add(WARN, "(sitemap)", "MAP-005", "URLs duplicadas no sitemap.")
    rb = os.path.join(dist, "robots.txt")
    if not os.path.isfile(rb):
        rep.add(ERROR, "(site)", "MAP-010", "robots.txt ausente.")
    else:
        txt = open(rb, encoding="utf-8", errors="replace").read()
        if "sitemap:" not in txt.lower():
            rep.add(ERROR, "(robots)", "MAP-011", "robots.txt sem linha Sitemap:.")
        if re.search(r"(?im)^\s*disallow:\s*/\s*$", txt):
            rep.add(ERROR if args.production else WARN, "(robots)", "MAP-012", "robots.txt bloqueia o site inteiro (Disallow: /).")
    if not os.path.isfile(os.path.join(dist, "404.html")):
        rep.add(ERROR, "(site)", "MAP-020", "404.html ausente (necessário para 404 real).")
    home = pages.get("/")
    if home is None:
        rep.add(ERROR, "(site)", "SITE-001", "Home (index.html) ausente.")
    else:
        if not home.link("icon"):
            rep.add(WARN, "/", "SEO-050", "Home sem link rel=icon.")

    # peso de JS/CSS
    heavy, total = [], 0
    for root, _, files in os.walk(dist):
        for fn in files:
            if fn.endswith((".js", ".mjs", ".css")):
                sz = os.path.getsize(os.path.join(root, fn))
                total += sz
                if sz > 250 * 1024:
                    heavy.append((fn, sz))
    for fn, sz in heavy:
        rep.add(WARN, "(peso)", "PERF-001", f"{fn} com {sz // 1024} KB (>250 KB).")
    if total > 500 * 1024:
        rep.add(WARN, "(peso)", "PERF-002", f"JS+CSS somam {total // 1024} KB (meta: <500 KB no total).")
    return routes, pages


# ----------------------------------------------------------------------------- modo live
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def fetch(url, follow=True, method="GET", timeout=20):
    opener = urllib.request.build_opener() if follow else urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, method=method, headers={"User-Agent": "VitalisAudit/1.0 (crawler sem JavaScript)"})
    try:
        with opener.open(req, timeout=timeout) as r:
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read() if method == "GET" else b""
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, (e.read() if method == "GET" else b"")
    except Exception as e:
        return None, {}, str(e).encode()


def audit_live(args, rep):
    base = args.live.rstrip("/")
    site_host = host_of(args.site_url)
    st, hd, body = fetch(base + "/sitemap.xml")
    routes = []
    if st == 200:
        routes = [urllib.parse.urlsplit(u).path or "/" for u in re.findall(r"<loc>\s*(.*?)\s*</loc>", body.decode("utf-8", "replace"), re.S)]
    else:
        rep.add(ERROR, "(site)", "MAP-001", f"sitemap.xml não respondeu 200 (status {st}).")
    if not routes:
        routes = ["/"]
    routes = sorted(set(routes) | {"/"})
    seen = {"title": defaultdict(list), "desc": defaultdict(list)}
    internal = set()
    for r in routes:
        st, hd, body = fetch(base + r)
        if st != 200:
            rep.add(ERROR, r, "HTTP-001", f"Status {st} (esperado 200).")
            continue
        if "html" not in (hd.get("Content-Type", "") + hd.get("content-type", "")).lower():
            rep.add(ERROR, r, "HTTP-002", "Content-Type não é HTML.")
        if "noindex" in (hd.get("X-Robots-Tag", "") or hd.get("x-robots-tag", "")).lower() and r not in args.noindex:
            rep.add(ERROR, r, "HTTP-003", "Cabeçalho X-Robots-Tag: noindex em página indexável.")
        pg = analyze(body.decode("utf-8", "replace"), r if r.endswith("/") else r + "/", args, rep, site_host, seen, is_live=True)
        for a in pg.anchors:
            h = (a.get("href") or "").strip()
            if h.startswith("/") and not h.startswith("//"):
                internal.add(urllib.parse.urlsplit(h).path)
    for kind, code, label in (("title", "SEO-015", "<title>"), ("desc", "SEO-016", "meta description")):
        for val, rs in seen[kind].items():
            if len(rs) > 1:
                rep.add(ERROR, ", ".join(rs), code, f"{label} DUPLICADO em {len(rs)} páginas: '{val[:70]}'")
    for path in sorted(internal)[:150]:
        st, _, _ = fetch(base + path, method="GET")
        if st is None or st >= 400:
            rep.add(ERROR, "(links)", "LNK-002", f"Link interno com status {st}: {path}")
    # 404 real
    st, _, _ = fetch(base + "/__vitalis-audit-404__")
    if st != 404:
        rep.add(ERROR, "(site)", "HTTP-010", f"URL inexistente devolveu {st} (esperado 404 real; 200 = soft 404 prejudica o SEO).")
    # https / www
    if base.startswith("https://"):
        st, hd, _ = fetch("http://" + host_of(base) + "/", follow=False)
        loc = hd.get("Location", "") or hd.get("location", "")
        if st not in (301, 308) or not loc.startswith("https://"):
            rep.add(ERROR, "(site)", "HTTP-011", f"http:// não redireciona 301 para https:// (status {st}).")
        st, hd, _ = fetch("https://www." + site_host.replace("www.", "") + "/", follow=False)
        if st is not None:
            loc = hd.get("Location", "") or hd.get("location", "")
            if st not in (301, 308) or host_of(loc) != site_host.replace("www.", ""):
                rep.add(WARN, "(site)", "HTTP-012", f"www não redireciona para o domínio canônico (status {st}).")
    st, hd, _ = fetch(base + "/")
    hl = {k.lower(): v for k, v in hd.items()}
    if "strict-transport-security" not in hl and base.startswith("https://"):
        rep.add(WARN, "(site)", "SEC-001", "Sem Strict-Transport-Security (HSTS).")
    if "x-content-type-options" not in hl:
        rep.add(WARN, "(site)", "SEC-002", "Sem X-Content-Type-Options: nosniff.")
    if hl.get("content-encoding", "") not in ("gzip", "br", "zstd"):
        rep.add(WARN, "(site)", "PERF-010", "Resposta HTML sem compressão (gzip/br).")


# ----------------------------------------------------------------------------- saída
def print_report(rep):
    order = {ERROR: 0, WARN: 1}
    items = sorted(rep.items, key=lambda i: (order[i["severity"]], i["where"], i["code"]))
    cur = None
    for i in items:
        if i["where"] != cur:
            cur = i["where"]
            print(f"\n■ {cur}")
        mark = "✖" if i["severity"] == ERROR else "!"
        print(f"  {mark} [{i['code']}] {i['message']}")
    e, w = rep.counts()
    print("\n" + "─" * 60)
    print(f"Resultado: {e} erro(s), {w} aviso(s).")
    if e:
        print("REPROVADO — corrija os ERROS antes de publicar.")
    else:
        print("APROVADO nas verificações automáticas (a revisão jurídica continua necessária).")


def main():
    # O PowerShell clássico pode anunciar cp1252 mesmo quando o projeto e o
    # terminal trabalham com UTF-8. Evita falha ao imprimir os símbolos do
    # relatório e mantém uma substituição segura em consoles mais antigos.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Auditoria do site Vitalis Ring (SEO técnico, copy regulatória, pendências).")
    ap.add_argument("--dist", help="pasta do build (ex.: ./dist)")
    ap.add_argument("--live", help="URL do site publicado (ex.: https://vitalisring.com.br)")
    ap.add_argument("--site-url", default=DEFAULT_SITE, help=f"URL canônica (padrão {DEFAULT_SITE})")
    ap.add_argument("--production", action="store_true", help="pendências e número de teste viram ERRO")
    ap.add_argument("--noindex", nargs="*", default=DEFAULT_NOINDEX, help="rotas que devem ser noindex")
    ap.add_argument("--allow-host", nargs="*", default=[], help="hosts externos permitidos para scripts/estilos/imagens")
    ap.add_argument("--allow-form-host", nargs="*", default=None, help="hosts permitidos como destino de formulário")
    ap.add_argument("--allow-route", nargs="*", default=["/login"], help="rotas dinâmicas servidas pela aplicação")
    ap.add_argument("--ignore", nargs="*", default=[], help="códigos a ignorar (ex.: CLM-002)")
    ap.add_argument("--min-chars", type=int, default=400, help="mínimo de caracteres de texto no HTML")
    ap.add_argument("--json", help="grava relatório JSON neste caminho")
    args = ap.parse_args()
    if not args.dist and not args.live:
        ap.error("informe --dist e/ou --live")
    args.site_url = args.site_url.rstrip("/")
    if args.allow_form_host is None:
        args.allow_form_host = ["app." + host_of(args.site_url)]
    rep = Report(args.ignore)
    if args.dist:
        print(f"Auditando dist: {args.dist}")
        audit_dist(args, rep)
    if args.live:
        print(f"Auditando ao vivo (sem JS): {args.live}")
        audit_live(args, rep)
    print_report(rep)
    if args.json:
        e, w = rep.counts()
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"errors": e, "warnings": w, "items": rep.items}, f, ensure_ascii=False, indent=2)
        print(f"Relatório JSON: {args.json}")
    sys.exit(1 if rep.counts()[0] else 0)


if __name__ == "__main__":
    main()
