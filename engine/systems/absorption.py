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
        "SELECT id, name, location_id, status, death_tick, kind FROM npcs WHERE id=?;",
        (target_id,)).fetchone()
    if npc is None:
        return {"status": "not_found"}
    if npc["location_id"] != player["location_id"]:
        return {"status": "not_here"}
    if npc["status"] not in ("dead",):
        return {"status": "not_dead"}

    kind = npc["kind"] or "human"
    ptier = cultivation.realm_tier(conn, "player", player_id)
    ttier = cultivation.realm_tier(conn, "npc", target_id)
    death_tick = npc["death_tick"] if npc["death_tick"] is not None else tick
    freshness = max(0.15, min(1.0, 1.0 - (tick - death_tick) / DECAY_WINDOW))

    soul = prof["aff_soul"]
    residue = prof["soul_residue"]
    overreach = max(0, ttier - ptier)
    p_clean = max(0.05, min(0.95, soul / 100.0 * freshness
                            - overreach * 0.18 - residue * 0.0015))
    # CORRUZIONE: oltre una soglia, assorbi meglio (ma sei più instabile)
    corruption_bonus = 1.0 + min(0.5, residue / 500.0)
    yield_pts = max(1, int((ttier * 1.5 + 2) * freshness * corruption_bonus
                           / (1 + max(0, ptier - ttier) * 0.2)))
    clean = rng.random() < p_clean
    if not clean:
        yield_pts = max(1, yield_pts // 2)        # integrazione imperfetta

    name = npc["name"]
    consequences = []
    if kind == "beast":
        outcome = _absorb_beast(conn, player_id, yield_pts, consequences, tick)
        residue_gain = 3 + overreach
        _bump_count(conn, player_id, "abs_beast")
        summary = f"Divori la carne di {name}: il tuo corpo si fa più forte e resistente."
    elif kind == "demon":
        outcome = _absorb_demon(conn, player_id, yield_pts, consequences, tick)
        residue_gain = 6 + overreach * 2
        _bump_count(conn, player_id, "abs_demon")
        summary = f"Divori {name}: un'aura feroce e demoniaca cresce in te."
    elif kind == "spirit":
        outcome = _absorb_spirit(conn, player_id, yield_pts, consequences, tick, rng)
        residue_gain = 4 + overreach
        _bump_count(conn, player_id, "abs_spirit")
        summary = f"Divori l'essenza di {name}: la tua anima si amplia."
    else:  # human / coltivatore
        outcome, residue_gain = _absorb_human(conn, player_id, target_id, freshness,
                                              ptier, ttier, clean, overreach, consequences,
                                              tick, rng, name)
        _bump_count(conn, player_id, "abs_human")
        summary = outcome.pop("_summary", f"Divori l'eredità di {name}.")

    # catastrofe rara: anima debole + bersaglio molto superiore
    if overreach >= 3 and soul < 60 and rng.random() < 0.20:
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
    from engine.systems import karma
    karma.on_absorb(conn, tick, player_id, target_id, name)
    conn.execute("UPDATE npcs SET status='absorbed' WHERE id=?;", (target_id,))

    ev.log_event(
        conn, event_type="absorption", tick=tick, location_id=npc["location_id"],
        title=f"Assorbimento di {name}", summary=summary,
        participants=[ev.Participant("player", player_id, "initiator"),
                      ev.Participant("npc", target_id, "victim")],
        consequences=consequences + [ev.Consequence(
            "player", player_id, "soul_residue", f"corruzione +{residue_gain}",
            visibility="hidden", resolve_tick=tick)],
    )
    outcome["residue"] = new_residue
    outcome["kind"] = kind
    outcome["summary"] = summary
    return outcome


def _bump_count(conn, player_id, col) -> None:
    conn.execute(
        f"UPDATE character_profiles SET {col}={col}+1 "
        "WHERE character_type='player' AND character_id=?;", (player_id,))


def _grow(conn, player_id, col, amount) -> None:
    conn.execute(
        f"UPDATE character_profiles SET {col}={col}+? "
        "WHERE character_type='player' AND character_id=?;", (amount, player_id))


def _absorb_beast(conn, player_id, pts, consequences, tick) -> dict:
    s, v, r = pts, max(1, int(pts * 0.7)), max(1, int(pts * 0.7))
    _grow(conn, player_id, "grow_strength", s)
    _grow(conn, player_id, "grow_vitality", v)
    _grow(conn, player_id, "grow_resistance", r)
    consequences.append(ev.Consequence("player", player_id, "body_growth",
                                       f"+{s} forza, +{v} vitalità, +{r} resistenza",
                                       visibility="hidden", resolve_tick=tick))
    return {"status": "body", "strength": s, "vitality": v, "resistance": r}


def _absorb_demon(conn, player_id, pts, consequences, tick) -> dict:
    a, s = pts, max(1, int(pts * 0.5))
    _grow(conn, player_id, "grow_aura", a)
    _grow(conn, player_id, "grow_strength", s)
    consequences.append(ev.Consequence("player", player_id, "demon_growth",
                                       f"+{a} aura, +{s} potenza offensiva",
                                       visibility="hidden", resolve_tick=tick))
    return {"status": "aura", "aura": a, "strength": s}


def _absorb_spirit(conn, player_id, pts, consequences, tick, rng) -> dict:
    _grow(conn, player_id, "grow_soul", pts)
    # gli spiriti nutrono anche la comprensione di un Dao che pratichi
    practiced = conn.execute(
        "SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? "
        "AND practiced=1 ORDER BY RANDOM() LIMIT 1;", (player_id,)).fetchone()
    dao_gain = 0
    if practiced:
        dao_gain = max(1, pts // 2)
        _raise_comprehension(conn, practiced["dao_key"], dao_gain, player_id)
    consequences.append(ev.Consequence("player", player_id, "spirit_growth",
                                       f"+{pts} anima" + (f", +{dao_gain} Dao" if dao_gain else ""),
                                       visibility="hidden", resolve_tick=tick))
    return {"status": "soul", "soul": pts, "dao_gain": dao_gain}


def _absorb_human(conn, player_id, target_id, freshness, ptier, ttier, clean,
                  overreach, consequences, tick, rng, name) -> tuple[dict, int]:
    tdao = conn.execute(
        "SELECT dao_key, comprehension FROM character_daos "
        "WHERE character_type='npc' AND character_id=? ORDER BY comprehension DESC LIMIT 1;",
        (target_id,)).fetchone()
    if clean and tdao:
        p_aff = dao_gen.player_dao_affinity(conn, tdao["dao_key"], player_id)
        gain = max(1, int(tdao["comprehension"] * 0.18 * freshness
                          * (p_aff / 100.0) / (1 + max(0, ptier - ttier) * 0.2)))
        _raise_comprehension(conn, tdao["dao_key"], gain, player_id)
        # TALENTO: assorbire coltivatori affina le tue radici (test futuri lo misurano)
        if rng.random() < 0.5:
            conn.execute(
                "UPDATE character_profiles SET aff_cultivation=MIN(100, aff_cultivation+1) "
                "WHERE character_type='player' AND character_id=?;", (player_id,))
        consequences.append(ev.Consequence(
            "player", player_id, "dao_fragment", f"+{gain} comprensione in {tdao['dao_key']}",
            visibility="hidden", resolve_tick=tick))
        return ({"status": "comprehension", "dao": tdao["dao_key"], "gain": gain,
                 "_summary": f"Divori l'eredità di {name}: un frammento del suo Dao risuona in te."},
                2 + overreach)
    consequences.append(ev.Consequence(
        "player", player_id, "soul_trauma", "frammento estraneo e instabile",
        visibility="hidden", resolve_tick=tick))
    return ({"status": "trauma",
             "_summary": f"Divori {name}, ma l'eredità ti contamina: echi non tuoi ti attraversano."},
            5 + overreach * 3)


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
            "VALUES ('player', ?, ?, 50, ?, 0);", (player_id, dao_key, max(0, gain)))
        return
    conn.execute(
        "UPDATE character_daos SET comprehension=?, affinity=? "
        "WHERE character_type='player' AND character_id=? AND dao_key=?;",
        (row["comprehension"] + gain, min(100, row["affinity"] + 1),
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


# soglie di CORRUZIONE dell'Abisso (sul soul_residue): (min, etichetta, effetti)
CORRUPTION_TIERS = [
    (0, "nessun segno visibile", []),
    (100, "i tuoi occhi si fanno più scuri", ["bonus_assorbimento"]),
    (250, "l'anima muta: gli anziani percepiscono qualcosa di sbagliato", ["sospetto_anziani"]),
    (500, "una presenza terrificante ti circonda: i deboli ti temono", ["terrore"]),
    (1000, "Anomalia Celeste: il Cielo stesso ti considera una minaccia", ["anomalia_celeste"]),
]


def corruption_tier(residue: int) -> tuple[str, list[str]]:
    label, effects = CORRUPTION_TIERS[0][1], CORRUPTION_TIERS[0][2]
    for thr, lab, eff in CORRUPTION_TIERS:
        if residue >= thr:
            label, effects = lab, eff
    return label, effects


def corruption_label(residue: int) -> str:
    return corruption_tier(residue)[0]


def evolution_path(conn, player_id: int = 1) -> str | None:
    """Linea evolutiva emergente dai conteggi di assorbimento (dominanza di un tipo)."""
    p = character.get_profile(conn, "player", player_id)
    if p is None:
        return None
    counts = {"bestie": p["abs_beast"] or 0, "demoni": p["abs_demon"] or 0,
              "spiriti": p["abs_spirit"] or 0, "umani": p["abs_human"] or 0}
    total = sum(counts.values())
    if total < 5:
        return None
    top, n = max(counts.items(), key=lambda kv: kv[1])
    if n / total < 0.5:
        return "Il Divoratore senza forma: nessuna natura prevale ancora in te."
    titles = {"bestie": "Predatore Primordiale (Via delle Bestie)",
              "demoni": "Tiranno Demoniaco (Via dei Demoni)",
              "spiriti": "Imperatore Spirituale (Via degli Spiriti)",
              "umani": "Divoratore Celeste (Via degli Immortali)"}
    stage = "nascente" if total < 30 else ("affermato" if total < 100 else "compiuto")
    return f"{titles[top]} — {stage}"


def _evolution_state(conn, player_id: int = 1):
    """(tipo dominante, stadio 1..3) oppure (None, 0)."""
    p = character.get_profile(conn, "player", player_id)
    if p is None:
        return (None, 0)
    counts = {"bestie": p["abs_beast"] or 0, "demoni": p["abs_demon"] or 0,
              "spiriti": p["abs_spirit"] or 0, "umani": p["abs_human"] or 0}
    total = sum(counts.values())
    if total < 5:
        return (None, 0)
    top, n = max(counts.items(), key=lambda kv: kv[1])
    if n / total < 0.5:
        return (None, 0)
    s = 1 if total < 30 else (2 if total < 100 else 3)
    return (top, s)


def evolution_bonuses(conn, player_id: int = 1) -> dict:
    """Bonus MECCANICI della linea evolutiva (per stadio). Solo per il giocatore.
    attack_mult/defense_mult/vitality_mult (potenza), spirit (percezione),
    fear (terrore in battaglia), dao_gain (comprensione più rapida)."""
    top, s = _evolution_state(conn, player_id)
    if not top:
        return {}
    if top == "bestie":     # Predatore Primordiale: corpo e rigenerazione
        return {"attack_mult": 1 + 0.08 * s, "vitality_mult": 1 + 0.09 * s}
    if top == "demoni":     # Tiranno Demoniaco: offensiva e aura terrificante
        return {"attack_mult": 1 + 0.11 * s, "fear": s}
    if top == "spiriti":    # Imperatore Spirituale: spirito, difesa, Dao
        return {"defense_mult": 1 + 0.07 * s, "spirit": 20 * s, "dao_gain": 0.08 * s}
    if top == "umani":      # Divoratore Celeste: tutto un po'
        return {"attack_mult": 1 + 0.04 * s, "defense_mult": 1 + 0.04 * s,
                "vitality_mult": 1 + 0.04 * s, "spirit": 10 * s}
    return {}


def dread_level(conn, player_id: int = 1) -> int:
    """Terrore che emani: dalla CORRUZIONE (presenza abissale) + aura demoniaca."""
    p = character.get_profile(conn, "player", player_id)
    if p is None or p["anomaly"] != "abisso_divoratore":
        return 0
    res = p["soul_residue"] or 0
    _label, effects = corruption_tier(res)
    dread = 0
    if "terrore" in effects:
        dread += 2
    if "anomalia_celeste" in effects:
        dread += 3
    dread += evolution_bonuses(conn, player_id).get("fear", 0)
    return dread


# --- Tribolazione dell'Abisso (Anomalia Celeste, corruzione >= 1000) -----------
TRIB_INTERVAL = 24
TRIB_CHANCE = 0.22


def maybe_tribulation(conn, tick, rng, player, observations) -> int:
    """Al culmine della corruzione, il Cielo ti considera una minaccia e ti colpisce:
    una tribolazione celeste ti ferisce, ma scarica parte della corruzione. Sopravvivere
    è leggendario (cresce la tua fama, e il tuo terrore)."""
    p = character.get_profile(conn, "player", player.id)
    if p is None or p["anomaly"] != "abisso_divoratore":
        return 0
    res = p["soul_residue"] or 0
    if res < 1000 or rng.random() >= TRIB_CHANCE:
        return 0
    from engine.simulation import cultivation
    from engine.systems import perception, reputation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    endure = ptier * 10 + perception.spirit_score(conn, "player", player.id) * 0.2
    severity = max(1, min(8, 7 - int(endure / 45)))
    conn.execute(
        "INSERT INTO injuries (character_type, character_id, severity, description, "
        "inflicted_tick, heal_tick) VALUES ('player', ?, ?, ?, ?, ?);",
        (player.id, severity, "fulmine della tribolazione dell'Abisso", tick, tick + 18))
    discharge = rng.randint(120, 220)
    conn.execute(
        "UPDATE character_profiles SET soul_residue=? "
        "WHERE character_type='player' AND character_id=?;", (max(0, res - discharge), player.id))
    reputation.adjust(conn, player.id, fame=15, infamy=12)
    if observations is not None:
        observations.append(
            "⚡ ANOMALIA CELESTE: una tribolazione dell'Abisso ti incenerisce dall'alto! "
            f"La reggi a stento (ferita di gravità {severity}); parte della corruzione si scarica. "
            "Sopravvivere a un castigo del Cielo ti rende leggenda.")
    return 1
