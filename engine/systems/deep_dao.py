"""
I TRE DAO PROFONDI E LA SFIDA AL CIELO — arcani, risonanze, e la guerra con il Cielo.

Spazio, Tempo e Destino non sono Dao come gli altri: sono le LEGGI su cui il Cielo regge
il mondo. Chi le comprende non diventa solo più forte: comincia a riscriverle. E il Cielo
se ne accorge (dao_powers.heaven_defiance).

ARCANI (奥义) — poteri attivi che si sbloccano salendo nella comprensione:
  SPAZIO   · Passo nel Vuoto      (iniziato)   ti sposti in un luogo che conosci, all'istante
           · Taglio del Vuoto     (adepto)     il prossimo scontro: la difesa non esiste, +2 echi
           · Prigione Spaziale    (maestro)    chi è qui con te perde un terzo della forza per 3 giorni
           · Piccolo Mondo        (dominatore) crei un mondo tuo dentro il vuoto: coltivazione +15% per sempre
  TEMPO    · Occhio del Domani    (iniziato)   vedi chi arriverà, e quando
           · Camera del Tempo     (adepto)     un anno di coltivazione in un giorno (costa anni di vita)
           · Rallentare il Tempo  (esperto)    il prossimo scontro: +30% schivata e un colpo in più per round
           · Riavvolgere          (maestro)    passivo: una volta al mese la morte si riavvolge
  DESTINO  · Leggere il Fato      (iniziato)   chi hai davanti: forza, karma, se ti darà la caccia
           · Riannodare il Filo   (adepto)     passivo: uno sfondamento fallito si ritenta (ogni 10 giorni)
           · Benedizione del Fato (esperto)    i prossimi tre bottini salgono di rarità
           · Recidere il Fato     (gran maestro) un nemico perde il 40% della forza per 5 giorni

RISONANZE (due Dao profondi almeno «maestro»):
  Spazio+Tempo   = Dominio Spazio-Tempo  (+1 eco, +10% schivata)
  Tempo+Destino  = Fiume del Destino     (+6% sfondamento, l'Occhio del Domani non costa nulla)
  Spazio+Destino = Causalità             (+12% critico: il colpo «è già avvenuto»)
  tutti e tre «gran maestro» = Trinità delle Leggi (tutte le risonanze raddoppiano)

LA GUERRA CON IL CIELO (capitoli, senza fine):
  50    Presagi            il cielo si incrina sopra di te
  150   L'Occhio del Cielo il Cielo ti guarda: le tribolazioni ti cercano
  300   I Messaggeri       Esecutori del Cielo ti danno la caccia (alla tua altezza); abbatterli
                           dà Frammenti della Legge
  600   Il Giudizio        una scelta: sottometterti, sfidare la Volontà del Cielo, o ingannarla
                           (col Destino) — e poi un Giudizio più alto a ogni raddoppio della sfida
  Ogni vittoria sulla Volontà del Cielo dà un SIGILLO DELLA SFIDA: forza e titoli che salgono.

  dao_profondi                il pannello: arcani, risonanze, capitolo della guerra
  arcano <nome> [bersaglio]   usa un arcano (passo, taglio, prigione, mondo, domani, camera,
                              rallenta, leggi, benedici, recidi)
  cielo sottometti|sfida|inganna   la risposta al Giudizio
"""

from __future__ import annotations

import math
import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "deep_dao"
DEEP = ("spazio", "tempo", "destino")
DEEP_NAME = {"spazio": "Spazio", "tempo": "Tempo", "destino": "Destino"}
ICON = {"spazio": "🌌", "tempo": "⏳", "destino": "🎲"}

