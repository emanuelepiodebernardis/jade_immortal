// Jade Immortal — IL TELEFONO (Aggiornamento 85).
// Sul telefono il gioco diventa un'app a schermate, non una pagina lunghissima:
//   · «Oggi» è la schermata di GIOCO (altare, cosa fare, scena del luogo, registro, comando);
//   · gli altri palazzi (La Via, Setta, Seguaci, Mondo, Tesori, Storia, Opzioni) si aprono a SCHERMO INTERO,
//     con la loro intestazione in alto e il tasto «‹ Gioco» per tornare;
//   · se fai qualcosa da un pannello, l'esito sale dal basso in un foglio (non devi tornare al registro);
//   · se si apre una scena con delle scelte, il gioco ti riporta da solo alla schermata di gioco;
//   · nei pannelli si scorre tra le schede col dito (destra / sinistra);
//   · con la tastiera aperta la barra in basso si nasconde; un piccolo tocco di vibrazione conferma i pulsanti.
// Sul computer non cambia nulla.
"use strict";
(function () {
  const mq = window.matchMedia("(max-width: 700px)");
  const phone = () => mq.matches;
  const store = { get: (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* niente */ } } };
  let view = "game";
  const body = document.body;

  // ---------------------------------------------------------------- vibrazione
  const hapticOn = () => store.get("ji_haptic", "1") === "1";
  function haptic(ms) { if (phone() && hapticOn() && navigator.vibrate) { try { navigator.vibrate(ms || 8); } catch (e) { /* niente */ } } }

  // ---------------------------------------------------------------- le due schermate
  function palaceNow() { const b = document.querySelector("#rail [data-palace].on"); return b ? b.dataset.palace : "oggi"; }
  function sync() {
    const pan = phone() && view === "panel";
    body.classList.toggle("m-panel", pan);
    body.classList.toggle("m-game", phone() && !pan);
    body.dataset.pal = palaceNow();
  }
  function setView(v, scroll) {
    if (v === view) { sync(); return; }
    view = v; sync();
    if (scroll !== false) window.scrollTo(0, 0);
    if (v === "game") hideSheet();
  }
  // il palazzo attivo cambia: lo sappiamo osservando la barra
  new MutationObserver(sync).observe(document.getElementById("rail"), { subtree: true, attributes: true, attributeFilter: ["class"] });
  mq.addEventListener ? mq.addEventListener("change", sync) : mq.addListener(sync);

  document.addEventListener("click", (ev) => {
    if (!phone()) return;
    const rb = ev.target.closest("#rail [data-palace]");
    if (rb) {
      haptic();
      const p = rb.dataset.palace;
      if (p === "oggi") { setView("game"); return; }                       // l'app apre «Oggi» sotto il registro
      if (view === "panel" && rb.classList.contains("on")) {                // ritocchi il palazzo aperto: torni al gioco
        ev.stopPropagation(); ev.preventDefault(); setView("game"); return;
      }
      setView("panel"); return;
    }
    if (ev.target.closest("#m-back")) { ev.preventDefault(); haptic(); setView("game"); return; }
    // collegamenti dentro la pagina verso un palazzo («e altre 8 cose», «impostazioni», le schede…)
    const link = ev.target.closest("[data-ptab], [data-palace]");
    if (link && !link.closest("#rail") && !link.closest("#subnav")) {
      const p = (link.dataset.ptab || link.dataset.palace || "").split(":")[0];
      if (p === "oggi") { setView("game", false); setTimeout(() => { const s = document.getElementById("side"); if (s) s.scrollIntoView({ behavior: "smooth" }); }, 250); }
      else if (p) setView("panel");
    }
    if (ev.target.closest(".primary, #scene .choices button, .card-act, .todo-card, .stg-act, .stg-gate, .gh-go")) haptic(10);
  }, true);

  // una scena con delle scelte ha la precedenza: si torna al gioco
  let sceneWas = false;
  new MutationObserver(() => {
    const on = body.classList.contains("scene-on") || body.classList.contains("duel-on");
    if (on && !sceneWas && phone() && view === "panel") {
      setView("game", false);
      setTimeout(() => { const s = document.getElementById("scene"); if (s && !s.hidden) s.scrollIntoView({ block: "start", behavior: "smooth" }); }, 200);
    }
    sceneWas = on;
  }).observe(body, { attributes: true, attributeFilter: ["class"] });

  // ---------------------------------------------------------------- l'esito dal basso
  let sheet = null, sheetT = null;
  function ensureSheet() {
    if (sheet) return sheet;
    sheet = document.createElement("div");
    sheet.id = "m-sheet"; sheet.hidden = true; sheet.setAttribute("role", "status");
    sheet.innerHTML = `<div class="ms-grip"></div><div class="ms-b"></div>
      <div class="ms-f"><button type="button" data-ms="game">Vai al gioco</button><button type="button" class="primary" data-ms="x">Ok</button></div>`;
    document.body.appendChild(sheet);
    sheet.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-ms]"); if (!b) return;
      if (b.dataset.ms === "game") setView("game"); else hideSheet();
    });
    let y0 = null;                                                           // trascina giù per chiudere
    sheet.addEventListener("touchstart", (e) => { y0 = e.touches[0].clientY; }, { passive: true });
    sheet.addEventListener("touchend", (e) => { if (y0 !== null && e.changedTouches[0].clientY - y0 > 60) hideSheet(); y0 = null; }, { passive: true });
    return sheet;
  }
  function hideSheet() { if (sheet) { sheet.classList.remove("in"); clearTimeout(sheetT); sheetT = setTimeout(() => { if (sheet) sheet.hidden = true; }, 250); } }
  function onLog(div) {
    if (!phone() || view !== "panel" || !div) return;
    const lines = [...div.querySelectorAll(".ln")].filter((l) => !l.classList.contains("rep") && !l.closest(".lnfold") && l.textContent.trim());
    if (!lines.length) return;
    const s = ensureSheet();
    const b = s.querySelector(".ms-b");
    b.innerHTML = lines.slice(0, 14).map((l) => `<div class="${l.className.replace(/\bwait\b/, "")}">${l.innerHTML}</div>`).join("")
      + (lines.length > 14 ? `<div class="muted small">… e altre ${lines.length - 14} righe nel registro.</div>` : "");
    clearTimeout(sheetT); s.hidden = false; requestAnimationFrame(() => s.classList.add("in"));
  }

  // ---------------------------------------------------------------- scorrere tra le schede
  let t0 = null;
  document.addEventListener("touchstart", (e) => {
    if (!phone() || view !== "panel" || e.touches.length !== 1) { t0 = null; return; }
    const el = e.target;
    if (!el.closest || !el.closest("#tabbody") || el.closest("svg, canvas, input, select, textarea, table, .noswipe, #map")) { t0 = null; return; }
    for (let n = el; n && n.id !== "tabbody"; n = n.parentElement) if (n.scrollWidth > n.clientWidth + 4 && getComputedStyle(n).overflowX !== "visible") { t0 = null; return; }
    t0 = { x: e.touches[0].clientX, y: e.touches[0].clientY, t: Date.now() };
  }, { passive: true });
  document.addEventListener("touchend", (e) => {
    if (!t0) return;
    const dx = e.changedTouches[0].clientX - t0.x, dy = e.changedTouches[0].clientY - t0.y, dt = Date.now() - t0.t;
    t0 = null;
    if (Math.abs(dx) < 70 || Math.abs(dy) > 45 || dt > 600) return;
    const chips = [...document.querySelectorAll("#subnav [data-ptab]")];
    const i = chips.findIndex((c) => c.classList.contains("on"));
    const nx = chips[i + (dx < 0 ? 1 : -1)];
    if (nx) { haptic(6); nx.click(); nx.scrollIntoView({ inline: "center", block: "nearest" }); body.classList.add(dx < 0 ? "m-swl" : "m-swr"); setTimeout(() => body.classList.remove("m-swl", "m-swr"), 300); }
  }, { passive: true });

  // ---------------------------------------------------------------- la tastiera
  document.addEventListener("focusin", (e) => { if (phone() && e.target.id === "cmd") body.classList.add("m-kb"); });
  document.addEventListener("focusout", (e) => { if (e.target.id === "cmd") setTimeout(() => body.classList.remove("m-kb"), 120); });

  // ---------------------------------------------------------------- il tasto «‹ Gioco» e i ritocchi
  function decorate() {
    const ph = document.getElementById("phead");
    if (ph && !document.getElementById("m-back")) {
      const b = document.createElement("button");
      b.id = "m-back"; b.type = "button"; b.setAttribute("aria-label", "Torna al gioco"); b.innerHTML = "‹ Gioco";
      ph.insertBefore(b, ph.firstChild);
    }
    const cmd = document.getElementById("cmd");
    if (cmd && phone()) cmd.placeholder = "Scrivi un comando… («help»)";
    const pop = document.getElementById("settings-pop");
    if (pop && !document.getElementById("hapticbtn")) {
      const b = document.createElement("button");
      b.id = "hapticbtn"; b.type = "button"; b.className = "m-only";
      b.innerHTML = `<span class="si">📳</span><span class="sl">Vibrazione al tocco (telefono)</span><em></em>`;
      pop.appendChild(b);
      const lab = () => { b.querySelector("em").textContent = hapticOn() ? "sì" : "no"; };
      lab();
      b.addEventListener("click", (e) => { e.stopPropagation(); store.set("ji_haptic", hapticOn() ? "0" : "1"); lab(); haptic(20); });
    }
    sync();
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", decorate); else decorate();
  mq.addEventListener ? mq.addEventListener("change", decorate) : mq.addListener(decorate);

  // la barra dei palazzi scorre: la sfumatura a destra dice che c'è altro, e sparisce in fondo
  const rail = document.getElementById("rail");
  if (rail) rail.addEventListener("scroll", () => rail.classList.toggle("end", rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 4), { passive: true });

  window.Phone = { phone, view: () => view, setView, onLog, haptic };
})();
