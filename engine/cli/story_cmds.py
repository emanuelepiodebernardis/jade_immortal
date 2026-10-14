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
    from engine.systems import bonds, encounters, storyline, rebirth, captivity
    if captivity.active(conn) and (cmd in _MOVE_CMDS or (cmd == "dimora" and arg.strip().lower().startswith("torna"))):
        return captivity.blocked_msg()
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
    if cmd in ("arti", "lavori", "lavoro", "mestieri", "professioni"):
        if not arg.strip():
            from engine.systems import menus
            return menus.show(conn, player, "arti")
        return professions.menu_command(conn, player.id, arg)
    if cmd in ("gather", "raccolta", "harvest", "erbe"):
        return professions.gather(conn, t, rng, player)
    if cmd in ("recipes", "ricette"):
        return professions.describe_recipes(conn, player.id, professions._key(arg) if arg.strip() else None)
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
        return ascension.ascend(conn, player, arg)
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
    if cmd in ("duello", "duel", "aturni"):
        from engine.systems import duel
        return duel.start(conn, player, arg)
    if cmd == "duello_azione":
        from engine.systems import duel
        return duel.command(conn, player, arg)
    if cmd in ("favori", "favors"):
        from engine.systems import dialogues
        return dialogues.describe(conn, player)
    if cmd in ("favore", "favor"):
        from engine.systems import dialogues
        return dialogues.fulfil(conn, player, arg)
    if cmd in ("cronaca", "chronicle", "annali"):
        from engine.systems import chronicle
        return chronicle.describe(conn, player, arg)
    if cmd in ("reincarnati", "reincarnazione", "samsara"):
        from engine.systems import rebirth
        if arg.strip().lower() in ("conferma", "si", "sì") and not rebirth.hardcore(conn):
            return rebirth.voluntary(conn, player)
        return rebirth.voluntary_preview(conn, player)
    if cmd in ("ricomincia", "restart", "nuovo_mondo"):
        from engine.systems import rebirth, state as _st
        if arg.strip().lower() in ("conferma", "si", "sì"):
            _st.set(conn, rebirth.RESTART_KEY, "1")
            return "Il mondo attuale andrà negli annali (resta salvato in archivio). Un mondo nuovo sta per nascere…"
        return ("RICOMINCIA DA ZERO: il mondo attuale va in archivio (database/saves/archivio_<data>.db, lo puoi "
                "ricaricare) e ne nasce uno nuovo, con un personaggio nuovo. Per farlo: 'ricomincia conferma'.")
    if cmd in ("senza_ritorno", "hardcore", "modalita"):
        from engine.systems import rebirth
        a = arg.strip().lower().replace("senza_ritorno", "").strip()
        if a in ("si", "sì", "on", "1"):
            return rebirth.set_hardcore(conn, True)
        if a in ("no", "off", "0"):
            return rebirth.set_hardcore(conn, False)
        return ("Modalità attuale: " + ("SENZA RITORNO (morte definitiva)" if rebirth.hardcore(conn) else
                "normale (alla morte rinasci)") + ". 'senza_ritorno si|no' per cambiarla.")
    if cmd in ("mete", "destinazioni", "dove"):
        from engine.systems import travel
        return travel.describe(conn, player)
    if cmd in ("vai", "raggiungi", "goto"):
        from engine.systems import travel
        return travel.go(conn, player, arg)
    if cmd in ("iscriviti", "partecipa") and arg.strip():
        from engine.systems import travel
        res = travel.join(conn, player, arg)
        if res is not None:
            return res
    if cmd in ("svolte", "traguardi", "milestones"):
        from engine.systems import svolte
        return svolte.describe(conn, player)
    if cmd in ("vola", "fly", "volo"):
        from engine.systems import svolte
        return svolte.fly(conn, player, arg)
    if cmd in ("crea_dao", "creadao"):
        from engine.systems import svolte
        return svolte.create_dao(conn, player, arg)
    if cmd in ("capolavoro", "masterpiece"):
        from engine.systems import svolte
        return svolte.masterpiece(conn, player, arg)
    if cmd in ("ritmo", "regista", "pacing"):
        from engine.systems import director
        return director.describe(conn)
    if cmd in ("trama", "storia", "plot"):
        from engine.systems import master_plot
        return master_plot.describe(conn, player)
    if cmd in ("arcinemico", "archrival", "rivale"):
        from engine.systems import archrival
        return archrival.describe(conn, player)
    if cmd in ("regni", "kingdoms", "imperi"):
        from engine.systems import kingdoms
        if arg.strip().lower() in ("elenco", "lista", "tutti"):
            return kingdoms.describe(conn, player)
        from engine.systems import menus
        return menus.show(conn, player, "regni")
    if cmd in ("corte", "court"):
        from engine.systems import kingdoms
        return kingdoms.court(conn, player)
    if cmd in ("sostieni", "support"):
        from engine.systems import kingdoms
        return kingdoms.back(conn, player, arg)
    if cmd in ("tributo", "tribute"):
        from engine.systems import kingdoms
        return kingdoms.tribute(conn, player, arg)
    if cmd in ("guerra_regni", "kingdomwar"):
        from engine.systems import kingdoms
        return kingdoms.war(conn, player)
    if cmd in ("trono", "throne", "usurpa"):
        from engine.systems import kingdoms
        return kingdoms.seize(conn, player)
    if cmd in ("razze", "races", "razza"):
        from engine.systems import race_realms
        return race_realms.command(conn, player, arg)
    if cmd in ("ambasciata", "embassy"):
        from engine.systems import races
        return races.embassy(conn, player, arg)
    if cmd in ("era", "ere", "epoca"):
        from engine.systems import eras
        return eras.describe(conn, player)
    if cmd in ("calamita", "calamità", "calamity"):
        from engine.systems import eras
        return eras.fight_wave(conn, player)
    if cmd in ("gara", "gare", "contest"):
        from engine.systems import contests
        return contests.command(conn, player, arg)
    if cmd in ("evadi", "fuggi", "escape"):
        from engine.systems import captivity
        return captivity.escape_step(conn, player)
    if cmd in ("anello", "ring", "maestro_anello"):
        from engine.systems import mentor_ring
        return mentor_ring.command(conn, player, arg)
    if cmd in ("spazio", "mondo_interiore", "bottiglia"):
        from engine.systems import inner_space
        return inner_space.command(conn, player, arg)
    if cmd in ("clone", "cloni", "clones"):
        from engine.systems import clones
        return clones.command(conn, player, arg)
    if cmd in ("elementi", "celesti", "elementi_celesti"):
        from engine.systems import celestial_elements
        return celestial_elements.command(conn, player, arg)
    if cmd in ("famiglia", "family", "clan"):
        from engine.systems import family
        if not arg.strip():
            from engine.systems import menus
            return menus.show(conn, player, "famiglia")
        return family.command(conn, player, arg)
    if cmd in ("scruta", "senso", "scan"):
        from engine.systems import divine_sense
        return divine_sense.scan(conn, player, arg)
    if cmd in ("cela", "nascondi", "conceal"):
        from engine.systems import divine_sense
        return divine_sense.toggle(conn, arg)
    if cmd in ("tesori", "treasures", "inventario_vivo"):
        from engine.systems import treasury
        return treasury.command(conn, player, arg)
    if cmd in ("marionette", "puppets"):
        from engine.systems import puppets
        return puppets.describe(conn, player)
    if cmd in ("marionetta", "puppet"):
        from engine.systems import puppets
        parts = arg.split(maxsplit=1)
        if parts and parts[0].lower() in ("crea", "create"):
            return puppets.create_puppet(conn, player)
        if parts and parts[0].lower() in ("potenzia", "upgrade"):
            return puppets.upgrade_puppet(conn, player, parts[1] if len(parts) > 1 else "")
        return puppets.describe(conn, player)
    if cmd in ("tesoro", "treasure"):
        from engine.systems import puppets
        parts = arg.split(maxsplit=1)
        if parts and parts[0].lower() in ("forgia", "forge"):
            return puppets.forge_treasure(conn, player, parts[1] if len(parts) > 1 else "")
        if parts and parts[0].lower() in ("nutri", "feed"):
            return puppets.feed(conn, player, parts[1] if len(parts) > 1 else "")
        return puppets.describe(conn, player)
    if cmd in ("retaggio", "legacy", "frammenti"):
        from engine.systems import lost_legacy
        return lost_legacy.describe(conn, player)
    if cmd in ("gu", "insetti"):
        from engine.systems import gu
        return gu.command(conn, player, arg)
    if cmd in ("bandiera", "soulflag"):
        from engine.systems import soul_war
        return soul_war.describe(conn, player)
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
    if cmd in ("corpo", "costituzione", "body") and arg.strip().lower().startswith(("supremo", "fondi", "fusione")):
        from engine.systems import supreme_body
        return supreme_body.unite(conn, player)
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
        from engine.systems import blood_menu
        return blood_menu.command(conn, player, arg)
    if cmd in ("trame", "intrighi", "trama_intrighi"):
        from engine.systems import intrigues
        return intrigues.command(conn, player, arg)
    if cmd in ("indaga", "investiga"):
        from engine.systems import intrigues
        return intrigues.investigate(conn, player, arg)
    if cmd in ("evolvi", "evolvi_sangue", "evoluzione"):
        from engine.systems import blood_evolution
        return blood_evolution.evolve(conn, player, arg)
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
        if not arg.strip():
            from engine.systems import menus
            return menus.show(conn, player, "dimora")
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
        from engine.systems import sect_menu
        return sect_menu.command(conn, player, arg)
    if cmd in ("profondi", "dao_profondi", "sfida_cielo", "guerra_cielo"):
        from engine.systems import deep_dao
        return deep_dao.command(conn, player, arg)
    if cmd in ("arcano", "arcani", "arcane"):
        from engine.systems import deep_dao
        return deep_dao.use_arcane(conn, player, arg)
    if cmd in ("cielo", "giudizio") and (arg.strip() or cmd == "giudizio"):
        from engine.systems import deep_dao
        return deep_dao.heaven_command(conn, player, arg)
    if cmd in ("spiriti", "spiriti_dao", "personificazioni"):
        from engine.systems import dao_spirits
        return dao_spirits.command(conn, player, arg)
    if cmd in ("attributi", "punti", "stats"):
        from engine.systems import attributes
        return attributes.command(conn, player, arg)
    if cmd in ("frontiera", "frontier", "anelli"):
        from engine.systems import frontier
        return frontier.describe(conn, player)
    if cmd in ("mistero", "misteri"):
        from engine.systems import frontier
        return frontier.resolve(conn, player, arg) if arg.strip() else frontier.describe(conn, player)
    if cmd in ("bacheca", "board") and not arg.strip():
        from engine.systems import menus
        return menus.show(conn, player, "bacheca")
    if cmd in ("quotidiana", "missione_quotidiana", "daily", "missione"):
        from engine.systems import system_daily
        return system_daily.describe(conn, player)
    if cmd in ("finestra", "stato_finestra", "finestra_stato", "status_window"):
        from engine.systems import attributes
        return attributes.window_text(conn, player.id)
    if cmd in ("osserva", "observe", "scruta_stato"):
        from engine.systems import attributes
        return attributes.observe(conn, player, arg)
    if cmd in ("costituzione", "corpo_leggendario", "fisico"):
        from engine.systems import constitutions
        return constitutions.describe_full(conn)
    if cmd in ("raccogli", "prendi", "raccogli_tutto", "prenditutto"):
        from engine.systems import auto_collect
        return auto_collect.collect_everything(conn, player)
    if cmd in ("autoraccolta", "auto_raccolta", "autoloot"):
        from engine.systems import auto_collect
        return auto_collect.toggle(conn, auto_collect.LOOT_KEY, arg, "Raccolta automatica del bottino")
    if cmd in ("autoassorbi", "auto_assorbi", "autoassorbimento"):
        from engine.systems import auto_collect
        return auto_collect.toggle(conn, auto_collect.ABSORB_KEY, arg, "Assorbimento automatico di essenze, nuclei, manuali, incensi")
    if cmd in ("rendite", "guadagni", "soldi", "entrate", "income"):
        from engine.systems import income
        return income.command(conn, player, arg)
    if cmd in ("tecniche", "fucina", "fondi"):
        from engine.systems import technique_forge
        if cmd == "fondi":
            arg = "fondi " + arg
        return technique_forge.command(conn, player, arg)
    if cmd in ("tempra", "temprati", "spirito", "anima"):
        from engine.systems import soul_temper
        if arg.strip().lower() in ("info", "stato", "?"):
            return soul_temper.describe(conn, player)
        return soul_temper.session(conn, player)
    if cmd in ("sigilla", "marchia", "asservisci", "soggioga", "sottometti"):
        from engine.systems import dominion
        return dominion.seal_command(conn, player, arg)
    if cmd in ("rianima", "resuscita", "salma"):
        from engine.systems import dominion
        return dominion.revive_command(conn, player, arg)
    if cmd in ("dominio", "servitori", "vassalli", "vassalle"):
        from engine.systems import dominion
        return dominion.command(conn, player, arg)
    if cmd in ("servo", "serva"):
        from engine.systems import dominion
        return dominion.servant_command(conn, player, arg)
    if cmd in ("faide", "rancori", "debiti", "vendette", "faida"):
        from engine.systems import feuds
        return feuds.command(conn, player, arg)
    if cmd in ("menu", "menù"):
        from engine.systems import menus
        return menus.show(conn, player, "menu")
    if cmd in ("coltivazione", "crescita"):
        from engine.systems import menus
        return menus.show(conn, player, "coltivazione")
    if cmd in ("eventi", "events"):
        from engine.systems import menus
        return menus.show(conn, player, "eventi")
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
        from engine.systems import dialogues
        dlg = dialogues.talk(conn, t, rng, player, npc)
        return dlg if dlg else bonds.talk(conn, t, rng, player, npc)
    if action == "spar":
        return bonds.spar(conn, t, rng, player, npc)
    if action == "recruit":
        return bonds.recruit(conn, t, player, npc)
    return bonds.take_master(conn, t, player, npc)


