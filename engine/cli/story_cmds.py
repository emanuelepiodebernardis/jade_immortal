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
    if cmd in ("realm", "reame", "reami", "secretrealm"):
        from engine.systems import secret_realms
        if arg.strip().lower() in ("leave", "esci", "exit"):
            return secret_realms.leave(conn)
        return secret_realms.describe(conn, player)
    if cmd in ("enter", "entra"):
        from engine.systems import secret_realms
        return secret_realms.enter(conn, player)
    if cmd in ("delve", "scendi", "esplora_reame"):
        from engine.systems import secret_realms
        return secret_realms.delve(conn, player)
    if cmd in ("giura", "swear", "fratellanza", "proponi", "compagno_dao", "daopartner"):
        from engine.systems import oaths
        npc = _find_here(conn, player, arg)
        if npc is None:
            return (f"Usa: {cmd} <nome>" if not arg.strip() else f"Non vedi nessuno di nome '{arg}' qui.")
        t = tick.get_tick(conn)
        if cmd in ("giura", "swear", "fratellanza"):
            return oaths.swear(conn, t, player, npc)
        return oaths.propose(conn, t, player, npc)
    if cmd in ("up", "down", "su", "giu", "giù") and not arg.strip():
        from engine.cli import loop
        return loop.cmd_move(conn, player, cmd)
    if cmd in ("ascendi_mondo", "ascensione", "porta_celeste"):
        from engine.systems import ascension
        return ascension.ascend(conn, player)
    if cmd in ("mondi", "worlds", "strati"):
        from engine.systems import ascension
        return ascension.describe(conn, player)
    if cmd in ("classe_arte", "miaclasse", "vocazione", "via_arte"):
        from engine.systems import classes
        return classes.describe(conn, player)
    if cmd in ("sintonia", "attune", "sintonizza"):
        from engine.systems import classes
        return classes.attune(conn, player, arg)
    if cmd in ("formazioni", "formations", "arrays"):
        from engine.systems import formations
        return formations.describe(conn, player)
    if cmd in ("teletrasporto", "teleport", "tp"):
        from engine.systems import formations
        return formations.teleport(conn, player, arg)
    if cmd in ("anziani", "elders"):
        from engine.systems import sect_politics
        return sect_politics.describe_elders(conn, player)
    if cmd in ("servi", "serve"):
        from engine.systems import sect_politics
        return sect_politics.serve(conn, player, arg)
    if cmd in ("missioni", "missions", "bacheca"):
        from engine.systems import sect_politics
        return sect_politics.missions(conn, player, arg)
    if cmd in ("asta", "aste", "auction"):
        from engine.systems import auction
        return auction.command(conn, player, arg)
    if cmd in ("gongfa", "metodo", "metodi", "method"):
        from engine.systems import gongfa
        return gongfa.command(conn, player, arg)
    if cmd in ("radici", "roots", "radice", "linggen"):
        from engine.systems import spirit_roots
        return spirit_roots.describe(conn, player)
    if cmd in ("chiama", "call"):
        from engine.systems import oaths
        return oaths.call(conn, tick.get_tick(conn), player, arg)
    if cmd in ("salva", "save"):
        from engine.systems import qol
        return qol.save(conn, arg)
    if cmd in ("carica", "load"):
        from engine.systems import qol
        return qol.load(conn, arg)
    if cmd in ("salvataggi", "saves", "slot"):
        from engine.systems import qol
        return qol.list_saves()
    if cmd in ("mappa", "carta", "worldmap"):
        from engine.systems import qol
        return qol.map_text(conn, player)
    if cmd in ("colori", "colors"):
        return _toggle(conn, "ui_colors", arg, "Colori")
    if cmd in ("codex", "enciclopedia", "scoperte"):
        from engine.systems import qol
        return qol.codex(conn, player, arg)
    if cmd in ("tutorial", "guida"):
        from engine.systems import qol
        return qol.tutorial(conn, player)
    if cmd in ("tribolazioni", "fulmine_celeste", "tribolazione_celeste"):
        from engine.systems import heaven_trib
        return heaven_trib.describe(conn, player)
    if cmd in ("richieste", "requests"):
        from engine.systems import npc_quests
        return npc_quests.describe_offers(conn, player)
    if cmd in ("incarico", "accept_request") and arg.strip().isdigit():
        from engine.systems import npc_quests
        return npc_quests.accept(conn, player, int(arg.strip()))
    if cmd in ("incarichi", "quests", "incarico"):
        from engine.systems import npc_quests
        return npc_quests.describe(conn, player)
    if cmd in ("consegna", "deliver"):
        from engine.systems import npc_quests
        return npc_quests.deliver(conn, player)
    if cmd in ("uova", "eggs", "cova"):
        from engine.systems import beast_eggs
        return beast_eggs.describe(conn, player)
    if cmd in ("alleva", "breed", "accoppia"):
        from engine.systems import beast_eggs
        return beast_eggs.breed(conn, player, arg)
    if cmd in ("prodigi", "rivali", "generazione", "prodigies"):
        from engine.systems import prodigies
        return prodigies.describe(conn, player)
    if cmd in ("corpo", "costituzione", "cuore", "tossine", "body"):
        from engine.systems import dao_heart
        return dao_heart.describe(conn, player)
    if cmd in ("arma", "miaarma", "spirito_arma"):
        from engine.systems import weapon_spirit
        return weapon_spirit.command(conn, player, arg)
    if cmd in ("auto", "autopilota", "pilota", "etereo", "autopilot"):
        from engine.systems import autopilot
        return autopilot.command(conn, player, arg)
    if cmd in ("sangue", "lignaggi", "bloodline", "bloodlines", "lignaggio"):
        from engine.systems import bloodlines
        return bloodlines.describe(conn, player)
    if cmd in ("fondi_sangue", "fondisangue", "fusione_sangue"):
        from engine.systems import bloodlines
        return bloodlines.fuse(conn, player, arg)
    if cmd in ("trasformati", "transform", "trasformazione"):
        from engine.systems import bloodlines
        return bloodlines.transform(conn, player, arg)
    if cmd in ("sistema", "system", "ding"):
        from engine.systems import system_quest
        return system_quest.command(conn, player, arg)
    if cmd in ("assemblea", "assembly", "torneo_mondiale", "alleanza"):
        from engine.systems import assembly
        return assembly.command(conn, player, arg)
    if cmd in ("ritiro", "retreat", "seclusion", "clausura"):
        from engine.systems import seclusion
        return seclusion.retreat(conn, player, arg)
    if cmd in ("dimora", "abode", "grotta"):
        from engine.systems import cave_abode
        return cave_abode.command(conn, player, arg)
    if cmd in ("classifica", "classifiche", "ranking", "rankings", "lista"):
        from engine.systems import rankings
        return rankings.describe(conn, player, arg)
    if cmd in ("discepoli", "disciples"):
        from engine.systems import own_sect
        return own_sect.describe_disciples(conn, player)
    if cmd in ("fonda", "found"):
        from engine.systems import own_sect
        return own_sect.found(conn, tick.get_tick(conn), player, arg)
    if cmd in ("setta", "mysect", "lamiasetta"):
        from engine.systems import own_sect
        t = tick.get_tick(conn)
        sub = arg.strip().lower()
        if sub in ("riscuoti", "collect", "tributi"):
            return own_sect.collect(conn, player)
        if sub in ("recluta", "recruit"):
            return own_sect.recruit(conn, t, random.Random(t * 53 + player.id), player)
        if sub in ("difendi", "defend", "difesa"):
            return own_sect.defend(conn, t, random.Random(t * 59 + player.id), player)
        return own_sect.describe(conn, player)
    if cmd in ("accogli", "prendi_discepolo", "adotta", "insegna", "teach",
               "congeda_discepolo", "espelli"):
        from engine.systems import own_sect
        t = tick.get_tick(conn)
        name, _, rest = arg.strip().partition(" ")
        npc = _find_here(conn, player, name)
        if npc is None:
            return (f"Usa: {cmd} <nome>" if not name else f"Non vedi nessuno di nome '{name}' qui.")
        if cmd in ("insegna", "teach"):
            return own_sect.teach(conn, t, random.Random(t * 61 + npc.id), player, npc, rest)
        if cmd in ("congeda_discepolo", "espelli"):
            return own_sect.dismiss_disciple(conn, player, npc)
        return own_sect.accept(conn, t, player, npc)
    if cmd in ("leave", "lascia", "esci") and arg.strip().lower() in ("realm", "reame", "il reame"):
        from engine.systems import secret_realms
        return secret_realms.leave(conn)

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
    if not ch:
        from engine.systems import world_arcs
        ch = world_arcs.maybe_advance(conn, player)
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
