import sys
from playwright.sync_api import sync_playwright
url = "http://127.0.0.1:8100/"
out = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/pack/vitalis-site/shots"
import os; os.makedirs(out, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, w, h in (("d1440", 1440, 800), ("d1024", 1024, 768), ("m390", 390, 844)):
        ctx = b.new_context(viewport={"width": w, "height": h}); ctx.add_init_script("try{localStorage.setItem('vr_consent','{}')}catch(e){}"); pg = ctx.new_page()
        msgs = []
        pg.on("console", lambda m: msgs.append(m.text) if m.type in ("error","warning") else None)
        pg.on("requestfailed", lambda r: msgs.append("FAILED " + r.url))
        pg.goto(url); pg.wait_for_timeout(3200)
        # revelar tudo para a captura full-page
        pg.evaluate("document.querySelectorAll('.reveal').forEach(e=>e.classList.add('in'))"); pg.wait_for_timeout(900)
        pg.screenshot(path=f"{out}/{name}_top.png")
        pg.screenshot(path=f"{out}/{name}_full.png", full_page=True)
        sw = pg.evaluate("document.documentElement.scrollWidth")
        hdr = pg.evaluate("(()=>{const e=document.querySelector('.hdr');return [e.getBoundingClientRect().height, [...e.querySelectorAll('a,button')].filter(x=>x.offsetParent).map(x=>Math.round(x.getBoundingClientRect().height))]})()")
        print(name, "scrollWidth", sw, "hdr", hdr, "msgs", msgs[:3])
    b.close()
