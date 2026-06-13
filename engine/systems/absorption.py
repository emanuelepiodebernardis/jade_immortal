"""
Anomalia: Abisso Divoratore (v1).

Assorbi l'EREDITÀ di un caduto, non la sua potenza. Principi di design:
  - mai garantito: l'esito è randomico (comprensione, frammento di ricordo, o trauma);
  - rendimento decrescente per dislivello: più il bersaglio è forte di te, meno integri;
  - decadimento del cadavere: più tempo passa dalla morte, meno resta da assorbire;
  - l'ANIMA è il contenitore: un'anima forte integra meglio, una debole si contamina;
  - ogni assorbimento lascia un RESIDUO: si accumula e mina la stabilità (frammentazione).

Slottato per dopo: cadaveri leggendari/jackpot, personalità multiple, karma ereditato.
"""

from __future__ import annotations

import random
import sqlite3

from engine.systems import character
from engine.generators import dao_gen
from engine.simulation import cultivation, event_system as ev

DECAY_WINDOW = 200.0        # tick dopo i quali un cadavere è quasi inerte
RESIDUE_CAP = 1000


def can_absorb(conn: sqlite3.Connection, player_id: int = 1) -> bool:
    p = character.get_profile(conn, "player", player_id)
    return p is not None and p["anomaly"] == "abisso_divoratore"


def absorb(conn: sqlite3.Connection, tick: int, rng: random.Random,
           target_id: int, player_id: int = 1) -> dict:
    prof = character.get_profile(conn, "player", player_id)
    if prof is None or prof["anomaly"] != "abisso_divoratore":
        return {"status": "no_anomaly"}

    player = conn.execute(
        "SELECT location_id FROM players WHERE id=?;", (player_id,)).fetchone()
    npc = conn.execute(
        "SELECT id, name, location_id, status, death_tick FROM npcs WHERE id=?;",
        (target_id,)).fetchone()
    if npc is None:
        return {"status": "not_found"}
    if npc["location_id"] != player["location_id"]:
        return {"status": "not_here"}
    if npc["status"] not in ("dead",):
        return {"status": "not_dead"}

    ptier = cultivation.realm_tier(conn, "player", player_id)
    ttier = cultivation.realm_tier(conn, "npc", target_id)
    death_tick = npc["death_tick"] if npc["death_tick"] is not None else tick
    freshness = max(0.15, min(1.0, 1.0 - (tick - death_tick) / DECAY_WINDOW))

    soul = prof["aff_soul"]
    residue = prof["soul_residue"]
    overreach = max(0, ttier - ptier)     # assorbire più forti è pericoloso
    p_clean = max(0.05, min(0.95, soul / 100.0 * freshness
                            - overreach * 0.18 - residue * 0.0015))

    # Dao primario del bersaglio
    tdao = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type='npc' AND character_id=? "
        "ORDER BY comprehension DESC LIMIT 1;", (target_id,)).fetchone()

    roll = rng.random()
    consequences = []
    name = npc["name"]

    if roll < p_clean and tdao:
        # integrazione riuscita: rubi un'OPPORTUNITÀ (comprensione/affinità), non potenza
        p_aff = dao_gen.player_dao_affinity(conn, tdao["dao_key"], player_id)
        gain = max(1, int(tdao["comprehension"] * 0.18 * freshness
                          * (p_aff / 100.0) / (1 + max(0, ptier - ttier) * 0.2)))
        _raise_comprehension(conn, tdao["dao_key"], gain, player_id)
        residue_gain = 2 + overreach
        outcome = {"status": "comprehension", "dao": tdao["dao_key"], "gain": gain}
        summary = f"Divori l'eredità di {name}: un frammento del suo Dao risuona in te."
        consequences.append(ev.Consequence(
            "player", player_id, "dao_fragment",
            f"+{gain} comprensione in {tdao['dao_key']}", visibility="hidden",
            resolve_tick=tick))
    else:
        # contaminazione: trauma e residuo elevato
        residue_gain = 5 + overreach * 3
        outcome = {"status": "trauma"}
        summary = f"Divori {name}, ma l'eredità ti contamina: echi non tuoi ti attraversano."
        consequences.append(ev.Consequence(
            "player", player_id, "soul_trauma", "frammento estraneo e instabile",
            visibility="hidden", resolve_tick=tick))
        # catastrofe rara: anima debole + bersaglio molto superiore
        if overreach >= 3 and soul < 60 and rng.random() < 0.25:
            conn.execute("UPDATE players SET status='dead' WHERE id=?;", (player_id,))
            outcome = {"status": "shattered"}
            summary = f"L'eredità di {name} è troppo vasta: la tua anima si frantuma."
            consequences.append(ev.Consequence(
                "player", player_id, "death", "anima frantumata dall'assorbimento",
                visibility="hidden", resolve_tick=tick))

    new_residue = max(0, min(RESIDUE_CAP, residue + residue_gain))
    conn.execute(
        "UPDATE character_profiles SET soul_residue=? "
        "WHERE character_type='player' AND character_id=?;", (new_residue, player_id))
    # karma: l'atto è negativo e EREDITI parte del karma (debiti) della vittima
    from engine.systems import karma
    karma.on_absorb(conn, tick, player_id, target_id, name)
    conn.execute("UPDATE npcs SET status='absorbed' WHERE id=?;", (target_id,))

    ev.log_event(
        conn, event_type="absorption", tick=tick, location_id=npc["location_id"],
        title=f"Assorbimento di {name}",
        summary=summary,
        participants=[ev.Participant("player", player_id, "initiator"),
                      ev.Participant("npc", target_id, "victim")],
        consequences=consequences + [ev.Consequence(
            "player", player_id, "soul_residue", f"residuo +{residue_gain}",
            visibility="hidden", resolve_tick=tick)],
    )
    outcome["residue"] = new_residue
    return outcome


def _raise_comprehension(conn, dao_key, gain, player_id) -> None:
    row = conn.execute(
        "SELECT comprehension, affinity FROM character_daos "
        "WHERE character_type='player' AND character_id=? AND dao_key=?;",
        (player_id, dao_key)).fetchone()
    if row is None:
        # primo frammento di un Dao mai praticato: nasce dalla tua affinità latente
        conn.execute(
            "INSERT INTO character_daos "
            "(character_type, character_id, dao_key, affinity, comprehension, practiced) "
            "VALUES ('player', ?, ?, 50, ?, 0);", (player_id, dao_key, min(100, gain)))
        return
    conn.execute(
        "UPDATE character_daos SET comprehension=?, affinity=? "
        "WHERE character_type='player' AND character_id=? AND dao_key=?;",
        (min(100, row["comprehension"] + gain), min(100, row["affinity"] + 1),
         player_id, dao_key))


def residue_label(residue: int) -> str:
    if residue == 0:
        return "limpida"
    if residue < 40:
        return "lievemente offuscata"
    if residue < 120:
        return "attraversata da echi estranei"
    if residue < 300:
        return "affollata di voci non tue"
    return "sull'orlo della frammentazione"
