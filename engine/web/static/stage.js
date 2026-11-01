"use strict";
/* Stage — il «palcoscenico» del luogo: una scena dipinta su cui si clicca.
 *
 *   Stage.render(stato, contenitore)   disegna (o aggiorna) la scena dentro il contenitore (di solito #place)
 *   Stage.heroEl()                     l'elemento del protagonista (#stage-hero)
 *   Stage.anchor(nome)                 il gettone di un PNG presente, per effetti futuri
 *   Stage.closeMenu()                  chiude il menu radiale
 *
 * Dipende (a runtime, in modo morbido) da face(), slotImg(), V.landscape(), Icons.svg(): se mancano usa i ripieghi.
 * I comandi passano da data-cmd: li esegue il gestore globale di app.js. Gli elementi cliccabili sono <div role="button">
 * e non <button>, così la funzione dedupe() dell'app non li nasconde scambiandoli per doppioni.
 */
(function () {
  const DIRN = { north: "Nord", south: "Sud", east: "Est", west: "Ovest", up: "Su", down: "Giù" };
  const MOM = { mattina: "Mattina", giorno: "Giorno", sera: "Sera", notte: "Notte" };
  const MOM_GLYPH = { mattina: "🌅", giorno: "☀", sera: "🌇", notte: "☾" };
  const METEO_GLYPH = { pioggia: "🌧", nebbia: "🌫", vento: "🍃", temporale: "⛈" };
  const KIND_BADGE = { demon: "👹", beast: "🐾", spirit: "👻", undead: "💀", plant: "🌿" };

  // posizioni dei gettoni, in % della scena: [x, y, xTel, yTel] (desktop, poi telefono). Ordine = preferenza di riempimento
  const SLOTS = [
    [50, 30, 50, 41], [33, 50, 30, 31], [67, 50, 70, 31], [22, 36, 30, 51], [78, 36, 70, 51], [17, 63, 14, 60], [83, 63, 86, 60],
  ];
  const MAX_TOKENS = 7;      // gettoni visibili al massimo (con «+N» compreso)

  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const hash = (s) => { let h = 2166136261; for (const c of String(s)) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; };
  const rng = (seed) => () => { seed |= 0; seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

  function fxOn() {
    try { if (localStorage.getItem("ji_fx") === "0") return false; } catch (e) { /* storage non disponibile */ }
    try { if (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches) return false; } catch (e) { /* ignora */ }
    return true;
  }
  const themeKey = () => { const d = document.documentElement.dataset.theme; if (d) return d; try { return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"; } catch (e) { return "light"; } };
  const cssv = (n, f) => { try { return getComputedStyle(document.documentElement).getPropertyValue(n).trim() || f; } catch (e) { return f; } };

  const dTier = (d) => (d <= 3 ? "safe" : d <= 6 ? "mid" : d <= 8 ? "high" : "dire");
  const momentOf = (s) => {
    if (MOM[s.momento]) return s.momento;
    const h = Number(s.ora); if (isNaN(h)) return "giorno";
    return h >= 5 && h < 10 ? "mattina" : h < 17 && h >= 10 ? "giorno" : h >= 17 && h < 20 ? "sera" : "notte";
  };

  // ---------------- ripieghi per le funzioni dell'app ----------------
  function callFace(name, size, aura, kind, o) {
    if (typeof face === "function") { try { return face(name, size, aura, kind, o); } catch (e) { /* ripiego */ } }
    return `<svg class="portrait" width="${size}" height="${size}" viewBox="0 0 10 10"><circle cx="5" cy="5" r="5" fill="currentColor" opacity=".2"/></svg>`;
  }
  function callSlot(dir, key) {
    if (typeof slotImg === "function") { try { return slotImg(dir, key); } catch (e) { return null; } }
    return null;
  }
  function iconHtml(t) {
    try {
      if (window.Icons && typeof Icons.svg === "function") {
        const cmd = String(t.cmd || "");
        for (const k of [cmd.split(" ")[0], cmd, t.icon]) { const v = k && Icons.svg(k); if (v) return `<span class="ic">${v}</span>`; }
      }
    } catch (e) { /* ripiego emoji */ }
    return `<span class="ic em">${esc(t.icon)}</span>`;
  }

  // ---------------- sfondo di ripiego: montagne a inchiostro ----------------
  function fallbackBg(L, mom) {
    const dark = themeKey() === "dark";
    const R = rng(hash(L.type + L.name));
    const sky = {
      mattina: dark ? ["#3a2a30", "#16211f"] : ["#f6dcc0", "#d3e4d2"], giorno: dark ? ["#22332e", "#121c19"] : ["#e6eee6", "#c3d6c9"],
      sera: dark ? ["#3a2638", "#17211e"] : ["#f1c9a8", "#c6d3c4"], notte: dark ? ["#0e1a2c", "#0a1412"] : ["#aab8cf", "#8ea49d"],
    }[mom];
    const ink = dark ? "#9fbfb2" : "#1d2a25", jade = cssv("--accent", "#1f8a65"), red = cssv("--bad", "#b3332a");
    const Wd = 800, H = 450;
    const ridge = (base, amp, op, n, col) => {
      let d = `M0 ${H} L0 ${base}`;
      for (let i = 1; i <= n; i++) { const x = (Wd / n) * i, y = base - amp * (0.25 + R() * 0.75); d += ` Q${(x - Wd / n / 2).toFixed(0)} ${(y - amp * 0.3).toFixed(0)} ${x.toFixed(0)} ${y.toFixed(0)}`; }
      return `<path d="${d} L${Wd} ${H} Z" fill="${col}" opacity="${op}"/>`;
    };
    let art = `<circle cx="${480 + R() * 200}" cy="${90 + R() * 40}" r="${mom === "notte" ? 26 : 38}" fill="${mom === "notte" ? "#e8eefc" : red}" opacity="${mom === "notte" ? .75 : .38}"/>`;
    if (L.type === "city") {
      art += ridge(330, 50, .16, 6, ink);
      for (let i = 0; i < 8; i++) { const x = 40 + i * 95 + R() * 20, y = 250 + R() * 60; art += `<rect x="${x}" y="${y}" width="56" height="${H - y}" fill="${ink}" opacity=".22"/><path d="M${x - 14} ${y} Q${x + 28} ${y - 34} ${x + 70} ${y} Z" fill="${red}" opacity=".35"/>`; }
    } else if (L.type === "ruin") {
      art += ridge(320, 60, .16, 7, ink);
      for (let i = 0; i < 6; i++) { const x = 70 + i * 120 + R() * 30, h = 60 + R() * 110; art += `<rect x="${x}" y="${H - h - 40}" width="16" height="${h + 40}" fill="${ink}" opacity=".26"/><rect x="${x - 6}" y="${H - h - 40}" width="28" height="6" fill="${ink}" opacity=".26"/>`; }
    } else {
      art += ridge(250, 140, .12, 7, ink) + ridge(310, 110, .2, 9, ink) + ridge(380, 70, .3, 11, jade);
      for (let i = 0; i < 3; i++) art += `<ellipse cx="${R() * Wd}" cy="${260 + i * 50}" rx="260" ry="16" fill="#fff" opacity="${dark ? .06 : .35}"/>`;
    }
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${Wd} ${H}' preserveAspectRatio='xMidYMax slice'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='${sky[0]}'/><stop offset='1' stop-color='${sky[1]}'/></linearGradient></defs><rect width='${Wd}' height='${H}' fill='url(#g)'/>${art.replace(/"/g, "'")}</svg>`;
    return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
  }

  // ---------------- particelle del tempo (CSS, poche decine di elementi) ----------------
  function fxPlan(s, mom) {
    const m = s.meteo, st = s.stagione, p = [];
    if (m === "temporale") { p.push(["rain", 64], ["flash", 1]); if (st === "inverno") p.push(["snow", 20]); }
    else if (m === "pioggia") p.push(["rain", 38]);
    else if (st === "inverno") p.push(["snow", m === "vento" ? 46 : 32]);
    if (m === "nebbia" || m === "pioggia" || m === "temporale") p.push(["mist", 3]);
    if (!/rain|snow/.test(p.map((x) => x[0]).join())) {
      if (st === "autunno") p.push(["leaf-a", m === "vento" ? 22 : 12]);
      else if (st === "primavera") p.push(["leaf-p", m === "vento" ? 22 : 12]);
      else if (st === "estate") p.push([mom === "notte" || mom === "sera" ? "fire" : "mote", 12]);
    }
    return p;
  }
  function fxHtml(plan, seed) {
    const R = rng(hash(seed)); let h = "";
    const AUT = ["#b8452a", "#d98a2b", "#9c5a2a", "#c9a227"], PET = ["#f4c6d0", "#f9dde3", "#eaa7b8", "#fff0f3"];
    for (const [k, n] of plan) {
      if (k === "mist") { for (let i = 0; i < n; i++) h += `<i class="ms" style="--t:${30 + i * 22}%;--d:${60 + R() * 40}s;--dl:${-R() * 60}s;--o:${.5 + R() * .25}"></i>`; continue; }
      if (k === "flash") { h += `<i class="fl"></i>`; continue; }
      for (let i = 0; i < n; i++) {
        const r = R(), r2 = R(), r3 = R();
        if (k === "rain") h += `<i class="rn" style="left:${(r * 115 - 8).toFixed(1)}%;--h:${(14 + r2 * 18).toFixed(0)}px;--d:${(.5 + r3 * .4).toFixed(2)}s;--dl:${(-r2 * 2).toFixed(2)}s;--o:${(.25 + r3 * .4).toFixed(2)}"></i>`;
        else if (k === "snow") h += `<i class="sn" style="left:${(r * 100).toFixed(1)}%;--s:${(2 + r2 * 4).toFixed(1)}px;--d:${(7 + r3 * 7).toFixed(1)}s;--dl:${(-r2 * 12).toFixed(1)}s;--sx:${(-30 + r * 60).toFixed(0)}px;--o:${(.5 + r3 * .45).toFixed(2)}"></i>`;
        else if (k === "leaf-a" || k === "leaf-p") { const pal = k === "leaf-a" ? AUT : PET;
          h += `<i class="lf ${k}" style="left:${(r * 100 - 10).toFixed(1)}%;--c:${pal[(r2 * pal.length) | 0]};--s:${(7 + r3 * 7).toFixed(0)}px;--d:${(9 + r2 * 9).toFixed(1)}s;--dl:${(-r3 * 18).toFixed(1)}s;--sx:${(40 + r * 150).toFixed(0)}px;--rt:${(360 + r2 * 540).toFixed(0)}deg"></i>`; }
        else if (k === "fire") h += `<i class="ff" style="left:${(8 + r * 84).toFixed(1)}%;top:${(38 + r2 * 50).toFixed(1)}%;--d:${(6 + r3 * 6).toFixed(1)}s;--dl:${(-r2 * 8).toFixed(1)}s"></i>`;
        else if (k === "mote") h += `<i class="mt" style="left:${(r * 100).toFixed(1)}%;top:${(15 + r2 * 70).toFixed(1)}%;--d:${(9 + r3 * 9).toFixed(1)}s;--dl:${(-r2 * 9).toFixed(1)}s"></i>`;
      }
    }
    return h;
  }
  function starsHtml(seed) {
    const R = rng(hash(seed + "stelle")); let h = "";
    for (let i = 0; i < 26; i++) h += `<i style="left:${(R() * 100).toFixed(1)}%;top:${(R() * 36).toFixed(1)}%;--d:${(2 + R() * 4).toFixed(1)}s;--dl:${(-R() * 5).toFixed(1)}s;--s:${(1 + R() * 1.6).toFixed(1)}px"></i>`;
    return h;
  }

  // ---------------- piccoli pezzi di HTML ----------------
  const CHEV = (rot) => `<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" style="transform:rotate(${rot}deg)"><path d="M5 15l7-7 7 7" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const STAIRS = (up) => `<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="${up ? "M3 20h5v-5h5v-5h5V5" : "M3 5h5v5h5v5h5v5"}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/><path d="${up ? "M14 5h4v4" : "M14 20h4v-4"}" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const GLYPH = { north: CHEV(0), east: CHEV(90), south: CHEV(180), west: CHEV(270), up: STAIRS(true), down: STAIRS(false) };

  function pips(d) {
    let h = ""; for (let i = 1; i <= 10; i++) h += `<i${i <= d ? " class=on" : ""}></i>`;
    return `<span class="pips t-${dTier(d)}" aria-hidden="true">${h}</span>`;
  }
  function plateHtml(s, mom) {
    const L = s.luogo, d = Math.max(0, Math.min(10, Number(L.danger) || 0));
    const mg = MOM_GLYPH[mom] || "", wg = METEO_GLYPH[s.meteo] || "";
    return `<div class="seal t-${dTier(d)}" title="Pericolo ${d} su 10"><b>${d}</b><small>pericolo</small></div>
      <div class="pt"><h3>${esc(L.name)}</h3>
      <div class="pm">${pips(d)}<span class="clock" title="${esc(MOM[mom] || "")}, ${esc(s.meteo || "")}, ${esc(s.stagione || "")}">${mg} ${esc((MOM[mom] || "").toLowerCase())}${wg ? ` · ${wg} ${esc(s.meteo)}` : s.meteo && s.meteo !== "sereno" ? ` · ${esc(s.meteo)}` : ""}</span></div>
      ${L.desc ? `<p class="pd">${esc(L.desc)}</p>` : ""}</div>`;
  }
  function gatesHtml(s) {
    return (s.uscite || []).map((e) => {
      const d = Math.max(0, Math.min(10, Number(e.danger) || 0)), dir = DIRN[e.dir] ? e.dir : "north";
      const tip = `${DIRN[dir]} → ${e.name} · pericolo ${d}`;
      return `<div class="stg-gate g-${dir} t-${dTier(d)}" role="button" tabindex="0" data-cmd="move ${esc(dir)}" data-dir="${dir}" title="${esc(tip)}" aria-label="${esc(tip)}">
        <span class="gi">${GLYPH[dir]}</span><span class="gl"><b>${esc(e.name)}</b><small>${DIRN[dir]} · ${pips(d)}</small></span></div>`;
    }).join("");
  }
  function hotbarHtml(s) {
    return (s.azioni_luogo || []).map((t) => {
      const tone = t.tone ? " tone-" + esc(t.tone) : "";
      if (t.ok) {
        const tip = `${t.label}${t.hint ? " — " + t.hint : ""}`;
        return `<div class="stg-act${tone}" role="button" tabindex="0" data-cmd="${esc(t.cmd)}" data-tip="${esc(tip)}" title="${esc(tip)}" aria-label="${esc(tip)}">${iconHtml(t)}</div>`;
      }
      const tip = `${t.label} — ${t.why || "non disponibile"}`;
      return `<div class="stg-act off" role="button" aria-disabled="true" tabindex="-1" data-tip="${esc(tip)}" title="${esc(tip)}" aria-label="${esc(tip)}">${iconHtml(t)}</div>`;
    }).join("");
  }
  function heroHtml(s) {
    return `<div class="tkh"><span class="halo"></span><span class="ring"></span><span class="pic">${callFace(s.nome || "Tu", 88, "--accent", "io")}</span>
      <span class="plaque"><b>${esc(s.nome || "Tu")}</b><small>Lv ${esc(s.livello == null ? "—" : s.livello)}</small></span></div>`;
  }
  const npcClass = (n) => (n.rel === "nemico" ? "foe" : n.rel === "legame" ? "friend" : n.kind && n.kind !== "human" ? "odd" : "");

  // ---------------- assegnazione dei posti (stabile tra un disegno e l'altro) ----------------
  function ordered(list) {
    const w = (n) => (n.rel === "nemico" ? 0 : n.rel === "legame" ? 1 : 2);
    return list.slice().sort((a, b) => w(a) - w(b) || (b.pri || 0) - (a.pri || 0) || (a.name < b.name ? -1 : 1));
  }
  function assign(list, st, cap) {
    const used = new Set(), out = new Map();
    for (const n of list) { const p = st.assigned.get(n.name); if (p != null && p < cap && !used.has(p)) { used.add(p); out.set(n.name, p); } }
    let next = 0;
    for (const n of list) { if (out.has(n.name)) continue; while (used.has(next)) next++; used.add(next); out.set(n.name, next); }
    st.assigned = out; return out;
  }
  function npcsHtml(s, st, fresh) {
    const all = ordered(s.presenti || []);
    const over = all.length > MAX_TOKENS;
    const shown = over ? all.slice(0, MAX_TOKENS - 1) : all;
    st.hidden = over ? all.slice(MAX_TOKENS - 1) : [];
    st.shown = shown;
    const slots = assign(shown, st, over ? MAX_TOKENS - 1 : MAX_TOKENS);
    const pos = (i, name) => { const S = SLOTS[i], h = hash(name); const j = ((h % 7) - 3) * 0.45, k = (((h >>> 5) % 7) - 3) * 0.45; return `--x:${(S[0] + j).toFixed(1)}%;--y:${(S[1] + k).toFixed(1)}%;--mx:${S[2]}%;--my:${S[3]}%;`; };
    let h = shown.map((n, idx) => {
      const isNew = fresh || !st.names.has(n.name);
      const badge = n.kind && KIND_BADGE[n.kind] ? `<span class="kb">${KIND_BADGE[n.kind]}</span>` : n.kind && n.kind !== "human" ? `<span class="kb">✦</span>` : "";
      const tip = `${n.name}${n.tag ? " — " + n.tag : ""}`;
      return `<div class="stg-tk ${npcClass(n)}${isNew ? " new" : ""}" role="button" tabindex="0" aria-haspopup="menu" data-npc="${esc(n.name)}" title="${esc(tip)}"
        style="${pos(slots.get(n.name), n.name)}--dl:${((hash(n.name) % 30) / 10).toFixed(1)}s;--in:${(idx * 0.07).toFixed(2)}s">
        <span class="tk"><span class="ring"></span><span class="pic">${callFace(n.name, 56, n.rel === "nemico" ? "--bad" : n.rel === "legame" ? "--good" : "--accent", "", { arch: n.arch, kind: n.kind, f: n.f })}</span>${badge}<span class="nm">${esc(n.name)}</span></span></div>`;
    }).join("");
    if (over) {
      const S = SLOTS[MAX_TOKENS - 1];
      h += `<div class="stg-tk more${fresh ? " new" : ""}" role="button" tabindex="0" aria-haspopup="menu" data-more="1" title="Altre ${st.hidden.length} persone"
        style="--x:${S[0]}%;--y:${S[1]}%;--mx:${S[2]}%;--my:${S[3]}%;--dl:1.2s;--in:.5s"><span class="tk"><span class="ring"></span><span class="pic"><b>+${st.hidden.length}</b></span><span class="nm">altri</span></span></div>`;
    }
    return h;
  }

  // ---------------- stato per contenitore ----------------
  let lastName = null, pendingDir = null, pendingAt = 0, globalsOn = false, openFor = null;
  const layer = (el, html) => { if (el && el._sig !== html) { el._sig = html; el.innerHTML = html; return true; } return false; };

  function render(s, box) {
    box = box || document.getElementById("place");
    if (!box || !s || !s.luogo) return;
    installGlobals();
    const L = s.luogo, fx = fxOn(), mom = momentOf(s);
    const bg = callSlot("luoghi", L.type);
    const key = [L.name, L.type, mom, s.meteo, s.stagione, bg || "", themeKey(), fx ? 1 : 0].join("|");
    let st = box._stg;
    box.classList.add("stage-on");
    if (!st || st.key !== key || !box.querySelector(".stg")) {
      if (st && st.ro) st.ro.disconnect();
      const arrive = lastName != null && lastName !== L.name;
      st = box._stg = { key, assigned: new Map(), names: new Set(), hidden: [], shown: [] };
      build(s, box, st, { bg, mom, fx, arrive });
    }
    lastName = L.name;
    update(s, box, st, mom);
  }

  function build(s, box, st, o) {
    const L = s.luogo;
    const bgCss = o.bg ? `url("${String(o.bg).replace(/"/g, "%22")}")` : fallbackBg(L, o.mom);
    const plan = o.fx ? fxPlan(s, o.mom) : [];
    const dir = o.arrive ? (pendingDir && Date.now() - pendingAt < 8000 ? pendingDir : "fade") : "";
    pendingDir = null;
    box.innerHTML = `<div class="stg${o.fx ? "" : " no-fx"}" data-m="${o.mom}" data-w="${esc(s.meteo || "")}" data-s="${esc(s.stagione || "")}">
      <div class="stg-view"${dir ? ` data-arrive="${dir}"` : ""}>
        <div class="stg-world">
          <div class="stg-par p1"><div class="stg-bg${o.bg ? " paint" : ""}"></div></div>
          <div class="stg-tint"></div>
          ${o.mom === "notte" && o.fx ? `<div class="stg-stars">${starsHtml(L.name)}</div>` : ""}
          <div class="stg-par p2"><div class="stg-fx">${fxHtml(plan, L.name + s.stagione + s.meteo)}</div></div>
          <div class="stg-par p3"><div class="stg-npcs"></div></div>
        </div>
        <div class="stg-vig"></div>
        <div class="stg-hero" id="stage-hero"></div>
        <div class="stg-plate"></div>
        <div class="stg-gates"></div>
        <div class="stg-banner"></div>
        <div class="stg-hotbar" role="toolbar" aria-label="Azioni del luogo"></div>
        <div class="stg-tip" role="tooltip"></div>
      </div><p class="stg-cap"></p></div>`;
    const view = box.querySelector(".stg-view");
    box.querySelector(".stg-bg").style.backgroundImage = bgCss;
    if (typeof ResizeObserver === "function") {
      st.ro = new ResizeObserver(() => { view.style.setProperty("--H", view.clientHeight + "px"); fitHero(view); });
      st.ro.observe(view);
    }
    view.style.setProperty("--H", (view.clientHeight || 450) + "px");
    if (dir) {
      const done = () => view.removeAttribute("data-arrive");
      view.addEventListener("animationend", (e) => { if (e.target.classList.contains("stg-world")) done(); }, { once: true });
      setTimeout(done, 1600);
    }
    st.fresh = true;
  }

  function fitHero(view) {
    const hb = view.querySelector(".stg-hotbar");
    view.style.setProperty("--hb", ((hb && hb.offsetHeight ? hb.offsetHeight + 10 : 0)) + "px");
  }

  function update(s, box, st, mom) {
    const $ = (q) => box.querySelector(q);
    const view = $(".stg-view"); if (!view) return;
    const stg = $(".stg");
    stg.classList.toggle("prison", !!s.prigioniero);
    stg.classList.toggle("has-n", (s.uscite || []).some((e) => e.dir === "north"));
    stg.classList.toggle("has-up", (s.uscite || []).some((e) => e.dir === "up"));
    layer($(".stg-plate"), plateHtml(s, mom));
    $(".stg-cap").textContent = (s.luogo.desc || "");
    $(".stg-cap").hidden = !s.luogo.desc;
    layer($(".stg-gates"), gatesHtml(s));
    layer($(".stg-hotbar"), hotbarHtml(s));
    layer($(".stg-hero"), heroHtml(s));
    layer($(".stg-banner"), s.prigioniero ? `<div class="stg-jail" role="button" tabindex="0" data-cmd="evadi"><span class="chain">⛓</span> Sei prigioniero — <b>Pianifica la fuga</b></div>` : "");
    const nh = npcsHtml(s, st, st.fresh);
    const sigNo = nh.replace(/ new"/g, '"');
    const nl = $(".stg-npcs");
    if (nl._sig2 !== sigNo) { nl._sig2 = sigNo; nl.innerHTML = nh; }
    st.names = new Set((s.presenti || []).map((n) => n.name));
    st.fresh = false;
    st.state = s;
    // il menu aperto sparisce se il suo PNG non c'è più
    if (openFor && openFor.box === box) {
      const stillThere = openFor.name ? st.names.has(openFor.name) : true;
      if (!stillThere) closeMenu();
    }
    fitHero(view);
  }

  // ---------------- menu radiale dei PNG ----------------
  function menuHtml(n) {
    const f = esc(String(n.name).split(" ")[0]);
    const acts = [["👁", "Osserva", "osserva " + f, ""], ["💬", "Parla", "talk " + f, "good"], ["⚔", "Attacca", "attack " + f, "bad"]];
    if (!n.kind || n.kind === "human") acts.push(["🤺", "Duello", "duello " + f, "warn"]);
    for (const x of n.extra || []) acts.push([x[0], x[1], x[2], x[3] || ""]);       // (Agg. 81) bottega, insegna, saluta…
    const rel = n.rel === "nemico" ? `<span class="rl foe">nemico</span>` : n.rel === "legame" ? `<span class="rl friend">legame</span>` : "";
    return `<div class="mh"><b>${esc(n.name)}</b>${rel}${n.tag ? `<small>${esc(n.tag)}</small>` : ""}</div>
      <div class="mb">${acts.map((a, i) => `<div class="mbtn ${a[3]}" role="menuitem" tabindex="0" data-cmd="${esc(a[2])}" style="--i:${i}" title="${a[1]} ${esc(n.name)} (${esc(a[2])})"><span class="mi">${a[0]}</span><span class="ml">${a[1]}</span></div>`).join("")}</div>`;
  }
  function placeMenu(view, menu, anchorEl) {
    const vr = view.getBoundingClientRect(), tr = anchorEl.getBoundingClientRect();
    const cx = tr.left - vr.left + tr.width / 2, w = menu.offsetWidth, h = menu.offsetHeight;
    let left = Math.max(6, Math.min(vr.width - w - 6, cx - w / 2));
    const below = tr.top - vr.top < vr.height * 0.5;
    let top = below ? tr.bottom - vr.top + 10 : tr.top - vr.top - h - 10;
    top = Math.max(6, Math.min(vr.height - h - 6, top));
    menu.style.left = left + "px"; menu.style.top = top + "px";
    menu.style.setProperty("--ax", Math.max(14, Math.min(w - 14, cx - left)) + "px");
    menu.classList.toggle("below", below);
  }
  function openMenu(box, tokenEl) {
    const st = box._stg, view = box.querySelector(".stg-view"); if (!st || !view) return;
    closeMenu();
    const menu = document.createElement("div");
    menu.className = "stg-menu"; menu.setAttribute("role", "menu");
    let name = null;
    if (tokenEl.dataset.more) {
      menu.classList.add("list");
      menu.innerHTML = `<div class="mh"><b>Altre persone qui</b><small>${st.hidden.length}</small></div><div class="ml-list">${st.hidden.map((n, i) =>
        `<div class="row ${npcClass(n)}" role="menuitem" tabindex="0" data-pick="${i}">${callFace(n.name, 28, "--accent", "", { arch: n.arch, kind: n.kind, f: n.f })}<span><b>${esc(n.name)}</b>${n.tag ? `<small>${esc(n.tag)}</small>` : ""}</span></div>`).join("")}</div>`;
    } else {
      name = tokenEl.dataset.npc;
      const n = (st.state.presenti || []).find((x) => x.name === name); if (!n) return;
      menu.innerHTML = menuHtml(n);
      tokenEl.classList.add("sel");
    }
    view.appendChild(menu);
    openFor = { box, menu, name, token: tokenEl };
    placeMenu(view, menu, tokenEl);
    requestAnimationFrame(() => menu.classList.add("in"));
    const f = menu.querySelector("[role=menuitem]"); if (f) { try { f.focus({ preventScroll: true }); } catch (e) { /* ok */ } }
  }
  function closeMenu() {
    if (!openFor) return;
    const o = openFor; openFor = null;
    if (o.token) o.token.classList.remove("sel");
    if (o.menu && o.menu.parentNode) o.menu.remove();
  }

  // ---------------- tooltip condiviso della barra delle azioni ----------------
  function showTip(view, el) {
    const tip = view.querySelector(".stg-tip"); if (!tip || !el.dataset.tip) return;
    tip.textContent = el.dataset.tip; tip.classList.toggle("off", el.classList.contains("off")); tip.classList.add("on");
    const vr = view.getBoundingClientRect(), r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.max(6, Math.min(vr.width - w - 6, r.left - vr.left + r.width / 2 - w / 2)) + "px";
    tip.style.top = Math.max(6, r.top - vr.top - h - 8) + "px";
  }
  const hideTip = (view) => { const t = view.querySelector(".stg-tip"); if (t) t.classList.remove("on"); };

  // ---------------- ascoltatori (una volta sola) ----------------
  function wire(box) {
    if (box._stgWired) return; box._stgWired = true;
    box.addEventListener("click", (ev) => {
      const t = ev.target;
      const pick = t.closest && t.closest("[data-pick]");
      if (pick && openFor) {   // dalla lista «+N» al menu del PNG scelto
        const st = box._stg, n = st.hidden[Number(pick.dataset.pick)], tok = openFor.token;
        ev.stopPropagation();
        if (n) { closeMenu(); openMenuFor(box, n, tok); }
        return;
      }
      const tk = t.closest && t.closest(".stg-tk");
      if (tk) { ev.stopPropagation(); if (openFor && openFor.token === tk) closeMenu(); else openMenu(box, tk); return; }
      const g = t.closest && t.closest(".stg-gate");
      if (g) { closeMenu(); startTravel(box, g.dataset.dir); return; }
      if (t.closest && t.closest(".mbtn")) { closeMenu(); return; }
    });
    box.addEventListener("keydown", (ev) => {
      if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches && ev.target.matches('.stg [role="button"], .stg [role="menuitem"]')) {
        if (ev.target.getAttribute("aria-disabled") === "true") return;
        ev.preventDefault(); ev.target.click();
      }
    });
    box.addEventListener("pointerover", (ev) => { const a = ev.target.closest && ev.target.closest(".stg-act"); if (a) showTip(box.querySelector(".stg-view"), a); });
    box.addEventListener("pointerout", (ev) => { const a = ev.target.closest && ev.target.closest(".stg-act"); if (a) hideTip(box.querySelector(".stg-view")); });
    box.addEventListener("focusin", (ev) => { const a = ev.target.closest && ev.target.closest(".stg-act"); if (a) showTip(box.querySelector(".stg-view"), a); });
    box.addEventListener("focusout", (ev) => { const v = box.querySelector(".stg-view"); if (v) hideTip(v); });
    // un po' di parallasse col puntatore (solo con mouse e animazioni attive)
    let raf = 0, nx = 0, ny = 0;
    box.addEventListener("pointermove", (ev) => {
      const stg = box.querySelector(".stg"); if (!stg || stg.classList.contains("no-fx") || ev.pointerType === "touch") return;
      const v = box.querySelector(".stg-view"), r = v.getBoundingClientRect();
      nx = ((ev.clientX - r.left) / r.width - 0.5) * 2; ny = ((ev.clientY - r.top) / r.height - 0.5) * 2;
      if (!raf) raf = requestAnimationFrame(() => { raf = 0; v.style.setProperty("--px", nx.toFixed(3)); v.style.setProperty("--py", ny.toFixed(3)); });
    });
    box.addEventListener("pointerleave", () => { const v = box.querySelector(".stg-view"); if (v) { v.style.setProperty("--px", 0); v.style.setProperty("--py", 0); } });
  }
  function openMenuFor(box, n, tok) {
    // apre il menu di un PNG nascosto nella lista «+N», agganciato al gettone «+N»
    const view = box.querySelector(".stg-view"); if (!view) return;
    const menu = document.createElement("div");
    menu.className = "stg-menu"; menu.setAttribute("role", "menu"); menu.innerHTML = menuHtml(n);
    view.appendChild(menu);
    openFor = { box, menu, name: null, token: tok };
    placeMenu(view, menu, tok);
    requestAnimationFrame(() => menu.classList.add("in"));
  }
  function startTravel(box, dir) {
    const stg = box.querySelector(".stg"), view = box.querySelector(".stg-view"); if (!view) return;
    pendingDir = dir; pendingAt = Date.now();
    if (stg.classList.contains("no-fx")) return;
    view.dataset.go = dir; view.classList.add("go");
    setTimeout(() => { if (view.isConnected) { view.classList.remove("go"); view.removeAttribute("data-go"); } }, 1800);   // il movimento è fallito: la scena torna
  }
  function installGlobals() {
    if (globalsOn) return; globalsOn = true;
    document.addEventListener("click", (ev) => {
      if (!openFor) return;
      if (openFor.menu.contains(ev.target) || (openFor.token && openFor.token.contains(ev.target))) return;
      closeMenu();
    });
    document.addEventListener("keydown", (ev) => { if (ev.key === "Escape" && openFor) { const t = openFor.token; closeMenu(); if (t && t.focus) { try { t.focus({ preventScroll: true }); } catch (e) { /* ok */ } } } });
  }
  const origRender = render;
  function renderWired(s, box) { box = box || document.getElementById("place"); if (box) wire(box); origRender(s, box); }

  window.Stage = {
    render: renderWired,
    heroEl: () => document.getElementById("stage-hero"),
    anchor: (name) => { const all = document.querySelectorAll(".stg-tk[data-npc]"); for (const e of all) if (e.dataset.npc === name) return e; return null; },
    closeMenu,
  };
})();
