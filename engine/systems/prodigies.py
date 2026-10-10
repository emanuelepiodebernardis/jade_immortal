"""
RIVALI CHE VIVONO DAVVERO — i PRODIGI della tua generazione, e le cronache del mondo.

Il mondo non aspetta te. Una manciata di PRODIGI (i tuoi rivali, le tue nemesi, i
giovani più forti) coltiva ogni giorno per conto proprio, con il talento scelto all'inizio
per i rivali. E come te, trovano FORTUNE: un reame segreto, il sangue di una bestia
sacra, un maestro nascosto, un metodo perduto. Le voci ti raggiungono; se resti fermo,
ti superano — e te lo fanno sapere.

Intanto il mondo vive: nascono nuovi geni, i clan si sposano, le sette declinano.

  prodigi       i prodigi della tua generazione: regno, forza rispetto a te, fortune, dove sono
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "prodigies"
FORT_KEY = "prodigy_fortunes"
MAX = 8
FORTUNES = [
    ("reame", "è uscito da un reame segreto con un'eredità antica", 3),
    ("sangue", "ha assorbito il sangue di {beast}", 2),
    ("maestro", "è stato accolto da un maestro nascosto", 2),
    ("metodo", "ha trovato un metodo di coltivazione perduto", 2),
    ("illuminazione", "ha avuto un'illuminazione meditando su una cascata", 1),
]
_BEASTS = ["una Fenice", "un Drago Azzurro", "una Tigre Bianca", "un Qilin", "una Tartaruga Nera"]


def _alive(conn, nid: int) -> bool:
    r = conn.execute("SELECT status FROM npcs WHERE id=?;", (nid,)).fetchone()
    return bool(r) and r["status"] == "alive"


def roster(conn) -> list[int]:
    ids = [i for i in (state.get_json(conn, KEY, []) or []) if _alive(conn, i)]
    if len(ids) < MAX:
        ids = _refill(conn, ids)
    state.set_json(conn, KEY, ids)
    return ids


def _refill(conn, ids: list[int]) -> list[int]:
    from engine.systems import bonds, power
    bonds.ensure_table(conn)
    cand = [r["npc_id"] for r in conn.execute(
        "SELECT b.npc_id FROM bonds b JOIN npcs n ON n.id=b.npc_id WHERE b.player_id=1 AND "
        "b.kind IN ('rival','nemesis') AND b.status='active' AND n.status='alive';")]
    me = power.combat_rating(conn, "player", 1)
    young = conn.execute("SELECT id FROM npcs WHERE status='alive' AND COALESCE(kind,'human')='human' "
                         "AND archetype IN ('discepolo','vagabondo') AND location_id IS NOT NULL;").fetchall()
    young = sorted((r["id"] for r in young), key=lambda i: abs(power.combat_rating(conn, "npc", i) - me))
    for i in cand + young:
        if i not in ids:
            ids.append(i)
        if len(ids) >= MAX:
            break
    return ids


def fortunes(conn) -> dict:
    return state.get_json(conn, FORT_KEY, {}) or {}


def _add_fortune(conn, nid: int, text: str) -> None:
    d = fortunes(conn)
    d.setdefault(str(nid), []).append(text)
    d[str(nid)] = d[str(nid)][-4:]
    state.set_json(conn, FORT_KEY, d)


def has_blood(conn, nid: int) -> bool:
    return any("sangue" in f for f in fortunes(conn).get(str(nid), []))


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import npc_factory, destinies, power
    mult = destinies.rival_mult(conn)
    ids = roster(conn)
    out = []
    me = power.combat_rating(conn, "player", player.id)
    above = set(state.get_json(conn, "prodigies_above", []) or [])
    new_above = set()
    for nid in ids:
        if rng.random() < 0.30 * mult:
            npc_factory.raise_npc(conn, nid, 1)
        if rng.random() < 0.035 * mult:
            kind, txt, stages = rng.choice(FORTUNES)
            txt = txt.format(beast=rng.choice(_BEASTS))
            npc_factory.raise_npc(conn, nid, stages + (1 if mult > 1.2 else 0))
            if kind in ("maestro", "illuminazione"):
                conn.execute("UPDATE character_daos SET comprehension=comprehension+10 "
                             "WHERE character_type='npc' AND character_id=?;", (nid,))
            _add_fortune(conn, nid, kind if kind != "sangue" else f"sangue: {txt.split('di ', 1)[-1]}")
            nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
            out.append(f"Voci dal mondo: {nm} {txt}.")
        if power.combat_rating(conn, "npc", nid) > me:
            new_above.add(nid)
    for nid in new_above - above:
        nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        out.append(f"⚠ {nm} ti ha superato: ora è più forte di te. Si dice che lo vada raccontando in giro.")
    for nid in above - new_above:
        if _alive(conn, nid):
            nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
            out.append(f"Hai superato {nm}: ora sei tu il più forte dei due.")
    state.set_json(conn, "prodigies_above", sorted(new_above))
    out += _chronicle(conn, t, rng, player)
    return out


def _chronicle(conn, t: int, rng: random.Random, player) -> list[str]:
    """Il mondo che vive: geni che emergono, clan che si alleano, sette che declinano."""
    r = rng.random()
    if r < 0.03:
        from engine.systems import npc_factory
        from engine.simulation import cultivation
        city = conn.execute("SELECT id, name FROM locations WHERE location_type='city' ORDER BY RANDOM() LIMIT 1;").fetchone()
        if not city:
            return []
        ptier = cultivation.realm_tier(conn, "player", player.id) or 1
        nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=city["id"],
                                tier=ptier, stage=rng.randint(4, 9), traits={"ambition": 90, "pride": 80}, tick=t)
        nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        ids = state.get_json(conn, KEY, []) or []
        if len(ids) < MAX + 2:
            ids.append(nid)
            state.set_json(conn, KEY, ids)
        return [f"Cronache: a {city['name']} è emerso un nuovo genio, {nm}. Dicono che non abbia rivali."]
    if r < 0.05:
        fs = conn.execute("SELECT id, name FROM factions WHERE status='active' ORDER BY RANDOM() LIMIT 2;").fetchall()
        if len(fs) == 2:
            a, b = sorted((fs[0]["id"], fs[1]["id"]))
            conn.execute(
                "INSERT INTO faction_relations (faction_a, faction_b, relation_score, relation_type, reason, "
                "last_updated_tick) VALUES (?, ?, 20, 'alleati', 'matrimonio', ?) "
                "ON CONFLICT(faction_a, faction_b) DO UPDATE SET relation_score=MIN(100, relation_score+20), "
                "reason='matrimonio', last_updated_tick=excluded.last_updated_tick;", (a, b, t))
            return [f"Cronache: un matrimonio unisce {fs[0]['name']} e {fs[1]['name']}. Le due sette ora sono vicine."]
    if r < 0.065:
        f = conn.execute("SELECT id, name FROM factions WHERE status='active' ORDER BY RANDOM() LIMIT 1;").fetchone()
        if f:
            conn.execute("UPDATE factions SET influence=MAX(0, influence-15) WHERE id=?;", (f["id"],))
            return [f"Cronache: la {f['name']} attraversa un periodo buio; la sua influenza declina."]
    return []


def enemy_bonus(conn, npc_id: int, fx) -> list[str]:
    """Un prodigio che ha assorbito sangue sacro combatte più forte."""
    if not has_blood(conn, npc_id):
        return []
    fx.e.atk_mult *= 1.15
    return [f"Il sangue sacro ribolle in {fx.e.name}: è più forte di quanto sembri."]


def describe(conn, player) -> str:
    from engine.systems import perception
    from engine.simulation import cultivation
    ids = roster(conn)
    if not ids:
        return "Nessun prodigio della tua generazione si è ancora fatto notare."
    fz = fortunes(conn)
    lines = ["✦ I PRODIGI DELLA TUA GENERAZIONE ✦"]
    for nid in ids:
        r = conn.execute("SELECT n.name, l.name AS loc FROM npcs n LEFT JOIN locations l ON l.id=n.location_id "
                         "WHERE n.id=?;", (nid,)).fetchone()
        f = fz.get(str(nid), [])
        lines.append(f"  · {r['name']} — {cultivation.realm_label(conn, 'npc', nid)} — "
                     f"{perception.relative_strength(conn, player.id, nid)}"
                     + (f" — a {r['loc']}" if r["loc"] else " — in ritiro, introvabile")
                     + (f"\n      fortune: {', '.join(f)}" if f else ""))
    return "\n".join(lines)
