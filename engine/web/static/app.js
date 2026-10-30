// Jade Immortal — dashboard. Nessuna libreria: fetch + DOM.
"use strict";

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
let S = null;            // ultima istantanea di stato
let showAllNpcs = false;
let tab = "mete";
let busy = false;
const history = [];
let hpos = 0;

async function api(path, body) {
  const opt = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  const r = await fetch(path, opt);
  const j = await r.json();
  if (j && j.errore) throw new Error(j.errore);
  return j;
}

// ---------------- registro ----------------
function lineClass(l) {
  if (/[☠✝]|morte|uccide te|DEVIAZIONE/.test(l)) return "l-bad";
  if (/[⚠⏸]/.test(l)) return "l-warn";
  if (/[✦★]|Nuovo titolo|SVOLTA/.test(l)) return "l-rare";
  if (/[✧✔]|Avanzi|sfonda fino|Riesci|Ce la fai/.test(l)) return "l-good";
  if (/[⚡☯🧭]/.test(l)) return "l-info";
  return "";
}
let logFilter = "tutto";
// i comandi suggeriti nel testo ('join', «attributi FOR 3», 'vola <luogo>') diventano azioni cliccabili:
// senza segnaposto si eseguono, con un <segnaposto> si scrivono nella riga di comando da completare
const NO_CLICK = /^(ricomincia|reincarnati|quit|esci|carica|nuovo_mondo|cancella)/;
function actionize(html) {
  const re = /(^|[\s(:→—,])(['«])([a-z_][a-z0-9_àèéìòù ]{0,38}(?: &lt;[^&]{1,20}&gt;)*(?: \[[^\]]{1,20}\])?)(['»])(?=[\s).,;:!?]|$)/gi;
  return html.replace(re, (m, pre, a, cmd, b) => {
    if ((a === "'") !== (b === "'")) return m;
    const raw = cmd.replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
    if (raw.split(" ").length > 6 || NO_CLICK.test(raw)) return m;
    const fill = /[<\[]/.test(raw);
    const clean = fill ? raw.replace(/\s*[<\[].*$/, " ") : raw;
    return `${pre}<button class="act" ${fill ? `data-fill="${esc(clean)}"` : `data-cmd="${esc(clean)}"`} title="${fill ? "scrivi e completa" : "esegui"}: ${esc(raw)}">▶ ${cmd}</button>`;
  });
}
// ---------------- (Agg. 69) LETTURA AL TUO RITMO ----------------
// In modalità manuale il testo nuovo arriva a pezzi: il primo subito, gli altri quando premi «Avanti» (Spazio,
// oppure Invio con la casella vuota). Anche le notifiche restano finché non le chiudi, e i cut-in del duello
// aspettano il tuo clic. In modalità automatica tutto scorre come prima.
let READ = "manuale", READ_STEP = 3;
try { READ = localStorage.getItem("ji_read") || "manuale"; READ_STEP = Number(localStorage.getItem("ji_read_step")) || 3; } catch (e) { /* niente */ }
const PENDING = [];                                   // pezzi di testo in attesa: liste di righe del registro
let CUT_NEXT = null;                                  // il cut-in aspetta il clic
const TOAST_Q = [];
const manual = () => READ === "manuale";
function chunkLines(els) {
  const out = []; let cur = [];
  for (const el of els) {
    const blank = !el.textContent.trim();
    if (blank) { if (cur.length) { out.push(cur); cur = []; } out.length ? out[out.length - 1].push(el) : cur.push(el); continue; }
    const head = /^\s*(✦|⚔|═|—|\[|☯|✧|🗼)/.test(el.textContent);
    if (cur.length && (cur.length >= READ_STEP || (head && cur.length >= 1 && READ_STEP > 1))) { out.push(cur); cur = []; }
    cur.push(el);
  }
  if (cur.length) out.push(cur);
  return out;
}
function advUi() {
  const bar = $("#advbar"); if (!bar) return;
  const n = PENDING.reduce((a, c) => a + c.filter((x) => x.textContent.trim()).length, 0);
  const more = n || CUT_NEXT || (manual() && $("#toasts") && $("#toasts").children.length);
  bar.hidden = !more;
  document.body.classList.toggle("reading", !!n);
  const sm = bar.querySelector("small");
  if (sm) sm.textContent = n ? `${n} rig${n === 1 ? "a" : "he"} in attesa` : CUT_NEXT ? "continua lo scambio" : "chiudi la notifica";
}
function advance() {
  if (CUT_NEXT) { const f = CUT_NEXT; CUT_NEXT = null; f(); advUi(); return true; }
  if (PENDING.length) {
    const chunk = PENDING.shift();
    chunk.forEach((el) => { el.classList.remove("wait"); el.classList.add("fresh"); });
    const first = chunk[0]; if (first) first.scrollIntoView({ block: "nearest" });
    const box = $("#log"); if (!PENDING.length && box) box.scrollTop = box.scrollHeight;
    advUi(); return true;
  }
  const t = $("#toasts") && $("#toasts").firstElementChild;
  if (t && manual()) { closeToast(t); advUi(); return true; }
  advUi(); return false;
}
function flushAll() {
  while (PENDING.length) PENDING.shift().forEach((el) => el.classList.remove("wait"));
  const box = $("#log"); if (box) box.scrollTop = box.scrollHeight;
  advUi();
}
function addLog(text, cmd, instant) {
  if (!text && !cmd) return;
  const box = $("#log");
  const div = document.createElement("div");
  div.className = "entry";
  let html = cmd ? `<div class="you">› ${esc(cmd)}</div>` : "";
  // le scelte delle scene hanno i loro pulsanti: nel registro non si ripetono
  const lines = (text || "").split("\n").filter((l) => !/^\s*\[\d+\] /.test(l) && !/scrivi il numero della tua scelta/.test(l));
  html += lines.map((l) => {
    const c = lineClass(l), cat = V.category(l);
    const hide = logFilter !== "tutto" && cat !== logFilter ? " hidden" : "";
    return `<div class="ln cat-${cat}${c ? " " + c : ""}"${hide}>${actionize(esc(l)) || "&nbsp;"}</div>`;
  }).join("");
  div.innerHTML = html;
  box.appendChild(div);
  while (box.children.length > 300) box.removeChild(box.firstChild);
  if (manual() && !instant && !document.body.classList.contains("duel-on")) {   // nel duello si legge l'arena; l'ingresso si legge subito
    const chunks = chunkLines([...div.querySelectorAll(".ln")]);
    const keepFirst = !PENDING.length;                // il primo pezzo si vede subito, se non c'è altro da leggere
    chunks.forEach((c, i) => { if (i === 0 && keepFirst) return; c.forEach((el) => el.classList.add("wait")); PENDING.push(c); });
    const y = div.offsetTop - box.offsetTop - 8;
    box.scrollTop = keepFirst ? Math.max(y, box.scrollHeight - box.clientHeight - 2000) : box.scrollTop;
    if (keepFirst) div.scrollIntoView({ block: "nearest" });
    advUi();
  } else box.scrollTop = box.scrollHeight;
  systemToasts(text || "");
}

// ---------------- notifiche di sistema (stile «The Gamer») ----------------
const TOAST_RULES = [
  [/Nuovo titolo|Titolo:/, "Titolo ottenuto", "rare"],
  [/sfonda|SFONDI|Avanzi (al|allo)|nuovo regno|Grande Perfezione/i, "Livello superiore", "good"],
  [/✺ .*(nasce|cresce)/, "Spirito del Dao", "rare"],
  [/\[Sistema\]/, "Sistema", "info"],
  [/GUERRA CON IL CIELO|Giudizio del Cielo|SIGILLO DELLA SFIDA/, "Il Cielo", "bad"],
  [/tribolazione/i, "Tribolazione", "warn"],
  [/si è messo sulle tue tracce|ti dà la caccia|scende dalle nubi/, "Pericolo", "bad"],
  [/SVOLTA|risveglia|Risveglio/, "Risveglio", "rare"],
];
function systemToasts(text) {
  let n = 0;
  for (const l of text.split("\n")) {
    for (const [re, head, tone] of TOAST_RULES) {
      if (re.test(l) && n < 3) { toast(head, l.replace(/^\s+/, ""), tone); n++; break; }
    }
  }
}
// ---------------- suoni discreti (sintetizzati, nessun file) ----------------
let SOUND = true;
try { SOUND = localStorage.getItem("ji_sound") !== "0"; } catch (e) { /* niente */ }
let AC = null;
// (Agg. 69) un suono per elemento, fatto col codice: rumore filtrato per fuoco/vento/acqua, toni per metallo e luce
const EL_SFX = {
  fuoco: { noise: 0.5, f: 900, q: 0.7, tone: [110], dur: 0.6 }, vento: { noise: 0.7, f: 1400, q: 0.4, dur: 0.7, sweep: 400 },
  acqua: { noise: 0.4, f: 500, q: 3, tone: [392, 330], dur: 0.6 }, fulmine: { noise: 0.9, f: 3000, q: 0.5, tone: [55], dur: 0.35, crack: 1 },
  terra: { noise: 0.5, f: 180, q: 1, tone: [65, 55], dur: 0.7 }, metallo: { tone: [1568, 2093, 1175], dur: 0.8, type: "square" },
  legno: { tone: [330, 392, 494], dur: 0.5, type: "triangle" }, luce: { tone: [880, 1109, 1319, 1760], dur: 0.9 },
  oscurita: { tone: [98, 92], dur: 0.9, type: "sawtooth", lp: 600 }, abisso: { noise: 0.4, f: 120, q: 2, tone: [49], dur: 1, type: "sawtooth", lp: 300 },
  anima: { tone: [523, 554, 523, 587], dur: 0.9, type: "sine" }, sangue: { tone: [147, 139], dur: 0.6, type: "sawtooth", lp: 900 },
  pugno: { noise: 0.6, f: 250, q: 1, tone: [82], dur: 0.25 }, corpo: { noise: 0.5, f: 200, q: 1, tone: [73], dur: 0.3 },
  spada: { noise: 0.6, f: 4000, q: 2, dur: 0.3, sweep: 2500, tone: [2637], type: "sine" },
};
function elSfx(e) {
  const cfg = EL_SFX[e]; if (!cfg) return false;
  const t0 = AC.currentTime, dur = cfg.dur || 0.5;
  if (cfg.noise) {
    const len = Math.floor(AC.sampleRate * dur), buf = AC.createBuffer(1, len, AC.sampleRate), ch = buf.getChannelData(0);
    for (let i = 0; i < len; i++) ch[i] = (Math.random() * 2 - 1) * (cfg.crack && Math.random() < 0.02 ? 3 : 1);
    const src = AC.createBufferSource(), flt = AC.createBiquadFilter(), g = AC.createGain();
    src.buffer = buf; flt.type = "bandpass"; flt.frequency.setValueAtTime(cfg.f, t0); flt.Q.value = cfg.q || 1;
    if (cfg.sweep) flt.frequency.exponentialRampToValueAtTime(cfg.sweep, t0 + dur);
    g.gain.setValueAtTime(0.0001, t0); g.gain.exponentialRampToValueAtTime(0.08 * cfg.noise, t0 + 0.03);
    g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(flt).connect(g).connect(AC.destination); src.start(t0); src.stop(t0 + dur);
  }
  (cfg.tone || []).forEach((f, i) => {
    const o = AC.createOscillator(), g = AC.createGain(); let out = g;
    o.type = cfg.type || "triangle"; o.frequency.value = f;
    const st = t0 + i * 0.07;
    g.gain.setValueAtTime(0.0001, st); g.gain.exponentialRampToValueAtTime(0.05, st + 0.02);
    g.gain.exponentialRampToValueAtTime(0.0001, st + dur);
    if (cfg.lp) { const lp = AC.createBiquadFilter(); lp.type = "lowpass"; lp.frequency.value = cfg.lp; g.connect(lp); out = lp; }
    o.connect(g); out.connect(AC.destination); o.start(st); o.stop(st + dur + 0.05);
  });
  return true;
}
function sfx(kind) {
  if (!SOUND) return;
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    if (kind.startsWith("el_")) { if (elSfx(kind.slice(3))) return; kind = "hit"; }
    const notes = { good: [523, 659, 784], rare: [659, 784, 988, 1319], bad: [220, 185], warn: [440, 392], info: [587, 740],
      hit: [196], crit: [147, 294], coin: [988, 1319], swing: [330, 247] }[kind] || [440];
    const t0 = AC.currentTime;
    notes.forEach((f, i) => {
      const o = AC.createOscillator(), g = AC.createGain();
      o.type = kind === "hit" || kind === "crit" ? "triangle" : "sine";
      o.frequency.value = f;
      g.gain.setValueAtTime(0.0001, t0 + i * 0.09);
      g.gain.exponentialRampToValueAtTime(kind === "crit" ? 0.12 : 0.06, t0 + i * 0.09 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + i * 0.09 + (kind === "hit" ? 0.18 : 0.45));
      o.connect(g).connect(AC.destination);
      o.start(t0 + i * 0.09); o.stop(t0 + i * 0.09 + 0.5);
    });
  } catch (e) { /* audio non disponibile */ }
}
// ---------------- (Agg. 69) MUSICA D'ATMOSFERA, generata dal codice ----------------
// Una cetra (guqin) pizzicata su una scala pentatonica, un bordone e, in montagna, il vento. Cambia con il luogo:
// la città è luminosa e fitta, le rovine minori e lente, la zona proibita dissonante, il duello incalzante.
const MOODS = {
  city: { base: 262, scale: [0, 2, 4, 7, 9, 12, 14], beat: 0.9, dens: 0.6, drone: 0, bell: 1 },
  mountain: { base: 196, scale: [0, 2, 4, 7, 9, 12], beat: 1.8, dens: 0.4, drone: 1, wind: 1 },
  ruin: { base: 174, scale: [0, 3, 5, 7, 10, 12], beat: 2.2, dens: 0.35, drone: 1 },
  forbidden_zone: { base: 110, scale: [0, 1, 6, 7, 10, 13], beat: 2.6, dens: 0.3, drone: 2 },
  sect: { base: 220, scale: [0, 2, 5, 7, 9, 12], beat: 1.4, dens: 0.45, drone: 1, bell: 1 },
  duel: { base: 147, scale: [0, 3, 5, 7, 10, 12, 15], beat: 0.45, dens: 0.75, drone: 2, drum: 1 },
  quiet: { base: 196, scale: [0, 2, 4, 7, 9], beat: 2.4, dens: 0.3, drone: 1 },
};
let MUSIC = true;
try { MUSIC = localStorage.getItem("ji_music") !== "0"; } catch (e) { /* niente */ }
const MU = { mood: null, timer: null, next: 0, master: null, drone: [], wind: null, step: 0 };
function muCtx() { AC = AC || new (window.AudioContext || window.webkitAudioContext)(); return AC; }
function muStop() {
  if (MU.timer) clearInterval(MU.timer); MU.timer = null;
  if (MU.master) { const g = MU.master, t = AC.currentTime; g.gain.setTargetAtTime(0.0001, t, 0.6); setTimeout(() => g.disconnect(), 3000); }
  MU.master = null; MU.drone = []; MU.wind = null; MU.mood = null;
}
function muPluck(f, t, vol, dest) {
  const o = AC.createOscillator(), o2 = AC.createOscillator(), g = AC.createGain(), lp = AC.createBiquadFilter();
  o.type = "triangle"; o.frequency.value = f; o2.type = "sine"; o2.frequency.value = f * 2.005;
  lp.type = "lowpass"; lp.frequency.setValueAtTime(2400, t); lp.frequency.exponentialRampToValueAtTime(500, t + 1.8);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + 2.6);
  const g2 = AC.createGain(); g2.gain.value = 0.25;
  o.connect(g); o2.connect(g2).connect(g); g.connect(lp).connect(dest);
  o.start(t); o2.start(t); o.stop(t + 2.7); o2.stop(t + 2.7);
}
function muDrum(t, dest) {
  const o = AC.createOscillator(), g = AC.createGain();
  o.type = "sine"; o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(45, t + 0.25);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.5, t + 0.01); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.35);
  o.connect(g).connect(dest); o.start(t); o.stop(t + 0.4);
}
function muStart(mood) {
  muStop();
  const M = MOODS[mood] || MOODS.quiet; MU.mood = mood;
  const ctx = muCtx(), master = ctx.createGain();
  master.gain.setValueAtTime(0.0001, ctx.currentTime); master.gain.setTargetAtTime(0.06, ctx.currentTime, 1.2);
  master.connect(ctx.destination); MU.master = master;
  if (M.drone) {                                       // bordone: fondamentale e quinta (o tritono, nella zona proibita)
    for (const r of [0.5, M.drone === 2 ? 0.5 * 1.414 : 0.75]) {
      const o = ctx.createOscillator(), g = ctx.createGain(); o.type = "sine"; o.frequency.value = M.base * r; g.gain.value = 0.12;
      o.connect(g).connect(master); o.start(); MU.drone.push(o);
    }
  }
  if (M.wind) {                                        // vento: rumore filtrato che ondeggia
    const len = ctx.sampleRate * 4, buf = ctx.createBuffer(1, len, ctx.sampleRate), ch = buf.getChannelData(0);
    for (let i = 0; i < len; i++) ch[i] = Math.random() * 2 - 1;
    const src = ctx.createBufferSource(), bp = ctx.createBiquadFilter(), g = ctx.createGain(), lfo = ctx.createOscillator(), lg = ctx.createGain();
    src.buffer = buf; src.loop = true; bp.type = "bandpass"; bp.frequency.value = 500; bp.Q.value = 0.8; g.gain.value = 0.18;
    lfo.frequency.value = 0.07; lg.gain.value = 300; lfo.connect(lg).connect(bp.frequency);
    src.connect(bp).connect(g).connect(master); src.start(); lfo.start(); MU.wind = src;
  }
  MU.next = ctx.currentTime + 0.3; MU.step = 0;
  let last = 2;
  MU.timer = setInterval(() => {
    if (!MU.master) return;
    while (MU.next < AC.currentTime + 1.0) {
      const t = MU.next;
      if (Math.random() < M.dens) {                    // una nota, con un passo breve sulla scala (melodia, non caso puro)
        last = Math.max(0, Math.min(M.scale.length - 1, last + [-2, -1, -1, 0, 1, 1, 2][Math.floor(Math.random() * 7)]));
        muPluck(M.base * Math.pow(2, M.scale[last] / 12), t, 0.5, MU.master);
        if (Math.random() < 0.18) muPluck(M.base * Math.pow(2, M.scale[Math.max(0, last - 2)] / 12) / 2, t + 0.02, 0.35, MU.master);
      }
      if (M.bell && MU.step % 16 === 0) muPluck(M.base * 4, t, 0.18, MU.master);
      if (M.drum && MU.step % 2 === 0) muDrum(t, MU.master);
      MU.step++;
      MU.next += M.beat * (0.85 + Math.random() * 0.3);
    }
  }, 250);
}
function musicFor(s) {
  if (!MUSIC || !SOUND || !AC_UNLOCKED) { if (MU.mood) muStop(); return; }
  let mood = s && s.duello && s.duello.arena && !s.duello.arena.finito ? "duel" : (s && s.luogo && s.luogo.type) || "quiet";
  if (!MOODS[mood]) mood = /sect|setta/.test(mood) ? "sect" : "quiet";
  if (mood !== MU.mood) try { muStart(mood); } catch (e) { /* audio non disponibile */ }
}
let AC_UNLOCKED = false;                               // i browser vogliono un gesto prima di suonare
document.addEventListener("pointerdown", () => { if (!AC_UNLOCKED) { AC_UNLOCKED = true; try { muCtx().resume(); } catch (e) { /* niente */ } musicFor(S); } }, { once: false });
function toast(head, body, tone) {
  sfx(tone || "info");
  const box = $("#toasts");
  if (!box) return;
  const d = document.createElement("div");
  d.className = "toast " + (tone || "");
  if (manual()) {                                     // resta finché non la chiudi (clic o Avanti); le altre aspettano in fila
    d.innerHTML = `<b>[ ${esc(head)} ]</b><div>${esc(body)}</div><i class="tclose" title="chiudi">×</i>`;
    d.addEventListener("click", () => { closeToast(d); advUi(); });
    if (box.children.length >= 3) { TOAST_Q.push(d); advUi(); return; }
    box.appendChild(d); advUi(); return;
  }
  d.innerHTML = `<b>[ ${esc(head)} ]</b><div>${esc(body.length > 180 ? body.slice(0, 177) + "…" : body)}</div>`;
  box.appendChild(d);
  setTimeout(() => d.classList.add("out"), 5200);
  setTimeout(() => d.remove(), 5800);
  while (box.children.length > 4) box.removeChild(box.firstChild);
}
function closeToast(d) {
  d.classList.add("out");
  setTimeout(() => { d.remove(); const nx = TOAST_Q.shift(); if (nx && $("#toasts")) $("#toasts").appendChild(nx); advUi(); }, 250);
}

