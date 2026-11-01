"""
I RIVALI CRESCONO CON LE TUE STESSE REGOLE (Aggiornamento 79).

I prodigi della tua generazione non si limitano a salire di regno: come te aprono vie nuove, FONDONO i loro Dao,
trovano reperti dei maestri. Le voci te lo fanno sapere. E chi ti ha superato da un pezzo prima o poi viene a
cercarti per una sfida davanti a tutti: accettarla è un duello d'onore; rifiutarla costa fama.

Le leggi che i rivali imparano sono vere: le fusioni e le vie nuove danno loro i punti dei Dao in combattimento
e i loro stati (gelo, veleno…). Tutto in `daily`, chiamata con i prodigi.
"""

from __future__ import annotations

import random

from engine.systems import state

P_NEW_WAY = 0.025
P_FUSE = 0.02
P_RELIC = 0.02
CHALLENGE_AFTER = 10             # giorni sopra di te prima di venirti a sfidare
P_CHALLENGE = 0.12


def _npc_daos(conn, nid: int) -> dict[str, int]:
    return {r["dao_key"]: int(r["comprehension"] or 0) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos WHERE character_type='npc' AND character_id=? "
        "AND comprehension>0;", (nid,))}


def _give(conn, nid: int, key: str, comp: int) -> None:
    from engine.generators import dao_gen
    dao_gen.seed_daos(conn)
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES ('npc', ?, ?, 60, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "comprehension=MAX(character_daos.comprehension, excluded.comprehension), practiced=1;", (nid, key, comp))


def _name(conn, nid: int) -> str:
    return conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]


def grow(conn, nid: int, rng: random.Random) -> str | None:
    """Un giorno di un prodigio: forse una via nuova, una fusione, un reperto. Ritorna la voce che corre."""
    from engine.systems import dao_laws, dao_insight
    from engine.systems.dao_techniques import _dao_label
    mine = _npc_daos(conn, nid)
    if not mine:
        return None
    r = rng.random()
    if r < P_FUSE:
        for fk, row in dao_laws.FUSED.items():
            if fk in mine or fk == "via_unica":
                continue
            if all(mine.get(c, 0) >= max(10, int(v * 0.6)) for c, v in row[2].items()):
                start = max(10, sum(mine[c] for c in row[2]) // 4)
                _give(conn, nid, fk, start)
                return f"Voci dal mondo: {_name(conn, nid)} si è chiuso in ritiro e ne è uscito con il {row[1]}."
    if r < P_FUSE + P_NEW_WAY:
        top = max(mine, key=mine.get)
        cand = [k for k in dao_insight.NEAR.get(top, []) if k not in mine and k in dao_laws.BY_KEY] or \
               [k for k, row in dao_laws.BY_KEY.items() if row[4][0] == "scelta" and k not in mine]
        if cand:
            k = rng.choice(sorted(cand))
            _give(conn, nid, k, rng.randint(10, 40))
            return f"Voci dal mondo: {_name(conn, nid)} ha aperto una via nuova, il {_dao_label(k)}."
    if r < P_FUSE + P_NEW_WAY + P_RELIC:
        k = max(mine, key=mine.get)
        gain = rng.randint(15, 40) + mine[k] // 20
        conn.execute("UPDATE character_daos SET comprehension=comprehension+? WHERE character_type='npc' "
                     "AND character_id=? AND dao_key=?;", (gain, nid, k))
        return (f"Voci dal mondo: {_name(conn, nid)} ha trovato la stele di un maestro antico; il suo "
                f"{_dao_label(k)} è andato più a fondo.")
    return None


def daily(conn, t: int, rng: random.Random, player, ids: list[int], above: set[int]) -> list[str]:
    out = []
    for nid in ids:
        v = grow(conn, nid, rng)
        if v:
            out.append(v)
    out += _challenge(conn, t, rng, player, above)
    return out


def _challenge(conn, t: int, rng: random.Random, player, above: set[int]) -> list[str]:
    """Chi ti ha superato da tempo viene a sfidarti davanti a tutti."""
    from engine.systems import encounters, duel
    day = t // 120
    since = state.get_json(conn, "rival_above_since", {}) or {}
    since = {k: v for k, v in since.items() if int(k) in above}
    for nid in above:
        since.setdefault(str(nid), day)
    state.set_json(conn, "rival_above_since", since)
    if encounters.pending(conn) or duel.get(conn) or state.get_int(conn, "rival_challenge_day", -99) > day - 15:
        return []
    ready = [int(k) for k, d0 in since.items() if day - int(d0) >= CHALLENGE_AFTER]
    if not ready or rng.random() >= P_CHALLENGE:
        return []
    nid = rng.choice(sorted(ready))
    nm = _name(conn, nid)
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, nid))
    state.set(conn, "rival_challenge_day", str(day))
    first = nm.split()[0]
    sc = {"key": "sfida_rivale", "title": f"{nm} ti sfida", "event_type": "combat", "sticky": True,
          "text": (f"{nm} si fa largo tra la folla. «Da quanto tempo ti guardo dall'alto, eh? Tutti dicono che eri il "
                   f"più promettente. Dimostralo. Qui, davanti a loro.» Intorno a voi la gente si ferma a guardare."),
          "ctx": {"npc_id": nid, "npc_name": nm},
          "choices": [{"label": "Accetti la sfida (duello d'onore: chi perde cede, nessuno muore)", "effects": {},
                       "command": f"sfida_onore {first}"},
                      {"label": "Rifiuti: non è il momento (la gente ne parlerà)",
                       "effects": {"fame": -12, "text": f"{first} ride e se ne va. «Lo sapevo.» Le voci corrono."},
                       "command": None}]}
    txt = encounters.start_scene(conn, player, sc, force=True)
    return [txt] if txt else []


def accept(conn, player, arg: str) -> str:
    """Il duello d'onore con un rivale: si combatte nell'arena improvvisata della folla; chi perde cede."""
    from engine.systems import duel
    return duel.start(conn, player, arg, arena=True) or "Il tuo sfidante non è più qui."


def dao_line(conn, nid: int) -> str:
    """Per la scheda dei prodigi: le vie nuove e le fusioni che conosce."""
    from engine.systems import dao_laws
    from engine.systems.dao_techniques import _dao_label
    mine = _npc_daos(conn, nid)
    fused = [_dao_label(k) for k in mine if k in dao_laws.FUSED]
    new = [_dao_label(k) for k in mine if k in dao_laws.BY_KEY]
    parts = []
    if fused:
        parts.append("fusioni: " + ", ".join(fused))
    if new:
        parts.append("vie nuove: " + ", ".join(new))
    return " · ".join(parts)
