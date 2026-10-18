"""
CAVALCATURE (Aggiornamento 63) — monti la tua bestia invece di farla combattere accanto a te.

Una bestia montata non attacca da sola: ti porta. La sua forza diventa la tua: attacco in più e danni
subiti in meno, tanto più quanto è forte rispetto a te. Se il suo elemento è lo stesso del tuo Dao
più forte, il legame è perfetto e il dono cresce della metà. (Spunto: le cavalcature di Immortal
Taoists, che danno attributi a chi le monta, di più se vengono dalla stessa regione.)

  cavalca [nome]   monti una delle tue bestie
  smonta           scendi: la bestia torna a combattere al tuo fianco
"""

from __future__ import annotations

from engine.systems import state

KEY = "mount"


def mounted(conn, pid: int = 1):
    from engine.systems import beasts
    nid = state.get_int(conn, KEY, 0)
    if not nid:
        return None
    return next((r for r in beasts.pets(conn, pid) if r["npc_id"] == nid), None)


def mount(conn, player, arg: str) -> str:
    from engine.systems import beasts
    ps = beasts.pets(conn, player.id)
    if not ps:
        return "Non hai bestie da cavalcare. ('tame <nome>' per domarne una)"
    a = (arg or "").strip().lower()
    b = next((r for r in ps if a and a in r["name"].lower()), None) or ps[0]
    state.set(conn, KEY, str(b["npc_id"]))
    m = bonus(conn, player.id)
    return (f"Monti {b['name']}. Ora non combatte accanto a te: ti porta. Attacco +{m['atk'] * 100:.0f}%, "
            f"danni subiti −{m['taken'] * 100:.0f}%" + (" — il suo elemento è il tuo: legame perfetto." if m["match"] else ".")
            + " ('smonta' per scendere)")


def dismount(conn, player) -> str:
    b = mounted(conn, player.id)
    state.delete(conn, KEY)
    return f"Scendi da {b['name']}: torna a combattere al tuo fianco." if b else "Non stai cavalcando nessuna bestia."


def _top_dao(conn, pid: int) -> str | None:
    r = conn.execute("SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? "
                     "ORDER BY comprehension DESC LIMIT 1;", (pid,)).fetchone()
    return r["dao_key"] if r else None


def bonus(conn, pid: int = 1) -> dict:
    from engine.systems import beasts
    from engine.simulation import combat
    b = mounted(conn, pid)
    if not b:
        return {"atk": 0.0, "taken": 0.0, "match": False}
    pa = combat.combat_power(conn, "player", pid)["attack"] or 1
    ba = combat.combat_power(conn, "npc", b["npc_id"])["attack"] or 0
    r = max(0.0, min(2.0, ba / pa))
    tr = beasts.traits(conn, b["npc_id"])
    match = bool(tr and _top_dao(conn, pid) in (tr["elements"] or "").split(","))
    k = 1.5 if match else 1.0
    return {"atk": min(0.35, (0.06 + 0.15 * r) * k), "taken": min(0.18, (0.03 + 0.07 * r) * k), "match": match}


def combat(conn, fx) -> list[str]:
    b = mounted(conn)
    if not b:
        return []
    m = bonus(conn)
    fx.p.atk_mult *= 1.0 + m["atk"]
    fx.p.prof["taken"] = fx.p.prof.get("taken", 0.0) + m["taken"]
    return [f"Cavalchi {b['name']}: la sua forza è la tua."]


def describe(conn, player) -> str:
    b = mounted(conn, player.id)
    if not b:
        return "Non cavalchi nessuna bestia. ('cavalca [nome]')"
    m = bonus(conn, player.id)
    return (f"Cavalchi {b['name']}: attacco +{m['atk'] * 100:.0f}%, danni subiti −{m['taken'] * 100:.0f}%"
            + (" (legame perfetto)." if m["match"] else "."))
