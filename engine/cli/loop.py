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
  sleep                         — dormi fino all'alba del giorno seguente
  cultivate (o 'c')             — mediti per accumulare progresso nel tuo regno
  dao                           — i Dao che pratichi e la loro comprensione
  comprehend <nome>             — affini un Dao (i Dao da combattimento ti rendono più forte)
  breakthrough                  — tenti di salire di regno (può fallire o ucciderti!)
  look                          — osservi la location corrente
  look <dir>                    — sbirci la location adiacente in quella direzione
  examine <nome>                — esamini un NPC presente (archetipo, indole, rapporto)
  greet <nome>                  — saluti un NPC: prima conoscenza / migliora il rapporto
  attack <nome> [mossa]         — attacchi un NPC (puoi morire!); mossa attiva opzionale
  attack all                    — attacchi tutte le creature selvagge presenti, in sequenza
  moves                         — le tue mosse attive in combattimento (cooldown)
  absorb <nome>                 — (Abisso Divoratore) divori i resti di un caduto
  absorb all                    — divori in sequenza tutti i resti presenti
  loot                          — raccogli l'eredità dei caduti (le armi della TUA via si equipaggiano da sé)
  inventory                     — il tuo zaino (oggetti raccolti)
  use <oggetto>                 — usi un oggetto dello zaino (pillole, essenze, manuali, nuclei)
  war                           — guerra tra sette in corso: fronte, punteggio, tempo
  spare <nome>                  — al fronte: sottometti e risparmia un nemico (onore)
  home                          — torni direttamente alla sede della tua setta
  rating                        — il tuo profilo di potenza (Qi/Corpo/Anima/Dao), classe e zona
  map                           — uscite della location corrente con destinazioni
  factions                      — elenco delle fazioni (influenza, territori)
  faction <nome>                — dettaglio di una fazione (territori, relazioni)
  sects                         — sette a cui iscriversi e dove hanno sede
  bounties                      — ricercati da cacciare (taglie e missioni)
  events                        — invasioni mondiali in corso (difendi un luogo)
  defend                        — difendi il luogo invaso (abbatti l'ondata)
  hunt <nome>                   — localizza un ricercato e ti indica dove andare
  join                          — test d'ingresso e iscrizione alla setta locale
  class                         — compagni di classe, classifica, prossima sfida/torneo
  invitations                   — inviti delle sette superiori (dopo aver vinto un torneo)
  accept <n>                    — accetti un invito e ascendi a una setta superiore
  huntzone                      — la zona di caccia della tua setta (mostri = merito)
  weapon <arma>                 — scegli l'arma principale (sblocca il Dao d'arma)
  techniques                    — tecniche segrete della setta e merito disponibile
  learn <n>                     — impari una tecnica segreta spendendo merito
  leave                         — lascia la tua setta
  log [n]                       — cronache recenti note al giocatore
  memories                      — ciò che il tuo personaggio ricorda (memoria attiva)
  narrate                       — rendi la scena attuale come prosa (LLM o fallback)
  chronicle                     — un breve passo di cronaca del mondo
  status                        — il tuo stato e il tick globale
  reputation                    — fama, infamia, allineamento percepito, sospetto
  mask <on|off>                 — indossi/togli la maschera (agisci in incognito)
  profilo                       — origine, età e affinità (descrizione qualitativa)
  where                         — nome e pericolo della location corrente
  help                          — questo messaggio (anche 'h')
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
    from engine.systems import world_events
    wev = world_events.active_event(conn)
    if wev and wev["location_id"] == loc.id:
        rem = conn.execute("SELECT COUNT(*) c FROM npcs WHERE event_id=? AND status='alive';",
                           (wev["id"],)).fetchone()["c"]
        lines.append(f"⚠ INVASIONE IN CORSO: {world_events.KIND_LABEL[wev['kind']]} "
                     f"({rem} creature). Usa 'defend' per respingerla!")

    npcs = entities.npcs_in_location(conn, loc.id)
    if npcs:
        lines.append("You see:")
        for n in npcs:
            tag = _npc_tag(conn, n)
            suffix = f" ({tag})" if tag else ""
            lines.append(f"  - {n.name}{suffix}")

    hunters_here = conn.execute(
        "SELECT name FROM npcs WHERE location_id=? AND hunting=1 AND status='alive' ORDER BY id;",
        (loc.id,)).fetchall()
    if hunters_here:
        who = ", ".join(h["name"] for h in hunters_here)
        lines.append(f"⚠ CACCIATORE DELL'ERETICO qui: {who}! Affrontalo ('attack <nome>') "
                     f"oppure fuggi ('mask on' e spostati per seminarlo).")

    from engine.systems import sect_war as _sw
    _war = _sw.active_war(conn)
    if _war and _war["battle_location_id"] == loc.id:
        en = _sw.enemy_disciples(conn, _war)
        fallen = conn.execute(
            "SELECT name FROM npcs WHERE war_id=? AND status='dead' ORDER BY id;",
            (_war["id"],)).fetchall()
        lines.append("⚔ FRONTE DI GUERRA TRA SETTE.")
        if en:
            lines.append("  Discepoli nemici: " + ", ".join(e["name"] for e in en))
            lines.append("  Per ognuno: 'attack <nome>' (uccidi), 'spare <nome>' (risparmia), "
                         "'absorb <nome>' sui caduti.")
        if fallen:
            lines.append("  Resti sul campo (anche tuoi compagni): "
                         + ", ".join(f["name"] for f in fallen) + ". 'war' per i dettagli.")

    # creature selvatiche: chiarisci che si cacciano e come (merito nella zona di setta)
    creatures = conn.execute(
        "SELECT name FROM npcs WHERE location_id=? AND status='alive' AND kind<>'human' "
        "AND kind IS NOT NULL ORDER BY id;", (loc.id,)).fetchall()
    if creatures:
        names = ", ".join(c["name"] for c in creatures)
        hz = conn.execute(
            "SELECT 1 FROM factions f JOIN sect_memberships sm ON sm.faction_id=f.id "
            "WHERE sm.player_id=? AND f.hunt_zone_id=?;", (player.id, loc.id)).fetchone()
        zone_note = (" — è la ZONA DI CACCIA della tua setta: abbatterle dà merito!"
                     if hz else "")
        lines.append(f"Creature selvatiche qui: {names}. Usa 'attack <nome>' per cacciarle"
                     f"{zone_note}")

    exits = entities.get_exits(conn, loc.id)
    lines.append("Exits: " + (", ".join(sorted(exits.keys())) if exits else "none"))
    corpses = entities.dead_npcs_in_location(conn, loc.id)
    if corpses:
        lines.append("Resti a terra: " + ", ".join(c.name for c in corpses))
    from engine.systems import loot as _loot
    _drops = _loot.drops_in_location(conn, loc.id)
    if _drops:
        lines.append("⚑ Bottino sul terreno: " + ", ".join(d["name"] for d in _drops)
                     + ". Usa 'loot' per raccoglierlo.")

    # Consapevolezza dei testimoni: ti permette di SCEGLIERE prima di agire.
    # (mostrata quando c'è gente o resti a terra: è allora che la cosa conta.)
    from engine.systems import reputation
    if npcs or corpses:
        watchers = reputation.witnesses(conn, loc.id)
        if reputation.is_disguised(conn, player.id):
            lines.append("Sei in incognito: i presenti non riconoscono il tuo volto.")
        elif watchers:
            names = ", ".join(w["name"] for w in watchers)
            lines.append(f"Occhi su di te — testimoni: {names}. "
                         f"Qui le azioni losche (uccidere innocenti, divorare resti) "
                         f"verrebbero notate. ('mask on' per agire in incognito.)")
        else:
            lines.append("Nessun testimone nei paraggi: puoi agire senza essere visto.")

    from engine.systems import sects
    hq = sects.sect_at_location(conn, loc.id)
    if hq:
        m = sects.get_membership(conn, player.id)
        if m and m["faction_id"] == hq["id"]:
            lines.append(f"Qui ha sede la tua setta, {hq['name']}.")
        elif m:
            lines.append(f"Qui ha sede la setta {hq['name']}.")
        else:
            lines.append(f"Qui ha sede la setta {hq['name']} — puoi 'join' per il test d'ingresso.")
    from engine.systems import zones
    _z = zones.zone_of(conn, loc.id)
    if _z:
        if _z["populated_tick"] < 0:
            now = tick.get_tick(conn)
            zones.populate_zone(conn, random.Random(loc.id * 131 + now), loc.id, now)
        lines.append(zones.describe(conn, loc.id))
    return "\n".join(lines)


def _danger_tag(level: int) -> str:
    word = {1: "tranquillo", 2: "incerto", 3: "rischioso",
            4: "pericoloso", 5: "letale"}.get(min(5, max(1, level)), "ignoto")
    return f"[pericolo {level}: {word}]"


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
    from engine.systems import qi as qimod
    qimod.restore_fraction(conn, 0.15, player.id)      # camminare recupera un po' di Qi
    from engine.systems import spirit as spmod
    spmod.restore_fraction(conn, 0.15, player.id)
    new_tick = tick.get_tick(conn)
    moved = entities.get_player(conn, player.id)
    out = f"Tick {new_tick}\n" + render_location(conn, moved)
    if obs:
        out += "\nNel frattempo:\n" + _format_observations(obs)
    return out


