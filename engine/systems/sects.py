"""
Sette (strato "agenzia del giocatore").

Una setta è una fazione con una sede. Il giocatore può recarsi alla sede e
iscriversi: un TEST D'INGRESSO misura il suo talento (riusando le affinità
nascoste già presenti nel profilo) e gli assegna un rango e delle risorse.

Niente garanzie di build dominante: il test riflette ciò che sei, e il rango
dà vantaggi (risorse, allenamento agevolato) ma non potere gratuito.
"""

from __future__ import annotations

import sqlite3

# soglie del talento -> grado di "radici spirituali" + rango + risorse
GRADES = [
    (85, "Radici Celesti", "Discepolo del Nucleo", 3, 300),
    (70, "Radici Superiori", "Discepolo Interno", 2, 150),
    (52, "Radici Comuni", "Discepolo Esterno", 1, 60),
    (0,  "Radici Torbide", "Servitore", 0, 20),
]

# livelli delle sette (1 più bassa .. 6 apice)
SECT_TIER_NAMES = {
    1: "Setta Regionale",
    2: "Setta Provinciale",
    3: "Setta Nazionale",
    4: "Terra Sacra",
    5: "Potere Imperiale",
    6: "Setta Celeste",
}
MAX_SECT_TIER = 6

# elemento -> moltiplicatore alla comprensione del Dao affine, da membro
ELEMENT_BONUS = 1.5

_GREAT_PREFIX = ["Setta", "Ordine", "Palazzo", "Dinastia", "Santuario", "Corte"]
_GREAT_SUFFIX = ["del Cielo Frantumato", "dell'Astro Eterno", "del Vuoto Primordiale",
                 "della Fenice d'Oro", "del Drago Ascendente", "delle Nove Nubi",
                 "della Fiamma Immortale", "dell'Abisso Stellare"]


def tier_name(tier: int | None) -> str:
    return SECT_TIER_NAMES.get(max(1, min(MAX_SECT_TIER, tier or 1)), "Setta")


def _dao_display(conn: sqlite3.Connection, dao_key: str | None) -> str:
    if not dao_key:
        return "nessun elemento"
    r = conn.execute("SELECT name FROM daos WHERE dao_key=?;", (dao_key,)).fetchone()
    return r["name"] if r else dao_key


