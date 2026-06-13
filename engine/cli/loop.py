"""
Loop CLI (Fase 1 — World Static).

Comandi: move <dir>, look [dir], status, map, where, help, quit.
Il parser resta volutamente semplice. Il mondo è generato proceduralmente
(engine/generators/world_gen.py); qui si legge soltanto lo stato.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick
from engine.db import transaction
from engine.generators import npc_gen
from engine.systems import relations
from engine.systems import memory
from engine.systems import character
from engine.narrative import renderer as narrator
from engine.simulation import world_tick
from engine.simulation import combat
from engine.simulation import cultivation

DIRECTIONS = {
    "north": "north", "n": "north",
    "south": "south", "s": "south",
    "east": "east", "e": "east",
    "west": "west", "w": "west",
}

HELP = """Comandi disponibili:
  move <north|south|east|west>  (abbrev: n/s/e/w)  — ti sposti, +1 tick
  wait                          — attendi (il mondo avanza, osservi i dintorni)
  cultivate                     — mediti per accumulare progresso nel tuo regno
  dao                           — i Dao che pratichi e la loro comprensione
  comprehend <nome>             — affini un Dao (i Dao da combattimento ti rendono più forte)
  breakthrough                  — tenti di salire di regno (può fallire o ucciderti!)
  look                          — osservi la location corrente
  look <dir>                    — sbirci la location adiacente in quella direzione
  examine <nome>                — esamini un NPC presente (archetipo, indole, rapporto)
  greet <nome>                  — saluti un NPC: prima conoscenza / migliora il rapporto
  attack <nome>                 — attacchi un NPC (puoi morire!)
  absorb <nome>                 — (Abisso Divoratore) divori i resti di un caduto
  map                           — uscite della location corrente con destinazioni
  factions                      — elenco delle fazioni (influenza, territori)
  faction <nome>                — dettaglio di una fazione (territori, relazioni)
  sects                         — sette a cui iscriversi e dove hanno sede
  bounties                      — ricercati da cacciare (taglie e missioni)
  join                          — test d'ingresso e iscrizione alla setta locale
  class                         — compagni di classe, classifica, prossima sfida/torneo
  leave                         — lascia la tua setta
  log [n]                       — cronache recenti note al giocatore
  memories                      — ciò che il tuo personaggio ricorda (memoria attiva)
  narrate                       — rendi la scena attuale come prosa (LLM o fallback)
  chronicle                     — un breve passo di cronaca del mondo
  status                        — il tuo stato e il tick globale
  profilo                       — origine, età e affinità (descrizione qualitativa)
  where                         — nome e pericolo della location corrente
  help                          — questo messaggio
  quit / exit                   — esci
  (con Ollama attivo puoi anche scrivere in linguaggio naturale, es. "esamina il vecchio")
