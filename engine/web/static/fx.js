/* ============================================================================
   fx.js — motore di effetti visivi per Jade Immortal (stile xianxia a inchiostro)
   Un solo <canvas> fisso a tutto schermo per le particelle + WAAPI/CSS per gli elementi DOM.
   Nessuna libreria. Espone window.FX. Vedi fx.css per le classi.

   Interruttori: localStorage "ji_fx" === "0" spegne tutto; prefers-reduced-motion idem.
   ============================================================================ */
(function () {
  "use strict";

  // ---------------------------------------------------------------- stato / interruttori
  const LS_KEY = "ji_fx";
  let userOn = true;
  try { userOn = localStorage.getItem(LS_KEY) !== "0"; } catch (e) { /* storage bloccato: resta acceso */ }
  const mq = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;
  const reduced = () => !!(mq && mq.matches);
  const enabled = () => { if (!userOn || reduced()) return false; refreshMode(); return true; };
  window.addEventListener("storage", (e) => {
    if (e.key === LS_KEY) { userOn = e.newValue !== "0"; if (!userOn) clearAll(); }
  });
  function setEnabled(on) {
    userOn = !!on;
    try { localStorage.setItem(LS_KEY, on ? "1" : "0"); } catch (e) { /* ignora */ }
    if (!userOn) clearAll();
  }

  // ---------------------------------------------------------------- utilità
  const rand = (a, b) => a + Math.random() * (b - a);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const easeOut = (t) => 1 - Math.pow(1 - clamp(t, 0, 1), 3);
  const easeIn = (t) => { t = clamp(t, 0, 1); return t * t; };
  const fmt = (n) => Number(n).toLocaleString("it-IT");
  const isEl = (t) => !!t && t.nodeType === 1;
  const vw = () => window.innerWidth || document.documentElement.clientWidth || 800;
  const vh = () => window.innerHeight || document.documentElement.clientHeight || 600;

  // colori: accetta #hex, rgb(), nomi CSS e var(--x); restituisce [r,g,b]
  const colCache = {};
  let colProbe = null;
  function toRGB(c) {
    if (Array.isArray(c)) return c;
    c = String(c || "#3fbf8f").trim();
    if (colCache[c]) return colCache[c];
    let src = c;
    const m = /^var\((--[\w-]+)/.exec(c);
    if (m) src = getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim() || "#3fbf8f";
    let out = null;
    let h = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(src);
    if (h) {
      let s = h[1]; if (s.length === 3) s = s.replace(/./g, "$&$&");
      out = [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
    } else {
      const r = /rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/.exec(src);
      if (r) out = [+r[1], +r[2], +r[3]];
      else {                                   // nome CSS o altro: lo risolve il browser
        try {
          if (!colProbe) { colProbe = document.createElement("i"); colProbe.style.display = "none"; document.body.appendChild(colProbe); }
          colProbe.style.color = ""; colProbe.style.color = src;
          const rr = /rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/.exec(getComputedStyle(colProbe).color);
          if (rr) out = [+rr[1], +rr[2], +rr[3]];
        } catch (e) { /* ignora */ }
      }
    }
    out = out || [63, 191, 143];
    colCache[c] = out;
    return out;
  }
  const rgba = (rgb, a) => `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${a})`;
  const mix = (a, b, t) => [Math.round(a[0] + (b[0] - a[0]) * t), Math.round(a[1] + (b[1] - a[1]) * t), Math.round(a[2] + (b[2] - a[2]) * t)];
  let WHITE = [255, 255, 255];     // "bianco" dei riflessi: sul tema chiaro diventa inchiostro scuro
  let LM = false, lmT = 0;         // LM = tema chiaro: niente composizione additiva (sparirebbe sulla carta)
  function refreshMode() {
    const n = performance.now(); if (n - lmT < 400) return; lmT = n;
    let lm = true;
    try {
      const m = /rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/.exec(getComputedStyle(document.body).backgroundColor);
      if (m && (0.299 * m[1] + 0.587 * m[2] + 0.114 * m[3]) < 110) lm = false;
    } catch (e) { /* ignora */ }
    LM = lm; WHITE = lm ? [16, 26, 22] : [255, 255, 255];
  }
  const LC = () => (LM ? "source-over" : "lighter");
  const pal = (k) => {              // palette dell'elemento adattata al tema
    const E = elOf(k); let rgb = toRGB(E.c), c2 = toRGB(E.c2);
    if (LM) { c2 = mix(rgb, [8, 18, 14], 0.38); rgb = mix(rgb, [8, 18, 14], 0.04); }
    return { rgb, c2, st: E.st };
  };

  // colore dell'inchiostro: scuro sul tema chiaro, nebbia chiara sul tema scuro
  function inkRGB() {
    try {
      const m = /rgba?\(\s*(\d+)[ ,]+(\d+)[ ,]+(\d+)/.exec(getComputedStyle(document.body).backgroundColor);
      if (m && (0.299 * m[1] + 0.587 * m[2] + 0.114 * m[3]) < 110) return [150, 175, 165];
    } catch (e) { /* ignora */ }
    return [14, 22, 19];
  }

  // ---------------------------------------------------------------- elementi: palette e stile dei colpi
  // c = colore principale, c2 = riflesso chiaro, st = famiglia di effetti
  const EL = {
    fuoco:    { c: "#ff6a2a", c2: "#ffd27a", st: "ember" },
    acqua:    { c: "#3a9bf0", c2: "#c4e8ff", st: "drop" },
    legno:    { c: "#4caf50", c2: "#d0f5a6", st: "leaf" },
    metallo:  { c: "#c3ccd4", c2: "#ffffff", st: "shard" },
    terra:    { c: "#b8843a", c2: "#ecd096", st: "rock" },
    fulmine:  { c: "#a98bff", c2: "#ffffff", st: "bolt" },
    vento:    { c: "#3ec9b6", c2: "#dcfff8", st: "swirl" },
    luce:     { c: "#f2cf5b", c2: "#fff7d0", st: "star" },
    oscurita: { c: "#7b3fc0", c2: "#d9b8ff", st: "smoke" },
    abisso:   { c: "#5a2f96", c2: "#bfa0ee", st: "smoke" },
    spada:    { c: "#d6e4ee", c2: "#ffffff", st: "blade" },
    corpo:    { c: "#c47f3a", c2: "#ffdca8", st: "fist" },
    sangue:   { c: "#b0202a", c2: "#ff9a8a", st: "ember" },
    anima:    { c: "#d08fd8", c2: "#fbe3ff", st: "star" },
    nemico:   { c: "#c2392e", c2: "#ffb4a0", st: "blade" },   // colpo nemico senza elemento: cinabro
    "":       { c: "#3fbf8f", c2: "#d4ffe9", st: "blade" }      // predefinito: giada
  };
  const elOf = (k) => EL[k] || EL[""];
  const MELEE = { "": 1, spada: 1, corpo: 1 };

  // ---------------------------------------------------------------- canvas e particelle
  const MAX_PARTS = 650;
  let cv = null, ctx = null, W = 0, H = 0, dpr = 1, raf = 0, lastT = 0;
  const parts = [];
  const drawers = [];            // {draw(ctx, dt, t) -> bool}; false = finito
  const sprites = {};

  function ensureCanvas() {
    if (cv && cv.isConnected) return;
    cv = document.createElement("canvas");
    cv.className = "fx-canvas";
    cv.setAttribute("aria-hidden", "true");
    document.body.appendChild(cv);
    ctx = cv.getContext("2d");
    resize();
  }
  function resize() {
    if (!cv) return;
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    W = vw(); H = vh();
    cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
    cv.style.width = W + "px"; cv.style.height = H + "px";
  }
  window.addEventListener("resize", resize);

  function sprite(rgb) {          // alone morbido pre-disegnato: costa poco
    const k = (LM ? "L" : "D") + rgb.join(",");
    if (sprites[k]) return sprites[k];
    const s = document.createElement("canvas"); s.width = s.height = 64;
    const g = s.getContext("2d");
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, rgba(mix(rgb, WHITE, LM ? 0.3 : 0.85), 1));
    gr.addColorStop(0.22, rgba(mix(rgb, WHITE, LM ? 0.12 : 0.35), 0.9));
    gr.addColorStop(0.55, rgba(rgb, LM ? 0.4 : 0.32));
    gr.addColorStop(1, rgba(rgb, 0));
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    return (sprites[k] = s);
  }
  function inkSprite(rgb) {       // macchia d'inchiostro: bordo morbido, nucleo pieno
    const k = "i" + rgb.join(",");
    if (sprites[k]) return sprites[k];
    const s = document.createElement("canvas"); s.width = s.height = 64;
    const g = s.getContext("2d");
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, rgba(rgb, 0.95)); gr.addColorStop(0.5, rgba(rgb, 0.55)); gr.addColorStop(1, rgba(rgb, 0));
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    return (sprites[k] = s);
  }

  function P(o) {
    if (parts.length >= MAX_PARTS) return null;
    const p = Object.assign({ x: 0, y: 0, vx: 0, vy: 0, g: 0, drag: 0, life: 0.8, t: 0, delay: 0, a: 1, fp: 1,
      s0: 10, s1: 10, rot: 0, vr: 0, kind: "glow", comp: "lighter", rgb: [63, 191, 143], shape: "diamond", fin: 0.06 }, o);
    parts.push(p);
    kick();
    return p;
  }
  function D(fn) { drawers.push(fn); kick(); }

  function kick() {
    if (raf || !enabled()) return;
    ensureCanvas();
    cv.style.display = "block";
    lastT = performance.now();
    raf = requestAnimationFrame(loop);
  }

  function loop(now) {
    raf = 0;
    if (!ctx) return;
    const dt = Math.min(0.05, Math.max(0.001, (now - lastT) / 1000)); lastT = now;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    let comp = "";
    const setComp = (c) => { if (c === "lighter" && LM) c = "source-over"; if (c !== comp) { ctx.globalCompositeOperation = c; comp = c; } };

    for (let i = parts.length - 1; i >= 0; i--) {
      const p = parts[i];
      if (p.delay > 0) { p.delay -= dt; continue; }
      p.t += dt;
      if (p.t >= p.life) { parts[i] = parts[parts.length - 1]; parts.pop(); if (p.done) p.done(p); continue; }
      const pr = p.t / p.life;
      if (p.kind === "spiral") {                       // particelle che si avvolgono verso il bersaglio
        p.px = p.x; p.py = p.y;
        p.ang += p.w * dt;
        const rad = p.r0 * (1 - easeIn(pr * 1.02)) ;
        p.x = p.cx + Math.cos(p.ang) * rad;
        p.y = p.cy + Math.sin(p.ang) * rad * 0.72;
      } else {
        const d = Math.max(0, 1 - p.drag * dt);
        p.vx *= d; p.vy *= d; p.vy += p.g * dt;
        p.x += p.vx * dt; p.y += p.vy * dt;
        p.rot += p.vr * dt;
      }
      let a = p.a * Math.pow(1 - pr, p.fp);
      if (pr < p.fin) a *= pr / p.fin;
      if (a <= 0.003) continue;
      const s = p.s0 + (p.s1 - p.s0) * pr;
      switch (p.kind) {
        case "glow": {
          setComp(p.comp);
          ctx.globalAlpha = Math.min(1, LM && p.comp === "lighter" ? a * 1.5 : a);
          const sp = p.comp === "lighter" ? sprite(p.rgb) : inkSprite(p.rgb);
          ctx.drawImage(sp, p.x - s, p.y - s, s * 2, s * 2);
          break;
        }
        case "spark": {
          setComp("lighter");
          ctx.globalAlpha = Math.min(1, a);
          ctx.strokeStyle = rgba(p.rgb, 1);
          ctx.lineWidth = Math.max(0.6, s) * (LM ? 1.5 : 1);
          ctx.lineCap = "round";
          ctx.beginPath(); ctx.moveTo(p.x, p.y);
          ctx.lineTo(p.x - p.vx * 0.045, p.y - p.vy * 0.045); ctx.stroke();
          break;
        }
        case "spiral": {
          setComp("lighter");
          ctx.globalAlpha = Math.min(1, a);
          ctx.strokeStyle = rgba(p.rgb, 0.9); ctx.lineWidth = Math.max(1, s * 0.35); ctx.lineCap = "round";
          if (p.px != null) { ctx.beginPath(); ctx.moveTo(p.px, p.py); ctx.lineTo(p.x, p.y); ctx.stroke(); }
          ctx.drawImage(sprite(p.rgb), p.x - s, p.y - s, s * 2, s * 2);
          break;
        }
        case "ring": {
          setComp("lighter");
          const r = p.r0 + (p.r1 - p.r0) * easeOut(pr);
          ctx.globalAlpha = Math.min(1, a);
          ctx.strokeStyle = rgba(p.rgb, 1);
          ctx.lineWidth = Math.max(0.5, p.s0 * (1 - pr * 0.8)) * (LM ? 1.5 : 1);
          ctx.beginPath(); ctx.ellipse(p.x, p.y, r, r * (p.sq || 1), 0, 0, 6.2832); ctx.stroke();
          break;
        }
        case "shard": {
          setComp(p.comp);
          ctx.globalAlpha = Math.min(1, a);
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.rot);
          ctx.fillStyle = rgba(p.rgb, 1);
          ctx.beginPath();
          if (p.shape === "leaf") { ctx.ellipse(0, 0, s, s * 0.45, 0, 0, 6.2832); }
          else if (p.shape === "drop") { ctx.arc(0, 0, s * 0.55, 0, 6.2832); }
          else if (p.shape === "rock") { ctx.moveTo(-s, -s * 0.3); ctx.lineTo(-s * 0.2, -s * 0.9); ctx.lineTo(s * 0.8, -s * 0.4); ctx.lineTo(s * 0.6, s * 0.7); ctx.lineTo(-s * 0.6, s * 0.6); }
          else { ctx.moveTo(0, -s); ctx.lineTo(s * 0.45, 0); ctx.lineTo(0, s); ctx.lineTo(-s * 0.45, 0); }
          ctx.closePath(); ctx.fill();
          ctx.restore();
          break;
        }
        case "glyph": {
          setComp("lighter");
          ctx.globalAlpha = Math.min(1, a);
          ctx.fillStyle = rgba(p.rgb, 1);
          ctx.shadowColor = rgba(p.rgb, 0.9); ctx.shadowBlur = 12;
          ctx.font = `700 ${Math.round(s)}px "Songti SC","Noto Serif CJK SC","Noto Serif SC",serif`;
          ctx.textAlign = "center"; ctx.textBaseline = "middle";
          ctx.fillText(p.ch, p.x, p.y);
          ctx.shadowBlur = 0;
          break;
        }
      }
    }
    ctx.globalAlpha = 1;
    // disegnatori personalizzati (lampi, falci, proiettili…)
    for (let i = drawers.length - 1; i >= 0; i--) {
      const d = drawers[i];
      d.t = (d.t || 0) + dt;
      ctx.save(); ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over"; comp = "";
      let alive = true;
      try { alive = d.draw(ctx, dt, d.t); } catch (e) { alive = false; if (window.console) console.warn("FX draw:", e.message); }
      ctx.restore(); comp = "";
      if (!alive) { drawers.splice(i, 1); if (d.end) { try { d.end(); } catch (e) { /* ignora */ } } }
    }
    if (parts.length || drawers.length) raf = requestAnimationFrame(loop);
    else { ctx.clearRect(0, 0, W, H); cv.style.display = "none"; }   // inattivo: niente RAF, niente costo
  }

  function clearAll() {
    parts.length = 0; drawers.length = 0;
    if (raf) { cancelAnimationFrame(raf); raf = 0; }
    if (ctx) ctx.clearRect(0, 0, W, H);
    if (cv) cv.style.display = "none";
    document.querySelectorAll(".fx-float,.fx-flash,.fx-shield,.fx-ghost").forEach((n) => n.remove());
    document.querySelectorAll(".fx-aura").forEach((n) => n.classList.remove("fx-aura"));
    document.querySelectorAll(".fx-active").forEach((n) => n.classList.remove("fx-active"));
    timers.forEach(clearTimeout); timers.length = 0;
    endDrag(true);
  }

  // ---------------------------------------------------------------- geometria
  function pt(t) {
    if (isEl(t)) {
      let e = t;
      if (e.classList && e.classList.contains("fighter")) { const p = e.querySelector(".portrait, svg"); if (p) e = p; }
      const r = e.getBoundingClientRect();
      if (r.width || r.height) return { x: r.left + r.width / 2, y: r.top + r.height / 2, w: r.width, h: r.height, el: t, r };
    } else if (t && typeof t.x === "number") return { x: t.x, y: t.y, w: t.w || 0, h: t.h || 0 };
    return { x: vw() / 2, y: vh() / 3, w: 0, h: 0 };
  }

  // ---------------------------------------------------------------- lampo a schermo / scuotimento
  function screenFlash(color, alpha, ms) {
    if (!enabled()) return;
    const d = document.createElement("div");
    d.className = "fx-flash";
    if (LM) { d.style.mixBlendMode = "normal"; if (/^#f{3}|#fff$|rgba?\(2[0-9]{2}/i.test(color || "#fff")) { color = "#e8b53c"; alpha = (alpha || 0.4) * 0.55; } }
    d.style.background = color || "#fff";
    document.body.appendChild(d);
    const a = d.animate ? d.animate([{ opacity: alpha == null ? 0.5 : alpha }, { opacity: 0 }], { duration: ms || 380, easing: "ease-out" }) : null;
    if (a) a.onfinish = () => d.remove(); else setTimeout(() => d.remove(), ms || 380);
  }

  function shake(el, strength) {
    if (!enabled() || !isEl(el) || !el.animate) return;
    const k = 9 * (strength == null ? 1 : strength);
    const f = [0, -1, 0.85, -0.7, 0.5, -0.3, 0.15, 0].map((m, i) => ({ transform: `translate(${(m * k).toFixed(1)}px, ${(i % 2 ? -m : m) * k * 0.25}px)` }));
    try { el.animate(f, { duration: 380 + 120 * (strength || 1), easing: "ease-out", composite: "add" }); }
    catch (e) { el.animate(f, { duration: 420 }); }
  }

  function flashEl(el, ms) {         // il bersaglio "sbianca" per un attimo
    if (!isEl(el) || !el.animate) return;
    const t = (el.classList && el.classList.contains("fighter")) ? (el.querySelector(".portrait, svg") || el) : el;
    t.animate([{ filter: "brightness(2.6) saturate(.2)" }, { filter: "brightness(1.3)", offset: 0.4 }, { filter: "none" }], { duration: ms || 300, easing: "ease-out" });
  }

  // ---------------------------------------------------------------- testo fluttuante
  const floatRecent = [];
  function floatText(target, text, tone) {
    if (!enabled()) return null;
    tone = tone || "dmg";
    const p = pt(target);
    const el = document.createElement("div");
    el.className = "fx-float fx-t-" + tone;
    el.textContent = text;
    document.body.appendChild(el);
    const now = performance.now();
    while (floatRecent.length && now - floatRecent[0].t > 900) floatRecent.shift();
    let k = 0; for (const f of floatRecent) if (Math.abs(f.x - p.x) < 120 && Math.abs(f.y - p.y) < 90) k += f.big ? 1.7 : 1.1;
    const big = tone === "crit" || tone === "rare";
    floatRecent.push({ t: now, x: p.x, y: p.y, big });
    const hw = Math.min(vw() / 2 - 6, el.offsetWidth * (tone === "crit" ? 0.75 : 0.6) + 8);   // non esce mai dallo schermo
    const x = clamp(p.x + rand(-10, 10), hw, vw() - hw);
    const y = clamp(p.y - (p.h ? p.h * 0.32 : 0) - k * 40, 24, vh() - 10);
    el.style.left = x + "px"; el.style.top = y + "px";
    const crit = tone === "crit";
    const rise = { dmg: 74, crit: 100, heal: 64, gain: 70, qi: 50, rare: 76, bad: 64 }[tone] || 64;
    const dur = { crit: 1500, rare: 1700, gain: 1400, heal: 1400 }[tone] || 1200;
    const T = (dy, sc, rot) => `translate(-50%,-50%) translateY(${dy}px) scale(${sc})${rot ? ` rotate(${rot}deg)` : ""}`;
    const tilt = crit ? rand(-7, 7) : 0;
    const frames = crit
      ? [{ transform: T(8, 0.3, tilt), opacity: 0 }, { transform: T(0, 1.9, tilt), opacity: 1, offset: 0.12 }, { transform: T(-6, 1.45, tilt), opacity: 1, offset: 0.3 },
         { transform: T(-rise * 0.55, 1.4, tilt), opacity: 1, offset: 0.75 }, { transform: T(-rise, 1.3, tilt), opacity: 0 }]
      : tone === "qi" || tone === "heal"
        ? [{ transform: T(10, 0.8), opacity: 0 }, { transform: T(0, 1.05), opacity: 1, offset: 0.18 }, { transform: T(-rise * 0.6, 1), opacity: 1, offset: 0.7 }, { transform: T(-rise, 1), opacity: 0 }]
        : [{ transform: T(10, 0.5), opacity: 0 }, { transform: T(0, 1.3), opacity: 1, offset: 0.14 }, { transform: T(-8, 1), opacity: 1, offset: 0.28 },
           { transform: T(-rise * 0.6, 1), opacity: 1, offset: 0.72 }, { transform: T(-rise, 0.95), opacity: 0 }];
    if (el.animate) {
      const a = el.animate(frames, { duration: dur, easing: "cubic-bezier(.2,.8,.3,1)", fill: "forwards" });
      a.onfinish = () => el.remove();
    } else setTimeout(() => el.remove(), dur);
    if (crit && isEl(target)) shake(target, 1.3);
    return el;
  }

  // ---------------------------------------------------------------- primitive a particelle
  function burst(target, color, n) {
    if (!enabled()) return;
    const p = pt(target), rgb = toRGB(color), c2 = mix(rgb, WHITE, 0.55);
    n = clamp(n == null ? 24 : n, 1, 140);
    P({ x: p.x, y: p.y, s0: 6, s1: 46, life: 0.35, a: 0.8, rgb, fp: 1.5 });
    for (let i = 0; i < n; i++) {
      const an = rand(0, 6.2832), sp = rand(80, 340);
      if (Math.random() < 0.62) P({ kind: "spark", x: p.x, y: p.y, vx: Math.cos(an) * sp, vy: Math.sin(an) * sp, drag: 2.4, life: rand(0.35, 0.8), s0: rand(1.2, 2.6), s1: 1, rgb: Math.random() < 0.4 ? c2 : rgb });
      else P({ x: p.x, y: p.y, vx: Math.cos(an) * sp * 0.6, vy: Math.sin(an) * sp * 0.6 - 20, drag: 2.2, life: rand(0.5, 1), s0: rand(4, 9), s1: 1, rgb, fp: 1.4 });
    }
  }

  function ringAt(x, y, rgb, r0, r1, w, life, delay, sq) {
    P({ kind: "ring", x, y, rgb, r0, r1, s0: w, life, delay: delay || 0, a: 0.9, sq: sq || 1, fin: 0.01 });
  }

  function qiSpiral(target, color) {
    if (!enabled()) return;
    const p = pt(target), rgb = toRGB(color || "#3fbf8f"), c2 = mix(rgb, WHITE, 0.5);
    const R = clamp(Math.max(p.w, p.h) * 0.9 + 40, 70, 150);
    for (let i = 0; i < 48; i++) {
      const dir = i % 2 ? 1 : -1;
      P({ kind: "spiral", cx: p.x, cy: p.y, x: p.x, y: p.y, ang: rand(0, 6.2832), w: dir * rand(3.4, 5.4), r0: R * rand(0.6, 1.25),
        life: rand(0.75, 1.15), delay: i * 0.018, s0: rand(7, 12), s1: 3, a: 0.95, rgb: Math.random() < 0.35 ? c2 : rgb, fp: 0.6 });
    }
    P({ x: p.x, y: p.y, s0: 8, s1: 60, life: 1.1, delay: 0.2, a: 0.5, rgb, fp: 0.8, fin: 0.5 });
    P({ kind: "glyph", ch: "氣", x: p.x, y: p.y, vy: -26, s0: 18, s1: 34, life: 1.3, delay: 0.05, a: 0.85, rgb: c2, fp: 1.2, fin: 0.25 });
    const fin = 0.85;
    ringAt(p.x, p.y, rgb, R * 0.9, 12, 3, 0.75, 0.45);
    setTimeout(() => { if (enabled()) { burst(p.x != null ? { x: p.x, y: p.y } : target, c2, 10); ringAt(p.x, p.y, c2, 6, 52, 2.2, 0.5); } }, fin * 1000);
  }

  // falce curva (slash): sweep con scia a inchiostro
  function slash(from, to, el, opts) {
    if (!enabled()) return;
    opts = opts || {};
    const a = pt(from), b = pt(to), E = pal(el), rgb = E.rgb, c2 = E.c2;
    const base = Math.atan2(b.y - a.y, b.x - a.x) + (opts.flip ? 1 : -1) * 0.95;
    const L = clamp((b.w || 90) * 2.3, 130, 240);
    const ink = inkRGB();
    const strokes = el === "corpo" ? [{ off: -22, dl: 0, k: 0.55 }, { off: 0, dl: 0.05, k: 0.7 }, { off: 22, dl: 0.1, k: 0.55 }]
      : el === "spada" ? [{ off: 0, dl: 0, k: 1 }, { off: 6, dl: 0.13, k: 0.55, mirror: true }]
      : [{ off: 0, dl: 0, k: 1 }];
    strokes.forEach((s) => {
      const ang = s.mirror ? base + 1.9 : base;
      const nx = -Math.sin(ang), ny = Math.cos(ang);
      const cx = b.x + nx * s.off, cy = b.y + ny * s.off;
      const p0 = { x: cx - Math.cos(ang) * L / 2, y: cy - Math.sin(ang) * L / 2 };
      const p1 = { x: cx + Math.cos(ang) * L / 2, y: cy + Math.sin(ang) * L / 2 };
      const ct = { x: cx + nx * L * 0.3, y: cy + ny * L * 0.3 };
      const bz = (u) => ({ x: (1 - u) * (1 - u) * p0.x + 2 * (1 - u) * u * ct.x + u * u * p1.x, y: (1 - u) * (1 - u) * p0.y + 2 * (1 - u) * u * ct.y + u * u * p1.y });
      const maxW = 15 * s.k;
      const d = {
        t: -s.dl,
        draw(g, dt, t) {
          if (t < 0) return true;
          const head = easeOut(t / 0.2), tail = easeIn((t - 0.08) / 0.4);
          if (tail >= 1) return false;
          if (head > tail + 0.01) {
            const N = 20, pts = [];
            for (let i = 0; i <= N; i++) { const u = tail + (head - tail) * (i / N); pts.push({ p: bz(u), w: Math.sin(Math.PI * (i / N)) * maxW * (1 - tail * 0.5) * (0.35 + 0.65 * (i / N)) }); }
            const poly = (mul) => {
              g.beginPath();
              pts.forEach((q, i) => { const o = pts[Math.min(i + 1, N)].p, pr = pts[Math.max(i - 1, 0)].p; const tx = o.x - pr.x, ty = o.y - pr.y, n = Math.hypot(tx, ty) || 1; const x = q.p.x - ty / n * q.w * mul, y = q.p.y + tx / n * q.w * mul; i ? g.lineTo(x, y) : g.moveTo(x, y); });
              for (let i = N; i >= 0; i--) { const q = pts[i]; const o = pts[Math.min(i + 1, N)].p, pr = pts[Math.max(i - 1, 0)].p; const tx = o.x - pr.x, ty = o.y - pr.y, n = Math.hypot(tx, ty) || 1; g.lineTo(q.p.x + ty / n * q.w * mul, q.p.y - tx / n * q.w * mul); }
              g.closePath();
            };
            g.globalCompositeOperation = "source-over"; g.fillStyle = rgba(ink, 0.5 * (1 - tail)); poly(1.1); g.fill();       // pennellata a inchiostro
            g.globalCompositeOperation = LC(); g.fillStyle = rgba(rgb, 0.55 * (1 - tail)); poly(2.2); g.fill();            // alone
            g.fillStyle = rgba(mix(c2, WHITE, 0.5), 0.95 * (1 - tail * 0.7)); poly(0.8); g.fill();                                // anima bianca
            if (t < 0.2 && Math.random() < 0.9) { const hp = bz(head); P({ kind: "spark", x: hp.x, y: hp.y, vx: rand(-160, 160), vy: rand(-160, 160), drag: 3, life: rand(0.25, 0.5), s0: 2, s1: 1, rgb: c2 }); }
          }
          return true;
        }
      };
      D(d);
    });
  }

  // bagliore d'impatto: lampo + anelli + scintille + dettagli per elemento
  function impact(target, el, crit) {
    if (!enabled()) return;
    const p = pt(target), E = pal(el), rgb = E.rgb, c2 = E.c2, ink = inkRGB();
    const k = crit ? 1.6 : 1;
    P({ x: p.x, y: p.y, s0: 16 * k, s1: 90 * k, life: 0.22, a: 1, rgb: c2, fp: 1.2, fin: 0.01 });
    P({ x: p.x, y: p.y, s0: 10, s1: 50 * k, life: 0.45, a: 0.7, rgb, fp: 1 });
    ringAt(p.x, p.y, c2, 6, 58 * k, 4, 0.38);
    ringAt(p.x, p.y, rgb, 4, 90 * k, 2.4, 0.55, 0.05);
    if (crit) { ringAt(p.x, p.y, [255, 224, 120], 4, 130, 3.2, 0.6, 0.08); ringAt(p.x, p.y, rgb, 2, 56, 7, 0.3, 0, 0.45); }
    const n = Math.round(14 * k);
    for (let i = 0; i < n; i++) {
      const an = rand(0, 6.2832), sp = rand(120, 380) * (crit ? 1.25 : 1);
      P({ kind: "spark", x: p.x, y: p.y, vx: Math.cos(an) * sp, vy: Math.sin(an) * sp, drag: 2.6, life: rand(0.25, 0.6), s0: rand(1.4, 3), s1: 1, rgb: Math.random() < 0.5 ? c2 : rgb });
    }
    // macchie d'inchiostro schizzate
    for (let i = 0; i < (crit ? 6 : 3); i++) {
      const an = rand(0, 6.2832), sp = rand(40, 130);
      P({ comp: "source-over", rgb: ink, x: p.x, y: p.y, vx: Math.cos(an) * sp, vy: Math.sin(an) * sp, drag: 2.2, life: rand(0.5, 0.9), s0: rand(4, 8), s1: rand(8, 15), a: 0.5 });
    }
    const st = E.st;
    const each = (m, fn) => { for (let i = 0; i < m; i++) fn(i); };
    if (st === "ember") each(10, () => P({ x: p.x + rand(-14, 14), y: p.y + rand(-6, 10), vx: rand(-30, 30), vy: rand(-170, -60), g: -40, drag: 0.6, life: rand(0.6, 1.1), s0: rand(5, 9), s1: 1, rgb: Math.random() < 0.5 ? rgb : c2, fp: 1.3 }));
    else if (st === "drop") each(12, () => { const an = rand(-3.0, -0.15); P({ kind: "shard", shape: "drop", x: p.x, y: p.y, vx: Math.cos(an) * rand(80, 220), vy: Math.sin(an) * rand(120, 280), g: 620, life: rand(0.5, 0.9), s0: rand(3.5, 6.5), s1: 2, rgb: Math.random() < 0.5 ? rgb : c2, fp: 0.7 }); });
    else if (st === "leaf") each(10, () => P({ kind: "shard", shape: "leaf", x: p.x, y: p.y, vx: rand(-200, 200), vy: rand(-220, 40), g: 140, drag: 1.4, rot: rand(0, 6), vr: rand(-8, 8), life: rand(0.8, 1.4), s0: rand(6, 10), s1: 4, rgb: Math.random() < 0.5 ? rgb : c2, comp: "source-over", fp: 0.8 }));
    else if (st === "shard") each(9, () => { const an = rand(0, 6.2832); P({ kind: "shard", shape: "diamond", x: p.x, y: p.y, vx: Math.cos(an) * rand(150, 340), vy: Math.sin(an) * rand(150, 340), drag: 2, rot: an, vr: rand(-10, 10), life: rand(0.4, 0.8), s0: rand(6, 11), s1: 2, rgb: Math.random() < 0.5 ? rgb : WHITE }); });
    else if (st === "rock") each(9, () => P({ kind: "shard", shape: "rock", comp: "source-over", x: p.x, y: p.y, vx: rand(-200, 200), vy: rand(-300, -80), g: 800, rot: rand(0, 6), vr: rand(-9, 9), life: rand(0.6, 1), s0: rand(4, 8), s1: 3, rgb: Math.random() < 0.5 ? rgb : mix(rgb, [60, 40, 20], 0.4), fp: 0.6 }));
    else if (st === "bolt") { const g0 = { x: p.x, y: p.y }; for (let i = 0; i < 4; i++) { const an = rand(0, 6.2832), len = rand(40, 85); boltDraw({ x: g0.x, y: g0.y }, { x: g0.x + Math.cos(an) * len, y: g0.y + Math.sin(an) * len }, rgb, c2, 0.18, 0, 1.2); } }
    else if (st === "swirl") { ringAt(p.x, p.y, c2, 10, 70, 2, 0.5, 0, 0.5); ringAt(p.x, p.y, rgb, 6, 50, 3, 0.5, 0.05, 0.4); }
    else if (st === "star") { each(2, (i) => { const ang = i ? Math.PI / 4 : 0; D({ draw(g, dt, t) { if (t > 0.35) return false; const f = 1 - t / 0.35, len = 110 * k * easeOut(t / 0.12) ; g.globalCompositeOperation = LC(); g.strokeStyle = rgba(c2, f); g.lineWidth = 3 * f + 0.5; g.lineCap = "round"; g.beginPath(); g.moveTo(p.x - Math.cos(ang) * len, p.y - Math.sin(ang) * len); g.lineTo(p.x + Math.cos(ang) * len, p.y + Math.sin(ang) * len); g.moveTo(p.x - Math.cos(ang + 1.5708) * len, p.y - Math.sin(ang + 1.5708) * len); g.lineTo(p.x + Math.cos(ang + 1.5708) * len, p.y + Math.sin(ang + 1.5708) * len); g.stroke(); return true; } }); }); }
    else if (st === "smoke") each(8, () => P({ comp: "source-over", rgb: mix(rgb, [10, 5, 20], 0.5), x: p.x + rand(-10, 10), y: p.y + rand(-10, 10), vx: rand(-50, 50), vy: rand(-90, -20), drag: 1, life: rand(0.8, 1.4), s0: rand(10, 18), s1: rand(26, 40), a: 0.6, fp: 1.2 }));
    else if (st === "fist") { ringAt(p.x, p.y, c2, 8, 90 * k, 6, 0.3, 0, 0.5); each(6, () => P({ comp: "source-over", rgb: mix(rgb, [70, 40, 15], 0.5), x: p.x + rand(-16, 16), y: p.y + rand(4, 16), vx: rand(-90, 90), vy: rand(-70, -10), drag: 1.5, life: rand(0.5, 0.9), s0: 8, s1: 22, a: 0.4 })); }
    else if (st === "blade") { const an = -0.7; D({ draw(g, dt, t) { if (t > 0.3) return false; const f = 1 - t / 0.3, len = 80 * k * easeOut(t / 0.1); g.globalCompositeOperation = LC(); g.strokeStyle = rgba(c2, f); g.lineWidth = 2.5 * f + 0.4; g.lineCap = "round"; g.beginPath(); g.moveTo(p.x - Math.cos(an) * len, p.y - Math.sin(an) * len); g.lineTo(p.x + Math.cos(an) * len, p.y + Math.sin(an) * len); g.moveTo(p.x - Math.cos(an + 1.57) * len * 0.6, p.y - Math.sin(an + 1.57) * len * 0.6); g.lineTo(p.x + Math.cos(an + 1.57) * len * 0.6, p.y + Math.sin(an + 1.57) * len * 0.6); g.stroke(); return true; } }); }
    // DOM: sbiancamento e sussulto del bersaglio
    if (isEl(target)) flashEl(target, crit ? 380 : 280);
    if (crit && !LM) screenFlash(rgba(c2, 1), 0.16, 260);
  }

  // saetta spezzata tra due punti (con biforcazioni); usata da lightning, projectile 'bolt' e impact
  function bolt(a, b, spread, depth) {
    const pts = [a];
    const L = Math.hypot(b.x - a.x, b.y - a.y), nseg = Math.max(4, Math.round(L / 15));
    const nx = -(b.y - a.y) / (L || 1), ny = (b.x - a.x) / (L || 1);
    for (let i = 1; i < nseg; i++) {
      const u = i / nseg, o = (Math.random() - 0.5) * spread * (1 - Math.abs(u - 0.5) * 0.5);
      pts.push({ x: a.x + (b.x - a.x) * u + nx * o, y: a.y + (b.y - a.y) * u + ny * o });
    }
    pts.push(b);
    const forks = [];
    if (depth > 0) for (let i = 2; i < pts.length - 2; i++) if (Math.random() < 0.2) {
      const an = Math.atan2(b.y - a.y, b.x - a.x) + rand(-0.9, 0.9), len = rand(0.15, 0.4) * L;
      forks.push(bolt(pts[i], { x: pts[i].x + Math.cos(an) * len, y: pts[i].y + Math.sin(an) * len }, spread * 0.6, depth - 1));
    }
    return { pts, forks };
  }
  function strokeBolt(g, B, w) {
    g.beginPath(); B.pts.forEach((q, i) => (i ? g.lineTo(q.x, q.y) : g.moveTo(q.x, q.y))); g.stroke();
    B.forks.forEach((f) => strokeBolt(g, f, w * 0.6));
  }
  function boltDraw(a, b, rgb, c2, life, delay, widthK, onEnd) {
    const B = bolt(a, b, clamp(Math.hypot(b.x - a.x, b.y - a.y) * 0.06, 10, 28), 2);
    let B2 = null;
    D({
      t: -(delay || 0),
      draw(g, dt, t) {
        if (t < 0) return true;
        if (t > life) return false;
        const f = 1 - t / life, flick = Math.sin(t * 90) > -0.3 ? 1 : 0.25;
        if (!B2 && t > life * 0.45) B2 = bolt(a, b, clamp(Math.hypot(b.x - a.x, b.y - a.y) * 0.06, 10, 28), 2);   // secondo scatto: sfarfallio
        const cur = B2 || B;
        g.globalCompositeOperation = LC(); g.lineCap = "round"; g.lineJoin = "round";
        g.strokeStyle = rgba(rgb, 0.35 * f * flick); g.lineWidth = 10 * (widthK || 1); strokeBolt(g, cur, 10 * (widthK || 1));
        g.strokeStyle = rgba(rgb, 0.85 * f * flick); g.lineWidth = 3.6 * (widthK || 1); strokeBolt(g, cur, 4);
        g.strokeStyle = rgba(c2, f * flick); g.lineWidth = 1.5 * (widthK || 1); strokeBolt(g, cur, 2);
        return true;
      },
      end: onEnd
    });
  }

  function lightning(target) {
    if (!enabled()) return;
    const p = pt(target), E = pal("fulmine"), rgb = E.rgb, c2 = E.c2;
    screenFlash("#d9ccff", 0.4, 420);
    const n = 3;
    for (let i = 0; i < n; i++) {
      const sx = clamp(p.x + rand(-170, 170), 10, vw() - 10);
      boltDraw({ x: sx, y: -10 }, { x: p.x + rand(-14, 14), y: p.y }, rgb, c2, 0.5, i * 0.09, i === 0 ? 1.6 : 0.9);
    }
    setTimeout(() => {
      if (!enabled()) return;
      impact(target, "fulmine", true);
      shake(isEl(target) ? target : document.body, 1.6);
      for (let i = 0; i < 18; i++) P({ kind: "spark", x: p.x, y: p.y, vx: rand(-260, 260), vy: rand(-380, -60), g: 600, drag: 0.8, life: rand(0.4, 0.9), s0: 2, s1: 1, rgb: c2 });
    }, 40);
    setTimeout(() => screenFlash("#fff", 0.28, 220), 260);
  }

  function breakthrough(target) {
    if (!enabled()) return;
    const p = pt(target), gold = LM ? [214, 148, 16] : [255, 205, 90], pale = LM ? [238, 178, 36] : [255, 244, 200], jade = toRGB("#3fbf8f");
    screenFlash("#ffe9a8", 0.6, 900);
    // colonna di luce
    D({ draw(g, dt, t) {
      const life = 1.5; if (t > life) return false;
      const f = t < 0.15 ? t / 0.15 : Math.pow(1 - (t - 0.15) / (life - 0.15), 1.6);
      const w = (26 + 70 * easeOut(t / 0.6)) * (0.5 + 0.5 * f);
      const gr = g.createLinearGradient(p.x - w, 0, p.x + w, 0);
      gr.addColorStop(0, rgba(gold, 0)); gr.addColorStop(0.5, rgba(pale, 0.85 * f)); gr.addColorStop(1, rgba(gold, 0));
      g.globalCompositeOperation = LC(); g.fillStyle = gr; g.fillRect(p.x - w, 0, w * 2, p.y + 30);
      return true;
    } });
    P({ x: p.x, y: p.y, s0: 30, s1: 260, life: 0.7, a: 1, rgb: pale, fp: 1.4, fin: 0.01 });
    P({ x: p.x, y: p.y, s0: 20, s1: 150, life: 1.4, a: 0.6, rgb: gold, fp: 1, fin: 0.1 });
    for (let i = 0; i < 4; i++) ringAt(p.x, p.y, i % 2 ? pale : gold, 10, 120 + i * 90, 6 - i, 1.0 + i * 0.12, i * 0.12);
    ringAt(p.x, p.y, jade, 10, 240, 3, 1.3, 0.3, 0.55);
    for (let i = 0; i < 90; i++) {
      const an = rand(0, 6.2832), sp = rand(120, 620);
      if (i % 3) P({ kind: "spark", x: p.x, y: p.y, vx: Math.cos(an) * sp, vy: Math.sin(an) * sp, g: 90, drag: 1.8, life: rand(0.7, 1.5), s0: rand(1.6, 3.4), s1: 1, rgb: Math.random() < 0.5 ? gold : pale, fp: 0.9 });
      else P({ x: p.x, y: p.y, vx: Math.cos(an) * sp * 0.5, vy: Math.sin(an) * sp * 0.5 - 30, drag: 1.6, life: rand(0.9, 1.7), s0: rand(6, 14), s1: 2, rgb: gold, fp: 1.2 });
    }
    ["破", "道", "仙", "天"].forEach((ch, i) => P({ kind: "glyph", ch, x: p.x + (i - 1.5) * 52, y: p.y + 10, vy: -46, s0: 26, s1: 44, life: 1.8, delay: 0.15 + i * 0.1, a: 0.95, rgb: pale, fp: 1.5, fin: 0.2 }));
    shake(isEl(target) ? target : document.body, 1.7);
    if (isEl(target) && target.animate) target.animate([{ filter: "brightness(2.4) drop-shadow(0 0 22px #ffd36a)" }, { filter: "brightness(1.4) drop-shadow(0 0 14px #ffd36a)", offset: 0.5 }, { filter: "none" }], { duration: 1400, easing: "ease-out" });
    setTimeout(() => { if (enabled()) screenFlash("#fff", 0.3, 300); }, 380);
  }

  // alone persistente su un elemento
  function aura(el, color, on) {
    if (!isEl(el)) return;
    if (on === false) { el.classList.remove("fx-aura"); el.style.removeProperty("--fx-c"); return; }
    if (!enabled()) return;
    const key = typeof color === "string" && EL[color] ? EL[color].c : color;
    const rgb = toRGB(key || "#3fbf8f");
    el.style.setProperty("--fx-c", `rgb(${rgb.join(",")})`);
    el.classList.add("fx-aura");
  }

  // proiettile: orb con scia a seconda dell'elemento; alla fine impatto e onHit
  function projectile(from, to, el, onHit, opts) {
    opts = opts || {};
    if (!enabled()) { if (onHit) onHit(); return; }
    const a = pt(from), b = pt(to), E = pal(el), rgb = E.rgb, c2 = E.c2, st = E.st;
    const dist = Math.hypot(b.x - a.x, b.y - a.y);
    const dur = clamp(dist / 1100, 0.28, 0.5);
    const side = opts.flip ? -1 : 1;
    const nx = -(b.y - a.y) / (dist || 1), ny = (b.x - a.x) / (dist || 1);
    const cp = { x: (a.x + b.x) / 2 + nx * dist * 0.14 * side, y: (a.y + b.y) / 2 + ny * dist * 0.14 * side - 18 };
    const at = (u) => ({ x: (1 - u) * (1 - u) * a.x + 2 * (1 - u) * u * cp.x + u * u * b.x, y: (1 - u) * (1 - u) * a.y + 2 * (1 - u) * u * cp.y + u * u * b.y });
    const done = () => { if (opts.noImpact !== true) impact(to, el, !!opts.crit); if (onHit) onHit(); };
    if (st === "bolt") {                              // il fulmine è istantaneo: saetta da punto a punto
      boltDraw(a, b, rgb, c2, 0.3, 0.05, 1.1);
      setTimeout(done, 130);
      return;
    }
    let acc = 0, ang = 0, prev = a;
    D({
      draw(g, dt, t) {
        const s = clamp(t / dur, 0, 1), u = 0.3 * s + 0.7 * s * s;
        const pos = at(u); ang += dt * 14;
        const dir = Math.atan2(pos.y - prev.y, pos.x - prev.x) || 0;
        prev = pos;
        // scia
        acc += dt;
        while (acc > 0.012) {
          acc -= 0.012;
          if (st === "ember") P({ x: pos.x + rand(-4, 4), y: pos.y + rand(-4, 4), vx: rand(-20, 20), vy: rand(-60, -10), life: rand(0.25, 0.5), s0: rand(8, 13), s1: 2, rgb: Math.random() < 0.5 ? rgb : c2, a: 0.8, fp: 1.3 });
          else if (st === "drop") P({ kind: "shard", shape: "drop", x: pos.x + rand(-5, 5), y: pos.y + rand(-5, 5), vy: 10, g: 400, life: rand(0.25, 0.5), s0: rand(3, 5.5), s1: 1.5, rgb: Math.random() < 0.5 ? rgb : c2 });
          else if (st === "leaf") P({ kind: "shard", shape: "leaf", comp: "source-over", x: pos.x + rand(-6, 6), y: pos.y + rand(-6, 6), rot: rand(0, 6), vr: rand(-10, 10), vy: 20, life: rand(0.3, 0.6), s0: rand(5, 8), s1: 2, rgb: Math.random() < 0.5 ? rgb : c2 });
          else if (st === "shard") P({ kind: "shard", shape: "diamond", x: pos.x + rand(-5, 5), y: pos.y + rand(-5, 5), rot: dir + 1.57, life: rand(0.18, 0.35), s0: rand(5, 9), s1: 1, rgb: Math.random() < 0.5 ? rgb : WHITE });
          else if (st === "rock") P({ comp: "source-over", rgb: mix(rgb, [70, 45, 20], 0.5), x: pos.x + rand(-5, 5), y: pos.y + rand(-5, 5), vy: -10, life: rand(0.3, 0.55), s0: 6, s1: 15, a: 0.45 });
          else if (st === "smoke") P({ comp: "source-over", rgb: mix(rgb, [10, 5, 20], 0.55), x: pos.x + rand(-5, 5), y: pos.y + rand(-5, 5), life: rand(0.35, 0.6), s0: 8, s1: 18, a: 0.6 });
          else if (st === "swirl") { const o = ang * 3; P({ x: pos.x + Math.cos(o) * 14, y: pos.y + Math.sin(o) * 14, life: 0.3, s0: 6, s1: 1, rgb: c2, a: 0.8 }); P({ x: pos.x - Math.cos(o) * 14, y: pos.y - Math.sin(o) * 14, life: 0.3, s0: 6, s1: 1, rgb, a: 0.8 }); }
          else if (st === "star") P({ kind: "spark", x: pos.x + rand(-8, 8), y: pos.y + rand(-8, 8), vx: rand(-30, 30), vy: rand(-30, 30), life: rand(0.3, 0.6), s0: 2, s1: 1, rgb: c2 });
          else P({ x: pos.x, y: pos.y, life: rand(0.2, 0.4), s0: rand(7, 11), s1: 1, rgb, a: 0.7, fp: 1.2 });
        }
        // testa
        g.globalCompositeOperation = LC();
        const sz = st === "blade" ? 20 : 24;
        g.drawImage(sprite(rgb), pos.x - sz * 1.5, pos.y - sz * 1.5, sz * 3, sz * 3);
        g.drawImage(sprite(c2), pos.x - sz * 0.7, pos.y - sz * 0.7, sz * 1.4, sz * 1.4);
        g.save(); g.translate(pos.x, pos.y);
        if (st === "blade" || st === "fist") {            // mezzaluna di qi in volo
          g.rotate(dir); g.strokeStyle = rgba(c2, 0.95); g.lineWidth = 4; g.lineCap = "round";
          g.beginPath(); g.arc(-6, 0, 22, -1.0, 1.0); g.stroke();
          g.strokeStyle = rgba(rgb, 0.6); g.lineWidth = 9; g.beginPath(); g.arc(-6, 0, 22, -0.9, 0.9); g.stroke();
        } else if (st === "star") {
          g.strokeStyle = rgba(c2, 0.9); g.lineWidth = 2;
          g.beginPath(); g.moveTo(-26, 0); g.lineTo(26, 0); g.moveTo(0, -26); g.lineTo(0, 26); g.stroke();
        } else if (st === "shard" || st === "rock" || st === "leaf") {
          for (let i = 0; i < 3; i++) {
            const o = ang * 1.4 + i * 2.094; g.save(); g.rotate(o); g.translate(14, 0); g.fillStyle = rgba(st === "rock" ? mix(rgb, [60, 40, 20], 0.35) : i ? rgb : c2, 0.95);
            g.beginPath();
            if (st === "leaf") g.ellipse(0, 0, 9, 4, 0, 0, 6.28); else if (st === "rock") { g.moveTo(-6, -4); g.lineTo(0, -8); g.lineTo(7, -2); g.lineTo(4, 6); g.lineTo(-5, 5); } else { g.moveTo(8, 0); g.lineTo(0, 4); g.lineTo(-8, 0); g.lineTo(0, -4); }
            g.closePath(); g.fill(); g.restore();
          }
        }
        g.restore();
        if (s >= 1) { done(); return false; }
        return true;
      }
    });
  }

  // ---------------------------------------------------------------- allenamento: spirale di qi nel bersaglio
  function train(target) {
    if (!enabled()) return;
    qiSpiral(target, "#3fbf8f");
    if (isEl(target) && target.animate) {
      target.animate([{ boxShadow: "0 0 0 0 rgba(63,191,143,.55)", transform: "scale(1)" }, { boxShadow: "0 0 0 16px rgba(63,191,143,0)", transform: "scale(1.05)", offset: 0.55 }, { boxShadow: "0 0 0 0 rgba(63,191,143,0)", transform: "scale(1)" }],
        { duration: 1100, easing: "ease-out", composite: "add" });
    }
  }

  // ---------------------------------------------------------------- DUELLO
  const timers = [];
  let turnToken = 0;
  let lastKey = null, lastHp = { me: null, foe: null };
  const after = (tok, ms, fn) => { const id = setTimeout(() => { if (tok === turnToken && enabled()) { try { fn(); } catch (e) { if (window.console) console.warn("FX:", e); } } }, ms); timers.push(id); return id; };

  const side = (root, s) => {
    const r = root && root.isConnected ? root : (document.querySelector("#scene") || document);
    return r.querySelector(".fighter." + s);
  };
  const portraitOf = (f) => f ? (f.querySelector(".portrait, svg") || f) : null;

  function lunge(f, toward, k) {          // il ritratto scatta verso l'avversario e torna
    const p = portraitOf(f); if (!p || !p.animate || !toward) return;
    const a = pt(p), b = pt(toward);
    const d = Math.hypot(b.x - a.x, b.y - a.y) || 1;
    const m = Math.min(70, d * 0.3) * (k || 1);
    const dx = (b.x - a.x) / d, dy = (b.y - a.y) / d;
    f.classList.add("fx-front");
    const an = p.animate([
      { transform: "translate(0,0) scale(1)" },
      { transform: `translate(${-dx * 12}px,${-dy * 12}px) scale(.96)`, offset: 0.2 },
      { transform: `translate(${dx * m}px,${dy * m}px) scale(1.12)`, offset: 0.42 },
      { transform: `translate(${dx * m * 0.9}px,${dy * m * 0.9}px) scale(1.1)`, offset: 0.52 },
      { transform: "translate(0,0) scale(1)" }], { duration: 520, easing: "cubic-bezier(.3,.7,.3,1)" });
    an.onfinish = an.oncancel = () => f.classList.remove("fx-front");
  }

  function hold(root, s, ms) {            // le barre della vita calano solo quando il colpo arriva
    const r = root && root.isConnected ? root : document;
    r.querySelectorAll('.hpbar[data-side="' + s + '"]').forEach((bar) => {
      const i = bar.querySelector("i"), g = bar.querySelector(".ghost");
      if (i) i.style.transitionDelay = ms + "ms";
      if (g) g.style.transitionDelay = ms + 100 + "ms";
      setTimeout(() => { if (i) i.style.transitionDelay = ""; if (g) g.style.transitionDelay = ""; }, ms + 1600);
    });
  }

  function hurtFlash(root) {
    const ar = (root && root.isConnected ? root : document).querySelector(".arena") || root;
    if (isEl(ar) && ar.animate) ar.animate([{ boxShadow: "inset 0 0 0 0 rgba(179,51,42,0)" }, { boxShadow: "inset 0 0 70px 6px rgba(179,51,42,.5)", offset: 0.25 }, { boxShadow: "inset 0 0 0 0 rgba(179,51,42,0)" }], { duration: 650, easing: "ease-out" });
  }

  function shield(f, rgb) {
    const p = portraitOf(f); if (!isEl(f) || !p) return;
    const el = document.createElement("div"); el.className = "fx-shield";
    const fr = f.getBoundingClientRect(), pr = p.getBoundingClientRect(), S = Math.max(pr.width, pr.height) * 1.5;
    Object.assign(el.style, { left: pr.left - fr.left + pr.width / 2 - S / 2 + "px", top: pr.top - fr.top + pr.height / 2 - S / 2 + "px", width: S + "px", height: S + "px", "--fx-c": `rgb(${rgb.join(",")})` });
    f.appendChild(el);
    if (el.animate) { const a = el.animate([{ transform: "scale(.3)", opacity: 0 }, { transform: "scale(1.12)", opacity: 1, offset: 0.25 }, { transform: "scale(1)", opacity: 0.9, offset: 0.6 }, { transform: "scale(1.04)", opacity: 0 }], { duration: 1200, easing: "ease-out" }); a.onfinish = () => el.remove(); }
    else setTimeout(() => el.remove(), 1200);
    const c = pt(p); ringAt(c.x, c.y, rgb, 10, S * 0.6, 4, 0.5); ringAt(c.x, c.y, mix(rgb, WHITE, 0.6), 8, S * 0.48, 2, 0.6, 0.08);
    for (let i = 0; i < 12; i++) { const an = (i / 12) * 6.2832; P({ kind: "spark", x: c.x + Math.cos(an) * S * 0.45, y: c.y + Math.sin(an) * S * 0.45, vx: Math.cos(an) * 60, vy: Math.sin(an) * 60, drag: 2, life: 0.5, s0: 2, s1: 1, rgb }); }
  }

  function healFx(f, rgb) {
    const c = pt(f);
    for (let i = 0; i < 26; i++) P({ x: c.x + rand(-34, 34), y: c.y + rand(10, 40), vx: rand(-12, 12), vy: rand(-110, -50), life: rand(0.8, 1.4), delay: rand(0, 0.5), s0: rand(5, 10), s1: 2, rgb: Math.random() < 0.4 ? mix(rgb, WHITE, 0.5) : rgb, a: 0.85, fp: 1.1 });
    for (let i = 0; i < 4; i++) P({ kind: "glyph", ch: "✚", x: c.x + rand(-30, 30), y: c.y + rand(0, 30), vy: -48, s0: 16, s1: 22, life: 1.2, delay: i * 0.12, a: 0.9, rgb: mix(rgb, WHITE, 0.4), fp: 1.2, fin: 0.2 });
    ringAt(c.x, c.y + 20, rgb, 10, 60, 3, 0.8, 0, 0.35);
  }

  function ko(f) {                        // KO: il ritratto si scolora e si dissolve in inchiostro
    const p = portraitOf(f); if (!isEl(p)) return;
    const r = p.getBoundingClientRect(), ink = inkRGB(), wisp = toRGB("#3fbf8f");
    if (p.animate) {
      p.animate([{ filter: "none", opacity: 1, transform: "none" }, { filter: "grayscale(1) contrast(1.1) brightness(.85)", opacity: 0.85, offset: 0.25 },
        { filter: "grayscale(1) blur(2px) brightness(.6)", opacity: 0.4, transform: "translateY(6px)" }], { duration: 1300, easing: "ease-in", fill: "forwards" });
    }
    setTimeout(() => f.classList.add("fx-ko"), 1250);
    for (let i = 0; i < 70; i++) {
      P({ comp: "source-over", rgb: ink, x: r.left + rand(0, r.width), y: r.top + rand(0, r.height), vx: rand(-25, 25), vy: rand(-90, -20), drag: 0.5, g: -10,
        life: rand(0.9, 1.9), delay: rand(0.1, 0.9), s0: rand(8, 16), s1: rand(26, 46), a: 0.55, fp: 1.2, fin: 0.25 });
      if (i % 4 === 0) P({ x: r.left + rand(0, r.width), y: r.top + rand(0, r.height), vy: rand(-80, -30), life: rand(0.8, 1.4), delay: rand(0.2, 1.0), s0: rand(4, 8), s1: 1, rgb: wisp, a: 0.7 });
    }
    for (let i = 0; i < 3; i++) P({ comp: "source-over", rgb: ink, x: r.left + r.width / 2, y: r.top + r.height * 0.6, s0: 20, s1: 100 + i * 20, life: 1.6, delay: 0.1 + i * 0.2, a: 0.28, fp: 1.5, fin: 0.3 });
  }

  // stati persistenti (aure, KO rimasto) a ogni rendering dell'arena
  function syncStatic(root, arena) {
    const me = side(root, "me"), foe = side(root, "foe");
    if (me) aura(portraitOf(me), "luce", !!arena.concentrato);
    if (foe) aura(portraitOf(foe), "#ff4a30", !!arena.carica && !arena.finito);
    if (arena.finito) {
      if (arena.lui && arena.lui.hp <= 0 && foe) foe.classList.add("fx-ko");
      if (arena.tu && arena.tu.hp <= 0 && me) me.classList.add("fx-ko");
    }
  }

  function duelTurn(root, arena, opts) {
    opts = opts || {};
    if (!isEl(root) || !arena || !enabled()) return { played: false };
    root.classList.add("fx-active");                // nasconde i vecchi .pop testuali
    const L = arena.ultimo || {};
    const key = arena.turno + "|" + JSON.stringify(L);
    const first = lastKey === null, same = key === lastKey;
    lastKey = key;
    const prev = lastHp;
    lastHp = { me: arena.tu ? arena.tu.hp : null, foe: arena.lui ? arena.lui.hp : null };
    syncStatic(root, arena);
    if (same || !L.mossa || (first && !opts.force)) return { played: false, key };

    const tok = ++turnToken;
    timers.forEach(clearTimeout); timers.length = 0;
    const me = side(root, "me"), foe = side(root, "foe");
    const elMe = L.el || "", elFoe = (arena.elementi && arena.elementi.lui && arena.elementi.lui[0]) || "";
    const mv = L.mossa;
    const passive = mv === "difendi" || mv === "concentrati" || mv === "pillola" || mv === "fuggi";
    let end = 700;

    // ----- la mia mossa
    if (!passive) {
      const melee = !!MELEE[elMe];
      let hitAt;
      const onHit = () => {
        const f = side(root, "foe") || foe;
        impact(f, elMe, !!L.critico);
        shake(f, L.critico ? 1.8 : 1);
        if (L.inflitto) {
          floatText(f, "−" + fmt(L.inflitto), L.critico ? "crit" : "dmg");
          if (L.critico) after(tok, 120, () => floatText(f, "CRITICO!", "crit"));
          if (L.eff === "super") after(tok, 260, () => { floatText(f, "SUPEREFFICACE!", "rare"); const c = pt(f); ringAt(c.x, c.y, toRGB("#f2cf5b"), 10, 110, 3, 0.6); });
          else if (L.eff === "poco") after(tok, 260, () => floatText(f, "poco efficace…", "qi"));
        } else floatText(f, "Mancato", "qi");
        if (L.stato) after(tok, 420, () => floatText(f, String(L.stato), "bad"));
        if (L.alleati > 0) after(tok, 160, () => { floatText(side(root, "me") || me, "+" + L.alleati + " spiriti", "rare"); burst(side(root, "me") || me, "#b39bff", 14); });
      };
      lunge(me, foe, 1);
      if (melee) {
        hitAt = 330;
        after(tok, 150, () => slash(side(root, "me") || me, side(root, "foe") || foe, elMe));
        after(tok, hitAt, onHit);
      } else {
        hitAt = 130 + 360;
        after(tok, 130, () => projectile(side(root, "me") || me, side(root, "foe") || foe, elMe, onHit, { crit: !!L.critico }));
      }
      hold(root, "foe", hitAt + 10);
      end = hitAt + 600;
    } else if (mv === "difendi") {
      after(tok, 0, () => { shield(side(root, "me") || me, toRGB("#7fd3ff")); floatText(side(root, "me") || me, "Guardia", "qi"); });
    } else if (mv === "concentrati") {
      after(tok, 0, () => { const m = side(root, "me") || me; qiSpiral(portraitOf(m), "#f2cf5b"); floatText(m, "Concentrazione", "gain"); });
    } else if (mv === "pillola") {
      after(tok, 0, () => {
        const m = side(root, "me") || me; healFx(m, toRGB("#3fbf8f"));
        const gain = prev.me != null && arena.tu ? arena.tu.hp - prev.me : 0;
        floatText(m, gain > 0 ? "+" + fmt(gain) : "Pillola", "heal");
      });
      hold(root, "me", 350);
    } else if (mv === "fuggi") {
      after(tok, 0, () => { const m = side(root, "me") || me; floatText(m, arena.finito ? "Fuga!" : "Fuga fallita", arena.finito ? "qi" : "bad"); const p = portraitOf(m); if (p && p.animate) p.animate([{ transform: "none", opacity: 1 }, { transform: "translateX(-40px)", opacity: 0.2, offset: 0.5 }, { transform: "none", opacity: 1 }], { duration: 700 }); });
    }

    // ----- il contraccolpo nemico
    let koAt = 0;
    const foeStart = (passive ? 0 : end - 600) + 600 + (passive ? 300 : 0);
    if (L.subito > 0) {
      const mm = !elFoe || !!MELEE[elFoe] || (arena.lui && arena.lui.kind && arena.lui.kind !== "human" && !elFoe);
      const cr = !!L.critico_lui;
      let hit2;
      const onHit2 = () => {
        const m = side(root, "me") || me, kind = elFoe || "nemico";
        impact(m, kind, cr);
        shake(m, cr ? 1.8 : 1.1);
        hurtFlash(root);
        floatText(m, "−" + fmt(L.subito), cr ? "crit" : "bad");
        if (cr) after(tok, 120, () => floatText(m, "CRITICO!", "bad"));
      };
      after(tok, foeStart, () => lunge(side(root, "foe") || foe, side(root, "me") || me, 1));
      if (mm) { hit2 = foeStart + 190; after(tok, foeStart + 40, () => slash(side(root, "foe") || foe, side(root, "me") || me, elFoe || "nemico", { flip: true })); after(tok, hit2, onHit2); }
      else { hit2 = foeStart + 130 + 360; after(tok, foeStart + 130, () => projectile(side(root, "foe") || foe, side(root, "me") || me, elFoe, onHit2, { flip: true, crit: cr })); }
      hold(root, "me", hit2 + 10);
      end = Math.max(end, hit2 + 600);
      koAt = hit2 + 280;
    } else if (!passive && L.inflitto) {
      koAt = 0;
    }

    // ----- fine dello scontro
    if (arena.finito) {
      if (arena.lui && arena.lui.hp <= 0 && !passive) {
        const t0 = (end - 600) + 280;      // poco dopo il colpo finale
        after(tok, t0, () => { ko(side(root, "foe") || foe); });
        after(tok, t0 + 900, () => { const m = side(root, "me") || me; floatText(m, "Vittoria!", "rare"); burst(m, "#f2cf5b", 28); });
        end = Math.max(end, t0 + 1600);
      } else if (arena.tu && arena.tu.hp <= 0 && koAt) {
        after(tok, koAt, () => ko(side(root, "me") || me));
        end = Math.max(end, koAt + 1400);
      }
    }
    return { played: true, key, duration: end };
  }

  // ---------------------------------------------------------------- trascinamento delle carte sul nemico
  let drag = null;
  function endDrag(abort) {
    if (!drag) return;
    const d = drag; drag = null;
    clearTimeout(d.lp);
    window.removeEventListener("pointermove", d.mv, true);
    window.removeEventListener("pointerup", d.up, true);
    window.removeEventListener("pointercancel", d.cn, true);
    window.removeEventListener("keydown", d.kd, true);
    document.removeEventListener("touchmove", d.tm, { capture: true });
    if (d.ghost) d.ghost.remove();
    if (d.card) d.card.classList.remove("fx-dragsrc");
    document.body.classList.remove("fx-dragging");
    document.querySelectorAll(".fx-target,.fx-hot").forEach((n) => n.classList.remove("fx-target", "fx-hot"));
  }

  function enableCardDrag(root) {
    if (!isEl(root) || root._fxDrag) return;
    root._fxDrag = true;
    root.addEventListener("pointerdown", (ev) => {
      if (!enabled() || drag) return;
      if (ev.pointerType === "mouse" && ev.button !== 0) return;
      const card = ev.target.closest && ev.target.closest(".hand .card-act[data-cmd]");
      if (!card || card.disabled || !root.contains(card)) return;
      const touch = ev.pointerType === "touch";
      const d = drag = { card, id: ev.pointerId, x0: ev.clientX, y0: ev.clientY, x: ev.clientX, y: ev.clientY, on: false, ghost: null, hot: false, root, touch, lastP: 0 };
      d.start = () => {
        if (d.on || drag !== d) return;
        d.on = true;
        const r = card.getBoundingClientRect();
        d.ox = d.x0 - r.left; d.oy = d.y0 - r.top;
        const g = card.cloneNode(true);
        g.classList.add("fx-ghost"); g.removeAttribute("data-cmd"); g.removeAttribute("id");
        g.querySelectorAll("kbd,.cdn").forEach((n) => n.remove());
        Object.assign(g.style, { width: r.width + "px", height: r.height + "px", left: "0px", top: "0px" });
        document.body.appendChild(g); d.ghost = g; d.gw = r.width; d.gh = r.height;
        card.classList.add("fx-dragsrc");
        document.body.classList.add("fx-dragging");
        const foe = side(root, "foe"); if (foe) foe.classList.add("fx-target");
        place();
        if (g.animate) g.animate([{ transform: g.style.transform + " scale(1)" }, { transform: g.style.transform + " scale(1.06)" }], { duration: 120, fill: "none" });
        if (navigator.vibrate) { try { navigator.vibrate(8); } catch (e) { /* ignora */ } }
      };
      const place = () => {
        if (!d.ghost) return;
        const tilt = clamp((d.x - d.lx) * 0.4, -14, 14);
        d.lx = d.x;
        d.ghost.style.transform = `translate(${d.x - d.ox}px, ${d.y - d.oy}px) rotate(${(d.tilt = (d.tilt || 0) * 0.7 + tilt * 0.3).toFixed(1)}deg) scale(1.06)`;
        const foe = side(root, "foe");
        let hot = false;
        if (foe) { const r = foe.getBoundingClientRect(); hot = d.x > r.left - 14 && d.x < r.right + 14 && d.y > r.top - 14 && d.y < r.bottom + 14; }
        if (hot !== d.hot) { d.hot = hot; if (foe) foe.classList.toggle("fx-hot", hot); }
        const now = performance.now();
        if (now - d.lastP > 40) {
          d.lastP = now;
          const col = (/el-(\w+)/.exec(card.className) || [])[1];
          P({ x: d.x + rand(-6, 6), y: d.y + rand(-6, 6), vx: rand(-20, 20), vy: rand(-20, 20), life: 0.5, s0: 9, s1: 1, a: 0.7, rgb: pal(col || "").rgb, fp: 1.2 });
        }
      };
      d.lx = ev.clientX;
      d.mv = (e) => {
        if (e.pointerId !== d.id) return;
        d.x = e.clientX; d.y = e.clientY;
        if (!d.on) {
          const dist = Math.hypot(d.x - d.x0, d.y - d.y0);
          if (touch) { if (dist > 10) endDrag(); return; }       // dito che scorre prima del tocco lungo: è uno scroll
          if (dist > 7) d.start(); else return;
        }
        place();
      };
      d.up = (e) => {
        if (e.pointerId !== d.id) return;
        const wasOn = d.on, hot = d.hot, c = d.card, root2 = d.root;
        const foe = side(root2, "foe");
        endDrag();
        if (!wasOn) return;                                       // clic semplice: ci pensa il browser
        // il clic sintetico che segue un trascinamento va inghiottito
        const swallow = (ce) => { ce.stopPropagation(); ce.preventDefault(); window.removeEventListener("click", swallow, true); };
        window.addEventListener("click", swallow, true);
        const stopSwallow = setTimeout(() => window.removeEventListener("click", swallow, true), 400);
        if (hot && c.isConnected && !c.disabled) {
          if (foe) { const p = pt(foe); ringAt(p.x, p.y, toRGB("#c2392e"), 6, 70, 3, 0.4); }
          setTimeout(() => { clearTimeout(stopSwallow); window.removeEventListener("click", swallow, true); c.click(); }, 40);   // dopo il clic sintetico del browser
        }
      };
      d.cn = (e) => { if (e.pointerId === d.id) endDrag(); };
      d.kd = (e) => { if (e.key === "Escape") endDrag(); };
      d.tm = (e) => { if (d.on && e.cancelable) e.preventDefault(); };   // sul touch, durante il trascinamento niente scroll
      window.addEventListener("pointermove", d.mv, true);
      window.addEventListener("pointerup", d.up, true);
      window.addEventListener("pointercancel", d.cn, true);
      window.addEventListener("keydown", d.kd, true);
      document.addEventListener("touchmove", d.tm, { capture: true, passive: false });
      if (touch) d.lp = setTimeout(() => { if (drag === d) d.start(); }, 230);   // tocco lungo = afferra la carta
    });
    // niente menu contestuale / selezione mentre si tiene premuta una carta
    root.addEventListener("contextmenu", (e) => { if (drag && drag.on) e.preventDefault(); });
  }

  // ---------------------------------------------------------------- dal testo del diario agli effetti
  function parseNum(s) { const n = parseInt(String(s).replace(/[.,\s ]/g, ""), 10); return isFinite(n) ? n : 0; }
  const NOT_GAIN = /(cost\w*|spend\w*|pagh\w*|serv\w*|occorr\w*|richied\w*|vuole|manc\w*|hai|possiedi|totale|dispon\w*|perdi|perdit\w*|rubat\w*|ruba|\bper|\bdi|[−-])\s*[:(]?\s*$/i;

  function logStones(text) {
    let sum = 0, m;
    const re = /([+−\-−])?\s?(\d[\d., ]*)\s*(?:💎\s*)?pietre/gi;
    while ((m = re.exec(text))) {
      const sign = m[1], n = parseNum(m[2]);
      if (!n || n > 1e9) continue;
      if (sign === "+") { sum += n; continue; }
      if (sign) continue;                                    // segno meno: spesa
      const back = text.slice(Math.max(0, m.index - 22), m.index);
      if (NOT_GAIN.test(back)) continue;
      sum += n;
    }
    const re2 = /pietre(?: spirituali)?\s*\+\s?(\d[\d., ]*)/gi;
    while ((m = re2.exec(text))) sum += parseNum(m[1]);
    return sum;
  }

  const INJURY_OK = /(ferit[ea]|ferite)[^.\n]{0,30}(si richiud|guarisc|guarit|si chiud|curat|svanisc|tolgon|rimargin)|richiude le ferite|le tue ferite (ha|si)|curare|hai ferite da/i;

  function fromLog(text, anchors) {
    const fired = [];
    if (!enabled() || !text) return fired;
    text = String(text);
    anchors = anchors || {};
    const hero = anchors.hero || null, stones = anchors.stones || hero, ring = anchors.ring || hero;
    const plan = [];
    const add = (name, fn) => { fired.push(name); plan.push(fn); };

    const st = logStones(text);
    if (st > 0) add("stones", () => {
      floatText(stones, "+" + fmt(st) + " pietre", "gain");
      burst(stones, "#f2cf5b", clamp(10 + Math.round(Math.log10(st + 1) * 8), 12, 44));
      const p = pt(stones); ringAt(p.x, p.y, toRGB("#f2cf5b"), 6, 46, 2.4, 0.5);
      for (let i = 0; i < 6; i++) P({ kind: "glyph", ch: "◈", x: p.x + rand(-26, 26), y: p.y + rand(-4, 12), vy: rand(-90, -40), g: 120, s0: 11, s1: 14, life: 1, delay: i * 0.05, a: 0.95, rgb: toRGB("#ffe08a"), fp: 1.3 });
    });
    const mStage = /Avanzi allo Strato\s+(\d+)/i.exec(text);
    if (mStage) add("stage", () => {
      qiSpiral(ring, "#3fbf8f");
      floatText(hero || ring, "Strato " + mStage[1], "rare");
      setTimeout(() => { if (enabled()) burst(ring, "#9af0cf", 22); }, 650);
    });
    if (/Il tuo regno si squarcia/i.test(text)) add("breakthrough", () => breakthrough(hero || ring));
    if (/🌀\s*(Qi compresso|COMPRESSIONE|Le fondamenta|Tempra|La tua anima|Sei al colmo)/i.test(text)) add("compressed", () => {
      qiSpiral(ring, "#79e2ff");
      const p = pt(ring); ringAt(p.x, p.y, toRGB("#79e2ff"), 70, 8, 3, 0.9, 0.3);
    });
    if (/⚡\s*TRIBOLAZION/i.test(text)) add("tribulation", () => { lightning(hero || ring); floatText(hero || ring, "TRIBOLAZIONE!", "bad"); });
    const mTit = /Nuovo titolo(?::\s*[«"]([^»"\n]+)[»"])?/i.exec(text);
    if (mTit) add("title", () => {
      floatText(hero || ring, mTit[1] ? "✧ " + mTit[1] + " ✧" : "✧ Nuovo titolo ✧", "rare");
      burst(hero || ring, "#b39bff", 26);
      const p = pt(hero || ring); ringAt(p.x, p.y, toRGB("#cdb6ff"), 8, 80, 3, 0.8);
    });
    const mSaga = /📚\s*Finale scoperto:?\s*([^(\n]*)/i.exec(text);
    if (mSaga) add("saga", () => {
      floatText(hero || ring, "📚 " + (mSaga[1].trim() || "Finale scoperto"), "rare");
      burst(hero || ring, "#cdb6ff", 30);
      for (let i = 0; i < 6; i++) { const p = pt(hero || ring); P({ kind: "glyph", ch: "✦", x: p.x + rand(-60, 60), y: p.y + rand(-10, 30), vy: -60, s0: 16, s1: 22, life: 1.4, delay: i * 0.08, a: 0.9, rgb: toRGB("#e5d8ff"), fp: 1.2 }); }
    });
    if (/ferit/i.test(text) && !INJURY_OK.test(text) && /(resti|sei|esci|rimani|ritrovi|ti|riporti|riporta)\s+(\w+\s+){0,3}ferit|ferita (grave|lieve|profonda)|ti ferisc|ferite? \+|ferito \(/i.test(text)) add("injury", () => {
      floatText(hero, "Ferito", "bad");
      shake(hero, 1.2);
      screenFlash("#b3332a", 0.22, 520);
      const p = pt(hero); for (let i = 0; i < 12; i++) P({ comp: "source-over", rgb: [150, 28, 30], x: p.x, y: p.y, vx: rand(-110, 110), vy: rand(-140, 30), g: 420, life: rand(0.5, 0.9), s0: rand(3, 6), s1: 2, a: 0.8 });
    });
    if (/ti guarda con simpatia|ti considera un amico|ora ti considera|diventa(te)? (tuo )?amic|è ora (tuo )?amic/i.test(text)) add("relation", () => {
      floatText(hero, "♥ legame", "heal");
      burst(hero, "#ff9ab8", 16);
      const p = pt(hero); for (let i = 0; i < 5; i++) P({ kind: "glyph", ch: "♥", x: p.x + rand(-28, 28), y: p.y + rand(-4, 14), vy: rand(-70, -35), s0: 14, s1: 20, life: 1.3, delay: i * 0.1, a: 0.9, rgb: toRGB("#ff7fa6"), fp: 1.2 });
    });
    plan.forEach((fn, i) => setTimeout(() => { if (enabled()) { try { fn(); } catch (e) { if (window.console) console.warn("FX:", e); } } }, i * 320));
    return fired;
  }

  // ---------------------------------------------------------------- API pubblica
  window.FX = {
    version: "1.0",
    enabled, setEnabled, reduced,
    // primitive
    floatText, burst, qiSpiral, slash, projectile, impact, shake, lightning, breakthrough, aura, screenFlash,
    // duello
    duelTurn, enableCardDrag,
    // testo del diario e allenamento
    fromLog, train,
    // utilità
    clear: clearAll,
    elements: EL,
    resetDuel() { lastKey = null; lastHp = { me: null, foe: null }; },
    _stats: () => ({ parts: parts.length, drawers: drawers.length, raf: !!raf })
  };
})();
