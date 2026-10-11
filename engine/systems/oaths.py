"""
GIURAMENTI: FRATELLANZA GIURATA (结拜) e COMPAGNO DEL DAO (道侣).

Fratellanza giurata
  giura <nome>      con chi ti è amico fraterno (rapporto ≥ 70): bruciate incenso, giurate
                    di non tradirvi. Massimo 3 fratelli giurati.
  chiama <nome>     chiedi aiuto: il fratello accorre al tuo fianco (una volta ogni 10 giorni)
  - In combattimento, un fratello giurato presente combatte con te.
  - Ogni tanto è LUI ad aver bisogno di te: hai pochi giorni per raggiungerlo. Ignorarlo
    è un tradimento: il giuramento si spezza, il karma ne soffre.
  - Uccidere un fratello giurato fa di te uno Spergiuro: infamia e karma terribili.

Compagna del Dao
  proponi <nome>    a colei che ti ama di un affetto profondo (rapporto ≥ 80) e cammina sulla
                    Via a un livello vicino al tuo: diventa la tua compagna del Dao. (Il
                    protagonista è un uomo: le compagne, come le fidanzate, sono donne.)
  - Viaggia con te; quando coltivate insieme, il Qi circola tra due corpi (doppia
    coltivazione: coltivazione e ritiro rendono molto di più).
  - Combatte al tuo fianco. Se cade, il lutto lascia un segno sul tuo cuore.
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

MAX_SWORN = 3
SWORN_MIN = 70
PARTNER_MIN = 80
CALL_COOLDOWN_DAYS = 10


def sworn(conn, pid: int = 1):
    from engine.systems import bonds
    bonds.ensure_table(conn)
    return [r for r in bonds._active(conn, pid, "sworn") if r["npc_status"] == "alive"]


def _human(conn, npc_id) -> bool:
    k = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    return bool(k) and k["kind"] in (None, "human")


def swear(conn, t: int, player, npc) -> str:
    from engine.systems import bonds, relations, karma
    if not _human(conn, npc.id):
        return f"Non si giura fratellanza con {npc.name}."
    kinds = bonds.bond_kinds(conn, npc.id, player.id)
    if "sworn" in kinds:
        return f"{npc.name} è già tuo fratello giurato."
    if "nemesis" in kinds:
        return "Con una nemesi? Mai."
    if len(sworn(conn, player.id)) >= MAX_SWORN:
        return f"Hai già {MAX_SWORN} fratelli giurati: un giuramento non si fa alla leggera."
    d = relations.get_disposition(conn, npc.id, player.id)
    if d.score < SWORN_MIN:
        return (f"{npc.name} ti stima, ma non abbastanza da legare la sua vita alla tua "
                f"(serve un'amicizia fraterna, rapporto ≥ {SWORN_MIN}; ora {d.score}).")
    bonds.add_bond(conn, player.id, npc.id, "sworn", t, reason="giuramento di fratellanza")
    karma.adjust_karma(conn, "player", player.id, 10, "giuramento di fratellanza", t)
    relations.adjust(conn, npc.id, 20, t, player.id)
    if state.grant_title(conn, "Fratello di Giuramento"):
        extra = "\n✧ Nuovo titolo: «Fratello di Giuramento» ✧"
    else:
        extra = ""
    return (f"Accendete tre bastoncini d'incenso e vi inginocchiate davanti al Cielo e alla Terra:\n"
            f"«Non nati lo stesso giorno, possiamo morire lo stesso giorno.» "
            f"{npc.name} ora è tuo FRATELLO GIURATO. ('chiama {npc.name.split()[0]}' se hai bisogno){extra}")


def call(conn, t: int, player, name: str) -> str:
    rows = sworn(conn, player.id)
    r = next((x for x in rows if name.strip().lower() in x["name"].lower()), None) if name.strip() else \
        (rows[0] if rows else None)
    if r is None:
        return "Chi vuoi chiamare? Solo un fratello giurato risponde a un richiamo da lontano."
    day = t // 120
    key = f"sworn_call_{r['npc_id']}"
    if day - state.get_int(conn, key, -999) < CALL_COOLDOWN_DAYS:
        return f"Hai chiamato {r['name']} da poco: lascialo respirare."
    state.set(conn, key, str(day))
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, r["npc_id"]))
    return f"Bruci un talismano di richiamo. Poco dopo {r['name']} atterra accanto a te: «Eccomi.»"


def propose(conn, t: int, player, npc) -> str:
    from engine.systems import bonds, relations
    from engine.simulation import cultivation
    if not _human(conn, npc.id):
        return f"{npc.name} non può essere la tua compagna del Dao."
    from engine.systems import npc_factory
    if not npc_factory.is_female(conn, npc.id):
        return (f"Con {npc.name} puoi giurare fratellanza ('giura'), ma la tua compagna del Dao sarà una "
                "donna.")
    if bonds.dao_partner(conn, player.id):
        return "Hai già una compagna del Dao."
    kinds = bonds.bond_kinds(conn, npc.id, player.id)
    if {"nemesis", "disciple", "master"} & kinds:
        return f"Con {npc.name} c'è già un legame che non lo permette."
    d = relations.get_disposition(conn, npc.id, player.id)
    if d.score < PARTNER_MIN:
        return (f"Tra te e {npc.name} non c'è ancora un sentimento così profondo "
                f"(serve un rapporto ≥ {PARTNER_MIN}; ora {d.score}). Passate del tempo insieme.")
    pt = cultivation.realm_tier(conn, "player", player.id) or 1
    nt = cultivation.realm_tier(conn, "npc", npc.id) or 1
    if abs(pt - nt) > 1:
        return (f"Le vostre Vie sono troppo distanti ({cultivation.realm_name(conn, 'npc', npc.id)}): "
                "la doppia coltivazione richiede regni vicini.")
    bonds.add_bond(conn, player.id, npc.id, "dao_partner", t, reason="compagni del Dao")
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, npc.id))
    msg = (f"Sotto un cielo limpido, tu e {npc.name} unite le vostre Vie: ora è la tua COMPAGNA DEL DAO. "
           "Viaggerà con te; coltivando insieme, il Qi circolerà tra i vostri corpi.")
    if state.grant_title(conn, "Compagno del Dao"):
        msg += "\n✧ Nuovo titolo: «Compagno del Dao» ✧"
    return msg


def combat_allies(conn, player_id: int, npc_id: int) -> list[dict]:
    """Fratelli giurati e compagno del Dao presenti combattono con te."""
    from engine.simulation import combat
    from engine.systems import bonds
    p = entities.get_player(conn, player_id)
    out = []
    rows = list(sworn(conn, player_id))
    dp = bonds.dao_partner(conn, player_id)
    if dp:
        rows.append(dp)
    for r in rows:
        if r["npc_id"] == npc_id or r["location_id"] != p.location_id:
            continue
        atk = combat.combat_power(conn, "npc", r["npc_id"])["attack"] * 0.45
        partner = dp is not None and r["npc_id"] == dp["npc_id"]
        out.append({"intro": (f"{r['name']}, la tua compagna del Dao, ti affianca." if partner
                              else f"{r['name']}, tuo fratello giurato, sguaina l'arma al tuo fianco."),
                    "attack": atk,
                    "line": f"{r['name']} " + random.choice(["colpisce dove ti eri aperto un varco.",
                                                             "copre il tuo fianco e affonda.",
                                                             "scatena una tecnica all'unisono con te."])})
    return out


def on_kill(conn, t: int, player, npc_id: int) -> list[str]:
    from engine.systems import bonds, karma, reputation
    kinds = bonds.bond_kinds(conn, npc_id, player.id)
    out = []
    if "sworn" in kinds:
        bonds.end_bond(conn, player.id, npc_id, "sworn", "tradito")
        karma.adjust_karma(conn, "player", player.id, -150, "assassinio di un fratello giurato", t)
        reputation.adjust(conn, player.id, infamy=30)
        if state.grant_title(conn, "Spergiuro"):
            out.append("✧ Il mondo ti marchia: «Spergiuro» ✧")
        out.append("Hai versato il sangue di chi aveva giurato di morire con te. Il Cielo ha visto.")
        from engine.systems import dao_heart
        out += dao_heart.adjust(conn, -20)
    if "dao_partner" in kinds:
        bonds.end_bond(conn, player.id, npc_id, "dao_partner", "ucciso")
        karma.adjust_karma(conn, "player", player.id, -100, "assassinio della compagna del Dao", t)
        out.append("Hai spezzato con le tue mani la Via che condividevate.")
    return out


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import bonds, karma, relations, heart_demon
    out = []
    day = t // 120
    # lutto: compagno del Dao o fratello caduto
    for kind in ("dao_partner", "sworn"):
        for r in bonds._active(conn, player.id, kind):
            if r["npc_status"] != "alive":
                bonds.end_bond(conn, player.id, r["npc_id"], kind, "morto")
                from engine.systems import chronicle
                chronicle.add(conn, "lutto", f"{r['name']}, " + ("la tua compagna del Dao" if kind == "dao_partner"
                                                                else "il tuo fratello giurato") + ", cade.")
                if kind == "dao_partner":
                    heart_demon.add_bonus(conn, -0.1)
                    out.append(f"✝ {r['name']}, la tua compagna del Dao, è caduta. Una crepa si apre nel "
                               "tuo cuore: il prossimo sfondamento sarà più difficile.")
                else:
                    out.append(f"✝ Il tuo fratello giurato {r['name']} è caduto. Il giuramento ti chiede vendetta.")
    # richieste d'aiuto dei fratelli giurati
    req = state.get_json(conn, "sworn_request")
    if req:
        if day > req["deadline"]:
            state.delete(conn, "sworn_request")
            row = conn.execute("SELECT name, status FROM npcs WHERE id=?;", (req["npc_id"],)).fetchone()
            if row and row["status"] == "alive" and "sworn" in bonds.bond_kinds(conn, req["npc_id"], player.id):
                bonds.end_bond(conn, player.id, req["npc_id"], "sworn", "abbandonato")
                karma.adjust_karma(conn, "player", player.id, -40, "fratello abbandonato", t)
                relations.adjust(conn, req["npc_id"], -80, t, player.id)
                out.append(f"Non sei venuto. {row['name']} è sopravvissuto da solo, e ha bruciato il "
                           "vostro giuramento. Il karma ricorda.")
                from engine.systems import dao_heart
                out += dao_heart.adjust(conn, -10)
        return out
    rows = [r for r in sworn(conn, player.id) if r["location_id"] and r["location_id"] != player.location_id]
    if rows and day - state.get_int(conn, "sworn_req_day", 0) >= 20 and rng.random() < 0.08:
        r = rng.choice(rows)
        state.set(conn, "sworn_req_day", str(day))
        state.set_json(conn, "sworn_request", {"npc_id": r["npc_id"], "loc": r["location_id"],
                                                "deadline": day + 5})
        loc = conn.execute("SELECT name FROM locations WHERE id=?;", (r["location_id"],)).fetchone()["name"]
        out.append(f"✉ Un messaggio macchiato di sangue da {r['name']}: «Fratello, sono in trappola a {loc}. "
                   "Vieni, se il giuramento vale ancora.» (5 giorni)")
    return out


def on_arrival(conn, player) -> str | None:
    """Se raggiungi il fratello in pericolo, scatta la scena del salvataggio."""
    from engine.systems import encounters, npc_factory
    req = state.get_json(conn, "sworn_request")
    if not req or req["loc"] != player.location_id or encounters.pending(conn):
        return None
    state.delete(conn, "sworn_request")
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (req["npc_id"],)).fetchone()["name"]
    rng = random.Random(tick_mod.get_tick(conn) + req["npc_id"])
    sc = {
        "key": "fratello_in_pericolo", "title": f"Il giuramento con {name}", "event_type": "bond",
        "text": f"{name} è a terra, accerchiato. Il capo degli aggressori, {{npc}}, si volta verso di te.",
        "spawn": {"archetype": "vagabondo", "tier_offset": 0, "stage": 8, "traits": {"compassion": 5}},
        "choices": [
            {"label": "Ti getti nella mischia", "effects": {"karma": 15, "heart": 5},
             "command": "attack {npc}"},
            {"label": "Tratti: offri pietre per la sua vita", "effects": {"stones": -150, "karma": 5,
                                                                          "npc_leaves": True,
                                                                          "text": "Prendono le pietre e se ne vanno."}},
        ]}
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    from engine.systems import relations
    relations.adjust(conn, req["npc_id"], 15, tick_mod.get_tick(conn), player.id)
    return encounters.start_scene(conn, player, sc)