# arcano -> (dao, indice minimo di soglia, nome, descrizione, ricarica in giorni, costo di spirito in frazione)
ARCANA = {
    "passo":    ("spazio", 1, "Passo nel Vuoto", "ti sposti all'istante in un luogo che conosci", 0, 0.10),
    "taglio":   ("spazio", 2, "Taglio del Vuoto", "il prossimo scontro: la difesa non esiste e ogni colpo ha 2 echi", 3, 0.20),
    "prigione": ("spazio", 4, "Prigione Spaziale", "chi è qui con te perde un terzo della forza per 3 giorni", 5, 0.30),
    "mondo":    ("spazio", 6, "Piccolo Mondo", "crei un mondo tuo nel vuoto: coltivazione +15% per sempre", -1, 0.60),
    "domani":   ("tempo", 1, "Occhio del Domani", "vedi chi ti cerca e quando arriverà", 1, 0.08),
    "camera":   ("tempo", 2, "Camera del Tempo", "un anno di coltivazione in un giorno, al prezzo di anni di vita", 7, 0.35),
    "rallenta": ("tempo", 3, "Rallentare il Tempo", "il prossimo scontro: +30% schivata e un colpo in più", 3, 0.20),
    "riavvolgi": ("tempo", 4, "Riavvolgere", "passivo: una volta ogni 30 giorni la tua morte si riavvolge", -2, 0.0),
    "leggi":    ("destino", 1, "Leggere il Fato", "forza, karma e intenzioni di chi hai davanti", 0, 0.05),
    "filo":     ("destino", 2, "Riannodare il Filo", "passivo: uno sfondamento fallito si ritenta (ogni 10 giorni)", -2, 0.0),
    "benedici": ("destino", 3, "Benedizione del Fato", "i prossimi tre bottini salgono di una classe di rarità", 5, 0.25),
    "recidi":   ("destino", 5, "Recidere il Fato", "un nemico perde il 40% della forza per 5 giorni", 10, 0.40),
}
ALIASES = {"vuoto": "passo", "teletrasporto": "passo", "piccolo_mondo": "mondo", "occhio": "domani",
           "prescienza": "domani", "rallentare": "rallenta", "leggere": "leggi", "fato": "leggi",
           "benedizione": "benedici", "recidere": "recidi", "prigione_spaziale": "prigione"}

RESONANCES = {
    ("spazio", "tempo"): ("Dominio Spazio-Tempo", "+1 eco per colpo, +10% schivata"),
    ("tempo", "destino"): ("Fiume del Destino", "+6% riuscita dello sfondamento, l'Occhio del Domani è gratis"),
    ("spazio", "destino"): ("Causalità", "+12% critico: il colpo «è già avvenuto»"),
}
RES_IDX = 4          # «maestro»
TRINITY_IDX = 5      # «gran maestro»

# capitoli della guerra con il Cielo
CHAPTERS = [
    (0, "Il Cielo dorme", "Le tue leggi sono ancora quelle del mondo."),
    (50, "Presagi", "Il cielo si incrina sopra di te nelle notti senza luna; gli animali tacciono quando passi."),
    (150, "L'Occhio del Cielo", "Un occhio senza palpebre si apre oltre le nubi. Le tribolazioni ti cercano."),
    (300, "I Messaggeri", "Il Cielo manda i suoi Esecutori: ti trovano ovunque, e sono alla tua altezza."),
    (600, "Il Giudizio", "Il Cielo chiede una risposta: piegarti, sfidarlo, o ingannarlo."),
]
JUDGMENT_BASE = 600
MESSENGER_EVERY = 20       # giorni tra un Messaggero e l'altro

_HEAVEN_NAMES = ["Esecutore della Legge", "Messaggero del Cielo", "Guardiano del Dao Celeste",
                 "Ufficiale della Tribolazione", "Inviato delle Nove Nubi", "Custode del Registro"]


# ---------------------------------------------------------------- stato

def get(conn) -> dict:
    d = state.get_json(conn, KEY, None) or {}
    d.setdefault("cool", {})
    d.setdefault("buffs", {})
    d.setdefault("debuff", {})
    d.setdefault("chapter", 0)
    d.setdefault("messengers", [])
    d.setdefault("msg_day", -999)
    d.setdefault("judgments", 0)
    d.setdefault("seals", 0)
    d.setdefault("hidden_until", -1)
    d.setdefault("filo_day", -999)
    d.setdefault("rewind_day", -999)
    d.setdefault("blessing", 0)
    d.setdefault("small_world", False)
    d.setdefault("pending_judgment", False)
    d.setdefault("will_npc", None)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def comp(conn, key: str, pid: int = 1) -> int:
    from engine.systems import dao_powers
    return dao_powers.comp(conn, key, pid)


def idx(conn, key: str, pid: int = 1) -> int:
    from engine.systems import dao_powers
    c = comp(conn, key, pid)
    return dao_powers._idx(c) if c > 0 else 0


def mastery(conn, key: str, pid: int = 1) -> float:
    """Padronanza continua e senza tetto: l'indice di soglia, più il logaritmo oltre l'ultima."""
    from engine.systems import dao_training as dt
    c = comp(conn, key, pid)
    if c <= 0:
        return 0.0
    i = idx(conn, key, pid)
    last = dt.DAO_THRESHOLDS[-1][0]
    return i + (math.log2(c / last) if c > last else 0.0)


# ---------------------------------------------------------------- risonanze

def resonances(conn, pid: int = 1) -> list[tuple[str, str, float]]:
    """[(nome, effetto, forza)] — forza 1 normale, 2 con la Trinità delle Leggi."""
    ids = {k: idx(conn, k, pid) for k in DEEP}
    trinity = all(v >= TRINITY_IDX for v in ids.values())
    out = []
    for (a, b), (name, eff) in RESONANCES.items():
        if ids[a] >= RES_IDX and ids[b] >= RES_IDX:
            out.append((name, eff, 2.0 if trinity else 1.0))
    if trinity:
        out.append(("Trinità delle Leggi", "tutte le risonanze raddoppiano", 1.0))
    return out


