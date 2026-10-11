"""
TESORI — un solo pannello per tutto ciò che porti con te e fai crescere.

Arma viva, maestro nell'anello, spazio interiore, Gu, marionette e tesori legati al sangue,
bandiera delle anime, elementi celesti, cloni: prima erano otto comandi da ricordare.

  tesori              il quadro di tutto, una riga (o due) per tesoro, con il comando utile
  tesori cura         la cura quotidiana in un colpo: raccogli lo spazio interiore e
                      risemini, nutri il maestro dell'anello coi nuclei che hai, sfami i Gu
  tesori <nome>       il dettaglio di uno (arma, anello, spazio, gu, marionette, bandiera,
                      elementi, cloni) — gli stessi comandi di prima restano validi
"""

from __future__ import annotations

from engine.core import tick as tick_mod


def _lines(conn, player) -> list[tuple[str, str, str]]:
    """[(chiave, riga, comando)] dei tesori che possiedi."""
    from engine.systems import (weapon_spirit, mentor_ring, inner_space, gu, puppets, soul_war,
                                celestial_elements, clones)
    out = []
    w = weapon_spirit.describe(conn, player.id)
    if w:
        out.append(("arma", "⚔ " + w, "arma"))
    r = mentor_ring.get(conn)
    if r:
        out.append(("anello", f"💍 Maestro nell'anello: {r['name']} — livello {r.get('level', 0)}", "anello"))
    s = inner_space.get(conn)
    if s:
        day = tick_mod.get_tick(conn) // 120
        crop = ("campo vuoto" if not s.get("planted") else
                "raccolto MATURO" if day >= s["ready_day"] else "erbe in crescita")
        out.append(("spazio", f"✧ {inner_space.name_of(s['level'])} — {crop}", "spazio"))
    g = gu.gus(conn)
    if g:
        hungry = sum(1 for x in g if x.get("hunger"))
        out.append(("gu", f"🐛 Gu: {len(g)} nell'apertura" + (f" — {hungry} affamati!" if hungry else ""), "gu"))
    ps, ts = puppets.puppets(conn), puppets.treasures(conn)
    if ps:
        out.append(("marionette", f"⚙ Marionette: {len(ps)} (livelli {', '.join(str(p['level']) for p in ps)})",
                    "marionette"))
    if ts:
        out.append(("tesori_sangue", "✧ Tesori legati al sangue: " + ", ".join(
            f"{puppets.TREASURES[t['kind']][0]} {t['level']}" for t in ts), "tesori sangue"))
    f = soul_war.flag(conn)
    if f:
        out.append(("bandiera", f"🏴 Bandiera delle Anime — {f['souls']} anime", "bandiera"))
    el = celestial_elements.owned(conn)
    if el:
        out.append(("elementi", "✦ Elementi celesti: " + ", ".join(
            f"{celestial_elements.EL_LABEL[k]} ({celestial_elements.grade(v['power'])})" for k, v in el.items()),
            "elementi"))
    cs = clones.clones(conn)
    if cs:
        out.append(("cloni", f"☯ Cloni: {len(cs)} — " + ", ".join(f"n.{c['n']} liv.{c['level']}" for c in cs),
                    "clone"))
    return out


def describe(conn, player) -> str:
    ls = _lines(conn, player)
    if not ls:
        return ("Non porti ancora tesori che crescono con te. L'arma si risveglia con l'uso; anelli, spazi "
                "interiori, Gu, marionette ed elementi celesti si trovano nel mondo. ('svolte' per la strada)")
    out = ["✦ I TUOI TESORI ✦"]
    out += [f"  {ln}   ('{cmd}')" for _k, ln, cmd in ls]
    out.append("'tesori cura' per la cura quotidiana di tutti in una volta; 'tesori <nome>' per il dettaglio.")
    return "\n".join(out)


def care(conn, player) -> str:
    from engine.systems import inner_space, mentor_ring, professions, gu
    out = []
    s = inner_space.get(conn)
    if s:
        day = tick_mod.get_tick(conn) // 120
        if s.get("planted") and day >= s["ready_day"]:
            out.append(inner_space.harvest(conn, player))
        if not (inner_space.get(conn) or {}).get("planted"):
            herbs = professions.material(conn, player.id, "erbe")
            n = min(herbs, 10 * s["level"])
            if n > 0:
                out.append(inner_space.sow(conn, player, str(n)))
    if mentor_ring.get(conn) and professions.material(conn, player.id, "nuclei") > 0:
        need = mentor_ring.feed_need(mentor_ring.level(conn))
        out.append(mentor_ring.feed(conn, player, str(min(need, professions.material(conn, player.id, "nuclei")))))
    if any(x.get("hunger") for x in gu.gus(conn)):
        out.append("I tuoi Gu hanno fame: servono pietre spirituali ogni giorno (li nutri automaticamente se ne hai).")
    return "\n".join(out) if out else "Non c'è nulla da curare, per ora."


_DETAIL = {"arma": ("weapon_spirit", "full"), "anello": ("mentor_ring", "describe_cmd"),
           "spazio": ("inner_space", "describe"), "gu": ("gu", "describe"), "marionette": ("puppets", "describe"),
           "sangue": ("puppets", "describe"), "bandiera": ("soul_war", "describe"),
           "elementi": ("celestial_elements", "describe"), "cloni": ("clones", "describe")}


def command(conn, player, arg: str) -> str:
    a = arg.strip().lower()
    if a in ("cura", "care", "nutri"):
        return care(conn, player)
    if a in _DETAIL:
        import importlib
        mod_name, fn = _DETAIL[a]
        mod = importlib.import_module(f"engine.systems.{mod_name}")
        if fn == "describe_cmd":
            return mod.command(conn, player, "")
        return getattr(mod, fn)(conn, player)
    return describe(conn, player)
