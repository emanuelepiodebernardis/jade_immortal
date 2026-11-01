"""
IL LIBRO DELLA TUA VITA (Aggiornamento 83) — la cronaca come un libro illustrato da conservare.

Una pagina HTML pronta da stampare (o da salvare in PDF dal browser: Stampa → Salva come PDF):
frontespizio col ritratto, i titoli come sigilli, i Dao con le loro immagini, e i capitoli della vita — un capitolo
ogni trenta giorni, con i fatti della cronaca.
"""

from __future__ import annotations

import html
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMG = ROOT / "immagini"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII",
         "XVIII", "XIX", "XX"]


def _img(rel: str) -> str:
    for ext in (".jpg", ".png", ".webp"):
        if (IMG / (rel + ext)).is_file():
            return "/immagini/" + rel + ext
    return ""


def _chapter_title(entries: list) -> str:
    for r in entries:
        if r["kind"] == "regno":
            return r["text"]
    for r in entries:
        if r["kind"] in ("storia", "titolo"):
            return r["text"]
    return entries[0]["text"] if entries else ""


def build(conn) -> str:
    from engine.core import entities, tick
    from engine.simulation import cultivation
    from engine.systems import chronicle, state, dao_training, lifespan, dao_laws, personal_fusion
    p = entities.get_player(conn)
    if p is None:
        return "<p>Nessuna vita da raccontare.</p>"
    e = html.escape
    day = tick.get_tick(conn) // 120 + 1
    portrait = _img("ritratti/" + (state.get(conn, "hero_portrait") or "eroe")) or _img("ritratti/eroe")
    titles = state.titles(conn)[-24:]
    daos = list(dao_training.trainable_daos(conn, p.id))[:15]
    fused = [r for r in daos if r["dao_key"] in dao_laws.FUSED]
    personal = personal_fusion.all_(conn)
    rows = list(chronicle.entries(conn))
    chapters: list[tuple[int, list]] = []
    for r in rows:
        k = (r["tick"] // 120) // 30
        if not chapters or chapters[-1][0] != k:
            chapters.append((k, []))
        chapters[-1][1].append(r)
    life_no = state.get_int(conn, "life_no", 1)
    portrait_html = '<img class="portrait" src="' + portrait + '" alt="">' if portrait else ""

    out = [f"""<!doctype html><html lang="it"><head><meta charset="utf-8"><title>Il libro di {e(p.name)}</title>
<link rel="stylesheet" href="/static/fonts/fonts.css">
<style>
  @page {{ size: A5; margin: 16mm 14mm; }}
  :root {{ --ink:#2b2620; --muted:#7b7062; --jade:#2f7d64; --gold:#a9822e; --red:#b03a2e; --paper:#f6efe1; }}
  body {{ margin:0; background:#e9e0cd; color:var(--ink); font: 15px/1.6 "Cormorant Garamond", Georgia, serif; }}
  .page {{ background: var(--paper); max-width: 148mm; margin: 18px auto; padding: 18mm 15mm; box-shadow: 0 6px 30px #0003;
           background-image: radial-gradient(ellipse at 20% 10%, #fff8 0, transparent 60%), radial-gradient(ellipse at 80% 90%, #d9c9a466 0, transparent 60%);
           page-break-after: always; }}
  h1 {{ font-size: 34px; margin: 6px 0 2px; text-align:center; letter-spacing:.04em; }}
  h2 {{ font-size: 22px; margin: 0 0 4px; color: var(--jade); }}
  .hz {{ font-family: "Ma Shan Zheng", serif; color: var(--red); }}
  .center {{ text-align:center; }} .muted {{ color: var(--muted); }}
  .portrait {{ display:block; width: 54mm; height: 54mm; object-fit: cover; border-radius: 50%; margin: 14px auto;
               border: 3px solid var(--gold); box-shadow: 0 0 0 6px #fff8; }}
  .seals {{ display:flex; flex-wrap:wrap; gap:8px; justify-content:center; margin-top:14px; }}
  .seal {{ display:inline-flex; flex-direction:column; align-items:center; width: 30mm; font-size: 11px; text-align:center; }}
  .seal b {{ display:grid; place-items:center; width: 40px; height: 40px; background: var(--red); color: #fbe9dc;
             font: 22px "Ma Shan Zheng", serif; border-radius: 4px; transform: rotate(-4deg); box-shadow: inset 0 0 0 2px #fbe9dc88; }}
  .daos {{ display:grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-top: 10px; }}
  .dao {{ text-align:center; font-size: 12.5px; }} .dao img {{ width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 8px; }}
  .chap {{ border-top: 1px solid #c9b78f; padding-top: 10px; margin-top: 14px; }}
  .chap .n {{ font: 28px "Ma Shan Zheng", serif; color: var(--red); float:left; margin-right: 10px; line-height: 1; }}
  .ev {{ margin: 3px 0; }} .ev small {{ color: var(--muted); }}
  .print {{ position: fixed; right: 16px; top: 16px; font: 14px system-ui; padding: 8px 14px; border-radius: 8px; border: 0;
            background: var(--jade); color: #fff; cursor: pointer; }}
  @media print {{ body {{ background: none; }} .page {{ box-shadow:none; margin:0; max-width:none; }} .print {{ display:none; }} }}
</style></head><body>
<button class="print" onclick="window.print()">🖨 Stampa o salva in PDF</button>
<section class="page center">
  <div class="hz" style="font-size:44px">玉仙錄</div>
  <h1>Il libro di {e(p.name)}</h1>
  <div class="muted">vita {life_no} · giorno {day} · {e(cultivation.realm_label(conn, "player", p.id))} · età {e(lifespan.label(conn, p.id))}</div>
  {portrait_html}
  <div class="seals">""" + "".join(
        f'<span class="seal"><b>{_seal_char(t)}</b>{e(t)}</span>' for t in titles) + """</div>
</section>"""]
    if daos:
        cards = []
        for r in daos:
            u = _img("dao/" + r["dao_key"])
            pic = '<img src="' + u + '" alt="">' if u else ""
            cards.append(f'<div class="dao">{pic}<b>{e(r["name"])}</b><br>'
                         f'<small class="muted">comprensione {r["comprehension"]}</small></div>')
        out.append('<section class="page"><h2>Le vie che hai percorso</h2><div class="daos">' + "".join(cards) + "</div>")
        if fused or personal:
            out.append('<p class="muted" style="margin-top:12px">Fusioni: ' + ", ".join(
                [e(r["name"]) for r in fused] + [e(f["name"]) + " (la tua via)" for f in personal]) + ".</p>")
        out.append("</section>")
    if chapters:
        out.append('<section class="page"><h2>I capitoli della vita</h2>')
        for i, (k, ents) in enumerate(chapters):
            num = ROMAN[i] if i < len(ROMAN) else str(i + 1)
            out.append(f'<div class="chap"><span class="n">{num}</span><b>Giorni {k * 30 + 1}–{k * 30 + 30}</b>'
                       f'<div class="muted"><i>{e(_chapter_title(ents))}</i></div>')
            for r in ents[:14]:
                out.append(f'<div class="ev"><small>g.{r["tick"] // 120 + 1}</small> '
                           f'{e(chronicle.ICON.get(r["kind"], "·"))} {e(r["text"])}</div>')
            if len(ents) > 14:
                out.append(f'<div class="ev muted"><small>… e altri {len(ents) - 14} fatti.</small></div>')
            out.append("</div>")
        out.append("</section>")
    out.append("</body></html>")
    return "".join(out)


_HZ = [("drag", "龍"), ("spad", "劍"), ("ciel", "天"), ("re ", "王"), ("imperat", "帝"), ("immortal", "仙"), ("dao", "道"),
       ("fuoco", "火"), ("acqua", "水"), ("mort", "死"), ("vita", "生"), ("anim", "魂"), ("fondator", "祖"), ("padre", "祖"),
       ("prescelt", "選"), ("maestr", "師"), ("demon", "魔"), ("campion", "勝"), ("antenat", "祖"), ("yin", "陰")]


def _seal_char(title: str) -> str:
    t = (title or "").lower() + " "
    for k, c in _HZ:
        if k in t:
            return c
    return "印"