def _res(conn, name: str, pid: int = 1) -> float:
    for n, _e, f in resonances(conn, pid):
        if n == name:
            return f
    return 0.0


def space_bonus(conn, pid: int = 1) -> dict:
    """Bonus delle risonanze e dei Sigilli allo Spazio (usato da dao_powers.space_combat)."""
    st = _res(conn, "Dominio Spazio-Tempo", pid)
    ca = _res(conn, "Causalità", pid)
    return {"extra": int(st), "crit": 0.12 * ca}


def time_evasion_bonus(conn, pid: int = 1) -> float:
    return 0.10 * _res(conn, "Dominio Spazio-Tempo", pid)


def fate_bt_bonus(conn, pid: int = 1) -> float:
    return 0.06 * _res(conn, "Fiume del Destino", pid)


def cultivation_mult(conn) -> float:
    return 1.15 if get(conn)["small_world"] else 1.0


def seal_mult(conn) -> float:
    """Ogni Sigillo della Sfida rafforza (in modo logaritmico, senza tetto)."""
    s = get(conn)["seals"]
    return 1.0 + 0.12 * math.log2(1 + s) if s else 1.0


# ---------------------------------------------------------------- effetti in combattimento

def npc_mult(conn, npc_id: int) -> float:
    """Indebolimenti degli arcani (Prigione Spaziale, Recidere il Fato) su un NPC."""
    try:
        d = state.get_json(conn, KEY, None)
    except Exception:
        return 1.0
    if not d or not d.get("debuff"):
        return 1.0
    e = d["debuff"].get(str(npc_id))
    if not e:
        return 1.0
    until, mult = e
    return mult if _day(conn) <= until else 1.0


def fight_buffs(conn, space: dict, evasion: float) -> tuple[dict, float, list[str]]:
    """All'inizio di uno scontro: consuma gli arcani preparati (Taglio del Vuoto, Rallentare il Tempo)."""
    d = get(conn)
    lines = []
    space = dict(space)
    if d["buffs"].pop("taglio", None):
        space["pierce"] = 1.0
        space["extra_strikes"] = space.get("extra_strikes", 0) + 2
        space["label"] = space.get("label") or "Taglio del Vuoto"
        lines.append("🌌 Taglio del Vuoto: tra te e il nemico lo spazio non esiste più. La sua difesa è un ricordo.")
    if d["buffs"].pop("rallenta", None):
        evasion = min(0.85, evasion + 0.30)
        space["extra_strikes"] = space.get("extra_strikes", 0) + 1
        lines.append("⏳ Rallenti il Tempo: per il nemico scorre come miele, per te come acqua.")
    if lines:
        _save(conn, d)
    return space, evasion, lines


def take_blessing(conn) -> bool:
    d = get(conn)
    if d["blessing"] <= 0:
        return False
    d["blessing"] -= 1
    _save(conn, d)
    return True


def try_fate_reroll(conn, pid: int = 1) -> bool:
    """Riannodare il Filo: uno sfondamento fallito si ritenta, ogni 10 giorni."""
    if idx(conn, "destino", pid) < ARCANA["filo"][1]:
        return False
    d = get(conn)
    if _day(conn) - d["filo_day"] < 10:
        return False
    d["filo_day"] = _day(conn)
    _save(conn, d)
    return True


def try_time_rewind(conn, player) -> str | None:
    """Riavvolgere: una volta ogni 30 giorni la morte si riavvolge."""
    if idx(conn, "tempo", player.id) < ARCANA["riavvolgi"][1]:
        return None
    d = get(conn)
    if _day(conn) - d["rewind_day"] < 30:
        return None
    d["rewind_day"] = _day(conn)
    _save(conn, d)
    conn.execute("UPDATE players SET status='alive' WHERE id=?;", (player.id,))
    conn.execute("UPDATE injuries SET healed=1 WHERE character_type='player' AND character_id=?;", (player.id,))
    return ("⏳ Il colpo ti attraversa… e il Tempo si riavvolge di tre respiri. Sei vivo, un passo indietro, "
            "con il ricordo della tua morte negli occhi. (Riavvolgere: di nuovo tra 30 giorni)")


# ---------------------------------------------------------------- arcani

