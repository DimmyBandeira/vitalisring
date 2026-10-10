#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gerador estático do site Vitalis Ring: templates Jinja2 -> dist/<rota>/index.html
Uso: python build.py            (gera ./dist)
Variáveis: SITE_URL, APP_URL, WHATSAPP_NUMBER, WHATSAPP_MESSAGE"""
import hashlib, json, os, re, shutil, datetime, urllib.parse
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist")
PACK = os.environ.get("PACK_DIR", ROOT)
DEFAULT_SITE_URL = (
    "https://vitalisring.pages.dev"
    if os.environ.get("CF_PAGES") == "1"
    else "https://vitalisring.com.br"
)
SITE_URL = (os.environ.get("SITE_URL") or DEFAULT_SITE_URL).rstrip("/")
APP_URL = os.environ.get("APP_URL", "").rstrip("/")
SHOW_APP_LINK = bool(APP_URL) or os.environ.get("CF_PAGES") != "1"
WA_NUMBER = os.environ.get("WHATSAPP_NUMBER", "").strip()
WA_MSG = os.environ.get("WHATSAPP_MESSAGE", "Olá! Gostaria de saber mais sobre o Vitalis Ring.")
WA_LINK = f"https://wa.me/{WA_NUMBER}?text={urllib.parse.quote(WA_MSG)}" if WA_NUMBER else ""

NAV = [{"href": "/para-familias/", "label": "Famílias"}, {"href": "/para-medicos/", "label": "Médicos"},
       {"href": "/para-instituicoes/", "label": "Instituições"}, {"href": "/como-funciona/", "label": "Como funciona"}]
NAV_MOBILE = NAV + [{"href": "/perguntas-frequentes/", "label": "Perguntas frequentes"}]
FOOT_NAV = [{"href": "/", "label": "Início"}] + NAV + [{"href": "/perguntas-frequentes/", "label": "Perguntas frequentes"},
            {"href": "/seguranca-e-privacidade/", "label": "Segurança e privacidade"}]
FOOT_JOIN = [{"href": "/lista-de-espera/", "label": "Lista de espera"}, {"href": "/programa-piloto-medicos/", "label": "Programa piloto para médicos"},
             {"href": "/agendar-demonstracao/", "label": "Agendar demonstração"}, {"href": "/contato/", "label": "Contato"}]

PAGES = [
    {"route": "/", "template": "home.html", "title": "Vitalis Ring | Cuidado que conecta",
     "description": "Anel inteligente que acompanha o bem-estar de quem você ama e avisa a família quando algo sai do padrão. Entre na lista de espera.",
     "jsonld": True},
]

COMING_SOON_PAGES = [
    ("/para-familias/", "Para famílias"),
    ("/para-medicos/", "Para médicos"),
    ("/para-instituicoes/", "Para instituições"),
    ("/como-funciona/", "Como funciona"),
    ("/perguntas-frequentes/", "Perguntas frequentes"),
    ("/seguranca-e-privacidade/", "Segurança e privacidade"),
    ("/lista-de-espera/", "Lista de espera"),
    ("/agendar-demonstracao/", "Agendar demonstração"),
    ("/programa-piloto-medicos/", "Programa piloto para médicos"),
    ("/contato/", "Contato"),
    ("/termos-de-uso/", "Termos de Uso"),
    ("/politica-de-privacidade/", "Política de Privacidade"),
    ("/politica-de-cookies/", "Política de Cookies"),
]
PAGES.extend(
    {
        "route": route,
        "template": "coming_soon.html",
        "title": f"{label} | Vitalis Ring",
        "heading": label,
        "description": f"A página {label} do Vitalis Ring está em preparação.",
        "noindex": True,
    }
    for route, label in COMING_SOON_PAGES
)

def h(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()[:10]

def read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()

def normalize_html(content):
    """Evita espaços residuais produzidos por blocos Jinja condicionais."""
    return "\n".join(line.rstrip() for line in content.splitlines()) + "\n"

def main():
    shutil.rmtree(DIST, ignore_errors=True)
    # OneDrive pode recriar/segurar a pasta por alguns instantes. O build deve
    # continuar idempotente mesmo quando a remoção acima não for completa.
    os.makedirs(os.path.join(DIST, "assets", "logo"), exist_ok=True)
    # ativos de marca e fontes
    logo = os.path.join(PACK, "design", "logo")
    for fn in os.listdir(logo):
        src = os.path.join(logo, fn)
        if fn.startswith("logo-") and fn.endswith(".svg") or fn.startswith("simbolo-"):
            shutil.copy(src, os.path.join(DIST, "assets", "logo", fn))
        elif fn in ("favicon.ico", "favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "og-default.png", "site.webmanifest"):
            shutil.copy(src, os.path.join(DIST, fn))
    shutil.copytree(os.path.join(PACK, "design", "fonts"), os.path.join(DIST, "fonts"),
                    ignore=shutil.ignore_patterns("LICENSE*"), dirs_exist_ok=True)
    for fn in os.listdir(os.path.join(PACK, "design", "fonts")):
        if fn.startswith("LICENSE"):
            shutil.copy(os.path.join(PACK, "design", "fonts", fn), os.path.join(DIST, "fonts", fn.replace(".txt", "") + ".txt"))
    # imagem do hero (opcional): static/hero/anel-hero-1200.webp e -720.webp
    hero_image = None
    hero_dir = os.path.join(ROOT, "static", "hero")
    hero_w = hero_h = None
    if os.environ.get("HERO", "auto") != "svg" and os.path.isfile(os.path.join(hero_dir, "anel-hero-1200.webp")):
        os.makedirs(os.path.join(DIST, "hero"), exist_ok=True); [shutil.copy(os.path.join(hero_dir, f), os.path.join(DIST, "hero", f)) for f in os.listdir(hero_dir) if f.endswith(".webp")]; hero_image = "anel-hero"
        from PIL import Image
        with Image.open(os.path.join(hero_dir, "anel-hero-1200.webp")) as _im:
            hero_w, hero_h = _im.size
    # CSS/JS com hash no nome (cache imutável)
    css = read(os.path.join(PACK, "design", "tokens.css")) + "\n" + read(os.path.join(ROOT, "static", "css", "site.css"))
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s*\n\s*", "\n", css).strip()
    js = read(os.path.join(ROOT, "static", "js", "site.js"))
    ctmp, jtmp = os.path.join(DIST, "assets", "_c.css"), os.path.join(DIST, "assets", "_j.js")
    open(ctmp, "w", encoding="utf-8").write(css); open(jtmp, "w", encoding="utf-8").write(js)
    css_file, js_file = f"site.{h(ctmp)}.css", f"site.{h(jtmp)}.js"
    os.replace(ctmp, os.path.join(DIST, "assets", css_file)); os.replace(jtmp, os.path.join(DIST, "assets", js_file))

    env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "templates")), autoescape=select_autoescape(["html"]))
    m = re.search(r'width="(\d+)" height="(\d+)"', read(os.path.join(logo, "logo-horizontal-claro.svg"))[:400])
    logo_w = round(52 * int(m.group(1)) / int(m.group(2)))
    ring_svg = read(os.path.join(ROOT, "templates", "ring.svg.html"))
    ld = json.dumps({"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "name": "Vitalis Ring", "url": SITE_URL + "/", "logo": SITE_URL + "/icon-512.png"},
        {"@type": "WebSite", "name": "Vitalis Ring", "url": SITE_URL + "/", "inLanguage": "pt-BR"}]}, ensure_ascii=False)
    ctx = dict(site_url=SITE_URL, app_url=APP_URL, show_app_link=SHOW_APP_LINK, wa_link=WA_LINK, nav=NAV, nav_mobile=NAV_MOBILE, foot_nav=FOOT_NAV,
               foot_join=FOOT_JOIN, css_file=css_file, js_file=js_file, logo_w=logo_w, logo_h=52, year=datetime.date.today().year,
               hero_image=hero_image, hero_w=hero_w, hero_h=hero_h, ring_svg=ring_svg)
    for p in PAGES:
        out = os.path.join(DIST, p["route"].strip("/"), "index.html")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        html = normalize_html(env.get_template(p["template"]).render(page=p, jsonld=ld if p.get("jsonld") else None, **ctx))
        open(out, "w", encoding="utf-8").write(html)
    # 404 estático (caminhos absolutos)
    p404 = {"route": "/404.html", "title": "Página não encontrada | Vitalis Ring", "description": "A página que você procurou não existe ou mudou de endereço. Volte ao início do Vitalis Ring.", "noindex": True}
    open(os.path.join(DIST, "404.html"), "w", encoding="utf-8").write(normalize_html(env.get_template("404.html").render(page=p404, jsonld=None, **ctx)))
    # sitemap e robots
    urls = "".join(f"<url><loc>{SITE_URL}{p['route']}</loc></url>" for p in PAGES if not p.get("noindex"))
    open(os.path.join(DIST, "sitemap.xml"), "w", encoding="utf-8").write(
        f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    open(os.path.join(DIST, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    hta = os.path.join(PACK, "hosting", "htaccess.txt")
    if os.path.isfile(hta):
        shutil.copy(hta, os.path.join(DIST, ".htaccess"))
    cloudflare_headers = os.path.join(PACK, "hosting", "cloudflare-headers.txt")
    if os.path.isfile(cloudflare_headers):
        shutil.copy(cloudflare_headers, os.path.join(DIST, "_headers"))
    print("Build OK ->", DIST, "|", [p["route"] for p in PAGES], "| hero_image:", hero_image)

if __name__ == "__main__":
    main()
