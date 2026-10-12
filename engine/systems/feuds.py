"""
RANCORI E DEBITI (恩怨) — chi uccidi lascia qualcuno; chi risparmi, anche.

Nei romanzi di arti marziali nessuno muore da solo: ogni vittima ha un padre, un fratello, un
maestro, una setta. E ogni nemico risparmiato porta con sé un debito di vita che, un giorno,
qualcuno ripagherà. Questo sistema tiene il LIBRO DEI RANCORI E DEI DEBITI.

UCCIDERE (un umano)
  · Chi gli era legato può GIURARE VENDETTA: padre o madre (più forti), fratelli (pari),
    figli (più deboli, ma crescono in fretta: il figlio che torna dopo anni è il più temibile),
    il maestro, un fratello giurato, e — se era un anziano o un patriarca — la sua SETTA.
  · Quanti e quanto accaniti dipende da chi era: chi uccide un ricercato o un predone non
    lascia quasi rancori (anzi: la sua famiglia se ne vergogna); chi uccide un anziano rispettato
    ne lascia molti.
  · Se agivi MASCHERATO e senza testimoni, i vendicatori non sanno chi cercare: ci mettono molto
    di più, e a volte non lo scoprono mai.
  · Ogni vendicatore si allena, poi viene a cercarti. Puoi:
        duellare (se lo uccidi, la faida passa alla generazione successiva — al massimo tre),
        risarcire (pietre: se il rancore non è troppo profondo, la faida si chiude),
        spiegare (se la vittima aveva torto, la verità può chiudere il conto),
        andartene (il rancore cresce).
    Se lo sconfiggi e lo RISPARMI, a volte il rancore si spegne per sempre.

RISPARMIARE (scegliere di non finire chi hai battuto)
  · Nasce un DEBITO DI VITA. Chi ha onore e compassione lo ripagherà: un dono, un'informazione,
    o arriverà a combattere al tuo fianco nel momento peggiore. La sua famiglia e la sua setta
    ti guardano con occhi diversi.
  · Chi è troppo orgoglioso, invece, può vivere il perdono come un'umiliazione (vedi le nemesi).

  faide               il Libro dei Rancori e dei Debiti
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

REL_LABEL = {"padre": "il padre", "madre": "la madre", "fratello": "il fratello", "sorella": "la sorella",
             "figlio": "il figlio", "figlia": "la figlia", "maestro": "il maestro", "giurato": "il fratello giurato",
             "setta": "la setta", "allievo": "l'allievo"}
FEMALE = {"madre", "sorella", "figlia"}
# relazione -> (scarto di regno rispetto alla vittima, ardore iniziale, giorni prima di partire)
REL = {"padre": (1, 85, (8, 25)), "madre": (1, 80, (8, 25)), "fratello": (0, 75, (5, 18)),
       "sorella": (0, 70, (5, 18)), "figlio": (-1, 95, (30, 70)), "figlia": (-1, 90, (30, 70)),
       "maestro": (1, 70, (10, 30)), "giurato": (0, 65, (5, 20)), "setta": (2, 60, (10, 30)),
       "allievo": (-1, 80, (20, 50))}
MAX_GEN = 3


def ensure_table(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS feuds ("
                 "id INTEGER PRIMARY KEY, kind TEXT NOT NULL, npc_id INTEGER NOT NULL, victim_id INTEGER, "
                 "victim_name TEXT, relation TEXT, intensity INTEGER DEFAULT 50, status TEXT DEFAULT 'giurata', "
                 "knows INTEGER DEFAULT 1, gen INTEGER DEFAULT 1, since_tick INTEGER DEFAULT 0, "
                 "ready_day INTEGER DEFAULT 0, place TEXT, note TEXT);")


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _rows(conn, kind: str, active: bool = True) -> list:
    ensure_table(conn)
    q = "SELECT f.*, n.name, n.status AS alive, n.location_id FROM feuds f JOIN npcs n ON n.id=f.npc_id WHERE f.kind=?"
    if active:
        q += " AND f.status IN ('giurata','in caccia','ignoto','debito','alleato')"
    return conn.execute(q + " ORDER BY f.intensity DESC;", (kind,)).fetchall()


def feuds(conn, active: bool = True) -> list:
    return [r for r in _rows(conn, "faida", active) if not active or r["alive"] == "alive"]


def debts(conn, active: bool = True) -> list:
    return [r for r in _rows(conn, "debito", active) if not active or r["alive"] == "alive"]


def avenger_ids(conn) -> set[int]:
    return {r["npc_id"] for r in feuds(conn)}


def ally_ids(conn) -> set[int]:
    return {r["npc_id"] for r in debts(conn)}


# ============================================================ chi piange la vittima

def _fac(conn, npc_id: int) -> int | None:
    r = conn.execute("SELECT faction_id FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    return r["faction_id"] if r else None


def _prominence(conn, npc) -> tuple[int, float]:
    """(quanti possono giurare vendetta, moltiplicatore dell'ardore) secondo chi era la vittima."""
    from engine.simulation import cultivation
    out = conn.execute("SELECT 1 FROM outlaws WHERE npc_id=?;", (npc.id,)).fetchone()
    arch = (npc.archetype or "")
    tier = cultivation.realm_tier(conn, "npc", npc.id) or 1
    if out or arch in ("predone", "bandito"):
        return 1, 0.35                              # la famiglia di un predone se ne vergogna
    n = 1 + (1 if tier >= 3 else 0) + (1 if arch in ("anziano", "patriarca", "eremita") else 0)
    return min(4, n), 1.0 + (0.3 if arch in ("anziano", "patriarca") else 0.0)


def _pick_relations(rng, npc, n: int, fac: int | None = None) -> list[str]:
    pool = ["padre", "madre", "fratello", "sorella", "figlio", "figlia", "maestro", "giurato", "allievo"]
    w = [3, 2, 4, 3, 3, 2, 2, 2, 1]
    if (npc.archetype or "") in ("anziano", "patriarca") and fac:
        out = ["setta"]
        n -= 1
    else:
        out = []
    while len(out) < n + (1 if out else 0) and pool:
        r = rng.choices(pool, weights=w)[0]
        i = pool.index(r)
        pool.pop(i)
        w.pop(i)
        out.append(r)
    return out


def _spawn_avenger(conn, rng, victim, relation: str) -> int:
    from engine.systems import npc_factory
    from engine.simulation import cultivation
    tier = max(1, (cultivation.realm_tier(conn, "npc", victim.id) or 1) + REL[relation][0])
    home = None
    vfac = _fac(conn, victim.id)
    if vfac:
        r = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (vfac,)).fetchone()
        home = r["home_location_id"] if r else None
    here = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    if home is None or home == here:              # il vendicatore non è sulla scena: arriverà, più tardi
        r = conn.execute("SELECT id FROM locations WHERE location_type='city' AND id<>? ORDER BY RANDOM() LIMIT 1;",
                         (here,)).fetchone()
        home = r["id"] if r else victim.location_id
    arch = {"maestro": "anziano", "setta": "anziano", "padre": "guardia", "madre": "eremita"}.get(relation, "discepolo")
    surname = victim.name.split()[0]
    nid = npc_factory.spawn(conn, rng, archetype=arch, location_id=home, tier=tier,
                            stage=rng.randint(4, 9), faction_id=vfac,
                            traits={"pride": 75, "courage": 80, "loyalty": 90},
                            **({"gender": "f"} if relation in FEMALE else {}))
    if relation in REL_LABEL and relation not in ("maestro", "setta", "giurato", "allievo"):
        # stessa famiglia, stesso cognome
        r = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()
        given = r["name"].split()[-1]
        conn.execute("UPDATE npcs SET name=? WHERE id=?;", (f"{surname} {given}", nid))
    return nid