def cmd_wait(conn: sqlite3.Connection, player: entities.Player) -> str:
    obs = world_tick.advance(conn, tick.cost_of("short_rest"))
    from engine.systems import qi as qimod
    qimod.restore_fraction(conn, 0.35, player.id)      # un po' di Qi recuperato
    from engine.systems import spirit as spmod
    spmod.restore_fraction(conn, 0.35, player.id)
    new_tick = tick.get_tick(conn)
    out = f"Tick {new_tick} — attendi e recuperi (Qi {qimod.qi_label(conn, player.id)})."
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
    from engine.systems import bounties, perception
    ol = bounties.get_outlaw(conn, npc.id)
    if ol:
        lines.append(f"⚠ RICERCATO: {ol['crime']}. Taglia: {ol['reward']} pietre.")
    # informazioni filtrate da notorietà + Dao dell'Anima
    lines += perception.describe(conn, player.id, npc)
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
    from engine.systems import reputation
    sf = reputation.social_factor(conn, player.id)
    # primo contatto vale di più; saluti successivi danno rendimenti decrescenti
    base = 10 if before.relationship_type == "stranger" else 2
    delta = max(0, int(round(base * sf)))
    after = relations.adjust(conn, npc.id, delta, t)
    fear = " Ti osserva con timore." if sf < 0.7 else ""
    if before.relationship_type == "stranger":
        return f"Ti presenti a {npc.name}. Ora siete {after.relationship_type}. ({after.score:+d}){fear}"
    return f"Scambi qualche parola con {npc.name}. Rapporto: {after.relationship_type} ({after.score:+d}){fear}"


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


def _after_player_kill(conn, t, rng, player, npc, move) -> list[str]:
    """Ricompense/conseguenze quando il giocatore uccide un bersaglio.
    Condiviso tra modalità automatica e a turni."""
    lines: list[str] = []
    from engine.systems import bounties
    was_outlaw = bounties.get_outlaw(conn, npc.id) is not None
    if was_outlaw:
        claim = bounties.claim(conn, t, npc.id, player.id)
        if claim["status"] == "claimed":
            lines.append(f"Era un ricercato: hai fatto giustizia. Taglia riscossa: "
                         f"+{claim['reward']} pietre spirituali.")
    rep_line = _kill_reputation(conn, player, npc, was_outlaw)
    if rep_line:
        lines.append(rep_line)
    from engine.systems import guild
    mk = guild.on_creature_kill(conn, npc.id, player.id)
    if mk["gained"]:
        zone = " (zona di caccia della tua setta!)" if mk.get("in_zone") else ""
        lines.append(f"Merito della setta +{mk['gained']}{zone}. Totale: {mk['merit']}.")
    from engine.systems import world_events
    ev_msg = world_events.on_creature_killed(conn, npc.id, t, player)
    if ev_msg:
        lines.append(ev_msg)
    from engine.systems import hunters
    h_msg = hunters.on_hunter_defeated(conn, npc.id, player)
    if h_msg:
        lines.append(h_msg)
    from engine.systems import sect_war
    w_msg = sect_war.on_enemy_defeated(conn, t, player, npc.id, "kill")
    if w_msg:
        lines.append(w_msg)
    if move and move["mods"].get("devour_on_kill"):
        dv = _devour_on_kill(conn, t, rng, player, npc)
        if dv:
            lines.append(dv)
    elif absorb_hint := _absorb_hint(conn, player):
        lines.append(absorb_hint)
    from engine.systems import loot
    lines += loot.on_player_kill(conn, t, rng, player, npc)
    return lines


def _parse_attack_arg(conn, player, arg):
    """Ritorna (npc, move) interpretando 'nome [mossa]'."""
    from engine.systems import moves
    move = None
    target = arg.strip()
    parts = target.split()
    if len(parts) >= 2:
        cand = moves.find_move(conn, parts[-1], player.id)
        if cand:
            move, target = cand, " ".join(parts[:-1])
    npc = entities.find_npc_in_location(conn, player.location_id, target)
    return npc, move, target


