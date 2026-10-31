"use strict";
/* DaoTree — il grafo dei Dao come SVG in linea.
 *
 *   DaoTree.render(contenitore, dati, {onCmd(cmd), img(chiave) -> url|null})
 *
 * dati = {nodes:[{key,name,group,state,comp,grade,label,cmd,hint}], edges:[{from,to,kind,at}]}
 * Disposizione a livelli da sinistra a destra (cammino più lungo). Filtri, ricerca, zoom (+/−, ctrl+rotella) e
 * trascinamento per spostarsi. I colori vengono dai token di style.css (tema chiaro e scuro).
 */
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const NW = 156, NH = 42, GX = 76, GY = 14, PAD = 24;
  const GROUP_ORDER = ["base", "superiore", "elementale", "arma", "corpo e anima", "profondo", "proibito", "fuso"];
  const STATE_NAME = { have: "posseduto", ready: "pronto", open: "aperto", locked: "bloccato" };
  let uid = 0;

  const norm = (s) => String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  const el = (name, attrs, parent) => {
    const e = document.createElementNS(NS, name);
    if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  const html = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };
  const clip = (s, n) => (s.length > n ? s.slice(0, n - 1) + "…" : s);

  function layout(nodes, edges) {
    const byKey = new Map(nodes.map((n) => [n.key, n]));
    const col = new Map(nodes.map((n) => [n.key, 0]));
    const es = edges.filter((e) => byKey.has(e.from) && byKey.has(e.to) && e.from !== e.to);
    for (let it = 0; it < nodes.length; it++) {
      let ch = false;
      for (const e of es) {
        const c = col.get(e.from) + 1;
        if (c > col.get(e.to) && c <= nodes.length) { col.set(e.to, c); ch = true; }
      }
      if (!ch) break;
    }
    const cols = [];
    nodes.forEach((n) => { const c = col.get(n.key); (cols[c] = cols[c] || []).push(n); });
    const gi = (g) => { const i = GROUP_ORDER.indexOf(g); return i < 0 ? 99 : i; };
    const pos = new Map();
    let maxRows = 0;
    cols.forEach((list, c) => {
      if (!list) return;
      list.sort((a, b) => gi(a.group) - gi(b.group) || String(a.name).localeCompare(String(b.name), "it"));
      list.forEach((n, r) => pos.set(n.key, { x: PAD + c * (NW + GX), y: PAD + r * (NH + GY), col: c }));
      maxRows = Math.max(maxRows, list.length);
    });
    return { pos, edges: es, w: PAD * 2 + cols.length * NW + Math.max(0, cols.length - 1) * GX, h: PAD * 2 + maxRows * NH + Math.max(0, maxRows - 1) * GY };
  }

  function render(container, data, o) {
    o = o || {};
    const nodes = (data && data.nodes) || [];
    const id = ++uid;
    container.textContent = "";
    container.classList.add("dt-root");

    const bar = html("div", "dt-bar", null);
    const chips = html("div", "dt-chips", null);
    const search = html("input", "dt-search", null);
    search.type = "search";
    search.placeholder = "Cerca un Dao…";
    search.setAttribute("aria-label", "Cerca un Dao");
    const zoomBox = html("div", "dt-zoom", null);
    const bOut = html("button", "dt-zbtn", "−");
    const bIn = html("button", "dt-zbtn", "+");
    const bFit = html("button", "dt-zbtn dt-zpct", "100%");
    [bOut, bIn, bFit].forEach((b) => { b.type = "button"; });
    bOut.title = "Riduci"; bIn.title = "Ingrandisci"; bFit.title = "Zoom 100%";
    bOut.setAttribute("aria-label", "Riduci"); bIn.setAttribute("aria-label", "Ingrandisci");
    zoomBox.append(bOut, bFit, bIn);
    bar.append(chips, search, zoomBox);

    const legend = html("div", "dt-legend", null);
    [["component", "Componente"], ["derive", "Derivazione"], ["insight", "Intuizione"]].forEach(([k, t]) => {
      const s = html("span", "dt-lg", null);
      const sw = html("i", "dt-sw dt-sw-" + k, null);
      s.append(sw, document.createTextNode(t));
      legend.appendChild(s);
    });

    const wrap = html("div", "dt-wrap", null);
    wrap.tabIndex = 0;
    const tip = html("div", "dt-tip", null);
    tip.hidden = true;
    container.append(bar, legend, wrap, tip);

    if (!nodes.length) {
      wrap.appendChild(html("p", "dt-empty", "Nessun Dao da mostrare."));
      return;
    }

    const L = layout(nodes, (data && data.edges) || []);
    const svg = el("svg", { class: "dt-svg", viewBox: "0 0 " + L.w + " " + L.h, width: L.w, height: L.h, role: "img", "aria-label": "Albero dei Dao" });
    const defs = el("defs", null, svg);
    const cp = el("clipPath", { id: "dt-clip-" + id, clipPathUnits: "objectBoundingBox" }, defs);
    el("circle", { cx: 0.5, cy: 0.5, r: 0.5 }, cp);
    ["component", "derive", "insight"].forEach((k) => {
      const m = el("marker", { id: "dt-arr-" + k + "-" + id, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 6, markerHeight: 6, orient: "auto" }, defs);
      el("path", { d: "M0 1 L10 5 L0 9 z", class: "dt-arrow dt-arrow-" + k }, m);
    });
    const gE = el("g", { class: "dt-edges" }, svg);
    const gN = el("g", { class: "dt-nodes" }, svg);

    const inE = new Map(), outE = new Map();
    const edgeEls = [];
    L.edges.forEach((e, i) => {
      const a = L.pos.get(e.from), b = L.pos.get(e.to);
      const x1 = a.x + NW, y1 = a.y + NH / 2, x2 = b.x - 1, y2 = b.y + NH / 2;
      const dx = Math.max(30, (x2 - x1) * 0.5);
      const kind = ["component", "derive", "insight"].indexOf(e.kind) >= 0 ? e.kind : "component";
      const p = el("path", {
        d: "M" + x1 + " " + y1 + " C" + (x1 + dx) + " " + y1 + " " + (x2 - dx) + " " + y2 + " " + x2 + " " + y2,
        class: "dt-edge dt-e-" + kind, "marker-end": "url(#dt-arr-" + kind + "-" + id + ")",
      }, gE);
      const rec = { p, e, lab: null };
      if (kind === "insight" && e.at != null) {
        rec.lab = el("text", { class: "dt-elabel", x: (x1 + x2) / 2, y: (y1 + y2) / 2 - 4, "text-anchor": "middle" }, gE);
        rec.lab.textContent = String(e.at);
      }
      edgeEls.push(rec);
      (outE.get(e.from) || outE.set(e.from, []).get(e.from)).push(i);
      (inE.get(e.to) || inE.set(e.to, []).get(e.to)).push(i);
    });

    const nodeEls = new Map();
    const nodeByKey = new Map(nodes.map((n) => [n.key, n]));
    nodes.forEach((n) => {
      const p = L.pos.get(n.key);
      const st = STATE_NAME[n.state] ? n.state : "open";
      const g = el("g", { class: "dt-node dt-s-" + st + (n.cmd ? " dt-click" : ""), transform: "translate(" + p.x + " " + p.y + ")", "data-key": n.key, tabindex: 0, role: n.cmd ? "button" : "img" }, gN);
      g.setAttribute("aria-label", n.name + ", " + STATE_NAME[st] + (n.cmd ? ". Premi per: " + n.cmd : ""));
      el("rect", { class: "dt-box", width: NW, height: NH, rx: 10, ry: 10 }, g);
      const url = o.img ? o.img(n.key) : null;
      let tx = 11;
      if (url) {
        el("circle", { class: "dt-imgbg", cx: 22, cy: NH / 2, r: 14 }, g);
        const im = el("image", { x: 8, y: NH / 2 - 14, width: 28, height: 28, "clip-path": "url(#dt-clip-" + id + ")", preserveAspectRatio: "xMidYMid slice" }, g);
        im.setAttribute("href", url);
        tx = 44;
      }
      const t1 = el("text", { class: "dt-name", x: tx, y: 17 }, g);
      t1.textContent = clip(String(n.name || n.key), url ? 15 : 20);
      const bits = [];
      if (n.grade) bits.push(n.grade);
      if (n.label) bits.push(n.label);
      if (!bits.length && n.comp != null && st !== "have") bits.push("comp. " + n.comp);
      else if (n.comp != null && st !== "have" && n.comp > 0 && n.comp < 100) bits.push(n.comp + "%");
      const t2 = el("text", { class: "dt-sub", x: tx, y: 32 }, g);
      t2.textContent = clip(bits.join(" · ") || STATE_NAME[st], url ? 20 : 26);
      if (n.comp != null && st !== "have" && n.comp > 0) {
        const w = Math.max(0, Math.min(100, n.comp)) / 100 * (NW - 20);
        el("rect", { class: "dt-prog", x: 10, y: NH - 4, width: w, height: 2, rx: 1 }, g);
      }
      nodeEls.set(n.key, g);
    });
    wrap.appendChild(svg);

    // evidenziazione al passaggio
    const clearHl = () => {
      svg.classList.remove("dt-hl");
      svg.querySelectorAll(".dt-on").forEach((x) => x.classList.remove("dt-on"));
      tip.hidden = true;
    };
    const hl = (key) => {
      clearHl();
      svg.classList.add("dt-hl");
      nodeEls.get(key).classList.add("dt-on");
      [].concat(inE.get(key) || [], outE.get(key) || []).forEach((i) => {
        const r = edgeEls[i];
        r.p.classList.add("dt-on");
        if (r.lab) r.lab.classList.add("dt-on");
        nodeEls.get(r.e.from).classList.add("dt-on");
        nodeEls.get(r.e.to).classList.add("dt-on");
      });
    };
    const showTip = (key, ev) => {
      const n = nodeByKey.get(key);
      tip.textContent = "";
      tip.appendChild(html("b", null, n.name));
      tip.appendChild(html("span", "dt-tip-st", " · " + STATE_NAME[n.state || "open"]));
      if (n.hint) tip.appendChild(html("div", "dt-tip-h", n.hint));
      if (n.cmd) tip.appendChild(html("div", "dt-tip-c", "› " + n.cmd));
      tip.hidden = false;
      const r = container.getBoundingClientRect();
      let x = ev.clientX - r.left + 14, y = ev.clientY - r.top + 16;
      const tw = tip.offsetWidth, th = tip.offsetHeight;
      if (x + tw > r.width - 4) x = Math.max(4, ev.clientX - r.left - tw - 14);
      if (y + th > r.height - 4) y = Math.max(4, ev.clientY - r.top - th - 12);
      tip.style.left = x + "px";
      tip.style.top = y + "px";
    };
    const keyOf = (t) => { const g = t.closest && t.closest(".dt-node"); return g ? g.getAttribute("data-key") : null; };
    svg.addEventListener("mouseover", (ev) => { const k = keyOf(ev.target); if (k) { hl(k); showTip(k, ev); } });
    svg.addEventListener("mousemove", (ev) => { const k = keyOf(ev.target); if (k && !tip.hidden) showTip(k, ev); });
    svg.addEventListener("mouseout", (ev) => { if (keyOf(ev.target)) clearHl(); });
    svg.addEventListener("focusin", (ev) => { const k = keyOf(ev.target); if (k) hl(k); });
    svg.addEventListener("focusout", clearHl);

    let dragged = false;
    const fire = (k) => { const n = nodeByKey.get(k); if (n && n.cmd && o.onCmd) o.onCmd(n.cmd); };
    svg.addEventListener("click", (ev) => { const k = keyOf(ev.target); if (k && !dragged) fire(k); });
    svg.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter" && ev.key !== " ") return;
      const k = keyOf(ev.target);
      if (k) { ev.preventDefault(); fire(k); }
    });

    // filtri e ricerca
    const FILTERS = [["tutti", "Tutti"], ["miei", "Miei"], ["pronti", "Pronti"], ["fusioni", "Fusioni"]];
    let filter = "tutti", query = "";
    const fusKeys = new Set();
    nodes.forEach((n) => { if (n.group === "fuso") fusKeys.add(n.key); });
    const fusComp = new Set(fusKeys);
    L.edges.forEach((e) => { if (e.kind === "component" && fusKeys.has(e.to)) fusComp.add(e.from); });
    const passes = (n) => {
      if (filter === "miei") return n.state === "have";
      if (filter === "pronti") return n.state === "ready";
      if (filter === "fusioni") return fusComp.has(n.key);
      return true;
    };
    const counts = {
      tutti: nodes.length,
      miei: nodes.filter((n) => n.state === "have").length,
      pronti: nodes.filter((n) => n.state === "ready").length,
      fusioni: fusComp.size,
    };
    const chipEls = {};
    FILTERS.forEach(([k, t]) => {
      const b = html("button", "dt-chip", null);
      b.type = "button";
      b.append(document.createTextNode(t + " "), html("span", "dt-n", String(counts[k])));
      b.addEventListener("click", () => { filter = k; apply(false); });
      chips.appendChild(b);
      chipEls[k] = b;
    });
    function apply(scroll) {
      FILTERS.forEach(([k]) => { chipEls[k].classList.toggle("dt-chip-on", k === filter); chipEls[k].setAttribute("aria-pressed", k === filter ? "true" : "false"); });
      const q = norm(query.trim());
      const vis = new Set();
      let first = null;
      nodes.forEach((n) => {
        const ok = passes(n);
        const hit = !!q && (norm(n.name).indexOf(q) >= 0 || norm(n.key).indexOf(q) >= 0);
        const g = nodeEls.get(n.key);
        g.classList.toggle("dt-dim", !ok || (!!q && !hit));
        g.classList.toggle("dt-hit", hit && ok);
        if (ok) vis.add(n.key);
        if (hit && ok && !first) first = n;
      });
      edgeEls.forEach((r) => {
        const dim = !(vis.has(r.e.from) && vis.has(r.e.to));
        r.p.classList.toggle("dt-dim", dim);
        if (r.lab) r.lab.classList.toggle("dt-dim", dim);
      });
      if (scroll && first) {
        const p = L.pos.get(first.key);
        wrap.scrollTo({ left: (p.x + NW / 2) * scale - wrap.clientWidth / 2, top: (p.y + NH / 2) * scale - wrap.clientHeight / 2, behavior: "smooth" });
      }
    }
    search.addEventListener("input", () => { query = search.value; apply(true); });
    search.addEventListener("keydown", (e) => { e.stopPropagation(); });

    // zoom
    let scale = 1;
    const setScale = (s, cx, cy) => {
      s = Math.max(0.35, Math.min(2.4, s));
      if (s === scale) return;
      const ax = cx == null ? wrap.clientWidth / 2 : cx, ay = cy == null ? wrap.clientHeight / 2 : cy;
      const ux = (wrap.scrollLeft + ax) / scale, uy = (wrap.scrollTop + ay) / scale;
      scale = s;
      svg.setAttribute("width", L.w * s);
      svg.setAttribute("height", L.h * s);
      wrap.scrollLeft = ux * s - ax;
      wrap.scrollTop = uy * s - ay;
      bFit.textContent = Math.round(s * 100) + "%";
    };
    bIn.addEventListener("click", () => setScale(scale * 1.2));
    bOut.addEventListener("click", () => setScale(scale / 1.2));
    bFit.addEventListener("click", () => setScale(1));
    wrap.addEventListener("wheel", (e) => {
      if (!e.ctrlKey && !e.metaKey) return;
      e.preventDefault();
      const r = wrap.getBoundingClientRect();
      setScale(scale * (e.deltaY < 0 ? 1.1 : 1 / 1.1), e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });

    // trascinamento con il mouse
    let drag = null;
    wrap.addEventListener("pointerdown", (e) => {
      if (e.pointerType !== "mouse" || e.button !== 0) return;
      drag = { x: e.clientX, y: e.clientY, l: wrap.scrollLeft, t: wrap.scrollTop, moved: false };
    });
    window.addEventListener("pointermove", (e) => {
      if (!drag) return;
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (!drag.moved && Math.abs(dx) + Math.abs(dy) < 5) return;
      drag.moved = true; dragged = true;
      wrap.classList.add("dt-grab");
      wrap.scrollLeft = drag.l - dx;
      wrap.scrollTop = drag.t - dy;
    });
    window.addEventListener("pointerup", () => {
      if (!drag) return;
      wrap.classList.remove("dt-grab");
      drag = null;
      setTimeout(() => { dragged = false; }, 0);
    });

    apply(false);
  }

  window.DaoTree = { render };
})();