def on_kill(conn, t: int, rng: random.Random, player, npc) -> list[str]:
    """Hai ucciso un umano: chi giurerà vendetta?"""
    ensure_table(conn)
    r = conn.execute("SELECT kind, war_id FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if not r or (r["kind"] not in (None, "human")):
        return []
    lines = []
    # il vendicatore stesso è caduto: la faida passa alla generazione successiva
    mine = conn.execute("SELECT * FROM feuds WHERE kind='faida' AND npc_id=? AND status IN "
                        "('giurata','in caccia','ignoto');", (npc.id,)).fetchone()
    gen = 1
    if mine:
        conn.execute("UPDATE feuds SET status='vendicata', note='caduto per mano tua' WHERE id=?;", (mine["id"],))
        gen = mine["gen"] + 1
        if gen > MAX_GEN:
            state.grant_title(conn, "Colui che Spezzò una Stirpe")
            lines.append(f"Con {npc.name} si estingue la faida della famiglia {mine['victim_name'].split()[0]}: "
                         "nessuno resta a pronunciare il tuo nome con odio.")
            return lines
    n, mult = _prominence(conn, npc)
    if r["war_id"]:
        mult *= 0.6                                  # in guerra si muore: il rancore è più tiepido
    from engine.systems import reputation
    masked = reputation.is_disguised(conn, player.id)
    witnesses = conn.execute("SELECT COUNT(*) c FROM npcs WHERE location_id=? AND status='alive' AND id<>? "
                             "AND (kind='human' OR kind IS NULL);", (player.location_id, npc.id)).fetchone()["c"]
    knows = 0 if (masked and witnesses == 0) else 1
    lname = conn.execute("SELECT name FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    place = lname["name"] if lname else "un luogo lontano"
    sworn = []
    for rel in _pick_relations(rng, npc, n, _fac(conn, npc.id)):
        chance = min(0.95, 0.55 * mult + 0.1 * gen)
        if rng.random() > chance:
            continue
        aid = _spawn_avenger(conn, rng, npc, rel)
        lo, hi = REL[rel][2]
        inten = int(min(100, REL[rel][1] * mult + 10 * (gen - 1)))
        ready = _day(conn) + rng.randint(lo, hi) * (2 if not knows else 1)
        conn.execute("INSERT INTO feuds (kind, npc_id, victim_id, victim_name, relation, intensity, status, knows, "
                     "gen, since_tick, ready_day, place) VALUES ('faida', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                     (aid, npc.id, npc.name, rel, inten, "giurata" if knows else "ignoto", knows, gen, t,
                      ready, place))
        sworn.append((aid, rel))
    if sworn:
        names = []
        for aid, rel in sworn:
            nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (aid,)).fetchone()["name"]
            names.append(f"{REL_LABEL.get(rel, rel)} {nm}" if rel != "setta" else f"la sua setta (l'anziano {nm})")
        if knows:
            lines.append(f"🩸 La morte di {npc.name} non resterà senza risposta: " + ", ".join(names) +
                         " giura vendetta. ('faide')")
        else:
            lines.append(f"🩸 Nessuno ti ha visto. Ma {', '.join(names)} giura di trovare chi ha ucciso "
                         f"{npc.name}. ('faide')")
        from engine.systems import chronicle
        chronicle.add(conn, "nemico", f"Uccide {npc.name}: " + ", ".join(names) + " giura vendetta.")
    return lines


