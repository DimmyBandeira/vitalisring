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
})();
