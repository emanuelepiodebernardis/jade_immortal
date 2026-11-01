// Jade Immortal — IL NARRATORE E LE VOCI DEI PERSONAGGI (Aggiornamento 76).
// Usa la sintesi vocale del browser (le voci italiane installate nel sistema: tutto in locale).
// Da una o due voci di base (una maschile, una femminile) ricava un'intera compagnia, giocando con tono e
// velocità: il narratore, gli uomini, le donne, i vecchi, i demoni (più profondi), i mostri, i draghi
// (profondissimi e lenti), gli spiriti e le creature eteree (alti e leggeri). Le battute tra «…» le dice
// chi parla; il resto lo racconta il narratore. La velocità si regola; ogni riga si può saltare.
"use strict";
(function () {
  const SS = window.speechSynthesis;
  const K = { on: "ji_narr", rate: "ji_narr_rate" };
  const store = { get: (k, d) => { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* niente */ } } };
  let ON = store.get(K.on, "0") === "1";
  let RATE = Number(store.get(K.rate, "1")) || 1;
  const Q = [];                 // [{text, prof}]
  let speaking = false, last = [], onIdle = null;

  // ---------------------------------------------------------------- le voci
  let VOICES = { m: null, f: null, any: null };
  function pickVoices() {
    if (!SS) return;
    const all = SS.getVoices().filter((v) => /^it(-|_|$)/i.test(v.lang));
    const pool = all.length ? all : SS.getVoices();
    const FEM = /(elsa|isabella|alice|federica|paola|silvia|lucia|carla|giulia|bianca|chiara|female|donna|google italiano)/i;
    const MAS = /(cosimo|diego|luca|giorgio|roberto|marco|paolo|giuseppe|male|uomo)/i;
    VOICES = { m: pool.find((v) => MAS.test(v.name)) || null, f: pool.find((v) => FEM.test(v.name)) || null, any: pool[0] || null };
  }
  if (SS) { pickVoices(); SS.onvoiceschanged = pickVoices; }

  // tono (pitch 0–2) e velocità relativa; "g" = genere della voce di base
  const PROF = {
    narratore: { g: "m", p: 0.95, r: 0.97 }, uomo: { g: "m", p: 1.0, r: 1.02 }, donna: { g: "f", p: 1.12, r: 1.03 },
    vecchio: { g: "m", p: 0.72, r: 0.86 }, vecchia: { g: "f", p: 0.82, r: 0.88 },
    demone: { g: "m", p: 0.35, r: 0.84 }, demonessa: { g: "f", p: 0.62, r: 0.9 },
    mostro: { g: "m", p: 0.1, r: 0.72 }, drago: { g: "m", p: 0.02, r: 0.76 },
    spirito: { g: "f", p: 1.65, r: 1.08 }, spirito_m: { g: "m", p: 1.45, r: 1.06 },
    eroe: { g: "m", p: 1.04, r: 1.03 }, eroina: { g: "f", p: 1.08, r: 1.03 },
  };

  // ---------------------------------------------------------------- chi parla
  function people() {
    const S = window.S || {};
    const out = [];
    for (const p of S.presenti || []) out.push(p);
    const d = S.duello && S.duello.arena;
    if (d) out.push({ name: d.nome, kind: d.lui && d.lui.kind, f: d.lui && d.lui.f, arch: d.lui && d.lui.arch });
    return out;
  }
  function heroProf() {
    const S = window.S || {};
    return /eroe_?f/.test(S.ritratto || "") ? "eroina" : "eroe";
  }
  function profOf(p) {
    if (!p) return null;
    const name = String(p.name || "").toLowerCase();
    const kind = p.kind || "human";
    if (/drag|loong|wyrm/.test(name)) return "drago";
    if (kind === "demon") return p.f ? "demonessa" : "demone";
    if (kind === "beast" || kind === "monster" || kind === "creature") return "mostro";
    if (kind === "spirit" || kind === "ghost") return p.f ? "spirito" : "spirito_m";
    if (/anzian|patriarc|eremit|vecch/.test(String(p.arch || ""))) return p.f ? "vecchia" : "vecchio";
    return p.f ? "donna" : "uomo";
  }
  function speakerOf(before, after) {
    const S = window.S || {};
    const list = people();
    const near = (before.slice(-60) + " " + after.slice(0, 50)).toLowerCase();
    if (S.nome && near.includes(String(S.nome).toLowerCase().split(" ")[0])) return heroProf();
    for (const p of list) {
      const first = String(p.name).toLowerCase().split(" ")[0];
      if (first.length > 1 && near.includes(first)) return profOf(p);
    }
    if (/\b(rispondi|dici|gridi|sussurri)\b/.test(near)) return heroProf();
    if (/\b(lei|ragazza|donna|vecchia|madre|sorella|principessa|spadaccina)\b/.test(near)) return "donna";
    if (/\b(demone|diavolo)\b/.test(near)) return "demone";
    if (/\b(drago)\b/.test(near)) return "drago";
    if (/\b(bestia|mostro|lupo|tigre)\b/.test(near)) return "mostro";
    if (/\b(spirito|fantasma|anima)\b/.test(near)) return "spirito";
    if (/\b(vecchio|anziano|maestro|patriarca)\b/.test(near)) return "vecchio";
    return "uomo";
  }

  // ---------------------------------------------------------------- testo → battute
  function clean(s) {
    return String(s || "")
      .replace(/\([^)]*'[^)]*'\)/g, "")                          // («scrivi 'duello X'»)
      .replace(/'[a-z_]+( [^']*)?'/gi, "")                        // i comandi tra apici
      .replace(/[█▓▒░·•►▸◂▶◀✦✧★☆♛⚔⚡☯✺✿⛩⇑↑↓→←═─—|_*#>]+/g, " ")
      .replace(/\p{Extended_Pictographic}/gu, " ")
      .replace(/\s+/g, " ").trim();
  }
  const SKIP = /^\s*(\[\d+\]|Turno \d|Qi \d|Tick \d|Uscite:|Presenti:|\(scrivi|Allenamento \d|Sei sfinito)/;
  function parts(line) {
    if (SKIP.test(line)) return [];
    const out = [];
    const re = /«([^»]+)»/g;
    let m, pos = 0;
    while ((m = re.exec(line))) {
      const before = line.slice(pos, m.index), after = line.slice(m.index + m[0].length);
      if (clean(before)) out.push({ text: clean(before), prof: "narratore" });
      out.push({ text: clean(m[1]), prof: speakerOf(line.slice(0, m.index), after) });
      pos = m.index + m[0].length;
    }
    const tail = clean(line.slice(pos));
    if (tail) out.push({ text: tail, prof: "narratore" });
    return out.filter((x) => x.text.length > 1);
  }

  // ---------------------------------------------------------------- (Agg. 83) le voci vere: Piper, in locale
  // Se il gioco ha la cartella «voci» (strumenti/installa_voci.py), le battute le dice Piper: voce maschile e femminile
  // di qualità; demoni, draghi e spiriti si ottengono abbassando o alzando il tono (senza preservare l'altezza).
  let PIPER = false, PIPER_G = {}, AUDIO = null;
  try { fetch("/api/tts/stato").then((r) => r.json()).then((j) => { PIPER = !!(j && j.attivo); PIPER_G = (j && j.voci) || {}; }).catch(() => {}); } catch (e) { /* niente */ }
  function nextPiper(it, P) {
    fetch("/api/tts", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ testo: it.text, genere: P.g, velocita: P.r * RATE }) })
      .then((r) => (r.status === 200 ? r.blob() : null))
      .then((b) => {
        if (!b || !speaking) { if (!b) { PIPER = false; Q.unshift(it); speaking = false; next(); } return; }
        AUDIO = new Audio(URL.createObjectURL(b));
        AUDIO.preservesPitch = false; AUDIO.mozPreservesPitch = false; AUDIO.webkitPreservesPitch = false;
        AUDIO.playbackRate = Math.max(0.75, Math.min(1.25, 1 + (P.p - 1) * 0.18));
        AUDIO.onended = AUDIO.onerror = () => { const u = AUDIO && AUDIO.src; AUDIO = null; if (u) URL.revokeObjectURL(u); next(); };
        AUDIO.play().catch(() => { AUDIO = null; next(); });
      })
      .catch(() => { PIPER = false; Q.unshift(it); speaking = false; next(); });
  }

  // ---------------------------------------------------------------- la coda
  function next() {
    if (!SS && !PIPER) return;
    const it = Q.shift();
    if (!it) { speaking = false; if (onIdle) { const f = onIdle; setTimeout(() => { if (!speaking && !Q.length) f(); }, 350); } return; }
    speaking = true;
    const P = PROF[it.prof] || PROF.narratore;
    if (PIPER && PIPER_G[P.g]) { nextPiper(it, P); return; }       // le voci che Piper ha; le altre dal browser
    if (!SS) { next(); return; }
    const u = new SpeechSynthesisUtterance(it.text);
    u.lang = "it-IT";
    const v = (P.g === "f" ? VOICES.f : VOICES.m) || VOICES.any;
    if (v) u.voice = v;
    // con una sola voce di base, il genere lo fa il tono
    const oneVoice = !(VOICES.f && VOICES.m);
    u.pitch = Math.max(0, Math.min(2, P.p + (oneVoice && P.g === "f" ? 0.25 : 0)));
    u.rate = Math.max(0.5, Math.min(2.5, P.r * RATE));
    u.onend = u.onerror = () => next();
    SS.speak(u);
  }
  function enqueue(list) {
    if (!ON || (!SS && !PIPER) || !list.length) return;
    Q.push(...list);
    if (!speaking) next();
  }

  window.Narrator = {
    on: () => ON,
    setOn(v) {
      ON = !!v; store.set(K.on, ON ? "1" : "0");
      if (!ON) this.stop(); else this.say("Il narratore ti accompagna.", "narratore");
    },
    rate: () => RATE,
    setRate(r) { RATE = Math.max(0.6, Math.min(1.8, Number(r) || 1)); store.set(K.rate, String(RATE)); },
    /** legge un pezzo di registro (testo con a capo) */
    feed(text) {
      if (!ON) return;
      const lines = String(text || "").split("\n");
      const list = [];
      for (const l of lines) list.push(...parts(l));
      if (list.length) last = list.slice();
      enqueue(list);
    },
    /** legge delle righe del registro (elementi), per la lettura al proprio ritmo */
    feedEls(els) { this.feed((els || []).map((e) => e.textContent).join("\n")); },
    say(text, prof) { enqueue([{ text: clean(text), prof: prof || "narratore" }]); },
    skip() { if (AUDIO) { AUDIO.pause(); const f = AUDIO.onended; AUDIO.onended = null; if (f) f(); return; } if (SS && speaking) SS.cancel(); },               // salta la riga (la coda prosegue)
    stop() { Q.length = 0; if (AUDIO) { AUDIO.onended = null; AUDIO.pause(); AUDIO = null; } if (SS) SS.cancel(); speaking = false; },
    repeat() { if (last.length) { this.stop(); enqueue(last.slice()); } },
    busy: () => speaking || Q.length > 0,
    /** chiamata quando ha finito di leggere tutto (per far avanzare la lettura al proprio ritmo) */
    onIdle(f) { onIdle = f; },
    available: () => !!SS || PIPER,
    piper: () => PIPER,
    voices: () => ({ maschile: VOICES.m && VOICES.m.name, femminile: VOICES.f && VOICES.f.name }),
    _parts: parts,
  };
})();