def on_spare(conn, t: int, rng: random.Random, player, npc, chosen: bool) -> list[str]:
    """Hai battuto qualcuno e non l'hai finito. Se è stata una scelta, nasce un debito di vita."""
    ensure_table(conn)
    r = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if not r or r["kind"] not in (None, "human"):
        return []
    # un vendicatore risparmiato a volte depone il rancore
    f = conn.execute("SELECT * FROM feuds WHERE kind='faida' AND npc_id=? AND status IN "
                     "('giurata','in caccia','ignoto');", (npc.id,)).fetchone()
    tr = entities.get_npc_traits(conn, npc.id) or {}
    if f:
        p_end = 0.25 + 0.004 * tr.get("honor", 50) + 0.003 * tr.get("compassion", 50) - 0.004 * f["intensity"]
        if chosen and rng.random() < max(0.1, p_end):
            conn.execute("UPDATE feuds SET status='riconciliata', note='risparmiato, ha deposto la spada' "
                         "WHERE id=?;", (f["id"],))
            return [f"☯ {npc.name} resta in ginocchio a lungo. Poi posa la spada: «Mio {_short(f['relation'])} "
                    f"non tornerà. Ma tu mi hai lasciato vivere. La faida finisce con me.»"]
        conn.execute("UPDATE feuds SET intensity=MIN(100, intensity+10), ready_day=? WHERE id=?;",
                     (_day(conn) + rng.randint(15, 40), f["id"]))
        return [f"{npc.name} fugge con l'odio negli occhi: «Questa non è pietà, è un insulto. Tornerò.»"]
    if not chosen:
        return []
    gratitude = int(30 + 0.4 * tr.get("honor", 50) + 0.3 * tr.get("compassion", 50) - 0.25 * tr.get("pride", 50))
    if gratitude < 35:
        return []
    conn.execute("INSERT INTO feuds (kind, npc_id, victim_name, relation, intensity, status, since_tick, ready_day, "
                 "place) VALUES ('debito', ?, ?, 'vita', ?, 'debito', ?, ?, ?);",
                 (npc.id, npc.name, min(100, gratitude), t, _day(conn) + rng.randint(6, 30),
                  (conn.execute("SELECT name FROM locations WHERE id=?;", (player.location_id,)).fetchone() or
                   {"name": "?"})["name"]))
    _family_warms(conn, npc, +12)
    return [f"🤝 {npc.name} ti guarda come si guarda chi poteva ucciderti e non l'ha fatto: «Ti devo la vita. "
            f"Non lo dimenticherò.» (debito di vita — 'faide')"]