def element_bonus(conn: sqlite3.Connection, dao_key: str, player_id: int = 1) -> float:
    """Moltiplicatore alla comprensione se il Dao coincide con l'elemento della tua setta."""
    m = get_membership(conn, player_id)
    if not m:
        return 1.0
    row = conn.execute("SELECT element FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    if row and row["element"] and row["element"] == dao_key:
        return ELEMENT_BONUS
    return 1.0


def joinable_sects(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """Fazioni con una sede: sette a cui ci si può iscrivere."""
    return conn.execute(
        "SELECT f.id, f.name, f.home_location_id, f.tier, f.element, l.name AS hq_name "
        "FROM factions f JOIN locations l ON l.id=f.home_location_id "
        "WHERE f.status='active' ORDER BY f.tier DESC, f.influence DESC;"
    ).fetchall()


def sect_at_location(conn: sqlite3.Connection, location_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, name, home_location_id FROM factions "
        "WHERE home_location_id=? AND status='active' LIMIT 1;", (location_id,)
    ).fetchone()


def get_membership(conn: sqlite3.Connection, player_id: int = 1) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT m.player_id, m.faction_id, m.rank, m.rank_level, m.grade, "
        "m.class_tier, m.class_rank, f.name AS sect_name, f.tier AS sect_tier, "
        "f.element AS sect_element "
        "FROM sect_memberships m JOIN factions f ON f.id=m.faction_id "
        "WHERE m.player_id=?;", (player_id,)
    ).fetchone()


def _talent_score(conn: sqlite3.Connection, player_id: int) -> int:
    """Talento dal profilo (numeri nascosti): coltivazione + qi + anima + miglior Dao."""
    from engine.systems import character
    p = character.get_profile(conn, "player", player_id)
    if p is None:
        return 50
    best_dao = conn.execute(
        "SELECT MAX(affinity) m FROM character_daos "
        "WHERE character_type='player' AND character_id=?;", (player_id,)
    ).fetchone()
    bd = best_dao["m"] if best_dao and best_dao["m"] is not None else 50
    score = (p["aff_cultivation"] * 0.5 + p["aff_qi"] * 0.2
             + p["aff_soul"] * 0.15 + bd * 0.15)
    from engine.systems import reputation
    score += reputation.fame_talent_bonus(conn, player_id)   # la fama apre le porte
    return int(round(score))


def _grade_for(score: int):
    for threshold, grade, rank, level, stones in GRADES:
        if score >= threshold:
            return grade, rank, level, stones
    return GRADES[-1][1:]


def get_resource(conn: sqlite3.Connection, resource: str, player_id: int = 1) -> int:
    row = conn.execute(
        "SELECT amount FROM player_resources WHERE player_id=? AND resource=?;",
        (player_id, resource)).fetchone()
    return row["amount"] if row else 0


def grant_resource(conn: sqlite3.Connection, resource: str, amount: int,
                   player_id: int = 1) -> int:
    cur = get_resource(conn, resource, player_id)
    new = max(0, cur + amount)
    conn.execute(
        "INSERT INTO player_resources (player_id, resource, amount) VALUES (?, ?, ?) "
        "ON CONFLICT(player_id, resource) DO UPDATE SET amount=excluded.amount;",
        (player_id, resource, new))
    return new


def join_sect(conn: sqlite3.Connection, tick: int, player_id: int = 1) -> dict:
    """Iscrizione alla setta nella location corrente del giocatore (test d'ingresso)."""
    player = conn.execute(
        "SELECT location_id FROM players WHERE id=?;", (player_id,)).fetchone()
    if get_membership(conn, player_id):
        m = get_membership(conn, player_id)
        return {"status": "already_member", "sect": m["sect_name"]}
    sect = sect_at_location(conn, player["location_id"])
    if sect is None:
        return {"status": "no_sect_here"}

    score = _talent_score(conn, player_id)
    grade, rank, level, stones = _grade_for(score)

    conn.execute(
        "INSERT INTO sect_memberships (player_id, faction_id, rank, rank_level, grade, joined_tick) "
        "VALUES (?, ?, ?, ?, ?, ?);",
        (player_id, sect["id"], rank, level, grade, tick))
    conn.execute("UPDATE players SET faction_id=? WHERE id=?;", (sect["id"], player_id))
    grant_resource(conn, "pietre_spirituali", stones, player_id)

    # la setta ora ti vede di buon occhio
    from engine.systems import relations
    from engine.simulation import event_system as ev
    # registra l'evento (vincolo 26)
    ev.log_event(
        conn, event_type="sect_join", tick=tick, location_id=player["location_id"],
        title=f"Ammissione a {sect['name']}",
        summary=f"Superi il test d'ingresso di {sect['name']} come {rank} ({grade}).",
        participants=[ev.Participant("player", player_id, "initiator")],
        consequences=[ev.Consequence("player", player_id, "sect_membership",
                                     f"{rank} di {sect['name']}", visibility="public",
                                     resolve_tick=tick)],
    )
    return {"status": "joined", "sect": sect["name"], "grade": grade,
            "rank": rank, "rank_level": level, "stones": stones}


def leave_sect(conn: sqlite3.Connection, player_id: int = 1) -> dict:
    m = get_membership(conn, player_id)
    if not m:
        return {"status": "not_member"}
    conn.execute("DELETE FROM sect_memberships WHERE player_id=?;", (player_id,))
    conn.execute("UPDATE players SET faction_id=NULL WHERE id=?;", (player_id,))
    return {"status": "left", "sect": m["sect_name"]}


# ============================================================
# Sette a livelli: i "7 rappresentanti" e l'ascesa
# ============================================================

def pending_invitations(conn: sqlite3.Connection, player_id: int = 1) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT slot, name, tier, element, hint FROM sect_invitations "
        "WHERE player_id=? AND resolved=0 ORDER BY slot;", (player_id,)).fetchall()


def current_sect_tier(conn: sqlite3.Connection, player_id: int = 1) -> int:
    m = get_membership(conn, player_id)
    return (m["sect_tier"] if m and m["sect_tier"] else 1) if m else 0


def generate_invitations(conn: sqlite3.Connection, tick: int, rng,
                         player_id: int = 1) -> list[sqlite3.Row]:
    """I 7 rappresentanti di sette superiori si presentano (dati leggeri).
    Non rigenera se ci sono già inviti pendenti."""
    if pending_invitations(conn, player_id):
        return pending_invitations(conn, player_id)
    cur_tier = max(1, current_sect_tier(conn, player_id))
    if cur_tier >= MAX_SECT_TIER:
        return []
    elements = ["corpo", "fulmine", "spada", "anima"]
    for slot in range(1, 8):
        t = min(MAX_SECT_TIER, cur_tier + rng.choices([1, 2, 3], weights=[5, 3, 1])[0])
        el = rng.choice(elements)
        name = f"{rng.choice(_GREAT_PREFIX)} {rng.choice(_GREAT_SUFFIX)}"
        hint = f"{tier_name(t)} · affine al {_dao_display(conn, el)}"
        conn.execute(
            "INSERT INTO sect_invitations (player_id, slot, name, tier, element, hint, "
            "created_tick, resolved) VALUES (?, ?, ?, ?, ?, ?, ?, 0);",
            (player_id, slot, name, t, el, hint, tick))
    return pending_invitations(conn, player_id)


