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
function addLog(text, cmd) {
  if (!text && !cmd) return;
  const box = $("#log");
  const div = document.createElement("div");
  div.className = "entry";
  let html = cmd ? `<div class="you">› ${esc(cmd)}</div>` : "";
  html += (text || "").split("\n").map((l) => {
    const c = lineClass(l);
    return c ? `<span class="${c}">${esc(l)}</span>` : esc(l);
  }).join("\n");
  div.innerHTML = html;
  box.appendChild(div);
  while (box.children.length > 300) box.removeChild(box.firstChild);
  box.scrollTop = box.scrollHeight;
}

// ---------------- comandi ----------------
async function run(cmd) {
  cmd = (cmd || "").trim();
  if (!cmd || busy) return;
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

// ---------------- stato ----------------
async function refresh() {
  const s = await api("/api/stato");
  if (s.fase === "nuovo") return showCreation();
  if (s.fase === "morto") return showDeath();
  S = s;
  renderTop(s); renderPlace(s); renderScene(s); renderSugg(s); renderAutoCfg(s);
  if (tab === "mete") renderMete(s);
  else if (tab === "mappa") loadMap();
}

function setBar(id, pct) { $(id).style.width = Math.max(0, Math.min(100, pct)) + "%"; }

function renderTop(s) {
  $("#t-nome").textContent = s.nome;
  $("#t-regno").textContent = s.regno;
  setBar("#b-esp", s.esperienza);
  setBar("#b-qi", s.qi.pct); $("#v-qi").textContent = `${s.qi.cur}/${s.qi.max}`;
  setBar("#b-sp", s.spirito.pct); $("#v-sp").textContent = `${s.spirito.cur}/${s.spirito.max}`;
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
    const many = s.presenti.length > 8 && !showAllNpcs;
    const list = many ? s.presenti.slice(0, 8) : s.presenti;
    h += `<div class="npcs">` + list.map((n) => {
      const first = n.name.split(" ")[0];
      return `<span class="npc" title="${esc(n.tag)}">${esc(n.name)}${n.tag ? ` <span class="muted">${esc(n.tag)}</span>` : ""}
        <button data-cmd="talk ${esc(first)}">parla</button><button data-cmd="attack ${esc(first)}">attacca</button></span>`;
    }).join("") + (many ? `<button id="more-npc">+ altri ${s.presenti.length - 8}</button>` : "") + `</div>`;
  }
  $("#place").innerHTML = h;
  const m = $("#more-npc"); if (m) m.onclick = () => { showAllNpcs = true; renderPlace(S); };
}

function renderScene(s) {
  const box = $("#scene");
  if (!s.scena) { box.hidden = true; box.innerHTML = ""; return; }
  box.hidden = false;
  box.innerHTML = `<h3>✦ ${esc(s.scena.title)}</h3><p>${esc(s.scena.text)}</p><div class="choices">` +
    s.scena.choices.map((c) => `<button data-cmd="${c.n}"><b>${c.n}.</b> ${esc(c.label)}${c.hint ? `<small>[${esc(c.hint)}]</small>` : ""}</button>`).join("") +
    `</div>`;
}

function renderSugg(s) {
  $("#sugg").innerHTML = s.scena ? "" :
    s.suggerimenti.map((x, i) => `<button data-cmd="${esc(x.cmd)}" title="${esc(x.cmd)}"><span class="n">${i + 1}</span>${esc(x.label)}</button>`).join("");
}

function renderMete(s) {
  const b = $("#tabbody");
  if (!s.mete.length) { b.innerHTML = `<div class="empty">Nulla di importante sta accadendo, per ora.</div>`; return; }
  b.innerHTML = s.mete.map((d) => {
    const where = d.dist === 0 ? "QUI" : d.dist == null ? "in un altro mondo" : `${d.dist} tappe`;
    return `<div class="dest card"><div class="t">${esc(d.title)}</div>
      <div class="w">${esc(d.where)} · ${where}</div>
      <div class="b">${d.dist ? `<button data-cmd="vai ${d.n}">Vai</button>` : ""}${d.join ? `<button class="primary" data-cmd="iscriviti ${d.n}">Partecipa</button>` : ""}</div></div>`;
  }).join("");
}

