/* LiveBG — paesaggio vivo per la scena del luogo: luce del momento, meteo, ambiente, parallasse, tono di combattimento.
   Un solo canvas, niente librerie. API: LiveBG.attach(container, scene) / update(scene) / detach() / setEnabled(b) / enabled().
   scene = { place, weather, time, combat, season? } */
(function () {
  "use strict";
  if (window.LiveBG) return;

  const KEY = "ji_livebg";
  const MAX_PARTICLES = 250;
  const rm = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false, addEventListener() {} };
  const rnd = (a, b) => a + Math.random() * (b - a);
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  let enabledFlag = true;
  try { enabledFlag = localStorage.getItem(KEY) !== "0"; } catch (e) {}

  const S = {
    container: null, view: null, root: null, cv: null, ctx: null, flash: null,
    W: 0, H: 0, dpr: 1, sig: "", sc: null,
    P: [], birds: [], stars: [], starsA: 0,
    raf: 0, last: 0, visible: true, frames: 0,
    io: null, ro: null, mo: null,
    speed: 1, nextBolt: 0, nextBird: 0, par: null, parRaf: 0,
  };

  // ---------------- normalizzazione ----------------
  const TIMES = { alba: "alba", mattina: "mattina", mattino: "mattina", giorno: "giorno", pomeriggio: "pomeriggio", sera: "sera", notte: "notte" };
  function normScene(sc) {
    sc = sc || {};
    const t = String(sc.weather || sc.meteo || "").toLowerCase();
    const storm = /tempest|temporal|fulmin|tuon/.test(t);
    const w = {
      storm,
      snow: /nev|nevic/.test(t),
      rain: storm || /piogg|pioviggin|acquazz|pioved/.test(t),
      fog: /nebbi|foschi|bruma/.test(t),
      wind: storm || /vent|raffic|brezza/.test(t),
    };
    if (w.snow) w.rain = false;
    const place = String(sc.place || "wilderness").toLowerCase();
    return {
      place, w, time: TIMES[String(sc.time || "giorno").toLowerCase()] || "giorno",
      combat: !!sc.combat, season: String(sc.season || "").toLowerCase(),
      indoor: place === "cave",
    };
  }
  const sigOf = (n) => [n.place, n.time, n.combat ? 1 : 0, n.season, n.w.storm ? "T" : "", n.w.rain ? "R" : "", n.w.snow ? "S" : "", n.w.fog ? "F" : "", n.w.wind ? "W" : ""].join("|");

  // ---------------- sprite luminosi ----------------
  const sprites = {};
  function glow(name, r, g, b, core) {
    const c = document.createElement("canvas"); c.width = c.height = 48;
    const x = c.getContext("2d"), gr = x.createRadialGradient(24, 24, 0, 24, 24, 24);
    gr.addColorStop(0, `rgba(${r},${g},${b},${core == null ? 1 : core})`);
    gr.addColorStop(0.3, `rgba(${r},${g},${b},.38)`);
    gr.addColorStop(1, `rgba(${r},${g},${b},0)`);
    x.fillStyle = gr; x.fillRect(0, 0, 48, 48); sprites[name] = c;
  }
  glow("ff", 214, 255, 120); glow("qi", 140, 240, 205); glow("qic", 150, 205, 255, .9);
  glow("em", 255, 138, 58); (function () { const c = document.createElement("canvas"); c.width = c.height = 48; const x = c.getContext("2d"), g = x.createRadialGradient(24, 24, 0, 24, 24, 24);
    g.addColorStop(0, "rgba(255,255,255,1)"); g.addColorStop(0.42, "rgba(255,255,255,.92)"); g.addColorStop(0.62, "rgba(255,255,255,.28)"); g.addColorStop(1, "rgba(255,255,255,0)");
    x.fillStyle = g; x.fillRect(0, 0, 48, 48); sprites.snow = c; })(); glow("dust", 232, 214, 173, .8);

  // ---------------- bersagli per tipo di particella ----------------
  function targets() {
    const n = S.sc, w = n.w, T = {};
    const area = clamp((S.W * S.H) / (1100 * 690), 0.6, 1.15);
    const out = !n.indoor, dayt = n.time !== "notte" && n.time !== "sera";
    const cm = n.combat ? 1.25 : 1;
    if (out) {
      if (w.storm) T.rain = 175; else if (w.rain) T.rain = 115;
      if (w.snow) T.snow = 85;
      if (w.wind) T.leaf = w.storm ? 30 : 24;
      if (n.place === "forest" || n.place === "sect") { if (w.wind || n.season === "primavera") T.leaf = Math.max(T.leaf || 0, w.wind ? 24 : 7); }
    }
    const bad = w.rain || w.snow;
    if (n.time === "notte" && !bad && (n.place === "forest" || n.place === "lake")) T.firefly = 20;
    if (n.place === "sect") T.qi = 30 * cm;
    if (n.place === "cave") T.qi = 34 * cm;
    if (n.place === "forbidden_zone") T.ember = 36 * cm;
    if ((n.place === "ruin" || n.place === "wilderness") && !bad) T.dust = 32;
    let tot = 0; for (const k in T) { T[k] = Math.round(T[k] * area); tot += T[k]; }
    const room = MAX_PARTICLES - 60 - 18;   // spazio per stelle (~56), spruzzi e uccelli
    if (tot > room) { const f = room / tot; for (const k in T) T[k] = Math.floor(T[k] * f); }
    return T;
  }

  // ---------------- generazione ----------------
  const PETAL = ["#f6b9cc", "#f3a3bd", "#ffd6e2", "#f9c8d6"];
  const LEAF = ["#8fb06a", "#a7bb62", "#c9a94e", "#7b9a5c"];
  const AUTUMN = ["#c9803a", "#b5532f", "#d9a441", "#9a5a2c"];
  function leafColor() {
    const n = S.sc;
    if ((n.place === "forest" || n.place === "sect") && n.season !== "autunno" && n.season !== "inverno") return PETAL[(Math.random() * 4) | 0];
    return (n.season === "autunno" ? AUTUMN : LEAF)[(Math.random() * 4) | 0];
  }
  function spawn(p, init) {
    const W = S.W, H = S.H, k = p.k;
    if (p.f === undefined) { p.f = init ? 1 : 0; p.ft = 1; }
    if (k === "rain") {
      const st = S.sc.w.storm;
      p.vy = rnd(640, 900) * (st ? 1.25 : 1); p.vx = -p.vy * (st ? 0.36 : 0.2);
      p.x = rnd(-0.15 * W, 1.15 * W); p.gy = H * rnd(0.52, 0.99);
      p.y = init ? rnd(-30, p.gy) : rnd(-60, -8); p.len = rnd(9, 20); p.z = Math.random() < 0.4 ? 0 : 1;
    } else if (k === "snow") {
      p.x = rnd(-20, W + 20); p.y = init ? rnd(0, H) : rnd(-12, -2); p.vy = rnd(22, 52); p.vx = S.sc.w.wind ? -rnd(20, 50) : 0;
      p.sw = rnd(8, 22); p.fr = rnd(0.6, 1.6); p.ph = rnd(0, 6.28); p.s = rnd(2.6, 7.5); p.a = rnd(0.55, 1);
    } else if (k === "leaf") {
      p.x = init ? rnd(0, W) : -rnd(10, 60); p.y = rnd(0.05, 0.85) * H;
      p.vx = rnd(55, 120) * (S.sc.w.storm ? 1.6 : 1); p.vy = rnd(6, 26); p.ph = rnd(0, 6.28); p.fr = rnd(0.8, 2);
      p.r = rnd(0, 6.28); p.vr = rnd(-2.2, 2.2); p.s = rnd(4, 8.5); p.c = leafColor(); p.a = rnd(0.55, 0.85);
    } else if (k === "firefly") {
      p.x = rnd(0.04, 0.96) * W; p.y = rnd(0.35, 0.95) * H; p.an = rnd(0, 6.28); p.sp = rnd(8, 20);
      p.ph = rnd(0, 6.28); p.fr = rnd(0.7, 1.8); p.s = rnd(12, 22);
    } else if (k === "qi") {
      p.x = rnd(0, W); p.y = init ? rnd(0, H) : H + rnd(4, 30); p.vy = -rnd(8, 24); p.sw = rnd(6, 18); p.fr = rnd(0.3, 0.9);
      p.ph = rnd(0, 6.28); p.s = rnd(6, 15); p.a = rnd(0.35, 0.8); p.sp = S.sc.place === "cave" ? "qic" : "qi";
    } else if (k === "ember") {
      p.x = rnd(0, W); p.y = init ? rnd(0.3 * H, H) : H * rnd(0.85, 1.02); p.vy = -rnd(24, 58); p.sw = rnd(6, 20); p.fr = rnd(0.6, 1.6);
      p.ph = rnd(0, 6.28); p.s = rnd(5, 11); p.life = init ? rnd(0, 5) : 0; p.max = rnd(3.5, 6.5);
    } else if (k === "dust") {
      p.x = rnd(0, W); p.y = rnd(0.1, 1) * H; p.vx = rnd(6, 22) * (S.sc.w.wind ? 3 : 1); p.vy = rnd(-3, 3);
      p.ph = rnd(0, 6.28); p.fr = rnd(0.3, 0.9); p.s = rnd(4, 11); p.a = rnd(0.12, 0.3);
    } else if (k === "splash") {
      p.life = 0; p.max = rnd(0.22, 0.34); p.s = rnd(2.5, 5);
    }
    return p;
  }

  function reconcile() {
    const T = targets(), cnt = {};
    for (const p of S.P) if (!p.dead && p.k !== "splash") cnt[p.k] = (cnt[p.k] || 0) + 1;
    for (const k in T) for (let i = cnt[k] || 0; i < T[k]; i++) S.P.push(spawn({ k, t: 0, f: 0, ft: 1 }, true));
    // eccesso: dissolvenza
    const seen = {};
    for (const p of S.P) {
      if (p.k === "splash") continue;
      seen[p.k] = (seen[p.k] || 0) + 1;
      p.ft = seen[p.k] <= (T[p.k] || 0) ? 1 : 0;
    }
    if (S.lastPlace !== S.sc.place) { S.lastPlace = S.sc.place; for (const p of S.P) if (p.k === "leaf") p.c = leafColor(); }
  }

  function makeStars() {
    S.stars = [];
    for (let i = 0; i < 56; i++) S.stars.push({ x: Math.random(), y: Math.pow(Math.random(), 1.4) * 0.52, r: rnd(0.6, 1.7), ph: rnd(0, 6.28), fr: rnd(0.6, 2.2), a: rnd(0.35, 1) });
  }

  // ---------------- DOM ----------------
  function buildRoot() {
    const r = document.createElement("div");
    r.className = "lbg"; r.setAttribute("aria-hidden", "true");
    r.innerHTML = '<div class="lbg-light"><i data-t="alba"></i><i data-t="mattina"></i><i data-t="giorno"></i><i data-t="pomeriggio"></i><i data-t="sera"></i><i data-t="notte"></i></div>' +
      '<div class="lbg-wx"></div><div class="lbg-fog"><i></i><i></i><i></i></div><canvas class="lbg-cv"></canvas>' +
      '<div class="lbg-flash"></div><div class="lbg-combat"></div>';
    S.root = r; S.cv = r.querySelector(".lbg-cv"); S.ctx = S.cv.getContext("2d"); S.flash = r.querySelector(".lbg-flash");
  }

  function mount() {
    const c = S.container; if (!c) return false;
    const v = c.querySelector(".stg-view"), w = v && v.querySelector(".stg-world");
    if (!w) return false;
    if (S.root.parentNode !== w) w.insertBefore(S.root, w.querySelector(".stg-par.p3") || null);
    if (S.view !== v) {
      S.view = v;
      if (S.io) S.io.disconnect(); if (S.ro) S.ro.disconnect();
      if (typeof IntersectionObserver === "function") { S.io = new IntersectionObserver((e) => { S.visible = e[e.length - 1].isIntersecting; sync(); }); S.io.observe(v); }
      if (typeof ResizeObserver === "function") { S.ro = new ResizeObserver(resize); S.ro.observe(v); }
    }
    v.classList.add("livebg-on");
    resize();
    return true;
  }

  function resize() {
    if (!S.view) return;
    const W = S.view.clientWidth, H = S.view.clientHeight; if (!W || !H) return;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    if (W === S.W && H === S.H && dpr === S.dpr) return;
    S.W = W; S.H = H; S.dpr = dpr;
    S.cv.width = Math.round(W * dpr); S.cv.height = Math.round(H * dpr);
    S.cv.style.width = W + "px"; S.cv.style.height = H + "px";
    if (S.sc) reconcile();
    if (rm.matches || !S.raf) drawFrame(0);
  }

  // ---------------- API ----------------
  function attach(container, scene) {
    if (!container) return;
    if (S.container && S.container !== container) detach();
    if (!S.root) buildRoot();
    if (!S.stars.length) makeStars();
    if (S.container !== container) {
      S.container = container;
      container.addEventListener("pointermove", onMove);
      container.addEventListener("pointerleave", onLeave);
      S.mo = new MutationObserver(() => { if (S.root && !S.root.isConnected) { mount(); apply(true); sync(); } });
      S.mo.observe(container, { childList: true });
    }
    mount();
    update(scene);
  }

  function update(scene) {
    if (!S.container) return;
    if (scene) { const n = normScene(scene), sg = sigOf(n); if (sg === S.sig && S.root.isConnected) { return; } S.sc = n; S.sig = sg; }
    if (!S.sc) return;
    if (!S.root.isConnected && !mount()) return;
    apply(false); sync();
  }

  function apply(force) {
    const n = S.sc, r = S.root; if (!n) return;
    r.dataset.time = n.time; r.dataset.place = n.place;
    r.classList.toggle("is-fog", n.w.fog); r.classList.toggle("is-rain", n.w.rain && !n.w.storm);
    r.classList.toggle("is-storm", n.w.storm); r.classList.toggle("is-snow", n.w.snow);
    r.classList.toggle("is-combat", n.combat); r.classList.toggle("is-in", n.indoor);
    r.hidden = !enabledFlag;
    if (S.view) S.view.classList.toggle("livebg-off", !enabledFlag);
    if (S.W) { reconcile(); }
    if (rm.matches || !S.raf) drawFrame(0);
  }

  function detach() {
    cancelAnimationFrame(S.raf); S.raf = 0;
    if (S.container) { S.container.removeEventListener("pointermove", onMove); S.container.removeEventListener("pointerleave", onLeave); }
    if (S.io) S.io.disconnect(); if (S.ro) S.ro.disconnect(); if (S.mo) S.mo.disconnect();
    S.io = S.ro = S.mo = null;
    if (S.view) { S.view.classList.remove("livebg-on", "livebg-off"); const bg = S.view.querySelector(".stg-bg"); if (bg) bg.style.translate = ""; }
    if (S.root && S.root.parentNode) S.root.parentNode.removeChild(S.root);
    S.container = S.view = null; S.sig = ""; S.sc = null; S.P = []; S.birds = []; S.W = S.H = 0; S.starsA = 0; S.visible = true;
  }

  function setEnabled(b) {
    enabledFlag = !!b;
    try { localStorage.setItem(KEY, enabledFlag ? "1" : "0"); } catch (e) {}
    if (S.root) { S.root.hidden = !enabledFlag; if (S.view) S.view.classList.toggle("livebg-off", !enabledFlag); if (!enabledFlag) resetPar(); }
    sync();
  }

  // ---------------- ciclo ----------------
  function wantsLoop() {
    if (!S.root || !S.sc || !enabledFlag || document.hidden || !S.visible || rm.matches || !S.root.isConnected) return false;
    return true;
  }
  function sync() {
    if (wantsLoop()) { if (!S.raf) { S.last = performance.now(); S.raf = requestAnimationFrame(frame); } }
    else if (S.raf) { cancelAnimationFrame(S.raf); S.raf = 0; }
  }
  function frame(ts) {
    S.raf = 0;
    if (!wantsLoop()) return;
    const dt = clamp((ts - S.last) / 1000 || 0.016, 0.001, 0.05); S.last = ts;
    S.speed += ((S.sc.combat ? 1.7 : 1) - S.speed) * Math.min(1, dt * 2.5);
    step(dt, ts); drawFrame(dt); S.frames++;
    S.raf = requestAnimationFrame(frame);
  }
  document.addEventListener("visibilitychange", sync);
  if (rm.addEventListener) rm.addEventListener("change", () => { sync(); if (S.root) { apply(true); } });

  // ---------------- simulazione ----------------
  function step(dt, ts) {
    const W = S.W, H = S.H, sp = S.speed, t = ts / 1000, P = S.P, n = S.sc;
    let spl = 0; for (const p of P) if (p.k === "splash") spl++;
    for (let i = P.length - 1; i >= 0; i--) {
      const p = P[i], d = dt * sp;
      p.f += (p.ft - p.f) * Math.min(1, dt * 1.6);
      if (p.ft === 0 && p.f < 0.02) { P.splice(i, 1); continue; }
      switch (p.k) {
        case "rain":
          p.x += p.vx * d; p.y += p.vy * d;
          if (p.y >= p.gy) {
            if (spl < 22 && Math.random() < 0.22 && p.ft) { P.push(spawn({ k: "splash", t: 0, x: p.x, y: p.gy }, true)); spl++; }
            if (p.ft) spawn(p, false); else p.f = 0;
          }
          break;
        case "snow":
          p.y += p.vy * d; p.x += (p.vx + Math.sin(t * p.fr + p.ph) * p.sw * 0.6) * d;
          if (p.y > H + 8 || p.x < -30 || p.x > W + 30) { if (p.ft) spawn(p, false); else p.f = 0; }
          break;
        case "leaf":
          p.x += p.vx * d; p.y += (p.vy + Math.sin(t * p.fr + p.ph) * 22) * d; p.r += p.vr * d;
          if (p.x > W + 20 || p.y > H + 10) { if (p.ft) spawn(p, false); else p.f = 0; }
          break;
        case "firefly":
          p.an += (Math.random() - 0.5) * 2.2 * dt; p.x += Math.cos(p.an) * p.sp * d; p.y += Math.sin(p.an) * p.sp * d * 0.7;
          if (p.x < 0 || p.x > W) p.an = Math.PI - p.an;
          if (p.y < 0.3 * H || p.y > H) p.an = -p.an;
          break;
        case "qi":
          p.y += p.vy * d; p.x += Math.sin(t * p.fr + p.ph) * p.sw * d;
          if (p.y < -20) { if (p.ft) spawn(p, false); else p.f = 0; }
          break;
        case "ember":
          p.life += d; p.y += p.vy * d; p.x += Math.sin(t * p.fr + p.ph) * p.sw * d;
          if (p.life > p.max || p.y < -10) { if (p.ft) spawn(p, false); else p.f = 0; }
          break;
        case "dust":
          p.x += p.vx * d + Math.sin(t * p.fr + p.ph) * 4 * d; p.y += (p.vy + Math.cos(t * p.fr + p.ph) * 4) * d;
          if (p.x > W + 12) p.x = -10;
          if (p.y < -10) p.y = H; else if (p.y > H + 10) p.y = 0;
          break;
        case "splash":
          p.life += dt; if (p.life > p.max) P.splice(i, 1);
          break;
      }
    }
    // stelle
    const wantStars = n.time === "notte" && !n.indoor && !n.w.rain && !n.w.snow;
    S.starsA += ((wantStars ? (n.w.fog ? 0.45 : 1) : 0) - S.starsA) * Math.min(1, dt * 1.2);
    // uccelli
    const calm = !n.w.rain && !n.w.snow && !n.w.storm;
    const dayt = n.time === "alba" || n.time === "mattina" || n.time === "giorno" || n.time === "pomeriggio";
    if ((n.place === "mountain" || n.place === "lake") && dayt && calm && !n.indoor && S.birds.length < 2 && ts > S.nextBird) {
      const cnt = 1 + ((Math.random() * 3) | 0), dir = Math.random() < 0.5 ? 1 : -1, y0 = rnd(0.08, 0.34) * H, v = rnd(34, 62);
      for (let i = 0; i < cnt; i++) S.birds.push({ x: dir > 0 ? -20 - i * rnd(18, 34) : W + 20 + i * rnd(18, 34), y: y0 + rnd(-10, 10) + i * 5, v: v * dir * rnd(0.92, 1.08), s: rnd(4.5, 8), ph: rnd(0, 6.28), fr: rnd(5, 7.5), wob: rnd(0.3, 0.8) });
      S.nextBird = ts + rnd(9000, 22000);
    } else if (!S.nextBird) S.nextBird = ts + rnd(2500, 6000);
    for (let i = S.birds.length - 1; i >= 0; i--) {
      const b = S.birds[i]; b.x += b.v * dt * sp; b.y += Math.sin(t * b.wob + b.ph) * 4 * dt;
      if (b.x < -60 || b.x > W + 60) S.birds.splice(i, 1);
    }
    // lampo
    if (n.w.storm) {
      if (!S.nextBolt) S.nextBolt = ts + rnd(2500, 6000);
      if (ts > S.nextBolt) {
        S.nextBolt = ts + rnd(5000, 12000);
        if (S.flash && S.flash.animate) S.flash.animate([{ opacity: 0 }, { opacity: 0.55, offset: 0.07 }, { opacity: 0.1, offset: 0.2 }, { opacity: 0.4, offset: 0.3 }, { opacity: 0 }], { duration: 700, easing: "ease-out" });
      }
    } else S.nextBolt = 0;
  }

  // ---------------- disegno ----------------
  function drawFrame(dt) {
    const ctx = S.ctx; if (!ctx || !S.W) return;
    const W = S.W, H = S.H, d = S.dpr, t = performance.now() / 1000;
    ctx.setTransform(d, 0, 0, d, 0, 0); ctx.clearRect(0, 0, W, H);
    if (!enabledFlag) return;
    const still = rm.matches;
    // stelle (in quiete: un fotogramma fisso)
    const sa = still ? (S.sc && S.sc.time === "notte" && !S.sc.indoor && !S.sc.w.rain && !S.sc.w.snow ? 1 : 0) : S.starsA;
    if (sa > 0.01) {
      ctx.fillStyle = "#eaf0ff";
      for (const s of S.stars) {
        const tw = still ? 0.7 : 0.3 + 0.7 * (0.5 + 0.5 * Math.sin(t * s.fr + s.ph));
        ctx.globalAlpha = sa * s.a * tw * 0.9;
        ctx.beginPath(); ctx.arc(s.x * W, s.y * H, s.r, 0, 6.2832); ctx.fill();
      }
    }
    if (still) { ctx.globalAlpha = 1; return; }
    // pioggia: due lotti in un solo tracciato ciascuno
    const rain = [[], []];
    for (const p of S.P) if (p.k === "rain") rain[p.z].push(p);
    for (let z = 0; z < 2; z++) {
      if (!rain[z].length) continue;
      ctx.beginPath();
      for (const p of rain[z]) {
        const k = p.len / p.vy; ctx.moveTo(p.x, p.y); ctx.lineTo(p.x + p.vx * k * 1.0, p.y + p.len);
      }
      ctx.globalAlpha = (z ? 0.62 : 0.36) * (rain[z][0].f > 0.99 ? 1 : rain[z][0].f);
      ctx.strokeStyle = "#d2e4f4"; ctx.lineWidth = z ? 1.3 : 0.9; ctx.lineCap = "round"; ctx.stroke();
    }
    for (const p of S.P) {
      const f = p.f;
      switch (p.k) {
        case "snow": ctx.globalAlpha = p.a * f; ctx.drawImage(sprites.snow, p.x - p.s, p.y - p.s, p.s * 2, p.s * 2); break;
        case "leaf":
          ctx.globalAlpha = p.a * f; ctx.fillStyle = p.c;
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.scale(1, 0.5 + 0.5 * Math.abs(Math.sin(p.r * 0.7)));
          ctx.beginPath(); ctx.ellipse(0, 0, p.s, p.s * 0.52, 0, 0, 6.2832); ctx.fill(); ctx.restore(); break;
        case "firefly": {
          const pl = Math.pow(0.5 + 0.5 * Math.sin(t * p.fr + p.ph), 2.2);
          ctx.globalAlpha = (0.1 + 0.85 * pl) * f; ctx.drawImage(sprites.ff, p.x - p.s / 2, p.y - p.s / 2, p.s, p.s); break;
        }
        case "qi": {
          const e = clamp(p.y / S.H, 0, 1), env = Math.sin(clamp(1 - e, 0, 1) * Math.PI) ;
          ctx.globalAlpha = p.a * (0.3 + 0.7 * Math.abs(Math.sin(t * p.fr * 2 + p.ph))) * clamp(env * 1.4, 0, 1) * f;
          ctx.drawImage(sprites[p.sp], p.x - p.s / 2, p.y - p.s / 2, p.s, p.s); break;
        }
        case "ember": {
          const u = p.life / p.max, al = Math.sin(clamp(u, 0, 1) * Math.PI) * (0.6 + 0.4 * Math.sin(t * 14 + p.ph));
          ctx.globalAlpha = clamp(al, 0, 1) * 0.9 * f; const s = p.s * (1 - u * 0.5);
          ctx.drawImage(sprites.em, p.x - s / 2, p.y - s / 2, s, s); break;
        }
        case "dust": ctx.globalAlpha = p.a * (0.5 + 0.5 * Math.sin(t * p.fr + p.ph)) * f; ctx.drawImage(sprites.dust, p.x - p.s, p.y - p.s, p.s * 2, p.s * 2); break;
        case "splash": {
          const u = p.life / p.max; ctx.globalAlpha = (1 - u) * 0.38; ctx.strokeStyle = "#dbeaf6"; ctx.lineWidth = 0.8;
          ctx.beginPath(); ctx.ellipse(p.x, p.y, p.s * (0.4 + u * 1.6), p.s * (0.4 + u * 1.6) * 0.38, 0, 0, 6.2832); ctx.stroke(); break;
        }
      }
    }
    // uccelli
    if (S.birds.length) {
      ctx.strokeStyle = S.sc.time === "alba" ? "rgba(70,36,48,.62)" : "rgba(18,24,30,.55)"; ctx.lineWidth = 1.35; ctx.lineCap = "round"; ctx.globalAlpha = 1;
      for (const b of S.birds) {
        const fl = Math.sin(t * b.fr + b.ph) * 0.8, w = b.s;
        ctx.beginPath(); ctx.moveTo(b.x - w, b.y - fl * w * 0.9); ctx.quadraticCurveTo(b.x - w * 0.4, b.y - w * 0.5 * (0.4 + fl * 0.6) , b.x, b.y);
        ctx.quadraticCurveTo(b.x + w * 0.4, b.y - w * 0.5 * (0.4 + fl * 0.6), b.x + w, b.y - fl * w * 0.9); ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }

  // ---------------- parallasse ----------------
  function onMove(ev) {
    if (ev.pointerType === "touch" || rm.matches || !enabledFlag || !S.view) return;
    const r = S.view.getBoundingClientRect(); if (!r.width) return;
    const nx = clamp(((ev.clientX - r.left) / r.width - 0.5) * 2, -1, 1), ny = clamp(((ev.clientY - r.top) / r.height - 0.5) * 2, -1, 1);
    S.par = { nx, ny };
    if (!S.parRaf) S.parRaf = requestAnimationFrame(applyPar);
  }
  function applyPar() {
    S.parRaf = 0; if (!S.par || !S.view || !S.root) return;
    const { nx, ny } = S.par, bg = S.view.querySelector(".stg-bg");
    S.root.style.translate = (-nx * 8).toFixed(2) + "px " + (-ny * 5).toFixed(2) + "px";
    if (bg) bg.style.translate = (-nx * 6).toFixed(2) + "px " + (-ny * 4).toFixed(2) + "px";
  }
  function resetPar() {
    S.par = { nx: 0, ny: 0 }; if (S.view) applyPar(); else if (S.root) S.root.style.translate = "";
  }
  function onLeave() { resetPar(); }

  window.LiveBG = {
    attach, update, detach, setEnabled, enabled: () => enabledFlag,
    running: () => !!S.raf, frames: () => S.frames, particles: () => S.P.length,
  };
})();
