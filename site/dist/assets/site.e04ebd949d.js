/* Vitalis Ring — JS mínimo (sem bibliotecas): cabeçalho, menu, revelação, Dia/Noite, cookies */
(function () {
  "use strict";
  var d = document, root = d.documentElement;

  // cabeçalho: fundo ao rolar
  var header = d.querySelector(".site-header");
  function onScroll() { if (header) header.classList.toggle("scrolled", window.scrollY > 8); }
  onScroll(); window.addEventListener("scroll", onScroll, { passive: true });

  // menu móvel acessível
  var btn = d.querySelector(".menu-btn"), menu = d.getElementById("mobile-menu");
  function setMenu(open) {
    if (!btn || !menu) return;
    menu.hidden = !open;
    btn.setAttribute("aria-expanded", String(open));
    btn.setAttribute("aria-label", open ? "Fechar menu" : "Abrir menu");
    btn.firstElementChild.firstElementChild.setAttribute("href", open ? "#i-close" : "#i-menu");
    d.body.classList.toggle("menu-open", open);
    if (open) { var f = menu.querySelector("a"); if (f) f.focus(); } else { btn.focus(); }
  }
  if (btn && menu) {
    btn.addEventListener("click", function () { setMenu(menu.hidden); });
    d.addEventListener("keydown", function (e) { if (e.key === "Escape" && !menu.hidden) setMenu(false); });
    menu.addEventListener("click", function (e) { if (e.target.closest("a")) setMenu(false); });
    window.addEventListener("resize", function () { if (window.innerWidth >= 1024 && !menu.hidden) setMenu(false); });
  }

  // revelação ao rolar
  var items = d.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && items.length) {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { threshold: 0.15 });
    items.forEach(function (el, i) { el.style.transitionDelay = (i % 3) * 90 + "ms"; io.observe(el); });
  } else { items.forEach(function (el) { el.classList.add("in"); }); }

  // demonstração Dia | Noite
  var phone = d.getElementById("phone");
  d.querySelectorAll(".seg-btn").forEach(function (b) {
    b.addEventListener("click", function () {
      var mode = b.getAttribute("data-mode");
      if (phone) phone.setAttribute("data-mode", mode);
      d.querySelectorAll(".seg-btn").forEach(function (x) { x.setAttribute("aria-pressed", String(x === b)); });
    });
    b.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        var all = Array.prototype.slice.call(d.querySelectorAll(".seg-btn")), i = all.indexOf(b);
        var next = all[(i + (e.key === "ArrowRight" ? 1 : all.length - 1)) % all.length]; next.focus(); next.click();
      }
    });
  });

  // aviso e preferências de cookies (essenciais + medição sem cookies; marketing desativado)
  var KEY = "vr_consent", notice = d.getElementById("cookie-notice"), dlg = d.getElementById("cookie-prefs");
  function saved() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function save() { try { localStorage.setItem(KEY, JSON.stringify({ v: 1, marketing: false, t: Date.now() })); } catch (e) {} }
  if (notice && !saved()) notice.hidden = false;
  d.querySelectorAll("[data-cookie-accept]").forEach(function (b) {
    b.addEventListener("click", function () { save(); if (notice) notice.hidden = true; });
  });
  d.querySelectorAll("[data-cookie-prefs]").forEach(function (b) {
    b.addEventListener("click", function () { if (dlg && dlg.showModal) dlg.showModal(); });
  });
  // gancho para marketing: nada é carregado sem consentimento explícito (hoje não há recurso de marketing)
  window.loadMarketing = function () {};

  // lista de espera: máscara, validação, envio sem recarregar e tela de sucesso
  var wl = d.querySelector("[data-waitlist]");
  if (wl && window.fetch && window.FormData) {
    wl.noValidate = true;
    var phoneIn = wl.querySelector("[name=whatsapp]"), submit = wl.querySelector(".wl-submit"),
        status = wl.querySelector(".wl-form-status"), success = d.querySelector(".wl-success");
    var MSG = {
      nome: "Informe seu nome completo.",
      whatsapp: "Informe um celular com DDD, por exemplo (21) 98765-4321.",
      email: "Informe um e-mail válido.",
      objetivo: "Escolha o seu principal objetivo.",
      consentimento: "É preciso concordar com a Política de Privacidade."
    };
    phoneIn.addEventListener("input", function () {
      var v = phoneIn.value.replace(/\D/g, "").slice(0, 11), out = v;
      if (v.length > 2) out = "(" + v.slice(0, 2) + ") " + v.slice(2);
      if (v.length > 7) out = "(" + v.slice(0, 2) + ") " + v.slice(2, 7) + "-" + v.slice(7);
      phoneIn.value = out;
    });
    function showErrors(errs) {
      wl.querySelectorAll("[data-error-for]").forEach(function (p) {
        var k = p.getAttribute("data-error-for"), field = wl.querySelector("[name=" + k + "]");
        p.textContent = errs[k] || ""; p.hidden = !errs[k];
        if (field && field.type !== "radio") field.setAttribute("aria-invalid", String(!!errs[k]));
      });
      var first = Object.keys(MSG).filter(function (k) { return errs[k]; })[0];
      if (first) wl.querySelector("[name=" + first + "]").focus();
      return !first;
    }
    function check() {
      var f = new FormData(wl), e = {};
      var nome = String(f.get("nome") || "").trim();
      if (nome.length < 3 || nome.indexOf(" ") < 0) e.nome = MSG.nome;
      if (!/^[1-9][1-9]9\d{8}$/.test(String(f.get("whatsapp") || "").replace(/\D/g, ""))) e.whatsapp = MSG.whatsapp;
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(String(f.get("email") || "").trim())) e.email = MSG.email;
      if (!f.get("objetivo")) e.objetivo = MSG.objetivo;
      if (!f.get("consentimento")) e.consentimento = MSG.consentimento;
      return e;
    }
    function busy(on) { submit.disabled = on; submit.classList.toggle("is-loading", on); submit.setAttribute("aria-busy", String(on)); }
    wl.addEventListener("submit", function (ev) {
      ev.preventDefault();
      status.hidden = true;
      if (!showErrors(check())) return;
      busy(true);
      fetch(wl.action, { method: "POST", body: new FormData(wl), headers: { Accept: "application/json" } })
        .then(function (r) { return r.json().catch(function () { return { ok: false }; }); })
        .then(function (res) {
          if (res.ok) {
            wl.hidden = true; success.hidden = false; success.focus();
          } else {
            if (res.errors) showErrors(res.errors);
            status.textContent = res.message || "Não foi possível registrar agora. Tente novamente em instantes.";
            status.hidden = false;
          }
        })
        .catch(function () {
          status.textContent = "Sem conexão. Verifique sua internet e tente novamente.";
          status.hidden = false;
        })
        .then(function () { busy(false); });
    });
    var share = d.querySelector("[data-share]"), shareStatus = d.querySelector(".wl-share-status");
    if (share) share.addEventListener("click", function () {
      var data = { title: "Vitalis Ring", text: "Conheça o Vitalis Ring e entre na lista de espera:", url: location.origin + "/lista-de-espera/" };
      if (navigator.share) { navigator.share(data).catch(function () {}); return; }
      if (navigator.clipboard) navigator.clipboard.writeText(data.url).then(function () { shareStatus.textContent = "Link copiado."; });
    });
  }
})();
