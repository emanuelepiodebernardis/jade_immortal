"use strict";
/* CmdBar — suggerimenti per la barra dei comandi (#cmd).
 *
 *   CmdBar.init({input, fetchJSON, onPick})   collega il widget all'input; carica /api/comandi una sola volta
 *   CmdBar.refresh()                          ricarica l'elenco dei comandi dal server
 *   CmdBar.suggest(testo)                     migliori corrispondenze (funzione pura sui dati in cache)
 *   CmdBar.didYouMean(parola)                 il comando più vicino (distanza ≤ 2) o null
 *   CmdBar.close()                            chiude l'elenco
 *
 * Le frecce su/giù restano alla cronologia della pagina finché l'elenco è chiuso: il widget le intercetta
 * (fase di cattura) solo quando l'elenco è aperto.
 */
(function () {
  const MAX_CMD = 8;
  const MAX_ARG = 8;
  let data = { comandi: [], argomenti: {} };
  let opts = null;
  let box = null;
  let items = [];
  let sel = 0;
  let moved = false;
  let open = false;
  let blurTimer = 0;
  let loading = null;

  const norm = (s) => String(s == null ? "" : s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  function lev(a, b, max) {
    if (Math.abs(a.length - b.length) > max) return max + 1;
    let prev = new Array(b.length + 1);
    for (let j = 0; j <= b.length; j++) prev[j] = j;
    for (let i = 1; i <= a.length; i++) {
      const cur = [i];
      let best = i;
      for (let j = 1; j <= b.length; j++) {
        const v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
        cur[j] = v;
        if (v < best) best = v;
      }
      if (best > max) return max + 1;
      prev = cur;
    }
    return prev[b.length];
  }

  function subseq(q, s) {
    let i = 0;
    for (let k = 0; k < s.length && i < q.length; k++) if (s[k] === q[i]) i++;
    return i === q.length;
  }

  function resolveCmd(word) {
    const w = norm(word);
    for (const c of data.comandi || []) {
      if (norm(c.cmd) === w) return c;
      for (const a of c.alias || []) if (norm(a) === w) return c;
    }
    return null;
  }

  // punteggio di una parola contro un nome: più basso è meglio, null se non corrisponde
  function score(q, name) {
    if (name.startsWith(q)) return 0;
    if (name.indexOf(q) > 0) return 2;
    if (q.length >= 2 && subseq(q, name)) return 4;
    if (q.length >= 3) {
      const d = Math.min(lev(q, name, 2), lev(q, name.slice(0, q.length), 2));
      if (d <= 2) return 5 + d;
    }
    return null;
  }

  function suggestCommands(word) {
    const q = norm(word);
    const out = [];
    (data.comandi || []).forEach((c, idx) => {
      let best = null;
      let via = null;
      const names = [c.cmd].concat(c.alias || []);
      names.forEach((n, k) => {
        const s = score(q, norm(n));
        if (s == null) return;
        const adj = s + (k > 0 ? 1 : 0);
        if (best == null || adj < best) { best = adj; via = k > 0 ? n : null; }
      });
      if (best != null) out.push({ type: "cmd", cmd: c.cmd, args: c.args || "", desc: c.desc || "", cat: c.cat || "", via, rank: best, idx });
    });
    out.sort((a, b) => a.rank - b.rank || a.idx - b.idx);
    return out.slice(0, MAX_CMD).map((o) => { delete o.rank; delete o.idx; o.insert = o.cmd + " "; return o; });
  }

  function suggestArgs(first, last, head) {
    const c = resolveCmd(first);
    const list = c && data.argomenti ? data.argomenti[c.cmd] : null;
    if (!list || !list.length) return [];
    const q = norm(last);
    const out = [];
    list.forEach((e, idx) => {
      const v = norm(e.v);
      let r = null;
      if (!q) r = 1;
      else if (v.startsWith(q)) r = 0;
      else if (v.indexOf(q) > 0) r = 2;
      else if (norm(e.d).indexOf(q) >= 0) r = 3;
      if (r != null) out.push({ type: "arg", v: e.v, d: e.d || "", rank: r, idx });
    });
    out.sort((a, b) => a.rank - b.rank || a.idx - b.idx);
    return out.slice(0, MAX_ARG).map((o) => ({ type: "arg", v: o.v, d: o.d, insert: head + o.v + " " }));
  }

  function suggest(text) {
    const t = String(text == null ? "" : text).replace(/^\s+/, "");
    if (!t) return [];
    const m = /^(\S+)\s+(.*)$/.exec(t);
    if (!m) return suggestCommands(t);
    const rest = m[2];
    const cut = rest.lastIndexOf(" ") + 1;
    const head = t.slice(0, t.length - (rest.length - cut));
    return suggestArgs(m[1], rest.slice(cut), head);
  }

  function didYouMean(word) {
    const w = norm(word);
    if (!w) return null;
    let best = null;
    let bd = 3;
    for (const c of data.comandi || []) {
      for (const n of [c.cmd].concat(c.alias || [])) {
        const nn = norm(n);
        if (nn === w) return null;
        const d = lev(w, nn, 2);
        if (d < bd) { bd = d; best = c.cmd; }
      }
    }
    return bd <= 2 ? best : null;
  }

  function load() {
    if (!opts || !opts.fetchJSON) return Promise.resolve();
    loading = Promise.resolve(opts.fetchJSON("/api/comandi")).then((d) => {
      if (d && Array.isArray(d.comandi)) data = { comandi: d.comandi, argomenti: d.argomenti || {} };
    }).catch(() => { /* elenco non disponibile: nessun suggerimento */ });
    return loading;
  }

  function ensureBox() {
    if (box) return box;
    box = document.createElement("div");
    box.className = "cb-list";
    box.id = "cb-list";
    box.setAttribute("role", "listbox");
    box.setAttribute("aria-label", "Suggerimenti dei comandi");
    box.hidden = true;
    const host = opts.input.form || opts.input.parentElement;
    if (host && getComputedStyle(host).position === "static") host.style.position = "relative";
    host.appendChild(box);
    box.addEventListener("mousedown", (e) => e.preventDefault());
    box.addEventListener("click", (e) => {
      const row = e.target.closest(".cb-row");
      if (row) { sel = +row.dataset.i; complete(); opts.input.focus(); }
    });
    return box;
  }

  function paint() {
    ensureBox();
    box.textContent = "";
    items.forEach((it, i) => {
      const row = document.createElement("div");
      row.className = "cb-row" + (i === sel ? " cb-sel" : "");
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", i === sel ? "true" : "false");
      row.id = "cb-opt-" + i;
      row.dataset.i = String(i);
      const main = document.createElement("div");
      main.className = "cb-main";
      const b = document.createElement("b");
      b.textContent = it.type === "cmd" ? it.cmd : it.v;
      main.appendChild(b);
      if (it.type === "cmd" && it.args) {
        const a = document.createElement("span");
        a.className = "cb-args";
        a.textContent = it.args;
        main.appendChild(a);
      }
      if (it.via) {
        const v = document.createElement("span");
        v.className = "cb-via";
        v.textContent = "(" + it.via + ")";
        main.appendChild(v);
      }
      row.appendChild(main);
      const dsc = it.type === "cmd" ? it.desc : it.d;
      if (dsc) {
        const d = document.createElement("small");
        d.className = "cb-desc";
        d.textContent = dsc;
        row.appendChild(d);
      }
      box.appendChild(row);
    });
    opts.input.setAttribute("aria-activedescendant", "cb-opt-" + sel);
    const cur = box.children[sel];
    if (cur && cur.scrollIntoView) cur.scrollIntoView({ block: "nearest" });
  }

  function show() {
    items = suggest(opts.input.value);
    if (!items.length) { hide(); return; }
    if (sel >= items.length) sel = 0;
    open = true;
    paint();
    box.hidden = false;
    opts.input.setAttribute("aria-expanded", "true");
  }

  function hide() {
    open = false;
    moved = false;
    sel = 0;
    if (box) box.hidden = true;
    if (opts && opts.input) {
      opts.input.setAttribute("aria-expanded", "false");
      opts.input.removeAttribute("aria-activedescendant");
    }
  }

  function complete() {
    const it = items[sel];
    if (!it) return;
    const inp = opts.input;
    inp.value = it.insert;
    try { inp.setSelectionRange(inp.value.length, inp.value.length); } catch (e) { /* ignora */ }
    moved = false;
    sel = 0;
    inp.dispatchEvent(new Event("input", { bubbles: true }));
    if (opts.onPick) opts.onPick(inp.value);
  }

  function onKey(e) {
    if (!open) return;
    const inp = opts.input;
    const stop = () => { e.preventDefault(); e.stopImmediatePropagation(); };
    if (e.key === "ArrowDown") { stop(); sel = (sel + 1) % items.length; moved = true; paint(); }
    else if (e.key === "ArrowUp") { stop(); sel = (sel - 1 + items.length) % items.length; moved = true; paint(); }
    else if (e.key === "Tab" && !e.shiftKey) { stop(); complete(); }
    else if (e.key === "ArrowRight" && inp.selectionStart === inp.value.length && inp.selectionEnd === inp.value.length) { stop(); complete(); }
    else if (e.key === "Enter" && moved) { stop(); complete(); }
    else if (e.key === "Escape") { stop(); hide(); }
  }

  function init(o) {
    opts = o || {};
    if (!opts.input) return;
    const inp = opts.input;
    ensureBox();
    inp.setAttribute("autocomplete", "off");
    inp.setAttribute("role", "combobox");
    inp.setAttribute("aria-controls", "cb-list");
    inp.setAttribute("aria-expanded", "false");
    inp.setAttribute("aria-autocomplete", "list");
    inp.addEventListener("keydown", onKey, true);
    inp.addEventListener("input", () => {
      moved = false;
      sel = 0;
      if (!inp.value.trim()) hide(); else show();
    });
    inp.addEventListener("focus", () => { clearTimeout(blurTimer); if (inp.value.trim()) show(); });
    inp.addEventListener("blur", () => { blurTimer = setTimeout(hide, 120); });
    if (inp.form) inp.form.addEventListener("submit", hide);
    load();
  }

  function refresh() { return load(); }

  window.CmdBar = { init, refresh, suggest, didYouMean, close: hide };
})();
