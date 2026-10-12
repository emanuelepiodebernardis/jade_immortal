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
  };
  const EDGE = { famiglia: "--info", legame: "--good", debito: "--good", nemico: "--bad", faida: "--bad", sangue: "--muted", parentela: "--muted" };
  function graph(d) {
    const nodes = d.nodi || [], edges = d.archi || [];
    if (nodes.length <= 1) return `<div class="card"><b>La rete</b><div class="empty">Nessun legame ancora: la rete si disegna man mano che vivi.</div></div>`;
    const W = 420, H = 400, cx = W / 2, cy = H / 2;
    const order = ["famiglia", "legame", "debito", "nemico", "faida"];
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

  return { emblem, picture, charts, graph, nodeInfo, book, legend, summary, category, esc };
})();
