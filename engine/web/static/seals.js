/* Jade Immortal — sigilli rossi (印章) in SVG inline.
   API: Seals.html(testo, {size, tone:'red'|'gold'|'jade', rotate}) -> stringa SVG
        Seals.el(testo, opts) -> elemento · Seals.stamp(el, testo, opts) -> appone il sigillo all'angolo di el con l'animazione
        Seals.remove(el) · Seals.forTitle(titolo) -> 1-2 hanzi scelti dal significato del titolo */
(function () {
  "use strict";

  var TONES = {
    red:  { fill: "#c3321f", edge: "#8f2012", glow: "rgba(195,50,31,.45)" },
    gold: { fill: "#c79a36", edge: "#8d6a16", glow: "rgba(199,154,54,.45)" },
    jade: { fill: "#2e9b76", edge: "#1b6a50", glow: "rgba(46,155,118,.45)" }
  };
  var uid = 0;

  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function isHan(ch) { return /[\u3400-\u9fff\uf900-\ufaff]/.test(ch); }

  // disposizione dei caratteri nella griglia 100x100: colonne da destra a sinistra, dall'alto in basso
  function layout(chars) {
    var n = chars.length, cells = [];
    if (n === 1) cells.push([50, 52, 66]);
    else if (n === 2) cells.push([50, 31, 44], [50, 71, 44]);
    else if (n === 3) cells.push([70, 31, 40], [70, 71, 40], [30, 51, 40]);
    else cells.push([70, 31, 40], [70, 71, 40], [30, 31, 40], [30, 71, 40]);
    return chars.map(function (c, i) { return { c: c, x: cells[i][0], y: cells[i][1], s: cells[i][2] }; });
  }

  function html(text, opts) {
    opts = opts || {};
    var tone = TONES[opts.tone] || TONES.red, size = opts.size || 44;
    var rot = opts.rotate == null ? -4 : opts.rotate;
    var chars = Array.from(String(text == null || text === "" ? "印" : text)).filter(function (c) { return !/\s/.test(c); }).slice(0, 4);
    if (!chars.length) chars = ["印"];
    var id = "sl" + (++uid), cells = layout(chars), seed = (uid * 7) % 90 + 3;
    var glyphs = cells.map(function (k) {
      var han = isHan(k.c);
      var fs = han ? k.s : Math.round(k.s * 0.92);
      return '<text x="' + k.x + '" y="' + k.y + '" font-size="' + fs + '" text-anchor="middle" dominant-baseline="central" fill="#000"' +
        ' font-family="' + (han ? "'Ma Shan Zheng','Kaiti SC','STKaiti','KaiTi','Noto Serif CJK SC',serif" : "'Cormorant Garamond','Iowan Old Style',Georgia,serif") + '"' +
        ' font-weight="' + (han ? 400 : 700) + '">' + esc(k.c) + "</text>";
    }).join("");
    return '<svg class="seal seal-' + (opts.tone && TONES[opts.tone] ? opts.tone : "red") + (opts.cls ? " " + esc(opts.cls) : "") + '" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="' + size + '" height="' + size +
      '" role="img" aria-label="Sigillo: ' + esc(chars.join("")) + '" style="display:inline-block;vertical-align:middle;flex:none;overflow:visible;transform:rotate(' + rot + 'deg);filter:drop-shadow(0 1px 1.5px ' + tone.glow + ')">' +
      "<defs>" +
      '<filter id="' + id + 'f" x="-8%" y="-8%" width="116%" height="116%" color-interpolation-filters="sRGB">' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.045" numOctaves="2" seed="' + seed + '" result="n1"/>' +
      '<feDisplacementMap in="SourceGraphic" in2="n1" scale="4.2" xChannelSelector="R" yChannelSelector="G" result="d"/>' +
      '<feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="1" seed="' + (seed + 11) + '" result="n2"/>' +
      '<feColorMatrix in="n2" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -14 10.1" result="holes"/>' +
      '<feComposite in="d" in2="holes" operator="in"/></filter>' +
      '<mask id="' + id + 'm" maskUnits="userSpaceOnUse" x="0" y="0" width="100" height="100">' +
      '<rect x="0" y="0" width="100" height="100" fill="#fff"/>' +
      '<rect x="7.500" y="7.500" width="85" height="85" rx="3" fill="none" stroke="#000" stroke-width="2.600"/>' + glyphs + "</mask></defs>" +
      '<g filter="url(#' + id + 'f)"><rect x="3" y="3" width="94" height="94" rx="6" fill="' + tone.fill + '" mask="url(#' + id + 'm)"/>' +
      '<rect x="3" y="3" width="94" height="94" rx="6" fill="none" stroke="' + tone.edge + '" stroke-width="1.400" opacity=".55"/></g></svg>';
  }

  function el(text, opts) {
    var h = document.createElement("span");
    h.innerHTML = html(text, opts);
    return h.firstChild;
  }

  var reduce = function () { try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; } };

  function remove(host) {
    if (!host || !host.querySelectorAll) return;
    Array.prototype.forEach.call(host.querySelectorAll(":scope > .seal-stamp"), function (n) { n.remove(); });
  }

  /* appone il sigillo all'angolo dell'elemento e lo lascia lì */
  function stamp(host, text, opts) {
    opts = opts || {};
    if (!host || !host.appendChild) return null;
    remove(host);
    try { if (getComputedStyle(host).position === "static") host.style.position = "relative"; } catch (e) { /* ignora */ }
    var size = opts.size || 44, corner = opts.corner || "tr", off = opts.offset == null ? 6 : opts.offset;
    var wrap = document.createElement("span");
    wrap.className = "seal-stamp";
    var st = wrap.style;
    st.position = "absolute"; st.pointerEvents = "none"; st.zIndex = opts.z || 5; st.width = st.height = size + "px"; st.lineHeight = "0";
    st[corner.indexOf("t") >= 0 ? "top" : "bottom"] = off + "px";
    st[corner.indexOf("l") >= 0 ? "left" : "right"] = off + "px";
    var svg = el(text, opts);
    svg.style.width = svg.style.height = "100%";
    var tone = TONES[opts.tone] || TONES.red;
    var ink = document.createElement("span");
    ink.className = "seal-ink";
    ink.style.cssText = "position:absolute;inset:-6px;border-radius:50%;pointer-events:none;opacity:0;background:radial-gradient(circle," + tone.glow + " 0%,transparent 68%)";
    wrap.appendChild(ink); wrap.appendChild(svg);
    host.appendChild(wrap);
    var rot = opts.rotate == null ? -4 : opts.rotate;
    if (!reduce() && wrap.animate && opts.animate !== false) {
      svg.animate([
        { transform: "scale(1.6) rotate(" + (rot + 9) + "deg)", opacity: 0, filter: "blur(3px)" },
        { transform: "scale(0.93) rotate(" + (rot - 1) + "deg)", opacity: 1, filter: "blur(0.4px)", offset: 0.62 },
        { transform: "scale(1) rotate(" + rot + "deg)", opacity: 1, filter: "blur(0)" }
      ], { duration: 450, easing: "cubic-bezier(.2,.8,.25,1)", fill: "backwards" });
      ink.animate([{ opacity: 0, transform: "scale(.6)" }, { opacity: 0.9, transform: "scale(1.05)", offset: 0.6 }, { opacity: 0, transform: "scale(1.5)" }],
        { duration: 650, easing: "ease-out", delay: 180, fill: "backwards" });
    }
    return wrap;
  }

  /* parole italiane -> hanzi (forme semplificate, coperte dal carattere impacchettato) */
  var MAP = [
    [/\bdrag/, "龙"], [/\bspad|\blam[ae]\b|\bsciabol/, "剑"], [/\bciel|\bcelest|\bparadis/, "天"], [/\bre\b|\bregin|\bimperat|\bsovran|\bregno|\bregal/, "王"],
    [/\bimmortal|\bascesi|\bascend/, "仙"], [/\bdao\b|\bvia\b|\bsentier/, "道"], [/\bfuoc|\bfiamm|\bardent|\binfern/, "火"], [/\bacqu|\bmare\b|\boceano|\bfium|\blago/, "水"],
    [/\bmort|\bmorte|\bmorti|\bfunebr|\bcadaver/, "死"], [/\bvita\b|\bvivent|\bnascit|\brinasc/, "生"], [/\banim|\bspettr|\bfantasm/, "魂"],
    [/\bfondator|\bpadre|\bantenat|\bprogenitor|\bpatriarc|\bavo\b/, "祖"], [/\bprescelt|\beletto|\bscelto/, "选"],
    [/\btigr/, "虎"], [/\bghiacc|\bgelo|\binvern/, "冰"], [/\btuon|\bfulmin|\btempest/, "雷"], [/\bvent/, "风"], [/\bterra\b|\bterren|\bsuolo/, "土"],
    [/\blegn|\bforesta|\bbosco|\balber/, "木"], [/\bmetall|\boro\b|\bferro|\bacciaio/, "金"], [/\bsangu/, "血"], [/\bspirit|\bnume\b/, "灵"],
    [/\bgiada|\bgioiell/, "玉"], [/\bmont|\bpicco|\bvetta/, "山"], [/\bvelen|\btossic/, "毒"], [/\bdemon|\bmalefic|\bdiavol/, "魔"],
    [/\bsant|\bsacr|\bdivin/, "圣"], [/\bdio\b|\bdivinit/, "神"], [/\bfenice|\bfenicott/, "凤"], [/\bvolpe/, "狐"], [/\bstell/, "星"],
    [/\bnuvol|\bnube/, "云"], [/\bpiogg/, "雨"], [/\bneve/, "雪"], [/\bfior/, "花"], [/\bpozion|\belisir|\bmedic|\bguarigion/, "药"], [/\bsigill|\bsimbol/, "印"],
    [/\bmaestr|\bsensei|\bmentor/, "师"], [/\bsetta|\bclan\b|\bsocieta/, "宗"], [/\bcuore/, "心"], [/\btribolaz|\bcalamit|\bdisastr/, "劫"]
  ];
  function forTitle(title) {
    var s = String(title == null ? "" : title).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ");
    s = " " + s.trim() + " ";
    var found = [], pos = [];
    MAP.forEach(function (m) {
      var r = new RegExp(m[0].source.replace(/\\b/g, "(?:^|\\s)"));
      var k = s.search(r);
      if (k >= 0 && found.indexOf(m[1]) < 0) { found.push(m[1]); pos.push(k); }
    });
    var order = found.map(function (c, i) { return { c: c, p: pos[i] }; }).sort(function (a, b) { return a.p - b.p; });
    var out = order.slice(0, 2).map(function (o) { return o.c; }).join("");
    return out || "印";
  }

  window.Seals = { html: html, el: el, stamp: stamp, remove: remove, forTitle: forTitle };
})();
