// Jade Immortal — L'AMBIENTE SONORO PROCEDURALE.
// Niente file audio: ogni suono nasce dal Web Audio API (rumore filtrato, oscillatori, FM, riverbero generato).
// Ogni luogo ha il suo paesaggio sonoro; meteo, ora del giorno e combattimento si sovrappongono al fondale.
// L'audio parte solo dopo un gesto dell'utente (setOn(true) da un clic). Effetti isolati (cue) con interruttore a parte.
"use strict";
(function () {
  const AC = window.AudioContext || window.webkitAudioContext;
  const K = { on: "ji_amb", vol: "ji_amb_vol", cues: "ji_amb_cues" };
  const store = { get: (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* niente */ } } };

  const PLACES = ["mountain", "forest", "city", "village", "sect", "ruin", "cave", "lake", "wilderness", "forbidden_zone"];
  const WEATHERS = ["", "pioggia", "neve", "nebbia", "vento", "tempesta"];
  const TIMES = ["alba", "mattino", "giorno", "pomeriggio", "sera", "notte"];
  const TC = { alba: "m", mattino: "m", giorno: "d", pomeriggio: "d", sera: "e", notte: "n" };   // classi di ora
  const ALIAS = { montagna: "mountain", foresta: "forest", bosco: "forest", citta: "city", "città": "city", villaggio: "village", setta: "sect",
    rovine: "ruin", rovina: "ruin", caverna: "cave", grotta: "cave", lago: "lake", natura: "wilderness", terre_selvagge: "wilderness",
    zona_proibita: "forbidden_zone", forbidden: "forbidden_zone" };
  const LABEL = { mountain: "Montagna", forest: "Foresta", city: "Città", village: "Villaggio", sect: "Setta", ruin: "Rovine", cave: "Caverna",
    lake: "Lago", wilderness: "Terre selvagge", forbidden_zone: "Zona proibita" };

  const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
  const rnd = (a, b) => a + Math.random() * (b - a);
  const pick = (a) => a[Math.floor(Math.random() * a.length)];

  let ON = store.get(K.on, "0") === "1";
  let VOL = (() => { const v = parseFloat(store.get(K.vol, "0.35")); return isFinite(v) ? clamp(v, 0, 1) : 0.35; })();
  let CUES_PREF = store.get(K.cues, null);          // null = segue on()
  // (Agg. 84) gli effetti isolati (sfondamento, fulmini, apparizioni, critici) seguono di base i «Suoni», non l'ambiente
  const cuesOn = () => (CUES_PREF === null ? store.get("ji_sound", "1") !== "0" : CUES_PREF === "1");

  let G = null;                                     // grafo audio corrente
  let want = null;                                  // scena richiesta (normalizzata)
  let bedL = null, wxL = null, cbL = null;          // strati attivi: fondale, meteo, combattimento
  let appBed = null, appWx = null, appCb = null;    // ciò che è effettivamente applicato
  let fading = [];                                  // strati in dissolvenza
  let applyTimer = 0, idleTimer = 0, lastCue = 0;
  const lastByName = {};
  const live = new Set();                           // nodi audio vivi (per il controllo del carico)
  const reg = (n) => { live.add(n); return n; };

  const calm = () => { const w = want ? want.weather : ""; return w === "" || w === "nebbia" || w === "vento"; };   // niente uccelli/grilli con pioggia o neve

  // ------------------------------------------------------------------ grafo di base
  function build(ctx, offline) {
    const g = { ctx, offline, nb: null, ir: null, lfo: [] };
    g.bus = reg(ctx.createGain());  g.bus.gain.value = offline ? 1 : 0;    // fondale (sale/scende con on/off e combattimento)
    g.tone = reg(ctx.createBiquadFilter()); g.tone.type = "lowpass"; g.tone.frequency.value = 16000; g.tone.Q.value = 0.5;
    g.cue = reg(ctx.createGain());                                           // effetti isolati
    g.comp = reg(ctx.createDynamicsCompressor());
    g.comp.threshold.value = -14; g.comp.knee.value = 12; g.comp.ratio.value = 6; g.comp.attack.value = 0.004; g.comp.release.value = 0.22;
    g.soft = reg(ctx.createWaveShaper());                                    // limite morbido: l'uscita non supera 0.9
    const N = 2049, c = new Float32Array(N);
    for (let i = 0; i < N; i++) { const x = (i / (N - 1)) * 2 - 1, a = Math.abs(x); c[i] = Math.sign(x) * (a <= 0.6 ? a : 0.6 + 0.35 * Math.tanh((a - 0.6) / 0.35)); }
    g.soft.curve = c;
    g.out = reg(ctx.createGain()); g.out.gain.value = offline ? 1 : VOL;
    g.bus.connect(g.tone); g.tone.connect(g.comp); g.cue.connect(g.comp);
    g.comp.connect(g.soft); g.soft.connect(g.out); g.out.connect(ctx.destination);
    [0.05, 0.11, 0.27].forEach((f) => { const o = reg(ctx.createOscillator()); o.frequency.value = f; o.start(); g.lfo.push(o); });   // LFO lenti condivisi
    return g;
  }

  function boot() {
    if (G) return G;
    if (!AC) return null;
    let ctx;
    try { ctx = new AC({ latencyHint: "playback" }); } catch (e) { try { ctx = new AC(); } catch (e2) { return null; } }
    G = build(ctx, false);
    return G;
  }

  function resume() {
    if (!G) return;
    try { if (G.ctx.state !== "running") { const p = G.ctx.resume(); if (p && p.catch) p.catch(() => {}); } } catch (e) { /* niente */ }
  }

  // ------------------------------------------------------------------ buffer condivisi
  function noiseBuf(g, kind) {
    if (!g.nb) g.nb = {};
    if (g.nb[kind]) return g.nb[kind];
    const sr = g.ctx.sampleRate, len = Math.floor(sr * 3), buf = g.ctx.createBuffer(1, len, sr), d = buf.getChannelData(0);
    if (kind === "white") { for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1; }
    else {
      let last = 0;
      for (let i = 0; i < len; i++) { last = (last + 0.03 * (Math.random() * 2 - 1)) / 1.03; d[i] = last; }
      const X = Math.floor(sr * 0.15);                                      // chiude il ciclo senza scatti
      for (let i = 0; i < X; i++) { const k = i / X; d[i] = d[i] * k + d[len - X + i] * (1 - k); }
      let mx = 0; for (let i = 0; i < len; i++) mx = Math.max(mx, Math.abs(d[i]));
      const s = 0.8 / (mx || 1); for (let i = 0; i < len; i++) d[i] *= s;
    }
    g.nb[kind] = buf;
    return buf;
  }

  function irBuf(g) {
    if (g.ir) return g.ir;
    const sr = g.ctx.sampleRate, len = Math.floor(sr * 2.4), buf = g.ctx.createBuffer(2, len, sr);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) { const t = i / len; d[i] = (Math.random() * 2 - 1) * Math.pow(1 - t, 3.2) * Math.min(1, i / (sr * 0.012)); }
    }
    g.ir = buf;
    return buf;
  }

  // ------------------------------------------------------------------ voci isolate (nodi che si auto-eliminano)
  function track(list, src) {
    list.forEach(reg);
    src.onended = () => { list.forEach((n) => { try { n.disconnect(); } catch (e) { /* già staccato */ } live.delete(n); }); };
  }

  function mkPan(g, list, tail, dest, p) {
    if (p && g.ctx.createStereoPanner) { const pn = g.ctx.createStereoPanner(); pn.pan.value = clamp(p, -1, 1); tail.connect(pn); pn.connect(dest); list.push(pn); }
    else tail.connect(dest);
  }

  // o: type f f2 glide t a d v lp pan det fm{r,i,f}
  function tone(g, dest, o) {
    const ctx = g.ctx, t = o.t, a = o.a == null ? 0.005 : o.a, end = t + a + o.d + 0.06;
    const osc = ctx.createOscillator(), gn = ctx.createGain(), list = [osc, gn];
    osc.type = o.type || "sine";
    osc.frequency.setValueAtTime(o.f, t);
    if (o.f2) osc.frequency.exponentialRampToValueAtTime(o.f2, t + (o.glide || (a + o.d)));
    if (o.det) osc.detune.value = o.det;
    gn.gain.setValueAtTime(0.0001, t);
    gn.gain.linearRampToValueAtTime(o.v, t + Math.max(a, 0.001));
    gn.gain.exponentialRampToValueAtTime(0.0001, t + Math.max(a, 0.001) + o.d);
    let tail = osc;
    if (o.lp) { const f = ctx.createBiquadFilter(); f.type = "lowpass"; f.frequency.value = o.lp; tail.connect(f); tail = f; list.push(f); }
    tail.connect(gn);
    if (o.fm) {
      const m = ctx.createOscillator(), mg = ctx.createGain();
      m.frequency.value = o.fm.f || o.f * (o.fm.r || 2); mg.gain.value = o.fm.i;
      m.connect(mg); mg.connect(osc.frequency); m.start(t); m.stop(end); list.push(m, mg);
    }
    mkPan(g, list, gn, dest, o.pan);
    osc.start(t); osc.stop(end);
    track(list, osc);
    return osc;
  }

  // o: kind ft f f2 glide q t a d v pan shape[[dt,level]...]  (shape sostituisce a/d)
  function burst(g, dest, o) {
    const ctx = g.ctx, t = o.t, src = ctx.createBufferSource(), gn = ctx.createGain(), list = [src, gn];
    src.buffer = noiseBuf(g, o.kind || "white");
    let tail = src, dur;
    if (o.ft) {
      const f = ctx.createBiquadFilter(); f.type = o.ft; f.Q.value = o.q || 0.8;
      f.frequency.setValueAtTime(o.f, t);
      if (o.f2) f.frequency.exponentialRampToValueAtTime(o.f2, t + (o.glide || 1));
      tail.connect(f); tail = f; list.push(f);
    }
    tail.connect(gn);
    gn.gain.setValueAtTime(0.0001, t);
    if (o.shape) {
      o.shape.forEach((s) => gn.gain.linearRampToValueAtTime(Math.max(s[1], 0.0001) * o.v, t + s[0]));
      dur = o.shape[o.shape.length - 1][0];
    } else {
      const a = o.a == null ? 0.003 : o.a;
      gn.gain.linearRampToValueAtTime(o.v, t + a); gn.gain.exponentialRampToValueAtTime(0.0001, t + a + o.d); dur = a + o.d;
    }
    mkPan(g, list, gn, dest, o.pan);
    src.start(t, Math.random() * 2.5); src.stop(t + dur + 0.06);
    track(list, src);
    return src;
  }

  function bell(g, dest, t, f0, vol, len) {
    [[1, 1, 1], [2.0, 0.5, 0.62], [2.76, 0.45, 0.45], [4.07, 0.25, 0.3], [5.4, 0.14, 0.2]].forEach((p) =>
      tone(g, dest, { f: f0 * p[0] * (1 + rnd(-0.002, 0.002)), t, a: 0.004, d: len * p[2], v: vol * p[1] }));
    burst(g, dest, { kind: "white", ft: "bandpass", f: f0 * 6, q: 1.2, t, a: 0.001, d: 0.035, v: vol * 0.3 });
  }

  function thunder(g, dest, t, vol, far) {
    if (!far) burst(g, dest, { kind: "white", ft: "highpass", f: 1800, q: 0.7, t, a: 0.002, d: 0.08, v: vol * 0.8 });
    burst(g, dest, { kind: "brown", ft: "lowpass", f: far ? 520 : 1000, f2: 70, glide: 3.4, q: 0.9, t: t + (far ? 0 : 0.03),
      shape: far ? [[0, 0], [0.5, 1], [1.2, 0.5], [1.7, 0.85], [3.2, 0.35], [4.6, 0]] : [[0, 0], [0.04, 1], [0.5, 0.45], [0.8, 0.8], [1.6, 0.4], [2.4, 0.5], [4.2, 0]], v: vol * 2.4 });
    tone(g, dest, { f: 62, f2: 30, glide: 2.4, t: t + 0.02, a: 0.05, d: 2.4, v: vol * 0.55 });
  }

  function birdPhrase(g, dest, t, vol) {
    const ctx = g.ctx, n = 2 + Math.floor(Math.random() * 4), base = rnd(2300, 4300), step = rnd(0.09, 0.17), end = t + n * step + 0.15;
    const osc = ctx.createOscillator(), gn = ctx.createGain(), m = ctx.createOscillator(), mg = ctx.createGain(), list = [osc, gn, m, mg];
    m.frequency.value = base * rnd(0.6, 1.6); mg.gain.value = rnd(150, 520);
    m.connect(mg); mg.connect(osc.frequency); osc.connect(gn);
    gn.gain.setValueAtTime(0.0001, t);
    for (let i = 0; i < n; i++) {
      const bt = t + i * step, f0 = base * rnd(0.9, 1.15), f1 = f0 * (Math.random() < 0.5 ? rnd(1.15, 1.5) : rnd(0.6, 0.85));
      osc.frequency.setValueAtTime(f0, bt); osc.frequency.exponentialRampToValueAtTime(f1, bt + 0.06);
      gn.gain.setValueAtTime(0.0001, bt); gn.gain.linearRampToValueAtTime(vol * rnd(0.6, 1), bt + 0.008); gn.gain.exponentialRampToValueAtTime(0.0001, bt + 0.07);
    }
    mkPan(g, list, gn, dest, rnd(-0.8, 0.8));
    osc.start(t); m.start(t); osc.stop(end); m.stop(end);
    track(list, osc);
  }

  function eagle(g, dest, t, vol) {
    const f = rnd(1800, 2200);
    tone(g, dest, { type: "triangle", f, t, a: 0.05, d: 1.1, v: vol, lp: 5000, pan: rnd(-0.6, 0.6), fm: { f: 7, i: 45 }, glide: 0.4, f2: f * 1.38 });
    // la discesa finale segue sotto forma di seconda nota
    tone(g, dest, { type: "triangle", f: f * 1.35, f2: f * 0.7, glide: 0.7, t: t + 0.4, a: 0.04, d: 0.8, v: vol * 0.8, lp: 4500, fm: { f: 6, i: 40 } });
  }

  function rooster(g, dest, t, vol) {
    const ctx = g.ctx, osc = ctx.createOscillator(), f1 = ctx.createBiquadFilter(), f2 = ctx.createBiquadFilter(), gn = ctx.createGain(), list = [osc, f1, f2, gn];
    osc.type = "sawtooth"; f1.type = "bandpass"; f1.frequency.value = 1000; f1.Q.value = 2.5; f2.type = "lowpass"; f2.frequency.value = 2200;
    osc.connect(f1); f1.connect(f2); f2.connect(gn);
    const notes = [[0, 0.16, 520, 680], [0.2, 0.15, 600, 780], [0.4, 0.14, 700, 880], [0.6, 0.85, 760, 1000, 560]];
    gn.gain.setValueAtTime(0.0001, t); osc.frequency.setValueAtTime(520, t);
    notes.forEach((n) => {
      osc.frequency.setValueAtTime(n[2], t + n[0]);
      osc.frequency.linearRampToValueAtTime(n[3], t + n[0] + n[1] * 0.5);
      if (n[4]) osc.frequency.linearRampToValueAtTime(n[4], t + n[0] + n[1]);
      gn.gain.setValueAtTime(0.0001, t + n[0]); gn.gain.linearRampToValueAtTime(vol, t + n[0] + 0.03);
      gn.gain.linearRampToValueAtTime(vol * 0.7, t + n[0] + n[1] - 0.03); gn.gain.linearRampToValueAtTime(0.0001, t + n[0] + n[1]);
    });
    mkPan(g, list, gn, dest, rnd(-0.7, 0.7));
    osc.start(t); osc.stop(t + 1.6); track(list, osc);
  }

  function frog(g, dest, t, vol) {
    const ctx = g.ctx, osc = ctx.createOscillator(), lp = ctx.createBiquadFilter(), gn = ctx.createGain(), list = [osc, lp, gn];
    osc.type = "triangle"; lp.type = "lowpass"; lp.frequency.value = 700; osc.connect(lp); lp.connect(gn);
    const f = rnd(150, 230), n = 2 + Math.floor(Math.random() * 3);
    gn.gain.setValueAtTime(0.0001, t);
    for (let i = 0; i < n; i++) {
      const bt = t + i * 0.12;
      osc.frequency.setValueAtTime(f, bt); osc.frequency.exponentialRampToValueAtTime(f * 0.72, bt + 0.09);
      gn.gain.setValueAtTime(0.0001, bt); gn.gain.linearRampToValueAtTime(vol, bt + 0.015); gn.gain.exponentialRampToValueAtTime(0.0001, bt + 0.1);
    }
    mkPan(g, list, gn, dest, rnd(-0.8, 0.8));
    osc.start(t); osc.stop(t + n * 0.12 + 0.2); track(list, osc);
  }

  function clink(g, dest, t, vol) {
    const f = rnd(1700, 3100);
    tone(g, dest, { f, t, a: 0.002, d: 0.16, v: vol, lp: 4200, pan: rnd(-0.8, 0.8) });
    tone(g, dest, { f: f * 2.76, t, a: 0.002, d: 0.07, v: vol * 0.5, lp: 4200 });
  }

  function creak(g, dest, t, vol) {
    const f = rnd(260, 800), n = 2 + Math.floor(Math.random() * 3), shape = [[0, 0]];
    let x = 0;
    for (let i = 0; i < n; i++) { shape.push([x + 0.003, 1], [x + 0.035, 0]); x += rnd(0.05, 0.11); shape.push([x, 0]); }
    burst(g, dest, { kind: "white", ft: "bandpass", f, f2: f * rnd(0.7, 1.4), glide: x, q: 28, t, shape, v: vol * 5, pan: rnd(-0.7, 0.7) });
  }

  function whisper(g, dest, t, vol) {
    const ctx = g.ctx, src = ctx.createBufferSource(), b1 = ctx.createBiquadFilter(), b2 = ctx.createBiquadFilter(), gn = ctx.createGain(), list = [src, b1, b2, gn];
    src.buffer = noiseBuf(g, "white");
    b1.type = "bandpass"; b2.type = "bandpass"; b1.Q.value = 9; b2.Q.value = 9;
    src.connect(b1); src.connect(b2); b1.connect(gn); b2.connect(gn);
    const V = [[300, 2200], [500, 1500], [700, 1100], [400, 900], [330, 2000], [550, 1700]], n = 3 + Math.floor(Math.random() * 4);
    let x = 0;
    gn.gain.setValueAtTime(0.0001, t);
    for (let i = 0; i < n; i++) {
      const v = pick(V), len = rnd(0.12, 0.3);
      b1.frequency.setValueAtTime(v[0], t + x); b2.frequency.setValueAtTime(v[1], t + x);
      gn.gain.setValueAtTime(0.0001, t + x); gn.gain.linearRampToValueAtTime(vol * rnd(0.5, 1), t + x + len * 0.35); gn.gain.linearRampToValueAtTime(0.0001, t + x + len);
      x += len + rnd(0.02, 0.12);
    }
    mkPan(g, list, gn, dest, rnd(-0.9, 0.9));
    src.start(t, Math.random() * 2.5); src.stop(t + x + 0.05); track(list, src);
  }

  function drop(g, dest, t, vol) {
    burst(g, dest, { kind: "white", ft: "bandpass", f: rnd(1500, 5000), q: 3, t, a: 0.001, d: 0.025, v: vol, pan: rnd(-0.9, 0.9) });
    if (vol > 0.14 && Math.random() < 0.5) tone(g, dest, { f: rnd(700, 1400), f2: 400, glide: 0.06, t, a: 0.002, d: 0.06, v: vol * 0.4 });
  }

  function thump(g, dest, t, vol) {
    tone(g, dest, { f: 72, f2: 38, glide: 0.13, t, a: 0.006, d: 0.18, v: vol, lp: 220 });
    tone(g, dest, { f: 144, f2: 80, glide: 0.1, t, a: 0.004, d: 0.1, v: vol * 0.4, lp: 400 });
  }

  // ------------------------------------------------------------------ strati (un fondale, un meteo, il combattimento)
  function makeLayer(g, trim) {
    const ctx = g.ctx, L = { g, dead: false, trim: trim || 1, nodes: [], srcs: [], timers: [] };
    const add = (n) => { reg(n); L.nodes.push(n); return n; };
    L.add = add;
    L.gain = add(ctx.createGain()); L.gain.gain.value = g.offline ? L.trim : 0; L.gain.connect(g.bus);
    L.gf = (v, to) => { const n = add(ctx.createGain()); n.gain.value = v; if (to) n.connect(to); return n; };
    L.flt = (type, f, q, to) => { const n = add(ctx.createBiquadFilter()); n.type = type; n.frequency.value = f; n.Q.value = q == null ? 0.7 : q; if (to) n.connect(to); return n; };
    L.noise = (kind) => { const s = add(ctx.createBufferSource()); s.buffer = noiseBuf(g, kind); s.loop = true; s.start(0, rnd(0, 2.5)); L.srcs.push(s); return s; };
    L.osc = (type, f) => { const o = add(ctx.createOscillator()); o.type = type; o.frequency.value = f; o.start(); L.srcs.push(o); return o; };
    L.mod = (i, param, depth) => { const n = L.gf(depth, param); g.lfo[i].connect(n); return n; };
    L.every = (a, b, fn, first) => {
      if (g.offline) return;
      const h = { id: 0 };
      const step = () => {
        if (L.dead) return;
        try { if (ctx.state === "running") fn(ctx.currentTime + 0.03); } catch (e) { /* un evento sbagliato non ferma il resto */ }
        h.id = setTimeout(step, rnd(a, b) * 1000);
      };
      h.id = setTimeout(step, (first == null ? rnd(a, b) : first) * 1000);
      L.timers.push(h);
    };
    return L;
  }

  function dispose(L) {
    if (!L || L.dead) return;
    L.dead = true;
    L.timers.forEach((h) => clearTimeout(h.id));
    L.srcs.forEach((s) => { try { s.stop(); } catch (e) { /* già fermo */ } });
    L.nodes.forEach((n) => { try { n.disconnect(); } catch (e) { /* già staccato */ } live.delete(n); });
    fading = fading.filter((x) => x !== L);
  }

  function fadeIn(L, tau) {
    if (L.g.offline) return;
    const t = L.g.ctx.currentTime;
    L.gain.gain.cancelScheduledValues(t); L.gain.gain.setValueAtTime(0, t); L.gain.gain.setTargetAtTime(L.trim, t, tau);
  }

  function retire(L, tau) {
    if (!L || L.retired) return;
    L.retired = true;
    while (fading.length >= 2) { const o = fading.shift(); quick(o); }      // se arrivano troppi cambi di fila, i più vecchi spariscono subito
    fading.push(L);
    const t = L.g.ctx.currentTime;
    L.gain.gain.cancelScheduledValues(t); L.gain.gain.setTargetAtTime(0, t, tau);
    setTimeout(() => dispose(L), tau * 5000 + 200);
  }
  function quick(L) {
    const t = L.g.ctx.currentTime;
    try { L.gain.gain.cancelScheduledValues(t); L.gain.gain.setTargetAtTime(0, t, 0.03); } catch (e) { /* niente */ }
    setTimeout(() => dispose(L), 250);
  }

  // ------------------------------------------------------------------ elementi riusabili dei fondali
  // o: f q lvl df lf lg dg  (frequenza centrale, risonanza, livello, escursione freq., LFO di freq. e di ampiezza)
  function wind(L, o) {
    const s = o.src || L.noise("white"), bp = L.flt("bandpass", o.f, o.q == null ? 0.8 : o.q), g = L.gf(o.lvl, L.gain);
    s.connect(bp); bp.connect(g);
    L.mod(o.lf == null ? 0 : o.lf, bp.frequency, o.df);
    L.mod(o.lg == null ? 1 : o.lg, g.gain, o.lvl * (o.dg == null ? 0.6 : o.dg));
    return { src: s, bp, g };
  }

  function crickets(L, k) {
    const c1 = L.osc("sine", 4300), c2 = L.osc("sine", 4650), am = L.gf(0.5), lfo = L.osc("sine", 30), env = L.gf(0, L.gain);
    c1.connect(am); c2.connect(am);
    const lg = L.gf(0.5, am.gain); lfo.connect(lg); am.connect(env);
    const lvl = 0.16 * k;
    L.every(0.4, 1.5, (t) => {
      if (!calm()) return;
      const dur = rnd(0.25, 0.8);
      c1.frequency.setValueAtTime(rnd(4100, 4600), t); c2.frequency.setValueAtTime(rnd(4500, 4900), t); lfo.frequency.setValueAtTime(rnd(24, 38), t);
      env.gain.cancelScheduledValues(t); env.gain.setValueAtTime(0, t); env.gain.linearRampToValueAtTime(lvl, t + 0.03);
      env.gain.setValueAtTime(lvl, t + dur); env.gain.linearRampToValueAtTime(0, t + dur + 0.05);
    });
  }

  function birds(L, tc, k, base) {
    const R = { m: [0.7, 2.2], d: [2.5, 6], e: [6, 14] }[tc];
    if (!R) return;
    L.every(R[0] * (base || 1), R[1] * (base || 1), (t) => { if (calm()) birdPhrase(L.g, L.gain, t, 0.09 * k); });
  }

  function crowd(L, bands, k) {
    const s = L.noise("white"), gs = [];
    bands.forEach((b) => { const bp = L.flt("bandpass", b[0], b[1]), g = L.gf(b[2] * k, L.gain); s.connect(bp); bp.connect(g); gs.push([g, b[2] * k]); });
    L.every(0.5, 1.5, (t) => gs.forEach((x) => x[0].gain.setTargetAtTime(x[1] * rnd(0.3, 1.35), t, 0.35)));
  }

  function rain(L, k) {
    const s = L.noise("white"), hiss = L.flt("bandpass", 5200, 0.5), hg = L.gf(0.4 * k, L.gain), body = L.flt("bandpass", 800, 0.7), bg = L.gf(0.6 * k, L.gain);
    s.connect(hiss); hiss.connect(hg); s.connect(body); body.connect(bg);
    L.every(0.12 * (1 / k), 0.5 * (1 / k), (t) => drop(L.g, L.gain, t, rnd(0.05, 0.22) * k));
    return s;
  }

  // ------------------------------------------------------------------ i paesaggi sonori
  const BEDS = {
    mountain(L, tc) {
      const w = wind(L, { f: 1100, q: 0.9, lvl: 0.8, df: 420, lf: 0, lg: 1, dg: 0.6 });
      const lp = L.flt("lowpass", 260, 0.5), lg = L.gf(0.5, L.gain);
      w.src.connect(lp); lp.connect(lg);
      if (tc !== "n") L.every(14, 32, (t) => { if (calm()) eagle(L.g, L.gain, t, 0.07); }, rnd(5, 12));
    },
    forest(L, tc) {
      const s = L.noise("white");
      const leaves = L.flt("bandpass", 3600, 0.6), lg = L.gf(0.4, L.gain), creek = L.flt("bandpass", 1900, 2.2), cg = L.gf(0.26, L.gain);
      s.connect(leaves); leaves.connect(lg); s.connect(creek); creek.connect(cg);
      L.mod(2, lg.gain, 0.2); L.mod(2, creek.frequency, 500); L.mod(1, cg.gain, 0.1);
      if (tc === "n") crickets(L, 0.8); else birds(L, tc, 1);
    },
    city(L, tc) {
      crowd(L, [[230, 1.4, 0.7], [520, 1.6, 0.6], [950, 1.8, 0.4]], tc === "n" ? 0.45 : 1);
      L.every(5, 12, (t) => clink(L.g, L.gain, t, tc === "n" ? 0.03 : 0.05));
    },
    village(L, tc) {
      crowd(L, [[210, 1.5, 0.45], [460, 1.7, 0.3]], tc === "n" ? 0.3 : 0.7);
      if (tc === "n") crickets(L, 0.7);
      else {
        birds(L, tc, 0.5);
        if (tc !== "e") L.every(tc === "m" ? 20 : 60, tc === "m" ? 45 : 95, (t) => { if (calm()) rooster(L.g, L.gain, t, 0.03); }, tc === "m" ? rnd(3, 9) : rnd(20, 50));
      }
      L.every(8, 18, (t) => clink(L.g, L.gain, t, 0.015));
    },
    sect(L, tc) {
      const o1 = L.osc("sine", 110), o2 = L.osc("sine", 165 * 1.003), o3 = L.osc("sine", 220.9), dg = L.gf(0.2, L.gain);
      o1.connect(dg); o2.connect(dg); o3.connect(dg);
      L.mod(1, dg.gain, 0.06);
      const air = L.noise("brown"), alp = L.flt("lowpass", 500, 0.5), ag = L.gf(0.12, L.gain);
      air.connect(alp); alp.connect(ag);
      L.every(20, 40, (t) => bell(L.g, L.gain, t, 196 * rnd(0.99, 1.01), 0.2, 7), rnd(4, 9));
      if (tc === "m" || tc === "d") birds(L, tc, 0.4, 2.5);
    },
    ruin(L, tc) {
      wind(L, { f: 340, q: 6, lvl: 1.6, df: 90, lf: 1, lg: 0, dg: 0.7 });
      const o1 = L.osc("sine", 55), o2 = L.osc("triangle", 58.1), dg = L.gf(0.2, L.gain);
      o1.connect(dg); o2.connect(dg); L.mod(0, dg.gain, 0.08);
      L.every(7, 17, (t) => creak(L.g, L.gain, t, 0.05));
    },
    cave(L, tc) {
      const bus = L.gf(1), dry = L.gf(0.8, L.gain), wet = L.gf(0.9, L.gain), conv = L.add(L.g.ctx.createConvolver());
      conv.buffer = irBuf(L.g); bus.connect(dry); bus.connect(conv); conv.connect(wet);
      const rb = L.noise("brown"), rl = L.flt("lowpass", 140, 0.5), rg = L.gf(0.35, L.gain);
      rb.connect(rl); rl.connect(rg);
      L.every(1, 4, (t) => {
        const f = rnd(1100, 2600), v = rnd(0.1, 0.24);
        tone(L.g, bus, { f, f2: f * 0.55, glide: 0.08, t, a: 0.002, d: 0.2, v, pan: rnd(-0.8, 0.8) });
        if (Math.random() < 0.25) tone(L.g, bus, { f: f * 1.2, f2: f * 0.7, glide: 0.08, t: t + 0.13, a: 0.002, d: 0.16, v: v * 0.5 });
      }, 0.8);
    },
    lake(L, tc) {
      const s = L.noise("white"), lp = L.flt("lowpass", 700, 0.5), wg = L.gf(0.8, L.gain), lap = L.flt("bandpass", 1700, 2.5), lg = L.gf(0.2, L.gain);
      s.connect(lp); lp.connect(wg); s.connect(lap); lap.connect(lg);
      L.mod(0, lp.frequency, 350); L.mod(1, wg.gain, 0.6); L.mod(2, lg.gain, 0.12);
      if (tc === "n") crickets(L, 0.6);
      const R = { n: [2, 6], e: [4, 10], m: [14, 30], d: [14, 30] }[tc];
      L.every(R[0], R[1], (t) => { if (calm()) frog(L.g, L.gain, t, tc === "n" ? 0.07 : 0.04); });
      if (tc === "m") birds(L, tc, 0.6, 1.5);
    },
    wilderness(L, tc) {
      wind(L, { f: 620, q: 0.7, lvl: 0.7, df: 240, lf: 0, lg: 1, dg: 0.55 });
      if (tc === "n") crickets(L, 0.9);
      else birds(L, tc === "e" ? "e" : "d", 0.6, 3);
    },
    forbidden_zone(L, tc) {
      const o1 = L.osc("sine", 41), o2 = L.osc("sine", 41.37), o3 = L.osc("triangle", 82.6), lp = L.flt("lowpass", 220, 0.5, null), dg = L.gf(0.3, L.gain);
      o1.connect(dg); o2.connect(dg); o3.connect(lp); lp.connect(dg);
      L.mod(0, dg.gain, 0.1);
      const dn = L.noise("brown"), dl = L.flt("lowpass", 110, 0.5), dgg = L.gf(0.4, L.gain);
      dn.connect(dl); dl.connect(dgg);
      L.every(5, 13, (t) => whisper(L.g, L.gain, t, 0.5));
    },
  };

  // livelli di compensazione: ogni fondale arriva a un volume percepito simile
  const TRIM = { mountain: 0.45, forest: 0.5, city: 0.65, village: 1.6, sect: 0.35, ruin: 0.35, cave: 1.2, lake: 0.45, wilderness: 0.5, forbidden_zone: 0.28 };
  function makeBed(g, place, tc) {
    const L = makeLayer(g, TRIM[place] || 0.5);
    (BEDS[place] || BEDS.wilderness)(L, tc);
    return L;
  }

  function makeWeather(g, wx) {
    const L = makeLayer(g, 0.5);
    if (wx === "pioggia") rain(L, 1);
    else if (wx === "tempesta") {
      const rs = rain(L, 1.35);
      wind(L, { src: rs, f: 700, q: 0.7, lvl: 0.6, df: 300, lf: 0, lg: 1, dg: 0.7 });
      L.every(15, 40, (t) => thunder(g, L.gain, t, rnd(0.3, 0.7), Math.random() < 0.4), rnd(5, 12));
    } else if (wx === "neve") wind(L, { f: 380, q: 0.5, lvl: 0.35, df: 120, lf: 0, lg: 1, dg: 0.5 });
    else if (wx === "nebbia") { const s = L.noise("brown"), lp = L.flt("lowpass", 180, 0.5), gg = L.gf(0.25, L.gain); s.connect(lp); lp.connect(gg); }
    else if (wx === "vento") wind(L, { f: 850, q: 0.6, lvl: 0.7, df: 380, lf: 0, lg: 1, dg: 0.8 });
    return L;
  }

  function makeCombat(g) {
    const L = makeLayer(g);
    L.every(0.86, 1.0, (t) => { thump(g, L.gain, t, 0.5); thump(g, L.gain, t + 0.19, 0.32); }, 0.25);
    if (g.offline) { thump(g, L.gain, 0.1, 0.5); thump(g, L.gain, 0.29, 0.32); }
    return L;
  }

  // ------------------------------------------------------------------ effetti isolati
  const CUES = {
    colpo(g, d, t) {
      tone(g, d, { f: 150 * rnd(0.9, 1.1), f2: 48, glide: 0.16, t, a: 0.003, d: 0.24, v: 0.8 });
      burst(g, d, { kind: "brown", ft: "lowpass", f: 900, q: 0.7, t, a: 0.002, d: 0.06, v: 0.5 });
    },
    critico(g, d, t) {
      burst(g, d, { kind: "white", ft: "highpass", f: 2500, q: 0.7, t, a: 0.001, d: 0.1, v: 0.55 });
      tone(g, d, { f: 230, f2: 60, glide: 0.14, t, a: 0.002, d: 0.18, v: 0.55 });
      [3136, 4186, 5274].forEach((f, i) => tone(g, d, { f: f * rnd(0.995, 1.005), t: t + 0.02 + i * 0.045, a: 0.005, d: 0.7 + i * 0.3, v: 0.08 }));
    },
    fulmine(g, d, t) { thunder(g, d, t, 0.8, false); },
    sfondamento(g, d, t) {
      burst(g, d, { kind: "white", ft: "bandpass", f: 250, f2: 4000, glide: 1.5, q: 2, t, shape: [[0, 0], [1.45, 1], [1.6, 0]], v: 0.3 });
      tone(g, d, { type: "sawtooth", f: 98, f2: 392, glide: 1.5, t, a: 1.45, d: 0.15, v: 0.13, lp: 1400 });
      tone(g, d, { f: 196, f2: 784, glide: 1.5, t, a: 1.45, d: 0.15, v: 0.2 });
      bell(g, d, t + 1.55, 392, 0.4, 5);
      [784, 1176, 1568].forEach((f, i) => tone(g, d, { f, t: t + 1.58 + i * 0.05, a: 0.01, d: 1.6 + i * 0.3, v: 0.06 }));
    },
    campana(g, d, t) { bell(g, d, t, 220 * rnd(0.99, 1.01), 0.5, 6.5); },
    gong(g, d, t) {
      [[1, 1, 1], [1.47, 0.6, 0.8], [2.09, 0.55, 0.65], [2.92, 0.35, 0.5], [4.16, 0.2, 0.35]].forEach((p) =>
        tone(g, d, { f: 98 * p[0], t, a: 0.12 + 0.05 * p[0], d: 6.5 * p[2], v: 0.34 * p[1] }));
      tone(g, d, { f: 98 * 1.004, t, a: 0.2, d: 5.5, v: 0.22 });
      tone(g, d, { f: 98 * 2.09 * 0.996, t, a: 0.25, d: 4, v: 0.14 });
      burst(g, d, { kind: "white", ft: "bandpass", f: 700, q: 0.8, t, a: 0.01, d: 0.25, v: 0.12 });
    },
    passo(g, d, t) {
      burst(g, d, { kind: "brown", ft: "lowpass", f: rnd(380, 560), q: 0.7, t, a: 0.004, d: 0.08, v: 0.4, pan: rnd(-0.3, 0.3) });
      tone(g, d, { f: rnd(100, 125), f2: 62, glide: 0.07, t, a: 0.004, d: 0.08, v: 0.28 });
    },
    moneta(g, d, t) {
      const r = rnd(0.94, 1.08), once = (tt, v, k) => {
        tone(g, d, { f: 2637 * r * k, t: tt, a: 0.001, d: 0.3, v });
        tone(g, d, { f: 3951 * r * k, t: tt, a: 0.001, d: 0.16, v: v * 0.7 });
        tone(g, d, { f: 5330 * r * k, t: tt, a: 0.001, d: 0.07, v: v * 0.35 });
      };
      once(t, 0.2, 1); once(t + rnd(0.05, 0.09), 0.14, 1.19);
    },
    fallimento(g, d, t) {
      tone(g, d, { f: 95, f2: 46, glide: 0.35, t, a: 0.005, d: 0.7, v: 0.7 });
      tone(g, d, { f: 67, f2: 45, glide: 0.5, t, a: 0.01, d: 0.8, v: 0.45 });
      tone(g, d, { type: "sawtooth", f: 70, t, a: 0.01, d: 0.7, v: 0.12, lp: 300 });
      tone(g, d, { type: "sawtooth", f: 74.5, t, a: 0.01, d: 0.7, v: 0.12, lp: 300 });
      burst(g, d, { kind: "brown", ft: "lowpass", f: 500, q: 0.7, t, a: 0.003, d: 0.1, v: 0.35 });
    },
    fusione(g, d, t) {
      tone(g, d, { f: 196, f2: 330, glide: 1.2, t, a: 0.25, d: 1.3, v: 0.2 });
      tone(g, d, { f: 523, f2: 330, glide: 1.2, t, a: 0.25, d: 1.3, v: 0.16 });
      const c = t + 1.2;
      [[220, 0.14], [330, 0.16], [440, 0.12], [660, 0.08], [990, 0.04]].forEach((p, i) => tone(g, d, { f: p[0], t: c, a: 0.12, d: 2.6 - i * 0.2, v: p[1] }));
      [1320, 1980].forEach((f, i) => tone(g, d, { f, t: c + 0.08 + i * 0.07, a: 0.01, d: 1.5, v: 0.04 }));
    },
  };

  // ------------------------------------------------------------------ logica di scena
  function normPlace(p) { p = String(p == null ? "" : p).toLowerCase().trim(); if (ALIAS[p]) p = ALIAS[p]; return PLACES.indexOf(p) >= 0 ? p : "wilderness"; }
  function norm(s) {
    s = s || {};
    const prev = want || { place: "wilderness", weather: "", time: "giorno", combat: false };
    const w = s.weather === undefined ? prev.weather : String(s.weather == null ? "" : s.weather).toLowerCase().trim();
    const tm = s.time === undefined ? prev.time : String(s.time == null ? "" : s.time).toLowerCase().trim();
    return {
      place: s.place === undefined ? prev.place : normPlace(s.place),
      weather: WEATHERS.indexOf(w) >= 0 ? w : "",
      time: TIMES.indexOf(tm) >= 0 ? tm : "giorno",
      combat: s.combat === undefined ? prev.combat : !!s.combat,
    };
  }

  function toneTarget() {
    const t = { m: 13000, d: 16000, e: 9500, n: 6500 }[TC[want.time]] || 16000;
    const w = { nebbia: 1100, neve: 2400, pioggia: 9500, tempesta: 8000 }[want.weather];
    return w ? Math.min(t, w) : t;
  }

  function busLevel() {
    if (!G) return;
    const t = G.ctx.currentTime, v = ON ? (want && want.combat ? 0.8 : 1) : 0;
    G.bus.gain.cancelScheduledValues(t); G.bus.gain.setTargetAtTime(v, t, ON ? 0.4 : 0.35);
  }

  function apply() {
    applyTimer = 0;
    if (!ON) return;
    const g = boot();
    if (!g) return;
    if (!want) want = { place: "wilderness", weather: "", time: "giorno", combat: false };
    resume();
    const tc = TC[want.time], key = want.place + "|" + tc;
    g.tone.frequency.setTargetAtTime(toneTarget(), g.ctx.currentTime, 1.0);
    if (key !== appBed || !bedL) { retire(bedL, 0.6); bedL = makeBed(g, want.place, tc); fadeIn(bedL, 0.6); appBed = key; }
    if (want.weather !== appWx || (want.weather && !wxL)) {
      retire(wxL, 0.6); wxL = null;
      if (want.weather) { wxL = makeWeather(g, want.weather); fadeIn(wxL, 0.6); }
      appWx = want.weather;
    }
    if (want.combat !== appCb) {
      retire(cbL, 0.25); cbL = null;
      if (want.combat) { cbL = makeCombat(g); fadeIn(cbL, 0.3); }
      appCb = want.combat;
    }
    busLevel();
  }

  function scheduleApply() { if (applyTimer) clearTimeout(applyTimer); applyTimer = setTimeout(apply, 90); }

  function setScene(s) {
    const n = norm(s);
    if (want && want.place === n.place && want.weather === n.weather && want.time === n.time && want.combat === n.combat) return false;
    want = n;
    if (ON) scheduleApply();
    return true;
  }

  function fadeOutAll() {
    if (applyTimer) { clearTimeout(applyTimer); applyTimer = 0; }
    retire(bedL, 0.5); retire(wxL, 0.5); retire(cbL, 0.25);
    bedL = wxL = cbL = null; appBed = appWx = appCb = null;
  }

  function armIdle() {
    if (idleTimer) clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      idleTimer = 0;
      if (G && !ON && performance.now() - lastCue > 5000 && G.ctx.state === "running") { try { G.ctx.suspend(); } catch (e) { /* niente */ } }
      else if (G && !ON) armIdle();
    }, 5500);
  }

  function setOn(v) {
    ON = !!v;
    store.set(K.on, ON ? "1" : "0");
    if (ON) {
      const g = boot();
      if (g) { resume(); busLevel(); apply(); }
    } else {
      fadeOutAll();
      if (G) { busLevel(); armIdle(); }
    }
    return ON;
  }

  function stop() {
    fadeOutAll();
    want = null;
    if (G) armIdle();
  }

  function setVolume(v) {
    v = parseFloat(v);
    if (!isFinite(v)) return VOL;
    VOL = clamp(v, 0, 1);
    store.set(K.vol, String(VOL));
    if (G) { const t = G.ctx.currentTime; G.out.gain.cancelScheduledValues(t); G.out.gain.setTargetAtTime(VOL, t, 0.08); }
    return VOL;
  }

  function setCues(v) {
    CUES_PREF = v ? "1" : "0";
    store.set(K.cues, CUES_PREF);
    return cuesOn();
  }

  function cue(name) {
    const fn = CUES[name];
    if (!fn || !cuesOn() || !AC) return false;
    const now = performance.now();
    if (lastByName[name] && now - lastByName[name] < 40) return false;       // niente raffiche identiche
    if (live.size > 160) return false;                                       // salvaguardia di carico
    lastByName[name] = now; lastCue = now;
    const g = boot();
    if (!g) return false;
    const ctx = g.ctx, play = () => { if (ctx.state === "running") fn(g, g.cue, ctx.currentTime + 0.01); };
    if (ctx.state === "running") play();
    else {
      try { const p = ctx.resume(); if (p && p.then) p.then(() => { if (performance.now() - now < 600) play(); }).catch(() => {}); } catch (e) { /* niente */ }
    }
    if (!ON) armIdle();
    return true;
  }

  // dopo un ricaricamento con l'ambiente acceso serve comunque un gesto: al primo clic/tasto riparte da solo
  if (ON && AC) {
    const evs = ["pointerdown", "keydown", "touchend", "click"];
    const kick = () => { evs.forEach((e) => removeEventListener(e, kick, true)); if (ON) setOn(true); };
    evs.forEach((e) => addEventListener(e, kick, true));
  }

  // ------------------------------------------------------------------ prove (per sviluppo)
  function offlineRender(sc, secs, cueName) {
    const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    if (!OAC) return Promise.reject(new Error("OfflineAudioContext non disponibile"));
    const sr = 44100, ctx = new OAC(2, Math.floor(sr * secs), sr), before = new Set(live), saveWant = want;
    want = null; want = norm(sc || {});
    const g = build(ctx, true);
    if (cueName) { if (CUES[cueName]) CUES[cueName](g, g.cue, 0.05); }
    else {
      makeBed(g, want.place, TC[want.time]);
      if (want.weather) makeWeather(g, want.weather);
      if (want.combat) makeCombat(g);
      g.tone.frequency.value = toneTarget();
    }
    const restore = () => { want = saveWant; Array.from(live).forEach((n) => { if (!before.has(n)) live.delete(n); }); };
    return ctx.startRendering().then((buf) => {
      restore();
      let peak = 0, sum = 0, n = 0;
      for (let c = 0; c < buf.numberOfChannels; c++) { const d = buf.getChannelData(c); for (let i = 0; i < d.length; i++) { const a = Math.abs(d[i]); if (a > peak) peak = a; sum += d[i] * d[i]; n++; } }
      return { peak, rms: Math.sqrt(sum / n), seconds: secs };
    }, (e) => { restore(); throw e; });
  }

  function peakTap(ms) {
    return new Promise((res) => {
      if (!G) return res(null);
      const an = G.ctx.createAnalyser(); an.fftSize = 2048; G.out.connect(an);
      const buf = new Float32Array(an.fftSize); let peak = 0, sum = 0, n = 0;
      const iv = setInterval(() => { an.getFloatTimeDomainData(buf); for (let i = 0; i < buf.length; i++) { const a = Math.abs(buf[i]); if (a > peak) peak = a; sum += buf[i] * buf[i]; n++; } }, 25);
      setTimeout(() => { clearInterval(iv); try { G.out.disconnect(an); } catch (e) { /* niente */ } res({ peak, rms: n ? Math.sqrt(sum / n) : 0 }); }, ms);
    });
  }

  window.Ambient = {
    PLACES, WEATHERS, TIMES, CUES: Object.keys(CUES),
    supported: () => !!AC,
    on: () => ON, setOn,
    volume: () => VOL, setVolume,
    cuesOn, setCues,
    setScene, scene: () => (want ? Object.assign({}, want) : null),
    cue, stop,
    label(s) {
      s = s || want; if (!s) return "";
      const p = LABEL[normPlace(s.place)], parts = [p];
      if (s.weather && WEATHERS.indexOf(s.weather) > 0) parts.push(s.weather);
      if (s.time && TIMES.indexOf(s.time) >= 0) parts.push(s.time);
      if (s.combat) parts.push("combattimento");
      return parts.join(" · ");
    },
    _debug: () => ({ nodes: live.size, ctxState: G ? G.ctx.state : "none", scene: want ? Object.assign({}, want) : null, on: ON, fading: fading.length,
      layers: { bed: !!bedL, weather: !!wxL, combat: !!cbL } }),
    _offline: offlineRender, _peak: peakTap,
  };
})();