def _short(rel: str) -> str:
    return {"padre": "figlio", "madre": "figlio", "fratello": "fratello", "sorella": "fratello",
            "figlio": "padre", "figlia": "padre", "maestro": "allievo", "allievo": "maestro"}.get(rel, "amico")


def _family_warms(conn, npc, delta: int) -> None:
    """La setta di chi risparmi ti guarda con occhi diversi."""
    fac = _fac(conn, npc.id)
    if not fac:
        return
    state.set(conn, f"faction_goodwill_{fac}", str(state.get_int(conn, f"faction_goodwill_{fac}", 0) + delta))


# ============================================================ ogni giorno

_HUNT_TEXT = {
    "padre": "Un uomo dai capelli grigi ti sbarra la strada. Non trema. «{victim} era mio figlio. Lo hai ucciso a {place}. "
             "Ho seppellito mio figlio: oggi seppellisco te.»",
    "madre": "Una donna in bianco da lutto ti aspetta in mezzo alla via. «{victim}. Ripeti quel nome, assassino. "
             "Ripetilo mentre muori.»",
    "fratello": "«Ti ricordi di {victim}?» Il giovane che ti si para davanti ha i suoi stessi occhi. «Io sì. Ogni notte.»",
    "sorella": "Una ragazza dalla spada sottile ti chiama per nome. «{victim} era mio fratello. Non andrai oltre questo ponte.»",
    "figlio": "Un giovane uomo ti attende, cresciuto di colpo, con una cicatrice che non hai fatto tu. «Avevo dodici anni "
              "quando hai ucciso mio padre, {victim}, a {place}. Ho passato ogni giorno da allora a prepararmi a questo.»",
    "figlia": "«Mio padre era {victim}.» La giovane donna sfila la spada lentamente, come una preghiera. «Mi chiamava "
              "il suo piccolo fiore. Il fiore è cresciuto.»",
    "maestro": "Un anziano dalla barba bianca scende dal cielo davanti a te. «{victim} era il mio miglior allievo. "
               "Hai spezzato un ramo del mio albero: ora l'albero ti cade addosso.»",
    "giurato": "«Avevamo giurato sotto lo stesso cielo, {victim} e io: nati in giorni diversi, morire nello stesso.» "
               "Lo sconosciuto snuda l'arma. «Tu gli hai rubato quel giorno.»",
    "setta": "Sette discepoli in tunica ti circondano; un anziano avanza. «{victim} era un anziano della nostra setta. "
             "La setta non dimentica: oggi paghi davanti a tutti.»",
    "allievo": "«Maestro {victim}...» Il giovane che ti fronteggia ha imparato da un morto. «Mi hai lasciato solo una cosa "
               "da imparare: come ucciderti.»",
}


def _cost(conn, f) -> int:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", 1) or 1
    return int(f["intensity"] * 4 * tier * f["gen"])


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import npc_factory, encounters
    ensure_table(conn)
    out = []
    day = _day(conn)
    for f in feuds(conn):
        # i vendicatori si allenano (i figli più di tutti)
        if rng.random() < (0.35 if f["relation"] in ("figlio", "figlia", "allievo") else 0.2):
            npc_factory.raise_npc(conn, f["npc_id"], 1)
        if f["status"] == "ignoto":
            if day >= f["ready_day"] and rng.random() < 0.08:
                conn.execute("UPDATE feuds SET status='giurata', knows=1, ready_day=? WHERE id=?;",
                             (day + rng.randint(3, 10), f["id"]))
                out.append(f"🩸 Voci da {f['place']}: {f['name']} ha scoperto chi ha ucciso {f['victim_name']}.")
            continue
        if day < f["ready_day"] or encounters.pending(conn):
            continue
        sc = scene(conn, player, f)
        txt = encounters.start_scene(conn, player, sc)
        if txt:
            _bring_here(conn, player, f)             # ti ha trovato: è qui, davanti a te
            conn.execute("UPDATE feuds SET status='in caccia' WHERE id=?;", (f["id"],))
            out.append(txt)
            break
    # i debiti di vita si ripagano
    for d in debts(conn):
        if d["status"] != "debito" or day < d["ready_day"]:
            continue
        out += _repay(conn, rng, player, d)
        break
    return out


