"""
I CORPI DEI NEMICI — anche gli altri nascono con un corpo leggendario, e chi li sconfigge lo prende.

  · Tra i coltivatori forti (dal 3° regno in su) alcuni portano un CORPO LEGGENDARIO: più sono alti,
    più è probabile (i patriarchi, gli anziani e i geni più di tutti). Combattono più forte (+20%)
    e il tuo pannello «presenti» lo mostra.
  · Sconfitti, lasciano un'ESSENZA DEL CORPO. Assorbirla ('use essenza del corpo'):
      - se non hai un corpo leggendario, diventa tuo (sigillato, come alla nascita);
      - se è lo stesso corpo che hai, il tuo si risveglia di uno stadio;
      - se è diverso, tenti la FUSIONE: riuscita (60% +5% per stadio del tuo corpo, fino al 95%),
        il tuo corpo diventa un CORPO FUSO che porta anche i DONI dell'altro (a metà forza, senza
        le sue maledizioni), la sua prima tecnica e le sue affinità di sangue. Fallita, l'essenza si
        disperde e ti ferisce. Si fonde senza limite: ogni corpo assorbito si aggiunge agli altri.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

NPC_MULT = 1.2
_RANK_BONUS = {"patriarca": 0.12, "anziano": 0.08, "prodigio": 0.12, "genio": 0.12, "maestro": 0.06}


def _salt(conn) -> int:
    s = state.get_int(conn, "body_salt", 0)
    if not s:
        s = random.randrange(1, 10 ** 9)
        state.set(conn, "body_salt", str(s))
    return s


def npc_body(conn, npc_id: int) -> str | None:
    """Il corpo leggendario di un NPC (deterministico: niente da salvare), o None."""
    from engine.systems import constitutions
    from engine.simulation import cultivation
    r = conn.execute("SELECT kind, archetype, status FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not r or (r["kind"] or "human") != "human":
        return None
    tier = cultivation.realm_tier(conn, "npc", npc_id) or 1
    if tier < 3:
        return None
    rng = random.Random(npc_id * 7919 + _salt(conn))
    p = min(0.2, 0.02 + 0.01 * (tier - 3) + _RANK_BONUS.get((r["archetype"] or "").lower(), 0.0))
    if rng.random() >= p:
        return None
    keys = [k for k in constitutions.BODIES if k != "spezzati"]
    return rng.choices(keys, weights=[constitutions.BODIES[k][3] for k in keys])[0]


def npc_mult(conn, npc_id: int) -> float:
    return NPC_MULT if npc_body(conn, npc_id) else 1.0


def on_kill(conn, t: int, rng, player, npc_id: int) -> list[str]:
    from engine.systems import constitutions, items
    key = npc_body(conn, npc_id)
    if not key:
        return []
    nm = constitutions.BODIES[key][0]
    iname = f"Essenza del Corpo: {nm}"
    iid = items.create_item(conn, iname, "essenza_corpo", "leggendario",
                            f"Ciò che resta del {nm} di chi hai sconfitto. Assorbilo con 'use'.", {"body_essence": key})
    items.grant(conn, "player", player.id, iid)
    return [f"✦ Dal corpo del caduto si leva una luce: il suo {nm}. Raccogli l'{iname} "
            f"('use essenza del corpo' per assorbirla)."]


def absorb(conn, t: int, rng: random.Random, player_id: int, key: str) -> list[str]:
    from engine.systems import constitutions, heart_demon
    if key not in constitutions.BODIES:
        return ["L'essenza si dissolve: non c'è più nulla da assorbire."]
    nm = constitutions.BODIES[key][0]
    c = constitutions.get(conn)
    if not c:
        return [constitutions.grant(conn, key).replace("Nasci con", "Assorbi")]
    if c["key"] == key or key in (c.get("absorbed") or []):
        return [f"Il {nm} riconosce sé stesso nel tuo corpo e vi si scioglie."] + \
            constitutions.awaken(conn, "hai assorbito un corpo gemello")
    st = int(c.get("stage", 0))
    p = min(0.95, 0.60 + 0.05 * st)
    if rng.random() >= p:
        conn.execute(
            "INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, healed, "
            "heal_tick) VALUES ('player', ?, 3, 'rigetto di un corpo estraneo', ?, 0, ?);", (player_id, t, t + 120))
        heart_demon.add_bonus(conn, -0.04)
        return [f"✖ Il {nm} rifiuta il tuo corpo: l'essenza esplode nei meridiani e si disperde. Ne esci ferito "
                f"(riuscita era {int(100 * p)}%: più il tuo corpo è risvegliato, più è facile)."]
    c.setdefault("absorbed", []).append(key)
    state.set_json(conn, constitutions.KEY, c)
    out = [f"✦ FUSIONE DEI CORPI: il {nm} si scioglie nel tuo {constitutions.BODIES[c['key']][0]}. ✦",
           f"Ora sei: {constitutions.display_name(c)}.",
           "Porti anche i suoi doni (a metà forza, senza la sua maledizione) e le sue affinità di sangue."]
    from engine.systems import body_powers
    pw = body_powers.POWERS.get(key)
    if pw:
        name, eff, _tale = pw[0]
        conn.execute("INSERT OR IGNORE INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, "
                     "learned_tick) VALUES (?, NULL, ?, ?, ?, ?);", (player_id, f"bodyfuse:{key}", name,
                                                                   round(eff.get("tech", 0.1), 3), t))
        out.append(f"✧ Impari la sua tecnica: «{name}».")
    n = len(c["absorbed"])
    for title, cond in (("Corpo Fuso", n == 1), ("Crogiolo dei Corpi", n == 3), ("Mille Corpi in Uno", n == 7)):
        if cond and state.grant_title(conn, title):
            out.append(f"✧ Nuovo titolo: «{title}» ✧")
    return out
