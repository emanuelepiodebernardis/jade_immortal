"""
ECHI — le conseguenze che ritornano.

Il mondo si ricorda di te. Chi hai AIUTATO, chi hai OFFESO, chi hai RISPARMIATO dopo averlo
battuto: settimane o mesi dopo, qualcuno di loro ti ritrova — cambiato, spesso più forte.
  · chi hai aiutato torna con un dono, un aiuto o la voglia di seguirti;
  · chi hai offeso torna a chiedere il conto (combattere, chiedere perdono, sfuggire);
  · chi hai risparmiato può tornare grato… o con la rabbia di chi ha dovuto inginocchiarsi.
Ogni eco entra nella cronaca. Le scene passano dal regista (non arrivano a raffica).
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "world_echoes"
MAX = 40


def _all(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []


def record(conn, npc_id: int, kind: str, about: str) -> None:
    """kind: 'aiutato' | 'offeso' | 'risparmiato'."""
    if not npc_id:
        return
    r = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not r or (r["kind"] or "human") != "human":
        return
    es = [e for e in _all(conn) if e["npc"] != npc_id]
    day = tick_mod.get_tick(conn) // 120
    rng = random.Random(npc_id * 31 + day)
    es.append({"npc": npc_id, "kind": kind, "about": about[:80], "day": day, "due": day + rng.randint(20, 60)})
    state.set_json(conn, KEY, es[-MAX:])


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import encounters
    if encounters.pending(conn):
        return []
    day = t // 120
    es = _all(conn)
    for e in es:
        if day < e["due"]:
            continue
        es.remove(e)
        state.set_json(conn, KEY, es)
        r = conn.execute("SELECT status FROM npcs WHERE id=?;", (e["npc"],)).fetchone()
        if not r or r["status"] != "alive":
            continue
        sc = _scene(conn, rng, player, e)
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, e["npc"]))
        txt = encounters.start_scene(conn, player, sc)
        return [txt] if txt else []
    return []


def _grow(conn, npc_id: int, player_id: int, ratio: float) -> None:
    """Il tempo è passato anche per loro: crescono fino a starti vicino."""
    from engine.systems import npc_factory, perception
    for _ in range(80):
        if perception.strength_ratio(conn, player_id, npc_id) <= ratio:
            return
        npc_factory.raise_npc(conn, npc_id, 1)


def _scene(conn, rng, player, e: dict) -> dict:
    from engine.simulation import cultivation
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (e["npc"],)).fetchone()["name"]
    kind = e["kind"]
    if kind == "risparmiato":
        kind = "aiutato" if rng.random() < 0.55 else "offeso"
        how = "grato" if kind == "aiutato" else "rancore"
    else:
        how = None
    ctx = {"npc_id": e["npc"], "npc_name": nm}
    if kind == "aiutato":
        _grow(conn, e["npc"], player.id, 1.4)
        realm = cultivation.realm_name(conn, "npc", e["npc"])
        gift = 60 + 40 * (cultivation.realm_tier(conn, "player", player.id) or 1)
        text = (f"{nm} ti riconosce da lontano e ti corre incontro. Ricordi? {e['about']}. "
                f"Ora è al regno {realm}. «Non ho mai dimenticato quello che hai fatto.»")
        if how:
            text = (f"{nm} — quello che avevi battuto e lasciato vivere ({e['about']}) — ti sbarra la strada… e "
                    f"si inchina. Ora è al regno {realm}. «Mi hai lasciato la vita. Ci ho pensato a lungo.»")
        return {"key": "eco_grato", "title": f"Un'eco dal passato: {nm}", "event_type": "bond", "ctx": ctx,
                "text": text,
                "choices": [
                    {"label": "Accetti il suo dono", "effects": {"stones": gift, "relation": 10,
                                                               "text": f"Ti lascia {gift} pietre spirituali e un sorriso."}},
                    {"label": "Gli proponi di viaggiare con te", "effects": {"relation": 25, "bond": "companion",
                                                                            "bond_reason": "un debito d'onore"}},
                    {"label": "Non gli chiedi nulla: «Basta sapere che stai bene.»",
                     "effects": {"relation": 35, "heart": 4, "karma": 15,
                                 "text": "Se ne va commosso. Il mondo, a volte, restituisce."}}]}
    _grow(conn, e["npc"], player.id, 0.95)
    realm = cultivation.realm_name(conn, "npc", e["npc"])
    pay = 80 + 60 * (cultivation.realm_tier(conn, "player", player.id) or 1)
    text = (f"{nm} non ha dimenticato ({e['about']}). Ora è al regno {realm}, e ti ha cercato a lungo. "
            "«È arrivato il giorno di pareggiare i conti.»")
    if how:
        text = (f"{nm} — quello che avevi battuto e risparmiato ({e['about']}) — è tornato, al regno {realm}. "
                "«Avresti dovuto uccidermi quando potevi.»")
    return {"key": "eco_rancore", "title": f"Un'eco dal passato: {nm}", "event_type": "bond", "ctx": ctx,
            "text": text, "sticky": True,
            "choices": [
                {"label": "Lo affronti", "effects": {}, "command": f"attack {nm.split()[0]}"},
                {"label": "Lo affronti a turni", "effects": {}, "command": f"duello {nm.split()[0]}"},
                {"label": f"Chiedi perdono e offri {pay} pietre", "effects": {"stones": -pay, "relation": 40,
                                                                             "npc_leaves": True, "fame": -2,
                                                                             "text": "Accetta. Il conto è chiuso."}},
                {"label": "Sfuggi nella folla", "check": {"stat": "istinto", "dc": 60},
                 "success": {"npc_leaves": True, "text": "Ti perde di vista. Per ora."},
                 "failure": {"injury": 2, "command": f"attack {nm.split()[0]}", "text": "Ti raggiunge!"}}]}


def on_choice(conn, ctx: dict, eff: dict, title: str) -> None:
    """Dagli effetti di una scelta: hai aiutato o offeso il personaggio della scena?"""
    nid = (ctx or {}).get("npc_id")
    if not nid or str((ctx or {}).get("title", title)).startswith("Un'eco"):
        return
    rel = int(eff.get("relation", 0) or 0)
    if rel >= 10 or eff.get("bond") in ("companion", "sworn"):
        record(conn, nid, "aiutato", f"«{title}»")
    elif rel <= -10:
        record(conn, nid, "offeso", f"«{title}»")