def scene(conn, player, f) -> dict:
    """La scena del vendicatore: duello, risarcimento, verità, fuga."""
    name = f["name"]
    first = name.split()[0]
    cost = _cost(conn, f)
    text = _HUNT_TEXT.get(f["relation"], _HUNT_TEXT["fratello"]).format(victim=f["victim_name"], place=f["place"])
    if f["gen"] > 1:
        text += f"\n(È la {f['gen']}ª generazione di questa faida: il sangue chiama sangue.)"
    victim_bad = conn.execute("SELECT 1 FROM outlaws WHERE npc_id=?;", (f["victim_id"] or -1,)).fetchone()
    choices = [
        {"label": f"Accetti la sfida: duello a turni con {name}", "effects": {}, "command": f"duello {first}"},
        {"label": f"Offri un risarcimento ({cost} pietre) e le tue scuse", "effects": {},
         "command": f"faide risarcisci {f['id']}"},
        {"label": "Gli racconti com'è andata davvero", "effects": {}, "command": f"faide verita {f['id']}"},
        {"label": "Te ne vai senza combattere (il suo odio crescerà)", "effects": {}, "command": f"faide fuggi {f['id']}"},
    ]
    if victim_bad:
        choices[2]["label"] += " (era un ricercato: hai la verità dalla tua)"
    return {"key": "vendetta", "title": f"Faida: {REL_LABEL.get(f['relation'], '')} di {f['victim_name']}",
            "event_type": "combat", "sticky": True, "text": text, "choices": choices,
            "ctx": {"npc_id": f["npc_id"], "npc_name": name}}


def _bring_here(conn, player, f) -> None:
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, f["npc_id"]))


def _repay(conn, rng, player, d) -> list[str]:
    from engine.systems import items, sects
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    kind = rng.choice(["dono", "dono", "segreto", "alleato"])
    if kind == "alleato" or d["intensity"] >= 75:
        conn.execute("UPDATE feuds SET status='alleato', note='al tuo fianco nel momento del bisogno' WHERE id=?;",
                     (d["id"],))
        return [f"🤝 {d['name']}, che risparmiasti a {d['place']}, ti manda a dire: «Il giorno in cui avrai "
                f"bisogno di me, ci sarò.» (accorrerà nelle battaglie difficili)"]
    conn.execute("UPDATE feuds SET status='saldato', note=? WHERE id=?;",
                 ("ha ripagato con un dono" if kind == "dono" else "ha ripagato con un segreto", d["id"]))
    if kind == "dono":
        n = 60 * tier
        sects.grant_resource(conn, "pietre_spirituali", n, player.id)
        iid = items.create_item(conn, "Pillola della Gratitudine", "pillola", "raro",
                                "Un dono di chi ti deve la vita.", {"cultivation_progress": round(0.2 + 0.05 * tier, 2)})
        items.grant(conn, "player", player.id, iid)
        return [f"🤝 Un messaggero ti consegna un pacco: {n} pietre e una Pillola della Gratitudine. "
                f"«Da parte di {d['name']}, che non ha dimenticato.» Il debito è saldato."]
    from engine.systems import secret_realms
    return [f"🤝 {d['name']} ti fa arrivare una mappa e una frase: «Dove la terra trema, c'è qualcosa che "
            f"aspetta te.» Il debito è saldato. (la prossima eredità nei reami segreti ti sarà più vicina)"]


