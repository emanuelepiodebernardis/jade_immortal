"""
Percezione dell'avversario.

Quanto sai di chi hai davanti dipende da due cose:
  1. NOTORIETÀ del bersaglio: ricercati e personaggi famosi (capi-setta, coltivatori
     di alto regno) hanno informazioni PUBBLICHE — altri li hanno visti combattere.
     Gente comune / compagni di classe / sconosciuti: non si sa nulla.
  2. Il tuo DAO DELL'ANIMA: più è profondo, più "leggi" lo spirito altrui.
       principiante  -> non percepisci nulla
       adepto (≥10)  -> capisci se è più forte o più debole di te
       (≥25)         -> ne percepisci il regno di coltivazione
       (≥50)         -> ne intuisci i Dao
       maestro (≥100)-> ne valuti le statistiche

Inoltre lo spirito conta in battaglia:
  - se il tuo spirito sovrasta di molto quello altrui, l'avversario è INTIMIDITO e si
    sottomette senza combattere;
  - a parità di forza, lo spirito superiore ti dà un VANTAGGIO (prevedi/rallenti le sue mosse).
"""

from __future__ import annotations

import sqlite3


def _anima(conn: sqlite3.Connection, ctype: str, cid: int) -> int:
    r = conn.execute(
        "SELECT comprehension FROM character_daos WHERE character_type=? AND character_id=? "
        "AND dao_key='anima';", (ctype, cid)).fetchone()
    return (r["comprehension"] if r and r["comprehension"] else 0)


def spirit_score(conn: sqlite3.Connection, ctype: str, cid: int) -> float:
    from engine.simulation import cultivation
    from engine.systems import progression
    tier = cultivation.realm_tier(conn, ctype, cid) or 1
    base = _anima(conn, ctype, cid) + tier * 8.0 + progression.spirit_bonus(conn, ctype, cid)
    if ctype == "player":
        from engine.systems import absorption, character
        prof = character.get_profile(conn, "player", cid)
        if prof and prof["anomaly"] == "abisso_divoratore":
            base += (prof["soul_residue"] or 0) * 0.05      # presenza abissale
        base += absorption.evolution_bonuses(conn, cid).get("spirit", 0)
    return base


def soul_level(conn: sqlite3.Connection, player_id: int = 1) -> int:
    c = _anima(conn, "player", player_id)
    if c >= 100:
        return 4
    if c >= 50:
        return 3
    if c >= 25:
        return 2
    if c >= 10:
        return 1
    return 0


def is_renowned(conn: sqlite3.Connection, npc_id: int) -> bool:
    """Informazioni pubblicamente note: ricercati, capi-setta, coltivatori di alto regno,
    e i cacciatori che ti danno la caccia (li vedi arrivare)."""
    from engine.systems import bounties
    from engine.simulation import cultivation
    if bounties.get_outlaw(conn, npc_id):
        return True
    h = conn.execute("SELECT hunting FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if h and h["hunting"]:
        return True
    if conn.execute("SELECT 1 FROM factions WHERE leader_id=?;", (npc_id,)).fetchone():
        return True
    return (cultivation.realm_tier(conn, "npc", npc_id) or 1) >= 6


def _overall(p: dict) -> float:
    return p["attack"] + p["defense"] * 0.6 + p["vitality"] * 0.4


def relative_strength(conn: sqlite3.Connection, player_id: int, npc_id: int) -> str:
    from engine.simulation import combat
    r = _overall(combat.combat_power(conn, "player", player_id)) / \
        max(1.0, _overall(combat.combat_power(conn, "npc", npc_id)))
    if r >= 1.6:
        return "molto più debole di te"
    if r >= 1.15:
        return "più debole di te"
    if r >= 0.87:
        return "circa alla tua pari"
    if r >= 0.6:
        return "più forte di te"
    return "molto più forte di te"


def _dao_names(conn: sqlite3.Connection, ctype: str, cid: int) -> list[str]:
    rows = conn.execute(
        "SELECT d.name FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type=? AND cd.character_id=? AND (cd.practiced=1 OR cd.comprehension>0) "
        "ORDER BY cd.comprehension DESC;", (ctype, cid)).fetchall()
    return [r["name"] for r in rows]


def _stat_compare(conn: sqlite3.Connection, player_id: int, npc_id: int) -> str:
    from engine.simulation import combat
    p = combat.combat_power(conn, "player", player_id)
    e = combat.combat_power(conn, "npc", npc_id)

    def q(mine, his):
        r = his / max(1.0, mine)
        if r >= 1.25:
            return "superiore"
        if r >= 0.8:
            return "pari"
        return "inferiore"
    return (f"Attacco {q(p['attack'], e['attack'])}, difesa {q(p['defense'], e['defense'])}, "
            f"vitalità {q(p['vitality'], e['vitality'])} (rispetto a te)")


def describe(conn: sqlite3.Connection, player_id, npc) -> list[str]:
    """Righe informative sull'avversario, filtrate da notorietà + Dao dell'Anima."""
    from engine.simulation import cultivation
    lines: list[str] = []
    level = soul_level(conn, player_id)
    known = is_renowned(conn, npc.id)
    if known:
        lines.append("(È un volto noto: molti l'hanno visto combattere.)")

    if level >= 1 or known:
        lines.append(f"Forza percepita: {relative_strength(conn, player_id, npc.id)}.")
    else:
        lines.append("Non riesci a percepirne la forza: il tuo Dao dell'Anima è troppo acerbo.")

    if known or level >= 2:
        lines.append(f"Coltivazione: {cultivation.realm_label(conn, 'npc', npc.id)}.")
    if known or level >= 3:
        daos = _dao_names(conn, "npc", npc.id)
        if daos:
            lines.append("Dao percepiti: " + ", ".join(daos[:4]) + ".")
    if known or level >= 4:
        lines.append(_stat_compare(conn, player_id, npc.id) + ".")
    return lines


def intimidates(conn: sqlite3.Connection, player_id: int, npc) -> bool:
    """True se il tuo spirito sovrasta tanto quello altrui che l'avversario si sottomette.
    Vale solo per esseri umani non ricercati (le bestie attaccano d'istinto; i ricercati
    sono disperati)."""
    from engine.systems import bounties
    kind = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if kind and kind["kind"] not in (None, "human"):
        return False
    if bounties.get_outlaw(conn, npc.id):
        return False
    ps = spirit_score(conn, "player", player_id)
    es = spirit_score(conn, "npc", npc.id)
    return ps >= es * 2.0 and (ps - es) >= 40.0


def spirit_edge(conn: sqlite3.Connection, player_id: int, npc_id: int) -> float:
    """Vantaggio di combattimento dovuto allo spirito superiore (0..0.3)."""
    diff = _anima(conn, "player", player_id) - _anima(conn, "npc", npc_id)
    if diff <= 0:
        return 0.0
    return min(0.3, diff / 200.0)
