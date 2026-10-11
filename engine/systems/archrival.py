"""
L'ARCINEMICO — il rivale che ti segue per tutta la vita (e oltre), senza mai essere l'ultimo.

Ispirato al «sistema Nemesi»: l'arcinemico RICORDA. Ricorda come l'hai battuto (le
CICATRICI che porta), ricorda quando ha vinto lui, e cresce: ogni volta che ti sconfigge
sale di livello, e cresce anche da solo, come i prodigi. Ricompare ogni tanto, dove sei tu.
Se lo uccidi, la sua ombra non muore: un fratello, un discepolo, un erede raccoglie il suo
nome e la sua rabbia — con la memoria di ciò che gli hai fatto. Una catena senza fine.

  arcinemico       chi è, cosa ricorda di te, quante volte vi siete scontrati
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "archrival"
_HEIRS = ["il fratello minore", "il discepolo prediletto", "la sorella gemella", "il figlio", "l'allievo segreto",
          "il compagno del Dao", "il vecchio servitore che lo crebbe"]
_EPITHETS = ["il Senza Pari", "Spada di Giada", "il Prescelto", "Figlio del Cielo", "Occhi di Brace", "il Freddo",
             "Mano di Ferro"]


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def npc_name(conn, d) -> str:
    r = conn.execute("SELECT name FROM npcs WHERE id=?;", (d["npc"],)).fetchone()
    return r["name"] if r else "l'arcinemico"


def create(conn, rng: random.Random, player, heir_of: dict | None = None) -> str:
    from engine.systems import npc_factory, prodigies
    from engine.simulation import cultivation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    nid = npc_factory.spawn(conn, rng, archetype="discepolo", location_id=player.location_id,
                            tier=ptier + (1 if heir_of else 0),
                            stage=min(10, 3 + rng.randint(0, 4) + (2 * heir_of["gen"] if heir_of else 0)),
                            traits={"pride": 95, "ambition": 95, "honor": 30}, tick=tick_mod.get_tick(conn))
    gen = (heir_of["gen"] + 1) if heir_of else 1
    d = {"npc": nid, "gen": gen, "epithet": rng.choice(_EPITHETS), "wins": 0, "losses": 0, "scars": [],
         "memory": list(heir_of.get("memory", []))[-3:] if heir_of else [], "next_day": tick_mod.get_tick(conn) // 120 + 12,
         "level": heir_of["level"] if heir_of else 1}
    if heir_of:
        d["memory"].append(f"Hai ucciso {heir_of['name']}.")
    d["name"] = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    _save(conn, d)
    ids = state.get_json(conn, prodigies.KEY, []) or []
    if nid not in ids:
        ids.insert(0, nid)
        state.set_json(conn, prodigies.KEY, ids)
    return d["name"]


def _promote(conn, d: dict, stages: int) -> None:
    from engine.systems import npc_factory
    npc_factory.raise_npc(conn, d["npc"], stages)
    d["level"] += 1


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import encounters, destinies
    d = get(conn)
    if not d:
        return []
    out = []
    r = conn.execute("SELECT status FROM npcs WHERE id=?;", (d["npc"],)).fetchone()
    if not r or r["status"] != "alive":
        # l'erede non arriva subito: cresce nell'ombra per qualche settimana, poi si rivela
        day = t // 120
        if "heir_day" not in d:
            d["heir_day"] = day + rng.randint(20, 40)
            _save(conn, d)
            return []
        if day < d["heir_day"]:
            return []
        heir = rng.choice(_HEIRS)
        prev = dict(d)
        prev.pop("heir_day", None)
        name = create(conn, rng, player, heir_of=prev)
        out.append(f"☠ La morte di {prev['name']} non chiude nulla: {heir}, {name}, raccoglie il suo nome. "
                   f"«Ricordo tutto. Hai ucciso {prev['name']}.» (arcinemico, {prev['gen'] + 1}ª generazione)")
        return out
    if rng.random() < 0.25 * destinies.rival_mult(conn):
        from engine.systems import npc_factory
        npc_factory.raise_npc(conn, d["npc"], 1)
    day = t // 120
    if day >= d["next_day"] and not encounters.pending(conn):
        d["next_day"] = day + rng.randint(15, 25)
        _save(conn, d)
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, d["npc"]))
        txt = encounters.start_scene(conn, player, scene(conn, d))
        if txt:
            out.append(txt)
    return out


def scene(conn, d: dict) -> dict:
    name = npc_name(conn, d)
    mem = ""
    if d["scars"]:
        mem = f" Porta ancora la cicatrice: «{d['scars'][-1]}»."
    elif d["memory"]:
        mem = f" «{d['memory'][-1]}»"
    elif d["wins"]:
        mem = " «L'ultima volta ti ho lasciato nella polvere. Sei venuto a farti umiliare di nuovo?»"
    return {"key": "arcinemico", "title": f"L'arcinemico: {name} «{d['epithet']}»", "event_type": "bond",
            "text": f"{name} ti sbarra la strada, più forte di quanto ricordassi.{mem}",
            "ctx": {"npc_id": d["npc"], "npc_name": name}, "sticky": True,
            "choices": [{"label": "Lo affronti", "effects": {}, "command": f"attack {name}"},
                        {"label": "Lo eviti: non è ancora il momento", "effects": {"heart": -2},
                         "text": "Ride alle tue spalle mentre ti allontani."}]}


def on_fight(conn, player, npc_id: int, won: bool, killed: bool) -> list[str]:
    d = get(conn)
    if not d or d["npc"] != npc_id:
        return []
    name = npc_name(conn, d)
    out = []
    if won:
        d["losses"] += 1
        if not killed:
            scar = random.choice(["Mi hai spezzato il braccio", "Mi hai sfregiato il volto", "Mi hai umiliato davanti a tutti",
                                  "Mi hai lasciato a terra nel fango", "Mi hai spezzato la spada"])
            d["scars"].append(scar)
            _promote(conn, d, 2)                     # torna più forte, come i capitani di Sauron
            out.append(f"{name} fugge giurando vendetta. Tornerà — e se lo ricorderà.")
    else:
        d["wins"] += 1
        _promote(conn, d, 3)
        d["memory"].append("Ti ho battuto.")
        out.append(f"{name} ride sopra di te: la vittoria lo rende ancora più forte.")
    _save(conn, d)
    return out


def describe(conn, player) -> str:
    from engine.systems import perception
    from engine.simulation import cultivation
    d = get(conn)
    if not d:
        return "Nessun arcinemico, per ora. Arriverà."
    name = npc_name(conn, d)
    alive = conn.execute("SELECT status FROM npcs WHERE id=?;", (d["npc"],)).fetchone()["status"] == "alive"
    lines = [f"⚔ ARCINEMICO — {name} «{d['epithet']}» ({d['gen']}ª generazione)",
             f"  {cultivation.realm_label(conn, 'npc', d['npc'])} — "
             f"{perception.relative_strength(conn, player.id, d['npc']) if alive else 'caduto'}",
             f"  Scontri: ti ha battuto {d['wins']} volte, l'hai battuto {d['losses']} volte."]
    if d["scars"]:
        lines.append("  Cicatrici che ricorda: " + "; ".join(d["scars"][-3:]))
    if d["memory"]:
        lines.append("  Ciò che ricorda: " + "; ".join(d["memory"][-3:]))
    return "\n".join(lines)
