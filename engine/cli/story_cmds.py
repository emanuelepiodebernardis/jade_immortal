"""
Comandi dei nuovi sistemi narrativi: scelte numerate, incontri, legami, obiettivi,
vite passate, titoli e impostazioni dell'interfaccia.

Tenuti fuori da loop.py (già molto grande): `handle` ritorna il testo se il comando è
suo, oppure None per lasciar proseguire il dispatch normale.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick
from engine.systems import state


def _find_here(conn, player, arg):
    if not arg.strip():
        return None
    return entities.find_npc_in_location(conn, player.location_id, arg)


def _choose_number(conn, player, n: int) -> str:
    from engine.systems import encounters, suggestions
    from engine.cli import loop
    if encounters.pending(conn):
        text, cmd = encounters.choose(conn, player, n)
        if cmd:
            res = loop.dispatch(conn, cmd, allow_nl=False)
            text += "\n" + (res or "")
        return text
    cmds = suggestions.stored(conn)
    if not cmds:
        return "Non c'è nessuna scelta in sospeso. Scrivi 'help' per i comandi."
    if not (1 <= n <= len(cmds)):
        return f"Scegli un numero tra 1 e {len(cmds)}."
    cmd = cmds[n - 1]
    res = loop.dispatch(conn, cmd, allow_nl=False)
    # ricorda l'ultima azione suggerita: se non ha fatto passare il tempo (es. 'market'),
    # non la riproponiamo subito identica
    state.set_json(conn, "sugg_last", {"cmd": cmd, "tick": tick.get_tick(conn)})
    return f"(→ {cmd})\n" + (res or "")


def _toggle(conn, key, arg, label) -> str:
    a = arg.strip().lower()
    if a in ("on", "si", "sì", "1"):
        state.set(conn, key, "1")
    elif a in ("off", "no", "0"):
        state.set(conn, key, "0")
    else:
        state.set(conn, key, "0" if state.flag(conn, key, True) else "1")
    return f"{label}: {'attivo' if state.flag(conn, key, True) else 'disattivato'}."


def handle(conn: sqlite3.Connection, player: entities.Player, cmd: str, arg: str) -> str | None:
    from engine.systems import bonds, encounters, storyline, rebirth
    if cmd.isdigit():
        return _choose_number(conn, player, int(cmd))
    if cmd in ("encounter", "incontro", "scelte"):
        return encounters.render(conn, player)
    if cmd in ("goals", "obiettivi", "goal", "diario", "quest"):
        return storyline.goals(conn, player)
    if cmd in ("lives", "vite", "tombe"):
        return rebirth.describe_lives(conn)
    if cmd in ("titles", "titoli"):
        tl = state.titles(conn)
        return ("Titoli conquistati: " + ", ".join(tl)) if tl else \
            "Nessun titolo, per ora. Le tue scelte e le tue imprese te ne daranno."
    if cmd == "hud":
        return _toggle(conn, "ui_hud", arg, "Riga di stato")
    if cmd in ("suggest", "suggerimenti", "suggestions"):
        return _toggle(conn, "ui_suggest", arg, "Azioni suggerite")
    if cmd in ("bonds", "legami", "relazioni"):
        return bonds.describe(conn, player)
    if cmd in ("dismiss", "congeda"):
        return bonds.dismiss(conn, tick.get_tick(conn), player)
    from engine.systems import beasts, professions
    t = tick.get_tick(conn)
    rng = random.Random(t * 101 + player.id)
    if cmd in ("beast", "bestia", "bestie", "beasts"):
        return beasts.describe(conn, player)
    if cmd in ("release", "libera"):
        return beasts.release(conn, t, player)
    if cmd in ("feed", "nutri"):
        return beasts.feed(conn, player)
    if cmd in ("tame", "doma", "addomestica"):
        npc = _find_here(conn, player, arg)
        if npc is None:
            return "Domare chi? Usa: tame <nome> (su una creatura presente)."
        text, follow = beasts.tame(conn, t, rng, player, npc)
        if follow:
            from engine.cli import loop
            text += "\n" + (loop.dispatch(conn, follow, allow_nl=False) or "")
        else:
            from engine.simulation import world_tick
            world_tick.advance(conn, tick.cost_of("short_rest"))
        return text
    if cmd in ("profession", "professione", "arte"):
        return professions.choose(conn, player.id, arg)
    if cmd in ("gather", "raccolta", "harvest", "erbe"):
        return professions.gather(conn, t, rng, player)
    if cmd in ("recipes", "ricette"):
        return professions.describe_recipes(conn, player.id)
    if cmd in ("craft", "crea", "forgia", "distilla"):
        return professions.craft(conn, t, rng, player, arg)
    if cmd in ("masters", "maestri"):
        from engine.systems import secret_masters
        return secret_masters.describe(conn, player)

    social = {"talk": "talk", "parla": "talk", "chat": "talk",
              "gift": "gift", "dona": "gift", "regala": "gift",
              "spar": "spar", "allenati": "spar", "duello_amichevole": "spar",
              "recruit": "recruit", "recluta": "recruit", "seguimi": "recruit",
              "disciple": "disciple", "maestro": "disciple", "apprendista": "disciple"}
    action = social.get(cmd)
    if action is None:
        return None
    t = tick.get_tick(conn)
    rng = random.Random(t * 97 + player.id)
    if action == "gift":
        parts = arg.rsplit(maxsplit=1)
        if len(parts) < 2 or not parts[1].isdigit():
            return "Usa: gift <nome> <pietre>  (es. 'gift Lin 30')"
        npc = _find_here(conn, player, parts[0])
        if npc is None:
            return f"Non vedi nessuno di nome '{parts[0]}' qui."
        return bonds.gift(conn, t, player, npc, int(parts[1]))
    npc = _find_here(conn, player, arg)
    if npc is None:
        return (f"Con chi? Usa: {cmd} <nome>" if not arg.strip()
                else f"Non vedi nessuno di nome '{arg}' qui.")
    kind = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if kind and kind["kind"] not in (None, "human") and action != "spar":
        return f"{npc.name} non è una persona con cui parlare."
    if action == "talk":
        return bonds.talk(conn, t, rng, player, npc)
    if action == "spar":
        return bonds.spar(conn, t, rng, player, npc)
    if action == "recruit":
        return bonds.recruit(conn, t, player, npc)
    return bonds.take_master(conn, t, player, npc)


def after_command(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Testo da mostrare dopo ogni comando: capitolo della storia pronto, HUD e
    azioni suggerite (o le scelte dell'incontro aperto)."""
    from engine.systems import encounters, storyline, suggestions
    from engine.cli import hud
    out = []
    if player.status != "alive":
        return ""
    from engine.systems import dao_superiori
    out += dao_superiori.check_awakenings(conn, player.id)
    ch = storyline.maybe_advance(conn, player)
    if ch:
        out.append(ch)
    else:
        from engine.systems import secret_masters
        ms = secret_masters.maybe_meet(conn, player)
        if ms:
            out.append(ms)
            ch = ms
    if hud.enabled(conn):
        out.append(hud.hud_line(conn, player))
    pend = encounters.pending(conn)
    if pend:
        if not ch and pend.get("tick") != tick.get_tick(conn):
            out.append("(Un incontro attende la tua scelta: 'encounter' per rileggerlo, "
                       "oppure scrivi il numero.)")
        suggestions.store(conn, [])
    elif suggestions.enabled(conn):
        sugg = suggestions.compute(conn, player)
        suggestions.store(conn, sugg)
        if sugg:
            out.append(suggestions.render_block(sugg))
    return "\n".join(out)
