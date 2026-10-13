"""
SVOLTE — i salti di QUALITÀ della via, non solo numeri che salgono.

Crescere all'infinito ha senso solo se ogni tanto cambia il MODO in cui giochi. Una svolta
sblocca un'azione nuova, un luogo nuovo o una regola nuova. Il comando `svolte` le mostra
tutte (raggiunte e prossime), e il mondo le annuncia quando arrivano.

Svolte nuove introdotte qui:
  VOLO (2° regno)              `vola <luogo>`: raggiungi un luogo già visitato senza camminare
                               (il tempo dipende dalla distanza; costa Qi)
  PASSO NEL VUOTO (6° regno)   `vola` diventa istantaneo
  PRIMO COLPO DELLO SPIRITO    un Dao oltre la Legge (2000, 4000, 8000… senza fine): il suo
                               Spirito del Dao (vedi dao_spirits) colpisce all'inizio di ogni
                               scontro con lo stato del Dao, più forte a ogni raddoppio
  IL TUO DAO (3 Dao alla Legge) `crea_dao <nome>`: fondi tre Dao in un Dao TUO, che
                               nessuno ha mai percorso. Ogni altri tre Dao alla Legge,
                               un nuovo Dao tuo
  CAPOLAVORO (arte 10, 20, 30…) `capolavoro <nome>`: un'opera unica che porta il tuo
                               nome; ogni capolavoro accelera per sempre la coltivazione

E raccoglie quelle che esistevano già (domini dei Dao, cloni, Mondo Interiore, forma del
sangue, Leggi dell'Imperatore, mondi superiori…), così vedi la strada davanti a te.
"""

from __future__ import annotations

import math

from engine.core import entities, tick as tick_mod
from engine.systems import state

FLY_TIER = 2
VOID_TIER = 6
LAW = 1000                 # soglia «legislatore» dei Dao
OWN_DAO_NEED = 3           # Dao alla Legge per ogni Dao tuo


# ------------------------------------------------------------
# Incarnazioni del Dao (oltre la Legge, senza fine)
# ------------------------------------------------------------

def incarnation(comprehension: int) -> int:
    """0 sotto i 2000; 1 a 2000, 2 a 4000, 3 a 8000… (ogni raddoppio, senza tetto)."""
    if comprehension < 2 * LAW:
        return 0
    return int(math.log2(comprehension / LAW))


def incarnations(conn, pid: int) -> list[tuple[str, str, int]]:
    rows = conn.execute(
        "SELECT cd.dao_key, d.name, cd.comprehension FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type='player' AND cd.character_id=? AND cd.comprehension>=?;", (pid, 2 * LAW)).fetchall()
    return [(r["dao_key"], r["name"], incarnation(r["comprehension"])) for r in rows]


def combat(conn, fx) -> list[str]:
    """All'inizio dello scontro i Dao incarnati colpiscono subito (stato garantito)."""
    from engine.systems.combat_states import STATE_OF_DAO
    out = []
    for key, name, n in incarnations(conn, 1):
        st = STATE_OF_DAO.get(key) or ("pressione" if key.startswith("proprio") else None)
        if not st:
            continue
        from engine.systems.combat_states import STATES
        target = fx.p if STATES.get(st, ("", "nemico"))[1] == "sé" else fx.e
        fx._apply(target, st, 1.0 + 0.25 * n)
        from engine.systems import dao_spirits
        form = dao_spirits._form(key, name)[0]
        out.append(f"✺ {form} colpisce per primo ({_roman(n)}): {st} prima ancora del tuo primo colpo.")
    return out


# ------------------------------------------------------------
# Volo
# ------------------------------------------------------------

def _tier(conn, pid: int) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def _distance(conn, a: int, b: int) -> int | None:
    from collections import deque
    if a == b:
        return 0
    seen, q = {a}, deque([(a, 0)])
    while q:
        cur, d = q.popleft()
        for r in conn.execute("SELECT to_location_id FROM location_connections WHERE from_location_id=?;", (cur,)):
            n = r["to_location_id"]
            if n == b:
                return d + 1
            if n not in seen:
                seen.add(n)
                q.append((n, d + 1))
    return None