def _available(conn, key: str, pid: int) -> tuple[bool, str]:
    dao, need, *_r = ARCANA[key]
    from engine.systems import dao_training as dt
    i = idx(conn, dao, pid)
    if i < need:
        return False, f"serve il Dao {DEEP_NAME[dao]} «{dt.DAO_THRESHOLDS[need][1]}»"
    cd = ARCANA[key][4]
    if cd == -2:
        return False, "è passivo: agisce da solo"
    d = get(conn)
    if cd == -1 and d["small_world"]:
        return False, "il tuo Piccolo Mondo esiste già"
    last = d["cool"].get(key)
    if cd > 0 and last is not None and _day(conn) - last < cd:
        return False, f"si ricarica tra {cd - (_day(conn) - last)} giorni"
    return True, ""


def _pay(conn, pid: int, frac: float) -> tuple[bool, str]:
    if frac <= 0:
        return True, ""
    from engine.systems import spirit
    cost = max(1, int(spirit.max_spirit(conn, pid) * frac))
    if not spirit.can_afford(conn, cost, pid):
        return False, f"Non hai abbastanza spirito (servono {cost})."
    spirit.spend(conn, cost, pid)
    return True, f"(−{cost} spirito)"


def use_arcane(conn, player, arg: str) -> str:
    parts = (arg or "").strip().split(maxsplit=1)
    if not parts:
        return describe(conn, player)
    key = ALIASES.get(parts[0].lower(), parts[0].lower())
    rest = parts[1] if len(parts) > 1 else ""
    if key not in ARCANA:
        return "Arcano sconosciuto. Arcani: " + ", ".join(ARCANA)
    ok, why = _available(conn, key, player.id)
    if not ok:
        return f"{ARCANA[key][2]}: {why}."
    if key == "domani" and _res(conn, "Fiume del Destino", player.id):
        paid = (True, "")
    else:
        paid = _pay(conn, player.id, ARCANA[key][5])
    if not paid[0]:
        return paid[1]
    d = get(conn)
    out = _ARCANE_FN[key](conn, player, rest, d)
    if out.startswith("✗"):
        return out[1:].strip()
    if ARCANA[key][4] > 0:
        d["cool"][key] = _day(conn)
    _save(conn, d)
    conn.execute("UPDATE character_daos SET comprehension=comprehension+1 WHERE character_type='player' "
                 "AND character_id=? AND dao_key=?;", (player.id, ARCANA[key][0]))   # usarlo insegna
    return out + (f" {paid[1]}" if paid[1] else "")


def _a_passo(conn, player, rest, d) -> str:
    from engine.core import entities
    target = None
    if rest:
        r = conn.execute("SELECT id, name FROM locations WHERE LOWER(name) LIKE ? ORDER BY LENGTH(name) LIMIT 1;",
                         (f"%{rest.lower()}%",)).fetchone()
        target = r
    else:
        from engine.systems import cave_abode
        ab = cave_abode.get(conn, player.id)
        hid = ab["loc"] if ab else None
        if hid:
            target = conn.execute("SELECT id, name FROM locations WHERE id=?;", (hid,)).fetchone()
    if not target:
        return "✗ Dove? Scrivi «arcano passo <luogo>» (un luogo del tuo mondo)."
    from engine.systems import ascension
    if ascension.layer_of_location(conn, target["id"]) != ascension.player_layer(conn):
        return "✗ Il Vuoto non attraversa i mondi: quel luogo è su un altro piano."
    entities.move_player(conn, player.id, target["id"])
    return f"🌌 Passo nel Vuoto: lo spazio si piega come carta, e sei a {target['name']}."


def _a_taglio(conn, player, rest, d) -> str:
    d["buffs"]["taglio"] = True
    return "🌌 Raccogli il vuoto sul filo della tua arte: il prossimo scontro, la difesa del nemico non conterà."


def _here_enemies(conn, player) -> list:
    return conn.execute("SELECT id, name FROM npcs WHERE location_id=? AND status='alive';",
                        (player.location_id,)).fetchall()


def _a_prigione(conn, player, rest, d) -> str:
    rows = _here_enemies(conn, player)
    if not rows:
        return "✗ Non c'è nessuno qui da imprigionare."
    for r in rows:
        d["debuff"][str(r["id"])] = [_day(conn) + 3, 0.67]
    return (f"🌌 Prigione Spaziale: lo spazio attorno a {len(rows)} presenti si fa vetro. "
            "Per tre giorni si muovono come in un sogno (−33% forza).")


def _a_mondo(conn, player, rest, d) -> str:
    d["small_world"] = True
    state.grant_title(conn, "Creatore di un Piccolo Mondo")
    return ("🌌 Apri una piega nel vuoto e vi soffi dentro il tuo Dao: nasce un PICCOLO MONDO, con un cielo "
            "tuo e leggi tue. Lì il qi ti obbedisce: coltivazione +15%, per sempre.")


