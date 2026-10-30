"""
I LEGAMI TI SEGUONO IN CIELO (Aggiornamento 63).

Quando ascendi a un mondo superiore, chi ti era legato non resta indietro per sempre: compagni,
discepoli, il tuo maestro, i fratelli giurati, la compagna del Dao, la famiglia. Nei giorni che
seguono, uno dopo l'altro, ascendono anche loro e ti ritrovano lassù: più forti, come se il cielo
superiore avesse risvegliato ciò che erano davvero. (Lo spunto viene da Immortal Taoists, dove i
compagni del mondo mortale tornano in Cielo come servitori, «ciò che erano un tempo, molto più forti».)

Anche i NEMICI: un tuo nemico giurato morto nel mondo di sotto può rinascere lassù, e ricordarsi
di te.

  legami_cielo   chi ti ha raggiunto, e chi deve ancora arrivare
"""

from __future__ import annotations


from engine.core import tick as tick_mod
from engine.systems import state

KEY = "heaven_reunions"
FOLLOW = ("companion", "disciple", "master", "sworn", "dao_partner", "family")
LABEL = {"companion": "compagno", "disciple": "discepolo", "master": "maestro", "sworn": "fratello giurato",
         "dao_partner": "compagna del Dao", "family": "famiglia"}
MAX_FOLLOW = 8


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"queue": [], "done": []}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def on_ascend(conn, player, layer: int) -> list[str]:
    """Si mettono in coda i legami rimasti nei mondi inferiori: arriveranno nei prossimi giorni."""
    from engine.systems import ascension
    d = get(conn)
    queued = {q["npc"] for q in d["queue"]} | set(d["done"])
    rows = conn.execute(
        "SELECT b.npc_id, b.kind, n.name, n.location_id FROM bonds b JOIN npcs n ON n.id=b.npc_id "
        "WHERE b.player_id=? AND b.status='active' AND n.status='alive' AND b.kind IN (%s) ORDER BY b.id;"
        % ",".join("?" * len(FOLLOW)), (player.id, *FOLLOW)).fetchall()
    day = _day(conn)
    n = 0
    for r in rows:
        if r["npc_id"] in queued or ascension.layer_of_location(conn, r["location_id"]) >= layer:
            continue
        n += 1
        if n > MAX_FOLLOW:
            break
        d["queue"].append({"npc": r["npc_id"], "kind": r["kind"], "layer": layer, "due": day + 2 + 3 * n})
    foe = conn.execute(
        "SELECT b.npc_id, n.name FROM bonds b JOIN npcs n ON n.id=b.npc_id WHERE b.player_id=? AND "
        "b.kind IN ('nemesis','arcinemico') AND n.status='dead' ORDER BY b.id DESC LIMIT 1;", (player.id,)).fetchone()
    if foe and foe["npc_id"] not in queued:
        d["queue"].append({"npc": foe["npc_id"], "kind": "nemico", "layer": layer, "due": day + 12})
    _save(conn, d)
    if n:
        return [f"Senti, lontani sotto di te, {n} fili che ti tengono legato al mondo di sotto. Non si spezzano: "
                "si tendono. Chi ti ama ti seguirà."]
    return []


def daily(conn, t: int, rng, player) -> list[str]:
    from engine.systems import ascension, npc_factory, bonds, pursuers
    from engine.simulation import cultivation
    if player is None:
        return []
    d = get(conn)
    if not d["queue"]:
        return []
    day = t // 120
    here = ascension.player_layer(conn, player.id)
    out = []
    keep = []
    for q in d["queue"]:
        if day < q["due"] or q["layer"] > here or out:
            keep.append(q)
            continue
        locs = ascension.plane_locations(conn, q["layer"]) or [player.location_id]
        loc = rng.choice(locs)
        ptier = cultivation.realm_tier(conn, "player", player.id) or 1
        if q["kind"] == "nemico":
            r = conn.execute("SELECT name FROM npcs WHERE id=?;", (q["npc"],)).fetchone()
            nm = f"{r['name']} Rinato" if r else "Un nemico rinato"
            nid = npc_factory.spawn(conn, rng, archetype="anziano", location_id=loc, tier=ptier, stage=4, name=nm,
                                    traits={"pride": 95, "honor": 15, "ambition": 95}, tick=t)
            conn.execute("UPDATE npcs SET hunting=1, description=? WHERE id=?;",
                         ("Morì per mano tua nel mondo di sotto. Il cielo superiore gli ha restituito la vita, "
                          "e la memoria.", nid))
            bonds.add_bond(conn, player.id, nid, "nemesis", t, rng=rng, reason="rinato in cielo per vendicarsi")
            pursuers.on_spawn(conn, player.id, nid, "nemesi")
            out.append(f"☠ Un brivido. Nel {ascension.layer_name(q['layer'])} qualcuno pronuncia il tuo nome con odio: "
                       f"{nm}, che uccidesti nel mondo di sotto, è rinato quassù. E ricorda.")
        else:
            r = conn.execute("SELECT name, status FROM npcs WHERE id=?;", (q["npc"],)).fetchone()
            if not r or r["status"] != "alive":
                continue
            ntier = cultivation.realm_tier(conn, "npc", q["npc"]) or 1
            target = max(ntier, min(ascension.world_cap(q["layer"]), ptier - (1 if q["kind"] == "disciple" else 0)))
            if target > ntier:
                npc_factory.raise_npc(conn, q["npc"], (target - ntier) * 10)
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, q["npc"]))
            d["done"].append(q["npc"])
            out.append(f"✦ Una scala di luce si posa accanto a te, e ne scende {r['name']}, il tuo "
                       f"{LABEL.get(q['kind'], 'legame')}: «Ti ho seguito. Quassù ho ricordato chi ero davvero.» "
                       f"Ora è {cultivation.realm_label(conn, 'npc', q['npc'])}.")
            from engine.systems import chronicle
            chronicle.add(conn, "legami", f"{r['name']} ascende e ti ritrova nel {ascension.layer_name(q['layer'])}.")
    d["queue"] = keep
    _save(conn, d)
    return out


def describe(conn, player) -> str:
    d = get(conn)
    lines = ["☁ I LEGAMI CHE TI SEGUONO IN CIELO"]
    for nid in d["done"][-10:]:
        r = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()
        if r:
            lines.append(f"  ✦ {r['name']} ti ha raggiunto.")
    day = _day(conn)
    for q in d["queue"]:
        r = conn.execute("SELECT name FROM npcs WHERE id=?;", (q["npc"],)).fetchone()
        nm = r["name"] if r else "?"
        lines.append(f"  … {nm} ({LABEL.get(q['kind'], q['kind'])}): arriverà tra {max(0, q['due'] - day)} giorni"
                     if q["kind"] != "nemico" else "  … qualcosa, dal mondo di sotto, sta salendo con odio.")
    if len(lines) == 1:
        lines.append("  Nessuno, per ora. Quando ascendi, chi ti è legato ti segue nei giorni successivi.")
    return "\n".join(lines)
