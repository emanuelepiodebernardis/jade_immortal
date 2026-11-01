/* Jade Immortal — set di icone SVG disegnate a mano (stile sigillo di giada / pennello a inchiostro).
   Tutte su griglia 24x24, tratto 1.8 con estremi arrotondati, colore = currentColor.
   API: Icons.svg(nome, size, cls) · Icons.has · Icons.names · Icons.forEmoji · Icons.forCmd · Icons.upgrade(root) */
(function () {
  "use strict";

  /* ---------- piccoli aiuti geometrici (calcolati una volta sola) ---------- */
  var r2 = function (n) { return Math.round(n * 100) / 100; };
  var F = ' fill="currentColor" stroke="none"';          // accento pieno

  // ingranaggio a n denti
  function gear(cx, cy, n, ri, ro) {
    var pts = [], step = Math.PI * 2 / n, i, a;
    for (i = 0; i < n; i++) {
      a = i * step - Math.PI / 2;
      [[-0.30, ri], [-0.17, ro], [0.17, ro], [0.30, ri]].forEach(function (q) {
        pts.push((r2(cx + Math.cos(a + q[0] * step * 1.5) * q[1])) + " " + (r2(cy + Math.sin(a + q[0] * step * 1.5) * q[1])));
      });
    }
    return "M" + pts.join("L") + "z";
  }
  // spirale archimedea dal centro verso l'esterno
  function spiral(cx, cy, rmax, turns, a0, rmin) {
    var pts = [], steps = Math.round(turns * 36), i, t, a, r;
    for (i = 0; i <= steps; i++) {
      t = i / steps; a = (a0 || 0) + t * turns * Math.PI * 2; r = (rmin || 0) + t * (rmax - (rmin || 0));
      pts.push(r2(cx + Math.cos(a) * r) + " " + r2(cy + Math.sin(a) * r));
    }
    return "M" + pts.join("L");
  }
  // raggi attorno a un centro
  function rays(cx, cy, r1, r2_, n, off) {
    var d = "", i, a;
    for (i = 0; i < n; i++) {
      a = (off || 0) + i * Math.PI * 2 / n;
      d += "M" + r2(cx + Math.cos(a) * r1) + " " + r2(cy + Math.sin(a) * r1) + "L" + r2(cx + Math.cos(a) * r2_) + " " + r2(cy + Math.sin(a) * r2_);
    }
    return d;
  }
  // tetto a pagoda con gronde rialzate
  function roof(cx, yb, w) {
    var t = w * 0.26;
    return '<path d="M' + r2(cx - w) + " " + yb + "Q" + r2(cx - w * 0.45) + " " + r2(yb - 0.2) + " " + r2(cx - t) + " " + r2(yb - 3.800) +
      "H" + r2(cx + t) + "Q" + r2(cx + w * 0.45) + " " + r2(yb - 0.2) + " " + r2(cx + w) + " " + yb + 'z"' + F + ' stroke="currentColor" stroke-width="1.4"/>';
  }
  // spada: punta (tx,ty) -> pomolo (hx,hy), con elsa
  function sword(tx, ty, hx, hy, gw) {
    var dx = hx - tx, dy = hy - ty, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L, px = -uy, py = ux;
    var gx = tx + dx * 0.66, gy = ty + dy * 0.66, w = gw || 3.1;
    return "M" + tx + " " + ty + "L" + hx + " " + hy +
      "M" + r2(gx + px * w) + " " + r2(gy + py * w) + "L" + r2(gx - px * w) + " " + r2(gy - py * w);
  }
  function pommel(hx, hy) { return '<circle cx="' + hx + '" cy="' + hy + '" r="1.25"' + F + '/>'; }

  /* ---------- le icone ---------- */
  var I = {};

  // === palazzi ===
  I.oggi = '<path d="M12 1.800V3.500"/>' + roof(12, 7, 5.600) + '<path d="M9.800 7v2.800M14.200 7v2.800"/>' + roof(12, 13.500, 7.800) +
    '<path d="M9 13.500v3M15 13.500v3"/>' + roof(12, 20.200, 9.800) + '<path d="M10.200 20.200V22M13.800 20.200V22"/>';
  I.via = '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18 4.500 4.500 0 0 1 0-9 4.500 4.500 0 0 0 0-9zM12 7.500m-1.300 0a1.300 1.300 0 1 0 2.600 0 1.300 1.300 0 1 0-2.600 0M12 16.500m-1.300 0a1.300 1.300 0 1 0 2.600 0 1.300 1.300 0 1 0-2.600 0" fill="currentColor" fill-rule="evenodd" stroke="none"/>';
  I.setta = '<path d="M2.500 6.200c3.200 1.400 15.800 1.400 19 0"/><path d="M4.500 9.800h15"/><path d="M7 6.800V21M17 6.800V21"/><path d="M12 9.800V12.500"/>';
  I.seguaci = '<circle cx="8.500" cy="7.500" r="3"/><circle cx="17" cy="9" r="2.400"/>' +
    '<path d="M2.800 20c0-3.800 2.600-6.300 5.700-6.300S14.200 16.200 14.200 20"/><path d="M15.300 14.100c3 0 5.600 2 5.700 5.500"/>';
  I.mondo = '<circle cx="12" cy="12" r="9"/><path d="M3.200 9.500c5.200 1.600 12.400 1.600 17.600 0M3.200 14.500c5.200-1.600 12.400-1.600 17.600 0"/><path d="M12 3c-3.600 3.600-3.600 14.400 0 18 3.600-3.600 3.600-14.400 0-18z"/>';
  I.tesori = '<path d="M9 3.500h6l-1.300 3.200h-3.400z"/><path d="M10.300 6.700C6.200 9.300 4.500 12.300 4.500 15.500c0 3 2.300 5 7.500 5s7.500-2 7.500-5c0-3.200-1.700-6.200-5.800-8.800"/>' +
    '<path d="M12 12.200v5M10 14h4"/>';
  I.storia = '<path d="M3.500 4h17M3.500 20h17"/><path d="M6 4.500v15M18 4.500v15"/><path d="M9.500 8.500h5M9.500 12h5M9.500 15.500h3"/>';
  I.opzioni = '<path d="' + gear(12, 12, 8, 7.200, 9.600) + '"/><circle cx="12" cy="12" r="2.800"/>';
  I.salva = '<path d="M9 8V5.200A1.700 1.700 0 0 1 10.700 3.500h2.600A1.700 1.700 0 0 1 15 5.200V8"/><rect x="3.500" y="8" width="17" height="12.500" rx="2.200"/><path d="M8 12.500h8M12 12.500v5M9 17.500h6"/>';

  // === azioni ===
  I.allenati = '<circle cx="12" cy="5.600" r="2.100"/><path d="M12 8.600v4.200"/><path d="M7.200 12.200c1.600.8 3.100 1 4.800 1s3.200-.2 4.800-1"/>' +
    '<path d="M4.500 19.200c2.600-.4 4.600-1.800 7.500-1.800s4.900 1.400 7.500 1.800"/><path d="M4.800 8c-1.200 1.700-1.200 3.800 0 5.600M19.200 8c1.200 1.700 1.200 3.800 0 5.600"/>';
  I.medita = '<circle cx="12" cy="12" r="9.500"/><circle cx="12" cy="8.200" r="1.800"/><path d="M12 10.600v3"/><path d="M8.200 13.900c1.300.7 2.600.9 3.800.9s2.500-.2 3.800-.9"/><path d="M7.500 17.200c1.600-.5 2.700-1.200 4.500-1.200s2.900.7 4.500 1.200"/>';
  I.sfonda = '<ellipse cx="12" cy="16" rx="8.500" ry="3.400"/><path d="M12 19V3.200M7.800 7.400L12 3.200l4.200 4.200"/><path d="M3.200 9.800l2 1.600M20.800 9.800l-2 1.600M2.800 13.500l1.500.5M21.200 13.500l-1.500.5" />';
  I.tribolazione = '<path d="M7.200 15.200a4.200 4.200 0 0 1-.4-8.300 5.600 5.600 0 0 1 10.600 1.200 3.600 3.600 0 0 1-.4 7.100"/><path d="M12.800 11.500l-3 4.700h3.800l-2 5.300"/>';
  I.tempra = '<path d="M12 2.800c.6 3.500 5.800 5.600 5.800 10.700a5.800 5.800 0 0 1-11.600 0c0-2.400 1-3.800 2.300-5.200.2 1.700.9 2.600 1.900 3C10 8.400 11.100 5.700 12 2.800z"/>' +
    '<path d="M12 18.400a2.500 2.500 0 0 1-2-4c.9 1 2 1 3 .2"/>';
  I.spiriti = '<path d="M12 3C8.200 3 6.200 6 6.200 9.500c0 2.200.8 3.800.8 6.200 0 1.800-1.100 3.200-2.800 4.300 2.300.2 4.200-.4 5.200-2 .9 1.500 1.600 2 2.600 2s1.700-.5 2.600-2c1 1.600 2.900 2.200 5.200 2-1.700-1.100-2.800-2.500-2.800-4.300 0-2.400.8-4 .8-6.200C17.800 6 15.800 3 12 3z"/>' +
    '<circle cx="9.600" cy="9.600" r="1.100"' + F + '/><circle cx="14.400" cy="9.600" r="1.100"' + F + '/>';
  I.dormi = '<path d="M19.800 14.300A8.400 8.400 0 1 1 9.700 4.200a6.700 6.700 0 0 0 10.100 10.100z"/><path d="M16.500 3.200v3.600M14.700 5h3.600"/>';
  I.raccogli = '<path d="M7.800 11.800V6.200a1.300 1.300 0 0 1 2.600 0v4.600"/><path d="M10.400 10.200V4.800a1.300 1.300 0 0 1 2.600 0v5.400"/><path d="M13 10.200V5.700a1.300 1.300 0 0 1 2.600 0v5.500"/>' +
    '<path d="M15.600 8.300a1.300 1.300 0 0 1 2.600 0v6.200c0 4-2.500 6.700-6 6.700-2.600 0-4.200-1-5.700-3.200L4.200 14c-.6-.9.500-2.100 1.500-1.400L7.800 14.200"/>';
  I.cura = '<circle cx="10" cy="14" r="6.500"/><circle cx="10" cy="14" r="2.200"/><path d="M18.200 2.800c.3 2 .9 2.800 2.800 3.200-1.900.4-2.500 1.200-2.800 3.200-.3-2-.9-2.800-2.800-3.200 1.900-.4 2.500-1.200 2.800-3.200z"' + F + '/>';
  I.esplora = '<circle cx="12" cy="12" r="9"/><path d="M15.800 8.200l-2.200 5.400-5.400 2.200 2.200-5.400z"/><circle cx="12" cy="12" r=".9"' + F + '/>';
  I.mappa = '<path d="M3.200 6.200l5.600-2.200 6.400 2.200 5.600-2.200v14l-5.600 2.200-6.400-2.200-5.600 2.200z"/><path d="M8.800 4v14.200M15.200 6.200v14"/>';
  I.viaggia = '<path d="M4.500 19.500c0-6 6-4 9-8.500 1-1.500 1.500-3 2-4.200" stroke-dasharray="0.01 3.900"/><path d="M13.200 5.800l5.300-1.300-.9 5.500" /><circle cx="4.500" cy="19.500" r="1.400"' + F + '/>';
  I.caccia = '<path d="M12 12c-3 0-5.700 3.200-5.700 5.500 0 1.900 1.600 2.300 3.100 2 1-.2 1.600-.6 2.600-.6s1.600.4 2.600.6c1.500.3 3.100-.1 3.100-2C17.700 15.200 15 12 12 12z"/>' +
    '<ellipse cx="5.600" cy="10.400" rx="1.500" ry="2"/><ellipse cx="9.400" cy="6.400" rx="1.600" ry="2.200"/><ellipse cx="14.600" cy="6.400" rx="1.600" ry="2.200"/><ellipse cx="18.400" cy="10.400" rx="1.500" ry="2"/>';
  I.raccolta = '<path d="M12 21.500V9.500"/><path d="M12 14.500c-4.300 0-6.500-2.200-6.500-6.500 4.300 0 6.500 2.200 6.500 6.500z"/><path d="M12 11c0-4.300 2.200-6.500 6.500-6.500 0 4.300-2.200 6.500-6.500 6.500z"/><path d="M8.500 21.500h7"/>';
  I.osserva = '<path d="M2.500 12c3.200-5.300 6.700-7.500 9.500-7.500s6.300 2.200 9.500 7.500c-3.200 5.300-6.700 7.500-9.500 7.500S5.700 17.300 2.500 12z"/><circle cx="12" cy="12" r="3.300"/><circle cx="12" cy="12" r="1.200"' + F + '/>';
  I.parla = '<path d="M4 5.200h16a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1h-8.200L7.200 20.500V16.200H4a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1z"/><path d="M7.500 9.200h9M7.500 12.300h5.500"/>';
  I.attacca = '<path d="' + sword(20.500, 3.500, 5.500, 18.500) + sword(3.500, 3.500, 18.500, 18.500) + '"/>' + pommel(5.500, 18.500) + pommel(18.500, 18.500);
  I.duello = '<path d="' + sword(12, 8.500, 3.800, 20.800) + sword(12, 8.500, 20.200, 20.800) + '"/>' + pommel(3.800, 20.800) + pommel(20.200, 20.800) +
    '<path d="M12 1.800v3.800M8.500 3.700l1.700 1.900M15.500 3.700l-1.700 1.900"/>';
  I.difendi = '<path d="M12 2.800l7.500 2.800v6c0 4.500-3.100 7.800-7.500 9.600-4.400-1.800-7.500-5.100-7.500-9.600v-6z"/><path d="M12 2.800v18"/><path d="M7.800 9.500c1.500.4 2.900.4 4.200 0"/>';
  I.concentrati = '<path d="M12 4c2.800 2.700 3.600 5.600 0 9.500-3.600-3.900-2.800-6.800 0-9.500z"/><path d="M12 13.500C8.800 13.700 5.800 12.300 4.500 8.200c3.600-.2 6.400 1.300 7.500 5.300z"/><path d="M12 13.500c3.200.2 6.200-1.200 7.500-5.300-3.600-.2-6.400 1.300-7.500 5.300z"/><path d="M4 15.800c2.200 2.500 5.200 3.800 8 3.800s5.800-1.300 8-3.800"/>';
  I.pillola = '<path d="M10.200 2.800h3.600"/><path d="M10.800 2.800c0 1.500-.2 2.600-1 3.300-.6.600-.9 1.300-.9 2.100 0 .9.600 1.600 1.300 2.100C7.200 11 5.800 13 5.800 15.300c0 3.500 2.700 5.900 6.200 5.900s6.200-2.400 6.200-5.900c0-2.300-1.400-4.300-4.400-5 .7-.5 1.300-1.200 1.300-2.100 0-.8-.3-1.500-.9-2.100-.8-.7-1-1.800-1-3.300"/><path d="M8.800 15.500c0 1.300.8 2.500 2 2.900"/>';
  I.fuggi = '<circle cx="14.800" cy="4.600" r="1.900"/><path d="M13.600 8l-2.800 5"/><path d="M13.800 8.600l3.400 2.700 2.700-.8M13.400 9.200L9.600 9.800 7.800 12.400"/><path d="M10.800 13l3.600 2.800.4 5M10.800 13l-2.600 3.600-3.700.8"/><path d="M2.500 7.500h3M1.500 11h3"/>';
  I.tecnica = '<path d="M3 20.500C4.500 10 12.500 3.500 21.200 3.200 14 7.800 9.600 13.500 3 20.500z"' + F + '/><path d="M3 11.500h4.200M5.500 7.500h3.300M10.800 21h5.200" />';

  // === armi, stili, elementi ===
  I.spada = '<path d="' + sword(19.500, 4.500, 5, 19, 3.600) + '"/>' + pommel(5, 19);
  I.lancia = '<path d="M5 19l11-11"/><path d="M16 8l1.300-4.800L20.800 6.700 16 8z"/><path d="M5 19l1.300-1.300"/><path d="M8.200 15.800L5.800 14.200M9.500 17.100l-1.600 2.200"/>';
  I.pugno = '<path d="M6 11V9.200A1.800 1.800 0 0 1 7.800 7.400h8.400A1.800 1.800 0 0 1 18 9.200v5.600c0 3-2.200 5.600-5.200 5.600h-1.600C8.200 20.400 6 18 6 15z"/><path d="M9.700 7.400V12M13 7.400V12M16 7.400V11.500"/><path d="M6 11.600h6.200c.9 0 1.600.7 1.600 1.600"/>';
  I.fuoco = '<path d="M12 2.500c.8 3.800 6.300 5.900 6.300 11.200a6.300 6.300 0 0 1-12.600 0c0-2.600 1-4.100 2.500-5.600.2 1.800 1 2.800 2 3.200C10 8.700 11 5.700 12 2.500z"/><path d="M12 20a2.800 2.800 0 0 1-2.800-2.800c0-1.800 1.700-2.800 2.800-4.700 1.100 1.900 2.800 2.900 2.800 4.700A2.800 2.800 0 0 1 12 20z"/>';
  I.acqua = '<path d="M2.800 8c2.100-2.300 4.100-2.300 6.200 0s4.100 2.300 6.200 0 4.100-2.300 6.200 0"/><path d="M2.800 13c2.100-2.300 4.100-2.300 6.200 0s4.100 2.300 6.200 0 4.100-2.300 6.200 0"/><path d="M2.800 18c2.100-2.300 4.100-2.300 6.200 0s4.100 2.300 6.200 0 4.100-2.300 6.200 0"/>';
  I.legno = '<path d="M8 21.500V8.700M16 21.500V10.200"/><path d="M6.500 14h3M14.500 15.500h3"/><path d="M8 8.700C8 5.800 9.200 3.800 11.700 2.800 12.200 5.600 10.900 7.800 8 8.700z"/><path d="M16 10.200c0-2.700 1.100-4.400 3.300-5.200.3 2.600-.9 4.400-3.300 5.200z"/>';
  I.metallo = '<path d="M2.500 10.200c2.600 1.900 6.200 2.700 9.500 2.700s6.900-.8 9.500-2.700L19 18.500H5z"/><path d="M7 10.500c0-3 2.200-5 5-5s5 2 5 5"/><path d="M9.500 15.300h5"/>';
  I.terra = '<path d="M2.500 19.500L9 7.500l3.600 6.200 2.400-3.700 6.500 9.500z"/><path d="M9 7.500l1.500 2.500-1.800.9M15 10l1 1.600"/>';
  I.fulmine = '<path d="M13.500 2.500L5 13.500h6l-1.200 8 8.700-11.400h-6z"/>';
  I.vento = '<path d="M2.800 9h10.200a2.800 2.800 0 1 0-2.700-3.500"/><path d="M2.800 13h14.400a3 3 0 1 1-2.800 4"/><path d="M2.800 17h6.200"/>';
  I.luce = '<circle cx="12" cy="12" r="4"/><path d="' + rays(12, 12, 6.800, 9.400, 8, Math.PI / 8) + '"/>';
  I.oscurita = '<circle cx="12" cy="12" r="5.800"' + F + '/><circle cx="12" cy="12" r="9.200" stroke-dasharray="1.200 3.350"/>';
  I.cuore = '<path d="M12 20.500C5.200 15.700 3 12.300 3 8.900A4.700 4.700 0 0 1 7.700 4.200c1.800 0 3.200.9 4.300 2.600 1.100-1.700 2.500-2.600 4.300-2.600A4.700 4.700 0 0 1 21 8.900c0 3.400-2.200 6.800-9 11.600z"/>';
  I.pietre = '<path d="M7 4.200h10L21.200 9.500 12 20.500 2.800 9.500z"/><path d="M2.800 9.500h18.400M9.600 4.200L8.200 9.500 12 20.500l3.800-11-1.400-5.300"/>';
  I.fama = '<path d="M12 2.800l2.800 5.800 6.300.9-4.600 4.400 1.100 6.300L12 17.200l-5.600 3 1.100-6.300L2.900 9.500l6.300-.9z"/>';
  I.ferita = '<g transform="rotate(-45 12 12)"><rect x="2.500" y="8" width="19" height="8" rx="4"/><path d="M9.500 8v8M14.500 8v8"/></g><circle cx="12" cy="10.600" r=".8"' + F + '/><circle cx="12" cy="13.400" r=".8"' + F + '/>';
  I.porta = '<path d="M4.500 21V10.500a7.500 7.500 0 0 1 15 0V21"/><path d="M2.500 21h19"/><path d="M12 6.500v14.500M8 21v-7M16 21v-7"/>';
  I.uscita = '<path d="M10 3.500H5.500a1.500 1.500 0 0 0-1.500 1.500v14a1.500 1.500 0 0 0 1.500 1.500H10"/><path d="M9.500 12h11M16.500 7.800l4.200 4.200-4.200 4.200"/>';
  I.scala_su = '<path d="M3.500 20.500h4.200V16h4.200v-4.500h4.200V7h4.400"/><path d="M6 10.500V3.800M3.200 6.500L6 3.800l2.800 2.700"/>';
  I.scala_giu = '<path d="M3.500 3.500h4.200V8h4.200v4.500h4.200V17h4.400"/><path d="M6 13.500v6.700M3.200 17.500L6 20.200l2.800-2.700"/>';
  I.mercato = '<path d="M3 9.500L4.600 4h14.800L21 9.500"/><path d="M3 9.500a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0"/><path d="M5 12.500V21M19 12.500V21M3.500 21h17"/><path d="M5 16.200h14"/>';
  I.forgia = '<path d="M3 10.500h14.500c0 2.300-1.800 3.500-4 3.700v2.300H16l1 2.500v1.500H7v-1.500l1-2.500h2.500v-2.300C6.800 13.800 4.500 12.500 3 10.500z"/><path d="M17.500 5.300l1-2.100M20.800 7.500l2-.5M14.800 5.800l-.1-2.300"/>';
  I.alchimia = '<path d="M4.500 9h15"/><path d="M5.800 9c0 5.800 2 8.700 6.200 8.700s6.200-2.900 6.200-8.700"/><path d="M7.700 6.500V9M16.300 6.500V9"/><path d="M8.800 17.200L7.600 21M15.200 17.200l1.200 3.800"/><path d="M10.500 3c-.9 1.100.9 1.900 0 3M14 3c-.9 1.100.9 1.900 0 3"/>';
  I.libro = '<path d="M12 6.200C9.800 4.500 6.800 4 3.800 4.600v13.600c3-.6 6 0 8.200 1.700 2.200-1.700 5.200-2.300 8.200-1.700V4.600c-3-.6-6-.1-8.200 1.600z"/><path d="M12 6.200v13.700"/>';
  I.bestia = '<path d="M4.600 4.200l3.800 2.300c2.300-.6 4.900-.6 7.200 0l3.800-2.300c1.300 3.200 1.200 5.600 0 8 .6 1.200.4 2.700-.7 4.200-1.500 2.600-3.600 3.800-6.700 3.800s-5.200-1.200-6.700-3.800c-1.100-1.500-1.300-3-.7-4.200-1.200-2.400-1.300-4.800 0-8z"/>' +
    '<path d="M12 7.200v2.800M7.800 11.200l2.600.9M16.200 11.200l-2.600.9"/><path d="M10.500 15h3l-1.500 1.700z"' + F + '/><path d="M12 16.700v1.200M9.800 19c.9-.6 1.600-.9 2.200-.9s1.300.3 2.200.9"/>';
  I.setta_missione = '<path d="M5.500 21.500V2.800"/><path d="M5.500 4.500h13.500l-3 4 3 4H5.500"/><path d="M9 8.500h4.500"/>';
  I.anima = '<path d="M5.200 15.600a4.800 4.800 0 1 1 8.700-3.400c.9-4 3.400-6.700 7-8-1.200 3.800-.5 7.300-3.400 10.400-2.800 3-8.500 3.300-12.300 1z"/><circle cx="9.800" cy="12.800" r="1.500"' + F + '/>';
  I.corpo = '<circle cx="12" cy="4.800" r="2.200"/><path d="M12 8.200v7"/><path d="M4.800 10.200c2.400.7 4.800.9 7.200.9s4.800-.2 7.200-.9"/><path d="M12 15.200l-3.600 6M12 15.200l3.600 6"/>';
  I.sangue = '<path d="M12 2.800C8.200 7.800 5.500 11 5.500 14.500a6.500 6.500 0 0 0 13 0C18.500 11 15.800 7.800 12 2.800z"/><path d="M8.800 14.800a3.300 3.300 0 0 0 2.300 3.200" />';
  I.dao = '<circle cx="12" cy="12" r="9.200"/><path d="M12 5.800v2.700M8.300 8.500h7.400"/><path d="M8.800 11.300h6.400M12 8.500v8.500"/><path d="M8.200 17.200c2.200 1 5.400 1 7.600 0"/>';
  I.compressione = '<path d="' + spiral(12, 12, 9.200, 2.250, -Math.PI / 2, 1.800) + '"/><circle cx="12" cy="12" r="1.600"' + F + '/>';
  I.saga = '<path d="M6.500 3h11a1.500 1.500 0 0 1 1.500 1.500v16H8a1.500 1.500 0 0 1-1.500-1.500z"/><path d="M6.500 18.500A1.500 1.500 0 0 1 8 17h11"/><path d="M14.500 3v6.800l1.500-1.300 1.500 1.300V3"/><path d="M9.800 7h2.200M9.800 10h1.800" />';

  // === extra per coprire le emoji del gioco ===
  I.casa = '<path d="M3 11.500L12 3.500l9 8"/><path d="M5.500 10v10.500h13V10"/><path d="M10 20.500v-5.500h4v5.500"/>';
  I.corona = '<path d="M3.500 18.500h17M4 18.500L3 8.500l5 4 4-7 4 7 5-4-1 10"/><circle cx="12" cy="14.500" r=".9"' + F + '/>';
  I.anello = '<circle cx="12" cy="14.500" r="6"/><path d="M9.500 4.300h5l1.700 2.500-4.200 3-4.200-3z"/>';
  I.moneta = '<circle cx="12" cy="12" r="9"/><rect x="9" y="9" width="6" height="6" rx=".8"/>';
  I.calendario = '<rect x="3.500" y="5" width="17" height="15.500" rx="2"/><path d="M3.500 10h17M8 2.800v4M16 2.800v4"/><path d="M8 14h2M14 14h2M8 17h2"/>';
  I.lista = '<rect x="4.500" y="3.500" width="15" height="17.500" rx="2"/><path d="M9 3.500V2.500h6v1"/><path d="M8.500 9.500h7M8.500 13h7M8.500 16.500h4"/>';
  I.lettera = '<rect x="3" y="5.500" width="18" height="13" rx="2"/><path d="M3.500 7l8.500 6.500L20.500 7"/>';
  I.penna = '<path d="M16.500 3.800l3.700 3.700L8.200 19.500l-4.700 1 1-4.700z"/><path d="M14 6.300l3.700 3.700"/>';
  I.ok = '<path d="M4.200 12.800l5.200 5.200L20 6.800"/>';
  I.allerta = '<path d="M12 3.200L22 20.500H2z"/><path d="M12 9.500v5"/><circle cx="12" cy="17.500" r=".5"' + F + ' stroke="currentColor" stroke-width="1"/>';
  I.teschio = '<path d="M12 3C7.500 3 4.500 6 4.500 10c0 2.500 1.200 4 2.500 5v3.500h10V15c1.300-1 2.500-2.500 2.500-5 0-4-3-7-7.500-7z"/><circle cx="9" cy="10.500" r="1.700"/><circle cx="15" cy="10.500" r="1.700"/><path d="M12 13.500l-.8 1.800h1.600zM10 18.500v-2M14 18.500v-2"/>';
  I.ragnatela = '<path d="M12 2.500v19M3.300 7.500l17.400 9M20.700 7.500l-17.400 9"/><path d="M12 7l4.500 2.500v5L12 17l-4.500-2.500v-5z"/>';
  I.cavallo = '<path d="M7 21v-4.200c0-1.600.3-2.700 1.200-3.800L6.300 10l1.200-3.500L10 4l.5 2.600c2.800.4 5.500 2 6.600 4.700.9 2 .9 4.200.4 6.200V21"/><circle cx="9.500" cy="8.300" r=".8"' + F + '/>';
  I.persona = '<circle cx="12" cy="7.500" r="3.500"/><path d="M5 21c0-4.300 3-7 7-7s7 2.700 7 7"/>';
  I.abito = '<path d="M8.800 3.500L3 6.800l2.200 4 2.300-1.200V20.500h9V9.600l2.300 1.200 2.200-4-5.800-3.300c-.5 1.500-1.800 2.300-3.200 2.300S9.300 5 8.800 3.500z"/>';
  I.trofeo = '<path d="M7.500 3.500h9v5.500a4.500 4.500 0 0 1-9 0z"/><path d="M7.500 5.500H4.500c0 3 1 4.700 3.200 5M16.500 5.500h3c0 3-1 4.700-3.200 5"/><path d="M12 13.500v4M8 20.500h8M9.500 17.500h5"/>';
  I.nuvola = '<path d="M7 18.500a4.300 4.300 0 0 1-.5-8.500 5.800 5.800 0 0 1 11 1.300 3.700 3.700 0 0 1-.5 7.200z"/>';
  I.ghiaccio = '<path d="M12 2.800v18.400M4 7.400l16 9.200M20 7.400L4 16.600"/><path d="M9.600 4.200L12 6.200l2.400-2M9.600 19.800L12 17.800l2.400 2"/>';
  I.stordito = '<path d="M12 2.800l1.800 4.600 4.800-1.600-1.600 4.800 4.600 1.800-4.600 1.800 1.600 4.800-4.800-1.600L12 21.200l-1.800-4.600-4.800 1.600L7 13.400 2.400 11.600 7 9.800 5.400 5l4.800 1.600z"/><circle cx="12" cy="11.600" r="1.600"' + F + '/>';
  I.abisso = '<ellipse cx="12" cy="12" rx="9.500" ry="9.500"/><ellipse cx="12" cy="12" rx="5.800" ry="5.800"/><circle cx="12" cy="12" r="2.200"' + F + '/>';
  I.scintilla = '<path d="M12 2.500c.9 5.500 3.500 8.100 9 9.500-5.500 1.400-8.100 4-9 9.500-.9-5.500-3.500-8.100-9-9.500 5.500-1.400 8.100-4 9-9.500z"' + F + '/>';
  I.bilancia = '<path d="M12 3.500v17M7.500 20.500h9M4.500 6.800h15"/><path d="M4.500 6.800L2.500 13a2.500 2.500 0 0 0 4 0zM19.500 6.800L17.500 13a2.500 2.500 0 0 0 4 0z"/>';
  I.musica = '<path d="M9 18V5.500l10-2.300V16"/><circle cx="6.500" cy="18" r="2.500"/><circle cx="16.500" cy="16" r="2.500"/><path d="M9 9.500l10-2.300"/>';
  I.suono = '<path d="M4 9.500h3.500L12.500 5v14l-5-4.500H4z"/><path d="M16 9a4.200 4.200 0 0 1 0 6M18.500 6.500a8 8 0 0 1 0 11"/>';
  I.espandi = '<path d="M14 3.500h6.500V10M10 20.500H3.500V14M20.500 3.500l-7 7M3.500 20.500l7-7"/>';
  I.contrasto = '<circle cx="12" cy="12" r="9"/><path d="M12 3a9 9 0 0 1 0 18z"' + F + '/>';

  // === serie 2: pittogrammi per le restanti emoji dell'interfaccia (stesso tratto, stessa griglia) ===
  I.medaglia = '<circle cx="12" cy="15" r="5.500"/><path d="M8 3.500l2.800 6.200M16 3.500l-2.800 6.200M7.500 3.500h9"/><path d="M12 12.600l.9 1.800 2 .3-1.450 1.400.35 2-1.800-.95-1.800.95.35-2L9.100 14.700l2-.3z"' + F + '/>';
  I.tomba = '<path d="M12 3v14M6.500 8h11"/><path d="M7 21h10M9 17.500h6"/>';
  I.piu = '<path d="M12 4.500v15M4.500 12h15"/>';
  I.urna = '<path d="M8.500 3.500h7M9.500 3.500v2.600C6.400 7.600 5.500 10.600 5.500 13.800c0 4 2.600 6.700 6.500 6.700s6.500-2.700 6.500-6.700c0-3.200-.9-6.200-4-7.700V3.500"/><path d="M6 11.500h12"/><path d="M9 20.500h6"/>';
  I.catena = '<rect x="2.500" y="8.800" width="11" height="6.400" rx="3.200" transform="rotate(-28 8 12)"/><rect x="10.500" y="8.800" width="11" height="6.400" rx="3.200" transform="rotate(-28 16 12)"/>';
  I.libri = '<path d="M4 4h4.500v16H4zM8.500 6.500H13V20H8.500z"/><path d="M14.200 7.200l4.200-1.100 3.400 13.200-4.200 1.100z"/><path d="M4 8h4.500"/>';
  I.microfono = '<rect x="9" y="2.800" width="6" height="11" rx="3"/><path d="M5.500 11.200a6.500 6.500 0 0 0 13 0M12 17.700v3.300M8.500 21h7"/>';
  I.clessidra = '<path d="M6 3h12M6 21h12"/><path d="M7.200 3c0 5.200 4.800 6.200 4.800 9s-4.800 3.800-4.800 9M16.800 3c0 5.200-4.800 6.200-4.800 9s4.800 3.800 4.800 9"/><path d="M10 18.500h4"/>';
  I.dado = '<rect x="3.800" y="3.800" width="16.400" height="16.400" rx="3.500"/><circle cx="8.600" cy="8.600" r="1"' + F + '/><circle cx="15.400" cy="8.600" r="1"' + F + '/><circle cx="12" cy="12" r="1"' + F + '/><circle cx="8.600" cy="15.400" r="1"' + F + '/><circle cx="15.400" cy="15.400" r="1"' + F + '/>';
  I.germoglio = '<path d="M12 21v-9.500"/><path d="M12 13.500c-4.300.2-6.600-2-6.800-5.800 4.300-.2 6.600 2 6.800 5.800z"/><path d="M12 11c.2-3.600 2.400-5.700 6.600-5.800.1 3.700-2.200 5.700-6.600 5.800z"/><path d="M6 21h12"/>';
  I.elica = '<path d="M7 3c0 5.500 10 6.500 10 12v6"/><path d="M17 3c0 5.500-10 6.500-10 12v6"/><path d="M8.200 6.800h7.600M8.200 17.200h7.600M7.800 12h8.400" />';
  I.quadro = '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3.500 17l5-5.500 4 4.200 2.800-2.800 5.200 4.800"/><circle cx="16.200" cy="8.800" r="1.600"/>';
  I.verme = '<circle cx="17.800" cy="7.200" r="2.600"/><circle cx="12.300" cy="11.300" r="2.500"/><circle cx="7.600" cy="15.800" r="2.300"/><circle cx="4.800" cy="20.200" r="1.300"' + F + '/><path d="M18.800 4.800l1.700-2.200M16.600 5.200l-.9-2.600"/>';
  I.albero = '<path d="M12 21v-7"/><path d="M12 14.200c-4.600 0-7.200-2.500-7.200-6C4.800 4.800 8 2.800 12 2.800s7.200 2 7.200 5.400c0 3.500-2.600 6-7.200 6z"/><path d="M12 18l-3-2.600M12 16l3-2.600"/>';
  I.esplosione = '<path d="M12 2.500l2.300 5.800 5.700-2.700-2.600 5.900 4.600 3.300-6 .3.200 6.100-4.200-4.500-4.200 4.500.2-6.100-6-.3 4.600-3.300L4 5.600l5.700 2.700z"/>';
  I.uovo = '<path d="M12 3c-4 0-6.500 6-6.500 10.500a6.500 6.500 0 0 0 13 0C18.500 9 16 3 12 3z"/><path d="M6.200 14.200l2.600-1.700 2.200 2.100 2.400-2.100 2.400 1.700"/>';
  I.domanda = '<circle cx="12" cy="12" r="9"/><path d="M9.200 9.600a2.900 2.900 0 1 1 4.100 2.600c-.9.500-1.300 1.100-1.300 2.100"/><circle cx="12" cy="17.200" r=".9"' + F + '/>';
  I.paesaggio = '<path d="M2.500 19.500l6.200-10.200 4 6.200 2.500-3.600 6.300 7.600z"/><circle cx="17.200" cy="6" r="2.100"/>';
  I.alba = '<path d="M2.500 18h19M6 21.500h12"/><path d="M6.600 18a5.400 5.400 0 0 1 10.800 0"/><path d="M12 6.200v2.600M4.700 9.900l1.800 1.800M19.300 9.900l-1.800 1.800"/>';
  I.pioggia = '<path d="M7 14.300a4.100 4.100 0 0 1-.5-8.100 5.600 5.600 0 0 1 10.600 1.200 3.500 3.500 0 0 1-.5 6.900z"/><path d="M8.600 17.300l-1.100 3M12.600 17.300l-1.100 3M16.600 17.300l-1.100 3"/>';
  I.nebbia = '<path d="M4.500 7.500h11M3 11.500h16M5.500 15.500h15M8.500 19.500h8"/>';
  I.foglia = '<path d="M4 20C3.800 10 9 4 20 4c.2 11-5.500 16.500-13.500 16.500"/><path d="M4 20c3-5.200 6.200-8.200 10.500-10.500"/>';
  I.demone = '<path d="M5.200 9.500L3.500 3.500l5.200 3.300M18.800 9.500l1.700-6-5.200 3.300"/><path d="M12 5.700c-4.500 0-7 3-7 7 0 4.500 3 8 7 8s7-3.500 7-8c0-4-2.500-7-7-7z"/><path d="M8.300 11.200l2.600 1.500M15.700 11.200l-2.600 1.500M9 17.300c2 1.200 4 1.200 6 0"/>';
  I.spettro = '<path d="M5 20.500V10.500a7 7 0 0 1 14 0v10l-2.300-2-2.400 2-2.300-2-2.300 2-2.400-2z"/><circle cx="9.500" cy="10.800" r="1.100"' + F + '/><circle cx="14.500" cy="10.800" r="1.100"' + F + '/>';
  I.grafico = '<path d="M3.500 3.500v17h17"/><path d="M7 15.500l4-5 3 3 5.500-7"/><path d="M16 6.500h3.500V10"/>';
  I.foglio = '<path d="M6 3h8l4.500 4.500V21H6z"/><path d="M14 3v4.500h4.500M9 12h6M9 15.500h6"/>';
  I.colomba = '<path d="M3 10.200c3 .6 5-.5 7-3.100 1-1.300 3.100-2.100 5.100-1l-1 2.600c3 .5 5.600 3 6.100 6.100-3-1-5.100-1-6.600 0-1 2.500-3.500 4.500-7.500 4.500l2-3.500C7 15.700 3.500 14.200 3 10.200z"/><circle cx="16.300" cy="8.900" r=".7"' + F + '/>';
  I.lucchetto = '<rect x="5" y="10.500" width="14" height="10" rx="2"/><path d="M8 10.500V7.500a4 4 0 0 1 8 0v3"/><path d="M12 14.500v2.200"/>';
  I.maschera = '<path d="M4 6c5-2 11-2 16 0v5c0 5-3.500 8-8 9.500C7.500 19 4 16 4 11z"/><path d="M7.300 10.300c1.600-.9 3-.8 3.700.6M16.700 10.300c-1.600-.9-3-.8-3.700.6M9 15.300c2 1.500 4 1.500 6 0"/>';
  I.dono = '<rect x="3.500" y="8.500" width="17" height="4.200" rx="1"/><path d="M5 12.700v8h14v-8M12 8.500v12"/><path d="M12 8.500C8.800 8.500 7 7 7 5.500S8.500 3.200 10 3.800c1.600.6 2 2.800 2 4.700zM12 8.500c3.200 0 5-1.500 5-3s-1.500-2.300-3-1.700c-1.600.6-2 2.800-2 4.700z"/>';
  I.fortuna = '<circle cx="8.800" cy="8.800" r="3.300"/><circle cx="15.200" cy="8.800" r="3.300"/><circle cx="8.800" cy="15.200" r="3.300"/><circle cx="15.200" cy="15.200" r="3.300"/><path d="M12 12c1.200 3.200 3 6 5.500 8.500"/>';
  I.automa = '<rect x="5" y="8" width="14" height="11.500" rx="2.800"/><path d="M12 8V4.200M10 4.200h4M2.800 12.500v3.200M21.200 12.500v3.200"/><circle cx="9.200" cy="13" r="1.200"' + F + '/><circle cx="14.800" cy="13" r="1.200"' + F + '/><path d="M9.500 16.600h5"/>';
  I.candela = '<path d="M12 2.500c1.600 2 2.600 3.200 2.600 4.600a2.600 2.600 0 0 1-5.200 0c0-1.400 1-2.600 2.600-4.600z"/><path d="M12 10.200v1.500"/><rect x="8.500" y="11.700" width="7" height="8.800" rx="1"/><path d="M6 21h12"/>';
  I.pausa = '<path d="M8.500 5.200v13.600M15.500 5.200v13.600"/>';
  I.avvia = '<path d="M7.500 4.500l11 7.500-11 7.500z"/>';
  I.ferma = '<rect x="5.500" y="5.500" width="13" height="13" rx="1.800"/>';
  I.chiudi = '<path d="M6 6l12 12M18 6L6 18"/>';
  I.losanga = '<path d="M12 2.500l3 3-3 3-3-3zM12 15.500l3 3-3 3-3-3zM2.500 12l3-3 3 3-3 3zM15.500 12l3-3 3 3-3 3z"/>';
  I.bersaglio = '<circle cx="12" cy="12" r="7.500"/><circle cx="12" cy="12" r="3.600"/><circle cx="12" cy="12" r="1"' + F + '/><path d="M12 1.800v3.300M12 18.900v3.300M1.800 12h3.300M18.900 12h3.300"/>';
  I.menu = '<path d="M4 6.500h16M4 12h16M4 17.500h16"/>';
  I.ripeti = '<path d="M4.600 12a7.500 7.500 0 1 0 2.400-5.500"/><path d="M4.200 3.800v4.700h4.700"/>';
  I.pesce = '<path d="M2.800 12c3-4.700 7-6.300 11-5 2.700.9 4.600 3 6.400 5-1.800 2-3.700 4.100-6.400 5-4 1.300-8-.3-11-5z"/><path d="M20.200 12l1.700-3.500v7z"/><circle cx="7.500" cy="11.200" r=".9"' + F + '/>';

  /* ---------- API di base ---------- */
  var ALIAS = { uscita: "uscita", exit: "uscita", gate: "porta", scale_su: "scala_su", scale_giu: "scala_giu",
    meditazione: "medita", sigillo: "salva", pozione: "pillola", gourd: "pillola", ritiro: "medita",
    nucleo: "pietre", gemma: "pietre", drago: "bestia", tigre: "bestia", stendardo: "setta_missione" };

  function norm(name) { name = String(name || "").toLowerCase().replace(/[\s-]+/g, "_"); return I[name] ? name : (ALIAS[name] || null); }
  function has(name) { return !!norm(name); }
  function names() { return Object.keys(I); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  function svg(name, size, cls) {
    var n = norm(name); if (!n) return "";
    var s = size == null ? 20 : size, dim = typeof s === "number" ? s + "" : esc(s);
    return '<svg class="ic-svg' + (cls ? " " + esc(cls) : "") + '" data-ic="' + n + '" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="' + dim + '" height="' + dim +
      '" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false" ' +
      'style="display:inline-block;vertical-align:-0.18em;flex:none;overflow:visible">' + I[n] + "</svg>";
  }

  /* ---------- emoji -> icona ---------- */
  var EMOJI = {
    "🏯": "oggi", "🗼": "oggi", "☯": "via", "⛩": "setta", "👥": "seguaci", "🤝": "seguaci", "🌍": "mondo", "🌌": "mondo",
    "🎒": "tesori", "🏺": "tesori", "📜": "storia", "⚙": "opzioni", "💾": "salva",
    "⇑": "sfonda", "⚡": "fulmine", "🌀": "tempra", "✺": "luce", "☾": "dormi", "✋": "raccogli", "✧": "cura",
    "🧭": "esplora", "🎯": "esplora", "🗺": "mappa", "➤": "viaggia", "🐎": "cavallo", "🐾": "caccia", "✿": "raccolta", "🌸": "raccolta", "🌿": "legno",
    "👁": "anima", "🔎": "osserva", "⚔": "attacca", "🗡": "spada", "🛡": "difendi", "🧘": "allenati", "🙏": "concentrati",
    "💊": "pillola", "🧪": "alchimia", "⚗": "alchimia", "🔮": "anima", "↩": "fuggi", "🏃": "fuggi", "✦": "scintilla", "✴": "luce", "☀": "luce",
    "✊": "pugno", "🔥": "fuoco", "💧": "acqua", "⛰": "terra", "🗿": "terra", "🌪": "vento", "🕳": "abisso",
    "♥": "cuore", "❤": "cuore", "💎": "pietre", "💠": "pietre", "◆": "pietre", "🎖": "fama", "⭐": "fama", "👑": "corona", "🏆": "trofeo", "🏟": "duello",
    "🩸": "sangue", "🩹": "ferita", "🏪": "mercato", "⚖": "bilancia", "⚒": "forgia", "🔨": "forgia", "📖": "libro", "🎓": "libro", "📋": "lista",
    "🐉": "bestia", "🏴": "setta_missione", "🏠": "casa", "⌂": "casa", "🪟": "porta", "🚪": "porta",
    "💍": "anello", "💰": "moneta", "📅": "calendario", "✉": "lettera", "✎": "penna", "✔": "ok", "✓": "ok", "⚠": "allerta",
    "💀": "teschio", "☠": "teschio", "🕸": "ragnatela", "🧓": "persona", "👤": "persona", "🧥": "abito", "☁": "nuvola", "☸": "dao",
    "❄": "ghiaccio", "💫": "stordito", "🎵": "musica", "🔊": "suono", "⤢": "espandi", "◐": "contrasto", "✨": "cura",
    "★": "fama", "☆": "fama", "🥇": "medaglia", "🥈": "medaglia", "🥉": "medaglia", "✝": "tomba", "✚": "piu", "⚱": "urna", "♛": "corona", "⛓": "catena",
    "📚": "libri", "🎙": "microfono", "🔈": "suono", "⏳": "clessidra", "⌛": "clessidra", "🎲": "dado", "🌱": "germoglio", "🧬": "elica", "🖼": "quadro",
    "🐛": "verme", "⚑": "setta_missione", "💬": "parla", "🗣": "parla", "🌳": "albero", "💥": "esplosione", "🥚": "uovo", "❓": "domanda", "🫀": "cuore",
    "🏞": "paesaggio", "🌅": "alba", "🌇": "alba", "🌧": "pioggia", "🌫": "nebbia", "🍃": "foglia", "⛈": "tribolazione", "👹": "demone", "😈": "demone", "👻": "spettro",
    "🤺": "duello", "📈": "grafico", "📄": "foglio", "🛒": "mercato", "🕊": "colomba", "🔒": "lucchetto", "🎭": "maschera", "🔍": "osserva", "🎁": "dono",
    "🌊": "acqua", "🍀": "fortuna", "🤖": "automa", "🕯": "candela", "🌗": "contrasto", "🜂": "fuoco", "⏸": "pausa", "▶": "avvia", "►": "avvia", "■": "ferma",
    "✖": "chiudi", "✕": "chiudi", "✗": "chiudi", "✘": "chiudi", "❖": "losanga", "◈": "bersaglio", "◉": "bersaglio", "◎": "bersaglio", "⟡": "scintilla",
    "☰": "menu", "↺": "ripeti", "🐟": "pesce", "🎣": "pesce", "🧙": "persona", "🧑": "persona", "🔔": "allerta", "⏱": "clessidra", "🌙": "dormi", "🌠": "scintilla", "🌟": "fama", "💡": "luce"
  };
  // ambiguità risolte dal contesto: le carte del duello usano le icone degli elementi
  var EMOJI_EL = { "⚙": "metallo", "✺": "luce", "☾": "oscurita", "☯": "concentrati", "⚡": "fulmine", "✦": "tecnica", "🛡": "difendi", "⚔": "attacca", "🔥": "fuoco", "🩸": "sangue", "🌀": "tempra" };

  function forEmoji(emoji, ctx) {
    if (emoji == null) return null;
    var e = String(emoji).replace(/[︎️‍]/g, "").trim();
    if (!e) return null;
    if (ctx === "el" && EMOJI_EL[e]) return EMOJI_EL[e];
    return EMOJI[e] || null;
  }

  /* ---------- comando -> icona ---------- */
  var ELEMENTI = { fuoco: 1, acqua: 1, legno: 1, metallo: 1, terra: 1, fulmine: 1, vento: 1, luce: 1, oscurita: 1, abisso: 1, anima: 1, sangue: 1, pugno: 1, corpo: 1, spada: 1 };
  var CMD1 = {
    train: "allenati", allena: "allenati", allenati: "allenati", medita: "medita", meditate: "medita", ritiro: "medita",
    breakthrough: "sfonda", sfonda: "sfonda", tribulation: "tribolazione", tribolazione: "tribolazione", tempra: "tempra",
    sleep: "dormi", dormi: "dormi", rest: "dormi", riposa: "dormi", raccogli: "raccogli", autoraccolta: "raccogli", autoassorbi: "raccogli",
    gather: "raccolta", raccolta: "raccolta", osserva: "osserva", guarda: "osserva", look: "osserva", examine: "osserva", indaga: "osserva",
    talk: "parla", parla: "parla", say: "parla", attack: "attacca", attacca: "attacca", duello: "duello", duel: "duello",
    mappa: "mappa", map: "mappa", mercato: "mercato", market: "mercato", asta: "bilancia", salva: "salva", save: "salva",
    setta: "setta", sect: "setta", dimora: "casa", casa: "casa", esplora: "esplora", explore: "esplora", viaggia: "viaggia", travel: "viaggia",
    move: "viaggia", vai: "viaggia", go: "viaggia", evadi: "fuggi", fuggi: "fuggi", flee: "fuggi", scappa: "fuggi",
    forgia: "forgia", forge: "forgia", alchimia: "alchimia", alchemy: "alchimia", libro: "libro", zaino: "tesori", inventario: "tesori", inventory: "tesori",
    use: "pillola", usa: "pillola", equip: "spada", indossa: "spada", sali: "scala_su", su: "scala_su", up: "scala_su", scendi: "scala_giu", giu: "scala_giu", down: "scala_giu",
    esci: "uscita", leave: "uscita", bacheca: "setta_missione", missione: "setta_missione", missioni: "setta_missione",
    cronaca: "storia", trame: "storia", storia: "storia", album: "libro", iscriviti: "fama", favori: "cuore", legami: "cuore",
    compra: "moneta", buy: "moneta", vendi: "moneta", sell: "moneta", encounter: "osserva", opzioni: "opzioni", options: "opzioni",
    oggi: "oggi", via: "via", seguaci: "seguaci", mondo: "mondo", tesori: "tesori", dao: "dao", compressione: "compressione", compress: "compressione",
    cura: "cura", heal: "cura", spiriti: "spiriti", saga: "saga", caccia: "caccia", hunt: "caccia", lancia: "lancia", spada: "spada", pugno: "pugno"
  };
  function forCmd(cmd) {
    if (cmd == null) return null;
    var c = String(cmd).trim().toLowerCase().replace(/\s*~q\d+\s*$/, "");
    if (!c) return null;
    var w = c.split(/\s+/), a = w[0], b = w[1] || "";
    if (a === "duello_azione") {
      if (b === "colpisci" || b === "attacca") return "attacca";
      if (b === "difendi") return "difendi";
      if (b === "concentrati") return "concentrati";
      if (b === "pillola") return "pillola";
      if (b === "fuggi") return "fuggi";
      if (b === "tecnica" || b === "mossa") return w[2] && ELEMENTI[w[2]] ? w[2] : "tecnica";
      return ELEMENTI[b] ? b : "tecnica";
    }
    if (a === "spiriti") return "spiriti";
    if (a === "tesori") return b === "cura" ? "cura" : "tesori";
    if (a === "attack" && (b === "creatures" || b === "creature" || b === "creature")) return "caccia";
    if (a === "via" && b) return "via";
    if (a === "ritiro") return "medita";
    if (a === "equip" && (b === "scomponi" || b === "forgia")) return "forgia";
    if (a === "gather" || a === "raccolta") return "raccolta";
    if (/^[0-9]+$/.test(a)) return null;
    return CMD1[a] || null;
  }

  /* ---------- upgrade del DOM ---------- */
  var SEL_BOX = ".ic, .ti, .ci, .si";
  // un solo pittogramma "grafico" (emoji o simbolo): niente lettere o numeri normali
  var GLYPH = /^[^\w\s.,;:'"()\[\]\-+*\/%!?<>=&#@]{1,4}$/u;
  var SKIP = "#log, textarea, input, select, option, script, style, svg, [contenteditable], .no-ic";

  function ctxOf(el) {
    var p = el.closest ? el.closest("[data-cmd]") : null;
    return { cmd: p ? p.getAttribute("data-cmd") : null, node: p };
  }
  function elementClass(node) {
    if (!node || !node.className || typeof node.className !== "string") return null;
    var m = node.className.match(/(?:^|\s)el-([a-z]+)/);
    return m && ELEMENTI[m[1]] ? m[1] : null;
  }
  function make(name, size, cls, glyph) {
    var holder = document.createElement("span");
    holder.innerHTML = svg(name, size, cls);
    var s = holder.firstChild;
    if (s && glyph) s.setAttribute("data-emoji", glyph);
    return s;
  }

  // contenitore con il solo glifo: <span class="ic">☯</span>
  function swapBox(el) {
    if (el.namespaceURI === "http://www.w3.org/2000/svg") return false;
    var kids = el.childNodes, tn = null, i;
    for (i = 0; i < kids.length; i++) {
      if (kids[i].nodeType === 3 && kids[i].nodeValue.trim()) { if (tn) return false; tn = kids[i]; }
      else if (kids[i].nodeType === 1 && kids[i].tagName !== "KBD") return false;
    }
    if (!tn) return false;
    var glyph = tn.nodeValue.trim();
    if (!GLYPH.test(glyph)) return false;
    var c = ctxOf(el), isCard = el.classList.contains("ci"), name = null;
    if (isCard) name = elementClass(c.node) || forEmoji(glyph, "el") || forCmd(c.cmd);
    else if (el.classList.contains("si")) name = forEmoji(glyph);
    else name = forEmoji(glyph) || forCmd(c.cmd);
    if (!name) return false;
    el.insertBefore(make(name, "1.15em", "", glyph), tn);
    el.removeChild(tn);
    el.setAttribute("data-ic-done", "1");
    el.setAttribute("data-emoji", glyph);
    if (!el.getAttribute("aria-label") && !(el.closest && el.closest("button[title], [aria-label]"))) { el.setAttribute("role", "img"); el.setAttribute("aria-label", glyph); }
    if (!el.getAttribute("title") && !(el.closest && el.closest("button, [title]"))) el.setAttribute("title", glyph);
    return true;
  }

  // un gruppo di simboli attaccati ("🌌⏳🎲") diventa una fila di icone
  function clusters(tok) {
    var out = [], cur = "";
    Array.from(tok).forEach(function (ch) {
      if (/[︎️‍]/.test(ch)) { cur += ch; return; }
      if (cur) out.push(cur);
      cur = ch;
    });
    if (cur) out.push(cur);
    return out;
  }

  // testo con pittogrammi: "☯ Allenati", "🏯 Oggi", "Alza ♥ Legami", oppure solo "🔎"
  function swapText(tn) {
    var par = tn.parentNode;
    if (!par || par.nodeType !== 1 || (par.closest && (par.closest(SKIP) || (par.closest("pre, code") && !par.closest("button"))))) return false;
    var val = tn.nodeValue;
    if (val.length > 400) return false;
    var parts = val.split(/(\s+)/), btn = par.closest("[data-cmd]"), inCard = par.closest(".ci, .eltag"), changed = false, onlyGlyph = true;
    var frag = document.createDocumentFragment(), buf = "";
    function flushText() { if (buf) { frag.appendChild(document.createTextNode(buf)); buf = ""; } }
    parts.forEach(function (tok, idx) {
      if (!tok || /^\s+$/.test(tok)) { buf += tok; return; }
      var names = null;
      if (GLYPH.test(tok) || /^[^\w\s]{1,8}$/u.test(tok)) {
        var cl = clusters(tok), one = null;
        if (cl.length === 1) {
          if (inCard) one = elementClass(inCard) || forEmoji(tok, "el") || forEmoji(tok);
          else if (par.id === "primary") one = "allenati";
          else if (idx === 0 && btn && btn.tagName === "BUTTON" && !btn.classList.contains("chip") && !btn.hasAttribute("data-palace")) one = forCmd(btn.getAttribute("data-cmd")) || forEmoji(tok);
          else one = forEmoji(tok);
          if (one) names = [one];
        } else {
          var all = cl.map(function (c) { return forEmoji(c); });
          if (all.every(Boolean)) names = all;
        }
      }
      if (!names) { buf += tok; onlyGlyph = false; return; }
      flushText();
      names.forEach(function (nm, k) { frag.appendChild(make(nm, "1.12em", "ic-lead", tok)); });
      changed = true;
    });
    if (!changed) return false;
    flushText();
    par.replaceChild(frag, tn);
    if (onlyGlyph && par.tagName === "BUTTON" && !par.getAttribute("aria-label")) par.setAttribute("aria-label", par.getAttribute("title") || val.trim());
    return true;
  }

  function upgrade(root) {
    root = root || document;
    if (!root.querySelectorAll || (root.nodeType === 1 && root.namespaceURI === "http://www.w3.org/2000/svg")) return 0;
    var n = 0;
    if (root.nodeType === 1 && root.closest && root.closest("#log")) return 0;
    if (root.nodeType === 1 && root.matches && root.matches(SEL_BOX) && swapBox(root)) n++;
    Array.prototype.forEach.call(root.querySelectorAll(SEL_BOX), function (el) { if (swapBox(el)) n++; });
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), list = [], t;
    while ((t = w.nextNode())) { if (/[^\x00-\u2000]/.test(t.nodeValue)) list.push(t); }
    list.forEach(function (tn) { if (swapText(tn)) n++; });
    return n;
  }

  /* osservatore: porta le nuove porzioni di DOM nello stesso stile senza chiedere nulla agli altri script */
  var queue = [], queued = false, obs = null;
  function flush() {
    queued = false;
    var items = queue; queue = [];
    items.forEach(function (el) { if (el.isConnected) { try { upgrade(el); } catch (e) { /* un errore non deve fermare gli altri */ } } });
  }
  function enqueue(el) {
    if (!el || el.nodeType !== 1 || el.namespaceURI === "http://www.w3.org/2000/svg") return;
    queue.push(el);
    if (!queued) { queued = true; (window.requestAnimationFrame || setTimeout)(flush); }
  }
  function observe() {
    if (obs || !window.MutationObserver || !document.body) return;
    obs = new MutationObserver(function (list) {
      list.forEach(function (m) {
        if (m.type === "characterData") { enqueue(m.target.parentNode); return; }
        var hasText = false;
        Array.prototype.forEach.call(m.addedNodes, function (nd) { if (nd.nodeType === 1) enqueue(nd); else if (nd.nodeType === 3) hasText = true; });
        if (hasText) enqueue(m.target);
      });
    });
    obs.observe(document.body, { childList: true, subtree: true, characterData: true });
    enqueue(document.body);
  }
  if (typeof document !== "undefined" && document.addEventListener) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", observe); else observe();
  }

  window.Icons = { svg: svg, has: has, names: names, forEmoji: forEmoji, forCmd: forCmd, upgrade: upgrade, observe: observe };
})();