def _a_domani(conn, player, rest, d) -> str:
    return "⏳ Occhio del Domani — " + "\n".join(foresight(conn, player))


def _a_camera(conn, player, rest, d) -> str:
    from engine.systems import items, lifespan
    i = idx(conn, "tempo", player.id)
    years = max(1, 6 - i // 2)
    lifespan.add_bonus_years(conn, -years)
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 13 + player.id)
    lines = items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": 0.25 + 0.08 * i})
    return (f"⏳ Camera del Tempo: dentro scorre un anno, fuori un giorno. Ne esci con la barba più lunga "
            f"e il qi più denso (−{years} anni di vita).\n" + "\n".join(lines))


def _a_rallenta(conn, player, rest, d) -> str:
    d["buffs"]["rallenta"] = True
    return "⏳ Prepari il Tempo come una trappola: il prossimo scontro scorrerà lento per tutti, tranne te."


def _a_leggi(conn, player, rest, d) -> str:
    from engine.systems import perception, karma, pursuers
    rows = _here_enemies(conn, player)
    if not rows:
        return "✗ Qui non c'è nessun filo da leggere."
    hunters = dict(pursuers.tracked(conn))
    out = ["🎲 Leggi i fili del fato di chi ti sta intorno:"]
    for r in rows[:8]:
        k = karma.get_karma(conn, "npc", r["id"]) if hasattr(karma, "get_karma") else 0
        k_txt = "karma luminoso" if k > 50 else "karma oscuro" if k < -50 else "karma tiepido"
        tag = f" — ⚠ ti dà la caccia ({hunters[r['id']]})" if r["id"] in hunters else ""
        out.append(f"  · {r['name']}: {perception.relative_strength(conn, player.id, r['id'])}, {k_txt}{tag}")
    return "\n".join(out)


def _a_benedici(conn, player, rest, d) -> str:
    d["blessing"] = d["blessing"] + 3
    return "🎲 Pieghi la fortuna come un ramo giovane: i prossimi tre bottini saranno migliori di quanto dovrebbero."


def _a_recidi(conn, player, rest, d) -> str:
    rows = _here_enemies(conn, player)
    if rest:
        rows = [r for r in rows if rest.lower() in r["name"].lower()]
    if not rows:
        return "✗ Di chi vuoi recidere il fato? (deve essere qui: «arcano recidi <nome>»)"
    r = rows[0]
    d["debuff"][str(r["id"])] = [_day(conn) + 5, 0.6]
    return (f"🎲 Trovi il filo del fato di {r['name']} e lo recidi. Per cinque giorni la sua fortuna è "
            "polvere: −40% forza.")


_ARCANE_FN = {"passo": _a_passo, "taglio": _a_taglio, "prigione": _a_prigione, "mondo": _a_mondo,
              "domani": _a_domani, "camera": _a_camera, "rallenta": _a_rallenta, "leggi": _a_leggi,
              "benedici": _a_benedici, "recidi": _a_recidi}