"""


def _npc_tag(conn: sqlite3.Connection, npc: entities.NPC) -> str:
    """Etichetta inline 'archetipo, aggettivo' derivata dai traits."""
    traits = entities.get_npc_traits(conn, npc.id)
    parts = []
    if npc.archetype:
        parts.append(npc.archetype)
    if traits:
        parts.append(npc_gen.dominant_descriptor(traits))
    return ", ".join(parts)


def _danger_tag(level: int) -> str:
    return f"[pericolo {level}]"


def render_location(conn: sqlite3.Connection, player: entities.Player) -> str:
    loc = entities.get_location(conn, player.location_id)
    if loc is None:
        return "Sei nel vuoto. (location mancante)"
    lines = [f"You are in: {loc.name} {_danger_tag(loc.danger_level)}"]
    if loc.description:
        lines.append(loc.description)
    owner = entities.location_owner_name(conn, loc.id)
    if owner:
        lines.append(f"Controllata da: {owner}")

    npcs = entities.npcs_in_location(conn, loc.id)
    if npcs:
        lines.append("You see:")
        for n in npcs:
            tag = _npc_tag(conn, n)
            suffix = f" ({tag})" if tag else ""
            lines.append(f"  - {n.name}{suffix}")

    exits = entities.get_exits(conn, loc.id)
    lines.append("Exits: " + (", ".join(sorted(exits.keys())) if exits else "none"))
    corpses = entities.dead_npcs_in_location(conn, loc.id)
    if corpses:
        lines.append("Resti a terra: " + ", ".join(c.name for c in corpses))
    from engine.systems import sects
    hq = sects.sect_at_location(conn, loc.id)
    if hq:
        lines.append(f"Qui ha sede la setta {hq['name']} — puoi 'join' per il test d'ingresso.")
    return "\n".join(lines)


def _format_observations(obs: list[str]) -> str:
    if not obs:
        return ""
    return "\n".join("  · " + o for o in obs)


def cmd_move(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    direction = DIRECTIONS.get(arg.lower())
    if direction is None:
        return f"Direzione non valida: '{arg}'. Usa north/south/east/west."
    exits = entities.get_exits(conn, player.location_id)
    if direction not in exits:
        return f"Non puoi andare a {direction} da qui."
    entities.move_player(conn, player.id, exits[direction])
    # il mondo simula durante lo spostamento (scope attivo intorno alla NUOVA posizione)
    obs = world_tick.advance(conn, tick.cost_of("move"))
    new_tick = tick.get_tick(conn)
    moved = entities.get_player(conn, player.id)
    out = f"Tick {new_tick}\n" + render_location(conn, moved)
    if obs:
        out += "\nNel frattempo:\n" + _format_observations(obs)
    return out


def cmd_wait(conn: sqlite3.Connection, player: entities.Player) -> str:
    obs = world_tick.advance(conn, tick.cost_of("short_rest"))
    new_tick = tick.get_tick(conn)
    out = f"Tick {new_tick} — attendi e osservi."
    if obs:
        out += "\n" + _format_observations(obs)
    else:
        out += "\n  (nulla di evidente accade intorno a te)"
    return out + "\n" + render_location(conn, entities.get_player(conn, player.id))


def cmd_look(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    if not arg:
        return render_location(conn, player)
    direction = DIRECTIONS.get(arg.lower())
    if direction is None:
        return f"Direzione non valida: '{arg}'."
    for ex in entities.get_exits_detailed(conn, player.location_id):
        if ex["direction"] == direction:
            return (f"A {direction} vedi: {ex['dest_name']} "
                    f"{_danger_tag(ex['danger'])}")
    return f"Non c'è nulla a {direction} da qui."


def cmd_map(conn: sqlite3.Connection, player: entities.Player) -> str:
    loc = entities.get_location(conn, player.location_id)
    exits = entities.get_exits_detailed(conn, player.location_id)
    if not exits:
        return f"{loc.name}: nessuna uscita."
    lines = [f"{loc.name} {_danger_tag(loc.danger_level)}", "Uscite:"]
    for ex in exits:
        lines.append(f"  {ex['direction']:>5} → {ex['dest_name']} {_danger_tag(ex['danger'])}")
    return "\n".join(lines)


def cmd_examine(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    if not arg:
        return "Esamina chi? Usa: examine <nome>"
    npc = entities.find_npc_in_location(conn, player.location_id, arg)
    if npc is None:
        return f"Non vedi nessuno di nome '{arg}' qui."
    traits = entities.get_npc_traits(conn, npc.id)
    disp = relations.get_disposition(conn, npc.id)
    lines = [f"{npc.name} — {npc.archetype or 'sconosciuto'}"]
    from engine.systems import bounties
    ol = bounties.get_outlaw(conn, npc.id)
    if ol:
        lines.append(f"⚠ RICERCATO: {ol['crime']}. Taglia: {ol['reward']} pietre.")
    realm = cultivation.realm_label(conn, "npc", npc.id)
    lines.append(f"Coltivazione: {realm}")
    faction = conn.execute(
        "SELECT f.name FROM npcs n JOIN factions f ON f.id=n.faction_id WHERE n.id=?;",
        (npc.id,),
    ).fetchone()
    if faction:
        lines.append(f"Affiliazione: {faction['name']}")
    if npc.description:
        lines.append(npc.description)
    if traits:
        ordered = sorted(traits.items(), key=lambda kv: abs(kv[1] - 50), reverse=True)
        shown = ", ".join(f"{k} {v}" for k, v in ordered)
        lines.append(f"Indole: {shown}")
    lines.append(f"Rapporto verso di te: {disp.relationship_type} ({disp.score:+d})")
    return "\n".join(lines)


def cmd_greet(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    if not arg:
        return "Saluta chi? Usa: greet <nome>"
    npc = entities.find_npc_in_location(conn, player.location_id, arg)
    if npc is None:
        return f"Non vedi nessuno di nome '{arg}' qui."
    t = tick.get_tick(conn)
    before = relations.get_disposition(conn, npc.id)
    # primo contatto vale di più; saluti successivi danno rendimenti decrescenti
    delta = 10 if before.relationship_type == "stranger" else 2
    after = relations.adjust(conn, npc.id, delta, t)
    if before.relationship_type == "stranger":
        return f"Ti presenti a {npc.name}. Ora siete {after.relationship_type}. ({after.score:+d})"
    return f"Scambi qualche parola con {npc.name}. Rapporto: {after.relationship_type} ({after.score:+d})"


def cmd_factions(conn: sqlite3.Connection) -> str:
    facs = entities.list_factions(conn)
    if not facs:
        return "Non esistono fazioni in questo mondo."
    lines = ["Fazioni (per influenza):"]
    for f in facs:
        lines.append(f"  {f['name']} — infl {f['influence']}, "
                     f"territori {f['territories']}, leader {f['leader'] or '—'}")
    return "\n".join(lines)


def cmd_faction(conn: sqlite3.Connection, arg: str) -> str:
    if not arg:
        return "Quale fazione? Usa: faction <nome>"
    d = entities.faction_detail(conn, arg)
    if d is None:
        return f"Nessuna fazione corrisponde a '{arg}'."
    lines = [f"{d['name']}",
             f"  Influenza: {d['influence']} | Ricchezza: {d['wealth']}",
             f"  Leader: {d['leader'] or '—'}",
             f"  Obiettivi: {d['goals']}",
             f"  Territori ({len(d['territories'])}): " +
             (", ".join(d['territories']) if d['territories'] else "nessuno")]
    if d["relations"]:
        lines.append("  Relazioni:")
        for other, rtype, score in d["relations"]:
            lines.append(f"    {other}: {rtype} ({score:+d})")
    return "\n".join(lines)


def cmd_log(conn: sqlite3.Connection, arg: str) -> str:
    try:
        n = max(1, min(20, int(arg))) if arg else 8
    except ValueError:
        n = 8
    events = entities.recent_events(conn, n, only_public=True)
    if not events:
        return "Non hai notizie di eventi degni di nota."
    lines = ["Cronache recenti (ciò che è giunto alle tue orecchie):"]
    for e in events:
        lines.append(f"  [tick {e['tick']:>4}] {e['summary']}")
    return "\n".join(lines)


def cmd_attack(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    if not arg:
        return "Attaccare chi? Usa: attack <nome>"
    npc = entities.find_npc_in_location(conn, player.location_id, arg)
    if npc is None:
        return f"Non vedi nessuno di nome '{arg}' qui."
    t = tick.get_tick(conn)
    rng = random.Random(t * 7919 + player.id + npc.id)
    obs: list[str] = []
    res = combat.resolve_combat(
        conn, t, rng,
        ("player", player.id, "Tu"), ("npc", npc.id, npc.name),
        player.location_id, player.location_id, obs,
    )
    # il tempo avanza un poco intorno allo scontro
    world_tick.advance(conn, 1)

    winner_is_player = res["winner"][0] == "player"
    lines = []
    if res["died"] and not winner_is_player:
        lines.append(f"Affronti {npc.name}... e cadi. ({res['rounds']} round)")
    elif res["died"] and winner_is_player:
        lines.append(f"Affronti {npc.name} e lo uccidi. ({res['rounds']} round)")
        from engine.systems import bounties
        if bounties.get_outlaw(conn, npc.id):
            claim = bounties.claim(conn, t, npc.id, player.id)
            if claim["status"] == "claimed":
                lines.append(f"Era un ricercato: hai fatto giustizia. Taglia riscossa: "
                             f"+{claim['reward']} pietre spirituali.")
        if absorb_hint := _absorb_hint(conn, player):
            lines.append(absorb_hint)
    elif winner_is_player:
        lines.append(f"Affronti {npc.name} e lo sopraffai: è ferito. ({res['rounds']} round)")
    else:
        lines.append(f"Affronti {npc.name} ma hai la peggio: sei ferito. ({res['rounds']} round)")
    return "\n".join(lines)


def _absorb_hint(conn, player) -> str | None:
    from engine.systems import absorption
    if absorption.can_absorb(conn, player.id):
        return "Puoi 'absorb' i suoi resti per divorarne l'eredità (ma l'anima si macchia)."
    return None


def cmd_cultivate(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import training
    t = tick.get_tick(conn)
    rng = random.Random(t * 31 + player.id)
    n = training.record_session(conn, t, "player", player.id)
    y = training.session_yield(n)
    bonus = training.location_bonus(conn, player.id, player.location_id)
    res = cultivation.cultivate(conn, "player", player.id, t, rng,
                                multiplier=y * (1 + bonus))
    world_tick.advance(conn, tick.cost_of("cultivate"))
    label = cultivation.realm_label(conn, "player", player.id)
    line = f"Mediti a lungo. {label} — esperienza {res['progress']*100:.0f}%."
    if res.get("stage_up"):
        line += f"\nAvanzi allo Strato {res['stage']}: il tuo corpo si rafforza."
    line += f"\nAllenamento {n}° della giornata (rendimento {training.yield_label(y)})."
    if bonus:
        line += " Le formazioni della tua setta amplificano il qi."
    if y <= 0.15:
        line += "\nSei sfinito: conviene riposare ('wait') o dedicarti ad altro."
    if res["ready"]:
        line += "\nSei al colmo dello Strato 10: prova 'breakthrough' per salire di regno (rischioso!)."
    return line


def cmd_breakthrough(conn: sqlite3.Connection, player: entities.Player) -> str:
    t = tick.get_tick(conn)
    rng = random.Random(t * 131 + player.id)
    res = cultivation.attempt_breakthrough(conn, "player", player.id, t, rng,
                                           observer=player.location_id, observations=[])
    world_tick.advance(conn, 1)
    status = res["status"]
    if status == "not_ready":
        return "Non sei ancora pronto. Continua a coltivare."
    if status == "peak":
        return "Hai già raggiunto la vetta: Immortale di Giada."
    if status == "success":
        from engine.systems import sects, sect_life
        extra = ""
        if sects.get_membership(conn, player.id):
            rng2 = random.Random(t * 91 + player.id)
            sect_life.promote_class(conn, t, rng2, player.id)
            ag = sect_life.agenda_line(conn, t, player.id)
            extra = f"\nLa setta ti promuove alla classe successiva. {ag or ''}"
        return f"Il tuo regno si squarcia e si ricompone: ora sei {res['realm']}!{extra}"
    if status == "failure":
        return "Il breakthrough fallisce. Subisci un contraccolpo e perdi terreno."
    if status == "death":
        return "Il qi si ribella nei tuoi meridiani... il tuo corpo cede."
    return "Nulla accade."


def cmd_narrate(conn: sqlite3.Connection, player: entities.Player) -> str:
    t = tick.get_tick(conn)
    return narrator.render_scene(conn, player, t)


def cmd_chronicle(conn: sqlite3.Connection) -> str:
    t = tick.get_tick(conn)
    return narrator.render_chronicle(conn, t)


def cmd_memories(conn: sqlite3.Connection, player: entities.Player) -> str:
    t = tick.get_tick(conn)
    mems = memory.active_memory(conn, "player", player.id, t)
    if not mems:
        return "Non porti ancora ricordi degni di nota."
    lines = ["Ciò che porti con te (memoria attiva):"]
    for m in mems:
        age = "ora" if m.age <= memory.SHORT_TERM_WINDOW else f"{m.age} tick fa"
        lines.append(f"  · {m.summary} ({age})")
    return "\n".join(lines)


def cmd_absorb(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import absorption
    if not absorption.can_absorb(conn, player.id):
        return "Non possiedi l'Abisso Divoratore: non puoi assorbire nessuno."
    if not arg:
        return "Assorbire chi? Usa: absorb <nome> (su resti a terra)"
    npc = entities.find_dead_npc_in_location(conn, player.location_id, arg)
    if npc is None:
        return f"Non vedi i resti di '{arg}' qui."
    t = tick.get_tick(conn)
    rng = random.Random(t * 2999 + player.id + npc.id)
    res = absorption.absorb(conn, t, rng, npc.id, player.id)
    s = res["status"]
    if s == "comprehension":
        return (f"Divori l'eredità di {npc.name}. Un frammento del Dao risuona in te "
                f"(comprensione di '{res['dao']}' +{res['gain']}).")
    if s == "trauma":
        return f"Divori {npc.name}, ma l'eredità ti contamina: echi non tuoi ti attraversano."
    if s == "shattered":
        return f"L'eredità di {npc.name} è troppo vasta: la tua anima si frantuma..."
    return "Nulla da assorbire."


def cmd_sects(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    rows = sects.joinable_sects(conn)
    if not rows:
        return "Non si conoscono sette in questo mondo."
    m = sects.get_membership(conn, player.id)
    lines = ["Sette conosciute (vai alla sede e usa 'join'):"]
    for r in rows:
        here = " ← sei qui" if r["home_location_id"] == player.location_id else ""
        mine = " [la tua setta]" if m and m["faction_id"] == r["id"] else ""
        lines.append(f"  · {r['name']} — sede: {r['hq_name']}{here}{mine}")
    if m:
        lines.append(f"\nSei {m['rank']} di {m['sect_name']} ({m['grade']}).")
    return "\n".join(lines)


def cmd_join(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    t = tick.get_tick(conn)
    res = sects.join_sect(conn, t, player.id)
    s = res["status"]
    if s == "no_sect_here":
        return "Qui non c'è la sede di alcuna setta. Usa 'sects' per sapere dove andare."
    if s == "already_member":
        return f"Sei già membro di {res['sect']}. Usa 'leave' per andartene."
    if s == "joined":
        from engine.systems import sect_life
        rng = random.Random(t * 17 + player.id)
        setup = sect_life.setup_class(conn, t, rng, player.id)
        agenda = sect_life.agenda_line(conn, t, player.id)
        mates = sect_life.classmates(conn, player.id)
        mate_names = ", ".join(m["name"] for m in mates)
        return (f"Ti presenti alla sede di {res['sect']}. Misurano le tue radici spirituali: "
                f"{res['grade']}.\nSei ammesso come {res['rank']}. "
                f"Ricevi {res['stones']} pietre spirituali.\n"
                f"I tuoi compagni di classe: {mate_names}.\n"
                f"Annuncio: {agenda} Allenati: la classifica deciderà chi conta.")
    return "Nulla accade."


def cmd_leave(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    res = sects.leave_sect(conn, player.id)
    if res["status"] == "not_member":
        return "Non appartieni ad alcuna setta."
    return f"Lasci {res['sect']}. Sei di nuovo un coltivatore errante."


def cmd_bounties(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import bounties
    bounties.replenish(conn, random.Random(tick.get_tick(conn) + 1))
    rows = bounties.active_bounties(conn)
    if not rows:
        return "Al momento nessuna taglia. La pace regna... per ora."
    lines = ["Ricercati (sconfiggili per riscuotere la taglia):"]
    for r in rows:
        where = f" — a {r['loc_name']}" if r["loc_name"] else ""
        lines.append(f"  · {r['name']}{where}: {r['crime']}. Taglia: {r['reward']} pietre.")
    lines.append("Giustiziarli è un atto giusto (karma). Divorarli dà potere, ma corrompe.")
    return "\n".join(lines)


def cmd_dao(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import dao_training
    rows = dao_training.trainable_daos(conn, player.id)
    if not rows:
        return "Non pratichi ancora alcun Dao."
    lines = ["I tuoi Dao (usa 'comprehend <nome>' per affinarli):"]
    for r in rows:
        tag = " [combattimento]" if r["dao_key"] in dao_training.COMBAT_DAOS else ""
        lines.append(f"  · {r['name']} — {dao_training.comprehension_label(r['comprehension'])}{tag}")
    # eventuali Dao latenti non ancora risvegliati
    latent = conn.execute(
        "SELECT d.name FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type='player' AND cd.character_id=? "
        "AND cd.practiced=0 AND cd.comprehension=0;", (player.id,)).fetchall()
    if latent:
        lines.append("Affinità latenti (risvegliabili assorbendo): "
                     + ", ".join(l["name"] for l in latent))
    return "\n".join(lines)


def cmd_comprehend(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import dao_training, training
    if not arg:
        return "Affinare quale Dao? Usa: comprehend <nome> (vedi 'dao')."
    d = dao_training.find_dao(conn, arg, player.id)
    if d is None:
        return f"Non conosci un Dao simile a '{arg}'. Usa 'dao' per la lista."
    t = tick.get_tick(conn)
    n = training.record_session(conn, t, "player", player.id)
    y = training.session_yield(n)
    rng = random.Random(t * 53 + player.id)
    res = dao_training.comprehend(conn, t, rng, d["dao_key"], multiplier=y, player_id=player.id)
    world_tick.advance(conn, tick.cost_of("cultivate"))
    if res["status"] == "locked":
        return f"Il {d['name']} è solo un'affinità latente: devi prima risvegliarlo (assorbendo)."
    if res["status"] == "maxed":
        return f"La tua comprensione del {d['name']} è già sublime (al colmo)."
    name = d["name"]
    if res["status"] in ("exhausted",):
        return (f"Mediti sul {name}, ma sei troppo sfinito per progredire oggi "
                f"(allenamento {n}°). Riposa ('wait').")
    line = (f"Affini il {name}: comprensione ora {dao_training.comprehension_label(res['comprehension'])}.")
    line += f"\nAllenamento {n}° della giornata (rendimento {training.yield_label(y)})."
    if res.get("combat"):
        line += " Senti il tuo potere in battaglia crescere."
    if y <= 0.15:
        line += "\nSei sfinito: conviene riposare ('wait') o dedicarti ad altro."
    return line


def cmd_class(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects, sect_life
    m = sects.get_membership(conn, player.id)
    if not m:
        return "Non appartieni ad alcuna setta. Usa 'sects' per trovarne una."
    t = tick.get_tick(conn)
    lines = [f"Setta: {m['sect_name']} — {m['rank']}"]
    if m["class_rank"]:
        lines.append(f"Posizione attuale in classifica: {m['class_rank']}°")
    mates = sect_life.classmates(conn, player.id)
    if mates:
        lines.append("Compagni di classe (rivali): " + ", ".join(m2["name"] for m2 in mates))
    ag = sect_life.agenda_line(conn, t, player.id)
    if ag:
        lines.append("Prossimo evento — " + ag)
    return "\n".join(lines)


def cmd_profile(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import character as ch, absorption
    from engine.generators import dao_gen
    t = tick.get_tick(conn)
    lines = [ch.describe_profile(conn, t, player.id)]
    prof = ch.get_profile(conn, "player", player.id)
    if prof and prof["anomaly"]:
        lines.append(f"Anomalia: {prof['anomaly'].replace('_', ' ').title()}.")
        lines.append(f"Stato dell'anima: {absorption.residue_label(prof['soul_residue'])}.")
    daos = dao_gen.list_character_daos(conn, "player", player.id)
    if daos:
        prat = [d for d in daos if d["practiced"]]
        lat = [d for d in daos if not d["practiced"]]
        if prat:
            lines.append("Dao praticati: " + ", ".join(
                f"{d['name']} ({_comp_label(d['comprehension'])})" for d in prat))
        if lat:
            lines.append("Affinità latenti: " + ", ".join(d["name"] for d in lat))
    from engine.systems import karma
    hint = karma.karma_hint(karma.get_karma(conn, "player", player.id))
    if hint:
        lines.append(hint)
    return "\n".join(lines)


def _comp_label(c: int) -> str:
    if c == 0:
        return "appena intuito"
    if c < 20:
        return "principiante"
    if c < 45:
        return "discreto"
    if c < 70:
        return "esperto"
    if c < 90:
        return "maestro"
    return "sublime"


def cmd_status(conn: sqlite3.Connection, player: entities.Player) -> str:
    t = tick.get_tick(conn)
    loc = entities.get_location(conn, player.location_id)
    wounds = combat.active_injuries(conn, "player", player.id)
    wound_line = ("Ferite: " + ", ".join(f"{w['description']} (gravità {w['severity']})"
                                         for w in wounds)) if wounds else "Ferite: nessuna"
    realm = cultivation.realm_label(conn, "player", player.id)
    rec = cultivation.get_record(conn, "player", player.id)
    prog = f"{rec['progress']*100:.0f}%" if rec else "—"
    prof = character.get_profile(conn, "player", player.id)
    origin_line = ""
    if prof:
        from engine.systems.character import ORIGINS, YEAR_TICKS
        oname = ORIGINS.get(prof["origin"], {}).get("name", prof["origin"])
        age = (prof["age"] or 16) + t // YEAR_TICKS
        origin_line = f"Origine: {oname} | Età: {age}\n"
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    sect_line = (f"Setta: {m['rank']} di {m['sect_name']}\n") if m else ""
    if m:
        from engine.systems import sect_life
        ag = sect_life.agenda_line(conn, t, player.id)
        if ag:
            sect_line += f"Prossimo evento di setta — {ag}\n"
    stones = sects.get_resource(conn, "pietre_spirituali", player.id)
    res_line = f"Pietre spirituali: {stones}\n" if (m or stones) else ""
    return (
        f"Name: {player.name}\n"
        f"{origin_line}"
        f"{sect_line}"
        f"{res_line}"
        f"Status: {player.status}\n"
        f"Coltivazione: {realm} (esperienza {prog})\n"
        f"Location: {loc.name if loc else '?'}\n"
        f"{wound_line}\n"
        f"Tick: {t}"
    )


def cmd_where(conn: sqlite3.Connection, player: entities.Player) -> str:
    loc = entities.get_location(conn, player.location_id)
    if loc is None:
        return "Posizione sconosciuta."
    return f"{loc.name} {_danger_tag(loc.danger_level)} — {loc.location_type}"


def dispatch(conn: sqlite3.Connection, raw: str, allow_nl: bool = True) -> str | None:
    parts = raw.strip().split(maxsplit=1)
    if not parts:
        return ""
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    player = entities.get_player(conn)
    if player is None:
        return "Nessun giocatore trovato. DB non generato?"

    if cmd in ("quit", "exit"):
        return None
    if cmd == "help":
        return HELP
    if cmd == "look":
        return cmd_look(conn, player, arg)
    if cmd == "examine":
        return cmd_examine(conn, player, arg)
    if cmd == "greet":
        return cmd_greet(conn, player, arg)
    if cmd == "attack":
        return cmd_attack(conn, player, arg)
    if cmd in ("absorb", "devour", "divora"):
        return cmd_absorb(conn, player, arg)
    if cmd == "map":
        return cmd_map(conn, player)
    if cmd == "where":
        return cmd_where(conn, player)
    if cmd == "factions":
        return cmd_factions(conn)
    if cmd == "faction":
        return cmd_faction(conn, arg)
    if cmd in ("sects", "sette"):
        return cmd_sects(conn, player)
    if cmd in ("join", "iscriviti"):
        return cmd_join(conn, player)
    if cmd in ("leave", "lascia"):
        return cmd_leave(conn, player)
    if cmd in ("class", "classe", "agenda"):
        return cmd_class(conn, player)
    if cmd in ("dao", "daos"):
        return cmd_dao(conn, player)
    if cmd in ("bounties", "missions", "taglie", "missioni"):
        return cmd_bounties(conn, player)
    if cmd in ("comprehend", "affina", "studia"):
        return cmd_comprehend(conn, player, arg)
    if cmd in ("log", "news"):
        return cmd_log(conn, arg)
    if cmd in ("memories", "recall"):
        return cmd_memories(conn, player)
    if cmd in ("narrate", "scene", "story"):
        return cmd_narrate(conn, player)
    if cmd in ("chronicle", "tale"):
        return cmd_chronicle(conn)
    if cmd == "status":
        return cmd_status(conn, player)
    if cmd in ("profilo", "profile", "background"):
        return cmd_profile(conn, player)
    if cmd == "move":
        return cmd_move(conn, player, arg)
    if cmd in ("wait", "rest"):
        return cmd_wait(conn, player)
    if cmd in ("cultivate", "meditate"):
        return cmd_cultivate(conn, player)
    if cmd == "breakthrough":
        return cmd_breakthrough(conn, player)

    # fallback in linguaggio naturale: traduci la frase in un comando (solo se Ollama attivo)
    if allow_nl:
        from engine.cli import intent
        translated = intent.translate(conn, player, raw)
        if translated:
            result = dispatch(conn, translated, allow_nl=False)
            if result is None:
                return None
            return f"(interpreto: {translated})\n" + (result or "")
    return f"Comando sconosciuto: '{cmd}'. Scrivi 'help'."


def run() -> None:
    with transaction() as conn:
        t = tick.get_tick(conn)
        player = entities.get_player(conn)
        print(f"Tick {t}")
        print(render_location(conn, player))
        print("(scrivi 'help' per i comandi)")

    while True:
        try:
            raw = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nA presto, coltivatore.")
            return
        with transaction() as conn:
            output = dispatch(conn, raw)
        if output is None:
            print("A presto, coltivatore.")
            return
        if output:
            print(output)
        # il mondo può averti ucciso (scontro o minaccia autonoma)
        with transaction() as conn:
            p = entities.get_player(conn)
        if p is None or p.status != "alive":
            print("\nLe tue ferite hanno avuto la meglio. Il mondo prosegue senza di te.")
            print("(fine partita)")
            return
