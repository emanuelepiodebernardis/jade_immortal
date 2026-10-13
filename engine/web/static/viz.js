// Jade Immortal — grafica: emblemi, grafici, rete delle relazioni, Libro, legenda, riepiloghi.
// Solo SVG generato qui: niente librerie, niente immagini da internet.
"use strict";

const V = (() => {
  const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim() || "#888";

  // ---------------- simboli e colori (una sola legenda per tutto il gioco) ----------------
  const RARITY = { comune: "--muted", non_comune: "--good", raro: "--info", prezioso: "--rare", leggendario: "--warn" };
  const RARITY_IT = { comune: "comune", non_comune: "non comune", raro: "raro", prezioso: "prezioso", leggendario: "leggendario" };
  const LEGEND = [
    ["⚔", "combattimento, duelli, guerre", "--bad"], ["☯", "coltivazione, Qi, sfondamenti", "--good"],
    ["☸", "Dao e comprensione", "--info"], ["♥", "legami e intimità", "--rare"],
    ["🩸", "faide e vendette", "--bad"], ["🤝", "debiti di vita, alleati", "--good"],
    ["⛓ 💀", "servi sigillati, salme rianimate", "--rare"], ["🏯", "sette vassalle", "--warn"], ["🌀", "spirito, tempra dell'anima", "--info"],
    ["⛩", "setta e merito", "--accent"], ["👑", "regni e corti", "--warn"],
    ["✦", "eventi e svolte della storia", "--rare"], ["⚠", "pericolo", "--warn"],
    ["☠ ✝", "morte, caduti", "--bad"], ["✧", "guadagni, titoli", "--good"],
    ["💰", "pietre spirituali", "--warn"], ["💊 📜 ◆ 🏺", "pillole, manuali, nuclei, tesori", "--info"],
  ];

  // ---------------- emblemi: sigilli generati dal nome ----------------
  const GLYPHS = {
    tesori: "宝鼎鏡鐘扇印塔壺丹符", bestie: "龍虎鳳麟龜蛇狼鷹獅蛟", sangue: "血脈魂源", reliquie: "火水木金土雷風光暗空",
    nemici: "仇敵魔鬼煞刃", maestri: "師道經賢", default: "道玄天靈",
  };
  function hash(s) { let h = 2166136261; for (const c of String(s)) { h ^= c.codePointAt(0); h = Math.imul(h, 16777619); } return h >>> 0; }
  function emblem(name, cat, rarity, size = 72) {
    const h = hash(name + cat);
    const col = css(RARITY[rarity] || "--muted");
    const ink = css("--ink"), panel = css("--panel");
    const glyphs = GLYPHS[cat] || GLYPHS.default;
    const g = [...glyphs][h % [...glyphs].length];
    const shape = (h >> 3) % 4, ring = 6 + ((h >> 6) % 10), rot = (h >> 10) % 45;
    const c = size / 2, r = size / 2 - 3;
    let outer;
    if (shape === 0) outer = `<circle cx="${c}" cy="${c}" r="${r}"/>`;
    else if (shape === 1) outer = `<rect x="3" y="3" width="${size - 6}" height="${size - 6}" rx="6"/>`;
    else {
      const n = shape === 2 ? 8 : 6;
      const pts = Array.from({ length: n }, (_, i) => {
        const a = (Math.PI * 2 * i) / n + (rot * Math.PI) / 180;
        return `${(c + r * Math.cos(a)).toFixed(1)},${(c + r * Math.sin(a)).toFixed(1)}`;
      }).join(" ");
      outer = `<polygon points="${pts}"/>`;
    }
    const dots = Array.from({ length: ring }, (_, i) => {
      const a = (Math.PI * 2 * i) / ring;
      return `<circle cx="${(c + (r - 7) * Math.cos(a)).toFixed(1)}" cy="${(c + (r - 7) * Math.sin(a)).toFixed(1)}" r="1.4"/>`;
    }).join("");
    return `<svg class="emblem" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" aria-hidden="true">
      <g fill="${panel}" stroke="${col}" stroke-width="2.5">${outer}</g>
      <g fill="${col}" opacity=".7">${dots}</g>
      <text x="${c}" y="${c + size * 0.15}" text-anchor="middle" font-size="${size * 0.45}" fill="${rarity === "comune" ? ink : col}"
        font-family="serif">${g}</text></svg>`;
  }
  function slug(s) { return String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]/g, ""); }
  function picture(name, cat, rarity, images, size = 72) {
    const s = slug(name);
    const f = (images || []).find((x) => slug(x.replace(/\.[^.]+$/, "")) === s);
    return f ? `<img class="emblem" src="/immagini/${encodeURIComponent(f)}" width="${size}" height="${size}" alt="">` : emblem(name, cat, rarity, size);
  }

  // ---------------- ritratti generati (busto in stile xianxia, dal nome) ----------------
  const ROBE = ["#2f6f5a", "#7a2e2e", "#2c4f7c", "#5b3f7a", "#8a6a2a", "#3b3b44", "#a14f2c", "#2a6b75", "#6e2f55"];
  const HAIR = ["#1d1a19", "#2b2220", "#3a2a22", "#e8e4dc", "#5b4636", "#14161c"];
  const SKIN = ["#f0d6bd", "#e8c5a5", "#dcb593", "#c99a78", "#f5e1cf"];
  function portrait(name, kind, size = 64, aura = "") {
    const h = hash(String(name) + (kind || ""));
    const pick = (arr, sh) => arr[(h >>> sh) % arr.length];
    const robe = pick(ROBE, 1), hair = pick(HAIR, 5), skin = pick(SKIN, 9);
    const style = (h >>> 13) % 4, female = (h >>> 17) % 2 === 0, beard = !female && (h >>> 19) % 3 === 0;
    const auraCol = aura ? css(aura) : css("--accent");
    const id = "p" + (h % 100000);
    let hairBack = "", hairFront = "";
    if (style === 0) { hairBack = `<path d="M30 44 Q50 10 70 44 L72 70 L28 70 Z" fill="${hair}"/>`; hairFront = `<path d="M33 38 Q50 22 67 38 Q60 30 50 31 Q40 30 33 38Z" fill="${hair}"/><circle cx="50" cy="21" r="7" fill="${hair}"/>`; }
    else if (style === 1) { hairBack = `<path d="M29 42 Q50 12 71 42 L76 92 L24 92 Z" fill="${hair}"/>`; hairFront = `<path d="M33 40 Q50 20 67 40 Q55 33 50 36 Q45 33 33 40Z" fill="${hair}"/>`; }
    else if (style === 2) { hairFront = `<path d="M32 40 Q50 18 68 40 Q62 28 50 28 Q38 28 32 40Z" fill="${hair}"/><rect x="40" y="16" width="20" height="7" rx="2" fill="${css("--gold") || "#b58a2a"}"/>`; }
    else { hairBack = `<path d="M31 44 Q50 14 69 44 L70 60 L30 60 Z" fill="${hair}"/>`; hairFront = `<path d="M33 39 Q42 26 50 30 Q58 26 67 39 Q58 33 50 35 Q42 33 33 39Z" fill="${hair}"/>`; }
    const eyes = `<ellipse cx="44" cy="45" rx="2.2" ry="${female ? 1.6 : 1.2}" fill="#1b1b1f"/><ellipse cx="56" cy="45" rx="2.2" ry="${female ? 1.6 : 1.2}" fill="#1b1b1f"/>
      <path d="M40.5 41 L47 41.5 M53 41.5 L59.5 41" stroke="${hair}" stroke-width="1.4" stroke-linecap="round"/>`;
    const mouth = `<path d="M46.5 53 Q50 ${female ? 55 : 54} 53.5 53" stroke="#8a4a3a" stroke-width="1.2" fill="none" stroke-linecap="round"/>`;
    const bd = beard ? `<path d="M43 54 Q50 66 57 54 Q50 58 43 54Z" fill="${hair}" opacity=".9"/>` : "";
    return `<svg class="portrait" width="${size}" height="${size}" viewBox="0 0 100 100" aria-hidden="true">
      <defs><radialGradient id="${id}"><stop offset="0" stop-color="${auraCol}" stop-opacity=".55"/><stop offset="1" stop-color="${auraCol}" stop-opacity="0"/></radialGradient>
        <clipPath id="${id}c"><circle cx="50" cy="50" r="48"/></clipPath></defs>
      <circle cx="50" cy="50" r="48" fill="${css("--panel2")}" stroke="${auraCol}" stroke-width="2"/>
      <g clip-path="url(#${id}c)"><circle cx="50" cy="50" r="46" fill="url(#${id})"/>${hairBack}
        <path d="M18 100 Q22 72 50 70 Q78 72 82 100Z" fill="${robe}"/>
        <path d="M42 70 L50 84 L58 70" fill="none" stroke="${css("--gold") || "#b58a2a"}" stroke-width="2"/>
        <rect x="45" y="58" width="10" height="13" fill="${skin}"/>
        <ellipse cx="50" cy="46" rx="15" ry="${female ? 17 : 18}" fill="${skin}"/>${eyes}${mouth}${bd}${hairFront}</g></svg>`;
  }

  // ---------------- sfondi dei luoghi (paesaggi a inchiostro, per tipo) ----------------
  function landscape(type, seed) {
    const h = hash(String(seed || type));
    const ink = css("--ink"), acc = css("--accent");
    const W = 600, H = 120;
    const ridge = (amp, base, op, n) => {
      let d = `M0 ${H}`;
      for (let i = 0; i <= n; i++) { const x = (W / n) * i, y = base - amp * Math.abs(Math.sin((i + (h % 7)) * 1.7 + (h >>> (i % 8)) % 3)); d += ` L${x.toFixed(0)} ${y.toFixed(0)}`; }
      return `<path d="${d} L${W} ${H} Z" fill="${ink}" opacity="${op}"/>`;
    };
    let art = "";
    if (type === "mountain") art = ridge(60, 110, .06, 9) + ridge(40, 118, .09, 13) + `<circle cx="${480 + h % 60}" cy="30" r="14" fill="${acc}" opacity=".12"/>`;
    else if (type === "city") {
      art = ridge(18, 116, .05, 8);
      for (let i = 0; i < 7; i++) { const x = 40 + i * 80 + (h >>> i) % 20, w = 46, y = 70 + ((h >>> (i + 3)) % 25);
        art += `<rect x="${x}" y="${y}" width="${w}" height="${H - y}" fill="${ink}" opacity=".07"/><path d="M${x - 10} ${y} Q${x + w / 2} ${y - 22} ${x + w + 10} ${y} Z" fill="${ink}" opacity=".09"/>`; }
    } else if (type === "ruin") {
      art = ridge(14, 118, .05, 7);
      for (let i = 0; i < 6; i++) { const x = 60 + i * 90 + (h >>> i) % 25, ht = 30 + (h >>> (i + 2)) % 50;
        art += `<rect x="${x}" y="${H - ht}" width="12" height="${ht}" fill="${ink}" opacity=".08"/><rect x="${x - 4}" y="${H - ht}" width="20" height="4" fill="${ink}" opacity=".08"/>`; }
    } else if (type === "forbidden_zone") {
      art = ridge(30, 116, .08, 11) + `<rect width="${W}" height="${H}" fill="${css("--bad")}" opacity=".04"/>`;
      for (let i = 0; i < 5; i++) art += `<ellipse cx="${(h >>> i) % W}" cy="${60 + (h >>> (i + 4)) % 40}" rx="90" ry="10" fill="${ink}" opacity=".04"/>`;
    } else art = ridge(25, 116, .06, 10);
    return `url("data:image/svg+xml;utf8,${encodeURIComponent(`<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 ${W} ${H}' preserveAspectRatio='xMidYMax slice'>${art.replace(/"/g, "'")}</svg>`)}")`;
  }

  // ---------------- grafici ----------------
  function lineChart(points, opts) {
    const W = 340, H = 130, P = { l: 38, r: 8, t: 14, b: 22 };
    if (!points.length) return "";
    const xs = points.map((p) => p.x), ys = points.map((p) => (opts.log ? Math.log10(Math.max(1, p.y)) : p.y));
    const x0 = Math.min(...xs), x1 = Math.max(...xs, x0 + 1), y0 = Math.min(...ys, opts.log ? 0 : Math.min(...ys)), y1 = Math.max(...ys, y0 + 1e-6);
    const X = (x) => P.l + ((x - x0) / (x1 - x0)) * (W - P.l - P.r);
    const Y = (y) => H - P.b - ((y - y0) / (y1 - y0 || 1)) * (H - P.t - P.b);
    const path = points.map((p, i) => `${i ? "L" : "M"}${X(p.x).toFixed(1)},${Y(ys[i]).toFixed(1)}`).join("");
    const col = css(opts.color || "--accent"), line = css("--line"), mut = css("--muted");
    const dec = y1 - y0 < 2 ? 100 : 10;
    const fmt = (v) => (opts.log ? Math.round(10 ** v) : Math.round(v * dec) / dec).toLocaleString("it-IT");
    const ticks = [y0, (y0 + y1) / 2, y1].map((v) => `<line x1="${P.l}" x2="${W - P.r}" y1="${Y(v)}" y2="${Y(v)}" stroke="${line}"/>
      <text x="${P.l - 4}" y="${Y(v) + 4}" text-anchor="end" font-size="10" fill="${mut}">${fmt(v)}</text>`).join("");
    const steps = (opts.marks || []).map((m) => `<line x1="${X(m.x)}" x2="${X(m.x)}" y1="${P.t}" y2="${H - P.b}" stroke="${css("--rare")}" stroke-dasharray="3 3" opacity=".6"><title>${esc(m.label)}</title></line>`).join("");
    const last = points[points.length - 1];
    return `<figure class="chart"><figcaption>${esc(opts.title)} <span class="muted">${esc(opts.sub || "")}</span></figcaption>
      <svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(opts.title)}">${ticks}${steps}
      <path d="${path}" fill="none" stroke="${col}" stroke-width="2"/>
      <circle cx="${X(last.x)}" cy="${Y(ys[ys.length - 1])}" r="3" fill="${col}"/>
      <text x="${P.l}" y="${H - 4}" font-size="10" fill="${mut}">giorno ${x0}</text>
      <text x="${W - P.r}" y="${H - 4}" font-size="10" fill="${mut}" text-anchor="end">giorno ${x1}</text></svg></figure>`;
  }
  function radar(values, title) {
    const keys = Object.keys(values), n = keys.length, R = 70, c = 100;
    const max = Math.max(...keys.map((k) => Math.sqrt(Math.max(0, values[k]))), 1);
    const pt = (i, f) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [c + R * f * Math.cos(a), c + R * f * Math.sin(a)]; };
    const line = css("--line"), mut = css("--muted"), col = css("--accent");
    const grid = [0.33, 0.66, 1].map((f) => `<polygon points="${keys.map((_, i) => pt(i, f).join(",")).join(" ")}" fill="none" stroke="${line}"/>`).join("");
    const axes = keys.map((k, i) => { const [x, y] = pt(i, 1.18); return `<line x1="${c}" y1="${c}" x2="${pt(i, 1)[0]}" y2="${pt(i, 1)[1]}" stroke="${line}"/>
      <text x="${x}" y="${y + 4}" text-anchor="middle" font-size="10" fill="${mut}">${esc(k)}</text>`; }).join("");
    const shape = keys.map((k, i) => pt(i, Math.sqrt(Math.max(0, values[k])) / max).join(",")).join(" ");
    return `<figure class="chart radar"><figcaption>${esc(title)} <span class="muted">(scala radice: i divari restano leggibili)</span></figcaption>
      <svg viewBox="0 0 200 200" width="220" role="img" aria-label="${esc(title)}">${grid}${axes}
      <polygon points="${shape}" fill="${col}" fill-opacity=".25" stroke="${col}" stroke-width="2"/></svg>
      <div class="radar-vals">${keys.map((k) => `<span>${esc(k)} <b>${Math.round(values[k]).toLocaleString("it-IT")}</b></span>`).join("")}</div></figure>`;
  }
  function charts(d) {
    const h = d.storia || [];
    const marks = [];
    for (let i = 1; i < h.length; i++) if (h[i].tier > h[i - 1].tier) marks.push({ x: h[i].d, label: `regno ${h[i].tier}` });
    return `<div class="card charts">` +
      lineChart(h.map((p) => ({ x: p.d, y: p.lvl })), { title: "Coltivazione", sub: "regno + strato (linee viola: sfondamenti)", marks, color: "--good" }) +
      lineChart(h.map((p) => ({ x: p.d, y: p.power })), { title: "Potenza di combattimento", sub: "scala logaritmica", log: true, color: "--bad" }) +
      lineChart(h.map((p) => ({ x: p.d, y: p.dao })), { title: "Comprensione dei Dao", sub: "somma", color: "--info" }) +
      radar(d.radar || {}, "Il tuo profilo") + `</div>`;
  }

  // ---------------- la rete delle relazioni ----------------
  const GROUP = {
    io: ["--accent", "Tu"], famiglia: ["--info", "Famiglia"], legame: ["--good", "Legami"], debito: ["--good", "Debiti di vita"],
    nemico: ["--bad", "Nemici"], faida: ["--bad", "Faide"], vittima: ["--muted", "Caduti"],
    servo: ["--rare", "Servi"], vassalla: ["--warn", "Sette vassalle"],
  };
  const EDGE = { famiglia: "--info", legame: "--good", debito: "--good", nemico: "--bad", faida: "--bad", sangue: "--muted", parentela: "--muted", servo: "--rare" };
  function graph(d) {
    const nodes = d.nodi || [], edges = d.archi || [];
    if (nodes.length <= 1) return `<div class="card"><b>La rete</b><div class="empty">Nessun legame ancora: la rete si disegna man mano che vivi.</div></div>`;
    const W = 420, H = 400, cx = W / 2, cy = H / 2;
    const order = ["famiglia", "legame", "servo", "vassalla", "debito", "nemico", "faida"];
    const ring = nodes.filter((n) => order.includes(n.group)).sort((a, b) => order.indexOf(a.group) - order.indexOf(b.group));
    const pos = { io: [cx, cy] };
    ring.forEach((n, i) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / ring.length; pos[n.id] = [cx + 130 * Math.cos(a), cy + 130 * Math.sin(a), a]; });
    nodes.filter((n) => n.group === "vittima").forEach((n, i) => {
      const e = edges.find((x) => x.b === n.id && x.kind === "parentela");
      const a = e && pos[e.a] ? pos[e.a][2] : (2 * Math.PI * i) / 7;
      pos[n.id] = [cx + 180 * Math.cos(a + 0.12), cy + 180 * Math.sin(a + 0.12), a];
    });
    const lines = edges.filter((e) => pos[e.a] && pos[e.b]).map((e) => {
      const [x1, y1] = pos[e.a], [x2, y2] = pos[e.b];
      return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${css(EDGE[e.kind] || "--line")}" stroke-width="${e.kind === "faida" ? 2 : 1.2}"
        ${e.kind === "sangue" || e.kind === "parentela" ? 'stroke-dasharray="4 3"' : ""} opacity=".75"><title>${esc(e.label)}</title></line>`;
    }).join("");
    const dots = nodes.filter((n) => pos[n.id]).map((n) => {
      const [x, y] = pos[n.id];
      const col = css((GROUP[n.group] || GROUP.legame)[0]);
      const r = n.id === "io" ? 16 : Math.max(7, Math.min(15, 9 * Math.sqrt(n.forza || 0.5)));
      const dead = !n.vivo;
      return `<g class="gnode" data-node="${esc(n.id)}" style="cursor:pointer">
        <circle cx="${x}" cy="${y}" r="${r}" fill="${dead ? "none" : col}" fill-opacity="${n.qui ? 1 : .55}" stroke="${col}" stroke-width="2"/>
        ${dead ? `<text x="${x}" y="${y + 4}" text-anchor="middle" font-size="11" fill="${col}">✝</text>` : ""}
        <text x="${x}" y="${y + r + 12}" text-anchor="middle" font-size="10.5" fill="${css("--ink")}">${esc(n.label)}</text>
        <title>${esc(n.label)} — ${esc((GROUP[n.group] || ["", ""])[1])}${n.vivo ? ` · forza ×${n.forza}` : " · caduto"}${n.qui ? " · QUI" : ""}</title></g>`;
    }).join("");
    const legend = Object.entries(GROUP).filter(([k]) => nodes.some((n) => n.group === k)).map(([, [c, l]]) =>
      `<span><i style="background:${css(c)}"></i>${l}</span>`).join("");
    return `<div class="card"><b>La rete delle relazioni</b> <span class="muted">— clicca un nome; pieno = qui, tenue = lontano, ✝ = caduto, tratteggio = sangue</span>
      <svg viewBox="0 0 ${W} ${H}" width="100%" class="graph">${lines}${dots}</svg>
      <div class="glegend">${legend}</div><div id="gnode-info"></div></div>`;
  }
  function nodeInfo(d, id) {
    const n = (d.nodi || []).find((x) => String(x.id) === String(id));
    if (!n || n.id === "io") return "";
    const first = (n.nome || n.label).split(" ")[0];
    const rel = (d.archi || []).filter((e) => String(e.a) === String(id) || String(e.b) === String(id)).map((e) => e.label);
    let btn = "";
    if (n.vivo) {
      if (n.qui) btn += n.group === "faida" || n.group === "nemico" ? `<button data-cmd="duello ${esc(first)}">Duello</button>` : `<button data-cmd="parla ${esc(first)}">Parla</button>`;
      else if (n.loc) btn += `<button data-cmd="vai #${n.loc}">Vai</button>`;
    }
    return `<div class="ginfo"><b>${esc(n.nome || n.label)}</b> <span class="muted">${esc(rel.join(" · "))}</span> ${btn}</div>`;
  }

  // ---------------- il Libro ----------------
  const BOOK_CATS = [["tutto", "Tutto"], ["tesori", "Tesori"], ["bestie", "Bestie"], ["sangue", "Sangue"],
    ["reliquie", "Reliquie"], ["nemici", "Nemici"], ["maestri", "Maestri"]];
  function book(d, cat) {
    const pages = (d.pagine || []).filter((p) => cat === "tutto" || p.cat === cat);
    const chips = BOOK_CATS.map(([k, l]) => {
      const n = k === "tutto" ? (d.pagine || []).length : (d.pagine || []).filter((p) => p.cat === k).length;
      return `<button class="chip ${k === cat ? "on" : ""}" data-book="${k}">${l} <span class="muted">${n}</span></button>`;
    }).join("");
    const cards = pages.map((p) => `<div class="page r-${esc(p.rarita)}">
      ${picture(p.nome, p.cat, p.rarita, d.immagini)}
      <div class="ptext"><b>${esc(p.nome)}</b><div class="muted">${esc(p.sub)}${p.rarita ? " · " + esc(RARITY_IT[p.rarita] || p.rarita) : ""}</div>
      ${p.desc ? `<div>${esc(p.desc)}</div>` : ""}${p.fatti.length ? `<ul>${p.fatti.map((f) => `<li>${esc(f)}</li>`).join("")}</ul>` : ""}</div></div>`).join("");
    return `<div class="card"><b>📖 Il Libro</b> <span class="muted">— tutto ciò che hai ottenuto e incontrato. Le tue immagini nella cartella «immagini» sostituiscono gli emblemi.</span>
      <div class="chips">${chips}</div>${cards || `<div class="empty">Ancora nulla in questa sezione.</div>`}</div>`;
  }

  function legend() {
    return `<div class="card"><b>Legenda dei simboli</b><div class="legend">` + LEGEND.map(([s, t, c]) =>
      `<span><b style="color:${css(c)}">${s}</b> ${esc(t)}</span>`).join("") +
      `</div><div class="legend rar">` + Object.entries(RARITY).map(([k, c]) => `<span style="color:${css(c)}">■ ${RARITY_IT[k]}</span>`).join("") + `</div></div>`;
  }

  // ---------------- riepilogo del pilota automatico ----------------
  function summary(r, stop) {
    if (!r || r.giorni === undefined) return "";
    const row = (ico, label, v, good = true) => (v ? `<div><span>${ico} ${label}</span><b class="${(v > 0) === good ? "up" : "down"}">${v > 0 ? "+" : ""}${Number(v).toLocaleString("it-IT")}</b></div>` : "");
    return `<div class="summary"><div class="sh">✧ Stato etereo: ${r.giorni} giorn${r.giorni === 1 ? "o" : "i"}${stop ? ` — si ferma: ${esc(stop)}` : ""}</div>
      <div class="sgrid">
        <div class="wide"><span>☯ Coltivazione</span><b>${r.regno_da === r.regno_a ? esc(r.regno_a) : esc(r.regno_da) + " → " + esc(r.regno_a)}</b></div>
        <div><span>⚔ Potenza</span><b class="${r.potenza >= 1 ? "up" : "down"}">×${r.potenza}</b></div>
        ${row("☸", "Dao", r.dao)}${row("💰", "Pietre", r.pietre)}${row("✧", "Fama", r.fama)}${row("☯", "Karma", r.karma)}
        ${row("⚔", "Vite tolte", r.uccisioni, false)}${row("🩸", "Nuove faide", r.faide, false)}${row("🤝", "Nuovi debiti di vita", r.debiti)}
        ${row("🎒", "Oggetti", r.oggetti)}
      </div>${r.titoli && r.titoli.length ? `<div class="stitles">✧ ${r.titoli.map(esc).join(" · ")}</div>` : ""}</div>`;
  }

  // ---------------- categorie del registro ----------------
  const CATS = [["combattimento", /⚔|uccid|round|duello|scontr|colp|ferit|attacc|bestia|nemic|razzia|guerra/i],
    ["coltivazione", /☯|☸|strato|regno|sfond|qi\b|dao|medit|tribolaz|elemento celeste|pillol|essenz/i],
    ["legami", /♥|🤝|🩸|faid|vendett|legam|nemesi|famigli|favore|amic|giurat|maestro|compagn/i],
    ["setta", /⛩|setta|merito|anzian|torneo|discepol|tecnica segreta|stipendio/i],
    ["mondo", /voci|arrivano|se ne vanno|passaggio|giorno|asta|invasion|era |calamit|regno di|regni|cielo|vento/i]];
  function category(line) { for (const [k, re] of CATS) if (re.test(line)) return k; return "altro"; }

  // ---------------- l'eroe (finestra di stato in stile «The Gamer») ----------------
  const fmt = (v) => Number(v || 0).toLocaleString("it-IT");
  function hbar(label, pct, value, tone, title) {
    return `<div class="hb ${tone || ""}" title="${esc(title || "")}"><span class="l">${label}</span>
      <div class="bar"><i style="width:${Math.max(0, Math.min(100, pct))}%"></i></div><span class="v">${value}</span></div>`;
  }
  function statusWindow(h) {
    const w = h.finestra;
    const mx = Math.max(1, ...w.attributi.map((a) => a.punti));
    const attrs = w.attributi.map((a) => `<div class="attr" title="${esc(a.nome)}: ${esc(a.effetto)} ×${a.mult}">
        <b>${a.k}</b><span class="an">${esc(a.nome)}</span><div class="bar"><i style="width:${Math.round(100 * a.punti / mx)}%"></i></div>
        <span class="av">${a.punti}</span><span class="am">×${a.mult.toFixed(2)}</span>
        <button data-cmd="attributi ${a.k} 1" ${w.liberi ? "" : "disabled"} title="+1 ${esc(a.nome)}">+</button></div>`).join("");
    return `<div class="syswin">
      <div class="sw-head"><span>STATO</span><span class="muted">${esc(w.regno)}</span></div>
      <div class="sw-name"><b>${esc(w.nome)}</b> <span class="lvtag">Lv. ${w.livello}</span> <span class="lvtag rank" title="Rango del cacciatore: E, D, C, B, A, S, SS, SSS, Nazionale, Monarca">Rango ${esc(w.rango)}</span></div>
      <div class="sw-title">Titolo: <b>${esc(w.titolo)}</b> <span class="muted">(${w.titoli})</span></div>
      <div class="sw-grid">
        <div><span>PV</span><b>${fmt(w.pv)}</b></div><div><span>ATT</span><b>${fmt(w.attacco)}</b></div><div><span>DIF</span><b>${fmt(w.difesa)}</b></div>
        <div><span>QI</span><b>${fmt(w.qi[0])}/${fmt(w.qi[1])}</b></div><div><span>SPIRITO</span><b>${fmt(w.spirito[0])}/${fmt(w.spirito[1])}</b></div>
        <div><span>CUORE</span><b>${h.cuore.val}</b></div>
        <div><span>CORPO</span><b>${fmt(w.corpo)}</b></div><div><span>ANIMA</span><b>${fmt(w.anima)}</b></div><div><span>KARMA</span><b>${fmt(w.karma)}</b></div>
        <div><span>PIETRE</span><b>${fmt(w.pietre)}</b></div><div><span>FAMA</span><b>${fmt(w.fama)}</b></div><div><span>TEMPRA</span><b>${esc(h.anima.grado)}</b></div>
      </div>
      <div class="sw-sep">ATTRIBUTI</div>${attrs}
      <div class="sw-foot">Punti liberi: <b class="${w.liberi ? "hot" : ""}">${w.liberi}</b>
        <button data-cmd="attributi bilancia" ${w.liberi ? "" : "disabled"}>Bilancia</button>
        <button data-cmd="attributi auto ${w.auto ? "off" : "on"}">Auto: ${w.auto ? "ON" : "OFF"}</button></div>
      ${h.titoli.length ? `<div class="sw-sep">TITOLI RECENTI</div><div class="titles">${h.titoli.slice().reverse().map((t) => `<span>${esc(t)}</span>`).join("")}</div>` : ""}
    </div>`;
  }
  function ring(pct, label, sub, color) {
    const r = 30, c = 2 * Math.PI * r, p = Math.max(0, Math.min(1, pct));
    return `<div class="ring"><svg viewBox="0 0 80 80" width="78" height="78"><circle cx="40" cy="40" r="${r}" fill="none" stroke="${css("--chip")}" stroke-width="8"/>
      <circle cx="40" cy="40" r="${r}" fill="none" stroke="${css(color)}" stroke-width="8" stroke-linecap="round"
        stroke-dasharray="${(c * p).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 40 40)"/>
      <text x="40" y="45" text-anchor="middle" font-size="15" fill="${css("--ink")}">${esc(sub)}</text></svg><div>${label}</div></div>`;
  }
  const DEEP_COL = ["--info", "--good", "--rare"];
  const IDX_NAME = ["—", "iniziato", "adepto", "esperto", "maestro", "gran maestro", "dominatore", "legislatore", "sovrano", "origine", "antenato"];
  function deepTriad(d) {
    if (!d) return "";
    const rings = d.dao.map((x, i) => ring(Math.min(1, x.idx / 7), `${x.icona} ${x.k}<br><small class="muted">${IDX_NAME[x.idx] || x.idx}</small>`, fmt(x.comp), DEEP_COL[i])).join("");
    return `<div class="card"><b>🌌⏳🎲 Dao profondi</b> <button data-menu="profondi">Arcani e Giudizio</button>
      <div class="rings">${rings}</div>
      ${hbar("Sfida al Cielo", Math.min(100, 100 * d.sfida / Math.max(600, d.sfida * 1.3)), fmt(d.sfida), "bad", "più sale, più il Cielo ti vuole cancellare")}
      <div class="muted small">Capitolo: <b>${esc(d.capitolo)}</b> · Sigilli della Sfida: ${d.sigilli}${d.risonanze.length ? " · Risonanze: " + d.risonanze.map(esc).join(", ") : ""}</div></div>`;
  }
  function spiritCards(sp, slots) {
    if (!sp || !sp.length) return `<div class="card"><b>✺ Spiriti del Dao</b><div class="empty">Quando un Dao arriva a «maestro» (100) prende forma e combatte con te.</div></div>`;
    return `<div class="card"><b>✺ Spiriti del Dao</b> <span class="muted">— in battaglia fino a ${slots}</span> <button data-cmd="spiriti allena">Allenati con loro</button>
      <div class="spirits">${sp.map((s, i) => `<div class="spirit ${i < slots ? "on" : ""}">${emblem(s.nome, "default", s.liv >= 4 ? "leggendario" : s.liv >= 3 ? "prezioso" : s.liv >= 2 ? "raro" : "non_comune", 44)}
        <div><b>${esc(s.nome)}</b><div class="muted small">${esc(s.stadio)} · ${esc(s.dao)} · ${fmt(s.comp)}</div></div></div>`).join("")}</div></div>`;
  }
  const RAR_COL = { narrative: "--warn", elemental: "--good", systemic: "--info", superior: "--rare", deep: "--bad" };
  function daoChart(ds, all) {
    if (!ds.length) return `<div class="card"><b>I tuoi Dao</b><div class="empty">Ancora nessun Dao: allenati («train») o comprendi («comprehend»).</div></div>`;
    const sorted = ds.slice().sort((a, b) => b.comp - a.comp);
    const list = all ? sorted : sorted.slice(0, 14);
    const mx = Math.log10(Math.max(10, sorted[0].comp + 1));
    const rows = list.map((d) => `<div class="dbar" title="${esc(d.name)} — ${d.comp}; prossima soglia: ${esc(d.next)} a ${d.goal}">
        <span class="n">${esc(d.short)}</span>
        <div class="track"><i style="width:${(100 * Math.log10(d.comp + 1) / mx).toFixed(1)}%;background:${css(RAR_COL[d.rarity] || "--accent")}"></i>
          <em style="width:${d.pct}%"></em></div>
        <span class="v">${fmt(d.comp)} <small>${esc(d.label)}</small></span></div>`).join("");
    const kinds = Object.entries({ narrative: "arma", elemental: "elemento", systemic: "sistemico", superior: "superiore", deep: "profondo" })
      .map(([k, l]) => `<span><i style="background:${css(RAR_COL[k])}"></i>${l}</span>`).join("");
    return `<div class="card"><b>☸ I tuoi Dao</b> <span class="muted">— ${ds.length} Dao · scala logaritmica; la linea sottile è il cammino verso la prossima soglia</span>
      <div class="dchart">${rows}</div><div class="glegend">${kinds}</div>
      ${ds.length > 14 ? `<button id="dao-all">${all ? "Mostra i primi 14" : `Mostra tutti (${ds.length})`}</button>` : ""}</div>`;
  }
  function talentRadar(t) {
    const vals = Object.fromEntries(t.map((x) => [x.k, x.v]));
    return `<div class="card"><b>🧬 Talento</b> <span class="muted">— le tue affinità innate</span>
      <div class="radar2">${radarSvg(vals, 100, "--warn")}<div>${t.map((x) => hbar(esc(x.k), x.v, esc(x.q), x.v >= 70 ? "good" : x.v < 40 ? "bad" : "")).join("")}</div></div></div>`;
  }
  function radarSvg(values, max, color) {
    const keys = Object.keys(values), n = keys.length, R = 66, c = 92;
    const pt = (i, f) => { const a = -Math.PI / 2 + (2 * Math.PI * i) / n; return [c + R * f * Math.cos(a), c + R * f * Math.sin(a)]; };
    const line = css("--line"), mut = css("--muted"), col = css(color || "--accent");
    const grid = [0.25, 0.5, 0.75, 1].map((f) => `<polygon points="${keys.map((_, i) => pt(i, f).join(",")).join(" ")}" fill="none" stroke="${line}"/>`).join("");
    const axes = keys.map((k, i) => { const [x, y] = pt(i, 1.2); return `<line x1="${c}" y1="${c}" x2="${pt(i, 1)[0]}" y2="${pt(i, 1)[1]}" stroke="${line}"/>
      <text x="${x}" y="${y + 4}" text-anchor="middle" font-size="10" fill="${mut}">${esc(k)}</text>`; }).join("");
    const shape = keys.map((k, i) => pt(i, Math.max(0.02, Math.min(1, values[k] / max))).join(",")).join(" ");
    return `<svg viewBox="0 0 184 184" width="200" role="img">${grid}${axes}<polygon points="${shape}" fill="${col}" fill-opacity=".28" stroke="${col}" stroke-width="2"/></svg>`;
  }
  const EL_COL = { legno: "#3f9d4f", fuoco: "#d9534f", terra: "#b08440", metallo: "#9aa4ad", acqua: "#3a86c8", fulmine: "#8f6be0", vento: "#4fb5a5", luce: "#e3b341", oscurita: "#5b4a73" };
  function rootsChart(r, combos, talents) {
    const mx = Math.max(10, ...r.map((x) => x.score));
    const vals = Object.fromEntries(r.map((x) => [x.el, Math.sqrt(Math.max(0, x.score))]));
    const rows = r.slice().sort((a, b) => b.score - a.score).map((x) =>
      `<div class="hb"><span class="l"><i class="dot" style="background:${EL_COL[x.key]}"></i>${esc(x.el)}</span>
       <div class="bar"><i style="width:${(100 * x.score / mx).toFixed(1)}%;background:${EL_COL[x.key]}"></i></div><span class="v">${fmt(Math.round(x.score))} <small>${esc(x.grado)}</small></span></div>`).join("");
    return `<div class="card"><b>🌱 Radici spirituali</b> <span class="muted">— radar in scala radice</span>
      <div class="radar2">${radarSvg(vals, Math.sqrt(mx), "--good")}<div>${rows}</div></div>
      ${combos.length ? `<div class="sw-sep">COMBINAZIONI ATTIVE</div><div class="titles">${combos.map((c) => `<span title="${esc(c.tipo)}">${esc(c.nome)}</span>`).join("")}</div>` : ""}
      ${talents.length ? `<div class="sw-sep">TALENTI DELLE RADICI</div><div class="titles">${talents.map((t) => `<span>${esc(t)}</span>`).join("")}</div>` : ""}</div>`;
  }
  function bodyCard(c, anima, cuore) {
    const soul = `<div class="card"><b>🌀 Anima e cuore</b>${hbar("Tempra", anima.pct, esc(anima.grado), "info")}${hbar("Cuore del Dao", cuore.val, `${cuore.val} · ${esc(cuore.label)}`, cuore.val < 30 ? "bad" : cuore.val < 50 ? "warn" : "good")}
      <div class="tools"><button data-cmd="tempra">Tempra lo spirito</button></div></div>`;
    if (!c) return `<div class="card"><b>✦ Corpo leggendario</b><div class="empty">Nessun corpo leggendario. Puoi nascerci affidandoti al Cielo alla prossima vita.</div></div>` + soul;
    return `<div class="card body"><b>✦ ${esc(c.nome)}</b> <span class="lvtag">${esc(c.stadio)}</span>
      ${hbar("Risveglio", c.pct, `stadio ${c.n}`, "rare")}
      <p class="lore">${esc(c.storia)}</p><ul>${c.doni.map((d) => `<li>${esc(d)}</li>`).join("")}</ul></div>` + soul;
  }
  function bloodChart(lines) {
    if (!lines.length) return `<div class="card"><b>🩸 Sangue</b><div class="empty">Nessun lignaggio. Le essenze delle bestie risvegliano il sangue.</div></div>`;
    const mx = Math.max(1, ...lines.map((l) => l.conc));
    return `<div class="card"><b>🩸 Lignaggi</b> <button data-menu="sangue">Apri il menu del sangue</button>` + lines.map((l) =>
      hbar(`${esc(l.icona)} ${esc(l.nome)}`, 100 * l.conc / mx, `${fmt(l.conc)} · ${esc(l.rango)}${l.purezza ? ` · ✧${l.purezza}` : ""}`, l.r >= 6 ? "rare" : l.r >= 4 ? "warn" : "", l.grado)).join("") + `</div>`;
  }

  function dailyQuest(q) {
    const rows = q.obiettivi.map((g) => `<div class="dq ${g.ok ? "ok" : ""}"><span>${g.ok ? "✔" : "·"} ${g.icon} ${esc(g.label)}</span>
      <div class="bar"><i style="width:${Math.min(100, Math.round(100 * g.have / Math.max(1, g.need)))}%"></i></div><b>${Math.min(g.have, g.need)}/${g.need}</b>${g.ok ? "<span></span>" : `<button data-cmd="${{ dao: "train", kills: "attack creatures", soul: "tempra" }[g.k]}">▶ ${{ dao: "allenati", kills: "caccia", soul: "tempra" }[g.k]}</button>`}</div>`).join("");
    return `<div class="syswin quest"><div class="sw-head"><span>MISSIONE QUOTIDIANA</span><span>Rango ${esc(q.rango)}</span></div>
      <div class="muted small">«Prepararsi a diventare forti.» Giorno ${q.giorno} · serie ${q.serie} ${q.serie >= 1 ? "🔥" : ""}</div>${rows}
      <div class="small" style="margin-top:6px">${q.fatta ? "✔ COMPLETATA — ricompensa ricevuta." : "Ricompensa: +1 punto attributo e pietre · ogni 7 giorni di fila +2 punti e un titolo · <span class=\"warn\">saltarla costa</span>"}</div></div>`;
  }

  return { slug, dailyQuest, emblem, picture, portrait, landscape, charts, graph, nodeInfo, book, legend, summary, category, esc,
    statusWindow, deepTriad, spiritCards, daoChart, talentRadar, rootsChart, bodyCard, bloodChart };
})();