def foresight(conn, player) -> list[str]:
    """Chi arriverà, e quando: nemesi, vendicatori, cacciatori, arcinemico, tribolazioni."""
    out = []
    t = tick_mod.get_tick(conn)
    day = t // 120
    try:
        from engine.systems import bonds
        for nm in bonds.nemeses(conn, player.id):
            dd = max(0, (nm["ready_tick"] - t) // 120)
            out.append(f"  ☠ la nemesi {nm['name']}: " + ("è già sulle tue tracce" if dd == 0 else f"tra {dd} giorni"))
    except Exception:
        pass
    try:
        from engine.systems import feuds
        for f in feuds.feuds(conn):
            dd = max(0, (f["ready_day"] or 0) - day)
            out.append(f"  🩸 {f['name']} ({f['relation']} di {f['victim_name']}): "
                       + ("ti cerca già" if dd == 0 else f"partirà tra {dd} giorni"))
    except Exception:
        pass
    for r in conn.execute("SELECT n.name, l.name AS lname FROM npcs n LEFT JOIN locations l ON l.id=n.location_id "
                          "WHERE n.hunting=1 AND n.status='alive';"):
        out.append(f"  ⚔ {r['name']} ti dà la caccia (ora a {r['lname'] or '?'})")
    try:
        from engine.systems import archrival
        a = archrival.get(conn)
        if a:
            out.append(f"  ⚡ l'arcinemico {a.get('name', '?')}: tornerà tra {max(0, a['next_day'] - day)} giorni")
    except Exception:
        pass
    from engine.systems import dao_powers
    if dao_powers.tribulation_due(conn, player.id) > 0:
        out.append("  ⚡ una tribolazione divina è già sopra di te")
    else:
        dfy = dao_powers.heaven_defiance(conn, player.id)
        nxt = (dfy // dao_powers.DEFIANCE_STEP + 1) * dao_powers.DEFIANCE_STEP
        out.append(f"  ⚡ prossima tribolazione divina a Sfida {nxt} (ora {dfy})")
    return out or ["  Nessuno ti cerca. Per ora."]


# ---------------------------------------------------------------- la guerra con il Cielo

def chapter_of(defiance: int) -> int:
    n = 0
    for i, (th, _n, _t) in enumerate(CHAPTERS):
        if defiance >= th:
            n = i
    return n


def judgment_level(defiance: int) -> int:
    """0 = nessun Giudizio; poi 1, 2, 3… a ogni raddoppio oltre 600 (senza fine)."""
    if defiance < JUDGMENT_BASE:
        return 0
    return 1 + int(math.log2(defiance / JUDGMENT_BASE))


def _ordinal(n: int) -> str:
    return ["", "Primo", "Secondo", "Terzo", "Quarto", "Quinto", "Sesto", "Settimo", "Ottavo", "Nono"][n] \
        if n < 10 else f"{n}°"


def messenger_ids(conn) -> list[int]:
    d = state.get_json(conn, KEY, None) or {}
    ids = list(d.get("messengers", []))
    if d.get("will_npc"):
        ids.append(d["will_npc"])
    return ids


def _spawn_heaven_npc(conn, rng, player, title: str, band: str) -> int:
    from engine.systems import npc_factory, pursuers
    from engine.simulation import cultivation
    pt = cultivation.realm_tier(conn, "player", player.id) or 1
    loc = conn.execute("SELECT id FROM locations WHERE id<>? ORDER BY RANDOM() LIMIT 1;",
                       (player.location_id,)).fetchone()
    nid = npc_factory.spawn(conn, rng, archetype="anziano", location_id=loc["id"] if loc else player.location_id,
                            tier=pt, stage=rng.randint(5, 9),
                            traits={"pride": 90, "courage": 95, "honor": 70, "loyalty": 100})
    given = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"].split()[-1]
    name = f"{title} {given}"
    if conn.execute("SELECT 1 FROM npcs WHERE name=?;", (name,)).fetchone():
        name = f"{title} {given} {nid}"
    conn.execute("UPDATE npcs SET name=?, hunting=1, description=? WHERE id=?;",
                 (name, "Un esecutore delle leggi del Cielo: il suo sguardo pesa come una sentenza.", nid))
    pursuers.on_spawn(conn, player.id, nid, band)
    if band == "campione" and title.startswith("Volontà"):
        pursuers.fit(conn, player.id, nid, band, target=1.3)
    return nid


def judgment_scene(conn, level: int) -> dict:
    o = _ordinal(level)
    return {"key": "giudizio_cielo", "title": f"⚡ Il {o} Giudizio del Cielo", "event_type": "story",
            "text": ("Le nubi si aprono come un libro. Una voce senza bocca pronuncia il tuo nome — quello vero, "
                     "quello che nemmeno tu ricordi. «Hai toccato leggi che non ti appartengono. Rispondi.»"),
            "ctx": {}, "sticky": True,
            "choices": [
                {"label": "Ti pieghi: restituisci al Cielo parte di ciò che hai preso", "effects": {},
                 "command": "cielo sottometti"},
                {"label": "Lo sfidi: che scenda la Volontà del Cielo, e la abbatterai", "effects": {},
                 "command": "cielo sfida"},
                {"label": "Lo inganni: nascondi il tuo fato tra mille fati mortali (Destino «esperto»)", "effects": {},
                 "command": "cielo inganna"}]}


def daily(conn, t: int, rng, player) -> list[str]:
    if player is None:
        return []
    from engine.systems import dao_powers, encounters, chronicle
    d = get(conn)
    day = t // 120
    out = []
    # pulizia degli indebolimenti scaduti
    d["debuff"] = {k: v for k, v in d["debuff"].items() if v[0] >= day}
    dfy = dao_powers.heaven_defiance(conn, player.id)
    ch = chapter_of(dfy)
    if ch > d["chapter"]:
        d["chapter"] = ch
        _th, name, txt = CHAPTERS[ch]
        out.append(f"⚡ LA GUERRA CON IL CIELO — {name}. {txt}")
        chronicle.add(conn, "svolta", f"La guerra con il Cielo: {name}.")
    hidden = day <= d["hidden_until"]
    # i Messaggeri caduti lasciano Frammenti della Legge
    alive = []
    for nid in d["messengers"]:
        r = conn.execute("SELECT status, name FROM npcs WHERE id=?;", (nid,)).fetchone()
        if r and r["status"] == "alive":
            alive.append(nid)
        elif r:
            out += _fragment(conn, player, rng, r["name"])
    d["messengers"] = alive
    # la Volontà del Cielo abbattuta: un Sigillo della Sfida
    if d["will_npc"]:
        r = conn.execute("SELECT status FROM npcs WHERE id=?;", (d["will_npc"],)).fetchone()
        if not r or r["status"] != "alive":
            d["will_npc"] = None
            d["seals"] += 1
            titles = ["Colui che Sfidò il Cielo", "Spezzatore di Sentenze", "Nemico delle Nove Nubi",
                      "Colui che il Cielo Teme"]
            ttl = titles[min(len(titles) - 1, d["seals"] - 1)] if d["seals"] <= len(titles) else f"Sfidante del Cielo ({d['seals']})"
            state.grant_title(conn, ttl)
            out.append(f"⚡ La Volontà del Cielo si disfa in pioggia di luce. Un SIGILLO DELLA SFIDA ti si imprime "
                       f"nell'anima ({d['seals']}): la tua forza cresce. Titolo: {ttl}.")
            chronicle.add(conn, "svolta", f"Abbatti la Volontà del Cielo: Sigillo della Sfida n.{d['seals']}.")
    # nuovi Messaggeri
    if ch >= 3 and not hidden and not d["messengers"] and day - d["msg_day"] >= MESSENGER_EVERY:
        d["msg_day"] = day
        nid = _spawn_heaven_npc(conn, rng, player, rng.choice(_HEAVEN_NAMES), "campione")
        d["messengers"].append(nid)
        nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        out.append(f"⚡ {nm} scende dalle nubi con il tuo nome inciso su una tavola di giada. Ti dà la caccia.")
    # il Giudizio
    lvl = judgment_level(dfy)
    if lvl > d["judgments"] and not hidden and not d["pending_judgment"] and not encounters.pending(conn):
        d["pending_judgment"] = True
        _save(conn, d)
        txt = encounters.start_scene(conn, player, judgment_scene(conn, lvl))
        if txt:
            out.append(txt)
        return out
    _save(conn, d)
    return out


def _fragment(conn, player, rng, who: str) -> list[str]:
    key = rng.choice(DEEP)
    from engine.systems import items
    t = tick_mod.get_tick(conn)
    lines = items.apply_effects(conn, t, rng, player.id, {"dao_key": key, "dao_gain": 6})
    return [f"⚡ Da ciò che resta di {who} raccogli un FRAMMENTO DELLA LEGGE: il Dao {DEEP_NAME[key]} si fa più chiaro."] + lines


def heaven_command(conn, player, arg: str) -> str:
    a = (arg or "").strip().lower()
    d = get(conn)
    from engine.systems import dao_powers
    dfy = dao_powers.heaven_defiance(conn, player.id)
    lvl = judgment_level(dfy)
    if not a or a in ("stato", "info"):
        return describe(conn, player)
    if not d["pending_judgment"]:
        return "Il Cielo non ti ha chiamato a giudizio. Per ora."
    rng = random.Random(tick_mod.get_tick(conn) * 7 + player.id)
    if a.startswith("sotto") or a.startswith("pieg"):
        from engine.systems import dao_heart
        for k in DEEP:
            c = comp(conn, k, player.id)
            if c:
                conn.execute("UPDATE character_daos SET comprehension=? WHERE character_type='player' "
                             "AND character_id=? AND dao_key=?;", (int(c * 0.85), player.id, k))
        try:
            dao_heart.adjust(conn, 8)
        except Exception:
            pass
        d["judgments"] = lvl
        d["pending_judgment"] = False
        d["hidden_until"] = _day(conn) + 30
        _save(conn, d)
        return ("Chini il capo. Il Cielo prende ciò che è suo: i tuoi Dao profondi si fanno più opachi (−15%). "
                "Ma il cuore si quieta, e per un mese nessun Messaggero ti cerca.")
    if a.startswith("sfid"):
        nid = _spawn_heaven_npc(conn, rng, player, "Volontà del Cielo", "campione")
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, nid))
        d["will_npc"] = nid
        d["judgments"] = lvl
        d["pending_judgment"] = False
        _save(conn, d)
        nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        return (f"Alzi lo sguardo e rifiuti. Il cielo si spacca e ne scende {nm}: il Cielo stesso, con un volto. "
                f"È qui. Abbattila («attack {nm.split()[0]}» o «duello {nm.split()[0]}») per un Sigillo della Sfida.")
    if a.startswith("ingann"):
        if idx(conn, "destino", player.id) < 3:
            return "Il tuo Destino non è abbastanza profondo per ingannare il Cielo (serve «esperto»)."
        d["judgments"] = lvl
        d["pending_judgment"] = False
        d["hidden_until"] = _day(conn) + 60
        _save(conn, d)
        return ("Disfi il tuo fato in mille fili e lo nascondi tra quelli dei mortali. Il Cielo cerca, non trova, "
                "e dimentica: per due mesi niente Messaggeri e niente Giudizio. Ma il debito resta.")
    return "Rispondi con: cielo sottometti · cielo sfida · cielo inganna"


