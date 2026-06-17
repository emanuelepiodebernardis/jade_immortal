"""
Combat System (Fase 6).

Risoluzione NON lineare e a round (no "somma pesata = vincitore"):
  - ogni round i due combattenti si colpiscono a vicenda;
  - il danno ha varianza (caos controllato) e una probabilità di COLPO CRITICO
    che raddoppia il danno (soglia non lineare -> ribaltoni possibili);
  - le ferite attive riducono la potenza (stato dinamico);
  - chi scende a 0 vitalità perde; l'esito può essere ferita o morte.

Funziona per NPC vs NPC e NPC vs giocatore. Hook `_realm_factor` pronto per la
Fase 7 (la coltivazione moltiplicherà la potenza). Tutto tracciato (vincolo 26).
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities
from engine.simulation import event_system as ev

# Profilo base del giocatore (novizio capace). La coltivazione lo aumenterà (Fase 7).
PLAYER_BASE = {"attack": 32.0, "defense": 18.0, "vitality": 65.0}
CRIT_CHANCE = 0.12
CRIT_MULT = 2.0
MAX_ROUNDS = 30


# ---------- potenza ----------

def _active_injury_penalty(conn: sqlite3.Connection, ctype: str, cid: int) -> float:
    s = conn.execute(
        "SELECT COALESCE(SUM(severity),0) s FROM injuries "
        "WHERE character_type=? AND character_id=? AND healed=0;",
        (ctype, cid),
    ).fetchone()["s"]
    return min(0.6, s * 0.03)   # max -60%


def _realm_factor(conn: sqlite3.Connection, ctype: str, cid: int) -> float:
    """Bonus di coltivazione: il regno moltiplica la potenza (Fase 7)."""
    from engine.simulation import cultivation
    lvl = cultivation.effective_level(conn, ctype, cid)
    return 1.0 + (lvl - 1) * cultivation.PER_STAGE_FACTOR


def combat_power(conn: sqlite3.Connection, ctype: str, cid: int) -> dict:
    if ctype == "player":
        base = dict(PLAYER_BASE)
        # crescita fisica da assorbimento (bestie/demoni): corpo più forte
        from engine.systems import character as _ch
        p = _ch.get_profile(conn, "player", cid)
        if p is not None:
            base["attack"] += (p["grow_strength"] or 0) + (p["grow_aura"] or 0) * 0.5
            base["vitality"] += (p["grow_vitality"] or 0)
            base["defense"] += (p["grow_resistance"] or 0)
        # qualità dell'arma equipaggiata (regno×rarità): amplifica l'attacco
        from engine.systems import weapons as _wp
        base["attack"] *= (1.0 + _wp.equipped_bonus(conn, cid))
    else:
        t = entities.get_npc_traits(conn, cid)
        cour, pride, amb = t.get("courage", 50), t.get("pride", 50), t.get("ambition", 50)
        base = {
            "attack": 10 + cour * 0.4 + amb * 0.15,
            "defense": 6 + cour * 0.25 + pride * 0.1,
            "vitality": 35 + cour * 0.4,
        }
        # corpo/anima della coltivazione: i Cultivatori del Corpo sono coriacei,
        # i Maestri dell'Anima colpiscono con la pressione spirituale (identità di classe)
        from engine.simulation import cultivation as _cult
        _rec = _cult.get_record(conn, ctype, cid)
        if _rec:
            base["vitality"] += (_rec["body_level"] or 0) * 0.6
            base["defense"] += (_rec["body_level"] or 0) * 0.2
            base["attack"] += (_rec["soul_level"] or 0) * 0.2
    rf = _realm_factor(conn, ctype, cid)
    keep = 1.0 - _active_injury_penalty(conn, ctype, cid)
    # affinità di combattimento (numero nascosto del profilo del personaggio)
    from engine.systems import character, dao_training
    caf = character.affinity_factor(conn, ctype, cid, "combat")
    # comprensione dei Dao da combattimento (Corpo/Fulmine/Spada): fino a +20%
    daf = dao_training.combat_dao_factor(conn, ctype, cid)
    # tecniche segrete apprese (solo player): bonus permanente alla potenza
    from engine.systems import guild
    tf = guild.technique_combat_factor(conn, ctype, cid)
    # punti DIRETTI da Dao (per tutti) e dalle sessioni/via (solo player)
    from engine.systems import progression
    flat = progression.growth_bonuses(conn, ctype, cid)
    result = {k: max(1.0, v * rf * keep * caf * daf * tf) + flat.get(k, 0.0)
              for k, v in base.items()}
    # linea evolutiva dell'Abisso (solo giocatore): moltiplicatori per statistica
    if ctype == "player":
        from engine.systems import absorption, tribulation
        evb = absorption.evolution_bonuses(conn, cid)
        if evb:
            result["attack"] *= evb.get("attack_mult", 1.0)
            result["defense"] *= evb.get("defense_mult", 1.0)
            result["vitality"] *= evb.get("vitality_mult", 1.0)
        # benedizioni della tribolazione (capacità celesti assorbite dai fulmini)
        bb = tribulation.boon_bonuses(conn, cid)
        result["attack"] = result["attack"] * bb["attack_mult"] + bb["attack_flat"]
        result["defense"] *= bb["defense_mult"]
        result["vitality"] *= bb["vitality_mult"]
    return result


# ---------- scambio di colpi ----------

def _strike(attack: float, defense: float, rng: random.Random) -> tuple[float, bool]:
    base = max(1.0, attack - defense * 0.5)
    roll = rng.uniform(0.6, 1.4)                 # caos
    crit = rng.random() < CRIT_CHANCE            # soglia non lineare
    return base * roll * (CRIT_MULT if crit else 1.0), crit


def resolve_combat(conn: sqlite3.Connection, tick: int, rng: random.Random,
                   atk: tuple[str, int, str], dfn: tuple[str, int, str],
                   loc: int | None, observer: int | None,
                   observations: list[str], atk_mods: dict | None = None) -> dict:
    """atk/dfn = (type, id, name). atk_mods = modificatori della MOSSA dell'attaccante
    (attack_mult, pierce, extra_strikes, taken_mult, death_bonus). Ritorna dict con
    winner, loser, rounds, died."""
    mods = atk_mods or {}
    pa = combat_power(conn, atk[0], atk[1])
    pd = combat_power(conn, dfn[0], dfn[1])
    a_attack = pa["attack"] * mods.get("attack_mult", 1.0)
    d_defense = pd["defense"] * (1.0 - mods.get("pierce", 0.0))
    extra = int(mods.get("extra_strikes", 0))
    taken_mult = mods.get("taken_mult", 1.0)
    hp = {"a": pa["vitality"], "d": pd["vitality"]}
    killing_crit = False
    rounds = 0

    while hp["a"] > 0 and hp["d"] > 0 and rounds < MAX_ROUNDS:
        rounds += 1
        for _ in range(1 + extra):                # colpi extra della mossa (raffica)
            dmg, crit = _strike(a_attack, d_defense, rng)
            hp["d"] -= dmg
            if hp["d"] <= 0:
                killing_crit = crit
                break
        if hp["d"] <= 0:
            break
        dmg, crit = _strike(pd["attack"], pa["defense"], rng)
        hp["a"] -= dmg * taken_mult               # mossa difensiva = subisci meno
        if hp["a"] <= 0:
            killing_crit = crit
            break

    if hp["a"] <= 0 and hp["d"] <= 0:
        winner, loser = (atk, dfn) if hp["a"] >= hp["d"] else (dfn, atk)
        winner_hp = max(hp["a"], hp["d"])
    elif hp["a"] <= 0:
        winner, loser, winner_hp = dfn, atk, hp["d"]
    else:
        winner, loser, winner_hp = atk, dfn, hp["a"]

    wfrac = winner_hp / max(1.0, combat_power(conn, winner[0], winner[1])["vitality"])
    death_prob = 0.12 + (0.28 if wfrac > 0.5 else 0.0) + (0.2 if killing_crit else 0.0)
    if winner == atk:
        death_prob += mods.get("death_bonus", 0.0)    # mossa esecutrice
    died = rng.random() < death_prob

    _apply_outcome(conn, tick, rng, winner, loser, rounds, died, killing_crit,
                   loc, observer, observations)
    return {"winner": winner, "loser": loser, "rounds": rounds, "died": died}


# ---------- esito: ferita o morte ----------

def _apply_outcome(conn, tick, rng, winner, loser, rounds, died, killing_crit,
                   loc, observer, observations) -> None:
    visible = loc == observer
    vis = "public" if visible else "hidden"
    consequences = []

    if died:
        consequences += _kill(conn, tick, rng, loser, vis)
        from engine.systems import karma
        karma.on_kill(conn, tick, winner, loser)
        summary = f"{winner[2]} uccide {loser[2]} dopo {rounds} round."
        if visible:
            observations.append(f"{winner[2]} uccide {loser[2]} in combattimento.")
    else:
        severity = max(1, min(10, rng.randint(2, 6) + (2 if killing_crit else 0)))
        heal_tick = tick + severity * 15
        # clemenza: il GIOCATORE che vince senza uccidere guadagna un po' di karma
        if winner[0] == "player":
            from engine.systems import karma
            karma.on_spare(conn, tick, winner)
        conn.execute(
            "INSERT INTO injuries (character_type, character_id, severity, description, "
            "inflicted_tick, healed, heal_tick) VALUES (?, ?, ?, ?, ?, 0, ?);",
            (loser[0], loser[1], severity, f"ferita da {winner[2]}", tick, heal_tick),
        )
        consequences.append(ev.Consequence(
            loser[0], loser[1], "wound", f"ferito (gravità {severity})",
            visibility=vis, resolve_tick=tick))
        # ferita GRAVE su un NPC: può rivelarsi fatale più tardi (conseguenza differita)
        if loser[0] == "npc" and severity >= 6:
            resolve_at = tick + rng.randint(3, 8)
            consequences.append(ev.Consequence(
                "npc", loser[1], "death_check",
                f"ferita grave, esito al tick {resolve_at}",
                visibility="hidden", resolved=0, resolve_tick=resolve_at))
        summary = f"{winner[2]} sconfigge {loser[2]} (ferito) dopo {rounds} round."
        if visible:
            observations.append(f"{winner[2]} ha la meglio su {loser[2]}.")

    ev.log_event(
        conn, event_type="fight", tick=tick, location_id=loc,
        title=f"Combattimento: {winner[2]} vs {loser[2]}",
        summary=summary,
        participants=[ev.Participant(winner[0], winner[1], "initiator"),
                      ev.Participant(loser[0], loser[1], "target")],
        consequences=consequences,
    )


def _kill(conn, tick, rng, victim, vis) -> list:
    """Uccide victim (npc o player). Ritorna le conseguenze da allegare all'evento."""
    conn.execute(
        f"UPDATE {'players' if victim[0]=='player' else 'npcs'} "
        "SET status='dead'" + (", death_tick=?" if victim[0] == "npc" else "") +
        " WHERE id=?;",
        ((tick, victim[1]) if victim[0] == "npc" else (victim[1],)),
    )
    consequences = [ev.Consequence(victim[0], victim[1], "death",
                                   "ucciso in combattimento", visibility=vis,
                                   resolve_tick=tick)]
    if victim[0] == "npc":
        consequences += _succession(conn, tick, rng, victim[1])
    return consequences


