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
function addLog(text, cmd) {
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
  box.scrollTop = box.scrollHeight;
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
function sfx(kind) {
  if (!SOUND) return;
  try {
    AC = AC || new (window.AudioContext || window.webkitAudioContext)();
    const notes = { good: [523, 659, 784], rare: [659, 784, 988, 1319], bad: [220, 185], warn: [440, 392], info: [587, 740],
      hit: [196], crit: [147, 294], coin: [988, 1319] }[kind] || [440];
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
function toast(head, body, tone) {
  sfx(tone || "info");
  const box = $("#toasts");
  if (!box) return;
  const d = document.createElement("div");
  d.className = "toast " + (tone || "");
  d.innerHTML = `<b>[ ${esc(head)} ]</b><div>${esc(body.length > 180 ? body.slice(0, 177) + "…" : body)}</div>`;
  box.appendChild(d);
  setTimeout(() => d.classList.add("out"), 5200);
  setTimeout(() => d.remove(), 5800);
  while (box.children.length > 4) box.removeChild(box.firstChild);
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
  "dominio", "razze", "profondi", "spiriti", "attributi", "mercato", "asta", "ricette", "bacheca", "menu"];
// i comandi che mostrano una lista da cui scegliere si aprono come menu cliccabili
const AS_MENU = { market: "mercato", shop: "mercato", negozio: "mercato", aste: "asta", auction: "asta", recipes: "ricette",
  invitations: "bacheca", inviti: "bacheca", missioni: "bacheca", missions: "bacheca", techniques: "tecniche", skills: "tecniche" };
async function run(cmd) {
  cmd = (cmd || "").trim();
  if (!cmd || busy) return;
  if (MENUS.includes(cmd.toLowerCase())) return loadTab("m:" + cmd.toLowerCase());   // i menu si aprono nel pannello
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
  auction: "asta", recipes: "ricette", missioni: "bacheca", inviti: "bacheca", invitations: "bacheca", save: "salva" };
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
    const regions = ["#actions", "#place", "#scene", "#tabbody", "#sugg"];
    for (const r of regions) {
      const root = $(r); if (!root) continue;
      root.querySelectorAll("button[data-cmd], button[data-menu]").forEach((el) => {
        if (el.closest(".attr") || el.closest(".choices")) return;          // +1 attributi e scelte delle scene: sempre
        const k = actKey(el);
        el.classList.remove("dup");
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
  renderTop(s); renderPlace(s); renderScene(s); renderSugg(s); renderAutoCfg(s);
  if (tab === "mete") renderMete(s);
  else if (tab === "mappa" || tab === "persone" || tab === "personaggio" || tab.startsWith("m:")) loadTab(tab);
}

function setBar(id, pct) { $(id).style.width = Math.max(0, Math.min(100, pct)) + "%"; }

function renderTop(s) {
  $("#t-nome").textContent = s.nome;
  $("#t-regno").textContent = s.regno;
  $("#t-lv").textContent = "Lv " + (s.livello ?? "—");
  const pts = $("#t-punti");
  pts.hidden = !s.punti; pts.textContent = `✦ ${s.punti} punti`;
  const q = s.rapidi || {};
  $("#q-spiriti").hidden = !q.spiriti; $("#q-trib").hidden = !q.tribulation;
  $("#q-sfonda").classList.toggle("ready", !!q.breakthrough);
  $("#q-sonno").classList.toggle("ready", !!q.sonno);
  $("#q-tempra").disabled = q.tempra === false;
  $("#q-raccogli").textContent = q.raccogli ? `✋ Raccogli (${q.raccogli})` : "✋ Raccogli";
  $("#q-raccogli").classList.toggle("ready", !!q.raccogli);
  const nb = $("#nav-punti"); nb.hidden = !s.punti; nb.textContent = s.punti || "";
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
function arenaHtml(a, s) {
  const pct = (c, m) => Math.max(0, Math.min(100, Math.round(100 * c / Math.max(1, m))));
  const L = a.ultimo || {};
  const pop = (v, cls) => v ? `<span class="pop ${cls}">−${Number(v).toLocaleString("it-IT")}</span>` : "";
  const txt = s.scena.text.split("\n").filter((l) => l.trim() && !l.includes("█") && !l.includes("·····") && !/^Turno \d/.test(l) && !/^Qi \d/.test(l));
  const me = `<div class="fighter me">${face(a.tu.nome, 72, "--accent", "io")}
      <div class="fi"><b>${esc(a.tu.nome)}</b><div class="muted small">${esc(a.tu.regno)}</div>
      <div class="hpbar"><i style="width:${pct(a.tu.hp, a.tu.max)}%"></i><span>${a.tu.hp.toLocaleString("it-IT")} / ${a.tu.max.toLocaleString("it-IT")}</span></div>
      <div class="mini"><div class="bar qi"><i style="width:${pct(a.tu.qi[0], a.tu.qi[1])}%"></i></div><small>Qi ${a.tu.qi[0]}</small>
        <div class="bar sp"><i style="width:${pct(a.tu.spirito[0], a.tu.spirito[1])}%"></i></div><small>Spirito ${a.tu.spirito[0]}</small></div>
      ${a.concentrato ? `<span class="tag rare">☯ concentrato</span>` : ""}</div>${pop(L.subito, "bad" + (L.critico_lui ? " crit" : ""))}</div>`;
  const foe = `<div class="fighter foe">${face(a.nome, 72, "--bad", "", { arch: a.lui.arch, kind: a.lui.kind, f: a.lui.f })}
      <div class="fi"><b>${esc(a.nome)}</b><div class="muted small">${esc(a.lui.regno)} · ${esc(a.lui.forza)}</div>
      <div class="hpbar foe"><i style="width:${pct(a.lui.hp, a.lui.max)}%"></i><span>${a.lui.hp.toLocaleString("it-IT")} / ${a.lui.max.toLocaleString("it-IT")}</span></div>
      <span class="tag" title="${esc(a.stile_desc)}">${esc(a.stile)}</span>
      ${a.vantaggio > 1 ? `<span class="tag good">☸ elemento a tuo favore</span>` : a.vantaggio < 1 ? `<span class="tag bad">☸ elemento a suo favore</span>` : ""}
      ${a.carica ? `<span class="tag bad blink">⚠ carica un colpo pesante</span>` : ""}</div>${pop(L.inflitto, "good" + (L.critico ? " crit" : ""))}</div>`;
  const allies = a.alleati.length ? `<details class="allies-box"><summary>${a.alleati.length} alleat${a.alleati.length === 1 ? "o" : "i"} in campo</summary><div class="allies">${a.alleati.map((x) => `<span>${esc(x)}</span>`).join("")}</div></details>` : "";
  const cards = a.carte.map((c, i) => `<button class="card-act k-${esc(c.kind)} ${c.hot ? "hot" : ""}" ${c.ok ? `data-cmd="${esc(c.cmd)}"` : "disabled"} title="${esc(c.desc)}${c.why ? " — " + esc(c.why) : ""}">
      <span class="ci">${esc(c.icon)}${i < 9 ? `<kbd>${i + 1}</kbd>` : ""}</span><b>${esc(c.name)}</b><small>${esc(c.desc)}</small>
      <em>${c.ok ? esc(c.cost) : esc(c.why)}</em></button>`).join("");
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
const BEAST_WORDS = ["drago", "fenice", "tigre", "tartaruga", "qilin", "gru", "volpe", "serpente", "kun"];
function faceSrc(name, o = {}) {
  let u = slotImg("", name) || slotImg("ritratti", name);
  if (u) return u;
  if (o.io) return slotImg("ritratti", "eroe");
  if (o.kind && o.kind !== "human") {
    const low = String(name).toLowerCase(), w = BEAST_WORDS.find((x) => low.includes(x));
    return (w && slotImg("bestie", w)) || slotImg("creature", o.kind);
  }
  if (o.f) return slotImg("ritratti", o.arch === "anziano" || o.arch === "patriarca" ? "f_anziana" : "f") || slotImg("ritratti", o.arch);
  return o.arch ? slotImg("ritratti", o.arch) : null;
}
function face(name, size, aura, kind = "", o = {}) {
  const u = faceSrc(name, Object.assign({ io: kind === "io" }, o));
  return u ? `<img class="portrait" src="${u}" width="${size}" height="${size}" alt="" loading="lazy">` : V.portrait(name, kind, size, aura);
}
let lastArenaTurn = null;
function renderScene(s) {
  const box = $("#scene");
  // con una scena aperta la colonna centrale fa spazio: luogo e diario si stringono, la scena si allarga
  document.body.classList.toggle("scene-on", !!s.scena);
  document.body.classList.toggle("duel-on", !!(s.scena && s.duello));
  if (!s.scena) { box.hidden = true; box.innerHTML = ""; box.classList.remove("in-duel"); return; }
  box.hidden = false;
  const ar = s.duello && s.duello.arena;
  box.classList.toggle("in-duel", !!ar);
  if (ar && ar.ultimo && ar.turno !== lastArenaTurn) { lastArenaTurn = ar.turno; if (ar.ultimo.inflitto) sfx(ar.ultimo.critico ? "crit" : "hit"); }
  if (ar && !ar.finito) { box.innerHTML = arenaHtml(ar, s); return; }
  if (ar && ar.finito) {
    box.innerHTML = arenaHtml(ar, s) + `<div class="choices">` + s.scena.choices.map((c) => `<button data-cmd="${c.n}"><b>${c.n}.</b> ${esc(c.label)}</button>`).join("") + `</div>`;
    return;
  }
  const du = s.duello ? `<div class="duel"><div><span>Tu</span><div class="bar hp"><i style="width:${s.duello.tu.pct}%"></i></div><em>${s.duello.tu.cur}/${s.duello.tu.max}</em></div>
    <div><span>${esc(s.duello.nome)}</span><div class="bar hp foe"><i style="width:${s.duello.lui.pct}%"></i></div><em>${s.duello.lui.cur}/${s.duello.lui.max}</em></div>
    <div class="muted">Stile: ${esc(s.duello.stile)}${s.duello.vantaggio > 1 ? " · ☸ elemento a tuo favore (+25%)" : s.duello.vantaggio < 1 ? " · ☸ elemento a suo favore (−15%)" : ""}</div>
    ${s.duello.carica ? `<div class="l-warn">⚠ Sta raccogliendo il qi: difenditi! (attento alle finte dei subdoli)</div>` : ""}</div>` : "";
  // nel duello le barre grafiche sostituiscono quelle di testo del terminale
  const txt = s.duello ? s.scena.text.split("\n").filter((l) => !l.includes("█") && !l.includes("·····") && !l.startsWith("⚠")).join("\n") : s.scena.text;
  box.innerHTML = `<h3>✦ ${esc(s.scena.title)}</h3>${du}<p>${actionize(esc(txt))}</p><div class="choices">` +
    s.scena.choices.map((c) => `<button data-cmd="${c.n}"><b>${c.n}.</b> ${esc(c.label)}${c.hint ? `<small>[${esc(c.hint)}]</small>` : ""}</button>`).join("") +
    `</div>`;
}

function renderSugg(s) {
  // niente doppioni: via le azioni che hanno già un pulsante fisso a sinistra o una tessera del luogo
  const fixed = new Set([...document.querySelectorAll("#actions [data-cmd], #actions [data-menu], #place [data-cmd]")]
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
  personaggio: [["stato", "🪟 Stato"], ["dao", "☸ Dao"], ["radici", "🌱 Radici e talento"], ["corpo", "🩸 Corpo e sangue"], ["crescita", "📈 Crescita"], ["dettagli", "📄 Schede"]],
  tesori: [["zaino", "🎒 Zaino"], ["libro", "📖 Libro"]],
  storia: [["cronaca", "📜 Cronaca"], ["trama", "✦ Trama"], ["mondo", "🌍 Mondo"]],
};
const sub = { personaggio: "stato", tesori: "zaino", storia: "cronaca" };
try { const j = JSON.parse(localStorage.getItem("ji_sub") || "{}"); Object.assign(sub, j); } catch (e) { /* niente */ }
function subChips(name) {
  return `<div class="subtabs">` + SUBTABS[name].map(([k, l]) => `<button class="chip ${sub[name] === k ? "on" : ""}" data-sub="${name}:${k}">${l}</button>`).join("") + `</div>`;
}
async function loadTab(name) {
  const keep = tab === name;
  tab = name;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll("[data-menu]").forEach((b) => b.classList.toggle("on", "m:" + b.dataset.menu === name));
  const b = $("#tabbody");
  if (name.startsWith("m:")) {
    if (!keep) b.innerHTML = `<div class="empty">Carico…</div>`;
    try { const top = b.scrollTop; b.innerHTML = menuHtml(await api("/api/menu/" + name.slice(2))); if (keep) b.scrollTop = top; }
    catch (e) { b.innerHTML = `<div class="empty">Errore: ${esc(e.message)}</div>`; }
    return;
  }
  if (name === "mete") { if (S) renderMete(S); return; }
  if (name === "mappa") return loadMap();
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
      else h += `<div class="tools"><button class="primary" data-cmd="tesori cura">✧ Cura tutti i tesori</button></div>` + await bagHtml() + await texts("tesori");
    } else if (name === "storia") {
      h = subChips("storia");
      if (sub.storia === "mondo") h += await worldHtml() + await texts("mondo");
      else if (sub.storia === "trama") h += await texts("storia", "trama");
      else h += await chronicleHtml();
    } else if (name === "aiuto") h = await gameHtml() + V.legend() + await texts("aiuto");
    b.innerHTML = h;
    if (keep) b.scrollTop = top;
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
  let h = `<div class="card sec msec${full ? "" : " mini"}"><b>${s.icon ? esc(s.icon) + " " : ""}${esc(s.title)}</b>`;
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
  let h = `<div class="card menuhead"><h3>${esc(m.title)}</h3>${m.sub.map((s) => `<div class="muted">${esc(s)}</div>`).join("")}</div>`;
  m.sections.slice(0, MENU_FULL).forEach((s) => { h += msecHtml(s, true); });
  const rest = m.sections.slice(MENU_FULL);
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
  const it = await api("/api/zaino");
  if (!it.length) return `<div class="card"><b>Zaino</b><div class="empty">Vuoto.</div></div>`;
  return `<div class="card"><b>Zaino</b>` + it.map((x) =>
    `<div class="item r-${esc(x.rarita)}" title="${esc(x.desc)}"><span>${esc(x.nome)}${x.n > 1 ? ` ×${x.n}` : ""}</span>
     <span class="muted">${esc(x.tipo)} · ${esc(x.rarita.replace("_", " "))}</span>
     ${x.tipo === "essenza" ? `<button data-cmd="use tutte ${esc(x.nome)}">Assorbi${x.n > 1 ? " tutte" : ""}</button>`
       : `<button data-cmd="use ${esc(x.nome)}">Usa</button>${x.n > 1 ? `<button data-cmd="use tutte ${esc(x.nome)}">Tutte</button>` : ""}`}</div>`).join("") +
    `<div class="tools"><button class="primary" data-cmd="raccogli">Raccogli e assorbi tutto</button>` +
    `<button data-cmd="use all">Usa anche le pillole</button>` +
    `<button data-cmd="autoraccolta">Raccolta automatica on/off</button>` +
    `<button data-cmd="autoassorbi">Assorbimento automatico on/off</button></div></div>`;
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
  let h = `<div class="card"><b>Salvataggi</b> <span class="muted">— automatici ogni 5 giorni (auto_1, auto_2, auto_3 a rotazione)</span>
    <div class="tools" style="margin-top:6px"><button class="primary" data-cmd="salva">💾 Salva ora</button></div>` +
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
    <defs><radialGradient id="glow"><stop offset="0" stop-color="var(--accent)" stop-opacity=".55"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></radialGradient></defs>`;
  for (const [a, b] of m.edges) {
    const A = byId[a], B = byId[b];
    svg += `<line data-e="${Math.min(a, b)}-${Math.max(a, b)}" x1="${px(A) + NW / 2}" y1="${py(A) + NH / 2}" x2="${px(B) + NW / 2}" y2="${py(B) + NH / 2}"/>`;
  }
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
      <text class="ic" x="${x + 6}" y="${y + 17}">${n.here ? "◉" : ic}</text>
      <text class="nm" x="${x + 6}" y="${y + 34}">${esc(short)}</text>`;
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
  document.querySelectorAll("#mapsvg line.route").forEach((l) => l.classList.remove("route"));
  document.querySelectorAll("#mapsvg .node.onroute").forEach((g) => g.classList.remove("onroute"));
  if (!MAP || target == null) return;
  const me = MAP.nodes.find((n) => n.here); if (!me) return;
  const adj = {};
  for (const [a, b] of MAP.edges) { (adj[a] = adj[a] || []).push(b); (adj[b] = adj[b] || []).push(a); }
  const prev = { [me.id]: null }, q = [me.id];
  while (q.length) { const c = q.shift(); if (c === target) break; for (const n of adj[c] || []) if (!(n in prev)) { prev[n] = c; q.push(n); } }
  if (!(target in prev)) return;
  for (let c = target; prev[c] != null; c = prev[c]) {
    const p = prev[c], l = document.querySelector(`#mapsvg line[data-e="${Math.min(c, p)}-${Math.max(c, p)}"]`);
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
    <fieldset><legend>Origine</legend>${choiceList("o", o.origini, "key", (x) => `<b>${esc(x.name)}</b> — ${esc(x.desc)}`)}</fieldset>
    <fieldset><legend>Destino</legend>${choiceList("d", o.destini, "key", (x) => esc(x.label))}</fieldset>
    <fieldset><legend>Rivali</legend>${choiceList("r", o.rivali, "key", (x) => esc(x.label), 1)}</fieldset>
    <p><label>Nome <input id="nm" value="Viandante" maxlength="32"></label></p>
    <p><label><input type="checkbox" id="hc"> Modalità <b>Senza Ritorno</b>: la morte è definitiva, niente reincarnazione</label></p>
    <p><label><input type="checkbox" id="cb"> ✦ Affidati al Cielo: nasci con un <b>corpo leggendario</b> a caso (Caos Primordiale, Osso Supremo, Doppie Pupille, Vene Yin…)</label></p>
    <button class="primary" id="go-new">Comincia</button>`);
  $("#go-new").onclick = async () => {
    const r = await api("/api/nuovo", { origine: val("o"), destino: val("d"), rivali: val("r"), nome: $("#nm").value, senza_ritorno: $("#hc").checked, corpo: $("#cb").checked });
    closeModal(); addLog(r.log); await refresh();
  };
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
    <fieldset><legend>Origine</legend>${choiceList("o", o.origini, "key", (x) => `<b>${esc(x.name)}</b> — ${esc(x.desc)}`)}</fieldset>
    <fieldset><legend>Destino</legend>${choiceList("d", o.destini, "key", (x) => esc(x.label))}</fieldset>
    <p><label>Nome <input id="nm" value="" placeholder="(lo stesso di prima)" maxlength="32"></label></p>
    <p><label><input type="checkbox" id="cb"> ✦ Affidati al Cielo: rinasci con un <b>corpo leggendario</b> a caso</label></p>
    <button class="primary" id="go-reb">Rinasci in questo mondo</button>`);
  $("#go-reb").onclick = async () => {
    const picks = [...document.querySelectorAll('input[name="e"]:checked')].map((x) => parseInt(x.value, 10)).slice(0, o.frammenti);
    const r = await api("/api/rinasci", { origine: val("o"), destino: val("d"), nome: $("#nm").value, eredita: picks.length ? picks : [o.eredita.length - 1], corpo: $("#cb").checked });
    closeModal(); addLog(r.log); await refresh();
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
  if (ev.target.closest("#sound")) {
    SOUND = !SOUND; try { localStorage.setItem("ji_sound", SOUND ? "1" : "0"); } catch (e) { /* niente */ }
    $("#sound").textContent = SOUND ? "🔊" : "🔈"; if (SOUND) sfx("info"); return;
  }
  if (ev.target.closest("#theme")) {
    const order = ["", "light", "dark"], cur = document.documentElement.dataset.theme || "";
    const nx = order[(order.indexOf(cur) + 1) % order.length];
    if (nx) document.documentElement.dataset.theme = nx; else delete document.documentElement.dataset.theme;
    try { localStorage.setItem("ji_theme", nx); } catch (e) { /* niente */ }
    toast("Tema", nx === "dark" ? "scuro" : nx === "light" ? "chiaro" : "automatico (come il sistema)", "info");
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
  const t = ev.target.closest("[data-cmd]");
  if (t) { ev.preventDefault(); run(t.dataset.cmd); return; }
  const tb = ev.target.closest("[data-tab]");
  if (tb) loadTab(tb.dataset.tab);
  const mb = ev.target.closest("[data-menu]");
  if (mb) loadTab("m:" + mb.dataset.menu);
});
document.addEventListener("change", (ev) => { if (ev.target.matches("[data-auto]")) autoSet(ev.target); });
$("#cmdform").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const v = $("#cmd").value;
  if (v.trim()) { history.push(v); hpos = history.length; }
  $("#cmd").value = "";
  run(v);
});
$("#cmd").addEventListener("keydown", (ev) => {
  if (ev.key === "ArrowUp" && hpos > 0) { hpos--; $("#cmd").value = history[hpos]; ev.preventDefault(); }
  if (ev.key === "ArrowDown") { hpos = Math.min(history.length, hpos + 1); $("#cmd").value = history[hpos] || ""; ev.preventDefault(); }
});
document.addEventListener("keydown", (ev) => {
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
  try { localStorage.setItem("ji_wide", on ? "1" : "0"); } catch (e) { /* niente */ }
  if (tab === "mappa") loadMap();
}
try { if (localStorage.getItem("ji_wide") === "1") document.body.classList.add("wide"); } catch (e) { /* niente */ }
$("#auto-go").onclick = autoStart;
$("#sound").textContent = SOUND ? "🔊" : "🔈";
$("#auto-stop").onclick = autoStop;

(async () => {
  try {
    const s = await api("/api/stato");
    if (s.fase === "gioco") { const r = await api("/api/intro", {}); addLog(r.log); }
    await refresh();
  } catch (e) { addLog("⚠ Non riesco a parlare con il gioco: " + e.message); }
})();