def _create_greater_sect(conn, rng, name, tier, element, tick) -> int:
    """Crea la setta superiore come fazione reale (con leader scalato al livello)."""
    from engine.generators import npc_gen
    home = conn.execute(
        "SELECT id FROM locations ORDER BY danger_level DESC, id LIMIT 1;").fetchone()["id"]
    cur = conn.execute(
        "INSERT INTO factions (name, home_location_id, influence, wealth, description, "
        "goals, tier, element, status) VALUES (?, ?, ?, ?, ?, '[]', ?, ?, 'active');",
        (name, home, 60 + tier * 6, 60 + tier * 6,
         "Una setta superiore, lontana e potente.", tier, element))
    fid = cur.lastrowid
    by_tier = {r["tier"]: r["id"] for r in conn.execute("SELECT id, tier FROM cultivation_realms;")}
    lr_tier = min(8, 2 + tier)                    # maestri scalati al livello della setta
    realm_id = by_tier.get(lr_tier, by_tier.get(1))
    used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
    lname = npc_gen._unique_name(rng, used)
    traits = npc_gen.roll_traits(rng, "patriarca")
    ldesc = npc_gen.make_description("patriarca", traits)
    lc = conn.execute(
        "INSERT INTO npcs (name, location_id, status, description, archetype, kind, "
        "faction_id, realm_id, last_active_tick) "
        "VALUES (?, ?, 'alive', ?, 'patriarca', 'human', ?, ?, ?);",
        (lname, home, ldesc, fid, realm_id, tick))
    lid = lc.lastrowid
    conn.execute(
        "INSERT INTO npc_traits (npc_id, ambition, honor, greed, courage, loyalty, "
        "compassion, pride) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
        (lid, traits["ambition"], traits["honor"], traits["greed"], traits["courage"],
         traits["loyalty"], traits["compassion"], traits["pride"]))
    conn.execute(
        "INSERT INTO cultivation_records (character_id, character_type, realm_id, progress, "
        "stage, qi_level, body_level, soul_level, dao_understanding) "
        "VALUES (?, 'npc', ?, 0.5, 10, ?, ?, ?, ?);",
        (lid, realm_id, lr_tier * 10 + 20, lr_tier * 8 + 10, lr_tier * 8 + 10, lr_tier * 6))
    conn.execute("UPDATE factions SET leader_id=? WHERE id=?;", (lid, fid))
    # zona di caccia con mostri scalati al livello della setta superiore
    from engine.generators import creature_gen
    creature_gen.setup_hunt_zone(conn, rng, fid)
    return fid


def accept_invitation(conn: sqlite3.Connection, tick: int, rng, slot: int,
                      player_id: int = 1) -> dict:
    inv = conn.execute(
        "SELECT slot, name, tier, element FROM sect_invitations "
        "WHERE player_id=? AND slot=? AND resolved=0;", (player_id, slot)).fetchone()
    if inv is None:
        return {"status": "no_invitation"}

    fid = _create_greater_sect(conn, rng, inv["name"], inv["tier"], inv["element"], tick)
    if get_membership(conn, player_id):
        leave_sect(conn, player_id)

    # nuovo test del talento: riflette la crescita (assorbire geni alza aff_cultivation)
    score = _talent_score(conn, player_id)
    grade, rank, level, stones = _grade_for(score)
    stones += inv["tier"] * 120                    # le sette superiori sono più generose
    conn.execute(
        "INSERT INTO sect_memberships (player_id, faction_id, rank, rank_level, grade, joined_tick) "
        "VALUES (?, ?, ?, ?, ?, ?);", (player_id, fid, rank, level, grade, tick))
    conn.execute("UPDATE players SET faction_id=? WHERE id=?;", (fid, player_id))
    grant_resource(conn, "pietre_spirituali", stones, player_id)

    home = conn.execute(
        "SELECT home_location_id FROM factions WHERE id=?;", (fid,)).fetchone()["home_location_id"]
    conn.execute("UPDATE players SET location_id=? WHERE id=?;", (home, player_id))
    conn.execute("UPDATE sect_invitations SET resolved=1 WHERE player_id=?;", (player_id,))

    from engine.systems import sect_life
    sect_life.setup_class(conn, tick, rng, player_id)

    from engine.simulation import event_system as ev
    ev.log_event(
        conn, event_type="sect_ascension", tick=tick, location_id=home,
        title=f"Ascesa a {inv['name']}",
        summary=f"Accogli l'invito di {inv['name']} ({tier_name(inv['tier'])}) come {rank}.",
        participants=[ev.Participant("player", player_id, "initiator")],
        consequences=[ev.Consequence("player", player_id, "sect_membership",
                                     f"{rank} di {inv['name']}", visibility="public",
                                     resolve_tick=tick)])
    return {"status": "ascended", "sect": inv["name"], "tier": inv["tier"],
            "rank": rank, "grade": grade, "stones": stones, "element": inv["element"]}
