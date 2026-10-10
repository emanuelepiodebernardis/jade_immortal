"""
CLONI (分身) — dividi l'anima in più corpi.

Dal quarto regno, con un Dao dell'Anima a 40 (o con la guida del maestro nell'anello al
livello 5), puoi separare un CLONE ('clone crea'). La coltivazione è UNA SOLA, condivisa:
ciò che uno impara, lo sa anche l'altro. Ma i compiti si dividono:

  clone lavora      il clone resta ad allenarsi: fa crescere la tua arte, raccoglie materiali,
                    affina il tuo Dao migliore e aggiunge un po' di coltivazione ogni giorno
  clone esplora     il clone va per il mondo: trova pietre e materiali, caccia bestie (a volte
                    torna ferito e deve riposare qualche giorno)
  clone riposa      il clone medita accanto a te: in battaglia combatte al tuo fianco
  clone crea        crea un nuovo clone (poi altri: uno in più ogni 3 regni)

Ogni clone ha un LIVELLO che cresce lavorando ed esplorando, senza fine: più è alto, più
rende. Se il tuo corpo principale muore, un clone sacrifica se stesso e la tua anima vi si
trasferisce: rinasci in lui (perdi quel clone).
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "clones"
_TASKS = {"lavora": "si allena e lavora", "esplora": "esplora il mondo", "riposa": "medita al tuo fianco"}


def clones(conn) -> list[dict]:
    return state.get_json(conn, KEY, []) or []


def _save(conn, c: list[dict]) -> None:
    state.set_json(conn, KEY, c)


def max_clones(conn, pid: int) -> int:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    return 0 if tier < 4 else 1 + (tier - 4) // 3


def _can_create(conn, pid: int) -> str | None:
    from engine.systems import mentor_ring
    from engine.simulation import cultivation
    if (cultivation.realm_tier(conn, "player", pid) or 1) < 4:
        return "Dividere l'anima richiede almeno il quarto regno."
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key='anima';", (pid,)).fetchone()
    if (not r or (r["comprehension"] or 0) < 40) and mentor_ring.level(conn) < 5:
        return "Serve un Dao dell'Anima almeno a 40 (o un maestro nell'anello di livello 5 che ti guidi)."
    if len(clones(conn)) >= max_clones(conn, pid):
        return f"La tua anima regge al massimo {max_clones(conn, pid)} cloni a questo regno."
    return None


def create(conn, player) -> str:
    from engine.systems import dao_heart
    why = _can_create(conn, player.id)
    if why:
        return why
    cs = clones(conn)
    n = len(cs) + 1
    cs.append({"n": n, "task": "lavora", "level": 1, "xp": 0, "down_until": 0})
    _save(conn, cs)
    dao_heart.adjust(conn, -3)
    state.grant_title(conn, "Anima Divisa")
    return (f"Ti siedi, chiudi gli occhi e strappi un lembo della tua anima: davanti a te apre gli occhi il "
            f"tuo CLONE n.{n}. La coltivazione resta una sola. ('clone lavora' / 'clone esplora' / 'clone riposa')")


def assign(conn, task: str, which: str = "") -> str:
    cs = clones(conn)
    if not cs:
        return "Non hai cloni. ('clone crea')"
    idx = [c for c in cs if not which or str(c["n"]) == which] or cs
    for c in idx:
        c["task"] = task
    _save(conn, cs)
    who = "Il clone" if len(idx) == 1 else "I cloni"
    return f"{who} {_TASKS[task]}."


def _level_up(c: dict, xp: float) -> str | None:
    c["xp"] = c.get("xp", 0) + xp
    need = 10 * c["level"]
    if c["xp"] >= need:
        c["xp"] -= need
        c["level"] += 1
        return f"Il clone n.{c['n']} si rafforza: livello {c['level']}."
    return None


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import professions, dao_training, sects, items, dao_superiori
    cs = clones(conn)
    if not cs:
        return []
    day = t // 120
    out = []
    for c in cs:
        if c.get("down_until", 0) > day:
            continue
        lv = c["level"]
        if c["task"] == "lavora":
            if professions.profession(conn, player.id):
                state.set(conn, "profession_xp", str(professions.xp(conn, player.id) + 1 + lv // 2))
            professions.give(conn, player.id, "erbe", 1 + lv // 3)
            professions.give(conn, player.id, "minerali", lv // 3)
            rows = dao_training.trainable_daos(conn, player.id)
            if rows:
                dao_training.comprehend(conn, t, rng, rows[0]["dao_key"], multiplier=0.5 + 0.1 * lv, player_id=player.id)
            items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": round(0.03 + 0.01 * lv, 3)})
            msg = _level_up(c, 1)
        elif c["task"] == "esplora":
            stones = rng.randint(5, 20) * lv
            sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
            professions.give(conn, player.id, rng.choice(["erbe", "minerali", "nuclei"]), 1 + lv // 2)
            if rng.random() < 0.4:
                dao_superiori.bump(conn, "kills_total")
            if rng.random() < max(0.03, 0.15 - 0.01 * lv):
                c["down_until"] = day + 3
                out.append(f"Il clone n.{c['n']} torna ferito da un'esplorazione: riposerà 3 giorni.")
            msg = _level_up(c, 1.5)
        else:
            msg = _level_up(c, 0.3)
        if msg:
            out.append(msg)
    _save(conn, cs)
    return out


def combat_allies(conn, player_id: int) -> list[dict]:
    from engine.simulation import combat
    day = tick_mod.get_tick(conn) // 120
    out = []
    for c in clones(conn):
        if c["task"] != "riposa" or c.get("down_until", 0) > day:
            continue
        atk = combat.combat_power(conn, "player", player_id)["attack"] * min(0.9, 0.35 + 0.03 * c["level"])
        out.append({"intro": f"Il tuo clone n.{c['n']} si mette spalla a spalla con te.", "attack": atk,
                    "line": f"Il clone n.{c['n']} colpisce in perfetta sincronia con te."})
    return out


def try_save(conn, player) -> str | None:
    """Il corpo principale muore: un clone si sacrifica e l'anima vi si trasferisce."""
    cs = clones(conn)
    if not cs:
        return None
    c = max(cs, key=lambda x: x["level"])
    cs.remove(c)
    _save(conn, cs)
    conn.execute("UPDATE players SET status='alive' WHERE id=?;", (player.id,))
    conn.execute("UPDATE injuries SET healed=1 WHERE character_type='player' AND character_id=?;", (player.id,))
    return (f"☯ Il tuo corpo cade… ma la tua anima fugge nel CLONE n.{c['n']}, che si fa carne della tua carne. "
            "Riapri gli occhi altrove: vivo. Quel clone non c'è più.")


def describe(conn, player) -> str:
    cs = clones(conn)
    mx = max_clones(conn, player.id)
    if not cs:
        why = _can_create(conn, player.id)
        return "Non hai cloni. " + (why if why else "Puoi crearne uno: 'clone crea'.")
    day = tick_mod.get_tick(conn) // 120
    lines = [f"☯ CLONI ({len(cs)}/{mx}) — una sola coltivazione, compiti divisi"]
    for c in cs:
        st = f"ferito (riposa ancora {c['down_until'] - day} giorni)" if c.get("down_until", 0) > day else _TASKS[c["task"]]
        lines.append(f"  · Clone n.{c['n']} — livello {c['level']} — {st}")
    lines.append("'clone lavora|esplora|riposa [n]' per assegnare i compiti.")
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    sub = parts[0].lower() if parts else ""
    which = parts[1] if len(parts) > 1 else ""
    if sub in ("crea", "create", "dividi"):
        return create(conn, player)
    if sub in _TASKS:
        return assign(conn, sub, which)
    return describe(conn, player)