def cmd_attack(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    if not arg:
        return "Attaccare chi? Usa: attack <nome> [tecnica]  (oppure 'attack all' per le creature)"
    if arg.strip().lower() in ("all", "tutti", "tutto", "tutte"):
        return _attack_all(conn, player)
    npc, forced, target = _parse_attack_arg(conn, player, arg)
    if npc is None:
        return f"Non vedi nessuno di nome '{target}' qui."
    return _attack_auto(conn, player, npc, forced)


def _attack_all(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Attacca in sequenza tutte le CREATURE (bestie/demoni/spiriti) nel luogo."""
    rows = conn.execute(
        "SELECT id, name FROM npcs WHERE location_id=? AND status='alive' "
        "AND kind IN ('beast','demon','spirit') ORDER BY id;", (player.location_id,)).fetchall()
    if not rows:
        return "Non c'è nessuna creatura selvaggia da attaccare qui."
    out = [f"Ti scagli contro tutte le creature presenti ({len(rows)})!"]
    killed = 0
    for r in rows:
        p = entities.get_player(conn, player.id)
        if p.status != "alive":
            out.append("Cadi prima di finire: non puoi più combattere.")
            break
        npc = entities.get_npc(conn, r["id"])
        if npc is None:
            continue
        res = _attack_auto(conn, p, npc, None)
        last = [ln for ln in res.split("\n") if ln.strip()][-1]
        if "ucciso" in last or "★" in last:
            killed += 1
        out.append(f"  • {r['name']}: {last.strip()}")
    out.append(f"Creature abbattute: {killed}/{len(rows)}.")
    return "\n".join(out)


# ---------- COMBATTIMENTO AUTOMATICO con narrazione round-per-round ----------
# Il sistema decide a ogni scambio se tirare un attacco normale o una tecnica
# (spendendo Qi), e racconta le azioni di entrambi. La durata emerge dal divario
# di forza: forze simili -> scontro prolungato; divario enorme -> si chiude subito.

_NORMAL_VERBS = ("Sferri un colpo", "Affondi rapido", "Colpisci di netto",
                 "Attacchi deciso", "Cerchi un'apertura e colpisci")
_ENEMY_VERBS = ("risponde", "contrattacca", "ti colpisce di rimando",
                "reagisce con ferocia", "ti affonda un colpo")
_MAX_AUTO_ROUNDS = 14


def _player_normal_line(wlabel, rng) -> str:
    if wlabel:
        return rng.choice((f"Sferri un fendente di {wlabel.lower()}",
                           f"Colpisci con la tua {wlabel.lower()}",
                           f"Affondi con la {wlabel.lower()}")) + "."
    return rng.choice(_NORMAL_VERBS) + "."


def _hit_desc(dealt, emax, name, crit) -> str:
    r = dealt / emax if emax > 0 else 1.0
    if r < 0.08:
        base = f"{name} para quasi del tutto: appena scalfito."
    elif r < 0.20:
        base = f"{name} incassa il colpo."
    elif r < 0.45:
        base = f"Vai a segno: {name} barcolla."
    else:
        base = f"Un colpo potente squarcia le difese di {name}!"
    return ("Critico! " + base) if crit else base


def _enemy_line(name, edmg, pmax, crit, rng) -> str:
    verb = rng.choice(_ENEMY_VERBS)
    r = edmg / pmax if pmax > 0 else 1.0
    if r < 0.08:
        s = f"{name} {verb}, ma schivi quasi tutto."
    elif r < 0.20:
        s = f"{name} {verb} e ti graffia."
    elif r < 0.45:
        s = f"{name} {verb}: accusi il colpo."
    else:
        s = f"{name} {verb} con violenza: vacilli!"
    return (s + " (critico!)") if crit else s


def _state_desc(hp, mx) -> str:
    r = hp / mx if mx > 0 else 0.0
    if r > 0.75:
        return "illeso"
    if r > 0.45:
        return "ferito"
    if r > 0.20:
        return "malconcio"
    return "allo stremo"


def _use_prob(hp_e, emax) -> float:
    # più probabile usare una tecnica quando il nemico è ancora in forze
    return 0.15 + 0.5 * (hp_e / emax if emax > 0 else 0.0)


_DAO_TECH_VERBS = {
    "spada": ["L'intento della tua spada incrina l'aria", "La tua lama proietta uno squarcio netto"],
    "sciabola": ["La tua sciabola disegna mezzelune d'acciaio", "Un ventaglio di fendenti si abbatte"],
    "lancia": ["La tua lancia trafigge lo spazio", "Una stoccata d'intento perfora la guardia"],
    "arco": ["Il tuo intento scocca prima della freccia", "Strali di volontà piovono"],
    "pugno": ["Il tuo intento si condensa in un pugno di montagna", "Una pressione tellurica esplode dal tuo pugno"],
    "bastone": ["Il tuo bastone erige una guardia incrollabile", "Un pilastro d'intento devia e contrattacca"],
    "corpo": ["Il tuo corpo-Dao incassa e restituisce", "La tua carne diventa arma vivente"],
    "fulmine": ["L'intento del Fulmine ti incorona di scariche", "Una saetta della tua volontà incenerisce"],
    "tempo": ["Pieghi l'istante: ti muovi prima del tempo", "Un attimo rubato moltiplica i tuoi colpi"],
    "spazio": ["Annulli la distanza: sei già addosso", "Lo spazio si ripiega sotto il tuo intento"],
    "destino": ["Un filo del fato stringe il tuo nemico", "La tua sentenza pesa come una legge"],
    "anima": ["La tua pressione spirituale schiaccia", "Il tuo intento dell'anima invade la sua mente"],
}


def _dao_tech_line(move: dict, rng) -> str:
    verbs = _DAO_TECH_VERBS.get(move.get("main"), [f"Manifesti {move['name']}"])
    return f"{rng.choice(verbs)} — {move['name']}!"


# Stile di combattimento dei NEMICI per classe: meccanica + linguaggio propri.
_ENEMY_CLASS = {
    "dao":   {"pierce": 0.30, "intro": "Si muove con l'intento del Dao: ogni colpo è una lama affilata di volontà.",
              "verbs": ["proietta un intento tagliente", "libera una lama di pura volontà",
                        "incide l'aria con un Dao affilato"]},
    "corpo": {"dmg_mult": 1.15, "intro": "Il suo corpo è una fortezza vivente: avanza incurante.",
              "verbs": ["ti travolge come una montagna", "incassa e carica a corpo nudo",
                        "abbatte un pugno di ferro"]},
    "anima": {"intro": "La sua pressione spirituale grava sulla tua mente.",
              "verbs": ["preme sulla tua anima", "ti assale con un'onda spirituale",
                        "incrina la tua concentrazione con l'intento dell'anima"]},
    "qi":    {"crit": 0.10, "intro": "Incanala il Qi in tecniche spettacolari.",
              "verbs": ["scaglia un'onda di Qi", "libera una tecnica fragorosa",
                        "ti investe con un colpo di Qi condensato"]},
}


def _enemy_class_line(klass, name, edmg, pmax, crit, rng) -> str:
    prof = _ENEMY_CLASS.get(klass)
    if not prof:
        return _enemy_line(name, edmg, pmax, crit, rng)
    verb = rng.choice(prof["verbs"])
    r = edmg / pmax if pmax > 0 else 1.0
    if r < 0.08:
        s = f"{name} {verb}, ma reggi."
    elif r < 0.20:
        s = f"{name} {verb}: accusi appena."
    elif r < 0.45:
        s = f"{name} {verb}: il colpo morde."
    else:
        s = f"{name} {verb}: vacilli sotto la potenza!"
    return (s + " (critico!)") if crit else s


def _attack_auto(conn, player, npc, forced) -> str:
    from engine.systems import moves as mvmod, qi as qimod, weapons, perception, absorption, spirit as spmod
    t = tick.get_tick(conn)
    rng = random.Random(t * 7919 + player.id + npc.id)
    pa = combat.combat_power(conn, "player", player.id)
    pd = combat.combat_power(conn, "npc", npc.id)
    edge = perception.spirit_edge(conn, player.id, npc.id)   # 0..0.3
    dread = absorption.dread_level(conn, player.id)          # terrore abissale
    fear_mult = 1.0 - min(0.4, dread * 0.08)                 # i nemici colpiscono peggio
    # se il tuo spirito sovrasta enormemente il suo, resta PARALIZZATO dal terrore:
    # non riesce a reagire e sei libero di abbatterlo.
    paralyzed = perception.intimidates(conn, player.id, npc)
    from engine.systems import power
    pclass, nclass = power.class_of(conn, "player", player.id), power.class_of(conn, "npc", npc.id)
    style_bonus = power.matchup_bonus(pclass, nclass)
    wlabel = weapons.weapon_label(weapons.get_weapon(conn, player.id))
    hp_p, hp_e = pa["vitality"], pd["vitality"]
    pmax, emax = hp_p, hp_e

    lines = [(f"Impugni la tua {wlabel.lower()} e affronti {npc.name}."
              if wlabel else f"Affronti {npc.name}.")]
    if edge >= 0.1:
        lines.append("Il tuo spirito superiore anticipa le sue mosse: lo leggi come un libro aperto.")
    if dread >= 2:
        lines.append(f"La tua presenza abissale terrorizza {npc.name}: i suoi colpi esitano.")
    if paralyzed:
        lines.append(f"{npc.name} è paralizzato dal terrore di fronte al tuo spirito: "
                     f"non riesce a reagire, e sei libero di abbatterlo.")
    _note = power.matchup_note(pclass, nclass)
    if _note:
        lines.append(_note)
    _eprof = _ENEMY_CLASS.get(nclass)
    if _eprof and not paralyzed:
        lines.append(_eprof["intro"])
    pool = mvmod.available_moves(conn, player.id)
    local_cd: dict[str, int] = {}     # cooldown della tecnica entro lo scontro (in round)
    rounds = 0
    last_crit = False
    last_mods: dict = {}

    while hp_p > 0 and hp_e > 0 and rounds < _MAX_AUTO_ROUNDS:
        rounds += 1
        usable = [m for m in pool
                  if (spmod.can_afford(conn, m["spirit_cost"], player.id)
                      if m.get("fuel") == "spirit"
                      else qimod.can_afford(conn, m["qi_cost"], player.id))
                  and local_cd.get(m["key"], 0) <= rounds]
        # non sprecare tecniche se un colpo normale basterebbe ad atterrarlo
        normal_dmg = max(1.0, pa["attack"] - pd["defense"] * 0.5)
        quick_kill = hp_e <= normal_dmg * 1.2
        chosen = None
        if quick_kill:
            chosen = None
        elif forced and rounds == 1 and any(m["key"] == forced["key"] for m in usable):
            chosen = next(m for m in usable if m["key"] == forced["key"])
        elif usable and rng.random() < _use_prob(hp_e, emax):
            chosen = max(usable, key=lambda m: m["mods"].get("attack_mult", 1.0)
                         + (0.3 if m["mods"].get("extra_strikes") else 0.0))
        mods = {}
        if chosen:
            if chosen.get("fuel") == "spirit":
                spmod.spend(conn, chosen["spirit_cost"], player.id)
            else:
                qimod.spend(conn, chosen["qi_cost"], player.id)
            local_cd[chosen["key"]] = rounds + 3
            mods = chosen["mods"]
            strikes = 1 + int(mods.get("extra_strikes", 0))
            if chosen["source"] == "dao":
                lines.append(f"◈ {_dao_tech_line(chosen, rng)} "
                             f"(Spirito {spmod.get_spirit(conn, player.id)}/"
                             f"{spmod.max_spirit(conn, player.id)})")
            else:
                lines.append(f"⚔ Scateni {chosen['name']}! "
                             f"(Qi {qimod.get_qi(conn, player.id)}/{qimod.max_qi(conn, player.id)})")
        else:
            strikes = 1
            lines.append(_player_normal_line(wlabel, rng))
        last_mods = mods

        a_attack = pa["attack"] * mods.get("attack_mult", 1.0) * (1.0 + edge * 0.5) * (1.0 + style_bonus)
        d_def = pd["defense"] * (1.0 - mods.get("pierce", 0.0))
        dealt = 0.0
        crit_any = False
        for _ in range(strikes):
            dmg, crit = combat._strike(a_attack, d_def, rng)
            hp_e -= dmg
            dealt += dmg
            crit_any = crit_any or crit
            if hp_e <= 0:
                break
        lines.append("  " + _hit_desc(dealt, emax, npc.name, crit_any))
        last_crit = crit_any

        if hp_e <= 0:
            return _auto_end_enemy(conn, t, rng, player, npc, rounds, hp_p, pmax,
                                   crit_any, mods, chosen, lines)

        edef = pa["defense"] * (1.0 - (_eprof.get("pierce", 0.0) if _eprof else 0.0))
        edmg, ecrit = combat._strike(pd["attack"], edef, rng)
        if _eprof and _eprof.get("crit") and rng.random() < _eprof["crit"]:
            ecrit = True
            edmg *= 1.5
        edmg *= mods.get("taken_mult", 1.0) * (1.0 - edge) * fear_mult \
            * (_eprof.get("dmg_mult", 1.0) if _eprof else 1.0)
        if paralyzed:
            edmg = 0.0
        hp_p -= edmg
        if paralyzed:
            lines.append(f"  {npc.name}, pietrificato dal terrore, non oppone resistenza.")
        else:
            lines.append("  " + _enemy_class_line(nclass, npc.name, edmg, pmax, ecrit, rng))

        if hp_p <= 0:
            return _auto_end_player(conn, t, rng, player, npc, rounds, lines)

        if rounds in (4, 8, 12):
            lines.append(f"  ({npc.name}: {_state_desc(hp_e, emax)}; tu: {_state_desc(hp_p, pmax)})")

    # round massimi raggiunti: scontro lunghissimo, decide chi sta meglio
    world_tick.advance(conn, 1)
    if (hp_p / pmax) >= (hp_e / emax):
        lines.append(f"Dopo un lungo, estenuante scontro {npc.name} cede e si ritira. "
                     f"Resti ferito. ({rounds} round)")
    else:
        lines.append(f"Dopo un lungo, estenuante scontro hai la peggio e ti ritiri, "
                     f"ferito. ({rounds} round)")
    return "\n".join(lines)


def _auto_end_enemy(conn, t, rng, player, npc, rounds, hp_p, pmax,
                    crit_any, mods, chosen, lines) -> str:
    wfrac = hp_p / max(1.0, pmax)
    # una vittoria decisa è un'uccisione: se lo abbatti in fretta restando in forze,
    # non si rialza. Solo gli scontri tirati lasciano al nemico la fuga da ferito.
    decisive = (rounds <= 2 and wfrac >= 0.6) or (rounds <= 1)
    death_prob = (0.5 + (0.3 if wfrac > 0.5 else 0.0) + (0.15 if crit_any else 0.0)
                  + mods.get("death_bonus", 0.0))
    died = True if decisive else (rng.random() < min(1.0, death_prob))
    obs: list[str] = []
    combat._apply_outcome(conn, t, rng, ("player", player.id, "Tu"),
                          ("npc", npc.id, npc.name), rounds, died, crit_any,
                          player.location_id, player.location_id, obs)
    world_tick.advance(conn, 1)
    if rounds == 1:
        lines.append("La differenza è schiacciante.")
    if died:
        lines.append(f"★ {npc.name} crolla: lo hai ucciso! ({rounds} round)")
        lines += _after_player_kill(conn, t, rng, player, npc, chosen)
    else:
        lines.append(f"{npc.name} è gravemente ferito e si ritira dallo scontro. ({rounds} round)")
    return "\n".join(lines)


def _auto_end_player(conn, t, rng, player, npc, rounds, lines) -> str:
    died = rng.random() < (0.5 if rounds > 1 else 0.7)
    obs: list[str] = []
    combat._apply_outcome(conn, t, rng, ("npc", npc.id, npc.name),
                          ("player", player.id, "Tu"), rounds, died, False,
                          player.location_id, player.location_id, obs)
    world_tick.advance(conn, 1)
    if rounds == 1:
        lines.append("Sei surclassato.")
    if died:
        lines.append(f"Cadi sotto i colpi di {npc.name}. ({rounds} round)")
    else:
        lines.append(f"Sei sopraffatto e ti accasci, ferito ma vivo. ({rounds} round)")
    return "\n".join(lines)

def _devour_on_kill(conn, t, rng, player, npc) -> str | None:
    """Assorbimento istantaneo del Morso dell'Abisso. Con testimoni lascia un segno:
    sul tuo nome a volto scoperto, sull'identità mascherata in incognito."""
    from engine.systems import absorption, reputation
    res = absorption.absorb(conn, t, rng, npc.id, player.id)
    if res["status"] in ("no_anomaly", "not_found", "not_here", "not_dead"):
        return None
    if reputation.witnesses(conn, player.location_id, npc.id):
        reputation.apply_deed(conn, player.id, infamy=10, suspicion=18, mask_leak=4)
    summary = res.get("summary", "L'Abisso reclama i resti.")
    return "L'Abisso reclama all'istante: " + summary


def _kill_reputation(conn, player, npc, was_outlaw: bool) -> str | None:
    """Effetto sociale di un'uccisione: giustizia -> fama; in pubblico/tradimento -> infamia.
    Con la maschera, le conseguenze ricadono sull'IDENTITÀ MASCHERATA, non sul tuo nome."""
    from engine.systems import reputation, sects
    disguised = reputation.is_disguised(conn, player.id)
    # uccidere creature (bestie/demoni/spiriti) non infanga: non sono persone
    vrow = conn.execute("SELECT faction_id, kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if vrow and vrow["kind"] not in (None, "human"):
        return None
    if was_outlaw:
        reputation.apply_deed(conn, player.id, fame=12)
        return ("La giustizia del Coltivatore Misterioso si diffonde." if disguised
                else "La tua giustizia si diffonde: la tua fama cresce.")
    vfac = vrow["faction_id"] if vrow else None
    m = sects.get_membership(conn, player.id)
    my_fac = m["faction_id"] if m else None
    if my_fac and vfac == my_fac and not disguised:
        # un tradimento riconoscibile macchia solo il volto scoperto
        reputation.adjust(conn, player.id, infamy=40, suspicion=10)
        return "Hai ucciso un membro della tua stessa setta: l'infamia ti macchia."
    witnesses = reputation.witnesses(conn, player.location_id, npc.id)
    if witnesses:
        reputation.apply_deed(conn, player.id, infamy=15)
        return ("Un'ombra mascherata uccide davanti a testimoni: l'infamia della maschera cresce."
                if disguised else "L'omicidio davanti a testimoni infanga il tuo nome.")
    return None


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
    from engine.systems import qi as qimod, progression
    qimod.restore_fraction(conn, 0.5, player.id)       # meditare ristora il Qi
    from engine.systems import spirit as spmod
    spmod.restore_fraction(conn, 0.5, player.id)
    progression.record_cultivation(conn, player.id)    # via dell'Universo
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


def _absorb_all(conn: sqlite3.Connection, player: entities.Player, force: bool) -> str:
    """Assorbe in sequenza tutti i resti assorbibili nel luogo."""
    from engine.systems import reputation
    bodies = conn.execute(
        "SELECT id, name FROM npcs WHERE location_id=? AND status='dead' ORDER BY id;",
        (player.location_id,)).fetchall()
    if not bodies:
        return "Non vedi resti da assorbire qui."
    disguised = reputation.is_disguised(conn, player.id)
    if not force and not disguised:
        watched = any(reputation.witnesses(conn, player.location_id, b["id"]) for b in bodies)
        if watched:
            return ("Ci sono testimoni: divorare i resti davanti a loro ti coprirà d'infamia.\n"
                    "  • 'mask on' poi 'absorb all'   → in incognito\n"
                    "  • 'absorb all confirm'          → fallo comunque")
    out = [f"Divori ogni resto presente ({len(bodies)})..."]
    done = 0
    for b in bodies:
        # ogni chiamata consuma un cadavere (poi diventa 'absorbed'); 'confirm' supera il gate
        line = cmd_absorb(conn, player, f"{b['name']} confirm")
        first = line.split("\n")[0].strip()
        out.append(f"  • {first}")
        done += 1
    out.append(f"Resti assorbiti: {done}.")
    return "\n".join(out)


def cmd_absorb(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import absorption
    if not absorption.can_absorb(conn, player.id):
        return "Non possiedi l'Abisso Divoratore: non puoi assorbire nessuno."
    if not arg:
        return "Assorbire chi? Usa: absorb <nome> (su resti a terra)"
    # 'absorb <nome> confirm' (o '!') = fallo comunque, anche davanti a testimoni
    raw = arg.strip()
    force = False
    low = raw.lower()
    for tok in (" confirm", " conferma", " comunque", " !"):
        if low.endswith(tok):
            force = True
            raw = raw[: len(raw) - len(tok)].strip()
            break
    if raw.endswith("!"):
        force = True
        raw = raw[:-1].strip()
    if raw.lower() in ("all", "tutti", "tutto", "tutte"):
        return _absorb_all(conn, player, force)
    npc = entities.find_dead_npc_in_location(conn, player.location_id, raw)
    if npc is None:
        return f"Non vedi i resti di '{raw}' qui."
    # contesto sociale PRIMA di assorbire (poi il bersaglio diventa 'absorbed')
    from engine.systems import reputation, sects
    watchers = reputation.witnesses(conn, player.location_id, npc.id)
    disguised = reputation.is_disguised(conn, player.id)
    # avviso: se c'è gente che guarda e non sei in incognito, lascia scegliere
    if watchers and not disguised and not force:
        names = ", ".join(w["name"] for w in watchers)
        return (f"Ci sono testimoni qui: {names}. Divorare i resti davanti a loro "
                f"ti coprirà d'infamia e farà crescere il sospetto.\n"
                f"  • 'mask on' poi 'absorb {raw}'  → in incognito\n"
                f"  • 'absorb {raw} confirm'         → fallo comunque")
    vf = conn.execute("SELECT faction_id FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    victim_fac = vf["faction_id"] if vf else None
    t = tick.get_tick(conn)
    rng = random.Random(t * 2999 + player.id + npc.id)
    res = absorption.absorb(conn, t, rng, npc.id, player.id)
    s = res["status"]
    # esiti che non producono assorbimento: messaggi diretti
    if s == "no_anomaly":
        return "Non possiedi l'Abisso Divoratore: non puoi assorbire nessuno."
    if s in ("not_found", "not_here"):
        return f"Non vedi i resti di '{arg}' qui."
    if s == "not_dead":
        return f"{npc.name} è ancora vivo: non puoi assorbirne i resti."

    # frase principale: fonte unica dal sistema (coerente con l'evento loggato)
    line = res.get("summary", f"Divori i resti di {npc.name}.")

    if s == "shattered":
        return line + ".."          # morte: l'anima si frantuma

    # dettaglio meccanico per tipo (qualitativo, niente numeri grezzi a parte i guadagni)
    detail = ""
    if s == "body":
        detail = (f" (+{res['strength']} forza, +{res['vitality']} vitalità, "
                  f"+{res['resistance']} resistenza)")
    elif s == "aura":
        detail = f" (+{res['aura']} aura, +{res['strength']} potenza offensiva)"
    elif s == "soul":
        detail = f" (+{res['soul']} anima" + (f", +{res['dao_gain']} Dao)" if res.get("dao_gain") else ")")
    elif s == "human":
        bits = [f"+{res['strength']} forza", f"+{res['vitality']} vitalità", f"+{res['soul']} anima"]
        if res.get("dao_gain"):
            bits.append(f"+{res['dao_gain']} Dao «{res['dao']}»")
        detail = " (" + ", ".join(bits) + ")"
    elif s == "comprehension":
        detail = f" (comprensione di '{res['dao']}' +{res['gain']})"

    out = [line + detail]

    # soglie di Corruzione e linea evolutiva: mostrale solo quando emergono
    clab = absorption.corruption_label(res.get("residue", 0))
    if clab and clab != "nessun segno visibile":
        out.append(f"Corruzione dell'Abisso: {clab}.")
    path = absorption.evolution_path(conn, player.id)
    if path:
        out.append(f"Ciò che stai diventando: {path}.")

    # SOSPETTO/INFAMIA: divorare un cadavere lascia sempre un segno; con testimoni
    # è molto peggio; un compagno di setta è un tradimento. La maschera SPOSTA il
    # marchio sull'identità mascherata (con una piccola fuga di sospetto sul vero te).
    m = sects.get_membership(conn, player.id)
    ally = bool(m and victim_fac and victim_fac == m["faction_id"])
    if disguised:
        if watchers:
            reputation.adjust_mask(conn, player.id,
                                   infamy=(40 if ally else 18), suspicion=28)
            reputation.adjust(conn, player.id, suspicion=4)   # la maschera contiene, non annulla
            out.append("L'identità mascherata si macchia: il Coltivatore Misterioso "
                       "è visto divorare i resti."
                       + (" Era uno dei tuoi: un orrore senza volto." if ally else ""))
        else:
            reputation.adjust(conn, player.id, suspicion=3)
    else:
        if watchers:
            reputation.adjust(conn, player.id, infamy=(40 if ally else 18), suspicion=28)
            out.append("Ti hanno visto divorare i resti: il sospetto cresce."
                       + (" Era uno dei tuoi: i compagni ti guardano con orrore." if ally else ""))
        else:
            reputation.adjust(conn, player.id, suspicion=8)
    sh = reputation.suspicion_hint(reputation.get(conn, player.id)["suspicion"])
    if sh and watchers and not disguised:
        out.append(sh)
    from engine.systems import sect_war
    w_msg = sect_war.on_enemy_defeated(conn, tick.get_tick(conn), player, npc.id, "absorb")
    if w_msg:
        out.append(w_msg)
    return " ".join(out)


def _weapon_drop_message(res: dict) -> str:
    s = res["status"]
    if s == "equipped":
        return (f"⚔ Impugni {res['found']}: è superiore alla tua {res['old']}. "
                f"Equipaggiata! (+{int(res['bonus']*100)}% attacco)")
    if s == "weaker":
        return (f"L'arma del caduto ({res['found']}) non è all'altezza della tua "
                f"{res['mine']}: la lasci.")
    if s == "wrong_type":
        return (f"Il caduto impugnava {res['found']}, ma la tua via è la {res['mine']}: "
                f"non puoi usarla.")
    if s == "no_path":
        return (f"Trovi {res['found']}, ma non hai ancora scelto una via marziale: "
                f"non puoi impugnarla (unisciti a una setta e scegli un'arma).")
    found = res.get("found", "un'arma")
    return f"Trovi {found}, ma non puoi usarla."


def cmd_loot(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    """Raccoglie il bottino lasciato a terra dai caduti importanti."""
    import json as _json
    from engine.systems import loot, items, weapons
    drops = loot.drops_in_location(conn, player.location_id)
    if not drops:
        return ("Non c'è nulla da raccogliere qui. Il bottino lo lasciano i caduti "
                "importanti (patriarchi, anziani, avversari di alto regno) e le bestie mitiche.")
    weapon_lines: list[str] = []
    item_lines: list[str] = []
    # le armi si valutano per l'auto-equip (non finiscono nello zaino); il resto va raccolto
    for d in drops:
        if d["item_type"] == "arma":
            erow = conn.execute("SELECT effects FROM items WHERE id=?;", (d["item_id"],)).fetchone()
            eff = _json.loads(erow["effects"]) if erow and erow["effects"] else {}
            res = weapons.try_equip_drop(conn, player.id, eff.get("weapon_type"),
                                         int(eff.get("tier", 1)), int(eff.get("rarity", 1)))
            weapon_lines.append("  " + _weapon_drop_message(res))
            conn.execute("DELETE FROM inventories WHERE id=?;", (d["inv_id"],))
        else:
            item_lines.append(f"  • {d['name']} [{items.rarity_word(d['rarity'])}] — {d['description']}")
    loot.take_all(conn, player.id, player.location_id)   # raccoglie i non-armi rimasti
    lines = []
    if weapon_lines:
        lines.append("Armi sul campo:")
        lines += weapon_lines
    if item_lines:
        lines.append(f"Raccogli l'eredità del campo ({len(item_lines)} oggetti):")
        lines += item_lines
        lines.append("Tutto riposto nello zaino. Usa 'inventory' per vederlo, "
                     "'use <oggetto>' per servirtene.")
    return "\n".join(lines)


def cmd_inventory(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import items
    inv = items.player_inventory(conn, player.id)
    if not inv:
        return ("Il tuo zaino è vuoto. Sconfiggi avversari importanti e raccogli "
                "la loro eredità ('loot').")
    lines = ["Il tuo zaino:"]
    for r in inv:
        lines.append("  · " + items.describe_item(r))
    lines.append("Usa 'use <oggetto>' per servirti di un oggetto (lo consumi).")
    return "\n".join(lines)


def cmd_use_item(conn: sqlite3.Connection, player: entities.Player, frag: str) -> str:
    from engine.systems import items
    t = tick.get_tick(conn)
    rng = random.Random(t * 7351 + player.id + len(frag))
    res = items.use_item(conn, t, rng, player.id, frag)
    if res["status"] == "not_found":
        return f"Non hai nessun oggetto simile a '{frag}' nello zaino. Usa 'inventory'."
    return f"Usi {res['name']}.\n" + "\n".join(f"  {ln}" for ln in res["lines"])


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
        el = f", affine al {sects._dao_display(conn, r['element'])}" if r["element"] else ""
        lines.append(f"  · {r['name']} — {sects.tier_name(r['tier'])}{el} — sede: {r['hq_name']}{here}{mine}")
    if m:
        tn = sects.tier_name(m["sect_tier"])
        lines.append(f"\nSei {m['rank']} di {m['sect_name']} ({m['grade']}) — {tn}.")
        if sects.pending_invitations(conn, player.id):
            lines.append("Hai inviti pendenti da sette superiori: usa 'invitations'.")
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
        from engine.systems import sect_life, weapons
        rng = random.Random(t * 17 + player.id)
        setup = sect_life.setup_class(conn, t, rng, player.id)
        agenda = sect_life.agenda_line(conn, t, player.id)
        mates = sect_life.classmates(conn, player.id)
        mate_names = ", ".join(m["name"] for m in mates)
        msg = (f"Ti presenti alla sede di {res['sect']}. Misurano le tue radici spirituali: "
               f"{res['grade']}.\nSei ammesso come {res['rank']}. "
               f"Ricevi {res['stones']} pietre spirituali.\n"
               f"I tuoi compagni di classe: {mate_names}.\n"
               f"Annuncio: {agenda} Allenati: la classifica deciderà chi conta.")
        if weapons.get_weapon(conn, player.id) is None:
            msg += ("\nÈ ora di scegliere la tua ARMA principale (scelta permanente): "
                    "usa 'weapon <spada|lancia|sciabola|arco|pugni|bastone>'.")
        return msg
    return "Nulla accade."


def cmd_weapon(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import weapons, sects
    current = weapons.get_weapon(conn, player.id)
    if not arg.strip():
        if current:
            eq = weapons.get_equipped(conn, player.id)
            qual = (f" — {weapons.rarity_name(eq['rarity'])}, regno {eq['tier']} "
                    f"(+{int(eq['bonus']*100)}% attacco)") if eq else ""
            return (f"La tua arma è: {weapons.weapon_label(current)}{qual}.\n"
                    f"Dao d'arma sbloccato; allenalo con 'comprehend {current}'. "
                    f"Troverai armi migliori sui caduti che seguono la tua stessa via.")
        lines = ["Non hai ancora scelto un'arma. Le vie disponibili:"]
        lines += weapons.list_choices()
        lines.append("Scegli con 'weapon <nome>' (o il numero). La scelta è permanente.")
        return "\n".join(lines)
    if current:
        return (f"Hai già intrapreso la via della {weapons.weapon_label(current)}: "
                f"non si torna indietro. Allenala con 'comprehend {current}'.")
    if sects.get_membership(conn, player.id) is None:
        return ("Si sceglie l'arma entrando in una setta, che ti istruisce nella sua via. "
                "Unisciti prima a una setta ('sects' per trovarne una).")
    res = weapons.choose_weapon(conn, arg, player.id)
    if res["status"] == "invalid":
        return ("Arma non riconosciuta. Scegli tra: spada, lancia, sciabola, arco, pugni, bastone "
                "(o il numero 1-6).")
    if res["status"] == "already":
        return f"Hai già scelto: {res['weapon']}."
    return (f"Abbracci la via della {res['weapon']}. Sblocchi il {res['dao']}: "
            f"un Dao da combattimento. Allenalo con 'comprehend {res['dao_key']}' "
            f"per crescere secondo la tua via.")


def cmd_leave(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    res = sects.leave_sect(conn, player.id)
    if res["status"] == "not_member":
        return "Non appartieni ad alcuna setta."
    return f"Lasci {res['sect']}. Sei di nuovo un coltivatore errante."


def cmd_invitations(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    invs = sects.pending_invitations(conn, player.id)
    if not invs:
        return ("Nessun rappresentante ti corteggia. Vinci un torneo di setta "
                "(arriva 1°) per attirare le sette superiori.")
    lines = ["I RAPPRESENTANTI delle sette superiori ti offrono un posto",
             "(usa 'accept <numero>' per ascendere — lascerai la setta attuale):"]
    for r in invs:
        lines.append(f"  {r['slot']}. {r['name']} — {r['hint']}")
    return "\n".join(lines)


def cmd_accept(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import sects
    if not arg or not arg.strip().isdigit():
        return "Accettare quale invito? Usa: accept <numero> (vedi 'invitations')."
    slot = int(arg.strip())
    t = tick.get_tick(conn)
    rng = random.Random(t * 131 + player.id + slot)
    res = sects.accept_invitation(conn, t, rng, slot, player.id)
    if res["status"] == "no_invitation":
        return f"Non c'è un invito numero {slot}. Usa 'invitations' per la lista."
    el = sects._dao_display(conn, res["element"])
    return (f"Ascendi a {res['sect']} ({sects.tier_name(res['tier'])}) come {res['rank']} "
            f"({res['grade']}). Ricevi {res['stones']} pietre spirituali. "
            f"La setta è affine al {el}: comprenderlo sarà più rapido. "
            f"Ti trasferisci alla nuova sede; una nuova classe di rivali ti attende.")


def cmd_huntzone(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    if not m:
        return "Non appartieni a una setta: nessuna zona di caccia. Usa 'sects'."
    f = conn.execute("SELECT hunt_zone_id FROM factions WHERE id=?;", (m["faction_id"],)).fetchone()
    if not f or not f["hunt_zone_id"]:
        return "La tua setta non ha una zona di caccia designata."
    zid = f["hunt_zone_id"]
    zone = entities.get_location(conn, zid)
    alive = conn.execute(
        "SELECT COUNT(*) c FROM npcs WHERE location_id=? AND kind<>'human' AND status='alive';",
        (zid,)).fetchone()["c"]
    if zid == player.location_id:
        return (f"Sei nella zona di caccia di {m['sect_name']}: {zone.name} "
                f"{_danger_tag(zone.danger_level)}. Mostri presenti: {alive}. "
                f"Attaccali ('attack <nome>') per guadagnare merito; puoi anche assorbirli.")
    step = _first_step_toward(conn, player.location_id, zid)
    where = f"{zone.name} {_danger_tag(zone.danger_level)}"
    if step:
        return (f"La zona di caccia di {m['sect_name']} è {where} (mostri: {alive}). "
                f"Muoviti verso '{step}' per raggiungerla.")
    return f"La zona di caccia di {m['sect_name']} è {where}, ma non trovo una via da qui."


def cmd_events(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import world_events
    ev = world_events.active_event(conn)
    if not ev:
        return "Nessun evento mondiale in corso. Il mondo è in quiete... per ora."
    return world_events.describe(conn, ev, player.location_id, _first_step_toward)


def cmd_defend(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import world_events
    ev = world_events.active_event(conn)
    if not ev:
        return "Non c'è nessuna invasione da respingere ora. Usa 'events' per controllare."
    if ev["location_id"] != player.location_id:
        lname = conn.execute("SELECT name FROM locations WHERE id=?;",
                             (ev["location_id"],)).fetchone()["name"]
        step = _first_step_toward(conn, player.location_id, ev["location_id"])
        if step:
            return (f"L'invasione è a {lname}: non sei sul posto. "
                    f"Muoviti verso '{step}' per raggiungerla.")
        return f"L'invasione è a {lname}, ma non trovo una via da qui."
    inv = conn.execute(
        "SELECT name FROM npcs WHERE event_id=? AND status='alive' AND location_id=? LIMIT 1;",
        (ev["id"], player.location_id)).fetchone()
    if not inv:
        return "Non resta alcun invasore da abbattere qui."
    return cmd_attack(conn, player, inv["name"].split()[0])


def _move_effect_label(mods: dict) -> str:
    parts = []
    if mods.get("attack_mult", 1) > 1:
        parts.append(f"+{int((mods['attack_mult'] - 1) * 100)}% attacco")
    if mods.get("pierce"):
        parts.append(f"perfora {int(mods['pierce'] * 100)}% difesa")
    if mods.get("extra_strikes"):
        parts.append(f"+{int(mods['extra_strikes'])} colpi/round")
    if mods.get("taken_mult", 1) < 1:
        parts.append(f"-{int((1 - mods['taken_mult']) * 100)}% danni subiti")
    if mods.get("death_bonus"):
        parts.append("colpo esecutore")
    if mods.get("devour_on_kill"):
        parts.append("divora se uccide")
    return ", ".join(parts) or "colpo speciale"


def cmd_moves(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import moves, qi as qimod, spirit as spmod, dao_techniques
    ms = moves.available_moves(conn, player.id)
    qline = f"Qi: {qimod.qi_label(conn, player.id)} (mosse dei coltivatori; recuperi riposando)"
    has_dao = any(m.get("fuel") == "spirit" for m in ms)
    spline = (f"Spirito: {spmod.spirit_label(conn, player.id)} (tecniche Dao; si affatica e recupera)"
              if has_dao else None)
    if not ms:
        return (qline + "\nNon hai ancora mosse attive. Le ottieni scegliendo un'arma in setta "
                "('weapon'), imparando tecniche segrete ('techniques'), coltivando i Dao "
                "(le tecniche Dao nascono a comprensione ≥10), o con l'Abisso.")
    head = [qline] + ([spline] if spline else [])
    lines = head + ["Le tue mosse (usa 'attack <bersaglio> <mossa>' o 'use <mossa> <bersaglio>'):"]
    for m in ms:
        spirit_fuel = m.get("fuel") == "spirit"
        cost = (f"Spirito {m['spirit_cost']}" if spirit_fuel else f"Qi {m['qi_cost']}")
        if not m["ready"]:
            status = f"pronta tra ~{m['ready_in']} tick"
        elif not m["affordable"]:
            status = "Spirito insufficiente" if spirit_fuel else "Qi insufficiente"
        else:
            status = "pronta"
        tag = " «Dao»" if m["source"] == "dao" else ""
        lines.append(f"  · {m['name']}{tag} [{m['key']}] — {_move_effect_label(m['mods'])} "
                     f"({cost}, cooldown {m['cooldown']}) — {status}")
    return "\n".join(lines)


def cmd_use(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    parts = arg.strip().split(maxsplit=1)
    if len(parts) < 2:
        # un solo token: prova a usarlo come OGGETTO dello zaino
        from engine.systems import items
        single = arg.strip()
        if single and items.find_in_inventory(conn, player.id, single):
            return cmd_use_item(conn, player, single)
        return ("Uso: use <mossa> <bersaglio> (vedi 'moves'), "
                "oppure use <oggetto> per servirti di un oggetto (vedi 'inventory').")
    move_tok, target = parts[0], parts[1]
    return cmd_attack(conn, player, f"{target} {move_tok}")


def cmd_techniques(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects, guild, dao_techniques, spirit as spmod
    out: list[str] = []
    dao_list = dao_techniques.technique_list(conn, player.id)
    if dao_list:
        out.append(f"Tecniche del Dao (Guerriero Dao) — Spirito: {spmod.spirit_label(conn, player.id)}:")
        out += [f"  ◈ {ln}" for ln in dao_list]
        out.append("  Nascono dai tuoi Dao (≥10) ed evolvono a soglie; affaticano lo Spirito, non il Qi.")
    m = sects.get_membership(conn, player.id)
    if not m:
        if not dao_list:
            return ("Non hai tecniche. Le tecniche Dao nascono coltivando un Dao fino a "
                    "comprensione ≥10 ('comprehend <dao>'); le tecniche segrete richiedono una setta.")
        return "\n".join(out)
    techs = guild.sect_techniques(conn, m["faction_id"])
    merit = guild.get_merit(conn, player.id)
    if out:
        out.append("")
    out.append(f"Tecniche segrete di {m['sect_name']} (merito disponibile: {merit}):")
    for t in techs:
        if guild.is_learned(conn, t["key"], player.id):
            mark = "✔ appresa"
        else:
            mark = f"costo {t['cost']} merito"
        out.append(f"  {t['rank']}. {t['name']} — +{int(t['magnitude']*100)}% potenza — {mark}")
    out.append("Guadagna merito cacciando i mostri ('huntzone'); 'learn <n>' per apprendere.")
    return "\n".join(out)


def cmd_learn(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import guild
    if not arg.strip().isdigit():
        return "Imparare quale tecnica? Usa: learn <numero> (vedi 'techniques')."
    t = tick.get_tick(conn)
    res = guild.learn(conn, t, int(arg.strip()), player.id)
    s = res["status"]
    if s == "no_sect":
        return "Non appartieni a una setta."
    if s == "no_such":
        return "Quella tecnica non esiste. Usa 'techniques'."
    if s == "already":
        return f"Conosci già {res['name']}."
    if s == "poor":
        return (f"Merito insufficiente per {res['name']}: servono {res['need']}, "
                f"ne hai {res['have']}. Caccia altri mostri ('huntzone').")
    return (f"Apprendi {res['name']}! La tua potenza cresce (+{int(res['magnitude']*100)}%). "
            f"Merito residuo: {res['merit']}.")


def cmd_bounties(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import bounties
    bounties.replenish(conn, random.Random(tick.get_tick(conn) + 1))
    rows = bounties.active_bounties(conn)
    if not rows:
        return "Al momento nessuna taglia. La pace regna... per ora."
    lines = ["Ricercati (sconfiggili per riscuotere la taglia):"]
    for r in rows:
        where = f" — a {r['loc_name']}" if r["loc_name"] else ""
        realm = cultivation.realm_label(conn, "npc", r["npc_id"]) if "npc_id" in r.keys() else None
        lvl = f" [{realm}]" if realm else ""
        lines.append(f"  · {r['name']}{lvl}{where}: {r['crime']}. Taglia: {r['reward']} pietre.")
    lines.append("Il livello tra [ ] è la loro coltivazione: misurati prima di attaccare.")
    lines.append("Giustiziarli è un atto giusto (karma). Divorarli dà potere, ma corrompe.")
    return "\n".join(lines)


def _day_banner(conn: sqlite3.Connection, player: entities.Player) -> str | None:
    """Mostra 'GIORNO N' quando inizia un nuovo giorno, con i giorni all'evento."""
    from engine.systems import training, sect_life, sects
    t = tick.get_tick(conn)
    day = training.current_day(t)
    row = conn.execute("SELECT value FROM game_state WHERE key='last_day';").fetchone()
    last = int(row["value"]) if row else -1
    if day == last:
        return None
    conn.execute(
        "INSERT INTO game_state (key, value) VALUES ('last_day', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value;", (str(day),))
    # nuovo giorno: energie ristabilite (Qi al massimo). Non serve più dormire di continuo.
    from engine.systems import qi as qimod
    qimod.restore_full(conn, player.id)
    from engine.systems import spirit as spmod
    spmod.restore_full(conn, player.id)
    bar = "=" * 26
    lines = [bar, f"  GIORNO {day + 1}", bar, "  Un nuovo giorno: Qi e spirito ristabiliti."]
    if sects.get_membership(conn, player.id):
        nxt = sect_life.next_event(conn, t, player.id)
        if nxt:
            days = max(0, (nxt["fire_tick"] - t + training.DAY_TICKS - 1) // training.DAY_TICKS)
            label = ("Sfida di Classifica" if nxt["kind"] == "ranking_challenge"
                     else "Torneo Mensile")
            lines.append(f"  {label}: {'oggi!' if days == 0 else f'tra {days} giorni'}")
    return "\n".join(lines)


def cmd_hunt(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import bounties
    if not arg:
        return "Dare la caccia a chi? Usa: hunt <nome> (vedi 'bounties')."
    rows = bounties.active_bounties(conn)
    target = next((r for r in rows if arg.strip().lower() in r["name"].lower()), None)
    if target is None:
        return f"Nessun ricercato di nome '{arg}'. Usa 'bounties' per la lista."
    tloc = conn.execute("SELECT location_id FROM npcs WHERE id=?;", (target["npc_id"],)).fetchone()["location_id"]
    if tloc == player.location_id:
        return f"{target['name']} è proprio qui! Usa 'attack {target['name'].split()[0]}' per affrontarlo."
    step = _first_step_toward(conn, player.location_id, tloc)
    loc_name = conn.execute("SELECT name FROM locations WHERE id=?;", (tloc,)).fetchone()["name"]
    if step:
        return (f"{target['name']} è stato avvistato a {loc_name}. "
                f"Da qui muoviti verso '{step}' per raggiungerlo.")
    return f"{target['name']} è a {loc_name}, ma non sembra esserci una via diretta."


def _first_step_toward(conn, start, goal) -> str | None:
    """BFS sul grafo delle location: ritorna la direzione del primo passo."""
    from collections import deque
    if start == goal:
        return None
    seen = {start}
    q = deque([(start, None)])
    while q:
        cur, first_dir = q.popleft()
        for r in conn.execute(
            "SELECT direction, to_location_id FROM location_connections WHERE from_location_id=?;",
            (cur,)).fetchall():
            nxt, d = r["to_location_id"], r["direction"]
            if nxt in seen:
                continue
            fd = first_dir or d
            if nxt == goal:
                return fd
            seen.add(nxt)
            q.append((nxt, fd))
    return None


def cmd_sleep(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Salta direttamente all'inizio del giorno successivo."""
    from engine.systems import training
    t = tick.get_tick(conn)
    to_next = training.DAY_TICKS - (t % training.DAY_TICKS)
    world_tick.advance(conn, to_next)
    from engine.systems import qi as qimod
    qimod.restore_full(conn, player.id)                # una notte di riposo: Qi pieno
    from engine.systems import spirit as spmod
    spmod.restore_full(conn, player.id)
    return "Riposi fino all'alba del giorno seguente. Il tuo Qi è ristabilito."


def cmd_dao(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import dao_training
    rows = dao_training.trainable_daos(conn, player.id)
    if not rows:
        return "Non pratichi ancora alcun Dao."
    lines = ["I tuoi Dao (usa 'comprehend <nome>' per affinarli):"]
    for r in rows:
        tag = " [combattimento]" if r["dao_key"] in dao_training.COMBAT_DAOS else ""
        label = dao_training.comprehension_label(r["comprehension"])
        tech = dao_training.unlocked_technique(r["name"], r["comprehension"])
        tech_txt = f" — sbloccata: {tech}" if tech else ""
        lines.append(f"  · {r['name']} — {label}{tag}{tech_txt}")
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
    from engine.systems import sects
    elem = sects.element_bonus(conn, d["dao_key"], player.id)   # setta affine = comprensione più rapida
    y *= elem
    from engine.systems import absorption
    y *= 1.0 + absorption.evolution_bonuses(conn, player.id).get("dao_gain", 0.0)  # Imperatore Spirituale
    rng = random.Random(t * 53 + player.id)
    res = dao_training.comprehend(conn, t, rng, d["dao_key"], multiplier=y, player_id=player.id)
    world_tick.advance(conn, tick.cost_of("cultivate"))
    if res["status"] == "locked":
        return f"Il {d['name']} è solo un'affinità latente: devi prima risvegliarlo (assorbendo)."
    from engine.systems import progression
    if res["status"] not in ("exhausted",):
        progression.record_dao_training(conn, player.id)   # via del Dao
    name = d["name"]
    if res["status"] in ("exhausted",):
        return (f"Mediti sul {name}, ma sei troppo sfinito per progredire oggi "
                f"(allenamento {n}°). Riposa ('wait').")
    line = (f"Affini il {name}: comprensione ora {dao_training.comprehension_label(res['comprehension'])}.")
    line += f"\nAllenamento {n}° della giornata (rendimento {training.yield_label(y)})."
    if res.get("combat"):
        line += " Senti il tuo potere in battaglia crescere."
    if elem > 1.0:
        line += " (la tua setta è affine a questo Dao: progredisci più in fretta)"
    if res.get("unlocked"):
        line += f"\n★ Hai sbloccato una tecnica: {res['unlocked']}!"
    elif res.get("tier_up"):
        line += f"\nLa tua maestria si eleva: ora sei {res['label']}."
    if y <= 0.15:
        line += "\nSei sfinito: conviene riposare ('wait') o dedicarti ad altro."
    return line


def cmd_class(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sects, sect_life
    m = sects.get_membership(conn, player.id)
    if not m:
        return "Non appartieni ad alcuna setta. Usa 'sects' per trovarne una."
    t = tick.get_tick(conn)
    lines = [f"Setta: {m['sect_name']} — {m['rank']} ({sects.tier_name(m['sect_tier'])})"]
    from engine.systems import guild
    lines.append(f"Merito: {guild.get_merit(conn, player.id)} (caccia i mostri con 'huntzone'; 'techniques' per spenderlo)")
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
    from engine.systems import weapons
    wkey = weapons.get_weapon(conn, player.id)
    if wkey:
        lines.append(f"Via marziale: {weapons.weapon_label(wkey)} ({weapons.WEAPONS[wkey][2]}).")
    daos = dao_gen.list_character_daos(conn, "player", player.id)
    if daos:
        prat = [d for d in daos if d["practiced"]]
        lat = [d for d in daos if not d["practiced"]]
        if prat:
            from engine.systems import dao_training as _dt
            lines.append("Dao praticati: " + ", ".join(
                f"{d['name']} ({_dt.comprehension_label(d['comprehension'])})" for d in prat))
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


def cmd_reputation(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import reputation
    r = reputation.get(conn, player.id)
    al = reputation.alignment_of(conn, player.id)
    t = reputation.title(conn, player.id)
    lines = [f"Allineamento percepito: {al}" + (f' — "{t}"' if t else "")]
    lines.append(f"Fama {reputation.fame_word(r['fame'])} · Infamia {reputation.fame_word(r['infamy'])}.")
    sh = reputation.suspicion_hint(r["suspicion"])
    lines.append(sh if sh else "Nessun sospetto particolare pende su di te.")
    lines.append("Sei in incognito (maschera indossata)." if r["disguised"]
                 else "Cammini a volto scoperto.")
    ml = reputation.mask_line(conn, player.id)
    if ml:
        lines.append(ml)
    return "\n".join(lines)


def cmd_mask(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    from engine.systems import reputation
    a = arg.strip().lower()
    if a in ("on", "indossa", "si", "sì"):
        reputation.set_disguise(conn, player.id, True)
        ml = reputation.mask_line(conn, player.id)
        base = "Indossi la maschera. Per il mondo sei un Coltivatore Misterioso."
        return base + (f"\n{ml}" if ml else
                       " Ciò che farai così resterà sull'identità mascherata, non sul tuo nome.")
    if a in ("off", "togli", "via", "no"):
        reputation.set_disguise(conn, player.id, False)
        return "Ti togli la maschera. Il tuo volto è di nuovo scoperto."
    if reputation.is_disguised(conn, player.id):
        return "Sei mascherato. Usa 'mask off' per toglierla."
    return "Sei a volto scoperto. Usa 'mask on' per agire in incognito."


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
    from engine.systems import sects, weapons
    m = sects.get_membership(conn, player.id)
    sect_line = (f"Setta: {m['rank']} di {m['sect_name']} ({sects.tier_name(m['sect_tier'])})\n") if m else ""
    wkey = weapons.get_weapon(conn, player.id)
    if wkey:
        eq = weapons.get_equipped(conn, player.id)
        if eq and eq["bonus"] > 0:
            sect_line += (f"Arma: {weapons.weapon_label(wkey)} "
                          f"({weapons.rarity_name(eq['rarity'])}, regno {eq['tier']}, "
                          f"+{int(eq['bonus']*100)}% attacco)\n")
        else:
            sect_line += f"Arma: {weapons.weapon_label(wkey)}\n"
    if m:
        from engine.systems import sect_life
        ag = sect_life.agenda_line(conn, t, player.id)
        if ag:
            sect_line += f"Prossimo evento di setta — {ag}\n"
    stones = sects.get_resource(conn, "pietre_spirituali", player.id)
    res_line = f"Pietre spirituali: {stones}\n" if (m or stones) else ""
    from engine.systems import reputation, qi as qimod, progression
    rep = reputation.line(conn, player.id)
    rep_line = f"{rep}\n" if rep else ""
    qi_line = f"Qi (mosse): {qimod.qi_label(conn, player.id)}\n"
    from engine.systems import spirit as spmod, dao_techniques as dtk
    spirit_line = ""
    if dtk.dao_techniques(conn, player.id):
        spirit_line = f"Spirito (tecniche Dao): {spmod.spirit_label(conn, player.id)}\n"
    path_line = f"Via: {progression.path_label(conn, player.id)}\n"
    abyss_line = ""
    _prof = character.get_profile(conn, "player", player.id)
    if _prof and _prof["anomaly"] == "abisso_divoratore":
        from engine.systems import absorption
        res = _prof["soul_residue"] or 0
        abyss_line = f"Corruzione dell'Abisso: {absorption.corruption_label(res)}.\n"
        evo = absorption.evolution_path(conn, player.id)
        if evo:
            abyss_line += f"Ciò che diventi: {evo}.\n"
        from engine.systems import tribulation
        boons = tribulation.boon_list(conn, player.id)
        if boons:
            abyss_line += f"Doni del Fulmine: {', '.join(boons)}.\n"
    return (
        f"Name: {player.name}\n"
        f"{origin_line}"
        f"{sect_line}"
        f"{res_line}"
        f"{rep_line}"
        f"{qi_line}"
        f"{spirit_line}"
        f"{path_line}"
        f"{abyss_line}"
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


def cmd_war(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import sect_war
    war = sect_war.active_war(conn)
    if not war:
        return "Nessuna guerra tra sette in corso. (Se appartieni a una setta, può scoppiare.)"
    return sect_war.describe(conn, war, player.location_id, _first_step_toward)


def cmd_spare(conn: sqlite3.Connection, player: entities.Player, arg: str) -> str:
    """Sottometti e risparmia un discepolo nemico al fronte (richiede di essere abbastanza forte)."""
    from engine.systems import sect_war
    if not arg:
        return "Risparmiare chi? Usa: spare <nome> (su un discepolo nemico al fronte)."
    war = sect_war.active_war(conn)
    if not war or war["battle_location_id"] != player.location_id:
        return "Non sei a un fronte di guerra: non c'è nessun nemico da risparmiare qui."
    enemies = sect_war.enemy_disciples(conn, war)
    low = arg.strip().lower()
    target = next((e for e in enemies if low in e["name"].lower()), None)
    if target is None:
        return f"Nessun discepolo nemico di nome '{arg}' al fronte."
    pr = combat.combat_power(conn, "player", player.id)
    er = combat.combat_power(conn, "npc", target["id"])
    p_rating = pr["attack"] * 0.5 + pr["defense"] * 0.3 + pr["vitality"] * 0.2
    e_rating = er["attack"] * 0.5 + er["defense"] * 0.3 + er["vitality"] * 0.2
    if p_rating < e_rating:
        return (f"{target['name']} è troppo forte per essere sottomesso a mani basse: "
                f"se vuoi affrontarlo devi combatterlo ('attack {arg}').")
    t = tick.get_tick(conn)
    msg = sect_war.on_enemy_defeated(conn, t, player, target["id"], "spare")
    obs = world_tick.advance(conn, tick.cost_of("short_rest"))
    out = f"Sopraffai {target['name']} e gli concedi la vita. " + (msg or "")
    if obs:
        out += "\n" + _format_observations(obs)
    return out


def cmd_home(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Torna direttamente alla sede della tua setta (evita di perderti)."""
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    if m is None:
        return "Non appartieni a nessuna setta. ('join' per iscriverti dove possibile.)"
    home = conn.execute("SELECT home_location_id FROM factions WHERE id=?;",
                        (m["faction_id"],)).fetchone()
    if not home or home["home_location_id"] is None:
        return "La tua setta non ha una sede raggiungibile."
    dest = home["home_location_id"]
    if dest == player.location_id:
        return "Sei già alla sede della tua setta.\n" + render_location(conn, player)
    entities.move_player(conn, player.id, dest)
    obs = world_tick.advance(conn, tick.cost_of("move"))
    moved = entities.get_player(conn, player.id)
    out = (f"Tick {tick.get_tick(conn)} — torni alla sede della tua setta.\n"
           + render_location(conn, moved))
    if obs:
        out += "\nNel frattempo:\n" + _format_observations(obs)
    return out


def cmd_rating(conn: sqlite3.Connection, player: entities.Player) -> str:
    from engine.systems import power, zones
    pr = power.power_profile(conn, "player", player.id)
    cls = power.classify(conn, "player", player.id)[1]
    rating = power.combat_rating(conn, "player", player.id)
    mx = max(pr.values()) or 1.0
    bars = []
    for axis in ("qi", "corpo", "anima", "dao"):
        n = int(round(pr[axis] / mx * 12))
        bars.append(f"  {axis.capitalize():7} |{'█' * n}{'·' * (12 - n)}| {int(pr[axis])}")
    out = [f"Classe: {cls}  ·  Potenza effettiva (rating): {rating}",
           "Profilo di potenza:"] + bars
    z = zones.zone_of(conn, player.location_id)
    if z:
        out.append(zones.describe(conn, player.location_id))
    out.append("(Stili: Dao batte Qi, Qi batte Corpo, Corpo batte Anima, Anima batte Dao.)")
    return "\n".join(out)


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
    if cmd in ("help", "h", "?", "comandi"):
        return HELP
    if cmd in ("war", "guerra"):
        return cmd_war(conn, player)
    if cmd in ("spare", "risparmia"):
        return cmd_spare(conn, player, arg)
    if cmd in ("home", "base", "casa", "torna"):
        return cmd_home(conn, player)
    if cmd in ("rating", "potenza", "classe", "class_power"):
        return cmd_rating(conn, player)
    if cmd == "look":
        return cmd_look(conn, player, arg)
    if cmd == "examine":
        return cmd_examine(conn, player, arg)
    if cmd == "greet":
        return cmd_greet(conn, player, arg)
    if cmd == "attack":
        return cmd_attack(conn, player, arg)
    if cmd in ("moves", "mosse"):
        return cmd_moves(conn, player)
    if cmd in ("use", "usa"):
        return cmd_use(conn, player, arg)
    if cmd in ("absorb", "devour", "divora"):
        return cmd_absorb(conn, player, arg)
    if cmd in ("loot", "raccogli", "saccheggia", "bottino"):
        return cmd_loot(conn, player, arg)
    if cmd in ("inventory", "inv", "bag", "zaino", "inventario"):
        return cmd_inventory(conn, player)
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
    if cmd in ("invitations", "inviti", "rappresentanti"):
        return cmd_invitations(conn, player)
    if cmd in ("accept", "accetta", "ascend", "ascendi"):
        return cmd_accept(conn, player, arg)
    if cmd in ("huntzone", "huntground", "zonadicaccia", "zona"):
        return cmd_huntzone(conn, player)
    if cmd in ("techniques", "tecniche", "skills"):
        return cmd_techniques(conn, player)
    if cmd in ("learn", "impara", "apprendi"):
        return cmd_learn(conn, player, arg)
    if cmd in ("weapon", "arma"):
        return cmd_weapon(conn, player, arg)
    if cmd in ("events", "eventi", "world"):
        return cmd_events(conn, player)
    if cmd in ("defend", "difendi"):
        return cmd_defend(conn, player)
    if cmd in ("class", "classe", "agenda"):
        return cmd_class(conn, player)
    if cmd in ("dao", "daos"):
        return cmd_dao(conn, player)
    if cmd in ("bounties", "missions", "taglie", "missioni"):
        return cmd_bounties(conn, player)
    if cmd in ("hunt", "caccia"):
        return cmd_hunt(conn, player, arg)
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
    if cmd in ("reputation", "reputazione", "fama", "standing"):
        return cmd_reputation(conn, player)
    if cmd in ("mask", "maschera", "disguise"):
        return cmd_mask(conn, player, arg)
    if cmd in ("profilo", "profile", "background"):
        return cmd_profile(conn, player)
    if cmd == "move":
        return cmd_move(conn, player, arg)
    if cmd in ("wait", "rest"):
        return cmd_wait(conn, player)
    if cmd in ("sleep", "dormi"):
        return cmd_sleep(conn, player)
    if cmd in ("cultivate", "meditate", "coltiva", "c", "med"):
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
        # banner di nuovo giorno (se il tempo è avanzato oltre la mezzanotte)
        with transaction() as conn:
            p0 = entities.get_player(conn)
            if p0 is not None:
                banner = _day_banner(conn, p0)
                if banner:
                    print(banner)
        # il mondo può averti ucciso (scontro o minaccia autonoma)
        with transaction() as conn:
            p = entities.get_player(conn)
        if p is None or p.status != "alive":
            print("\nLe tue ferite hanno avuto la meglio. Il mondo prosegue senza di te.")
            print("(fine partita)")
            return
