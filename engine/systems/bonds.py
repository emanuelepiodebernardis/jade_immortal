"""
LEGAMI — compagni di viaggio, maestro, rivali e NEMESI.

Prima l'unica interazione sociale era 'greet'. Ora le persone del mondo possono
diventare qualcuno per te (ispirazione: l'affinità dei personaggi nelle storie
interattive e le vite degli NPC nei giochi di coltivazione):

  - COMPAGNO: un amico (rapporto alto) che viaggia con te, combatte al tuo fianco e
    cresce ogni giorno. Ha una sua indole: se la tua condotta lo disgusta, se ne va.
  - MAESTRO: un anziano/eremita più forte di te che ti guida: la tua coltivazione
    rende di più e parlandogli ti insegna qualcosa del tuo Dao.
  - RIVALE: qualcuno che hai umiliato o sfidato. Si ricorda di te.
  - NEMESI: chi ti è sfuggito dopo una sconfitta, o chi giura vendetta per qualcuno
    che hai ucciso. Si allena, cresce e TORNA a cercarti.

Il DB resta la fonte di verità: tabella `bonds` + `npc_player_relations` per l'affinità.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import relations, state

KINDS_IT = {"companion": "compagno di viaggio", "master": "maestro",
            "rival": "rivale", "nemesis": "nemesi", "beast": "bestia spirituale",
            "disciple": "discepolo", "sworn": "fratello giurato", "dao_partner": "compagna del Dao",
            "family": "famiglia", "servo": "servo (sigillo dell'anima)", "scorta": "servo di scorta"}
RECRUIT_MIN = 40              # rapporto minimo per chiedere a qualcuno di seguirti
MASTER_MIN = 50               # rapporto minimo per diventare discepolo
MAX_NEMESES = 2
MASTER_CULTIVATION_BONUS = 0.25


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS bonds ("
        "id INTEGER PRIMARY KEY, player_id INTEGER NOT NULL, npc_id INTEGER NOT NULL, "
        "kind TEXT NOT NULL, status TEXT DEFAULT 'active', since_tick INTEGER DEFAULT 0, "
        "grudge INTEGER DEFAULT 0, ready_tick INTEGER DEFAULT 0, reason TEXT, "
        "UNIQUE(player_id, npc_id, kind));")


# ============================================================
# Lettura
# ============================================================

def _active(conn, player_id, kind):
    return conn.execute(
        "SELECT b.*, n.name, n.location_id, n.status AS npc_status FROM bonds b "
        "JOIN npcs n ON n.id=b.npc_id WHERE b.player_id=? AND b.kind=? AND b.status='active' "
        "ORDER BY b.id;", (player_id, kind)).fetchall()


def companion(conn: sqlite3.Connection, player_id: int = 1) -> sqlite3.Row | None:
    rows = [r for r in _active(conn, player_id, "companion") if r["npc_status"] == "alive"]
    return rows[0] if rows else None


def master(conn: sqlite3.Connection, player_id: int = 1) -> sqlite3.Row | None:
    rows = [r for r in _active(conn, player_id, "master") if r["npc_status"] == "alive"]
    return rows[0] if rows else None


def nemeses(conn: sqlite3.Connection, player_id: int = 1) -> list[sqlite3.Row]:
    return [r for r in _active(conn, player_id, "nemesis") if r["npc_status"] == "alive"]


def bond_kinds(conn: sqlite3.Connection, npc_id: int, player_id: int = 1) -> set[str]:
    try:
        return {r["kind"] for r in conn.execute(
            "SELECT kind FROM bonds WHERE player_id=? AND npc_id=? AND status='active';",
            (player_id, npc_id))}
    except sqlite3.OperationalError:
        return set()


def tag(conn: sqlite3.Connection, npc_id: int, player_id: int = 1) -> str | None:
    k = bond_kinds(conn, npc_id, player_id)
    if "nemesis" in k:
        return "NEMESI"
    if "companion" in k:
        return "tuo compagno"
    if "beast" in k:
        return "tua bestia"
    if "master" in k:
        return "tuo maestro"
    if "rival" in k:
        return "tuo rivale"
    if "servo" in k:
        return "tuo servo"
    return None


def protected_ids(conn: sqlite3.Connection, player_id: int = 1) -> set[int]:
    """NPC da non colpire per sbaglio con 'attack all' (compagno, maestro)."""
    try:
        return {r["npc_id"] for r in conn.execute(
            "SELECT npc_id FROM bonds WHERE player_id=? AND status='active' "
            "AND kind IN ('companion','master','beast','disciple','sworn','dao_partner','family','servo');", (player_id,))}
    except sqlite3.OperationalError:
        return set()


def pinned_ids(conn: sqlite3.Connection, player_id: int = 1) -> set[int]:
    """NPC che non vagano a caso: il compagno (ti segue) e le nemesi in caccia."""
    try:
        t = tick_mod.get_tick(conn)
        return {r["npc_id"] for r in conn.execute(
            "SELECT npc_id FROM bonds WHERE player_id=? AND status='active' AND "
            "(kind IN ('companion','beast','disciple','dao_partner','scorta','servo') OR (kind='nemesis' AND ready_tick<=?));",
            (player_id, t))}
    except sqlite3.OperationalError:
        return set()


# ============================================================
# Scrittura
# ============================================================

def add_bond(conn: sqlite3.Connection, player_id: int, npc_id: int, kind: str, t: int,
             rng: random.Random | None = None, reason: str = "") -> str | None:
    ensure_table(conn)
    npc = entities.get_npc(conn, npc_id)
    if npc is None:
        return None
    if kind == "nemesis":
        if len(nemeses(conn, player_id)) >= MAX_NEMESES and "nemesis" not in bond_kinds(conn, npc_id, player_id):
            return None
        rng = rng or random.Random(t + npc_id)
        from engine.systems import training
        ready = t + training.DAY_TICKS * rng.randint(2, 4)
        conn.execute(
            "INSERT INTO bonds (player_id, npc_id, kind, status, since_tick, grudge, ready_tick, reason) "
            "VALUES (?, ?, 'nemesis', 'active', ?, 1, ?, ?) "
            "ON CONFLICT(player_id, npc_id, kind) DO UPDATE SET status='active', "
            "grudge=bonds.grudge+1, ready_tick=excluded.ready_tick, reason=excluded.reason;",
            (player_id, npc_id, t, ready, reason))
        # una nemesi si ritira ad allenarsi: sparisce dalla mappa finché non è pronta
        conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (npc_id,))
        relations.adjust(conn, npc_id, -100, t, player_id)
        return f"☠ {npc.name} giura di vendicarsi ({reason}). È diventato la tua NEMESI: tornerà."
    conn.execute(
        "INSERT INTO bonds (player_id, npc_id, kind, status, since_tick, reason) "
        "VALUES (?, ?, ?, 'active', ?, ?) "
        "ON CONFLICT(player_id, npc_id, kind) DO UPDATE SET status='active', reason=excluded.reason;",
        (player_id, npc_id, kind, t, reason))
    if kind == "rival":
        relations.adjust(conn, npc_id, -25, t, player_id)
        return f"{npc.name} ora è il tuo RIVALE."
    if kind == "master":
        return (f"{npc.name} ora è il tuo MAESTRO: la tua coltivazione renderà di più e "
                f"parlandogli ('talk') imparerai qualcosa del tuo Dao.")
    if kind == "companion":
        return f"{npc.name} ora viaggia con te."
    return None


def end_bond(conn, player_id, npc_id, kind, status="ended") -> None:
    conn.execute("UPDATE bonds SET status=? WHERE player_id=? AND npc_id=? AND kind=? "
                 "AND status='active';", (status, player_id, npc_id, kind))


def follow_player(conn: sqlite3.Connection, player_id: int, location_id: int) -> None:
    """Il compagno si sposta con te."""
    try:
        conn.execute(
            "UPDATE npcs SET location_id=? WHERE status='alive' AND id IN ("
            "SELECT npc_id FROM bonds WHERE player_id=? AND kind IN ('companion','beast','dao_partner','scorta') "
            "AND status='active');",
            (location_id, player_id))
    except sqlite3.OperationalError:
        pass


# ============================================================
# Azioni sociali
# ============================================================

def _today_key(conn, action, npc_id) -> tuple[str, int]:
    from engine.systems import training
    day = training.current_day(tick_mod.get_tick(conn))
    return f"{action}:{npc_id}", day


def _used_today(conn, action, npc_id) -> bool:
    key, day = _today_key(conn, action, npc_id)
    log = state.get_json(conn, "social_day", {}) or {}
    return log.get(key) == day


def _mark_today(conn, action, npc_id) -> None:
    key, day = _today_key(conn, action, npc_id)
    log = state.get_json(conn, "social_day", {}) or {}
    log = {k: v for k, v in log.items() if v == day}      # ripulisce i giorni passati
    log[key] = day
    state.set_json(conn, "social_day", log)


_TALK_BY_TRAIT = {
    "ambition": ("parla solo di regni da scalare e di nomi da rendere immortali.",
                 "ti confida che gli basterebbe una vita tranquilla."),
    "honor": ("ti racconta dei giuramenti che ha mantenuto, anche a caro prezzo.",
              "ride delle regole: «Vince chi sopravvive»."),
    "greed": ("tiene il conto di ogni pietra spirituale, anche mentre parla.",
              "regala le sue pietre a chi ne ha bisogno, dice, senza pentirsene."),
    "courage": ("ti mostra con orgoglio le cicatrici di cento battaglie.",
                "ammette di temere le zone proibite più della morte."),
    "loyalty": ("parla della sua setta come di una famiglia.",
                "ha cambiato bandiera più volte, e non se ne vergogna."),
    "compassion": ("si preoccupa per i mortali dei villaggi vicini.",
                   "considera i deboli un peso per il mondo."),
    "pride": ("non perde occasione di ricordarti chi è.",
              "si schermisce quando gli fai un complimento."),
}


def talk(conn: sqlite3.Connection, t: int, rng: random.Random, player, npc) -> str:
    from engine.generators import npc_gen
    traits = entities.get_npc_traits(conn, npc.id)
    kinds = bond_kinds(conn, npc.id, player.id)
    if "nemesis" in kinds:
        return f"{npc.name} non ha parole per te: solo odio."
    lines = []
    first = not _used_today(conn, "talk", npc.id)
    if traits:
        tname, val = npc_gen._salient_traits(traits, 1)[0]
        hi, lo = _TALK_BY_TRAIT[tname]
        lines.append(f"Parli a lungo con {npc.name}, che {hi if val >= 50 else lo}")
    else:
        lines.append(f"Scambi qualche parola con {npc.name}.")
    from engine.systems import reputation
    delta = int(round((6 if first else 1) * reputation.social_factor(conn, player.id)))
    d = relations.adjust(conn, npc.id, delta, t, player.id)
    _mark_today(conn, "talk", npc.id)
    # una voce utile: chi parla con te ti dice qualcosa del mondo
    if first:
        hint = _rumor(conn, rng, player, npc)
        if hint:
            lines.append(f"«{hint}»")
    if "master" in kinds and first:
        from engine.systems import items, dao_training
        rows = dao_training.trainable_daos(conn, player.id)
        if rows:
            dk = rng.choice([r["dao_key"] for r in rows])
            lines.append(f"Il tuo maestro corregge la tua comprensione del Dao «{dk}».")
            lines += items.apply_effects(conn, t, rng, player.id, {"dao_key": dk, "dao_gain": 3})
    lines.append(f"Rapporto: {_rel_label(d.relationship_type)} ({d.score:+d}).")
    if (d.score >= recruit_need(conn, npc.id) and not kinds and npc_is_recruitable(conn, npc.id)
            and companion(conn, player.id) is None):
        lines.append(f"(Vi intendete: potresti chiedergli di viaggiare con te — 'recruit {npc.name}')")
    return "\n".join(lines)


def _rumor(conn, rng, player, npc) -> str | None:
    from engine.systems import bounties, world_events
    opts = []
    ab = bounties.active_bounties(conn)
    if ab:
        b = rng.choice(list(ab))
        opts.append(f"Dicono che {b['name']} si nasconda dalle parti di {b['loc_name'] or 'nessuno sa dove'}"
                    f": la taglia è di {b['reward']} pietre.")
    ev = world_events.active_event(conn)
    if ev:
        ln = conn.execute("SELECT name FROM locations WHERE id=?;", (ev["location_id"],)).fetchone()
        if ln:
            opts.append(f"Un'invasione minaccia {ln['name']}: servono braccia forti.")
    for nm in nemeses(conn, player.id):
        opts.append(f"Ho sentito che {nm['name']} chiede di te in giro. Non con buone intenzioni.")
    z = conn.execute("SELECT l.name FROM zone_themes z JOIN locations l ON l.id=z.location_id "
                     "ORDER BY RANDOM() LIMIT 1;").fetchone() if _has_table(conn, "zone_themes") else None
    if z:
        opts.append(f"A {z['name']} si allenano coltivatori di ogni scuola: buon posto per mettersi alla prova.")
    return rng.choice(opts) if opts else None


def _has_table(conn, name) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
                        (name,)).fetchone() is not None


def _rel_label(rt: str) -> str:
    return {"friend": "amico", "acquaintance": "conoscente", "stranger": "estraneo",
            "rival": "rivale", "enemy": "nemico"}.get(rt, rt)


def gift(conn, t, player, npc, amount: int) -> str:
    from engine.systems import sects
    if amount <= 0:
        return "Quante pietre vuoi donare? Usa: gift <nome> <pietre>"
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    if have < amount:
        return f"Non hai abbastanza pietre (ne hai {have})."
    if "nemesis" in bond_kinds(conn, npc.id, player.id):
        return f"{npc.name} getta a terra il tuo dono."
    traits = entities.get_npc_traits(conn, npc.id)
    greed = traits.get("greed", 50) if traits else 50
    pride = traits.get("pride", 50) if traits else 50
    sects.grant_resource(conn, "pietre_spirituali", -amount, player.id)
    gain = int(min(30, amount / 5 * (0.5 + greed / 100)))
    if pride >= 80 and amount < 20:
        gain = -3
        msg = f"{npc.name} guarda il dono con disprezzo: «Mi prendi per un mendicante?»"
    elif greed >= 65:
        msg = f"Gli occhi di {npc.name} brillano: accetta il dono con entusiasmo."
    else:
        msg = f"{npc.name} accetta il dono con un cenno grato."
    d = relations.adjust(conn, npc.id, max(-5, gain), t, player.id)
    return f"{msg} (-{amount} pietre) Rapporto: {_rel_label(d.relationship_type)} ({d.score:+d})."


def spar(conn, t, rng, player, npc) -> str:
    from engine.simulation import combat, cultivation
    if "nemesis" in bond_kinds(conn, npc.id, player.id):
        return f"Con {npc.name} non esistono duelli amichevoli. Solo 'attack'."
    k = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if k and k["kind"] not in (None, "human"):
        return "Le creature selvagge non conoscono i duelli amichevoli."
    if _used_today(conn, "spar", npc.id):
        return f"Avete già incrociato le armi oggi. {npc.name} ha bisogno di riposare."
    d0 = relations.get_disposition(conn, npc.id, player.id)
    if d0.score <= -30:
        return f"{npc.name} rifiuta: se combatterete, sarà sul serio."
    _mark_today(conn, "spar", npc.id)
    pa = combat.combat_power(conn, "player", player.id)
    pn = combat.combat_power(conn, "npc", npc.id)
    sp = (pa["attack"] + pa["defense"] * 0.5 + pa["vitality"] * 0.3) * rng.uniform(0.85, 1.15)
    sn = (pn["attack"] + pn["defense"] * 0.5 + pn["vitality"] * 0.3) * rng.uniform(0.85, 1.15)
    won = sp >= sn
    ratio = sn / max(1.0, sp)
    # chi si misura con qualcuno più forte impara di più
    gain = max(0.04, min(0.25, 0.08 * ratio))
    cultivation.cultivate(conn, "player", player.id, t, rng, amount=gain)
    from engine.systems import npc_factory
    if won and rng.random() < 0.3:
        npc_factory.raise_npc(conn, npc.id, 1)        # anche lui impara dalla sconfitta
    traits = entities.get_npc_traits(conn, npc.id)
    pride = traits.get("pride", 50) if traits else 50
    honor = traits.get("honor", 50) if traits else 50
    if won:
        delta = 4 if honor >= 50 else (-4 if pride >= 75 else 1)
        head = f"Duello amichevole con {npc.name}: hai la meglio."
        mood = ("Ti stringe l'avambraccio con rispetto." if delta > 0
                else "Si rialza livido: l'orgoglio ferito brucia.")
    else:
        delta = 5
        head = f"Duello amichevole con {npc.name}: è lui a prevalere."
        mood = "Ti tende la mano per rialzarti: «Di nuovo, quando vuoi»."
    d = relations.adjust(conn, npc.id, delta, t, player.id)
    from engine.simulation import world_tick
    world_tick.advance(conn, tick_mod.cost_of("short_rest"))
    return (f"{head} {mood}\nMisurarti con lui affina la tua coltivazione. "
            f"Rapporto: {_rel_label(d.relationship_type)} ({d.score:+d}).")


def npc_is_recruitable(conn, npc_id) -> bool:
    r = conn.execute("SELECT kind, war_id, event_id, hunting, status FROM npcs WHERE id=?;",
                     (npc_id,)).fetchone()
    if not r or r["status"] != "alive":
        return False
    if r["kind"] not in (None, "human") or r["war_id"] or r["event_id"] or r["hunting"]:
        return False
    from engine.systems import bounties
    return not bounties.is_outlaw(conn, npc_id)


def recruit_need(conn, npc_id) -> int:
    arch = conn.execute("SELECT archetype FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    return 80 if arch and arch["archetype"] == "patriarca" else RECRUIT_MIN


def recruit(conn, t, player, npc) -> str:
    ensure_table(conn)
    if not npc_is_recruitable(conn, npc.id):
        return f"{npc.name} non può seguirti."
    cur = companion(conn, player.id)
    if cur and cur["npc_id"] == npc.id:
        return f"{npc.name} viaggia già con te."
    if cur:
        return f"Viaggi già con {cur['name']}. ('dismiss' per congedarlo.)"
    kinds = bond_kinds(conn, npc.id, player.id)
    if "nemesis" in kinds or "rival" in kinds:
        return f"{npc.name} ride: «Seguirti? Piuttosto la morte»."
    d = relations.get_disposition(conn, npc.id, player.id)
    need = recruit_need(conn, npc.id)
    if d.score < need:
        return (f"{npc.name} non ti conosce abbastanza per legare la sua strada alla tua "
                f"(rapporto {d.score:+d}, serve almeno {need:+d}: parlagli, aiutalo, fagli un dono).")
    add_bond(conn, player.id, npc.id, "companion", t, reason="ha scelto di seguirti")
    return (f"{npc.name} raccoglie le sue cose: «Andiamo». Da ora viaggia con te e "
            f"combatterà al tuo fianco.")


def dismiss(conn, t, player) -> str:
    cur = companion(conn, player.id)
    if not cur:
        return "Non hai compagni di viaggio."
    end_bond(conn, player.id, cur["npc_id"], "companion")
    relations.adjust(conn, cur["npc_id"], -5, t, player.id)
    return f"Saluti {cur['name']}: le vostre strade si separano, per ora."


def take_master(conn, t, player, npc) -> str:
    from engine.simulation import cultivation
    ensure_table(conn)
    arch = conn.execute("SELECT archetype FROM npcs WHERE id=?;", (npc.id,)).fetchone()["archetype"]
    if arch not in ("anziano", "eremita", "patriarca"):
        return f"{npc.name} non ha la statura di un maestro (cerca un anziano o un eremita)."
    cur = master(conn, player.id)
    if cur:
        return f"Hai già un maestro: {cur['name']}."
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    ntier = cultivation.realm_tier(conn, "npc", npc.id) or 1
    if ntier <= ptier:
        return f"{npc.name} scuote il capo: «Non ho più nulla da insegnarti»."
    d = relations.get_disposition(conn, npc.id, player.id)
    if d.score < MASTER_MIN:
        return (f"{npc.name} ti studia a lungo: «Non ti conosco ancora». "
                f"(rapporto {d.score:+d}, serve almeno {MASTER_MIN:+d})")
    add_bond(conn, player.id, npc.id, "master", t, reason="ti ha accettato come discepolo")
    state.grant_title(conn, f"Discepolo di {npc.name}")
    return (f"Ti inginocchi e {npc.name} ti accetta come discepolo. La tua coltivazione "
            f"renderà di più (+{int(MASTER_CULTIVATION_BONUS*100)}%) e parlandogli ('talk') "
            f"imparerai qualcosa del tuo Dao.")


def dao_partner(conn, player_id: int = 1):
    try:
        rows = [r for r in _active(conn, player_id, "dao_partner") if r["npc_status"] == "alive"]
    except sqlite3.OperationalError:
        return None
    return rows[0] if rows else None


def dao_partner_mult(conn, player_id: int, location_id) -> tuple[float, str]:
    """Doppia coltivazione: con la compagna del Dao accanto, il Qi circola tra due corpi."""
    dp = dao_partner(conn, player_id)
    if not dp or dp["location_id"] != location_id:
        return 1.0, ""
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "npc", dp["npc_id"]) or 1
    return 1.25 + 0.05 * min(tier, 10), f"la doppia coltivazione con {dp['name']}"


def cultivation_bonus(conn, player_id: int = 1) -> float:
    return MASTER_CULTIVATION_BONUS if master(conn, player_id) else 0.0


def describe(conn, player) -> str:
    ensure_table(conn)
    rows = conn.execute(
        "SELECT b.kind, b.status, b.reason, b.grudge, n.id AS npc_id, n.name, n.status AS npc_status, "
        "l.name AS loc FROM bonds b JOIN npcs n ON n.id=b.npc_id "
        "LEFT JOIN locations l ON l.id=n.location_id "
        "WHERE b.player_id=? ORDER BY b.status='active' DESC, b.id;", (player.id,)).fetchall()
    if not rows:
        return ("Nessun legame, per ora. Parla con le persone ('talk'), aiutale, sfidale: "
                "il mondo è pieno di futuri compagni, maestri e nemici.")
    from engine.simulation import cultivation
    lines = ["I tuoi legami:"]
    for r in rows:
        if r["status"] != "active":
            continue
        realm = cultivation.realm_label(conn, "npc", r["npc_id"]) if r["npc_status"] == "alive" else "caduto"
        where = r["loc"] or "lontano, chissà dove"
        d = relations.get_disposition(conn, r["npc_id"], player.id)
        extra = f" — rancore {r['grudge']}" if r["kind"] == "nemesis" else ""
        lines.append(f"  · {KINDS_IT.get(r['kind'], r['kind']).upper()}: {r['name']} "
                     f"({realm}; {where}; rapporto {d.score:+d}){extra}"
                     + (f" — {r['reason']}" if r["reason"] else ""))
    ended = [r for r in rows if r["status"] != "active"]
    if ended:
        lines.append("Legami chiusi: " + ", ".join(
            f"{r['name']} ({KINDS_IT.get(r['kind'], r['kind'])}, {r['status']})" for r in ended[-6:]))
    return "\n".join(lines)


# ============================================================
# Hook dal combattimento
# ============================================================

def companion_assist(conn, player_id: int, target_id: int):
    """(nome, potenza) del compagno che combatte con te, se presente qui e non è il bersaglio."""
    comp = companion(conn, player_id)
    if not comp or comp["npc_id"] == target_id:
        return None
    p = entities.get_player(conn, player_id)
    if comp["location_id"] != p.location_id:
        return None
    from engine.simulation import combat
    return comp["name"], combat.combat_power(conn, "npc", comp["npc_id"])


def on_enemy_fled(conn, t, rng, player, npc) -> str | None:
    """Un avversario UMANO ti sfugge ferito: chi è orgoglioso o ambizioso giura vendetta."""
    r = conn.execute("SELECT kind, war_id, event_id, hunting FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if not r or r["kind"] not in (None, "human") or r["war_id"] or r["event_id"]:
        return None
    kinds = bond_kinds(conn, npc.id, player.id)
    if "companion" in kinds or "master" in kinds:
        return None
    traits = entities.get_npc_traits(conn, npc.id)
    p = 0.25
    if traits:
        p += 0.35 * (traits.get("pride", 50) >= 70) + 0.2 * (traits.get("ambition", 50) >= 70)
    if "rival" in kinds or "nemesis" in kinds:
        p = 1.0
    if rng.random() >= p:
        return None
    return add_bond(conn, player.id, npc.id, "nemesis", t, rng=rng,
                    reason="gli hai inflitto una sconfitta umiliante")


def on_npc_killed(conn, t, rng, player, npc_id) -> list[str]:
    """Hai ucciso qualcuno: chiude un conto (nemesi/rivale) oppure ne APRE uno — chi gli
    voleva bene potrebbe giurare vendetta."""
    ensure_table(conn)
    lines = []
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (npc_id,)).fetchone()["name"]
    kinds = bond_kinds(conn, npc_id, player.id)
    if "nemesis" in kinds:
        end_bond(conn, player.id, npc_id, "nemesis", "vendicata")
        from engine.systems import reputation
        reputation.adjust(conn, player.id, fame=15)
        state.grant_title(conn, "Colui che Chiude i Conti")
        lines.append(f"Il conto con {name} è chiuso per sempre. (+15 fama)")
    for k in ("rival", "companion", "master"):
        if k in kinds:
            end_bond(conn, player.id, npc_id, k, "morto")
    # vendetta: l'amico più caro della vittima
    friend = conn.execute(
        "SELECT r.source_npc AS fid, n.name FROM npc_relationships r JOIN npcs n ON n.id=r.source_npc "
        "WHERE r.target_npc=? AND r.score>=35 AND n.status='alive' AND (n.kind='human' OR n.kind IS NULL) "
        "AND n.war_id IS NULL AND n.event_id IS NULL ORDER BY r.score DESC LIMIT 1;",
        (npc_id,)).fetchone()
    if friend and friend["fid"] not in protected_ids(conn, player.id) and rng.random() < 0.6:
        from engine.systems import npc_factory
        npc_factory.raise_npc(conn, friend["fid"], rng.randint(2, 5))
        msg = add_bond(conn, player.id, friend["fid"], "nemesis", t, rng=rng,
                       reason=f"vendetta per {name}")
        if msg:
            lines.append(msg)
    return lines


# ============================================================
# Ritmo giornaliero e caccia delle nemesi
# ============================================================

def daily(conn, t, rng, player) -> list[str]:
    """Una volta al giorno: crescita/lealtà del compagno, allenamento delle nemesi."""
    ensure_table(conn)
    out = []
    from engine.systems import npc_factory, reputation
    from engine.simulation import cultivation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    # compagno caduto?
    for r in _active(conn, player.id, "companion"):
        if r["npc_status"] != "alive":
            end_bond(conn, player.id, r["npc_id"], "companion", "morto")
            out.append(f"✝ Il tuo compagno {r['name']} è caduto. Il posto al tuo fianco resta vuoto.")
    comp = companion(conn, player.id)
    if comp:
        if rng.random() < 0.45 and npc_factory.npc_tier(conn, comp["npc_id"]) <= ptier:
            npc_factory.raise_npc(conn, comp["npc_id"], 1)
            out.append(f"{comp['name']} si è allenato con costanza: è più forte di ieri.")
        traits = entities.get_npc_traits(conn, comp["npc_id"])
        align = reputation.alignment_of(conn, player.id)
        dark = align in ("Eretico", "Mostro", "Temuto")
        if traits and traits.get("honor", 50) >= 60 and dark:
            d = relations.adjust(conn, comp["npc_id"], -10, t, player.id)
            if d.score < 20:
                end_bond(conn, player.id, comp["npc_id"], "companion", "se n'è andato")
                out.append(f"{comp['name']} non sopporta più ciò che sei diventato: se ne va "
                           f"senza voltarsi.")
            else:
                out.append(f"{comp['name']} ti guarda in silenzio. La tua fama lo turba.")
        else:
            relations.adjust(conn, comp["npc_id"], 2, t, player.id)
    # nemesi: si allenano finché non tornano (non oltre il tuo regno + 1)
    from engine.systems import destinies
    rm = destinies.rival_mult(conn)
    for nm in nemeses(conn, player.id):
        if nm["ready_tick"] > t and npc_factory.npc_tier(conn, nm["npc_id"]) <= ptier:
            npc_factory.raise_npc(conn, nm["npc_id"], max(1, round(rng.randint(1, 3) * rm)))
    return out


def _nearby_spawn(conn, start, rng, hops=3):
    loc = start
    for _ in range(hops):
        ex = entities.get_exits(conn, loc)
        if not ex:
            break
        loc = rng.choice(list(ex.values()))
    return loc


def tick(conn, t, rng, player, observations) -> int:
    """Le nemesi pronte riappaiono vicino a te e ti danno la caccia; quando ti trovano,
    si apre una scena con le tue scelte."""
    if player is None:
        return 0
    try:
        rows = nemeses(conn, player.id)
    except sqlite3.OperationalError:
        return 0
    p = entities.get_player(conn, player.id)
    if p is None or p.status != "alive":
        return 0
    events = 0
    from engine.systems import hunters, encounters, reports
    for nm in rows:
        if nm["ready_tick"] > t:
            continue
        if nm["location_id"] is None:
            loc = _nearby_spawn(conn, p.location_id, rng)
            conn.execute("UPDATE npcs SET location_id=?, last_active_tick=? WHERE id=?;",
                         (loc, t, nm["npc_id"]))
            reports.push(conn, player.id, t,
                         f"☠ Voci di strada: {nm['name']} è tornato, più forte, e chiede di te.")
            events += 1
            continue
        if nm["location_id"] == p.location_id:
            if encounters.pending(conn) or t - state.get_int(conn, "nemesis_scene_tick", -999) < 24:
                continue
            txt = encounters.start_scene(conn, p, nemesis_scene(conn, nm))
            if txt:
                state.set(conn, "nemesis_scene_tick", str(t))
                reports.push(conn, player.id, t, txt)
                events += 1
            continue
        step = hunters._next_step_toward(conn, nm["location_id"], p.location_id)
        if step is not None and rng.random() < 0.5:
            conn.execute("UPDATE npcs SET location_id=?, last_active_tick=? WHERE id=?;",
                         (step, t, nm["npc_id"]))
    return events


def nemesis_scene(conn, nm) -> dict:
    from engine.simulation import cultivation
    realm = cultivation.realm_label(conn, "npc", nm["npc_id"])
    grudge = nm["grudge"] or 1
    again = " di nuovo" if grudge > 1 else ""
    return {
        "key": "nemesi", "title": f"La nemesi: {nm['name']}", "event_type": "bond",
        "text": (f"{nm['name']} ti sbarra la strada{again}. Ora è {realm}. "
                 f"«{nm['reason'] or 'Ti avevo promesso che sarei tornato'}… e io mantengo le promesse»."),
        "ctx": {"npc_id": nm["npc_id"], "npc_name": nm["name"]},
        "on_leave": f"(Sfuggi a {nm['name']}, per ora. Ti troverà di nuovo.)",
        "choices": [
            {"label": "Combatti fino alla fine", "effects": {}, "command": f"attack {nm['name']}"},
            {"label": "Combatti a turni (ogni mossa la scegli tu)", "effects": {},
             "command": f"duello {nm['name']}"},
            {"label": "Provi a placare il suo rancore con le parole",
             "check": {"stat": "anima", "dc": 70 + 8 * grudge},
             "success": {"relation": 120, "karma": 30, "end_bond": "nemesis",
                         "text": f"{nm['name']} abbassa l'arma. «Forse… ho inseguito un'ombra». "
                                 f"Il rancore si scioglie."},
             "failure": {"text": "Le tue parole cadono nel vuoto.",
                         "command": f"attack {nm['name']}"}},
            {"label": "Fuggi",
             "check": {"stat": "istinto", "dc": 62},
             "success": {"bond_delay": 1, "text": "Sparisci tra la folla e i vicoli. Per ora."},
             "failure": {"injury": 3, "text": f"{nm['name']} ti ferisce mentre scappi.",
                         "command": f"attack {nm['name']}"}},
        ],
    }


def delay_nemesis(conn, player_id, npc_id, days: int) -> None:
    """La nemesi perde le tue tracce: sparisce e torna fra `days` giorni."""
    from engine.systems import training
    t = tick_mod.get_tick(conn)
    conn.execute("UPDATE bonds SET ready_tick=? WHERE player_id=? AND npc_id=? AND kind='nemesis' "
                 "AND status='active';", (t + training.DAY_TICKS * max(1, days), player_id, npc_id))
    conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (npc_id,))


def on_player_defeated(conn, t, rng, player, npc) -> str | None:
    """Se una nemesi ti batte senza ucciderti, se ne va soddisfatta… per ora."""
    if "nemesis" not in bond_kinds(conn, npc.id, player.id):
        return None
    delay_nemesis(conn, player.id, npc.id, rng.randint(2, 4))
    return f"{npc.name} sputa a terra: «Non vali ancora la mia spada. Allenati, e tornerò»."


def extra_fighters(conn, player_id: int, npc_id: int, fx) -> list[dict]:
    """Altri alleati nello scontro oltre al compagno: la bestia spirituale e lo spirito
    dell'arma. Possono anche aggiungere stati al contesto di combattimento `fx`."""
    out: list[dict] = []
    from engine.systems import beasts, weapon_spirit
    out += beasts.combat_allies(conn, player_id, npc_id, fx)
    w = weapon_spirit.combat_ally(conn, player_id, fx)
    if w:
        out.append(w)
    from engine.systems import clones, puppets
    out += clones.combat_allies(conn, player_id)
    out += puppets.combat_allies(conn, player_id, fx)
    from engine.systems import oaths, dominion
    out += oaths.combat_allies(conn, player_id, npc_id)
    out += dominion.combat_allies(conn, player_id, npc_id, fx)
    from engine.systems import dialogues, perception
    try:
        ratio = perception.strength_ratio(conn, player_id, npc_id)
        out += dialogues.rescuers(conn, player_id, npc_id, ratio)
        from engine.systems import feuds, race_realms
        out += feuds.allies_in_battle(conn, player_id, npc_id, ratio)
        out += race_realms.combat_allies(conn, player_id, npc_id, ratio)
    except Exception:
        pass
    return out