function addCard(html) {
  const box = $("#log");
  const div = document.createElement("div");
  div.className = "entry card-entry";
  div.innerHTML = html;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

// ---------------- comandi ----------------
const MENUS = ["setta", "arti", "coltivazione", "eventi", "regni", "famiglia", "dimora", "faide", "tecniche", "sangue", "rendite",
  "dominio", "razze", "profondi", "spiriti", "attributi", "mercato", "asta", "ricette", "bacheca", "menu", "cloni", "discepoli", "sotto", "compagni", "stagione"];
// i comandi che mostrano una lista da cui scegliere si aprono come menu cliccabili
// LA TUA VIA: le schede della crescita in un pannello solo (l'ultima aperta si ricorda)
const VIA_TABS = ["coltivazione", "corpo", "sangue", "attributi", "tecniche", "profondi", "spiriti", "anime", "meridiani", "dharma", "forza"];
let lastVia = "coltivazione";
try { lastVia = localStorage.getItem("ji_via") || lastVia; } catch (e) { /* niente */ }
// ---------------- I PALAZZI (Aggiornamento 64): pochi pulsanti grandi, ognuno con le sue schede ----------------
// [chiave, etichetta, destinazione] — la destinazione è ciò che loadTab sa aprire
const PALACES = {
  oggi: { t: "🏯 Oggi", tabs: [["sintesi", "✦ Cosa fare", "oggi"], ["mete", "🎯 Mete", "mete"], ["eventi", "📅 Eventi", "m:eventi"], ["traguardi", "🏆 Traguardi", "m:stagione"]] },
  // (Agg. 72) sette schede invece di dodici: ognuna raccoglie due sistemi vicini
  via: { t: "☯ La tua Via", tabs: [["eroe", "🪟 Eroe", "personaggio"], ["coltivazione", "☯ Coltivazione", "m:via:coltivazione"],
    ["corpo", "🩸 Corpo e sangue", "m:via:corpo"], ["tecniche", "⚒ Tecniche e attributi", "m:via:tecniche"],
    ["profondi", "🌌 Dao e spiriti", "m:via:profondi"], ["anime", "✧ Anime e Dharma", "m:via:anime"], ["forza", "⚖ Forza", "m:via:forza"]] },
  setta: { t: "⛩ Setta e potere", tabs: [["setta", "⛩ Setta", "m:setta"], ["bacheca", "📋 Bacheca", "m:bacheca"], ["arti", "⚗ Arti", "m:arti"],
    ["ricette", "📜 Ricette", "m:ricette"], ["dimora", "⌂ Dimora", "m:dimora"], ["rendite", "💰 Rendite", "m:rendite"], ["dominio", "⛓ Dominio", "m:dominio"]] },
  seguaci: { t: "👥 Seguaci", tabs: [["cloni", "☯ Cloni", "m:cloni"], ["discepoli", "🎓 Discepoli", "m:discepoli"], ["legami", "♥ Legami", "persone"],
    ["compagni", "🌀 Compagni", "m:compagni"], ["famiglia", "🏠 Famiglia", "m:famiglia"], ["faide", "⚔ Faide", "m:faide"]] },
  mondo: { t: "🌍 Il mondo", tabs: [["mappa", "🗺 Mappa", "mappa"], ["mercato", "🏪 Mercato", "m:mercato"], ["asta", "⚖ Aste", "m:asta"],
    ["regni", "👑 Regni", "m:regni"], ["razze", "🐉 Razze", "m:razze"], ["sotto", "🙏 Mondo di sotto", "m:sotto"]] },
  tesori: { t: "🎒 Tesori", tabs: [["zaino", "🎒 Zaino", "tesori:zaino"], ["album", "🖼 Album", "tesori:album"], ["libro", "📖 Libro", "tesori:libro"]] },
  storia: { t: "📜 Storia", tabs: [["cronaca", "📜 Cronaca", "storia:cronaca"], ["scelte", "⚖ Scelte", "storia:scelte"], ["trama", "✦ Trama", "storia:trama"], ["mondo", "🌍 Mondo", "storia:mondo"], ["codex", "📖 Codex", "storia:codex"]] },
  opzioni: { t: "⚙ Opzioni", tabs: [["pilota", "✧ Pilota e difficoltà", "pilota"], ["partita", "💾 Partita", "aiuto"]] },
};
const TARGET_OF = {};                               // destinazione → [palazzo, scheda]
for (const [p, d] of Object.entries(PALACES)) for (const [k, , dest] of d.tabs) TARGET_OF[dest] = [p, k];
// le schede della Via accorpate: il vecchio indirizzo porta alla scheda che ora le contiene
const VIA_GROUP = { meridiani: "coltivazione", sangue: "corpo", attributi: "tecniche", spiriti: "profondi", dharma: "anime" };
for (const [k, g] of Object.entries(VIA_GROUP)) TARGET_OF["m:via:" + k] = ["via", g];
let palace = "oggi";
const lastTab = {};
try { palace = localStorage.getItem("ji_palace") || palace; Object.assign(lastTab, JSON.parse(localStorage.getItem("ji_ptab") || "{}")); } catch (e) { /* niente */ }
if (!PALACES[palace]) palace = "oggi";
function openPalace(p, key) {
  if (!PALACES[p]) return;
  palace = p;
  const L = (S && S.bloccati) || {};
  const tabs = PALACES[p].tabs.filter(([k]) => !L[p + ":" + k]);
  const k = key || (L[p + ":" + lastTab[p]] ? null : lastTab[p]) || tabs[0][0];
  const t = tabs.find((x) => x[0] === k) || tabs[0];
  loadTab(t[2]);
}
function renderPalaceHead() {
  const P = PALACES[palace]; if (!P) return;
  const cur = (TARGET_OF[tab] || [palace, ""])[1];
  const B = (S && S.badges) || {};
  $("#ptitle").textContent = P.t;
  const L = (S && S.bloccati) || {};
  const dot = (k) => B[palace + ":" + k] || (palace === "via" && Object.entries(VIA_GROUP).some(([m, g]) => g === k && B["via:" + m]));
  $("#subnav").innerHTML = P.tabs.filter(([k]) => !L[palace + ":" + k] || k === cur).map(([k, l, dest]) => `<button class="chip ${k === cur ? "on" : ""}" data-ptab="${palace}:${k}">${esc(l)}${dot(k) ? `<i class="pdot"></i>` : ""}</button>`).join("");
  document.querySelectorAll("#rail [data-palace]").forEach((b) => b.classList.toggle("on", b.dataset.palace === palace));
}
function renderBadges(s) {
  const B = s.badges || {};
  document.querySelectorAll("#rail [data-palace]").forEach((b) => {
    const d = b.querySelector(".dot"); if (!d) return;
    const n = B[b.dataset.palace] || 0;
    d.hidden = !n; d.textContent = n > 9 ? "9+" : n;
  });
}
const AS_MENU = { market: "mercato", shop: "mercato", negozio: "mercato", aste: "asta", auction: "asta", recipes: "ricette",
  invitations: "bacheca", inviti: "bacheca", missioni: "bacheca", missions: "bacheca", techniques: "tecniche", skills: "tecniche",
  clone: "cloni", clones: "cloni", sigilli: "via:dharma", rune: "via:dharma" };
// ---------------- (Agg. 71) IL MINIGIOCO DI MANO ----------------
// Tre colpi: un ago corre sulla barra, premi Spazio (o il pulsante) quando è nella zona verde.
// La zona si stringe e l'ago accelera. Il punteggio medio (0-100) diventa la qualità del lavoro.
let MINIGAME = true;
try { MINIGAME = localStorage.getItem("ji_minigame") !== "0"; } catch (e) { /* niente */ }
function playMinigame(kind) {
  return new Promise((done) => {
    const T = kind === "martello" ? { t: "🔨 Il ritmo del martello", s: "Colpisci quando l'ago è nella zona incandescente.", hit: "Colpisci!" }
      : { t: "⚗ Il fuoco del calderone", s: "Ravviva la fiamma quando l'ago è nella zona giusta.", hit: "Ravviva!" };
    const box = document.createElement("div"); box.id = "minigame";
    box.innerHTML = `<div class="mg"><b>${T.t}</b><div class="muted small">${T.s} Tre volte. Spazio o il pulsante.</div>
      <div class="mg-bar"><i class="mg-zone"></i><i class="mg-needle"></i></div>
      <div class="mg-score">colpo 1/3</div>
      <div class="mg-btns"><button class="primary" data-mg="hit">${T.hit}</button><button class="link" data-mg="skip">lascia al caso</button>
      <button class="link" data-mg="off" title="Si riattiva scrivendo 'minigiochi'">non chiederlo più</button></div></div>`;
    document.body.appendChild(box);
    const zone = box.querySelector(".mg-zone"), needle = box.querySelector(".mg-needle"), sc = box.querySelector(".mg-score");
    let round = 0, scores = [], t0 = performance.now(), raf = 0, zc = 0, zw = 0, speed = 0;
    const setZone = () => { zw = [18, 13, 9][round]; zc = 15 + Math.random() * 70; speed = [1.1, 1.5, 2.0][round];
      zone.style.left = (zc - zw / 2) + "%"; zone.style.width = zw + "%"; t0 = performance.now(); };
    const pos = () => 50 + 48 * Math.sin((performance.now() - t0) / 1000 * speed * Math.PI);
    const tick = () => { needle.style.left = pos() + "%"; raf = requestAnimationFrame(tick); };
    const end = (q) => { cancelAnimationFrame(raf); document.removeEventListener("keydown", key, true); box.remove(); done(q); };
    const hit = () => {
      const d = Math.abs(pos() - zc);
      const s = Math.max(0, Math.round(100 - Math.max(0, d - zw / 2) * 4));
      scores.push(s); round++;
      sc.textContent = `colpo ${Math.min(3, round + 1)}/3 · ultimo: ${s}` + (s >= 90 ? " — perfetto!" : s >= 60 ? " — buono" : s >= 30 ? " — così così" : " — mancato");
      sfx(s >= 60 ? "good" : "bad");
      if (round >= 3) { const q = Math.round(scores.reduce((a, b) => a + b, 0) / 3); sc.textContent = `Qualità del lavoro: ${q}/100`; setTimeout(() => end(q), 700); }
      else setZone();
    };
    const key = (ev) => { if (ev.key === " " || ev.key === "Enter") { ev.preventDefault(); ev.stopPropagation(); if (round < 3) hit(); }
      else if (ev.key === "Escape") { ev.preventDefault(); end(50); } };
    box.addEventListener("click", (ev) => { const b = ev.target.closest("[data-mg]"); if (!b) return; ev.stopPropagation();
      if (b.dataset.mg === "hit" && round < 3) hit();
      else if (b.dataset.mg === "skip") end(50);
      else if (b.dataset.mg === "off") { MINIGAME = false; try { localStorage.setItem("ji_minigame", "0"); } catch (e) { /* niente */ } end(50); } });
    document.addEventListener("keydown", key, true);
    setZone(); tick();
  });
}
async function run(cmd) {
  cmd = (cmd || "").trim();
  if (!cmd || busy) return;
  if (PENDING.length) flushAll();                     // agisci: il testo che stavi leggendo si mostra tutto
  if (CUT_NEXT) { document.querySelectorAll(".cutin").forEach((x) => x.remove()); CUT_NEXT = null; }
  const lc = cmd.toLowerCase();
  if (lc === "mappa" || lc === "map") return loadTab("mappa");
  if (lc === "equip" || lc === "equipaggiamento") return loadTab("tesori:zaino");
  if (lc === "traguardi") return loadTab("m:stagione");
  if (lc === "minigiochi") { MINIGAME = !MINIGAME; try { localStorage.setItem("ji_minigame", MINIGAME ? "1" : "0"); } catch (e) { /* niente */ }
    toast("Minigiochi", MINIGAME ? "attivi: forgia e calderone chiedono il tuo tempismo" : "spenti: decide il caso", "info"); return; }
  // (Agg. 71) forgia e alchimia: prima il minigioco di tempismo, poi il comando con la qualità
  if (MINIGAME && /^(equip forgia|forgia|craft|crea|distilla)\s+\S/.test(lc) && !/~q\d+$/.test(cmd)) {
    const q = await playMinigame(/forgia/.test(lc) ? "martello" : "calderone");
    if (q === null) return;
    cmd = cmd + " ~q" + q;
  }
  if (VIA_TABS.includes(lc)) return loadTab("m:via:" + lc);                              // la crescita: schede della Via
  if (lc === "via" || lc.startsWith("via ")) return loadTab("m:via:" + (lc.split(" ")[1] || lastVia));
  if (MENUS.includes(lc)) return loadTab("m:" + lc);   // i menu si aprono nel pannello
  if (AS_MENU[cmd.toLowerCase()]) return loadTab("m:" + AS_MENU[cmd.toLowerCase()]);
  busy = true;
  document.body.style.cursor = "progress";
  try {
    const r = await api("/api/comando", { cmd });
    addLog(r.log, cmd);
    if (r.morto) return await showDeath();
    await refresh();
  } catch (e) {
    addLog("⚠ Errore: " + e.message, cmd);
  } finally {
    busy = false;
    document.body.style.cursor = "";
  }
}

// ---------------- niente doppioni: ogni azione compare una volta sola a schermo ----------------
// Ordine di precedenza: i pulsanti fissi e i menu a sinistra, poi le tessere del luogo, poi la scena, il pannello di destra,
// infine le azioni suggerite. Il registro (testo narrativo) non viene toccato.
const KEY_ALIAS = { t: "train", allenati: "train", dormi: "sleep", market: "mercato", shop: "mercato", aste: "asta",
  auction: "asta", recipes: "ricette", missioni: "bacheca", inviti: "bacheca", invitations: "bacheca", save: "salva",
  coltivazione: "via", sangue: "via", attributi: "via", tecniche: "via", profondi: "via", spiriti: "via", forza: "via" };
function actKey(el) {
  let k = (el.dataset.menu || el.dataset.cmd || "").trim().toLowerCase();
  return KEY_ALIAS[k] || k;
}
let dedupeQueued = false;
function dedupe() {
  if (dedupeQueued) return;
  dedupeQueued = true;
  requestAnimationFrame(() => {
    dedupeQueued = false;
    const seen = new Set();
    const regions = ["#altar", "#todo", "#place", "#scene", "#tabbody", "#sugg"];
    for (const r of regions) {
      const root = $(r); if (!root) continue;
      root.querySelectorAll("button[data-cmd], button[data-menu]").forEach((el) => {
        if (el.closest(".attr") || el.closest(".choices") || el.closest("#todo") || el.closest(".todo-list")) return;   // scelte e «cosa fare»: sempre
        const k = actKey(el);
        el.classList.remove("dup");
        if (k === "via" && r === "#tabbody") return;                          // i collegamenti tra le schede della Via restano
        if (!k || /^\d+$/.test(k)) return;
        if (seen.has(k)) el.classList.add("dup"); else seen.add(k);
      });
    }
  });
}
new MutationObserver(() => dedupe()).observe(document.body, { childList: true, subtree: true });

// ---------------- stato ----------------
async function refresh() {
  const s = await api("/api/stato");
  if (s.fase === "nuovo") return showCreation();
  if (s.fase === "morto") return showDeath();
  S = s;
  renderTop(s); renderTodo(s); renderBadges(s); renderPlace(s); renderScene(s); renderSugg(s); renderAutoCfg(s);
  musicFor(s);
  renderPalaceHead();
  if (tab === "mete") renderMete(s);
  else if (tab === "oggi") renderToday(s);
  else if (tab === "mappa" || tab === "persone" || tab === "personaggio" || tab.startsWith("m:")) loadTab(tab);
}

function setBar(id, pct) { $(id).style.width = Math.max(0, Math.min(100, pct)) + "%"; }

function renderTop(s) {
  document.body.classList.toggle("no-numbers", !!s.nascondi_numeri);      // modalità Immortale
  $("#t-nome").textContent = s.nome;
  $("#t-regno").textContent = s.regno;
  $("#t-lv").textContent = "Lv " + (s.livello ?? "—");
  const pts = $("#t-punti");
  pts.hidden = !s.punti; pts.textContent = `✦ ${s.punti} punti`; pts.dataset.cmd = "via attributi";
  const q = s.rapidi || {};
  $("#q-spiriti").hidden = !q.spiriti; $("#q-trib").hidden = !q.tribulation;
  $("#q-sfonda").classList.toggle("ready", !!q.breakthrough);
  $("#q-sonno").classList.toggle("ready", !!q.sonno);
  $("#q-tempra").disabled = q.tempra === false;
  $("#q-raccogli").textContent = q.raccogli ? `✋ Raccogli (${q.raccogli})` : "✋ Raccogli";
  $("#q-raccogli").classList.toggle("ready", !!q.raccogli);
  // l'ALTARE: il cerchio dello strato e un solo tasto principale, quello giusto per il momento
  const rf = $("#ring-f"); if (rf) { const C = 2 * Math.PI * 52; rf.style.strokeDasharray = C; rf.style.strokeDashoffset = C * (1 - Math.max(0, Math.min(100, s.esperienza)) / 100); }
  $("#ring-pct").textContent = s.esperienza + "%";
  const mst = /Strato (\d+)\/(\d+)/.exec(s.regno || "");
  $("#ring-sub").textContent = mst ? `strato ${mst[1]}/${mst[2]}` : "strato";
  $("#altar-realm").textContent = (s.regno || "").split("·")[0].trim();
  $("#altar-where").textContent = ` · giorno ${s.giorno}, ore ${String(s.ora).padStart(2, "0")} · ${s.stagione}, ${s.meteo} · età ${s.eta}`;
  const pr = $("#primary");
  const P = q.tribulation ? ["tribulation", "⚡ Affronta la tribolazione"] : q.breakthrough ? ["breakthrough", "⇑ Sfonda!"]
          : q.sonno ? ["sleep", "☾ Dormi fino all'alba"] : ["train", "☯ Allenati"];
  pr.dataset.cmd = P[0]; pr.textContent = P[1];
  $("#q-sfonda").hidden = true;            // (Agg. 72) «Sfonda» compare solo quando sei pronto: è il tasto principale
  pr.title = P[0] === "train" && mst ? `Allenati: lo sfondamento si apre al ${mst[2]}° strato con la barra piena (ora ${mst[1]}/${mst[2]}, ${s.esperienza}%).` : "";
  $("#q-trib").hidden = !q.tribulation || P[0] === "tribulation";
  $("#q-sonno").hidden = P[0] === "sleep";
  setBar("#b-esp", s.esperienza); $("#v-esp").textContent = s.esperienza + "%";
  setBar("#b-qi", s.qi.pct); $("#v-qi").textContent = `${s.qi.cur}/${s.qi.max}`;
  setBar("#b-sp", s.spirito.pct); $("#v-sp").textContent = `${s.spirito.cur}/${s.spirito.max}`;
  if (s.anima) $("#b-sp").closest(".meter").title = `Spirito — ${s.anima}`;
  const c = $("#t-cuore");
  c.textContent = `Cuore ${s.cuore.val} · ${s.cuore.label}`;
  c.className = "chip" + (s.cuore.val < 30 ? " bad" : s.cuore.val < 50 ? " warn" : "");
  const f = $("#t-ferite");
  f.textContent = s.ferite.n ? `Ferite ${s.ferite.n} (max ${s.ferite.max})` : "Illeso";
  f.className = "chip" + (s.ferite.max >= 6 ? " bad" : s.ferite.n ? " warn" : "");
  f.hidden = !s.ferite.n;                                     // illeso: niente chip, più spazio
  $("#t-pietre").textContent = `Pietre ${s.pietre} · Fama ${s.fama}`;
  $("#t-tempo").textContent = `Giorno ${s.giorno}, ore ${String(s.ora).padStart(2, "0")} · ${s.stagione}, ${s.meteo} · ${s.era} · età ${s.eta}`;
}

const DIR = { north: "Nord", south: "Sud", east: "Est", west: "Ovest", up: "Su", down: "Giù" };
function renderPlace(s) {
  const L = s.luogo;
  let h = `<h2>${esc(L.name)} <span class="muted">· pericolo ${L.danger}</span></h2>`;
  if (L.desc) h += `<p class="desc">${esc(L.desc)}</p>`;
  if (s.prigioniero) h += `<p class="desc">⛓ Sei prigioniero: <button data-cmd="evadi">Pianifica la fuga</button></p>`;
  h += `<div class="exits">` + s.uscite.map((e) =>
    `<button data-cmd="move ${e.dir}" title="pericolo ${e.danger}">${DIR[e.dir] || e.dir} → ${esc(e.name)}</button>`).join("") + `</div>`;
  if (s.presenti.length) {
    const many = s.presenti.length > 6 && !showAllNpcs;
    const list = many ? s.presenti.slice(0, 6) : s.presenti;
    h += `<div class="npcs">` + list.map((n) => {
      const first = n.name.split(" ")[0];
      return `<span class="npc ${n.rel === "nemico" ? "foe" : n.rel === "legame" ? "friend" : ""}" title="${esc(n.tag)}">${face(n.name, 22, n.rel === "nemico" ? "--bad" : "--accent", "", { arch: n.arch, kind: n.kind, f: n.f })}${esc(n.name)}${n.tag ? ` <span class="muted">${esc(n.tag)}</span>` : ""}
        <button data-cmd="osserva ${esc(first)}" title="la sua finestra di stato">osserva</button><button data-cmd="talk ${esc(first)}">parla</button><button data-cmd="attack ${esc(first)}">attacca</button></span>`;
    }).join("") + (many ? `<button id="more-npc">+ altri ${s.presenti.length - 6}</button>` : "") + `</div>`;
  }
  if (s.azioni_luogo && s.azioni_luogo.length) {
    h += `<div class="tiles">` + s.azioni_luogo.map((t) => t.ok
      ? `<button class="tile ${t.tone || ""}" data-cmd="${esc(t.cmd)}" title="${esc(t.label)} — ${esc(t.hint)} (${esc(t.cmd)})"><span class="ti">${esc(t.icon)}</span><span class="tl">${esc(t.label)}</span><span class="th">${esc(t.hint)}</span></button>`
      : `<button class="tile" disabled title="${esc(t.why)}"><span class="ti">${esc(t.icon)}</span><span class="tl">${esc(t.label)}</span><span class="th">${esc(t.why)}</span></button>`).join("") + `</div>`;
  }
  $("#place").innerHTML = h;
  const lu = slotImg("luoghi", L.type);
  $("#place").classList.toggle("has-img", !!lu);
  $("#place").style.backgroundImage = lu ? `linear-gradient(90deg, var(--panel) 38%, color-mix(in srgb, var(--panel) 55%, transparent)), url("${lu}")`
                                         : V.landscape(L.type, L.name);
  const m = $("#more-npc"); if (m) m.onclick = () => { showAllNpcs = true; renderPlace(S); };
}

// ---------------- arena del duello: ritratti, barre, carte delle tecniche, alleati ----------------
// (Agg. 69) barre della vita animate: si disegnano alla larghezza di prima e scendono, con la scia del danno
const HP_PREV = { me: null, foe: null };
function hpBar(side, cur, max, foe) {
  const p = Math.max(0, Math.min(100, Math.round(100 * cur / Math.max(1, max))));
  const prev = HP_PREV[side] == null ? p : HP_PREV[side];
  const tone = p <= 20 ? " low" : p <= 50 ? " mid" : "";
  return `<div class="hpbar${foe ? " foe" : ""}${tone}" data-side="${side}" data-to="${p}"><b class="ghost" style="width:${prev}%"></b><i style="width:${prev}%"></i><span>${cur.toLocaleString("it-IT")} / ${max.toLocaleString("it-IT")}</span></div>`;
}
function animateHp(root) {
  requestAnimationFrame(() => requestAnimationFrame(() => root.querySelectorAll(".hpbar[data-to]").forEach((b) => {
    const to = b.dataset.to + "%"; b.querySelector("i").style.width = to;
    setTimeout(() => { const g = b.querySelector(".ghost"); if (g) g.style.width = to; }, 450);
    HP_PREV[b.dataset.side] = Number(b.dataset.to);
  })));
}
const stBadges = (list) => (list || []).map((x) => `<span class="stb st-${esc(x.k)}" title="${esc(x.nome)}: ancora ${x.turni} turn${x.turni === 1 ? "o" : "i"}">${esc(x.icon)}<sub>${x.turni}</sub></span>`).join("");
const elTag = (e) => e && e[0] ? `<span class="eltag el-${esc(e[0])}" title="Elemento: ${esc(e[2])}">${esc(e[1])} ${esc(e[2])}</span>` : "";
function arenaHtml(a, s) {
  const pct = (c, m) => Math.max(0, Math.min(100, Math.round(100 * c / Math.max(1, m))));
  const L = a.ultimo || {};
  const pop = (v, cls) => v ? `<span class="pop ${cls}">−${Number(v).toLocaleString("it-IT")}</span>` : "";
  const txt = s.scena.text.split("\n").filter((l) => l.trim() && !l.includes("█") && !l.includes("·····") && !/^Turno \d/.test(l) && !/^Qi \d/.test(l));
  const me = `<div class="fighter me">${face(a.tu.nome, 72, "--accent", "io")}
      <div class="fi"><b>${esc(a.tu.nome)}</b><div class="muted small">${esc(a.tu.regno)}</div>
      ${hpBar("me", a.tu.hp, a.tu.max, false)}<div class="stati">${elTag((a.elementi || {}).tu)}${stBadges(a.stati_tu)}</div>
      <div class="mini"><div class="bar qi"><i style="width:${pct(a.tu.qi[0], a.tu.qi[1])}%"></i></div><small>Qi ${a.tu.qi[0]}</small>
        <div class="bar sp"><i style="width:${pct(a.tu.spirito[0], a.tu.spirito[1])}%"></i></div><small>Spirito ${a.tu.spirito[0]}</small></div>
      ${a.concentrato ? `<span class="tag rare">☯ concentrato</span>` : ""}</div>${pop(L.subito, "bad" + (L.critico_lui ? " crit" : ""))}</div>`;
  const foe = `<div class="fighter foe">${face(a.nome, 72, "--bad", "", { arch: a.lui.arch, kind: a.lui.kind, f: a.lui.f })}
      <div class="fi"><b>${esc(a.nome)}</b><div class="muted small">${esc(a.lui.regno)} · ${esc(a.lui.forza)}</div>
      ${hpBar("foe", a.lui.hp, a.lui.max, true)}<div class="stati">${elTag((a.elementi || {}).lui)}${stBadges(a.stati_lui)}</div>
      <span class="tag" title="${esc(a.stile_desc)}">${esc(a.stile)}</span>${a.rango === "boss" ? `<span class="tag boss">♛ BOSS${a.fase > 1 ? " · fase " + a.fase : ""}</span>` : a.rango === "elite" ? `<span class="tag rare">★ élite</span>` : ""}
      ${a.vantaggio > 1 ? `<span class="tag good">☸ elemento a tuo favore</span>` : a.vantaggio < 1 ? `<span class="tag bad">☸ elemento a suo favore</span>` : ""}
      ${a.intento && !a.finito ? `<div class="intent it-${esc(a.intento.tipo)}" title="Cosa farà al prossimo scambio"><b>${esc(a.intento.icon)} Prossima mossa:</b> ${esc(a.intento.testo)}${a.intento.danno[1] ? `<small>fino a −${a.intento.danno[1].toLocaleString("it-IT")} (${a.intento.pct[0]}–${a.intento.pct[1]}% della tua vita)</small>` : ""}</div>` : a.carica ? `<span class="tag bad blink">⚠ carica un colpo pesante</span>` : ""}</div>${pop(L.inflitto, "good" + (L.critico ? " crit" : ""))}</div>`;
  const allies = a.alleati.length ? `<details class="allies-box"><summary>${a.alleati.length} alleat${a.alleati.length === 1 ? "o" : "i"} in campo</summary><div class="allies">${a.alleati.map((x) => `<span>${esc(x)}</span>`).join("")}</div></details>` : "";
  const EFF = { super: ["superefficace", "eff-super"], poco: ["poco efficace", "eff-poco"] };
  const cards = a.carte.map((c, i) => `<button class="card-act k-${esc(c.kind)} ${c.hot ? "hot" : ""} ${c.el ? "el-" + esc(c.el) : ""}" ${c.ok ? `data-cmd="${esc(c.cmd)}"` : "disabled"} title="${esc(c.desc)}${c.el_nome ? " — elemento " + esc(c.el_nome) : ""}${c.stato ? " — può lasciare " + esc(c.stato) : ""}${c.why ? " — " + esc(c.why) : ""}">
      <span class="ci">${esc(c.icon)}${i < 9 ? `<kbd>${i + 1}</kbd>` : ""}</span><b>${esc(c.name)}</b><small>${esc(c.desc)}</small>
      ${c.eff ? `<span class="eff ${EFF[c.eff][1]}">${EFF[c.eff][0]}</span>` : ""}${c.stato ? `<span class="cst">${esc(c.stato)}</span>` : ""}
      <em>${c.ok ? esc(c.cost) : esc(c.why)}</em>${c.cd ? `<span class="cdn">${c.cd}</span>` : ""}</button>`).join("");
  const ab = S && slotImg("luoghi", S.luogo.type);
  return `<div class="arena"${ab ? ` style="background-image:linear-gradient(color-mix(in srgb, var(--panel) 80%, transparent), var(--panel) 70%), url('${ab}')"` : ""}><div class="arena-head">⚔ Duello — turno ${a.turno}</div>
    <div class="ring-fight">${me}<div class="vs">VS</div>${foe}</div>
    ${a.finito ? "" : `<div class="hand">${cards}</div>`}
    <div class="arena-log">${txt.slice(-6).map((l) => `<div class="${lineClass(l)}">${actionize(esc(l))}</div>`).join("")}</div>${allies}</div>`;
}

// IMMAGINI: la cartella «immagini» (anche le sottocartelle luoghi/, ritratti/, bestie/, creature/, mondi/)
// prende il posto dei disegni generati. strumenti/scarica_immagini.py la riempie di dipinti classici.
let IMAGES = [], IMGMAP = {};
function loadImages() {
  return api("/api/immagini").then((list) => {
    IMAGES = list || []; IMGMAP = {};
    for (const f of IMAGES) {
      const i = f.lastIndexOf("/"), dir = i >= 0 ? f.slice(0, i) : "", base = f.slice(i + 1).replace(/\.[^.]+$/, "");
      IMGMAP[(dir ? dir + "/" : "") + V.slug(base)] = f;
    }
    if (S) { renderPlace(S); renderScene(S); }
  }).catch(() => {});
}
loadImages();
const imgUrl = (f) => "/immagini/" + f.split("/").map(encodeURIComponent).join("/");
function slotImg(dir, key) { const f = IMGMAP[(dir ? dir + "/" : "") + V.slug(key)]; return f ? imgUrl(f) : null; }
window.daoImg = (k) => imgOf(["dao/" + k]);
// (Agg. 68) il primo quadro che esiste tra i candidati ("oggetti/arma_spada", "oggetti/tesoro"…)
function imgOf(list) {
  for (const p of [].concat(list || [])) { const i = p.lastIndexOf("/"); const u = slotImg(i >= 0 ? p.slice(0, i) : "", p.slice(i + 1)); if (u) return u; }
  return null;
}
const BEAST_WORDS = ["drago", "fenice", "tigre", "tartaruga", "qilin", "gru", "volpe", "serpente", "kun"];
function faceSrc(name, o = {}) {
  let u = slotImg("", name) || slotImg("ritratti", name);
  if (u) return u;
  if (o.io) return slotImg("ritratti", "eroe");
  if (o.kind && o.kind !== "human") {
    const low = String(name).toLowerCase(), w = BEAST_WORDS.find((x) => low.includes(x));
    return (w && slotImg("bestie", w)) || slotImg("creature", o.kind);
  }
  // (Agg. 69) volti diversi: tra le varianti di un tipo (guardia, guardia_2, guardia_3…) sceglie sempre la stessa
  // per la stessa persona, in base al nome. Chi non ha un tipo con ritratto pesca da tutti i volti maschili.
  if (o.f) return pickVariant(o.arch === "anziano" || o.arch === "patriarca" ? ["f_anziana"] : ["f"], name) || slotImg("ritratti", o.arch);
  return pickVariant(o.arch && variants(o.arch).length ? [o.arch] : MALE_TYPES, name);
}
const MALE_TYPES = ["anziano", "patriarca", "eremita", "discepolo", "guardia", "mercante", "vagabondo", "cacciatore"];
const VAR_CACHE = {};
function variants(base) {
  if (VAR_CACHE[base] && VAR_CACHE[base].n === IMAGES.length) return VAR_CACHE[base].v;
  const re = new RegExp("^ritratti/" + V.slug(base) + "\\d*$");             // lo slug toglie «_»: guardia_2 → guardia2
  const v = Object.keys(IMGMAP).filter((k) => re.test(k)).sort();
  VAR_CACHE[base] = { n: IMAGES.length, v };
  return v;
}
function nameHash(n) { let h = 2166136261; for (const c of String(n)) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
function pickVariant(bases, name) {
  const all = [].concat(...bases.map(variants));
  return all.length ? imgUrl(IMGMAP[all[nameHash(name) % all.length]]) : null;
}
function face(name, size, aura, kind = "", o = {}) {
  const u = faceSrc(name, Object.assign({ io: kind === "io" }, o));
  return u ? `<img class="portrait" src="${u}" width="${size}" height="${size}" alt="" loading="lazy">` : V.portrait(name, kind, size, aura);
}
let lastArenaTurn = null;
// (Agg. 68) il CUT-IN delle mosse, come nei giochi di lotta: il quadro della tua mossa, poi quello del colpo nemico
function cutIn(box, L, ar) {
  const arena = box.querySelector(".arena"); if (!arena) return;
  const steps = [];
  const mine = imgOf(L.img);
  if (mine) steps.push({ u: mine, t: L.nome || ({ colpisci: "Colpo", difendi: "Difesa", concentrati: "Concentrazione", pillola: "Pillola", fuggi: "Fuga" }[L.mossa] || "Colpo"),
    sub: (L.inflitto ? `−${Number(L.inflitto).toLocaleString("it-IT")}${L.critico ? " · CRITICO" : ""}` : "") +
      (L.eff === "super" ? " · SUPEREFFICACE!" : L.eff === "poco" ? " · poco efficace…" : ""), cls: "me" + (L.eff ? " eff-" + L.eff : ""), el: L.el });
  const foe = L.subito ? imgOf(L.img_nemico) : null;
  if (foe) steps.push({ u: foe, t: ar.nome, sub: `−${Number(L.subito).toLocaleString("it-IT")}${L.critico_lui ? " · CRITICO" : ""}`, cls: "foe" });
  if (!steps.length) return;
  document.querySelectorAll(".cutin").forEach((x) => x.remove());
  const r = box.getBoundingClientRect();
  const el = document.createElement("div"); el.className = "cutin";
  Object.assign(el.style, { position: "fixed", left: r.left + "px", top: r.top + "px", width: r.width + "px", height: Math.min(r.height, 360) + "px" });
  document.body.appendChild(el);
  let i = 0;
  const show = () => {
    if (i >= steps.length) { el.remove(); CUT_NEXT = null; advUi(); return; }
    const s = steps[i++];
    if (s.el) sfx("el_" + s.el); else sfx(s.cls === "foe" ? "hit" : "swing");
    el.innerHTML = `<div class="cut ${s.cls}"><div class="cut-img" style="background-image:url('${s.u}')"></div><div class="cut-t"><b>${esc(s.t)}</b>${s.sub ? `<span>${esc(s.sub)}</span>` : ""}</div></div>`;
    const f = document.querySelector(s.cls === "me" ? "#scene .fighter.foe" : "#scene .fighter.me"); if (f) { f.classList.remove("shake"); void f.offsetWidth; f.classList.add("shake"); }
    if (manual()) { el.firstElementChild.insertAdjacentHTML("beforeend", `<em class="cut-next">▸ clic o Spazio</em>`); CUT_NEXT = show; advUi(); }
    else setTimeout(show, s.cls === "me" ? 1250 : 1000);
  };
  el.addEventListener("click", () => { if (manual() && CUT_NEXT) { advance(); return; } el.remove(); });
  show();
}
function renderScene(s) {
  const box = $("#scene");
  // con una scena aperta la colonna centrale fa spazio: luogo e diario si stringono, la scena si allarga
  document.body.classList.toggle("scene-on", !!s.scena);
  document.body.classList.toggle("duel-on", !!(s.scena && s.duello));
  if (!s.scena) { box.hidden = true; box.innerHTML = ""; box.classList.remove("in-duel"); return; }
  box.hidden = false;
  const ar = s.duello && s.duello.arena;
  box.classList.toggle("in-duel", !!ar);
  if (ar) codexHint("duello", "toast");
  let cut = null;
  const sig = ar && ar.ultimo ? ar.turno + "|" + JSON.stringify(ar.ultimo) : null;    // ogni scambio nuovo, anche l'ultimo
  if (sig && sig !== lastArenaTurn) { const first = lastArenaTurn === null || !ar.ultimo.mossa; lastArenaTurn = sig;
    if (ar.ultimo.inflitto) sfx(ar.ultimo.critico ? "crit" : "hit"); if (!first) cut = ar.ultimo; }
  if (!ar) { HP_PREV.me = HP_PREV.foe = null; }
  if (ar && !ar.finito) { box.innerHTML = arenaHtml(ar, s); animateHp(box); if (cut) cutIn(box, cut, ar); return; }
  if (ar && ar.finito) {
    box.innerHTML = arenaHtml(ar, s) + `<div class="choices">` + s.scena.choices.map((c) => `<button data-cmd="${c.n}"><b>${c.n}.</b> ${esc(c.label)}</button>`).join("") + `</div>`;
    animateHp(box);
    if (cut) cutIn(box, cut, ar);
    return;
  }
  const du = s.duello ? `<div class="duel"><div><span>Tu</span><div class="bar hp"><i style="width:${s.duello.tu.pct}%"></i></div><em>${s.duello.tu.cur}/${s.duello.tu.max}</em></div>
    <div><span>${esc(s.duello.nome)}</span><div class="bar hp foe"><i style="width:${s.duello.lui.pct}%"></i></div><em>${s.duello.lui.cur}/${s.duello.lui.max}</em></div>
    <div class="muted">Stile: ${esc(s.duello.stile)}${s.duello.vantaggio > 1 ? " · ☸ elemento a tuo favore (+25%)" : s.duello.vantaggio < 1 ? " · ☸ elemento a suo favore (−15%)" : ""}</div>
    ${s.duello.carica ? `<div class="l-warn">⚠ Sta raccogliendo il qi: difenditi! (attento alle finte dei subdoli)</div>` : ""}</div>` : "";
  // nel duello le barre grafiche sostituiscono quelle di testo del terminale
  const txt = s.duello ? s.scena.text.split("\n").filter((l) => !l.includes("█") && !l.includes("·····") && !l.startsWith("⚠")).join("\n") : s.scena.text;
  const sci = imgOf(s.scena.imgs);
  box.innerHTML = `${sci ? `<div class="scene-img" style="background-image:url('${sci}')"></div>` : ""}<h3>✦ ${esc(s.scena.title)}</h3>${du}<p>${actionize(esc(txt))}</p><div class="choices">` +
    s.scena.choices.map((c) => `<button data-cmd="${c.n}"><b>${c.n}.</b> ${esc(c.label)}${c.hint ? `<small>[${esc(c.hint)}]</small>` : ""}</button>`).join("") +
    `</div>`;
}

// «COSA FARE ORA»: le tre cose più urgenti, con il perché e il tasto per farle
function todoCard(x) {
  return `<button class="todo-card ${x.hot ? "hot" : ""}" data-cmd="${esc(x.cmd)}" title="${esc(x.cmd)}"><span class="ti">${esc(x.icon)}</span>
    <span class="tt"><b>${esc(x.title)}</b><small>${esc(x.why)}</small></span></button>`;
}
function renderTodo(s) {
  const box = $("#todo"); if (!box) return;
  const items = (s.todo || []).slice(0, 3);
  box.innerHTML = s.scena || !items.length ? "" : `<div class="h">Cosa fare ora</div><div class="todo-row">${items.map(todoCard).join("")}</div>`
    + ((s.todo || []).length > 3 ? `<button class="link more-todo" data-ptab="oggi:sintesi">e altre ${(s.todo || []).length - 3} cose ›</button>` : "");
}
function renderToday(s) {
  const b = $("#tabbody");
  const groups = {};
  for (const x of s.todo || []) (groups[x.palace] = groups[x.palace] || []).push(x);
  let h = s.quotidiana ? V.dailyQuest(s.quotidiana) : "";
  if (!(s.todo || []).length) h += `<div class="empty">Niente di urgente: allenati, esplora, segui le tue mete.</div>`;
  for (const p of Object.keys(PALACES)) {
    if (!groups[p]) continue;
    h += `<div class="card sec todo-list"><b>${esc(PALACES[p].t)}</b>${groups[p].map(todoCard).join("")}</div>`;
  }
  b.innerHTML = h;
}
function pilotHtml() {
  return `<div class="card sec pilot"><b>✧ Pilota automatico</b>
    <div class="muted small">Si avvia dall'altare, al centro. Qui decidi come si comporta.</div>
    <label>Bersagli <select data-auto="bersagli"><option>nessuno</option><option>bestie</option><option>ricercati</option><option>deboli</option><option>tutti</option></select></label>
    <label>Condotta <select data-auto="condotta"><option>virtuosa</option><option>prudente</option><option>opportunista</option><option>spietata</option></select></label>
    <label><input type="checkbox" data-auto="sfonda"> Sfonda da solo</label>
    <label>Rischio massimo <input type="number" min="0" max="100" data-auto="rischio"> %</label>
    <label><input type="checkbox" data-auto="assorbi"> Divora i caduti</label>
    <label><input type="checkbox" data-auto="loot"> Raccogli il bottino</label>
    <label><input type="checkbox" data-auto="oggetti"> Usa pillole ed essenze</label>
    <label><input type="checkbox" data-auto="routine"> Faccende (stipendio, missioni, cura dei tesori)</label>
    <label><input type="checkbox" data-auto="potenzia"> Potenzia la dimora</label>
    <label><input type="checkbox" data-auto="pietre"> Assorbi le pietre in eccesso</label>
    <label><input type="checkbox" data-auto="setta"> Setta: iscriviti e ascendi</label>
    <label><input type="checkbox" data-auto="assente"> Medita mentre sei via (a gioco chiuso, fino a 12 ore)</label></div>
    <div class="card sec"><b>▦ Schede</b><div class="muted small">All'inizio le schede si aprono poco a poco, con il regno.</div>
    <label><input type="checkbox" id="showall"> Mostra sempre tutte le schede</label></div>
    <div class="card sec"><b>⚖ Difficoltà</b><div class="muted small">Quanto morde il mondo: agguati, inseguitori, rischio di morte.</div>
    <select id="diff"><option value="sereno">Sereno</option><option value="normale">Normale</option><option value="spietato">Spietato</option><option value="immortale">Immortale (senza numeri né salvataggi manuali)</option></select></div>`;
}

function renderSugg(s) {
  // niente doppioni: via le azioni che hanno già un pulsante fisso a sinistra o una tessera del luogo
  const fixed = new Set([...document.querySelectorAll("#altar [data-cmd], #todo [data-cmd], #place [data-cmd]")]
    .filter((b) => !b.hidden).map(actKey));
  const norm = (c) => { const k = c.trim().toLowerCase(); return KEY_ALIAS[k] || k; };
  s.suggVisibili = s.suggerimenti.filter((x) => !fixed.has(norm(x.cmd)));
  $("#sugg").innerHTML = s.scena ? "" :
    s.suggVisibili.map((x, i) => `<button data-cmd="${esc(x.cmd)}" title="${esc(x.label)} — ${esc(x.cmd)}"><span class="n">${i + 1}</span>${esc(x.label)}</button>`).join("");
}

async function renderMete(s) {
  const b = $("#tabbody");
  const head = (s.quotidiana ? V.dailyQuest(s.quotidiana) : "") + `<h4>Mete</h4>`;
  const list = !s.mete.length ? `<div class="empty">Nulla di importante sta accadendo, per ora.</div>` : s.mete.map((d) => {
    const where = d.dist === 0 ? "QUI" : d.dist == null ? "in un altro mondo" : `${d.dist} tappe`;
    return `<div class="dest card"><div class="t">${esc(d.title)}</div>
      <div class="w">${esc(d.where)} · ${where}</div>
      <div class="b">${d.dist ? `<button data-cmd="vai ${d.n}">Vai</button>` : ""}${d.join && d.dist ? `<button class="primary" data-cmd="iscriviti ${d.n}">Partecipa</button>` : d.join ? `<span class="muted small">↖ tessera qui</span>` : ""}</div></div>`;
  }).join("");
  b.innerHTML = head + list + `<div id="objs"><div class="empty">Carico gli obiettivi…</div></div>`;
  try { const o = await objectivesHtml(); if (tab === "mete" && $("#objs")) $("#objs").innerHTML = o; } catch (e) { /* niente */ }
}

// ---------------- pannelli ----------------
const PANEL_TEXT = { personaggio: 1, tesori: 1, storia: 1, mondo: 1, aiuto: 1 };
const SUBTABS = {
  personaggio: [["stato", "🪟 Stato"], ["dao", "☸ Dao"], ["radici", "🌱 Radici"], ["crescita", "📈 Crescita"], ["dettagli", "📄 Schede"]],
  tesori: [["zaino", "🎒 Zaino"], ["album", "🖼 Album"], ["libro", "📖 Libro"]],
  storia: [["cronaca", "📜 Cronaca"], ["scelte", "⚖ Scelte"], ["trama", "✦ Trama"], ["mondo", "🌍 Mondo"], ["codex", "📖 Codex"]],
};
// (Agg. 70) il CODEX: la prima volta che apri una scheda, una pagina che spiega quel sistema
let CODEX = null, CODEX_SEEN = {};
try { CODEX_SEEN = JSON.parse(localStorage.getItem("ji_codex_seen") || "{}"); } catch (e) { /* niente */ }
async function codexData() { if (!CODEX) CODEX = await api("/api/codex").catch(() => []); return CODEX; }
function codexKeyOf(name) {
  if (name.startsWith("m:via:")) return name.slice(6);
  if (name === "tesori:zaino" || name === "tesori") return "zaino";
  if (name === "m:setta" || name.startsWith("m:setta")) return "setta";
  if (name === "mappa") return "mappa";
  return null;
}
async function codexHint(key, where) {
  if (!key || CODEX_SEEN[key]) return;
  const c = (await codexData()).find((x) => x.key === key); if (!c) return;
  if (where === "toast") { CODEX_SEEN[key] = 1; saveCodexSeen(); toast("Codex — " + c.titolo, c.testo, "info"); return; }
  const b = $("#tabbody"); if (!b || b.querySelector(".codex-card")) return;
  b.insertAdjacentHTML("afterbegin", `<div class="card codex-card"><b>📖 ${esc(c.titolo)}</b><p>${esc(c.testo)}</p>
    <button class="primary" data-codex-ok="${esc(key)}">Ho capito</button> <span class="muted small">Lo ritrovi in Storia → Codex.</span></div>`);
}
function saveCodexSeen() { try { localStorage.setItem("ji_codex_seen", JSON.stringify(CODEX_SEEN)); } catch (e) { /* niente */ } }
// (Agg. 72) l'ALBUM: sei pagine da completare; chi hai trovato è a colori, chi manca è un'ombra
let albumPage = "bestie";
function albumHtml(a) {
  const pg = a.pagine.find((p) => p.key === albumPage) || a.pagine[0];
  const tabs = a.pagine.map((p) => `<button class="chip ${p.key === pg.key ? "on" : ""}" data-album="${p.key}">${esc(p.titolo)} <small>${p.pct}%</small>${p.premi.length ? `<i class="pdot"></i>` : ""}</button>`).join("");
  const cards = pg.voci.map((v) => { const u = imgOf(v.img);
    return `<div class="al-card ${v.visto ? "seen" : "unseen"}" title="${v.visto ? esc(v.nome) : "ancora da scoprire"}">${u ? `<img src="${u}" alt="" loading="lazy">` : `<span class="eq-ph">?</span>`}
      <b>${v.visto ? esc(v.nome) : "???"}</b>${v.visto && v.sub ? `<small>${esc(v.sub)}</small>` : ""}</div>`; }).join("");
  const claim = a.pagine.some((p) => p.premi.length) ? `<button class="primary" data-cmd="album premi">📖 Ritira i premi dell'album</button>` : "";
  return `<div class="card sec album"><b>🖼 Album del coltivatore</b> <span class="muted small">completo al ${a.totale}% · premi al 25, 50, 75 e 100% di ogni pagina</span>
    <div class="subtabs">${tabs}</div>
    <div class="mbar"><span>${esc(pg.titolo)}</span><div class="bar"><i style="width:${pg.pct}%"></i></div><em>${pg.visti}/${pg.totale}</em></div>
    ${claim ? `<div class="tools">${claim}</div>` : ""}<div class="al-grid">${cards}</div></div>`;
}
// (Agg. 70) il registro delle tue scelte
async function choicesHtml() {
  const list = await api("/api/scelte").catch(() => []);
  if (!list.length) return `<div class="empty">Ancora nessuna scelta: quando una scena ti chiede di decidere, la ritrovi qui.</div>`;
  let day = null, h = `<div class="card sec choices-log"><b>⚖ Le tue scelte</b><div class="muted small">Ogni decisione presa nelle scene, dalla più recente.</div>`;
  for (const c of list) {
    if (c.giorno !== day) { day = c.giorno; h += `<div class="cl-day">Giorno ${day}</div>`; }
    h += `<div class="cl-row"><span class="muted">${esc(c.titolo)}</span><b>${esc(c.scelta)}</b></div>`;
  }
  return h + `</div>`;
}
async function codexHtml() {
  const list = await codexData();
  return `<div class="codex">` + list.map((c) => `<details class="card sec"><summary><b>${esc(c.titolo)}</b></summary><p>${esc(c.testo)}</p></details>`).join("") + `</div>`;
}
const sub = { personaggio: "stato", tesori: "zaino", storia: "cronaca" };
try { const j = JSON.parse(localStorage.getItem("ji_sub") || "{}"); Object.assign(sub, j); } catch (e) { /* niente */ }
function subChips(name) {
  if (name === "tesori" || name === "storia") return "";                    // le schede le mostra il palazzo
  return `<div class="subtabs">` + SUBTABS[name].map(([k, l]) => `<button class="chip ${sub[name] === k ? "on" : ""}" data-sub="${name}:${k}">${l}</button>`).join("") + `</div>`;
}
async function loadTab(name) {
  if (name === "tesori" || name === "storia") name = name + ":" + sub[name];      // le schede interne ora sono del palazzo
  if (name.startsWith("tesori:") || name.startsWith("storia:")) { const [t, k] = name.split(":"); sub[t] = k; }
  if (name.startsWith("m:via:")) { lastVia = name.slice(6); try { localStorage.setItem("ji_via", lastVia); } catch (e) { /* niente */ } }
  const where = TARGET_OF[name] || TARGET_OF[name.split(":").slice(0, 2).join(":")];
  if (where) {
    palace = where[0]; lastTab[palace] = where[1];
    try { localStorage.setItem("ji_palace", palace); localStorage.setItem("ji_ptab", JSON.stringify(lastTab)); } catch (e) { /* niente */ }
  }
  const keep = tab === name;
  tab = name;
  renderPalaceHead();
  const b = $("#tabbody");
  if (name === "oggi") { if (S) renderToday(S); return; }
  if (name === "pilota") { b.innerHTML = pilotHtml(); if (S) renderAutoCfg(S); return; }
  if (name.startsWith("tesori:") || name.startsWith("storia:")) name = name.split(":")[0];
  if (name.startsWith("m:")) {
    if (!keep) b.innerHTML = `<div class="empty">Carico…</div>`;
    try { const top = b.scrollTop; b.innerHTML = menuHtml(await api("/api/menu/" + name.slice(2))); if (keep) b.scrollTop = top; }
    catch (e) { b.innerHTML = `<div class="empty">Errore: ${esc(e.message)}</div>`; }
    if (!keep) codexHint(codexKeyOf(name));
    return;
  }
  if (name === "mete") { if (S) renderMete(S); return; }
  if (name === "mappa") { await loadMap(); codexHint("mappa"); return; }
  const top = keep ? b.scrollTop : 0;
  if (!keep) b.innerHTML = `<div class="empty">Carico…</div>`;
  const texts = async (panel, open) => (await api("/api/pannello/" + panel)).map((p) =>
    `<details class="txt"${open && p.cmd === open ? " open" : ""}><summary>${esc(TITLES[p.cmd] || p.cmd)}</summary><pre>${actionize(esc(p.text))}</pre></details>`).join("");
  try {
    let h = "";
    if (name === "persone") { GRAPH = await api("/api/rete"); h = V.graph(GRAPH) + await peopleHtml(); }
    else if (name === "personaggio") {
      const sb = sub.personaggio;
      h = subChips("personaggio");
      if (sb === "dettagli") h += await texts("personaggio", "status");
      else if (sb === "crescita") h += V.charts(await api("/api/grafici"));
      else { HERO = await api("/api/eroe"); h += heroHtml(HERO, sb, sb === "dao" ? await api("/api/dao") : null); }
    } else if (name === "tesori") {
      h = subChips("tesori");
      if (sub.tesori === "libro") { BOOK = await api("/api/libro"); h += V.book(BOOK, bookCat); }
      else if (sub.tesori === "album") h += albumHtml(await api("/api/album"));
      else h += `<div class="tools"><button class="primary" data-cmd="tesori cura">✧ Cura tutti i tesori</button></div>` + await bagHtml() + await texts("tesori");
    } else if (name === "storia") {
      h = subChips("storia");
      if (sub.storia === "codex") h += await codexHtml();
      else if (sub.storia === "scelte") h += await choicesHtml();
      else if (sub.storia === "mondo") h += await worldHtml() + await texts("mondo");
      else if (sub.storia === "trama") h += await texts("storia", "trama");
      else h += await chronicleHtml();
    } else if (name === "aiuto") h = await gameHtml() + V.legend() + await texts("aiuto");
    b.innerHTML = h;
    if (keep) b.scrollTop = top;
    else if (tab === "tesori:zaino") codexHint("zaino");
  } catch (e) { b.innerHTML = `<div class="empty">Errore: ${esc(e.message)}</div>`; }
}

// ---------------- l'eroe: finestra di stato e grafici ----------------
let HERO = null, daoAll = false;
function heroHtml(h, sb, daos) {
  if (!h || !h.finestra) return `<div class="empty">Nessun personaggio.</div>`;
  if (sb === "stato") return V.statusWindow(h) + V.deepTriad(h.profondi) + V.spiritCards(h.spiriti, h.spiriti_slot);
  if (sb === "dao") return V.daoChart(daos || [], daoAll) + V.deepTriad(h.profondi);
  if (sb === "radici") return V.talentRadar(h.talento) + V.rootsChart(h.radici, h.combinazioni, h.talenti);
  if (sb === "corpo") return V.bodyCard(h.corpo, h.anima, h.cuore) + V.bloodChart(h.sangue);
  return "";
}
// menu a sezioni: setta, arti, coltivazione, eventi, regni, famiglia
// IL TESTO ESSENZIALE: a schermo solo le voci più alte; il resto è a un clic (▸ altri…)
const MENU_FULL = 6, LINES_FULL = 3;
function msecHtml(s, full) {
  const si = full && s.img ? imgOf(s.img) : null;
  let h = (s.divider ? `<h4 class="mdiv">${esc(s.divider)}</h4>` : "") + `<div class="card sec msec${full ? "" : " mini"}${si ? " has-img" : ""}">${si ? `<img class="msec-img" src="${si}" alt="" loading="lazy">` : ""}<b>${s.icon ? esc(s.icon) + " " : ""}${esc(s.title)}</b>`;
  for (const b of s.bars) h += `<div class="mbar ${b.tone || ""}"><span>${esc(b.label)}</span><div class="bar"><i style="width:${b.pct}%"></i></div><em>${b.text ? esc(b.text) : b.pct + "%"}</em></div>`;
  const lines = full ? s.lines : s.lines.slice(0, 1);
  lines.slice(0, LINES_FULL).forEach((l) => { h += `<div class="mline">${actionize(esc(l))}</div>`; });
  if (lines.length > LINES_FULL) h += `<details class="more"><summary>altri ${lines.length - LINES_FULL} dettagli</summary>` +
    lines.slice(LINES_FULL).map((l) => `<div class="mline">${actionize(esc(l))}</div>`).join("") + `</details>`;
  const ok = s.actions.filter((a) => a.ok), no = s.actions.filter((a) => !a.ok);
  const acts = full ? ok.concat(no) : ok.slice(0, 2);
  const many = s.actions.length > 2;
  if (acts.length) h += `<div class="mact">` + acts.map((a) => a.ok
    ? `<button class="${a.main ? "primary" : ""}" data-cmd="${esc(a.cmd)}" title="${esc(a.cmd)}">${esc(a.label)}</button>`
    : `<button disabled class="${many ? "chip" : ""}" title="${esc(a.why)}">${esc(a.label)}${many ? "" : `<small>${esc(a.why)}</small>`}</button>`).join("") + `</div>`;
  return h + `</div>`;
}
function menuHtml(m) {
  if (m.errore) return `<div class="empty">${esc(m.errore)}</div>`;
  const tabs = m.tabs && palace !== "via" ? `<div class="subtabs viatabs">` + m.tabs.map((t) => `<button class="chip ${t.on ? "on" : ""}" data-menu="${esc(t.key)}">${esc(t.label)}</button>`).join("") + `</div>` : "";
  let h = tabs + `<div class="card menuhead"><h3>${esc(m.inner_title || m.title)}</h3>${m.sub.map((s) => `<div class="muted">${esc(s)}</div>`).join("")}</div>`;
  // nelle schede accorpate della Via ogni sistema ha le sue prime sezioni aperte
  const cut = m.sections.some((s) => s.divider) ? m.sections.length : MENU_FULL;
  m.sections.slice(0, cut).forEach((s) => { h += msecHtml(s, true); });
  const rest = m.sections.slice(cut);
  if (rest.length) h += `<details class="card more mrest"><summary>Altre ${rest.length} voci</summary>` + rest.map((s) => msecHtml(s, false)).join("") + `</details>`;
  return h + (m.foot ? `<div class="muted">${esc(m.foot)}</div>` : "");
}

let GRAPH = null, BOOK = null, bookCat = "tutto";
const TITLES = { status: "Stato", rating: "Potenza e classe", dao: "Dao (dettaglio)", corpo: "Corpo e cuore",
  radici: "Radici spirituali", sangue: "Lignaggi di sangue", tesori: "Tesori (dettaglio)", arma: "Arma",
  trama: "La trama", goals: "Diario degli obiettivi", arcinemico: "Arcinemico", retaggio: "Retaggio spezzato",
  svolte: "Svolte", era: "Era del mondo", setta: "La tua setta", ritmo: "Ritmo degli eventi", "help tutto": "Tutti i comandi" };

function itemList(title, items, empty) {
  return `<div class="card sec"><b>${title}</b>` + (items.length ? items.map((x) =>
    `<button class="obj" data-cmd="${esc(x.cmd)}" title="${esc(x.cmd)}"><span>${esc(x.t)}</span><span class="go">▶ ${esc(x.cmd)}</span></button>`).join("")
    : `<div class="empty">${actionize(empty)}</div>`) + `</div>`;
}
// le TRAME in corso: cosa è successo finora, gli indizi svelati uno alla volta, e i pulsanti per indagare
function plotCard(j) {
  const need = j.servono, have = j.indizi.length;
  const clues = need ? `<div class="mbar rare"><span>Indizi</span><div class="bar"><i style="width:${Math.min(100, Math.round(100 * have / Math.max(1, j.totale)))}%"></i></div><em>${have}/${j.totale} · ${have >= need ? "sai abbastanza" : `ne servono ${need}`}</em></div>` +
    (have ? `<ol class="clues">${j.indizi.map((c) => `<li>🔎 ${esc(c)}</li>`).join("")}</ol>` : `<div class="muted small">Nessun indizio ancora: indaga, o segui la trama.</div>`) : "";
  const log = j.diario.length ? `<details class="more"><summary>cosa è successo finora</summary><ul class="plotlog">${j.diario.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></details>` : "";
  const btn = [];
  if (j.indaga) btn.push(`<button class="primary" data-cmd="trame indaga ${j.n}">🔎 Indaga</button>`);
  else if (need && j.indagato_oggi && have < j.totale) btn.push(`<button disabled title="si può indagare una volta al giorno">🔎 Domani potrai indagare ancora</button>`);
  if (j.accusa) btn.push(`<button class="primary" data-cmd="trame accusa ${j.n}">⚖ Affronta il colpevole</button>`);
  else if (j.continua) btn.push(`<button data-cmd="trame continua ${j.n}">▶ Continua la trama</button>`);
  return `<div class="card sec plot"><div class="plot-head"><b>🕸 ${esc(j.titolo)}</b><span class="lvtag">atto ${j.atto}/${j.atti}</span></div>
    <div class="muted small">${j.attesa ? `Prossimo atto «${esc(j.prossimo)}» tra ${j.attesa} giorni` : `Prossimo atto «${esc(j.prossimo)}»: pronto`}</div>
    ${clues}${log}${btn.length ? `<div class="tools">${btn.join("")}</div>` : ""}</div>`;
}
async function objectivesHtml() {
  const o = await api("/api/obiettivi");
  return (o.indagini && o.indagini.length ? `<div class="card sec"><b>🕸 Trame e indagini</b></div>` + o.indagini.map(plotCard).join("") : "") +
    itemList("★ Obiettivi primari", o.primari, "Nessuno, per ora: la tua leggenda la scrivi tu.") +
    itemList("◆ Obiettivi secondari", o.secondari, "Niente in sospeso.") +
    itemList("✎ Missioni", o.missioni, "Nessuna missione: unisciti a una setta per la bacheca, o ascolta chi ha bisogno di te ('richieste').");
}

function personCard(c, me, enemy) {
  const ratio = me.potenza ? c.potenza / me.potenza : 1;
  const pct = Math.max(4, Math.min(100, Math.round(50 * ratio)));
  const cls = /molto più forte/.test(c.confronto) ? "bad" : /più forte/.test(c.confronto) ? "warn" : /debole/.test(c.confronto) ? "good" : "";
  const first = c.nome.split(" ")[0];
  let btn = "";
  if (c.vivo) {
    if (c.qui) {
      btn += enemy ? `<button data-cmd="duello ${esc(first)}">Duello</button><button data-cmd="attack ${esc(first)}">Attacca</button>`
                   : `<button data-cmd="parla ${esc(first)}">Parla</button>`;
    } else btn += `<button data-cmd="vai ${esc(c.dove)}">Vai da ${c.donna ? "lei" : "lui"}</button>`;
    if (!enemy && c.favore) btn += `<button data-cmd="favori">Favore</button>`;
  }
  const hearts = !enemy && c.intimita ? " · " + "♥".repeat(Math.min(5, c.intimita)) : "";
  return `<div class="person card ${enemy ? "enemy" : ""}">${face(c.nome, 52, enemy ? "--bad" : "--good", "", { arch: c.arch, kind: c.kind, f: c.donna })}
    <div class="top"><b>${esc(c.nome)}</b> <span class="muted">${esc(c.ruolo)}${hearts}</span></div>
    <div class="w">${esc(c.regno)} · ${c.vivo ? (c.qui ? "QUI" : esc(c.dove)) : "✝ caduto"}${c.perche ? " · " + esc(c.perche) : ""}</div>
    ${c.vivo ? `<div class="pw"><span>Potenza ${c.potenza}</span><div class="bar"><i style="width:${pct}%"></i></div><span class="${cls}">${esc(c.confronto)}</span></div>` : ""}
    ${c.favore ? `<div class="w">♥ ${esc(c.favore)}</div>` : ""}
    <div class="b">${btn}</div></div>`;
}
async function peopleHtml() {
  const d = await api("/api/persone");
  return `<div class="card"><b>Tu</b> — ${esc(d.io.regno)} · potenza ${d.io.potenza} <span class="muted">(la barra a metà = alla tua pari)</span></div>` +
    `<h4>Alleati e affetti</h4>` + (d.alleati.length ? d.alleati.map((c) => personCard(c, d.io, false)).join("") : `<div class="empty">Ancora nessuno.</div>`) +
    `<h4>Nemici</h4>` + (d.nemici.length ? d.nemici.map((c) => personCard(c, d.io, true)).join("") : `<div class="empty">Nessun nemico dichiarato. Per ora.</div>`);
}

async function bagHtml() {
  const [it, eq, gr] = await Promise.all([api("/api/zaino"), api("/api/equip").catch(() => []), api("/api/gear").catch(() => null)]);
  // (Agg. 68) ciò che porti addosso, con il suo quadro
  const eqh = eq.length ? `<div class="card sec"><b>⚔ Arma, vasi d'anima e sigilli</b><div class="equip">` + eq.map((e) => {
    const u = imgOf(e.img);
    return `<button class="eq-slot" data-cmd="${esc(e.cmd)}" title="${esc(e.nota || e.nome)}">${u ? `<img src="${u}" alt="" loading="lazy">` : `<span class="eq-ph">✦</span>`}
      <small>${esc(e.slot)}</small><b>${esc(e.nome)}</b>${e.nota ? `<em>${esc(e.nota)}</em>` : ""}</button>`; }).join("") + `</div></div>` : "";
  const gh = gr ? gearHtml(gr) : "";
  if (!it.length) return gh + eqh + `<div class="card"><b>Zaino</b><div class="empty">Vuoto.</div></div>`;
  return gh + eqh + `<div class="card"><b>🎒 Zaino</b><div class="bag">` + it.map((x) => {
    const u = imgOf(x.img);
    return `<div class="bag-it r-${esc(x.rarita)}" title="${esc(x.desc)}">${u ? `<img src="${u}" alt="" loading="lazy">` : `<span class="eq-ph">✦</span>`}
     ${x.n > 1 ? `<span class="qty">×${x.n}</span>` : ""}<b>${esc(x.nome)}</b><small>${esc(x.tipo)} · ${esc(x.rarita.replace("_", " "))}</small>
     <div class="bag-act">${x.tipo === "essenza" ? `<button data-cmd="use tutte ${esc(x.nome)}">Assorbi${x.n > 1 ? " tutte" : ""}</button>`
       : `<button data-cmd="use ${esc(x.nome)}">Usa</button>${x.n > 1 ? `<button data-cmd="use tutte ${esc(x.nome)}">Tutte</button>` : ""}`}</div></div>`; }).join("") + `</div>` +
    `<div class="tools"><button class="primary" data-cmd="raccogli">Raccogli e assorbi tutto</button>` +
    `<button data-cmd="use all">Usa anche le pillole</button>` +
    `<button data-cmd="autoraccolta">Raccolta automatica on/off</button>` +
    `<button data-cmd="autoassorbi">Assorbimento automatico on/off</button></div></div>`;
}

// (Agg. 69) l'EQUIPAGGIAMENTO come una bambola di carta: sei posti attorno alla figura, lo zaino dei pezzi sotto
const RAR_IT = { comune: "comune", raffinata: "raffinata", pregiata: "pregiata", divina: "divina" };
function gearPiece(p, slot) {
  const u = imgOf((p && p.img) || slot.img);
  return `<div class="gd-slot gd-${esc(slot.slot)} ${p ? "r-" + esc(p.rar) : "empty"}" title="${p ? esc(p.nome + " — " + p.stats.join(", ") + (p.set ? " — set " + p.set : "")) : "posto libero"}">
    ${u ? `<img src="${u}" alt="" loading="lazy">` : `<span class="eq-ph">✦</span>`}<small>${esc(slot.posto)}</small>
    ${p ? `<b>${esc(p.nome)}</b><em>${esc(p.stats[0] || "")}</em>${p.id ? `<button class="mini" data-cmd="equip togli ${esc(slot.slot)}">togli</button>` : ""}`
      : `<em>vuoto</em><button class="mini" data-cmd="equip forgia ${esc(slot.slot)}">forgia</button>`}</div>`;
}
function gearHtml(g) {
  const hero = imgOf(["ritratti/eroe"]);
  const doll = `<div class="gdoll">${g.posti.map((s) => gearPiece(s.pezzo, s)).join("")}
    <div class="gd-hero">${hero ? `<img src="${hero}" alt="">` : V.portrait("io", "io", 120, "--accent")}</div></div>`;
  const bag = g.zaino.length ? `<div class="gbag">${g.zaino.map((x) => {
    const u = imgOf(x.img);
    return `<div class="bag-it r-${esc(x.rar)} ${x.meglio ? "better" : ""}" title="${esc(x.stats.join(", "))}${x.set ? " — set " + esc(x.set) : ""}">
      ${u ? `<img src="${u}" alt="" loading="lazy">` : `<span class="eq-ph">✦</span>`}${x.meglio ? `<span class="qty">▲ meglio</span>` : ""}
      <b>${esc(x.nome)}</b><small>${esc(x.posto)} · ${esc(RAR_IT[x.rar] || x.rar)} · regno ${x.tier}</small><small>${esc(x.stats.join(" · "))}</small>
      <div class="bag-act"><button data-cmd="equip metti ${x.id}">Indossa</button><button data-cmd="equip scomponi ${x.id}" title="+${x.valore} pietre">Scomponi</button></div></div>`; }).join("")}</div>` : "";
  return `<div class="card sec gear"><b>🧥 Equipaggiamento</b> <span class="muted small">${esc(g.riepilogo)}</span>${doll}
    <div class="tools"><button class="primary" data-cmd="equip auto">Indossa il meglio</button>${g.zaino.length ? `<button data-cmd="equip scomponi tutto">Scomponi i superati</button>` : ""}
    <span class="muted small">Forgia: ${g.costo_forgia.toLocaleString("it-IT")} pietre a pezzo (regno ${g.regno})</span></div>${bag}</div>`;
}

let allLives = false;
async function chronicleHtml() {
  const cr = await api("/api/cronaca" + (allLives ? "?tutte" : ""));
  const rows = cr.slice(-60).reverse().map((r) => `<div class="cr"><span class="muted">${allLives ? `vita ${r.vita} · ` : ""}g.${r.giorno}</span> ${esc(r.icona)} ${esc(r.testo)}</div>`).join("");
  return `<div class="card"><b>Cronaca</b> <button id="cr-all">${allLives ? "Solo questa vita" : "Tutte le vite"}</button>
    <button data-cmd="cronaca esporta">Esporta (.md)</button>
    <div class="crlist">${rows || `<div class="empty">Ancora nulla da raccontare.</div>`}</div></div>
    <div class="tools"><button data-cmd="encounter">Rileggi la scena</button><button data-cmd="favori">Favori</button></div>`;
}

async function worldHtml() {
  const w = await api("/api/mondo");
  const reg = w.regni.map((k) => `<tr><td>${esc(k.nome)}</td><td>${esc(k.re)}</td><td>${esc(k.rango)}</td><td>${k.favore}</td><td>${k.guerra ? "⚔" : ""}</td></tr>`).join("");
  const top = w.classifica.map((x) => `<tr class="${x.tu ? "me" : ""}"><td>${x.pos}</td><td>${esc(x.nome)}</td><td>${esc(x.regno)}</td><td>${x.potenza}</td></tr>`).join("");
  const rz = w.razze.map((r) => `<tr><td>${esc(r.nome)}</td><td>${r.incontrata ? r.rel : "—"}</td><td>${r.onore}</td></tr>`).join("");
  return `<div class="card"><b>Classifica del Cielo</b><table><tr><th>#</th><th>Nome</th><th>Regno</th><th>Potenza</th></tr>${top}</table></div>
    <div class="card"><b>Regni</b><table><tr><th>Regno</th><th>Sovrano</th><th>Il tuo rango</th><th>Favore</th><th></th></tr>${reg}</table>
      <div class="tools"><button data-cmd="corte">Corte qui</button><button data-cmd="sostieni">Sostieni il regno</button></div></div>
    <div class="card"><b>Razze antiche</b><table><tr><th>Razza</th><th>Rapporto</th><th>Onore</th></tr>${rz}</table></div>`;
}

async function gameHtml() {
  const m = await api("/api/merito");
  const sv = await api("/api/salvataggi");
  const last = await api("/api/ultimo_salvataggio").catch(() => ({}));
  let h = `<div class="card"><b>Salvataggi</b> <span class="muted">— automatici ogni 5 giorni (auto_1, auto_2, auto_3 a rotazione)</span>
    ${last.testo ? `<div class="muted small">Ultimo salvataggio: ${esc(last.testo)}</div>` : ""}
    <div class="tools" style="margin-top:6px"><button class="primary" data-cmd="salva">💾 Salva ora</button>
      <a class="btn" href="/api/esporta" download title="Scarica la partita in un file .jiw: per conservarla o portarla su un altro computer">⬇ Esporta in un file</a>
      <label class="btn" title="Carica una partita esportata (.jiw): quella attuale viene messa al sicuro">⬆ Importa da file<input type="file" id="imp-file" accept=".jiw,.db" hidden></label></div>` +
    (sv.length ? sv.map((x) => `<div class="dest"><div class="t">${esc(x.name)}</div><div class="w">${esc(x.when)}</div>
      <div class="b"><button data-cmd="carica ${esc(x.name)}">Carica</button></div></div>`).join("") : `<div class="empty">Nessun salvataggio.</div>`) + `</div>`;
  h += `<div class="card"><b>Rinascita e nuova partita</b>`;
  if (m.senza_ritorno) {
    h += `<p class="muted">Modalità Senza Ritorno: niente reincarnazione volontaria.</p>`;
  } else {
    h += `<p>☸ <b>Reincarnati ora</b>, di tua scelta. Merito di questa vita: <b>${m.punti}</b>
      <span class="muted">(${Object.entries(m.parti).map(([k, v]) => `${esc(k)} ${v}`).join(", ")})</span></p>
      <ul class="muted"><li>porti con te <b>tutti</b> i frammenti della vita passata</li><li>rinasci con <b>${m.pietre}</b> pietre spirituali</li>
      <li>ciclo del Samsara: coltivazione <b>×${m.coltivazione.toFixed(2)}</b> per sempre</li><li>la memoria del regno ti fa risalire in fretta</li></ul>
      <button class="primary" id="btn-reinc">☸ Reincarnati ora</button> `;
  }
  h += `<button id="btn-restart">↺ Ricomincia da zero</button>
    <p class="muted">«Ricomincia da zero» mette il mondo attuale in archivio (puoi ricaricarlo) e ne crea uno nuovo.</p></div>`;
  return h;
}

const RAR = { narrative: "arma", elemental: "elemento", systemic: "sistemico", superior: "superiore", deep: "profondo" };
async function daoBars() {
  const ds = await api("/api/dao");
  if (!ds.length) return "";
  return `<div class="card daos"><b>I tuoi Dao</b>` + ds.map((d) =>
    `<div class="dao" title="${esc(d.name)} — comprensione ${d.comp}; prossima soglia: ${esc(d.next)} a ${d.goal}">
      <span class="n">${esc(d.short)} <small class="muted">${esc(RAR[d.rarity] || "")}</small></span>
      <div class="bar"><i style="width:${d.pct}%"></i></div>
      <span class="v">${d.comp} · ${esc(d.label)}</span></div>`).join("") + `</div>`;
}

// ---------------- mappa: zoom, trascinamento, minacce, sette, presenze ----------------
const ICON = { city: "▣", mountain: "▲", ruin: "▒", forbidden_zone: "☠", forest: "♣", village: "⌂", sect: "⛩", wilderness: "∴", cave: "◓", lake: "≈" };
let MAP = null, MAPFULL = null, mapView = null, mapWide = null, mapLayers = { minacce: true, presenze: true, sette: true };
async function loadMap() {
  const wide = document.body.classList.contains("wide");
  const prevHere = MAP ? (MAP.nodes.find((n) => n.here) || {}).id : null;
  MAP = await api("/api/mappa" + (wide ? "?largo" : ""));
  const here = (MAP.nodes.find((n) => n.here) || {}).id;
  if (here !== prevHere || mapWide !== wide) mapView = null;     // la vista resta dov'era finché non ti sposti
  mapWide = wide;
  drawMap();
}
function dangerColor(d) {
  const t = Math.max(0, Math.min(1, (d || 0) / 10));
  const hue = 140 - 140 * t;               // verde → rosso
  return `hsl(${hue} 55% 50%)`;
}
function drawMap() {
  const m = MAP; if (!m) return;
  const W = 92, H = 64, NW = 80, NH = 48;
  const xs = m.nodes.map((n) => n.x), ys = m.nodes.map((n) => n.y);
  const minx = Math.min(...xs), miny = Math.min(...ys);
  const cols = Math.max(...xs) - minx + 1, rows = Math.max(...ys) - miny + 1;
  const px = (n) => (n.x - minx) * W + 10, py = (n) => (n.y - miny) * H + 10;
  const full = [0, 0, cols * W + 10, rows * H + 10];
  MAPFULL = full;
  if (!mapView) {
    const me = m.nodes.find((n) => n.here);
    const cw = Math.max(300, $("#tabbody").clientWidth - 4), ch = Math.min(window.innerHeight * 0.7, 620);
    let vw = Math.min(Math.max(full[2], 3.5 * W), 7 * W), vh = vw * ch / cw;
    if (vh < Math.min(full[3], 5 * H)) { vh = Math.min(full[3], 5 * H) + 20; vw = vh * cw / ch; }
    mapView = me ? [px(me) + NW / 2 - vw / 2, py(me) + NH / 2 - vh / 2, vw, vh] : full.slice();
  }
  const byId = Object.fromEntries(m.nodes.map((n) => [n.id, n]));
  let svg = `<svg id="mapsvg" viewBox="${mapView.join(" ")}" xmlns="http://www.w3.org/2000/svg">
    <defs><radialGradient id="glow"><stop offset="0" stop-color="var(--accent)" stop-opacity=".55"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></radialGradient>
      <filter id="ink" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="7" result="n"/>
        <feDisplacementMap in="SourceGraphic" in2="n" scale="3"/></filter>
      <clipPath id="med" clipPathUnits="objectBoundingBox"><circle cx=".5" cy=".5" r=".5"/></clipPath></defs><g class="edges" filter="url(#ink)">`;
  // (Agg. 69) la MAPPA DIPINTA: le strade sono tratti di pennello leggermente curvi, i luoghi hanno il loro sigillo
  for (const [a, b] of m.edges) {
    const A = byId[a], B = byId[b];
    const x1 = px(A) + NW / 2, y1 = py(A) + NH / 2, x2 = px(B) + NW / 2, y2 = py(B) + NH / 2;
    const bend = (((a * 37 + b * 61) % 9) - 4) * 2.2, dx = x2 - x1, dy = y2 - y1, L = Math.hypot(dx, dy) || 1;
    const cx = (x1 + x2) / 2 - dy / L * bend, cy = (y1 + y2) / 2 + dx / L * bend;
    svg += `<path class="edge" data-e="${Math.min(a, b)}-${Math.max(a, b)}" d="M${x1},${y1} Q${cx.toFixed(1)},${cy.toFixed(1)} ${x2},${y2}"/>`;
  }
  svg += `</g>`;
  for (const n of m.nodes) {
    const x = px(n), y = py(n);
    const cls = ["node", "r" + Math.min(9, n.ring || 0), n.visited ? "visited" : "unseen", n.here ? "here" : "", n.marks.length ? "mark" : "", n.threats.length && mapLayers.minacce ? "threat" : ""].join(" ");
    const short = n.name.length > 14 ? n.name.slice(0, 13) + "…" : n.name;
    const ic = n.home ? "⌂" : (ICON[n.type] || "·");
    const tip = [`${n.name} — pericolo ${n.danger}`, n.sect ? `⛩ sede: ${n.sect}` : "", n.people ? `👥 ${n.people} persone` : "",
      n.beasts ? `🐾 ${n.beasts} creature` : "", n.threats.length ? `⚔ ti cercano: ${n.threats.join(", ")}` : "",
      n.marks.length ? `★ ${n.marks.join(", ")}` : "", n.mystery ? `❖ ${n.mystery}` : "",
      n.ring ? `frontiera, anello ${n.ring}` : ""].filter(Boolean).join("\n");
    svg += `<g class="${cls}" data-cmd="vai #${n.id}" data-node-id="${n.id}"><title>${esc(tip)}</title>`;
    if (n.here) svg += `<circle class="pulse" cx="${x + NW / 2}" cy="${y + NH / 2}" r="46" fill="url(#glow)"/>`;
    svg += `<rect x="${x}" y="${y}" width="${NW}" height="${NH}" rx="8"/>
      <rect class="dz" x="${x + 3}" y="${y + NH - 6}" width="${NW - 6}" height="4" rx="2" style="fill:${dangerColor(n.danger)}"/>
      ${(() => { const u = !n.home && imgOf(["mappa/" + n.type]); return u
        ? `<image href="${u}" x="${x + 4}" y="${y + 3}" width="22" height="22" clip-path="url(#med)" preserveAspectRatio="xMidYMid slice"/>${n.here ? `<circle class="herering" cx="${x + 15}" cy="${y + 14}" r="12"/>` : ""}`
        : `<text class="ic" x="${x + 6}" y="${y + 17}">${n.here ? "◉" : ic}</text>`; })()}
      <text class="nm" x="${x + 6}" y="${y + 38}">${esc(short)}</text>`;
    let bx = x + NW - 4;
    const badge = (t, c) => { svg += `<text class="bd ${c}" x="${bx}" y="${y + 15}" text-anchor="end">${t}</text>`; bx -= 16; };
    if (n.mystery) badge("❖", "rare");
    if (n.threats.length && mapLayers.minacce) badge("⚔", "bad");
    if (n.marks.length) badge("★", "warn");
    if (n.sect && mapLayers.sette) badge("⛩", "info");
    if (n.people && mapLayers.presenze) badge(String(Math.min(9, n.people)), "muted");
    svg += `</g>`;
  }
  svg += `</svg>`;
  const tog = (k, l) => `<button class="chip ${mapLayers[k] ? "on" : ""}" data-maptool="layer:${k}">${l}</button>`;
  const fr = m.frontiera || {};
  const frh = fr.totale ? `<div class="frontier"><span><b>🗺 ${esc(fr.mondo)}</b> · frontiera ${fr.anelli}/${fr.totale}</span>
      <div class="bar"><i style="width:${Math.round(100 * fr.anelli / fr.totale)}%"></i></div>
      <span class="muted">${fr.prossimo ? `prossimo anello al regno ${fr.prossimo.regno}, strato ${fr.prossimo.strato}` : "mappa completa"}</span></div>` : "";
  const mb = slotImg("mondi", String(fr.strato ?? 0));
  $("#tabbody").innerHTML = `<div id="map"${mb ? ` class="has-img" style="--mapbg:url('${mb}')"` : ""}>${frh}
    <div class="maptools"><button data-maptool="in">＋</button><button data-maptool="out">－</button><button data-maptool="me">◉ Tu</button><button data-maptool="all">⤢ Tutto</button>
      ${tog("minacce", "⚔ Minacce")}${tog("sette", "⛩ Sette")}${tog("presenze", "👥 Presenze")}</div>
    ${svg}
    <div class="legend">❖ incontro misterioso · i luoghi più scuri sono gli anelli più lontani (nemici più forti, bottini più rari, più risorse) · ◉ tu · ⌂ dimora · ▣ città · ▲ montagna · ▒ rovine · ☠ zona proibita · ★ meta in corso · ⚔ chi ti dà la caccia · ⛩ sede di setta · numero = persone.
      La striscia sotto ogni luogo è il pericolo (verde → rosso). Rotella per lo zoom, trascina per muoverti. Passa sopra un luogo per vedere la strada; clic per viaggiare a tappe (lungo la via si raccoglie, si incontra, si cade in agguato). ⤢ in alto allarga il pannello e la mappa.</div></div>`;
  bindMapDrag();
}
// passando sopra un luogo, la strada a tappe che percorreresti
function mapRoute(target) {
  document.querySelectorAll("#mapsvg .edge.route").forEach((l) => l.classList.remove("route"));
  document.querySelectorAll("#mapsvg .node.onroute").forEach((g) => g.classList.remove("onroute"));
  if (!MAP || target == null) return;
  const me = MAP.nodes.find((n) => n.here); if (!me) return;
  const adj = {};
  for (const [a, b] of MAP.edges) { (adj[a] = adj[a] || []).push(b); (adj[b] = adj[b] || []).push(a); }
  const prev = { [me.id]: null }, q = [me.id];
  while (q.length) { const c = q.shift(); if (c === target) break; for (const n of adj[c] || []) if (!(n in prev)) { prev[n] = c; q.push(n); } }
  if (!(target in prev)) return;
  for (let c = target; prev[c] != null; c = prev[c]) {
    const p = prev[c], l = document.querySelector(`#mapsvg .edge[data-e="${Math.min(c, p)}-${Math.max(c, p)}"]`);
    if (l) l.classList.add("route");
    const g = document.querySelector(`#mapsvg [data-node-id="${c}"]`); if (g) g.classList.add("onroute");
  }
}
function mapTool(t) {
  if (!MAP || !mapView) return;
  if (t.startsWith("layer:")) { const k = t.slice(6); mapLayers[k] = !mapLayers[k]; return drawMap(); }
  const [x, y, w, h] = mapView, cx = x + w / 2, cy = y + h / 2;
  if (t === "in" || t === "out") { const f = t === "in" ? 0.75 : 1.33; mapView = [cx - (w * f) / 2, cy - (h * f) / 2, w * f, h * f]; }
  if (t === "me") mapView = null;
  if (t === "all") mapView = MAPFULL.slice();
  drawMap();
}
function bindMapDrag() {
  const s = $("#mapsvg"); if (!s) return;
  let drag = null, moved = false;
  s.addEventListener("wheel", (ev) => {
    ev.preventDefault();
    const f = ev.deltaY < 0 ? 0.85 : 1.18, r = s.getBoundingClientRect();
    const [x, y, w, h] = mapView, mx = x + ((ev.clientX - r.left) / r.width) * w, my = y + ((ev.clientY - r.top) / r.height) * h;
    mapView = [mx - (mx - x) * f, my - (my - y) * f, w * f, h * f];
    s.setAttribute("viewBox", mapView.join(" "));
  }, { passive: false });
  s.addEventListener("pointerdown", (ev) => { drag = [ev.clientX, ev.clientY, mapView[0], mapView[1]]; moved = false; });
  s.addEventListener("mouseover", (ev) => { const g = ev.target.closest("[data-node-id]"); if (g) mapRoute(Number(g.dataset.nodeId)); });
  s.addEventListener("mouseleave", () => mapRoute(null));
  s.addEventListener("pointermove", (ev) => {
    if (!drag) return;
    const r = s.getBoundingClientRect(), k = mapView[2] / r.width;
    const dx = (ev.clientX - drag[0]) * k, dy = (ev.clientY - drag[1]) * k;
    if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
    mapView[0] = drag[2] - dx; mapView[1] = drag[3] - dy;
    s.setAttribute("viewBox", mapView.join(" "));
  });
  const end = () => { drag = null; };
  s.addEventListener("pointerup", end); s.addEventListener("pointerleave", end);
  s.addEventListener("click", (ev) => { if (moved) { ev.stopPropagation(); ev.preventDefault(); moved = false; } }, true);
}

// ---------------- pilota automatico ----------------
let es = null;
function autoStart() {
  if (es || busy) return;
  const days = Math.max(1, Math.min(60, parseInt($("#auto-giorni").value || "7", 10)));
  $("#auto-go").hidden = true; $("#auto-stop").hidden = false;
  addLog(`✧ Stato etereo per ${days} giorni…`, `auto ${days}`);
  busy = true;
  es = new EventSource("/api/auto?giorni=" + days);
  es.onmessage = async (ev) => {
    const d = JSON.parse(ev.data);
    if (d.log) addLog(d.log);
    if (d.fine) {
      es.close(); es = null; busy = false;
      $("#auto-go").hidden = false; $("#auto-stop").hidden = true;
      if (d.stop === "morto") return showDeath();
      if (d.riepilogo && d.riepilogo.giorni !== undefined) addCard(V.summary(d.riepilogo, d.stop));
      else if (d.stop) addLog(`⏸ Il pilota si ferma: ${d.stop}`);
      await refresh();
    } else if (d.giorno % 3 === 0) {
      refresh();
    }
  };
  es.onerror = () => { if (es) { es.close(); es = null; } busy = false; $("#auto-go").hidden = false; $("#auto-stop").hidden = true; refresh(); };
}
async function autoStop() { await api("/api/auto/stop", {}); }

function renderAutoCfg(s) {
  const sa = $("#showall"); if (sa) sa.checked = !!s.schede_tutte;
  const d = $("#diff");
  if (d && s.difficolta && document.activeElement !== d) d.value = s.difficolta;
  const c = s.auto || {};
  document.querySelectorAll("[data-auto]").forEach((el) => {
    const k = el.dataset.auto;
    if (el.type === "checkbox") el.checked = !!c[k];
    else if (c[k] !== undefined && document.activeElement !== el) el.value = c[k];
  });
}
async function autoSet(el) {
  const k = el.dataset.auto;
  const v = el.type === "checkbox" ? (el.checked ? "si" : "no") : el.value;
  await run(`auto imposta ${k} ${v}`);
}

// ---------------- creazione e rinascita ----------------
function openModal(html) { $("#modal").innerHTML = html; $("#overlay").hidden = false; }
function closeModal() { $("#overlay").hidden = true; $("#modal").innerHTML = ""; }

function choiceList(name, items, keyField, labelFn, checkedIdx = 0) {
  return items.map((it, i) => `<label class="opt"><input type="radio" name="${name}" value="${esc(it[keyField] ?? i)}" ${i === checkedIdx ? "checked" : ""}> ${labelFn(it)}</label>`).join("");
}
const val = (name) => (document.querySelector(`input[name="${name}"]:checked`) || {}).value;

async function showCreation() {
  const o = await api("/api/nuovo");
  openModal(`<h2>Una nuova vita</h2>
    <fieldset class="origins"><legend>Origine</legend>${choiceList("o", o.origini, "key", originLabel)}</fieldset>
    <fieldset><legend>Destino</legend>${choiceList("d", o.destini, "key", (x) => esc(x.label))}</fieldset>
    <fieldset><legend>Rivali</legend>${choiceList("r", o.rivali, "key", (x) => esc(x.label), 1)}</fieldset>
    ${o.difficolta ? `<fieldset><legend>Difficoltà</legend>${choiceList("df", o.difficolta, "key", (x) => esc(x.label), 1)}</fieldset>` : ""}
    <p><label>Nome <input id="nm" value="Viandante" maxlength="32"></label></p>
    <p><label><input type="checkbox" id="hc"> Modalità <b>Senza Ritorno</b>: la morte è definitiva, niente reincarnazione</label></p>
    <p><label><input type="checkbox" id="cb"> ✦ Affidati al Cielo: nasci con un <b>corpo leggendario</b> a caso (Caos Primordiale, Osso Supremo, Doppie Pupille, Vene Yin…)</label></p>
    <button class="primary" id="go-new">Comincia</button>`);
  $("#go-new").onclick = async () => {
    const origin = val("o");
    const r = await api("/api/nuovo", { origine: origin, destino: val("d"), rivali: val("r"), nome: $("#nm").value, senza_ritorno: $("#hc").checked, corpo: $("#cb").checked, difficolta: val("df") || "" });
    closeModal(); await showPrologue(origin, r.log); addLog(r.log); await refresh();
  };
}
function originLabel(x) {
  const u = imgOf(["prologo/" + x.key]);
  return `${u ? `<img class="orig-img" src="${u}" alt="" loading="lazy">` : ""}<span><b>${esc(x.name)}</b> — ${esc(x.desc)}</span>`;
}
// (Agg. 69) il PROLOGO ILLUSTRATO: il quadro della tua origine e il racconto, una pagina alla volta (Avanti / Spazio)
function showPrologue(origin, text) {
  const pages = [];
  let cur = [];
  for (const l of String(text || "").split("\n")) {
    if (!l.trim()) { if (cur.length) { pages.push(cur); cur = []; } continue; }
    cur.push(l);
    if (cur.length >= 5) { pages.push(cur); cur = []; }
  }
  if (cur.length) pages.push(cur);
  if (!pages.length) return Promise.resolve();
  const u = imgOf(["prologo/" + origin, "luoghi/mountain", "mondi/0"]);
  return new Promise((done) => {
    let i = 0;
    const box = document.createElement("div"); box.id = "prologue";
    document.body.appendChild(box);
    const end = () => { document.removeEventListener("keydown", key, true); box.remove(); done(); };
    const draw = () => {
      box.innerHTML = `<div class="pro-img"${u ? ` style="background-image:url('${u}')"` : ""}></div>
        <div class="pro-text"><div class="pro-page">${pages[i].map((l) => `<p>${actionize(esc(l))}</p>`).join("")}</div>
        <div class="pro-nav"><span class="muted small">${i + 1} / ${pages.length} · Spazio per continuare</span>
        <button class="link" data-pro="skip">salta</button><button class="primary" data-pro="next">${i + 1 < pages.length ? "Avanti ▸" : "Comincia"}</button></div></div>`;
    };
    const next = () => { i++; if (i >= pages.length) end(); else draw(); };
    const key = (ev) => { if (ev.key === " " || ev.key === "Enter" || ev.key === "ArrowRight") { ev.preventDefault(); ev.stopPropagation(); next(); }
      else if (ev.key === "Escape") { ev.preventDefault(); end(); } };
    box.addEventListener("click", (ev) => { const b = ev.target.closest("[data-pro]"); ev.stopPropagation(); if (!b) return; b.dataset.pro === "skip" ? end() : next(); });
    document.addEventListener("keydown", key, true);
    draw();
  });
}

async function showDeath() {
  const o = await api("/api/morte");
  if (o.salvato) { addLog(o.salvato); return refresh(); }
  if (o.senza_ritorno) {
    openModal(`<h2>La tua storia è finita</h2><pre>${esc(o.epilogo)}</pre>
      <p>☠ Senza Ritorno: non c'è reincarnazione. Il mondo andrà negli annali (resta salvato in archivio).</p>
      <button class="primary" id="go-world">Comincia un nuovo mondo</button>`);
    $("#go-world").onclick = async () => { const r = await api("/api/nuovo_mondo", {}); closeModal(); addLog(r.log); await refresh(); };
    return;
  }
  openModal(`<h2>La tua vita è finita</h2><pre>${esc(o.epilogo)}</pre>
    <p>Il mondo prosegue senza di te. Ma le anime, qui, non si spengono del tutto.</p>
    <fieldset><legend>Cosa porti con te (fino a ${o.frammenti} frammenti)</legend>${o.eredita.map((l, i) =>
      `<label class="opt"><input type="checkbox" name="e" value="${i}" ${i === 0 ? "checked" : ""}> ${esc(l)}</label>`).join("")}</fieldset>
    ${o.eredi && o.eredi.length ? `<fieldset><legend>Chi continua la tua Via</legend>
      <label class="opt"><input type="radio" name="er" value="" checked> Un'anima nuova (rinasci da capo, con i frammenti scelti)</label>
      ${o.eredi.map((h) => `<label class="opt"><input type="radio" name="er" value="${h.id}"> ☯ Continua come <b>${esc(h.label)}</b> — tutti i frammenti, il suo regno, il suo nome</label>`).join("")}</fieldset>` : ""}
    <fieldset class="origins"><legend>Origine</legend>${choiceList("o", o.origini, "key", originLabel)}</fieldset>
    <fieldset><legend>Destino</legend>${choiceList("d", o.destini, "key", (x) => esc(x.label))}</fieldset>
    <p><label>Nome <input id="nm" value="" placeholder="(lo stesso di prima)" maxlength="32"></label></p>
    <p><label><input type="checkbox" id="cb"> ✦ Affidati al Cielo: rinasci con un <b>corpo leggendario</b> a caso</label></p>
    <button class="primary" id="go-reb">Rinasci in questo mondo</button>`);
  $("#go-reb").onclick = async () => {
    const picks = [...document.querySelectorAll('input[name="e"]:checked')].map((x) => parseInt(x.value, 10)).slice(0, o.frammenti);
    const origin = val("o");
    const r = await api("/api/rinasci", { origine: origin, destino: val("d"), nome: $("#nm").value, eredita: picks.length ? picks : [o.eredita.length - 1], corpo: $("#cb").checked, erede: val("er") ? parseInt(val("er"), 10) : null });
    closeModal(); await showPrologue(origin, r.log); addLog(r.log); await refresh();
  };
}

// ---------------- eventi ----------------
document.addEventListener("click", async (ev) => {
  if (ev.target.id === "btn-reinc") {
    if (!confirm("Lasciare questa vita e rinascere, con i benefici del merito accumulato?")) return;
    const r = await api("/api/reincarnati", {}); addLog(r.log); return showDeath();
  }
  if (ev.target.id === "btn-restart") {
    if (!confirm("Ricominciare da zero? Il mondo attuale va in archivio (potrai ricaricarlo) e ne nasce uno nuovo.")) return;
    const r = await api("/api/nuovo_mondo", {}); addLog(r.log); $("#log").innerHTML = ""; addLog(r.log); return refresh();
  }
  if (ev.target.id === "cr-all") { allLives = !allLives; return loadTab("storia"); }
  const fl = ev.target.closest("[data-fill]");
  if (fl) { const c = $("#cmd"); c.value = fl.dataset.fill; c.focus(); return; }
  const sbt = ev.target.closest("[data-sub]");
  if (sbt) {
    const [t, k] = sbt.dataset.sub.split(":"); sub[t] = k;
    try { localStorage.setItem("ji_sub", JSON.stringify(sub)); } catch (e) { /* niente */ }
    return loadTab(t);
  }
  if (ev.target.id === "dao-all") { daoAll = !daoAll; return loadTab("personaggio"); }
  if (ev.target.closest("#widen")) { setWide(!document.body.classList.contains("wide")); return; }
  const alb = ev.target.closest("[data-album]");
  if (alb) { albumPage = alb.dataset.album; return loadTab("tesori:album"); }
  const cx = ev.target.closest("[data-codex-ok]");
  if (cx) { CODEX_SEEN[cx.dataset.codexOk] = 1; saveCodexSeen(); const card = cx.closest(".codex-card"); if (card) card.remove(); return; }
  if (ev.target.closest("#adv")) { advance(); return; }
  if (ev.target.closest("#adv-all")) { flushAll(); return; }
  if (ev.target.closest("#settings-btn")) { const pp = $("#settings-pop"); pp.hidden = !pp.hidden; settingsUi(); return; }
  if (!ev.target.closest("#settings-pop") && $("#settings-pop") && !$("#settings-pop").hidden) $("#settings-pop").hidden = true;
  if (ev.target.closest("#mgtoggle")) {
    MINIGAME = !MINIGAME; try { localStorage.setItem("ji_minigame", MINIGAME ? "1" : "0"); } catch (e) { /* niente */ }
    settingsUi(); return;
  }
  if (ev.target.closest("#fontsz")) {
    const order = [100, 112, 125, 90], cur = Number(document.documentElement.dataset.fs || 100);
    const nx = order[(order.indexOf(cur) + 1) % order.length]; applyFs(nx);
    try { localStorage.setItem("ji_fs", String(nx)); } catch (e) { /* niente */ }
    settingsUi(); return;
  }
  if (ev.target.closest("#contrast")) {
    const on = document.documentElement.dataset.contrast !== "1";
    if (on) document.documentElement.dataset.contrast = "1"; else delete document.documentElement.dataset.contrast;
    try { localStorage.setItem("ji_contrast", on ? "1" : "0"); } catch (e) { /* niente */ }
    settingsUi(); return;
  }
  if (ev.target.closest("#readmode")) {
    READ = manual() ? "auto" : "manuale"; try { localStorage.setItem("ji_read", READ); } catch (e) { /* niente */ }
    if (!manual()) { flushAll(); while ($("#toasts") && $("#toasts").firstElementChild) $("#toasts").firstElementChild.remove(); TOAST_Q.length = 0; }
    readBtn();
    return;
  }
  if (ev.target.closest("#music")) {
    MUSIC = !MUSIC; try { localStorage.setItem("ji_music", MUSIC ? "1" : "0"); } catch (e) { /* niente */ }
    settingsUi(); musicFor(S); return;
  }
  if (ev.target.closest("#sound")) {
    SOUND = !SOUND; try { localStorage.setItem("ji_sound", SOUND ? "1" : "0"); } catch (e) { /* niente */ }
    musicFor(S); settingsUi(); if (SOUND) sfx("info"); return;
  }
  if (ev.target.closest("#theme")) {
    const order = ["", "light", "dark"], cur = document.documentElement.dataset.theme || "";
    const nx = order[(order.indexOf(cur) + 1) % order.length];
    if (nx) document.documentElement.dataset.theme = nx; else delete document.documentElement.dataset.theme;
    try { localStorage.setItem("ji_theme", nx); } catch (e) { /* niente */ }
    settingsUi();
    return loadTab(tab);
  }
  const mt = ev.target.closest("[data-maptool]");
  if (mt) { mapTool(mt.dataset.maptool); return; }
  const bk = ev.target.closest("[data-book]");
  if (bk && BOOK) { bookCat = bk.dataset.book; $("#tabbody").innerHTML = V.book(BOOK, bookCat); return; }
  const gn = ev.target.closest("[data-node]");
  if (gn && GRAPH) { const box = $("#gnode-info"); if (box) box.innerHTML = V.nodeInfo(GRAPH, gn.dataset.node); return; }
  const lf = ev.target.closest("[data-logf]");
  if (lf) {
    logFilter = lf.dataset.logf;
    document.querySelectorAll("[data-logf]").forEach((b) => b.classList.toggle("on", b === lf));
    document.querySelectorAll("#log .ln").forEach((l) => { l.hidden = logFilter !== "tutto" && !l.classList.contains("cat-" + logFilter); });
    return;
  }
  const pa = ev.target.closest("[data-palace]");
  if (pa) { openPalace(pa.dataset.palace); return; }
  const pt = ev.target.closest("[data-ptab]");
  if (pt) { const [p, k] = pt.dataset.ptab.split(":"); openPalace(p, k); return; }
  if (ev.target.closest("#auto-go")) { autoStart(); return; }
  if (ev.target.closest("#auto-stop")) { autoStop(); return; }
  const t = ev.target.closest("[data-cmd]");
  if (t) { ev.preventDefault(); run(t.dataset.cmd); return; }
  const tb = ev.target.closest("[data-tab]");
  if (tb) loadTab(tb.dataset.tab);
  const mb = ev.target.closest("[data-menu]");
  if (mb) loadTab("m:" + (mb.dataset.menu === "via" ? "via:" + lastVia : mb.dataset.menu));
});
document.addEventListener("change", async (ev) => {
  if (ev.target.id === "imp-file" && ev.target.files && ev.target.files[0]) {       // (Agg. 72) importa una partita
    const f = ev.target.files[0];
    const buf = new Uint8Array(await f.arrayBuffer());
    let bin = ""; for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    const r = await api("/api/importa", { dati: btoa(bin) });
    addLog(r.log, null, true);
    if (r.ok) { setTimeout(() => location.reload(), 900); }
    return;
  }
  if (ev.target.matches("[data-auto]")) autoSet(ev.target);
  if (ev.target.id === "showall") run(ev.target.checked ? "schede tutte" : "schede graduali");
  if (ev.target.id === "diff") run(`difficolta ${ev.target.value}`);
});
$("#cmdform").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const v = $("#cmd").value;
  if (!v.trim()) { advance(); return; }               // Invio a casella vuota = Avanti
  if (v.trim()) { history.push(v); hpos = history.length; }
  $("#cmd").value = "";
  run(v);
});
$("#cmd").addEventListener("keydown", (ev) => {
  if (ev.key === "ArrowUp" && hpos > 0) { hpos--; $("#cmd").value = history[hpos]; ev.preventDefault(); }
  if (ev.key === "ArrowDown") { hpos = Math.min(history.length, hpos + 1); $("#cmd").value = history[hpos] || ""; ev.preventDefault(); }
});
document.addEventListener("keydown", (ev) => {
  // Spazio (fuori dalla casella dei comandi) o freccia destra: Avanti
  const typing = document.activeElement && ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName);
  if ((ev.key === " " && !typing) || (ev.key === "ArrowRight" && (!typing || !$("#cmd").value))) {
    if (advance()) { ev.preventDefault(); return; }
  }
  if (ev.key === "Escape" && (PENDING.length || CUT_NEXT)) { flushAll(); if (CUT_NEXT) { CUT_NEXT = null; document.querySelectorAll(".cutin").forEach((x) => x.remove()); } return; }
  // numeri 1-9 con la casella vuota: scelta della scena o azione suggerita
  if (document.activeElement === $("#cmd") && $("#cmd").value) return;
  if (document.activeElement && ["INPUT", "SELECT"].includes(document.activeElement.tagName) && document.activeElement !== $("#cmd")) return;
  if (/^[1-9]$/.test(ev.key) && S) {
    const n = parseInt(ev.key, 10);
    const cards = S.duello && S.duello.arena && !S.duello.arena.finito ? S.duello.arena.carte : null;
    if (cards) { const c = cards[n - 1]; if (c && c.ok) { ev.preventDefault(); run(c.cmd); } }
    else if (S.scena) { if (n <= S.scena.choices.length) { ev.preventDefault(); run(String(n)); } }
    else if (n <= (S.suggVisibili || S.suggerimenti).length) { ev.preventDefault(); run((S.suggVisibili || S.suggerimenti)[n - 1].cmd); }
  }
});
function setWide(on) {
  document.body.classList.toggle("wide", on);
  settingsUi();
  try { localStorage.setItem("ji_wide", on ? "1" : "0"); } catch (e) { /* niente */ }
  if (tab === "mappa") loadMap();
}
try { if (localStorage.getItem("ji_wide") === "1") document.body.classList.add("wide"); } catch (e) { /* niente */ }
// (Agg. 72) il menu ⚙ Impostazioni: ogni voce dice cosa fa e com'è impostata adesso
function settingsUi() {
  const set = (id, v) => { const e = $("#" + id + " em"); if (e) e.textContent = v; };
  const th = document.documentElement.dataset.theme || "";
  set("fontsz", (document.documentElement.dataset.fs || "100") + "%");
  set("contrast", document.documentElement.dataset.contrast === "1" ? "sì" : "no");
  set("readmode", manual() ? "al tuo ritmo" : "automatica");
  set("music", MUSIC ? "sì" : "no"); set("sound", SOUND ? "sì" : "no"); set("mgtoggle", MINIGAME ? "sì" : "no");
  set("theme", th === "dark" ? "scuro" : th === "light" ? "chiaro" : "automatico");
  set("widen", document.body.classList.contains("wide") ? "sì" : "no");
}
settingsUi();
// (Agg. 70) grandezza del testo e alto contrasto, ricordati nel browser
function applyFs(v) { document.documentElement.dataset.fs = String(v); document.body.style.zoom = v === 100 ? "" : String(v / 100); }
try { const fs = Number(localStorage.getItem("ji_fs") || 100); if (fs !== 100) applyFs(fs); if (localStorage.getItem("ji_contrast") === "1") document.documentElement.dataset.contrast = "1"; } catch (e) { /* niente */ }
function readBtn() { settingsUi(); advUi(); }
readBtn();

(async () => {
  try {
    const s = await api("/api/stato");
    if (s.fase === "gioco") { const r = await api("/api/intro", {}); addLog(r.log, null, true); }
    await refresh();
    openPalace(palace);
  } catch (e) { addLog("⚠ Non riesco a parlare con il gioco: " + e.message); }
})();
