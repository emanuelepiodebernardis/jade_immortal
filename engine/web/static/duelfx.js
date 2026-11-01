/* DuelFX — spettacolo dei duelli: cut-in delle tecniche, numeri del danno, hit-stop sui critici,
 * crepe nell'arena, sipario di vittoria / sconfitta.  Vanilla, nessuna dipendenza, mai lancia eccezioni.
 *
 *   DuelFX.turn(arenaEl, a, prev, opts?)   da chiamare dopo ogni scambio (dopo aver ridisegnato l'arena)
 *   DuelFX.enabled() / DuelFX.setEnabled(bool)     localStorage "ji_duelfx" (default: acceso)
 *   DuelFX.config   { numbers:true, cutin:true, cracks:true, banner:true }   interruttori fini
 *   DuelFX.reset()  dimentica crepe e dedup (nuovo duello)
 *   DuelFX.skip()   salta subito cut-in / sipario in corso
 *   DuelFX.PALETTE  colori degli elementi
 */
(function () {
  "use strict";
  const KEY = "ji_duelfx";
  const PAL = {
    fuoco: { n: "Fuoco", a: "#ff7a2a", b: "#c8281c", g: "#ffd08a", ink: "#fff1dc" },
    acqua: { n: "Acqua", a: "#3a9bff", b: "#1450b8", g: "#a5dcff", ink: "#e8f6ff" },
    fulmine: { n: "Fulmine", a: "#b58cff", b: "#5b34c9", g: "#f4eeff", ink: "#ffffff" },
    vento: { n: "Vento", a: "#58d68a", b: "#1f9a5c", g: "#c9ffe0", ink: "#effff6" },
    terra: { n: "Terra", a: "#c99a4a", b: "#7d5520", g: "#f0d79b", ink: "#fff6e2" },
    metallo: { n: "Metallo", a: "#cfd6df", b: "#7d8794", g: "#ffffff", ink: "#ffffff" },
    legno: { n: "Legno", a: "#6fcf5e", b: "#2f7a2e", g: "#d7ffc4", ink: "#f2ffe9" },
    luce: { n: "Luce", a: "#ffd75e", b: "#d49a14", g: "#fffbe0", ink: "#fffdf2" },
    oscurita: { n: "Oscurità", a: "#8a4fd0", b: "#1a0a2e", g: "#d3b0ff", ink: "#f1e6ff" },
    sangue: { n: "Sangue", a: "#e0334f", b: "#7c0f26", g: "#ffb3c0", ink: "#fff0f3" },
    default: { n: "", a: "#3fbf8f", b: "#14694c", g: "#b8ffe3", ink: "#effff8" }
  };
  const ALIAS = { spada: "metallo", sciabola: "metallo", lancia: "metallo", tuono: "fulmine", ombra: "oscurita", buio: "oscurita",
    massacro: "sangue", ghiaccio: "acqua", tenebra: "oscurita", tenebre: "oscurita", oscurita: "oscurita" };
  const BASIC = { colpisci: 1, attacca: 1, attacco: 1, difendi: 1, concentrati: 1, pillola: 1, fuggi: 1 };
  const CFG = { numbers: true, cutin: true, cracks: true, banner: true };
  const REDUCED = () => { try { return matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; } };

  let on = true;
  try { on = localStorage.getItem(KEY) !== "0"; } catch (e) {}
  const enabled = () => on;
  function setEnabled(v) { on = !!v; try { localStorage.setItem(KEY, on ? "1" : "0"); } catch (e) {} if (!on) skip(); }

  // ---------- stato del duello corrente ----------
  let duelId = null, lastTurno = -1, lastKey = null, cracks = [], doneShown = null;
  let timers = [], host = null, skipFn = null;
  const later = (ms, fn) => { const t = setTimeout(() => { try { fn(); } catch (e) { console.error(e); } }, ms); timers.push(t); return t; };

  const norm = (s) => String(s == null ? "" : s).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z]/g, "");
  function pal(el) { const k = norm(el); return PAL[k] || PAL[ALIAS[k]] || PAL.default; }
  const fmt = (n) => Number(n || 0).toLocaleString("it-IT");
  const hash = (s) => { let h = 2166136261; for (const c of String(s)) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  function rng(seed) { let s = seed >>> 0 || 1; return () => ((s = Math.imul(s ^ (s >>> 15), 2246822507) + 0x9e3779b9 >>> 0) / 4294967296); }
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const css = (el, o) => { for (const k in o) el.style.setProperty(k, o[k]); return el; };
  function mk(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  // ---------- host fisso, allineato all'arena (sopravvive a un ridisegno dell'arena) ----------
  function mkHost(arenaEl) {
    killHost();
    const r = arenaEl.getBoundingClientRect();
    host = mk("div", "dfx-host");
    css(host, { left: r.left + "px", top: r.top + "px", width: r.width + "px", height: r.height + "px" });
    document.body.appendChild(host);
    return host;
  }
  function killHost() { if (host) { host.remove(); host = null; } skipFn = null; }
  function skip() { try { if (skipFn) skipFn(); } catch (e) {} }

  function side(root, which) { return root.querySelector(".fighter." + which); }
  function relBox(el, h) {
    const r = el.getBoundingClientRect(), hr = h.getBoundingClientRect();
    return { x: r.left - hr.left, y: r.top - hr.top, w: r.width, h: r.height, cx: r.left - hr.left + r.width / 2, cy: r.top - hr.top + r.height / 2 };
  }

  // ---------- (1) CUT-IN ----------
  function cutIn(root, h, who, title, kicker, el, done) {
    const P = pal(el);
    const f = side(root, who);
    const img = f && f.querySelector("img.portrait, img");
    let face;
    if (img) { face = img.cloneNode(false); face.removeAttribute("loading"); face.removeAttribute("width"); face.removeAttribute("height"); face.className = "dfx-face-img"; }
    else if (f && f.querySelector("svg")) { face = f.querySelector("svg").cloneNode(true); face.setAttribute("class", "dfx-face-img"); face.removeAttribute("width"); face.removeAttribute("height"); }
    else face = mk("span", "dfx-face-img dfx-face-none", who === "me" ? "道" : "敵");
    const band = mk("div", "dfx-cut dfx-" + who);
    css(band, { "--c1": P.a, "--c2": P.b, "--cg": P.g, "--ci": P.ink });
    const fw = mk("div", "dfx-face"); fw.appendChild(face);
    const body = mk("div", "dfx-cut-body",
      `<small class="dfx-kick">${esc(kicker)}${P.n ? ` <i>·</i> ${esc(P.n)}` : ""}</small>` +
      `<b class="dfx-title">${esc(title)}</b>`);
    band.innerHTML = `<div class="dfx-cut-bg"></div><svg class="dfx-brush" viewBox="0 0 1000 120" preserveAspectRatio="none" aria-hidden="true">
      <defs><linearGradient id="dfxg-${who}" x1="0" x2="1"><stop offset="0" stop-color="${P.b}" stop-opacity="0"/><stop offset=".12" stop-color="${P.b}"/><stop offset=".55" stop-color="${P.a}"/><stop offset=".92" stop-color="${P.g}" stop-opacity=".85"/><stop offset="1" stop-color="${P.g}" stop-opacity="0"/></linearGradient></defs>
      <path d="M0 62 C60 30 140 70 230 48 C340 22 430 74 560 52 C690 30 790 66 880 44 C930 34 970 50 1000 40 L1000 84 C960 94 920 74 860 90 C760 112 680 72 560 94 C440 114 340 74 230 98 C140 116 60 84 0 96 Z" fill="url(#dfxg-${who})"/>
      <path d="M20 58 C120 42 220 66 330 52 M560 56 C680 40 790 64 900 50" stroke="${P.g}" stroke-opacity=".5" stroke-width="2" fill="none" stroke-linecap="round"/></svg>
      <div class="dfx-rays"></div>`;
    band.appendChild(fw); band.appendChild(body);
    h.appendChild(band);
    try { const t = body.querySelector(".dfx-title"); let sz = parseFloat(getComputedStyle(t).fontSize); while (t.scrollWidth > t.clientWidth + 1 && sz > 18) { sz -= 2; t.style.fontSize = sz + "px"; } } catch (e) {}
    let ended = false;
    const end = () => {
      if (ended) return; ended = true; band.classList.add("out");
      later(200, () => { band.remove(); });
      done && done();
    };
    band.addEventListener("click", (e) => { e.stopPropagation(); end(); });
    skipFn = end;
    later(1020, end);
    return band;
  }

  // ---------- (2) numeri del danno ----------
  function number(h, root, who, val, o) {
    const f = side(root, who); if (!f) return;
    const pic = f.querySelector("img.portrait, img, svg") || f;
    const b = relBox(pic, h);
    const P = pal(o.el);
    const n = mk("div", "dfx-num dfx-fx" + (o.crit ? " crit" : "") + (who === "me" ? " taken" : ""));
    css(n, { left: b.cx + "px", top: Math.max(8, b.cy - 14) + "px", "--c1": P.a, "--cg": P.g });
    n.innerHTML = `<span class="dfx-n">−${fmt(val)}</span>` +
      (o.crit ? `<em class="dfx-lab crit">Colpo critico</em>` : "") +
      (o.super ? `<em class="dfx-lab sup">Superefficace!</em>` : "");
    h.appendChild(n);
    try { const w = n.offsetWidth / 2 + 6, W = h.clientWidth; const x = Math.max(w, Math.min(W - w, b.cx)); n.style.left = x + "px"; } catch (e) {}
    later(o.crit ? 2000 : 1500, () => n.remove());
  }

  // ---------- (3) hit-stop / flash / scossa ----------
  function hitStop(root, h, strong) {
    if (REDUCED()) { flash(h, 0.35); return; }
    root.classList.add("dfx-freeze");
    flash(h, strong ? 0.85 : 0.5);
    later(250, () => {
      root.classList.remove("dfx-freeze");
      root.classList.remove("dfx-shake"); void root.offsetWidth; root.classList.add("dfx-shake");
      later(520, () => root.classList.remove("dfx-shake"));
    });
  }
  function flash(h, a) {
    const f = mk("div", "dfx-flash"); f.style.setProperty("--a", a); h.appendChild(f);
    later(520, () => f.remove());
  }

  // ---------- (4) crepe e polvere ----------
  function crackSvg(c, animate) {
    // c: {x,y,seed,w,h} — origine in frazione dell'arena; ramificazioni a spezzata in pixel reali
    const R = rng(c.seed), W = c.w, H = c.h, ox = c.x * W, oy = c.y * H, paths = [], f = (v) => v.toFixed(0);
    const arms = 5 + Math.floor(R() * 3);
    for (let i = 0; i < arms; i++) {
      let a = (i / arms) * Math.PI * 2 + (R() - 0.5) * 0.7, x = ox, y = oy, d = `M${f(ox)} ${f(oy)}`;
      const segs = 3 + Math.floor(R() * 3); let len = 16 + R() * 26;
      for (let s = 0; s < segs; s++) {
        a += (R() - 0.5) * 1.0; x += Math.cos(a) * len; y += Math.sin(a) * len; d += ` L${f(x)} ${f(y)}`;
        if (R() < 0.3) { const b = a + (R() < 0.5 ? -1 : 1) * (0.6 + R() * 0.5), l2 = len * (0.7 + R() * 0.8); paths.push(`M${f(x)} ${f(y)} L${f(x + Math.cos(b) * l2)} ${f(y + Math.sin(b) * l2)}`); }
        len *= 0.85;
      }
      paths.push(d);
    }
    const g = paths.map((d, i) => `<path d="${d}" pathLength="1" style="${animate ? `animation-delay:${(i % 6) * 30}ms` : ""}"/>`).join("");
    return `<svg class="dfx-crack${animate ? " grow" : ""}" viewBox="0 0 ${f(W)} ${f(H)}" preserveAspectRatio="none" aria-hidden="true"><g class="lo">${g}</g><g class="hi">${g}</g></svg>`;
  }
  function layer(root) {
    let l = root.querySelector(":scope > .dfx-cracks");
    if (!l) { l = mk("div", "dfx-cracks"); root.insertBefore(l, root.firstChild); }
    return l;
  }
  function syncCracks(root, newOne) {
    if (!CFG.cracks) return;
    const l = layer(root);
    l.innerHTML = cracks.map((c, i) => crackSvg(c, newOne && i === cracks.length - 1)).join("");
  }
  function dust(h, x, y) {
    if (REDUCED()) return;
    const R = rng((Math.random() * 1e9) | 0);
    for (let i = 0; i < 9; i++) {
      const p = mk("i", "dfx-dust dfx-fx");
      const s = 18 + R() * 34, dx = (R() - 0.5) * 150, dy = -(18 + R() * 56);
      css(p, { left: x + (R() - 0.5) * 50 + "px", top: y + (R() - 0.2) * 24 + "px", width: s + "px", height: s + "px", "--dx": dx + "px", "--dy": dy + "px" });
      p.style.animationDelay = Math.floor(R() * 110) + "ms";
      h.appendChild(p); later(1500, () => p.remove());
    }
    for (let i = 0; i < 7; i++) {
      const p = mk("i", "dfx-chip dfx-fx");
      css(p, { left: x + "px", top: y + "px", "--dx": (R() - 0.5) * 220 + "px", "--dy": -(30 + R() * 90) + "px", "--r": (R() * 540 - 270) + "deg", width: 3 + R() * 5 + "px", height: 3 + R() * 5 + "px" });
      h.appendChild(p); later(1000, () => p.remove());
    }
  }
  function envDamage(root, h, who) {
    if (!CFG.cracks) return;
    const f = side(root, who); if (!f) return;
    const ar = root.getBoundingClientRect(), b = relBox(f, h);
    const px = Math.max(0.08, Math.min(0.92, (b.cx + (who === "foe" ? -30 : 30)) / ar.width));
    const py = Math.max(0.2, Math.min(0.8, (b.cy + 20) / ar.height));
    const c = { x: px, y: py, seed: hash(duelId + "|" + cracks.length + "|" + lastTurno), w: ar.width, h: ar.height };
    if (cracks.length >= 3) cracks.shift();
    cracks.push(c);
    syncCracks(root, true);
    dust(h, b.cx, b.cy + b.h * 0.25);
  }

  // ---------- (5) vittoria / sconfitta ----------
  function banner(root, h, win) {
    const b = mk("div", "dfx-banner " + (win ? "win" : "lose"));
    b.innerHTML = `<div class="dfx-bn-bg"></div><div class="dfx-bn-in"><small>${win ? "il nemico è caduto" : "la tua via si spezza"}</small>
      <b>${win ? "Vittoria" : "Sconfitta"}</b><svg viewBox="0 0 400 24" preserveAspectRatio="none" aria-hidden="true"><path d="M2 14 C60 4 120 20 200 11 C280 3 340 18 398 8" pathLength="1"/></svg></div>`;
    h.appendChild(b);
    if (!win && !REDUCED()) root.classList.add("dfx-defeat");
    let ended = false;
    const end = () => { if (ended) return; ended = true; b.classList.add("out"); later(450, () => { b.remove(); root.classList.remove("dfx-defeat"); }); };
    b.style.pointerEvents = "auto"; b.addEventListener("click", end);
    skipFn = end;
    later(2600, end);
  }

  // ---------- ingresso ----------
  function turn(arenaEl, a, prev, opts) {
    try {
      opts = opts || {};
      if (!arenaEl || !a || !arenaEl.isConnected) return { played: false };
      // nuovo duello?
      const id = String(a.nome || "") + "|" + (a.lui && a.lui.max || 0);
      const fresh = duelId === null || id !== duelId || (a.turno != null && a.turno < lastTurno) || (!prev && !a.ultimo);
      if (fresh) { duelId = id; cracks = []; doneShown = null; lastKey = null; killHost(); timers.forEach(clearTimeout); timers = []; }
      lastTurno = a.turno != null ? a.turno : lastTurno;
      if (!on) return { played: false };
      syncCracks(arenaEl, false);
      const L = a.ultimo || {};
      const key = id + "|" + a.turno + "|" + JSON.stringify(L) + "|" + (a.finito ? 1 : 0);
      const same = key === lastKey; lastKey = key;
      if (same && !opts.force) return { played: false, dedup: true };
      // la prima volta che si vede un duello (ricarica pagina) non si rigioca nulla, salvo force
      if (!prev && !opts.force) return { played: false };
      if (!L.mossa) return { played: false };

      timers.forEach(clearTimeout); timers = [];
      const h = mkHost(arenaEl);
      const reduced = REDUCED();
      const el = L.el || (a.elementi && a.elementi.tu && a.elementi.tu[0]) || "";
      const tech = !!L.mossa && !BASIC[L.mossa];
      const dealt = Number(L.inflitto) || 0, taken = Number(L.subito) || 0;
      const crit = !!L.critico, critFoe = !!L.critico_lui;
      if (crit || critFoe) { try { if (window.Ambient && Ambient.cuesOn()) Ambient.cue("critico"); } catch (e) { /* niente */ } }   // (Agg. 84)
      const maxFoe = (a.lui && a.lui.max) || 1, maxMe = (a.tu && a.tu.max) || 1;

      let cut = null;
      if (CFG.cutin && (tech || crit || critFoe) && !(L.mossa === "difendi" || L.mossa === "fuggi" || L.mossa === "pillola" || L.mossa === "concentrati")) {
        if (tech || crit) {
          const t = L.nome || (crit ? "Colpo critico" : "Tecnica");
          cut = { who: "me", title: t, kicker: tech ? (L.mossa === "bestia" ? "Bestia spirituale" : "Tecnica") : "Colpo critico", el };
        } else cut = { who: "foe", title: a.nome || "Nemico", kicker: "Colpo devastante", el: (a.elementi && a.elementi.lui && a.elementi.lui[0]) || "" };
      }

      const impact = () => {
        if (CFG.numbers) {
          if (dealt > 0) number(h, arenaEl, "foe", dealt, { crit, super: L.eff === "super", el });
          if (taken > 0) number(h, arenaEl, "me", taken, { crit: critFoe, el: (a.elementi && a.elementi.lui && a.elementi.lui[0]) || "" });
        }
        if (crit || critFoe) hitStop(arenaEl, h, true);
        else if (dealt >= maxFoe * 0.5 || taken >= maxMe * 0.5) hitStop(arenaEl, h, false);
        if (dealt >= maxFoe * 0.3) envDamage(arenaEl, h, "foe");
        else if (taken >= maxMe * 0.3) envDamage(arenaEl, h, "me");
      };

      let end = 0;
      if (cut) { cutIn(arenaEl, h, cut.who, cut.title, cut.kicker, cut.el, () => later(40, impact)); end = 1020; }
      else { later(360, impact); end = 360; }

      if (a.finito && ((prev && !prev.finito) || opts.force) && doneShown !== id && CFG.banner) {
        doneShown = id;
        const win = !(a.tu && a.tu.hp <= 0);
        later(Math.max(end + 900, 1100), () => banner(arenaEl, h, win));
      }
      later(6000, () => { if (host === h) killHost(); });
      return { played: true, cutin: !!cut };
    } catch (e) { try { console.error("DuelFX", e); } catch (_) {} return { played: false, error: true }; }
  }

  function reset() { duelId = null; cracks = []; lastKey = null; doneShown = null; lastTurno = -1; killHost(); }

  window.DuelFX = { turn, enabled, setEnabled, config: CFG, reset, skip, PALETTE: PAL, _pal: pal };
})();
