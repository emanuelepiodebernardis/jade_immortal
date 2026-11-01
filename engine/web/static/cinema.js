/* Cinema: sequenze cinematografiche a tutto schermo, procedurali (CSS, SVG, canvas). API: window.Cinema */
(function () {
  "use strict";

  var LS_KEY = "ji_cinema", MAX_QUEUE = 3;
  var SVGNS = "http://www.w3.org/2000/svg";
  var queue = [], cur = null;

  /* ---------- preferenze ---------- */
  function reduced() { try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch (e) { return false; } }
  function enabled() {
    try { var v = localStorage.getItem(LS_KEY); if (v === "1") return true; if (v === "0") return false; } catch (e) {}
    return !reduced();
  }
  function setEnabled(b) { try { localStorage.setItem(LS_KEY, b ? "1" : "0"); } catch (e) {} if (!b) cancelAll(); return !!b; }

  /* ---------- utilita ---------- */
  function el(tag, cls, parent, html) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    if (parent) parent.appendChild(n);
    return n;
  }
  function svg(tag, attrs, parent) {
    var n = document.createElementNS(SVGNS, tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  function ease(p) { p = clamp(p, 0, 1); return p * p * (3 - 2 * p); }
  function easeIn3(p) { p = clamp(p, 0, 1); return p * p * p; }
  function easeOut3(p) { p = clamp(p, 0, 1); return 1 - Math.pow(1 - p, 3); }
  function rnd(a, b) { return a + Math.random() * (b - a); }
  function hash(s) { var h = 7; s = String(s || ""); for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0; return h; }
  function small() { return Math.min(window.innerWidth, window.innerHeight) < 520; }
  function cap(s) { s = String(s || "").trim(); return s ? s.charAt(0).toUpperCase() + s.slice(1) : s; }

  function ambient(name) { try { if (window.Ambient && Ambient.cuesOn && Ambient.cuesOn()) Ambient.cue(name); } catch (e) {} }
  function narrate(text) { try { if (window.Narrator && Narrator.on && Narrator.on()) Narrator.say(text); } catch (e) {} }

  /* ---------- canvas ---------- */
  function makeCanvas(parent, env) {
    var c = el("canvas", "cin-canvas", parent);
    var o = { c: c, x: c.getContext("2d"), w: 0, h: 0 };
    function fit() {
      var d = Math.min(window.devicePixelRatio || 1, 2);
      o.w = parent.clientWidth || window.innerWidth; o.h = parent.clientHeight || window.innerHeight;
      c.width = Math.round(o.w * d); c.height = Math.round(o.h * d);
      o.x.setTransform(d, 0, 0, d, 0, 0);
    }
    fit();
    window.addEventListener("resize", fit);
    env.cleanups.push(function () { window.removeEventListener("resize", fit); c.width = c.height = 0; });
    return o;
  }

  /* ---------- scene ---------- */
  var SCENES = {};

  // Sfondamento
  SCENES.sfondamento = function (env) {
    var d = env.data, st = env.stage;
    var main = cap(d.regno || d.nome || "Nuovo regno");
    var subParts = [];
    if (d.strato != null && d.strato !== "") subParts.push("Strato " + d.strato);
    if (d.nome && d.regno && String(d.nome).toLowerCase() !== String(d.regno).toLowerCase()) subParts.push(d.nome);
    var sub = subParts.length ? subParts.join("  ·  ") : "Il tuo Qi si è fatto più profondo";
    env.headline = "Sfondamento. " + main + (subParts.length ? ". " + subParts.join(", ") : "");

    el("div", "cin-sky", st);
    var cv = makeCanvas(st, env);
    el("div", "cin-vig", st);
    var hz = el("div", "cin-hanzi", st, "境"); hz.style.setProperty("--d", "2.3s"); hz.className += " cin-show";
    var flash = el("div", "cin-flash", st);
    var box = el("div", "cin-center", st);
    var k = el("div", "cin-kicker cin-in", box, "Sfondamento"); k.style.setProperty("--d", "2.6s");
    var t = el("div", "cin-title cin-in", box, esc(main)); t.style.setProperty("--d", "2.45s");
    var r = el("div", "cin-rule cin-in", box); r.style.setProperty("--d", "3.0s");
    var s = el("div", "cin-sub cin-in", box, esc(sub)); s.style.setProperty("--d", "3.2s");

    var n = small() ? 130 : 240, P = [];
    for (var i = 0; i < n; i++) P.push({ a: rnd(0, 6.283), r: rnd(.28, 1.0), dl: rnd(0, .38), sz: rnd(.8, 2.2), g: Math.random() < .28, w: rnd(2.6, 5.2) });
    var CONV = 2300;
    var sparks = [];
    for (i = 0; i < 70; i++) sparks.push({ a: rnd(0, 6.283), v: rnd(.25, 1), sz: rnd(.8, 2.4) });

    env.at(2250, function () { flash.className = "cin-flash cin-go"; ambient("sfondamento"); });
    env.at(300, function () { narrate("Sfondamento. " + main); });
    env.draw(function (tm) {
      var x = cv.x, W = cv.w, H = cv.h, cx = W / 2, cy = H / 2, R = Math.hypot(W, H) / 2;
      x.clearRect(0, 0, W, H);
      x.globalCompositeOperation = "lighter";
      var base = clamp((tm - 250) / (CONV - 250), 0, 1);
      if (tm < CONV + 200) {
        // alone che cresce al centro
        var gr = 20 + 140 * easeIn3(base);
        var g = x.createRadialGradient(cx, cy, 0, cx, cy, gr * 1.8);
        g.addColorStop(0, "rgba(255,244,205," + (.15 + .75 * base) + ")"); g.addColorStop(.4, "rgba(226,191,106," + (.25 * base) + ")"); g.addColorStop(1, "rgba(226,191,106,0)");
        x.fillStyle = g; x.beginPath(); x.arc(cx, cy, gr * 1.8, 0, 6.283); x.fill();
        x.lineCap = "round";
        for (var i = 0; i < P.length; i++) {
          var q = P[i], p = clamp((tm - 250 - q.dl * 900) / (CONV - 250 - 900 * .4), 0, 1);
          if (p <= 0 || p >= 1) continue;
          var pos = function (pp) {
            var e = easeIn3(pp) * .9 + pp * .1, rr = q.r * R * .62 * (1 - e) + 4, aa = q.a + (e * 7.5) + (1 - q.r) * 2;
            return [cx + Math.cos(aa) * rr, cy + Math.sin(aa) * rr * .86];
          };
          var a0 = pos(Math.max(0, p - .09)), a1 = pos(p), al = Math.min(1, p * 4) * (1 - p * .25);
          x.strokeStyle = q.g ? "rgba(140,235,200," + (al * .85) + ")" : "rgba(255,226,150," + (al * .9) + ")";
          x.lineWidth = q.sz * (1 + p);
          x.beginPath(); x.moveTo(a0[0], a0[1]); x.lineTo(a1[0], a1[1]); x.stroke();
        }
      }
      if (tm > 2250) {
        var pr = clamp((tm - 2250) / 1700, 0, 1), eo = easeOut3(pr), fade = 1 - pr;
        x.strokeStyle = "rgba(255,236,170," + (.8 * fade) + ")"; x.lineWidth = 2.2 * fade + .4;
        x.beginPath(); x.arc(cx, cy, eo * R * .95, 0, 6.283); x.stroke();
        x.strokeStyle = "rgba(140,235,200," + (.5 * fade) + ")"; x.lineWidth = 1.2;
        x.beginPath(); x.arc(cx, cy, eo * R * .6, 0, 6.283); x.stroke();
        for (var j = 0; j < sparks.length; j++) {
          var sp = sparks[j], rr2 = easeOut3(pr * sp.v + .02) * R * .75 * sp.v;
          x.fillStyle = "rgba(255,232,160," + (.8 * fade) + ")";
          x.beginPath(); x.arc(cx + Math.cos(sp.a) * rr2, cy + Math.sin(sp.a) * rr2, sp.sz, 0, 6.283); x.fill();
        }
      }
      x.globalCompositeOperation = "source-over";
    });
    return { dur: 4600 };
  };

  // Tribolazione
  SCENES.tribolazione = function (env) {
    var d = env.data, st = env.stage;
    var N = clamp(parseInt(d.fulmini, 10) || 9, 1, 99), ok = d.esito !== "fallita";
    env.headline = "Tribolazione " + (ok ? "superata" : "fallita");

    el("div", "cin-storm", st);
    el("div", "cin-cloud c3", st); el("div", "cin-cloud c1", st); el("div", "cin-cloud c2", st);
    el("div", "cin-clear " + (ok ? "ok" : "ko"), st);
    el("div", "cin-ground", st);
    var fg = el("div", "cin-figure", st,
      '<svg viewBox="0 0 120 80" xmlns="' + SVGNS + '"><g fill="#020305"><circle cx="60" cy="26" r="9"/><path d="M60 36 C44 38 34 54 28 74 L92 74 C86 54 76 38 60 36Z"/><path d="M20 76 C34 66 86 66 100 76 L100 80 L20 80Z"/></g></svg>');
    el("div", "cin-vig", st);
    var bf = el("div", "cin-bflash", st), boltLayer = el("div", "cin-layer", st);
    var cnt = el("div", "cin-count", st, "Fulmine <b>0</b>/" + N), cb = cnt.querySelector("b");
    var verdict = el("div", "cin-center cin-verdict", st);
    var shakeTarget = st;

    function jag(x0, y0, x1, y1, amp, steps) {
      var pts = [[x0, y0]];
      for (var i = 1; i < steps; i++) {
        var f = i / steps;
        pts.push([x0 + (x1 - x0) * f + rnd(-amp, amp) * (1 - f * .3), y0 + (y1 - y0) * f + rnd(-amp * .25, amp * .25)]);
      }
      pts.push([x1, y1]);
      return pts;
    }
    function pathOf(p) { return "M" + p.map(function (q) { return q[0].toFixed(1) + " " + q[1].toFixed(1); }).join("L"); }

    function bolt(i, last) {
      var W = st.clientWidth, H = st.clientHeight;
      var x0 = rnd(.15, .85) * W, x1 = clamp(x0 + rnd(-.18, .18) * W, W * .08, W * .92), y1 = rnd(.62, .84) * H;
      if (last) { x1 = W * .5; x0 = W * .5 + rnd(-.08, .08) * W; y1 = H * .8; }
      var main = jag(x0, -10, x1, y1, W * (small() ? .05 : .035), 16);
      var s = svg("svg", { "class": "cin-bolt" + (!ok && last ? " red" : ""), width: W, height: H, viewBox: "0 0 " + W + " " + H }, boltLayer);
      var col = !ok && last ? "#ffe3e0" : "#f4f9ff";
      svg("path", { d: pathOf(main), fill: "none", stroke: col, "stroke-width": last ? 5 : 3.2, "stroke-linejoin": "round", "stroke-linecap": "round" }, s);
      svg("path", { d: pathOf(main), fill: "none", stroke: "#fff", "stroke-width": last ? 2 : 1.2, "stroke-linejoin": "round" }, s);
      var nb = Math.floor(rnd(2, 4));
      for (var b = 0; b < nb; b++) {
        var m = main[Math.floor(rnd(3, main.length - 3))], dir = Math.random() < .5 ? -1 : 1;
        var br = jag(m[0], m[1], m[0] + dir * rnd(.06, .16) * W, m[1] + rnd(.12, .26) * H, W * .02, 7);
        svg("path", { d: pathOf(br), fill: "none", stroke: col, "stroke-width": 1.6, "stroke-linejoin": "round", opacity: .8 }, s);
      }
      env.later(function () { if (s.parentNode) s.parentNode.removeChild(s); }, 700);
      bf.className = "cin-bflash" + (!ok && last ? " red" : ""); void bf.offsetWidth; bf.className += " cin-go";
      shakeTarget.classList.remove("cin-shake"); void shakeTarget.offsetWidth; shakeTarget.classList.add("cin-shake");
      cb.textContent = String(i + 1);
      ambient("fulmine");
    }
    var t0 = 550, span = 3100, step = span / N;
    for (var i = 0; i < N; i++) (function (i) { env.at(t0 + i * step, function () { bolt(i, i === N - 1); }); })(i);

    env.at(t0 + span + 250, function () {
      cnt.style.transition = "opacity .5s"; cnt.style.opacity = ".0"; cnt.style.animation = "none";
      st.querySelector(".cin-clear").classList.add("on");
      fg.style.transition = "opacity 1s"; fg.style.opacity = ok ? ".95" : ".5";
      verdict.innerHTML = "";
      var k = el("div", "cin-kicker cin-in" + (ok ? "" : " ko"), verdict, ok ? "Il cielo si placa" : "Il Cielo ti ha rifiutato"); k.style.setProperty("--d", ".1s");
      var t = el("div", "cin-title cin-in " + (ok ? "ok" : "ko"), verdict, ok ? "Tribolazione superata" : "Tribolazione fallita"); t.style.setProperty("--d", ".25s");
      ambient(ok ? "campana" : "fulmine");
      narrate(ok ? "Tribolazione superata." : "Tribolazione fallita.");
    });
    return { dur: 5300 };
  };

  // Fusione
  var SEAL_MAP = [
    ["fuoco", "火"], ["fiamm", "火"], ["acqua", "水"], ["vapore", "汽"], ["legno", "木"], ["terra", "土"], ["metall", "金"], ["ghiacc", "冰"], ["vento", "風"],
    ["fulmin", "雷"], ["tuono", "雷"], ["ombra", "影"], ["luce", "光"], ["spada", "劍"], ["vuoto", "虛"], ["vita", "生"], ["morte", "死"], ["sangue", "血"],
    ["temp", "時"], ["spazio", "空"], ["nebbia", "霧"], ["sabbia", "沙"], ["lava", "熔"], ["luna", "月"], ["sole", "日"], ["stell", "星"], ["drago", "龍"], ["tigre", "虎"],
    ["fenice", "凰"], ["loto", "蓮"], ["giada", "玉"], ["cielo", "天"], ["mare", "海"], ["monte", "山"], ["montagna", "山"], ["pioggia", "雨"], ["sogno", "夢"]
  ];
  function sealChar(d) {
    if (d.char) return String(d.char).charAt(0);
    var s = String((d.nome || "") + " " + (d.a || "") + " " + (d.b || "")).toLowerCase();
    for (var i = 0; i < SEAL_MAP.length; i++) if (s.indexOf(SEAL_MAP[i][0]) >= 0) return SEAL_MAP[i][1];
    return "道";
  }

  SCENES.fusione = function (env) {
    var d = env.data, st = env.stage;
    var nome = String(d.nome || "Via nuova"), A = d.a || "", B = d.b || "";
    env.headline = "Fusione. Nasce " + nome;
    var h1 = A ? hash(A) % 360 : 190, h2 = B ? hash(B) % 360 : 18;
    if (Math.abs(((h1 - h2 + 540) % 360) - 180) < 70) h2 = (h1 + 150) % 360;

    el("div", "cin-fus-bg", st);
    var cv = makeCanvas(st, env);
    el("div", "cin-vig", st);
    var flash = el("div", "cin-flash", st);
    var box = el("div", "cin-center", st);
    var sealWrap = el("div", "cin-seal", box);
    var ch = sealChar(d), sealHtml = null;
    try { if (window.Seals && Seals.html) sealHtml = Seals.html(ch, { size: 120 }); } catch (e) { sealHtml = null; }
    if (sealHtml) sealWrap.innerHTML = sealHtml; else el("div", "cin-seal-fb", sealWrap, esc(ch));
    var k = el("div", "cin-kicker cin-in", box, "Nasce una via nuova"); k.style.setProperty("--d", "3.15s");
    var t = el("div", "cin-title cin-in", box, esc(nome)); t.style.setProperty("--d", "3.0s");
    var r = el("div", "cin-rule cin-in", box); r.style.setProperty("--d", "3.5s");
    if (A || B) { var p = el("div", "cin-sub cin-in", box); p.innerHTML = '<span class="cin-pair"><span>' + esc(A || "Qi") + "</span><i>✦</i><span>" + esc(B || "Qi") + "</span></span>"; p.style.setProperty("--d", "3.6s"); }

    var n = small() ? 70 : 120, S = [];
    for (var s = 0; s < 2; s++) for (var i = 0; i < n; i++) S.push({ s: s, dl: rnd(0, .5), j: rnd(-1, 1), sz: rnd(.9, 2.4), off: rnd(0, 1) });
    var MERGE = 2500;
    function col(h, a, l) { return "hsla(" + h + ",90%," + (l || 62) + "%," + a + ")"; }

    env.at(MERGE - 80, function () { flash.className = "cin-flash cin-go"; ambient("fusione"); });
    env.at(MERGE + 120, function () { sealWrap.classList.add("cin-go"); ambient("campana"); });
    env.at(2900, function () { narrate("Fusione. Nasce " + nome); });

    env.draw(function (tm) {
      var x = cv.x, W = cv.w, H = cv.h, cx = W / 2, cy = H * (tm > MERGE ? .42 : .5), R = Math.min(W, H) * .46;
      x.clearRect(0, 0, W, H);
      x.globalCompositeOperation = "lighter"; x.lineCap = "round";
      var base = clamp((tm - 200) / (MERGE - 200), 0, 1);
      if (tm < MERGE + 300) {
        for (var i = 0; i < S.length; i++) {
          var q = S[i], p = clamp((tm - 200 - q.dl * 800) / (MERGE - 200 - 800 * .5), 0, 1);
          if (p <= 0) continue;
          var hue = q.s ? h2 : h1;
          var pos = function (pp) {
            var e = easeIn3(pp) * .7 + pp * .3, rr = R * (1 - e) * (1 + q.j * .12 * (1 - e)) + 3 + q.j * 8 * (1 - pp), aa = (q.s ? Math.PI : 0) + e * 9.4 + q.j * .12;
            return [cx + Math.cos(aa) * rr, cy + Math.sin(aa) * rr * .8];
          };
          var a0 = pos(Math.max(0, p - .1)), a1 = pos(Math.min(p, 1)), al = Math.min(1, p * 5) * (p >= 1 ? Math.max(0, 1 - (tm - MERGE) / 300) : 1);
          if (al <= 0) continue;
          x.strokeStyle = col(hue, al * .85); x.lineWidth = q.sz * (1 + p * .6);
          x.beginPath(); x.moveTo(a0[0], a0[1]); x.lineTo(a1[0], a1[1]); x.stroke();
        }
        // nuclei dei due flussi che si avvicinano
        var gr = 28 + 90 * easeIn3(base);
        var g = x.createRadialGradient(cx, cy, 0, cx, cy, gr * 1.6);
        g.addColorStop(0, "rgba(255,248,225," + (.12 + .8 * base) + ")"); g.addColorStop(.35, col(h1, .3 * base)); g.addColorStop(.65, col(h2, .24 * base)); g.addColorStop(1, "rgba(0,0,0,0)");
        x.fillStyle = g; x.beginPath(); x.arc(cx, cy, gr * 1.6, 0, 6.283); x.fill();
      }
      if (tm > MERGE - 80) {
        var pr = clamp((tm - MERGE + 80) / 1600, 0, 1), fd = 1 - pr, eo = easeOut3(pr);
        x.lineWidth = 2 * fd + .5;
        x.strokeStyle = col(h1, .7 * fd); x.beginPath(); x.arc(cx, cy, eo * R * 1.1, 0, 6.283); x.stroke();
        x.strokeStyle = col(h2, .7 * fd); x.beginPath(); x.arc(cx, cy, eo * R * .8, 0, 6.283); x.stroke();
      }
      x.globalCompositeOperation = "source-over";
    });
    return { dur: 4700 };
  };

  // Morte
  SCENES.morte = function (env) {
    var d = env.data, st = env.stage;
    var nome = d.nome || "", eta = d.eta;
    env.headline = "Fine di una vita" + (nome ? ". " + nome : "");
    st.classList.add("cin-death");
    // filtro inchiostro irregolare
    var defs = svg("svg", { width: 0, height: 0, "aria-hidden": "true", style: "position:absolute" }, st);
    var f = svg("filter", { id: "cin-inkf", x: "-30%", y: "-30%", width: "160%", height: "160%" }, defs);
    svg("feTurbulence", { type: "fractalNoise", baseFrequency: ".012", numOctaves: "3", seed: String(1 + (hash(nome) % 40)), result: "n" }, f);
    svg("feDisplacementMap", { "in": "SourceGraphic", in2: "n", scale: small() ? "90" : "170", xChannelSelector: "R", yChannelSelector: "G" }, f);
    el("div", "cin-grey", st);
    el("div", "cin-paper", st);
    el("div", "cin-drop", st);
    el("div", "cin-ink", st);
    el("div", "cin-vig", st);
    var box = el("div", "cin-center", st);
    var k = el("div", "cin-kicker cin-in", box, "Il filo si spezza"); k.style.setProperty("--d", "2.6s");
    var t = el("div", "cin-title cin-in", box, "Fine di una vita"); t.style.setProperty("--d", "2.8s");
    var r = el("div", "cin-rule cin-in", box); r.style.setProperty("--d", "3.3s");
    var line = (nome ? nome : "") + (nome && eta != null && eta !== "" ? "  ·  " : "") + (eta != null && eta !== "" ? "a " + eta + " anni" : "");
    if (line) { var s = el("div", "cin-sub cin-in", box, esc(line)); s.style.setProperty("--d", "3.4s"); }
    env.at(500, function () { ambient("campana"); });
    env.at(2700, function () { narrate("Fine di una vita." + (nome ? " " + nome + "." : "")); });
    return { dur: 4800 };
  };

  // Rinascita (ruota del Samsara)
  SCENES.rinascita = function (env) {
    var st = env.stage;
    env.headline = "Rinascita";
    el("div", "cin-reb-bg", st);
    el("div", "cin-rays", st);
    el("div", "cin-bloom", st);
    var wh = el("div", "cin-wheel", st);
    var s = svg("svg", { viewBox: "0 0 200 200", fill: "none", stroke: "currentColor", "stroke-linecap": "round" }, wh);
    svg("circle", { cx: 100, cy: 100, r: 92, "stroke-width": 2.4 }, s);
    svg("circle", { cx: 100, cy: 100, r: 84, "stroke-width": .8, "stroke-dasharray": "2 5" }, s);
    svg("circle", { cx: 100, cy: 100, r: 30, "stroke-width": 1.6 }, s);
    svg("circle", { cx: 100, cy: 100, r: 12, "stroke-width": 2.2, fill: "currentColor", "fill-opacity": .25 }, s);
    for (var i = 0; i < 8; i++) {
      var a = i * Math.PI / 4, c = Math.cos(a), sn = Math.sin(a);
      svg("line", { x1: 100 + c * 30, y1: 100 + sn * 30, x2: 100 + c * 84, y2: 100 + sn * 84, "stroke-width": 3 }, s);
      svg("circle", { cx: 100 + c * 92, cy: 100 + sn * 92, r: 5, fill: "currentColor", stroke: "none" }, s);
      var a2 = a + Math.PI / 8;
      svg("path", { d: "M" + (100 + Math.cos(a2) * 40) + " " + (100 + Math.sin(a2) * 40) + " Q " + (100 + Math.cos(a2) * 62) + " " + (100 + Math.sin(a2) * 62) + " " + (100 + Math.cos(a2) * 78) + " " + (100 + Math.sin(a2) * 78), "stroke-width": .9, opacity: .7 }, s);
    }
    el("div", "cin-vig", st);
    var box = el("div", "cin-reb-text", st);
    var k = el("div", "cin-kicker cin-in", box, "Samsara"); k.style.setProperty("--d", "2.2s");
    var t = el("div", "cin-title cin-in", box, "Rinasci"); t.style.setProperty("--d", "2.35s");
    var r = el("div", "cin-rule cin-in", box); r.style.setProperty("--d", "2.8s");
    var sb = el("div", "cin-sub cin-in", box, "La ruota gira ancora"); sb.style.setProperty("--d", "3.0s");
    env.at(1200, function () { ambient("sfondamento"); });
    env.at(2300, function () { narrate("Rinascita. La ruota gira ancora."); });
    return { dur: 4400 };
  };

  // Titolo (banner)
  SCENES.titolo = function (env) {
    var d = env.data;
    var ttl = cap(d.titolo || d.nome || "Titolo");
    env.headline = "Nuovo titolo: " + ttl;
    env.soft = true;
    var w = el("div", "cin-banner-wrap", env.root);
    var b = el("div", "cin-banner", w);
    el("div", "cin-kicker", b, "Nuovo titolo");
    el("div", "cin-btitle", b, esc(ttl));
    b.addEventListener("click", function (e) { e.stopPropagation(); env.skip(); });
    env.at(250, function () { ambient("campana"); narrate("Nuovo titolo: " + ttl); });
    return { dur: 2500 };
  };

  // Intuizione
  SCENES.intuizione = function (env) {
    var d = env.data, st = env.stage, nome = d.nome || "Una nuova comprensione";
    env.headline = "Intuizione. " + nome;
    el("div", "cin-ins-bg", st);
    el("div", "cin-aura", st);
    var lw = el("div", "cin-lotus", st);
    var s = svg("svg", { viewBox: "0 0 200 200" }, lw);
    var defs = svg("defs", {}, s);
    var g1 = svg("linearGradient", { id: "cin-pg", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    svg("stop", { offset: "0", "stop-color": "#fff6d8" }, g1); svg("stop", { offset: "1", "stop-color": "#e2bf6a", "stop-opacity": ".75" }, g1);
    var rings = [{ n: 10, sc: 1, off: 0, dl: .35, op: .62 }, { n: 8, sc: .78, off: 18, dl: .8, op: .78 }, { n: 6, sc: .52, off: 0, dl: 1.25, op: .95 }];
    rings.forEach(function (rg) {
      for (var i = 0; i < rg.n; i++) {
        var gp = svg("g", { "class": "cin-petal", style: "--r:" + (rg.off + i * 360 / rg.n) + "deg;--s:" + rg.sc + ";--d:" + (rg.dl + i * .04) + "s" }, s);
        svg("path", { d: "M100 100 C86 82 88 52 100 24 C112 52 114 82 100 100Z", fill: "url(#cin-pg)", "fill-opacity": rg.op, stroke: "#c79a3a", "stroke-opacity": .7, "stroke-width": .7 }, gp);
        svg("path", { d: "M100 96 C98 78 99 58 100 40", stroke: "#fff", "stroke-opacity": .5, "stroke-width": .5, fill: "none" }, gp);
      }
    });
    var core = svg("circle", { cx: 100, cy: 100, r: 7, fill: "#fff8e0" }, s);
    core.setAttribute("class", "cin-petal"); core.style.setProperty("--r", "0deg"); core.style.setProperty("--d", "1.7s");
    for (var m = 0; m < (small() ? 10 : 18); m++) {
      var mo = el("div", "cin-mote", st);
      mo.style.left = (30 + Math.random() * 40) + "%"; mo.style.setProperty("--x", rnd(-60, 60) + "px");
      mo.style.setProperty("--d", (1 + Math.random() * 1.6).toFixed(2) + "s"); mo.style.setProperty("--t", (1.4 + Math.random() * 1.2).toFixed(2) + "s");
    }
    var box = el("div", "cin-ins-text", st);
    var k = el("div", "cin-kicker cin-in", box, "Intuizione"); k.style.setProperty("--d", "1.5s");
    var t = el("div", "cin-title cin-in", box, esc(cap(nome))); t.style.setProperty("--d", "1.7s");
    env.at(1100, function () { ambient("campana"); narrate("Intuizione. " + nome); });
    return { dur: 3300 };
  };

  /* ---------- apparizione (Agg. 83): la creatura, la reliquia, la forma che prendi, in sovrimpressione ---------- */
  var TONES = { sangue: "#c0392b", reliquia: "#c9a227", trasformazione: "#e0662f", essenza: "#7d6bd6", reperto: "#2f9d7e", bestia: "#c9a227" };
  SCENES.apparizione = function (env) {
    var d = env.data, tone = TONES[d.tono] || "#c9a227";
    env.headline = (d.titolo || "") + (d.sottotitolo ? " — " + d.sottotitolo : "");
    var st = env.stage; st.classList.add("cin-app"); st.style.setProperty("--tone", tone);
    var wrap = el("div", "cin-app-wrap", st);
    el("div", "cin-app-glow", wrap);
    if (d.img) { var im = el("img", "cin-app-img", wrap); im.src = d.img; im.alt = ""; }
    else el("div", "cin-app-img cin-app-noimg", wrap, esc((d.titolo || "?").charAt(0)));
    for (var m = 0; m < (small() ? 8 : 16); m++) {
      var mo = el("div", "cin-mote", st);
      mo.style.left = (25 + Math.random() * 50) + "%"; mo.style.setProperty("--x", rnd(-70, 70) + "px");
      mo.style.setProperty("--d", (0.6 + Math.random() * 1.4).toFixed(2) + "s"); mo.style.setProperty("--t", (1.6 + Math.random() * 1.2).toFixed(2) + "s");
    }
    var box = el("div", "cin-app-text", st);
    var k = el("div", "cin-kicker cin-in", box, esc(d.kicker || "")); k.style.setProperty("--d", ".9s");
    var t = el("div", "cin-title cin-in", box, esc(cap(d.titolo || ""))); t.style.setProperty("--d", "1.1s");
    if (d.sottotitolo) { var sub = el("div", "cin-sub cin-in", box, esc(d.sottotitolo)); sub.style.setProperty("--d", "1.4s"); }
    env.at(500, function () { ambient(d.tono === "trasformazione" ? "gong" : "campana"); narrate((d.kicker ? d.kicker + ". " : "") + (d.titolo || "")); });
    return { dur: 3800 };
  };

  /* ---------- runner ---------- */
  function isEditable(t) {
    if (!t || !t.tagName) return false;
    var n = t.tagName.toLowerCase();
    return n === "input" || n === "textarea" || n === "select" || t.isContentEditable;
  }

  function start(job) {
    var env = { data: job.data || {}, cleanups: [], events: [], draws: [], timers: [], headline: "", soft: false };
    var root = el("div", "cin-root"), stage = el("div", "cin-stage", root);
    env.root = root; env.stage = stage;
    env.at = function (ms, fn) { env.events.push({ t: ms, fn: fn, done: false }); };
    env.draw = function (fn) { env.draws.push(fn); };
    env.later = function (fn, ms) { env.timers.push(setTimeout(function () { try { fn(); } catch (e) {} }, ms)); };
    env.skip = function () { finish(true); };
    var c = cur = { job: job, env: env, root: root, raf: 0, done: false, t0: 0, dur: 0 };
    try {
      root.setAttribute("data-kind", job.kind);
      document.body.appendChild(root);
      var info = SCENES[job.kind](env);
      c.dur = info.dur;
      var sr = el("div", "cin-sr", root, esc(env.headline)); sr.setAttribute("role", "status"); sr.setAttribute("aria-live", "polite");
      if (env.soft) root.classList.add("cin-soft");
      else {
        var btn = el("button", "cin-skip", root, "Salta ▸"); btn.type = "button"; btn.setAttribute("aria-label", "Salta la sequenza");
        btn.addEventListener("click", function (e) { e.stopPropagation(); finish(true); });
        root.addEventListener("click", function () { finish(true); });
      }
      c.key = function (e) {
        try {
          var k = e.key;
          if (k !== "Escape" && k !== " " && k !== "Enter" && k !== "Spacebar") return;
          if (env.soft && k !== "Escape" && isEditable(e.target)) return;
          if (!env.soft || k === "Escape") { e.preventDefault(); e.stopPropagation(); }
          finish(true);
        } catch (er) {}
      };
      document.addEventListener("keydown", c.key, true);
      c.t0 = performance.now();
      c.safety = setTimeout(function () { finish(false); }, c.dur + 1200);
      c.raf = requestAnimationFrame(loop);
    } catch (err) {
      finish(true);
    }
  }

  function loop(now) {
    var c = cur;
    if (!c || c.done) return;
    try {
      var t = (now || performance.now()) - c.t0, env = c.env, i;
      for (i = 0; i < env.events.length; i++) {
        var ev = env.events[i];
        if (!ev.done && t >= ev.t) { ev.done = true; try { ev.fn(); } catch (e) {} }
      }
      for (i = 0; i < env.draws.length; i++) { try { env.draws[i](t); } catch (e) {} }
      if (t >= c.dur - 380 && !c.fading) { c.fading = true; c.root.classList.add("cin-out"); }
      if (t >= c.dur) { finish(false); return; }
    } catch (e) { finish(true); return; }
    c.raf = requestAnimationFrame(loop);
  }

  function teardown(c) {
    try { cancelAnimationFrame(c.raf); } catch (e) {}
    clearTimeout(c.safety);
    c.env.timers.forEach(clearTimeout);
    document.removeEventListener("keydown", c.key, true);
    c.env.cleanups.forEach(function (f) { try { f(); } catch (e) {} });
    if (c.root.parentNode) c.root.parentNode.removeChild(c.root);
  }

  function finish() {
    var c = cur;
    if (!c || c.done) return;
    c.done = true;
    try { teardown(c); } catch (e) {}
    cur = null;
    try { c.job.res(); } catch (e) {}
    setTimeout(next, 80);
  }

  function next() {
    if (cur) return;
    var j = queue.shift();
    if (j) start(j);
  }

  function cancelAll() {
    var q = queue; queue = [];
    q.forEach(function (j) { try { j.res(); } catch (e) {} });
    if (cur) finish(true);
  }

  function play(kind, data) {
    return new Promise(function (resolve) {
      try {
        if (!enabled() || !SCENES[kind] || !document.body) { resolve(); return; }
        var job = { kind: kind, data: data || {}, res: resolve };
        if (cur) { if (queue.length >= MAX_QUEUE) { resolve(); return; } queue.push(job); return; }
        start(job);
      } catch (e) { resolve(); }
    });
  }

  function skip() { if (cur) finish(true); }

  /* ---------- rilevamento dal log ---------- */
  function clean(s) { return String(s || "").replace(/[☯✦★✧◆◇▸»«"“”]+/g, " ").replace(/\s+/g, " ").replace(/[\s.,;:!\-—–→]+$/, "").replace(/^[\s.,;:!\-—–→]+/, "").trim(); }
  function m1(text, re) { var m = re.exec(text); return m ? m[1] : null; }

  function fromLog(text) {
    try {
      text = String(text == null ? "" : text);
      if (!text || !enabled()) return false;
      var m, n;

      // morte
      if (/☠/.test(text) && /sei\s+morto|sei\s+morta|la\s+tua\s+vita\s+finisce/i.test(text)) {
        var eta = m1(text, /(\d{1,4})\s*anni/i);
        var nome = clean(m1(text, /(?:^|\n|\s)(?:nome|cultivatore)\s*[:=]\s*([^\n,.;]+)/i) || "");
        play("morte", { nome: nome, eta: eta });
        return true;
      }
      // rinascita
      if (/RINASCI|reincarn/i.test(text)) { play("rinascita", {}); return true; }

      // sfondamento
      if (/SFONDAMENTO|Avanzi\s+al\s+regno|sei\s+salito/i.test(text) && !/fallit|non\s+riesci|respint/i.test(text.split(/\n/).filter(function (l) { return /SFONDAMENTO|Avanzi|sei\s+salito/i.test(l); }).join(" "))) {
        var regno = clean(m1(text, /Avanzi\s+al\s+regno\s*[:→\-—–]*\s*([^!.\n(\[]+)/i) || m1(text, /(?:nel|al|del|il)?\s*regno\s*[:→\-—–]+\s*([^!.\n(\[]+)/i) || m1(text, /→\s*([^!.\n(\[]+)/) || m1(text, /sei\s+salito\s+(?:al|nel|di)\s+(?:regno\s+)?(?:del(?:la)?\s+)?([^!.\n(\[]+)/i) || "");
        var strato = m1(text, /strato\s*(?:n\.?\s*)?(\d{1,3})/i);
        play("sfondamento", { regno: regno || "Nuovo regno", strato: strato, nome: regno || "" });
        return true;
      }
      // tribolazione
      if (/TRIBOLAZIONE/i.test(text)) {
        var fail = /fallit|non\s+sopravvivi|sei\s+morto/i.test(text), good = /superat|sopravvivi/i.test(text);
        if (fail || good) {
          n = parseInt(m1(text, /(\d{1,3})\s*fulmin/i) || m1(text, /fulmin[ei]\s*\d{1,3}\s*\/\s*(\d{1,3})/i) || m1(text, /\d{1,3}\s*\/\s*(\d{1,3})\s*fulmin/i), 10) || 9;
          play("tribolazione", { fulmini: n, esito: fail ? "fallita" : "superata" });
          return true;
        }
      }
      // fusione
      if (/FUSIONE\s*[—–-]|NASCE\s+UNA\s+VIA\s+NUOVA/i.test(text)) {
        var nm = m1(text, /FUSIONE\s*[—–-]\s*([^☯\n!]+)/) || m1(text, /NASCE\s+UNA\s+VIA\s+NUOVA\s*[:—–\-]\s*([^☯\n!.]+)/i) || m1(text, /NASCE\s+UNA\s+VIA\s+NUOVA[^\n]*?\b(D[AEI]L?(?:LA)?\s+[A-ZÀ-Ý][A-ZÀ-Ý' ]+)/);
        var pair = /([A-Za-zÀ-ÿ' ]{2,28}?)\s*\+\s*([A-Za-zÀ-ÿ' ]{2,28})/.exec(text);
        var dn = clean(nm || "");
        play("fusione", { a: pair ? clean(pair[1]) : "", b: pair ? clean(pair[2]) : "", nome: dn || "Via nuova" });
        return true;
      }
      // intuizione
      if (/INTUIZIONE\s*[—–-]/i.test(text)) {
        play("intuizione", { nome: clean(m1(text, /INTUIZIONE\s*[—–-]\s*([^\n!.]+)/i) || "") || "Una nuova comprensione" });
        return true;
      }
      // apparizioni: sangue di bestie sacre, essenze, reliquie, reperti, trasformazioni
      var app = apparition(text);
      if (app) { play("apparizione", app); return true; }
      // titolo
      m = /Nuovo\s+titolo\s*:\s*[«"“]([^»"”\n]+)[»"”]/i.exec(text);
      if (m) { play("titolo", { titolo: m[1].trim() }); return true; }
    } catch (e) {}
    return false;
  }

  var BEASTS = ["drago", "fenice", "qilin", "tigre", "volpe", "serpente", "tartaruga", "gru", "kun", "demone", "gigante",
                "leviatano", "silvano"];
  function img(keys) { try { return (window.imgOf && window.imgOf(keys)) || ""; } catch (e) { return ""; } }
  function beastOf(s) { s = String(s || "").toLowerCase(); for (var i = 0; i < BEASTS.length; i++) if (s.indexOf(BEASTS[i]) >= 0) return BEASTS[i]; return ""; }
  function apparition(text) {
    var m;
    if ((m = /🩸\s*Un nuovo sangue scorre in te:\s*([^(\n]+)/.exec(text))) {
      var b = beastOf(m[1]);
      return { tono: "sangue", kicker: "Un nuovo sangue scorre in te", titolo: clean(m[1]),
               img: img(["bestie/" + b, "trasformazioni/" + b, "creature/beast"]) };
    }
    if ((m = /TRASFORMAZIONE:[^\n]*?diventi\s+([^—.,!\n]+)/i.exec(text))) {
      var t = beastOf(m[1]);
      return { tono: "trasformazione", kicker: "Trasformazione", titolo: clean(m[1]),
               img: img(["trasformazioni/" + t, "bestie/" + t, "trasformazioni/corpo_supremo"]) };
    }
    if ((m = /🏺[^\n]*?reliquia,?\s*([^!\n]+)/i.exec(text))) {
      var race = (/(demon|drag|gigant|mare|spirit)/i.exec(text) || [""])[0].toLowerCase();
      var rk = { demon: "demoni", drag: "draghi", gigant: "giganti", mare: "maree", spirit: "spiriti" }[race] || "";
      return { tono: "reliquia", kicker: "Una reliquia", titolo: clean(m[1]), img: img(rk ? ["reliquie/" + rk] : ["scene/reperti"]) };
    }
    if ((m = /🏺\s*([^\n]+)/.exec(text))) {
      return { tono: "reperto", kicker: "Un reperto dei maestri", titolo: clean(m[1]).slice(0, 70), img: img(["scene/reperti"]) };
    }
    if ((m = /Divori l'essenza di\s+([^:\n]+)/.exec(text))) {
      return { tono: "essenza", kicker: "Divori un'essenza", titolo: clean(m[1]), img: img(["creature/spirit"]) };
    }
    return null;
  }

  window.Cinema = { enabled: enabled, setEnabled: setEnabled, play: play, skip: skip, fromLog: fromLog, kinds: Object.keys(SCENES) };
})();