def _succession(conn, tick, rng, dead_npc_id) -> list:
    leads = conn.execute(
        "SELECT id, leader_id FROM factions WHERE leader_id=?;", (dead_npc_id,)
    ).fetchone()
    if not leads:
        return []
    succ = conn.execute(
        "SELECT n.id FROM npcs n JOIN npc_traits t ON t.npc_id=n.id "
        "WHERE n.faction_id=(SELECT faction_id FROM npcs WHERE id=?) "
        "AND n.status='alive' AND n.id<>? ORDER BY (t.ambition+t.pride) DESC LIMIT 1;",
        (dead_npc_id, dead_npc_id),
    ).fetchone()
    new_leader = succ["id"] if succ else None
    conn.execute("UPDATE factions SET leader_id=? WHERE id=?;", (new_leader, leads["id"]))
    return [ev.Consequence("faction", leads["id"], "succession",
                           f"nuovo leader: {new_leader}" if new_leader else "fazione acefala",
                           visibility="hidden", resolve_tick=tick)]


# ---------- guarigione ferite (chiamata ogni tick dal world_tick) ----------

def heal_due_injuries(conn: sqlite3.Connection, tick: int) -> int:
    cur = conn.execute(
        "UPDATE injuries SET healed=1 WHERE healed=0 AND heal_tick<=?;", (tick,))
    return cur.rowcount


def active_injuries(conn: sqlite3.Connection, ctype: str, cid: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT severity, description FROM injuries "
        "WHERE character_type=? AND character_id=? AND healed=0 ORDER BY severity DESC;",
        (ctype, cid))]