def fly(conn, player, arg: str) -> str:
    from engine.simulation import world_tick
    from engine.systems import qi as qimod, captivity, encounters, qol
    tier = _tier(conn, player.id)
    if tier < FLY_TIER:
        return f"Non sai ancora volare: serve il {FLY_TIER}° regno (Fondazione)."
    if captivity.active(conn):
        return captivity.blocked_msg()
    if encounters.pending(conn):
        return "Prima risolvi ciò che hai davanti."
    places = state.get_json(conn, "world_codex_luoghi", []) or []
    a = arg.strip().lower()
    if not a:
        return ("Dove vuoi volare? 'vola <luogo>' (uno già visitato). Luoghi: "
                + ", ".join(places[:20]) + ("…" if len(places) > 20 else ""))
    match = [p for p in places if a in p.lower()]
    if not match:
        return f"Non conosci un luogo simile a '{arg}': puoi volare solo dove sei già stato ('codex luoghi')."
    row = conn.execute("SELECT id, name FROM locations WHERE name=? LIMIT 1;", (match[0],)).fetchone()
    if not row:
        return "Quel luogo non esiste più."
    if row["id"] == player.location_id:
        return "Sei già qui."
    dist = _distance(conn, player.location_id, row["id"])
    if dist is None:
        return f"{row['name']} è in un altro mondo: il volo non basta."
    instant = tier >= VOID_TIER
    cost = 0 if instant else 5 * dist
    if cost and not qimod.can_afford(conn, cost, player.id):
        return f"Ti servono {cost} di Qi per volare fin là (ne hai {qimod.get_qi(conn, player.id)}). Riposa o medita."
    if cost:
        qimod.spend(conn, cost, player.id)
    entities.move_player(conn, player.id, row["id"])
    world_tick.advance(conn, 1 if instant else max(1, dist // 2))
    qol.note(conn, "luoghi", row["name"])
    from engine.cli import loop
    after = loop._after_arrival(conn, entities.get_player(conn, player.id))
    if instant:
        return f"Fai un passo nel vuoto, e lo spazio si richiude dietro di te: sei a {row['name']}." + after
    return f"Sali sulla tua spada e solchi il cielo: {dist} tappe in un soffio. Atterri a {row['name']}." + after


# ------------------------------------------------------------
# Il tuo Dao
# ------------------------------------------------------------

def own_daos(conn, pid: int) -> list:
    return conn.execute(
        "SELECT cd.dao_key, d.name, cd.comprehension FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type='player' AND cd.character_id=? AND cd.dao_key LIKE 'proprio%';", (pid,)).fetchall()


def _laws(conn, pid: int) -> list:
    return conn.execute(
        "SELECT cd.dao_key, d.name, cd.comprehension FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key "
        "WHERE cd.character_type='player' AND cd.character_id=? AND cd.comprehension>=? "
        "AND cd.dao_key NOT LIKE 'proprio%' ORDER BY cd.comprehension DESC;", (pid, LAW)).fetchall()


def own_dao_slots(conn, pid: int) -> int:
    return len(_laws(conn, pid)) // OWN_DAO_NEED - len(own_daos(conn, pid))


def create_dao(conn, player, arg: str) -> str:
    name = arg.strip().strip("«»\"'")
    if own_dao_slots(conn, player.id) <= 0:
        have = len(_laws(conn, player.id))
        need = OWN_DAO_NEED * (len(own_daos(conn, player.id)) + 1)
        return (f"Per creare un Dao tuo servono {need} Dao alla Legge (comprensione ≥{LAW}): "
                f"ne hai {have}.")
    if not name or len(name) > 30:
        return "Dai un nome al tuo Dao: 'crea_dao <nome>' (es. 'crea_dao Giada Eterna')."
    used = {r["dao_key"] for r in own_daos(conn, player.id)}
    laws = [r for r in _laws(conn, player.id)][:OWN_DAO_NEED]
    n = len(used) + 1
    key = f"proprio{n}"
    comp = int(sum(r["comprehension"] for r in laws) / len(laws))
    full = f"Dao {name}" if name.lower().startswith(("del", "della", "dello", "dell", "delle", "dei")) \
        else f"Dao di {name}"
    conn.execute("INSERT OR REPLACE INTO daos (dao_key, name, level, description) VALUES (?, ?, 'superior', ?);",
                 (key, full, "Un Dao che nessuno aveva percorso prima: nato da " +
                  ", ".join(r["name"] for r in laws) + "."))
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES ('player', ?, ?, 90, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "comprehension=excluded.comprehension, practiced=1;", (player.id, key, comp))
    title = f"Fondatore del {full}"
    state.grant_title(conn, title)
    return (f"☯ Fondi {', '.join(r['name'] for r in laws)} in qualcosa che non esisteva: il {full}.\n"
            f"Il Cielo trema e lo registra nelle sue leggi. Comprensione iniziale {comp}.\n"
            f"✧ Nuovo titolo: «{title}» ✧")


# ------------------------------------------------------------
# Capolavori dell'arte
# ------------------------------------------------------------

def masterpieces(conn) -> list[dict]:
    return state.get_json(conn, "world_masterpieces_" + str(state.get_int(conn, "life_no", 1)), []) or []


def masterpiece_slots(conn, pid: int) -> int:
    from engine.systems import professions
    if not professions.profession(conn, pid):
        return 0
    return professions.level(conn, pid) // 10 - len(masterpieces(conn))


def masterpiece(conn, player, arg: str) -> str:
    from engine.systems import professions
    from engine.simulation import world_tick
    art = professions.profession(conn, player.id)
    if not art:
        return "Non pratichi nessuna arte."
    if masterpiece_slots(conn, player.id) <= 0:
        nxt = (len(masterpieces(conn)) + 1) * 10
        return f"Un capolavoro chiede maestria: il prossimo al livello {nxt} dell'arte (ora {professions.level(conn, player.id)})."
    name = arg.strip().strip("«»\"'")
    if not name or len(name) > 40:
        return "Dai un nome alla tua opera: 'capolavoro <nome>'."
    kind = {"alchimia": "pillola", "forgia": "arma", "talismani": "sigillo", "formazioni": "formazione",
            "domatore": "patto"}.get(art, "opera")
    lst = masterpieces(conn)
    lst.append({"name": name, "art": art, "kind": kind, "day": tick_mod.get_tick(conn) // 120})
    state.set_json(conn, "world_masterpieces_" + str(state.get_int(conn, "life_no", 1)), lst)
    world_tick.advance(conn, 120)
    title = f"Autore di «{name}»"
    state.grant_title(conn, title)
    from engine.systems import reputation
    reputation.adjust(conn, player.id, fame=15)
    return (f"Per un giorno e una notte non esisti che per l'opera. All'alba la {kind} «{name}» è compiuta: "
            f"chi la guarda capisce che un'arte ha cambiato padrone.\n"
            f"La tua coltivazione ne esce per sempre più limpida (+5%).\n✧ Nuovo titolo: «{title}» ✧")


def cultivation_mult(conn) -> tuple[float, str]:
    n = len(masterpieces(conn))
    return (1.0 + 0.05 * n, "i tuoi capolavori") if n else (1.0, "")


# ------------------------------------------------------------
# Il quadro di tutte le svolte
# ------------------------------------------------------------

def _roman(n: int) -> str:
    vals = [(1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"), (40, "XL"),
            (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]
    out = ""
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out or "0"


def milestones(conn, player) -> list[tuple[str, str, bool, str]]:
    """[(id, nome, raggiunta, come/cosa)] di tutte le svolte conosciute."""
    from engine.systems import (professions, clones, inner_space, bloodlines, master_plot, mentor_ring,
                                elements)
    pid = player.id
    tier = _tier(conn, pid)
    out = []
    out.append(("volo", "Volo", tier >= FLY_TIER, f"2° regno → 'vola <luogo>'"))
    out.append(("cloni", "Corpi Esterni (cloni)", tier >= 4 or bool(clones.clones(conn)), "4° regno → 'clone crea'"))
    out.append(("vuoto", "Passo nel Vuoto", tier >= VOID_TIER, f"{VOID_TIER}° regno → 'vola' istantaneo"))
    isl = inner_space.level(conn)
    out.append(("mondo_interiore", "Mondo Interiore", isl >= 5, f"spazio interiore al livello 5 (ora {isl})"))
    doms = elements.profile(conn, "player", pid)["domains"]
    out.append(("dominio", "Dominio del Dao", bool(doms), "un Dao a 500: lo spazio obbedisce al tuo Dao in battaglia"))
    laws = _laws(conn, pid)
    out.append(("legge", "Legge del Dao", bool(laws), f"un Dao a {LAW}"))
    incs = incarnations(conn, pid)
    best = max((n for _k, _nm, n in incs), default=0)
    out.append((f"incarnazione_{best}" if best else "incarnazione", "Primo Colpo dello Spirito del Dao" +
                (f" {_roman(best)}" if best else ""), bool(incs),
                f"un Dao a {2 * LAW}: il suo Spirito colpisce prima di te (più forte a ogni raddoppio)"))
    owns = own_daos(conn, pid)
    out.append((f"dao_proprio_{len(owns)}" if owns else "dao_proprio", "Il tuo Dao" +
                (f" ({len(owns)})" if len(owns) > 1 else ""), bool(owns),
                f"{OWN_DAO_NEED} Dao alla Legge → 'crea_dao <nome>' (puoi crearne: {max(0, own_dao_slots(conn, pid))})"))
    sacred = any(bloodlines.grade_index(ln["conc"]) >= bloodlines.SACRED for _k, ln in bloodlines.ordered(conn))
    out.append(("forma_sangue", "Forma del Sangue", sacred, "un lignaggio al grado Sacro → 'trasformati'"))
    out.append(("legato_anello", "Eredità del Maestro dell'Anello", mentor_ring.level(conn) >= 6,
                f"maestro dell'anello al livello 6 (ora {mentor_ring.level(conn)})"))
    mp = masterpieces(conn)
    out.append((f"capolavoro_{len(mp)}" if mp else "capolavoro", "Capolavoro" + (f" ({len(mp)})" if mp else ""),
                bool(mp), f"arte al livello 10, 20, 30… → 'capolavoro <nome>' (ora "
                          f"{professions.level(conn, pid) if professions.profession(conn, pid) else 0})"))
    nlaw = len(master_plot.get(conn).get("laws", []))
    out.append((f"leggi_imperatore_{nlaw}" if nlaw else "leggi_imperatore", "Leggi dell'Imperatore del Dao" +
                (f" ({nlaw})" if nlaw else ""), bool(nlaw), "una per ogni mondo superiore conquistato"))
    return out


def describe(conn, player) -> str:
    ms = milestones(conn, player)
    lines = ["✦ SVOLTE DELLA VIA — ciò che cambia il modo in cui giochi ✦"]
    done = [m for m in ms if m[2]]
    todo = [m for m in ms if not m[2]]
    if done:
        lines.append(" Raggiunte:")
        lines += [f"  ✔ {nm} — {how}" for _i, nm, _d, how in done]
    if todo:
        lines.append(" Davanti a te:")
        lines += [f"  · {nm} — {how}" for _i, nm, _d, how in todo]
    return "\n".join(lines)


def check_new(conn, player) -> list[str]:
    """Annuncia le svolte appena raggiunte (una volta sola)."""
    seen = set(state.get_json(conn, "svolte_seen", []) or [])
    out = []
    for mid, nm, done, how in milestones(conn, player):
        if done and mid not in seen:
            seen.add(mid)
            out.append(f"✦ SVOLTA: {nm}! ({how}) — 'svolte' per la strada che ti resta.")
            from engine.systems import chronicle
            chronicle.add(conn, "svolta", f"Svolta: {nm}.")
    if out:
        state.set_json(conn, "svolte_seen", sorted(seen))
    return out