# ---------------------------------------------------------------- pannello e menu

def describe(conn, player) -> str:
    m = menu_build(conn, player)
    from engine.systems import menus
    return menus.render(conn, m) if hasattr(menus, "render") else m["title"]


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import dao_powers, dao_training as dt
    secs = []
    for k in DEEP:
        c = comp(conn, k, player.id)
        i = idx(conn, k, player.id)
        nxt = dt.DAO_THRESHOLDS[i + 1][0] if i + 1 < len(dt.DAO_THRESHOLDS) else None
        prev = dt.DAO_THRESHOLDS[i][0]
        pct = 100 if nxt is None else 100 * (c - prev) / max(1, nxt - prev)
        label = {"spazio": dao_powers.space_combat(conn, player.id)["label"],
                 "tempo": dao_powers.time_label(conn, player.id),
                 "destino": dao_powers.fate_label(conn, player.id)}[k]
        lines = [f"Comprensione {c} — {dt.comprehension_label(c)}" + (f" · mistero: {label}" if label else "")]
        acts = []
        for ak, (dao, need, name, desc, cd, _cost) in ARCANA.items():
            if dao != k:
                continue
            ok, why = _available(conn, ak, player.id)
            if cd == -2:
                lines.append(f"{'✔' if i >= need else '·'} {name} — {desc}")
                continue
            acts.append(act(f"{name} — {desc}", f"arcano {ak}", ok, why))
        secs.append(section(f"Dao {DEEP_NAME[k]}", lines, acts,
                            [bar(DEEP_NAME[k], pct, f"{c} → {nxt}" if nxt else f"{c}", tone="info")], icon=ICON[k]))
    res = resonances(conn, player.id)
    secs.append(section("Risonanze", [f"✦ {n} — {e}" for n, e, _f in res] or [
        "Porta due Dao profondi a «maestro» per farli risuonare: Spazio+Tempo, Tempo+Destino, Spazio+Destino. "
        "Tutti e tre a «gran maestro»: la Trinità delle Leggi."], icon="✦"))
    d = get(conn)
    dfy = dao_powers.heaven_defiance(conn, player.id)
    ch = chapter_of(dfy)
    nxt_ch = next((th for th, _n, _t in CHAPTERS if th > dfy), None)
    lvl = judgment_level(dfy)
    nxt_j = JUDGMENT_BASE * 2 ** lvl
    lines = [f"Sfida al Cielo: {dfy} — {dao_powers.defiance_label(dfy)}",
             f"Capitolo: {CHAPTERS[ch][1]} — {CHAPTERS[ch][2]}",
             f"Sigilli della Sfida: {d['seals']}" + (f" (forza ×{seal_mult(conn):.2f})" if d["seals"] else ""),
             f"Giudizi affrontati: {d['judgments']} · il prossimo a Sfida {nxt_j}"]
    if d["small_world"]:
        lines.append("🌌 Il tuo Piccolo Mondo esiste: coltivazione +15%.")
    if _day(conn) <= d["hidden_until"]:
        lines.append(f"🎲 Il tuo fato è nascosto: il Cielo non ti trova fino al giorno {d['hidden_until']}.")
    if d["messengers"]:
        lines.append(f"⚔ Messaggeri del Cielo sulle tue tracce: {len(d['messengers'])}")
    acts = [act("Affronta la tribolazione divina", "tribulation", dao_powers.tribulation_due(conn, player.id) > 0,
                "nessuna tribolazione incombe")]
    if d["pending_judgment"]:
        acts += [act("Piegati al Giudizio", "cielo sottometti"), act("Sfida la Volontà del Cielo", "cielo sfida", main=True),
                 act("Inganna il Cielo", "cielo inganna", idx(conn, "destino", player.id) >= 3, "serve Destino «esperto»")]
    bars = [bar("Verso il prossimo capitolo", 100 if nxt_ch is None else 100 * dfy / nxt_ch,
                f"{dfy}/{nxt_ch}" if nxt_ch else "tutti i capitoli", tone="bad")]
    secs.append(section("La guerra con il Cielo", lines, acts, bars, icon="⚡"))
    return menu("profondi", "🌌⏳🎲 I TRE DAO PROFONDI",
                ["Spazio distrugge, Tempo fa crescere, Destino piega la sorte. Insieme sfidano il Cielo."], secs)


def command(conn, player, arg: str) -> str:
    from engine.systems import menus
    return menus.show(conn, player, "profondi")
