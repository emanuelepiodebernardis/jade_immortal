"""
GLI EREDI (Aggiornamento 65) — alla morte, la Via continua in chi hai cresciuto.

Lo spunto viene da The Scroll of Taiwu, dove alla morte del protagonista si continua come il suo
erede, e il sapere passa di generazione in generazione.

Quando muori puoi, invece di rinascere come un'anima nuova, CONTINUARE COME IL TUO EREDE: uno dei tuoi
discepoli, o un familiare più giovane, ancora vivo. Diventi lui (o lei):
  · porti con te TUTTI i frammenti della vita passata (non solo due);
  · parti dal SUO regno, non dal primo;
  · ti risvegli dove si trova, con il suo nome;
  · ottieni il titolo «Erede di <nome di prima>».
"""

from __future__ import annotations

from engine.systems import state

KEY = "heir_candidates"


def candidates(conn, player) -> list[dict]:
    """Chi può raccogliere la tua eredità: discepoli e familiari più giovani, vivi. (Va letto prima della morte.)"""
    from engine.simulation import cultivation
    out = []
    rows = conn.execute(
        "SELECT b.npc_id, n.name FROM bonds b JOIN npcs n ON n.id=b.npc_id WHERE b.player_id=? AND b.kind='disciple' "
        "AND b.status='active' AND n.status='alive' ORDER BY b.id;", (player.id,)).fetchall()
    for r in rows:
        out.append({"id": r["npc_id"], "name": r["name"], "ruolo": "discepolo",
                    "regno": cultivation.realm_label(conn, "npc", r["npc_id"]),
                    "tier": cultivation.realm_tier(conn, "npc", r["npc_id"]) or 1})
    try:
        from engine.systems import family
        fam = family.get(conn) or {}
        for m in fam.get("members", []):
            role = m.get("role", "")
            if not any(w in role for w in ("minore", "figli", "figlia", "nipote")):
                continue
            nid = m.get("id")
            r = conn.execute("SELECT name, status FROM npcs WHERE id=?;", (nid,)).fetchone()
            if r and r["status"] == "alive":
                out.append({"id": nid, "name": r["name"], "ruolo": role,
                            "regno": cultivation.realm_label(conn, "npc", nid),
                            "tier": cultivation.realm_tier(conn, "npc", nid) or 1})
    except Exception:                                    # noqa: BLE001
        pass
    return out


def remember(conn, player) -> list[dict]:
    c = candidates(conn, player)
    state.set_json(conn, KEY, c)
    return c


def stored(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []


def become(conn, rng, heir: dict, old_name: str, origin: str, destiny: str | None, inherit: list[dict],
           body: bool = False) -> list[str]:
    """Rinasci come l'erede: tutti i frammenti, il suo regno, il suo nome, il suo luogo."""
    from engine.systems import rebirth
    from engine.simulation import cultivation
    from engine.core import entities
    r = conn.execute("SELECT name, location_id, status FROM npcs WHERE id=?;", (heir["id"],)).fetchone()
    if not r or r["status"] != "alive":
        return rebirth.reincarnate(conn, rng, origin, None, inherit, destiny=destiny, body=body)
    loc = r["location_id"]
    lines = rebirth.reincarnate(conn, rng, origin, r["name"], inherit, destiny=destiny, body=body)
    tier = int(heir.get("tier") or 1)
    if tier > (cultivation.realm_tier(conn, "player", 1) or 1):
        rid = cultivation.ensure_realm(conn, tier)
        conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
        conn.execute("UPDATE cultivation_records SET realm_id=?, stage=1, progress=0 WHERE character_type='player' "
                     "AND character_id=1;", (rid,))
    if loc:
        entities.move_player(conn, 1, loc)
    conn.execute("UPDATE npcs SET status='dead', location_id=NULL, description=? WHERE id=?;",
                 (f"Ha raccolto l'eredità di {old_name}: ora vive come il nuovo protagonista.", heir["id"]))
    state.grant_title(conn, f"Erede di {old_name}")
    state.delete(conn, KEY)
    return [f"☯ {old_name} chiude gli occhi. Quando li riapre sono quelli di {r['name']}, il suo {heir['ruolo']}: "
            f"la Via continua. Parti dal regno {tier}, con tutto ciò che la vita passata ti ha lasciato."] + lines
