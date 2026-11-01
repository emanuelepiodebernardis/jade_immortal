/* Aura — il ritratto dell'eroe «vivo»: respiro, battito di ciglia, anello di qi colorato dal Dao principale,
 * che cresce col regno (realmTier 1..12+).  Vanilla, nessuna dipendenza, mai lancia eccezioni.
 *
 *   Aura.apply(imgOrContainer, { dao, realmTier, combat })   idempotente: richiamarla aggiorna
 *   Aura.remove(el)                                          toglie tutto e rimette il DOM com'era
 *   Aura.enabled() / Aura.setEnabled(bool)                   localStorage "ji_aura" (default acceso)
 *   Aura.tierOf(regnoStr)                                    "Immortale di Giada · Strato 2/10" -> tier numerico stimato
 *
 * Se passi un <img> viene avvolto in uno span.aura-wrap; se passi un contenitore (es. .tkh del token
 * dell'eroe, o .pic) le luci vengono aggiunte dentro al contenitore e il respiro va sull'immagine al suo interno.
 */
(function () {
  "use strict";
  const KEY = "ji_aura";
  const PAL = {
    fuoco: ["#ff7a2a", "#c8281c", "#ffd08a"], acqua: ["#3a9bff", "#1450b8", "#a5dcff"], fulmine: ["#b58cff", "#5b34c9", "#f4eeff"],
    vento: ["#58d68a", "#1f9a5c", "#c9ffe0"], terra: ["#c99a4a", "#7d5520", "#f0d79b"], metallo: ["#cfd6df", "#7d8794", "#ffffff"],
    legno: ["#6fcf5e", "#2f7a2e", "#d7ffc4"], luce: ["#ffd75e", "#d49a14", "#fffbe0"], oscurita: ["#8a4fd0", "#1a0a2e", "#d3b0ff"],
    sangue: ["#e0334f", "#7c0f26", "#ffb3c0"], spazio: ["#6b7bff", "#2a2f9a", "#d0d6ff"], tempo: ["#e8b84a", "#8a5a14", "#fff0c4"],
    illusione: ["#e86bd0", "#7a1f78", "#ffd0f4"], karma: ["#e8b84a", "#8a3f14", "#ffe6b0"], creazione: ["#7be0b0", "#d4a83a", "#f6ffe0"],
    corpo: ["#d9863a", "#7d3a14", "#ffd9a8"], default: ["#3fbf8f", "#14694c", "#b8ffe3"],
    yinyang: ["#ffffff", "#0b0b0e", "#9aa0aa"], caos: ["#ff4d6d", "#4d7cff", "#ffe14d"], stelle: ["#aebcff", "#0a1030", "#fff3b0"], vuoto: ["#6a4a9c", "#050309", "#2a1a44"]
  };
  const ALIAS = { spada: "metallo", sciabola: "metallo", lancia: "metallo", tuono: "fulmine", ombra: "oscurita", massacro: "sangue",
    yinyang: "yinyang", yin: "yinyang", yang: "yinyang", stella: "stelle", anima: "default" };
  const RUNES = ["☰", "☱", "☲", "☳", "☴", "☵", "☶", "☷", "道", "天", "玄", "劍"];
  let on = true;
  try { on = localStorage.getItem(KEY) !== "0"; } catch (e) {}

  const norm = (s) => String(s == null ? "" : (typeof s === "object" ? (s.key || s.short || s.name || "") : s)).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^a-z]/g, "");
  function daoKey(d) {
    const k = norm(d);
    if (PAL[k]) return k;
    if (ALIAS[k]) return ALIAS[k];
    for (const p of Object.keys(PAL)) if (p !== "default" && k.includes(p)) return p;
    if (/yin|yang/.test(k)) return "yinyang";
    return "default";
  }
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  function mk(tag, cls, html) { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  // "Mortale / Raffinamento del Qi / Fondazione / ... / Immortale di Giada · Strato 2/10": stima grossolana
  const REALMS = ["mortale", "raffinamento", "fondazione", "nucleo", "anima nascente", "trasformazione", "unione", "grande veicolo", "tribolazione", "immortale", "venerabile", "sovrano", "supremo"];
  function tierOf(regno) {
    const s = String(regno || "").toLowerCase();
    let t = 1; REALMS.forEach((r, i) => { if (s.includes(r)) t = i + 1; });
    const m = s.match(/strato\s+(\d+)\s*\/\s*(\d+)/); if (m) t += 0.9 * (Number(m[1]) - 1) / Math.max(1, Number(m[2]) - 1);
    return Math.round(t * 10) / 10;
  }

  function build(st) {
    const { key, tier } = st, P = PAL[key] || PAL.default;
    const q = clamp((tier - 1) / 11, 0, 1);                       // 0..1
    const I = 0.1 + 0.9 * Math.pow(q, 0.8);                       // intensità
    const pad = 2 + q * 12;                                       // % di alone oltre il bordo
    const L = mk("div", "aura-layer aura-" + key);
    L.style.cssText = `--c1:${P[0]};--c2:${P[1]};--cg:${P[2]};--ai:${I.toFixed(3)};--pad:${pad.toFixed(1)}%;--q:${q.toFixed(3)}`;
    L.setAttribute("aria-hidden", "true");
    const back = mk("div", "aura-back"), ring = mk("div", "aura-ring"), glow = mk("div", "aura-glow");
    back.append(glow, ring);
    // lingue di qi: dal tier 4 in su, più numerose e alte salendo
    const nFl = tier < 3.5 ? 0 : clamp(Math.round(4 + q * 12), 5, 16);
    if (nFl) {
      const fl = mk("div", "aura-flames");
      for (let i = 0; i < nFl; i++) {
        const f = mk("i", "af", "<b></b>");
        f.style.cssText = `--th:${(i / nFl * 360 + (i % 2) * 9).toFixed(1)}deg;--d:${(-(i * 0.61) % 3.4).toFixed(2)}s;--h:${(0.7 + ((i * 37) % 10) / 14 + q * 0.55).toFixed(2)};--w:${(0.75 + ((i * 53) % 7) / 12).toFixed(2)}`;
        fl.appendChild(f);
      }
      back.appendChild(fl);
    }
    const front = mk("div", "aura-front");
    const nM = clamp(Math.round(2 + q * 8), 2, 10);
    const motes = mk("div", "aura-motes");
    for (let i = 0; i < nM; i++) {
      const m = mk("i", "am", "<b></b>");
      m.style.cssText = `--a0:${(i / nM * 360 + (i * 47) % 30).toFixed(0)}deg;--r:${(1.02 + ((i * 29) % 11) / 55).toFixed(2)};--s:${(0.5 + ((i * 17) % 8) / 8 * 0.9 + q * 0.5).toFixed(2)};--dur:${(7 + (i * 3) % 6 - q * 2).toFixed(1)}s;--alt:${i % 2 ? c(key, 1) : c(key, 0)}`;
      if (i % 2) m.classList.add("rev");
      motes.appendChild(m);
    }
    front.appendChild(motes);
    if (tier >= 8) {
      const nR = clamp(Math.round(6 + (tier - 8) * 1.2), 6, 12), rr = mk("div", "aura-runes");
      for (let i = 0; i < nR; i++) {
        const r = mk("i", "ar", `<b>${RUNES[(i * 5) % RUNES.length]}</b>`);
        r.style.setProperty("--a0", (i / nR * 360).toFixed(1) + "deg"); r.style.setProperty("--ri", String(0.55 + (i % 3) * 0.25));
        rr.appendChild(r);
      }
      front.appendChild(rr);
    }
    if (key === "yinyang") front.appendChild(mk("div", "aura-yy", "☯"));
    L.append(back, front);
    return L;
  }
  const c = (key, i) => { const P = PAL[key] || PAL.default; return i ? P[1] === "#0b0b0e" || key === "vuoto" ? P[0] : P[2] : P[2]; };

  function target(x) {
    if (!x || x.nodeType !== 1) return null;
    return x;
  }

  function apply(x, o) {
    try {
      x = target(x); if (!x) return null;
      o = o || {};
      let st = x._aura;
      const key = daoKey(o.dao), tier = clamp(Number(o.realmTier) || 1, 1, 14);
      if (!on) { remove(x); return null; }
      if (!st) {
        let host, img, wrapped = false;
        if (/^(IMG|SVG)$/i.test(x.tagName) || x.tagName === "svg") {
          img = x; const par = x.parentNode; if (!par) return null;
          if (par.classList && par.classList.contains("aura-wrap")) host = par;
          else {
            const cs = getComputedStyle(x), pr = par.getBoundingClientRect(), r = x.getBoundingClientRect();
            host = mk("span", "aura-wrap");
            const fill = pr.width && Math.abs(pr.width - r.width) < 1.5 && Math.abs(pr.height - r.height) < 1.5;
            host.style.display = cs.display === "inline" || cs.display === "inline-block" ? "inline-block" : "block";
            host.style.width = fill ? "100%" : r.width + "px"; host.style.height = fill ? "100%" : r.height + "px";
            host.style.borderRadius = cs.borderRadius; host.style.margin = cs.margin; host.style.flex = cs.flex;
            par.insertBefore(host, x); host.appendChild(x); wrapped = true;
            x.classList.add("aura-img-fill");
          }
        } else {
          host = x; img = x.querySelector("img.portrait, img, svg");
        }
        host.classList.add("aura-host");
        st = x._aura = { x, host, img, wrapped, layer: null, key: null, tier: null };
        host._auraSt = st;
        if (img) img.classList.add("aura-live");
      }
      if (st.layer && (st.key !== key || Math.abs(st.tier - tier) > 0.05)) { st.layer.remove(); st.layer = null; }
      st.key = key; st.tier = tier;
      if (!st.layer) { st.layer = build(st); st.host.insertBefore(st.layer, st.host.firstChild); }
      st.host.classList.toggle("aura-combat", !!o.combat);
      st.host.classList.toggle("aura-lowtier", tier < 3);
      st.host.dataset.aura = key;
      return st.host;
    } catch (e) { try { console.error("Aura", e); } catch (_) {} return null; }
  }

  function remove(x) {
    try {
      x = target(x); const st = x && (x._aura || x._auraSt); if (!st) return;
      if (st.layer) st.layer.remove();
      st.host.classList.remove("aura-host", "aura-combat", "aura-lowtier"); delete st.host.dataset.aura;
      if (st.img) st.img.classList.remove("aura-live", "aura-img-fill");
      if (st.wrapped && st.host.parentNode && st.img) { st.host.parentNode.insertBefore(st.img, st.host); st.host.remove(); }
      delete st.x._aura; delete st.host._auraSt;
    } catch (e) { try { console.error("Aura", e); } catch (_) {} }
  }

  function setEnabled(v) {
    on = !!v; try { localStorage.setItem(KEY, on ? "1" : "0"); } catch (e) {}
    if (!on) document.querySelectorAll(".aura-host").forEach((h) => h._auraSt && remove(h._auraSt.x));
  }

  window.Aura = { apply, remove, enabled: () => on, setEnabled, tierOf, PALETTE: PAL, daoKey };
})();
