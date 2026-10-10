"""
VIE DELLE SETTE: ORTODOSSA, ETERODOSSA, DEMONIACA (正道 / 旁门 / 魔道).

  - Le sette ORTODOSSE non accolgono chi ha un nome macchiato (infamia più alta della fama,
    karma molto negativo). Uccidere coltivatori demoniaci porta loro onore.
  - Le sette ETERODOSSE non chiedono nulla: contano solo forza e utilità.
  - Le sette DEMONIACHE diffidano dei cuori troppo puri; premiano il sangue versato (merito
    per ogni uccisione) e, quando la tua infamia cresce, ti mandano un emissario.
"""

from __future__ import annotations

import sqlite3

from engine.systems import state

LABEL = {"ortodossa": "Via Ortodossa", "eterodossa": "Via Eterodossa", "demoniaca": "Via Demoniaca"}
_PATTERN = ["ortodossa", "demoniaca", "eterodossa", "ortodossa", "ortodossa", "eterodossa"]


def ensure(conn: sqlite3.Connection) -> None:
    """Assegna una Via alle sette che non ne hanno (in modo deterministico)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(factions);")}
    if "alignment" not in cols:
        conn.execute("ALTER TABLE factions ADD COLUMN alignment TEXT;")
    rows = conn.execute("SELECT id, name, alignment FROM factions ORDER BY id;").fetchall()
    for i, r in enumerate(rows):
        if r["alignment"]:
            continue
        nm = (r["name"] or "").lower()
        if any(w in nm for w in ("demon", "sangue", "ombra", "abisso", "inferi", "veleno")):
            al = "demoniaca"
        else:
            al = _PATTERN[i % len(_PATTERN)]
        conn.execute("UPDATE factions SET alignment=? WHERE id=?;", (al, r["id"]))


def of(conn, fid: int | None) -> str:
    if not fid:
        return ""
    try:
        r = conn.execute("SELECT alignment FROM factions WHERE id=?;", (fid,)).fetchone()
    except sqlite3.OperationalError:
        ensure(conn)
        r = conn.execute("SELECT alignment FROM factions WHERE id=?;", (fid,)).fetchone()
    if r and not r["alignment"]:
        ensure(conn)
        r = conn.execute("SELECT alignment FROM factions WHERE id=?;", (fid,)).fetchone()
    return (r["alignment"] if r else "") or ""


def label(conn, fid) -> str:
    return LABEL.get(of(conn, fid), "")


def can_join(conn, pid: int, fid: int) -> tuple[bool, str]:
    from engine.systems import reputation, karma
    al = of(conn, fid)
    rep = reputation.get(conn, pid)
    k = karma.get_karma(conn, "player", pid)
    if al == "ortodossa":
        if rep["infamy"] > max(30, rep["fame"]) or k < -200:
            return False, ("Gli anziani ti squadrano: «Il tuo nome puzza di sangue innocente. "
                           "La Via Ortodossa non è per te.»")
    if al == "demoniaca":
        if k > 300 and rep["infamy"] < 20 and not state.flag(conn, "invito_demoniaco", False):
            return False, ("Un sorriso storto: «Un cuore così pulito? Torna quando avrai le mani "
                           "sporche.»")
    return True, ""


def on_kill(conn, t: int, player, npc_id: int) -> list[str]:
    from engine.systems import sects, guild, reputation
    out = []
    row = conn.execute("SELECT faction_id, kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    victim_al = of(conn, row["faction_id"]) if row else ""
    m = sects.get_membership(conn, player.id)
    my_al = of(conn, m["faction_id"]) if m else ""
    if my_al == "demoniaca" and row and (row["kind"] in (None, "human")):
        guild.add_merit(conn, 3, player.id)
        out.append("La tua setta demoniaca premia il sangue versato: merito +3.")
    if victim_al == "demoniaca" and my_al != "demoniaca":
        reputation.adjust(conn, player.id, fame=3)
        if my_al == "ortodossa":
            guild.add_merit(conn, 5, player.id)
            out.append("Hai abbattuto un coltivatore demoniaco: la tua setta ortodossa ti onora (merito +5).")
        else:
            out.append("Hai abbattuto un coltivatore demoniaco: la gente ne parla con sollievo.")
    return out


def daily(conn, t: int, rng, player) -> list[str]:
    """Con molta infamia e senza setta, un emissario demoniaco viene a cercarti."""
    from engine.systems import reputation, sects, encounters
    if sects.get_membership(conn, player.id) or encounters.pending(conn):
        return []
    rep = reputation.get(conn, player.id)
    if rep["infamy"] < 50:
        return []
    day = t // 120
    if day - state.get_int(conn, "demon_envoy_day", -999) < 30:
        return []
    dem = conn.execute("SELECT f.id, f.name, l.name AS hq FROM factions f "
                       "JOIN locations l ON l.id=f.home_location_id "
                       "WHERE f.alignment='demoniaca' AND f.status='active' LIMIT 1;").fetchone()
    if not dem:
        return []
    state.set(conn, "demon_envoy_day", str(day))
    sc = {
        "key": "emissario_demoniaco", "title": "Un emissario dalle vesti nere", "event_type": "social",
        "text": (f"Un uomo dalle vesti color sangue ti si accosta: «La {dem['name']} ha sentito parlare "
                 f"di te. Quelli come noi non devono restare soli. La nostra sede è a {dem['hq']}.»"),
        "spawn": {"archetype": "vagabondo", "tier_offset": 0, "traits": {"compassion": 5}},
        "choices": [
            {"label": "Accetti il suo dono e l'invito",
             "effects": {"flags": ["invito_demoniaco"], "infamy": 3,
                         "learn_technique": {"name": "Arte del Sangue che Ribolle", "magnitude": 0.07,
                                             "tech_key": "demoniaca:sangue_ribolle"},
                         "text": "Ti consegna un rotolo vergato col sangue. «Ti aspettiamo.»"}},
            {"label": "Rifiuti con freddezza", "effects": {"text": "Scrolla le spalle e svanisce."}},
            {"label": "Lo abbatti: un demonio in meno", "effects": {}, "command": "attack {npc}"},
        ]}
    from engine.systems import npc_factory
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    txt = encounters.start_scene(conn, player, sc)
    return [txt] if txt else []