def story_tick(conn, player) -> str | None:
    """Prova a far avanzare la storia: origine, archi del mondo, trama maestra, maestri segreti."""
    from engine.systems import storyline, world_arcs, master_plot, secret_masters, director, encounters
    if encounters.pending(conn) or not director.story_ready(conn):
        return None                            # un capitolo alla volta, con il tempo di respirare
    fns = [storyline.maybe_advance, master_plot.maybe_advance, world_arcs.maybe_advance,
           secret_masters.maybe_meet]
    for i in director.story_order(conn, len(fns)):    # le trame si alternano
        txt = fns[i](conn, player)
        if txt:
            director.story_shown(conn, i)
            return txt
    return None


_MOVE_CMDS = {"vai", "raggiungi", "goto", "vola", "fly", "volo", "move", "go", "n", "s", "e", "w", "north", "south", "east", "west", "nord", "sud", "est", "ovest",
              "home", "warzone", "raidtarget", "teletrasporto", "teleport", "tp", "up", "down", "su", "giu", "giù",
              "enter", "entra", "ascendi_mondo"}


def after_command(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Testo da mostrare dopo ogni comando: capitolo della storia pronto, HUD e
    azioni suggerite (o le scelte dell'incontro aperto)."""
    from engine.systems import encounters, storyline, suggestions, menus
    from engine.cli import hud
    out = []
    if player.status != "alive":
        return ""
    from engine.systems import dao_superiori, system_daily, frontier
    out += dao_superiori.check_awakenings(conn, player.id)
    out += system_daily.check(conn, player)
    out += frontier.expand(conn, player)
    from engine.systems import supreme_body
    out += supreme_body.after_command(conn, player)
    ch = story_tick(conn, player)
    if ch:
        out.append(ch)
    if hud.enabled(conn):
        out.append(hud.hud_line(conn, player))
    pend = encounters.pending(conn)
    if pend:
        if not ch and pend.get("tick") != tick.get_tick(conn):
            out.append("(Un incontro attende la tua scelta: 'encounter' per rileggerlo, "
                       "oppure scrivi il numero.)")
        suggestions.store(conn, [])
    elif menus.consume_open(conn):
        pass                                  # i numeri restano quelli del menu appena aperto
    elif suggestions.enabled(conn):
        sugg = suggestions.compute(conn, player)
        suggestions.store(conn, sugg)
        if sugg:
            out.append(suggestions.render_block(sugg))
    return "\n".join(out)