def allies_in_battle(conn, player_id: int, npc_id: int, ratio: float) -> list[dict]:
    """Chi ti deve la vita accorre negli scontri difficili."""
    from engine.simulation import combat
    if ratio >= 1.0:
        return []
    rng = random.Random(tick_mod.get_tick(conn) * 29 + npc_id)
    out = []
    for d in debts(conn):
        if d["status"] != "alleato" or d["npc_id"] == npc_id or rng.random() > 0.45:
            continue
        atk = combat.combat_power(conn, "npc", d["npc_id"])["attack"] * 0.5
        out.append({"intro": f"🤝 Un'ombra si getta tra te e il colpo: è {d['name']}. «Il mio debito, ricordi?»",
                    "attack": atk, "line": f"{d['name']} " + rng.choice(["colpisce al tuo fianco.",
                                                                        "para un affondo diretto a te.",
                                                                        "incalza il nemico."])})
        if len(out) >= 1:
            break
    return out


# ============================================================ comandi

def command(conn, player, arg: str) -> str:
    from engine.systems import sects, menus, chronicle
    p = arg.strip().split()
    if not p:
        return menus.show(conn, player, "faide")
    sub, fid = p[0].lower(), (int(p[1]) if len(p) > 1 and p[1].isdigit() else None)
    f = conn.execute("SELECT f.*, n.name FROM feuds f JOIN npcs n ON n.id=f.npc_id WHERE f.id=?;",
                     (fid,)).fetchone() if fid else None
    if sub in ("risarcisci", "paga") and f:
        cost = _cost(conn, f)
        have = sects.get_resource(conn, "pietre_spirituali", player.id)
        if have < cost:
            return f"Non hai abbastanza pietre: servono {cost}, ne hai {have}."
        if f["intensity"] >= 90:
            _bring_here(conn, player, f)
            return (f"{f['name']} sputa per terra davanti alle tue pietre. «Il sangue non si compra.» "
                    f"Non resta che combattere: 'duello {f['name'].split()[0]}'.")
        sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
        conn.execute("UPDATE feuds SET status='chiusa', note='risarcita' WHERE id=?;", (f["id"],))
        chronicle.add(conn, "scelta", f"Risarcisce la famiglia di {f['victim_name']}: la faida si chiude.")
        return (f"Posi {cost} pietre davanti a {f['name']} e chini il capo. Un lungo silenzio. Poi: «Non è "
                f"abbastanza. Non lo sarà mai. Ma basta.» La faida per {f['victim_name']} è chiusa.")
    if sub in ("verita", "verità", "spiega") and f:
        from engine.systems import encounters
        bad = conn.execute("SELECT 1 FROM outlaws WHERE npc_id=?;", (f["victim_id"] or -1,)).fetchone()
        rng = random.Random(tick_mod.get_tick(conn) + f["id"])
        tr = entities.get_npc_traits(conn, f["npc_id"]) or {}
        p_ok = (0.75 if bad else 0.15) + 0.003 * tr.get("honor", 50) - 0.003 * f["intensity"]
        if rng.random() < p_ok:
            conn.execute("UPDATE feuds SET status='riconciliata', note='ha ascoltato la verità' WHERE id=?;", (f["id"],))
            return (f"Racconti tutto: chi era davvero {f['victim_name']}, cosa stava facendo. {f['name']} trema, "
                    "poi abbassa l'arma. «Non sapevo… o non volevo sapere.» La faida si chiude.")
        _bring_here(conn, player, f)
        conn.execute("UPDATE feuds SET intensity=MIN(100, intensity+5) WHERE id=?;", (f["id"],))
        return (f"«Bugie!» {f['name']} non ascolta una parola. Non resta che combattere: "
                f"'duello {f['name'].split()[0]}'.")
    if sub in ("fuggi", "vattene") and f:
        rng = random.Random(tick_mod.get_tick(conn) + f["id"])
        conn.execute("UPDATE feuds SET status='giurata', intensity=MIN(100, intensity+10), ready_day=? WHERE id=?;",
                     (_day(conn) + rng.randint(7, 20), f["id"]))
        return f"Te ne vai. Alle tue spalle {f['name']} grida il tuo nome finché non sparisci. Tornerà, più forte."
    if sub in ("pace",) and f:
        return command(conn, player, f"risarcisci {fid}")
    if sub == "duello" and f:
        _bring_here(conn, player, f)
        from engine.cli import loop
        return loop.dispatch(conn, f"duello {f['name'].split()[0]}", allow_nl=False)
    return menus.show(conn, player, "faide")


def describe(conn, player) -> str:
    from engine.systems import menus
    return menus.render(conn, menus.build(conn, player, "faide"))