// ---------------- pannelli ----------------
async function loadTab(name) {
  tab = name;
  document.querySelectorAll("#tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  const b = $("#tabbody");
  if (name === "mete") { if (S) renderMete(S); return; }
  if (name === "mappa") return loadMap();
  b.innerHTML = `<div class="empty">Carico…</div>`;
  try {
    const parts = await api("/api/pannello/" + name);
    let head = "";
    if (name === "personaggio") head = await daoBars();
    if (name === "tesori") head = `<div class="tools"><button class="primary" data-cmd="tesori cura">✧ Cura tutti i tesori</button></div>`;
    if (name === "aiuto") {
      const sv = await api("/api/salvataggi");
      head = `<div class="card"><b>Partite salvate</b><div class="tools" style="margin-top:6px">
        <button class="primary" data-cmd="salva">💾 Salva ora</button></div>` +
        (sv.length ? sv.map((x) => `<div class="dest"><div class="t">${esc(x.name)}</div><div class="w">${esc(x.when)}</div>
          <div class="b"><button data-cmd="carica ${esc(x.name)}">Carica</button></div></div>`).join("")
          : `<div class="empty">Nessun salvataggio.</div>`) + `</div>`;
    }
    if (name === "storia") head = `<div class="tools"><button data-cmd="encounter">Rileggi la scena</button><button data-cmd="svolte">Svolte</button></div>`;
    b.innerHTML = head + parts.map((p) => `<pre>${esc(p.text)}</pre>`).join("");
  } catch (e) { b.innerHTML = `<div class="empty">Errore: ${esc(e.message)}</div>`; }
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

const ICON = { city: "▣", mountain: "▲", ruin: "▒", forbidden_zone: "☠" };
async function loadMap() {
  const m = await api("/api/mappa");
  const xs = m.nodes.map((n) => n.x), ys = m.nodes.map((n) => n.y);
  const minx = Math.min(...xs), miny = Math.min(...ys), W = 64, H = 46;
  const cols = Math.max(...xs) - minx + 1, rows = Math.max(...ys) - miny + 1;
  const px = (n) => (n.x - minx) * W + 8, py = (n) => (n.y - miny) * H + 8;
  const byId = Object.fromEntries(m.nodes.map((n) => [n.id, n]));
  let svg = `<svg viewBox="0 0 ${cols * W + 8} ${rows * H + 8}" xmlns="http://www.w3.org/2000/svg">`;
  for (const [a, b] of m.edges) {
    const A = byId[a], B = byId[b];
    svg += `<line x1="${px(A) + 27}" y1="${py(A) + 16}" x2="${px(B) + 27}" y2="${py(B) + 16}"/>`;
  }
  for (const n of m.nodes) {
    const cls = ["node", n.visited ? "visited" : "", n.here ? "here" : "", n.marks.length ? "mark" : ""].join(" ");
    const short = n.name.length > 11 ? n.name.slice(0, 10) + "…" : n.name;
    const ic = n.here ? "@" : n.home ? "⌂" : (ICON[n.type] || "·");
    const tip = `${n.name} (pericolo ${n.danger})${n.marks.length ? " — " + n.marks.join(", ") : ""}`;
    svg += `<g class="${cls}" data-cmd="vai ${esc(n.name)}"><title>${esc(tip)}</title>
      <rect x="${px(n)}" y="${py(n)}" width="54" height="32" rx="5"/>
      <text class="ic" x="${px(n) + 4}" y="${py(n) + 14}">${ic}</text>
      <text x="${px(n) + 4}" y="${py(n) + 27}">${esc(short)}</text></g>`;
  }
  svg += `</svg>`;
  $("#tabbody").innerHTML = `<div id="map">${svg}<div class="legend">@ tu · ⌂ dimora · ▣ città · ▲ montagna · ▒ rovine · ☠ zona proibita · bordo giallo = meta in corso. Clic su un luogo per andarci.</div></div>`;
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
      if (d.stop) addLog(`⏸ Il pilota si ferma: ${d.stop}`);
      if (d.stop === "morto") return showDeath();
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
    <button class="primary" id="go-new">Comincia</button>`);
  $("#go-new").onclick = async () => {
    const r = await api("/api/nuovo", { origine: val("o"), destino: val("d"), rivali: val("r"), nome: $("#nm").value });
    closeModal(); addLog(r.log); await refresh();
  };
}

async function showDeath() {
  const o = await api("/api/morte");
  if (o.salvato) { addLog(o.salvato); return refresh(); }
  openModal(`<h2>La tua vita è finita</h2><pre>${esc(o.epilogo)}</pre>
    <p>Il mondo prosegue senza di te. Ma le anime, qui, non si spengono del tutto.</p>
    <fieldset><legend>Cosa porti con te (un solo frammento)</legend>${choiceList("e", o.eredita.map((l, i) => ({ i, l })), "i", (x) => esc(x.l))}</fieldset>
    <fieldset><legend>Origine</legend>${choiceList("o", o.origini, "key", (x) => `<b>${esc(x.name)}</b> — ${esc(x.desc)}`)}</fieldset>
    <fieldset><legend>Destino</legend>${choiceList("d", o.destini, "key", (x) => esc(x.label))}</fieldset>
    <p><label>Nome <input id="nm" value="" placeholder="(lo stesso di prima)" maxlength="32"></label></p>
    <button class="primary" id="go-reb">Rinasci in questo mondo</button>`);
  $("#go-reb").onclick = async () => {
    const r = await api("/api/rinasci", { origine: val("o"), destino: val("d"), nome: $("#nm").value, eredita: parseInt(val("e") || "0", 10) });
    closeModal(); addLog(r.log); await refresh();
  };
}

// ---------------- eventi ----------------
document.addEventListener("click", (ev) => {
  const t = ev.target.closest("[data-cmd]");
  if (t) { ev.preventDefault(); run(t.dataset.cmd); return; }
  const tb = ev.target.closest("[data-tab]");
  if (tb) loadTab(tb.dataset.tab);
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
    if (S.scena) { if (n <= S.scena.choices.length) { ev.preventDefault(); run(String(n)); } }
    else if (n <= S.suggerimenti.length) { ev.preventDefault(); run(S.suggerimenti[n - 1].cmd); }
  }
});
$("#auto-go").onclick = autoStart;
$("#auto-stop").onclick = autoStop;

(async () => {
  try {
    const s = await api("/api/stato");
    if (s.fase === "gioco") { const r = await api("/api/intro", {}); addLog(r.log); }
    await refresh();
  } catch (e) { addLog("⚠ Non riesco a parlare con il gioco: " + e.message); }
})();
