"""
DOMINIO — il Sigillo dell'Anima (魂印), le salme rianimate (炼尸) e le sette vassalle.

SIGILLO DELL'ANIMA
  Chi hai sconfitto (o chi ha un'anima di gran lunga più debole della tua) può essere
  MARCHIATO: imprimi il tuo sigillo nel suo mare della coscienza e diventa tuo servo.
  Regola d'oro: il tuo SPIRITO deve essere più forte del suo (perception.spirit_score:
  Dao dell'Anima + regno + tempra dello spirito). Più lo sovrasti, più è probabile riuscire;
  i patriarchi e gli orgogliosi resistono di più, le bestie e gli spiriti cedono prima.
  Se fallisci, l'anima ti respinge — e i più fieri preferiscono farsi esplodere l'anima.

  Quando un servo è tuo:
    · entri in possesso di TUTTI i suoi beni (pietre, manuali, essenze, la sua arma);
    · gli dai un COMPITO: scorta (ti segue e combatte con te), lavoro (porta pietre),
      guardia (veglia sulla tua dimora), reggente (solo un patriarca: governa per te);
    · il sigillo si INCRINA se la sua anima cresce fino a sfidare la tua: rinsaldalo, o
      si ribellerà e tornerà da nemico;
    · la sua famiglia può giurare di spezzare il sigillo (una faida, come per un'uccisione).

  Se marchi il PATRIARCA di una setta, la setta è tua VASSALLA:
    · apri il suo tesoro (pietre e tesori, una volta sola);
    · ti versa un TRIBUTO ogni giorno;
    · ti insegna le sue tecniche segrete (pagando in pietre, non in merito);
    · combatte per te: rinforzi nelle guerre tra sette, nelle invasioni e nelle guerre dei regni,
      e su tuo ordine assalta le sette rivali ('dominio attacca <setta>'). Una setta piegata
      fino in fondo si arrende e diventa vassalla anch'essa.

SALME (l'Arte del Ritorno della Salma — rara: la si trova nelle eredità demoniache, nei
tesori dei reami e delle sette vassalle demoniache)
  Riporti in piedi un caduto recente ('rianima <nome>') come servo senza volontà: non si
  ribella mai, non cresce, combatte con una parte della forza che aveva in vita. Ogni manuale
  in più dell'arte ne alza il livello (salme più forti, più salme insieme). È un'arte proibita:
  karma, infamia davanti ai testimoni, e la famiglia del morto non perdonerà la profanazione.
  Un patriarca morto da meno di un giorno, rianimato senza testimoni, può essere rimesso sul
  trono come burattino… finché qualcuno non se ne accorge.

  sigilla <nome>                          marchi l'anima di chi hai battuto
  rianima <nome>                          (con l'arte) rianimi un cadavere fresco
  servi / dominio                         il menu del dominio
  servo <nome> scorta|lavoro|guardia|reggente|rinsalda|libera
  dominio riscuoti | tecniche | impara <n> [setta] | attacca <setta>
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

DAY = 120
VINTI = "dominion_defeated"
VASSALS = "vassals"
ART = "salma_art"
ROLES = {"scorta": "scorta", "lavoro": "lavoro", "guardia": "guardia", "reggente": "reggente"}
ROLE_LABEL = {"scorta": "ti scorta", "lavoro": "lavora per te", "guardia": "veglia sulla dimora",
              "reggente": "governa la sua setta per te"}


# ============================================================ tabella e letture

def ensure_table(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS servants ("
                 "npc_id INTEGER PRIMARY KEY, kind TEXT NOT NULL, role TEXT DEFAULT 'lavoro', "
                 "seal REAL DEFAULT 80, since_tick INTEGER DEFAULT 0, status TEXT DEFAULT 'attivo', "
                 "faction_id INTEGER, warned INTEGER DEFAULT 0, note TEXT);")


def servants(conn, active: bool = True) -> list:
    ensure_table(conn)
    q = ("SELECT s.*, n.name, n.kind AS nkind, n.archetype, n.location_id, n.status AS alive "
         "FROM servants s JOIN npcs n ON n.id=s.npc_id")
    if active:
        q += " WHERE s.status='attivo' AND n.status='alive'"
    return conn.execute(q + " ORDER BY s.since_tick;").fetchall()


def servant(conn, npc_id: int):
    ensure_table(conn)
    return conn.execute("SELECT s.*, n.name, n.kind AS nkind, n.archetype, n.location_id FROM servants s "
                        "JOIN npcs n ON n.id=s.npc_id WHERE s.npc_id=? AND s.status='attivo' "
                        "AND n.status='alive';", (npc_id,)).fetchone()


def servant_ids(conn) -> set[int]:
    try:
        return {r["npc_id"] for r in servants(conn)}
    except Exception:
        return set()


def art_level(conn) -> int:
    return state.get_int(conn, ART, 0)


def _tier(conn, ctype, cid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, ctype, cid) or 1


def capacity(conn, pid: int = 1) -> int:
    from engine.systems import soul_temper
    return 2 + soul_temper.grade(conn, pid) + _tier(conn, "player", pid) // 2


def salma_capacity(conn) -> int:
    return 2 * art_level(conn)


def _kind(conn, npc_id) -> str:
    r = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    return (r["kind"] if r and r["kind"] else "human")


def _leads(conn, npc_id):
    return conn.execute("SELECT id, name, tier, alignment, wealth, influence FROM factions "
                        "WHERE leader_id=? AND status='active';", (npc_id,)).fetchone()


def _loc_name(conn, loc) -> str:
    r = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone() if loc else None
    return r["name"] if r else "un luogo lontano"


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // DAY


# ============================================================ confronto delle anime

def soul_scores(conn, pid: int, npc_id: int) -> tuple[float, float]:
    from engine.systems import perception
    return (perception.spirit_score(conn, "player", pid), perception.spirit_score(conn, "npc", npc_id))


def note_defeated(conn, npc_id: int) -> None:
    d = state.get_json(conn, VINTI, {}) or {}
    d[str(npc_id)] = tick_mod.get_tick(conn)
    if len(d) > 12:
        d = dict(sorted(d.items(), key=lambda kv: kv[1])[-12:])
    state.set_json(conn, VINTI, d)


def recently_defeated(conn, npc_id: int) -> bool:
    d = state.get_json(conn, VINTI, {}) or {}
    t0 = d.get(str(npc_id))
    return t0 is not None and tick_mod.get_tick(conn) - t0 <= DAY


def defeated_list(conn) -> list:
    d = state.get_json(conn, VINTI, {}) or {}
    t = tick_mod.get_tick(conn)
    out = []
    for k, t0 in d.items():
        if t - t0 > DAY:
            continue
        r = conn.execute("SELECT id, name, status FROM npcs WHERE id=?;", (int(k),)).fetchone()
        if r and r["status"] == "alive" and not servant(conn, r["id"]):
            out.append(r)
    return out


def seal_odds(conn, pid: int, npc_id: int, beaten: bool) -> tuple[bool, float, str]:
    """(possibile, probabilità, motivo se impossibile)."""
    mine, theirs = soul_scores(conn, pid, npc_id)
    ratio = mine / max(1.0, theirs)
    if ratio <= 1.0:
        return False, 0.0, (f"la sua anima ({theirs:.0f}) regge il confronto con la tua ({mine:.0f}): "
                            "tempra lo spirito ('tempra') o approfondisci il Dao dell'Anima")
    if not beaten and ratio < 2.5:
        return False, 0.0, ("prima devi piegarlo in combattimento (senza combattere serve un'anima "
                            f"almeno 2,5 volte la sua: ora {ratio:.1f}×)")
    p = 0.3 + 0.55 * (ratio - 1.0)
    kind = _kind(conn, npc_id)
    if kind in ("beast", "spirit", "demon"):
        p += 0.1
    arch = conn.execute("SELECT archetype FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if arch and arch["archetype"] == "patriarca":
        p -= 0.15
    tr = entities.get_npc_traits(conn, npc_id) or {}
    if tr.get("honor", 50) >= 75:
        p -= 0.1
    if tr.get("pride", 50) >= 75:
        p -= 0.05
    if not beaten:
        p -= 0.1
    return True, max(0.1, min(0.97, p)), ""


def after_defeat(conn, player, npc) -> list[str]:
    """Dopo una vittoria che lascia vivo il nemico: lo ricordi come 'vinto' e, se puoi, lo dici."""
    note_defeated(conn, npc.id)
    ok, p, _why = seal_odds(conn, player.id, npc.id, True)
    if not ok:
        return []
    first = npc.name.split()[0]
    return [f"💠 La sua anima vacilla sotto la tua: puoi marchiarla e farne un servo "
            f"('sigilla {first}', ~{int(p * 100)}%)."]


def not_my_servant(conn, player, npc, frag: str):
    """Se il bersaglio di un attacco è un tuo servo, cerca un altro con quel nome; altrimenti
    rifiuta (un servo lo liberi, non lo abbatti per sbaglio). Ritorna (npc|None, messaggio)."""
    if npc is None or not servant(conn, npc.id):
        return npc, ""
    low = (frag or "").strip().lower()
    mine = servant_ids(conn)
    for r in conn.execute("SELECT id FROM npcs WHERE location_id=? AND status='alive' AND LOWER(name) LIKE ? "
                          "ORDER BY id;", (player.location_id, f"%{low}%")).fetchall():
        if r["id"] not in mine:
            return entities.get_npc(conn, r["id"]), ""
    return None, (f"{npc.name} porta il tuo sigillo: obbedisce, non combatte contro di te. "
                  f"Se vuoi liberartene: 'servo {npc.name.split()[0]} libera'.")


# ============================================================ sigillo

def _find_target(conn, player, arg: str):
    low = arg.strip().lower()
    if not low:
        return None, False
    for r in defeated_list(conn):
        if low in r["name"].lower():
            return entities.get_npc(conn, r["id"]), True
    n = entities.find_npc_in_location(conn, player.location_id, low)
    if n:
        return n, recently_defeated(conn, n.id)
    return None, False


def _blocked(conn, player, npc) -> str | None:
    from engine.systems import bonds
    k = bonds.bond_kinds(conn, npc.id, player.id)
    if k & {"family", "companion", "master", "dao_partner", "disciple", "sworn"}:
        return f"{npc.name} ti è legato da ben altro che un sigillo: non puoi farlo."
    if servant(conn, npc.id):
        return f"{npc.name} porta già il tuo sigillo."
    return None


def seal_command(conn, player, arg: str) -> str:
    if not arg.strip():
        vs = defeated_list(conn)
        if not vs:
            return ("Sigillare chi? Usa: sigilla <nome> — su chi hai appena sconfitto (vale per un giorno), "
                    "o su chi ha un'anima di gran lunga più debole della tua.")
        return "Puoi tentare il sigillo su: " + ", ".join(v["name"] for v in vs) + ". (sigilla <nome>)"
    npc, beaten = _find_target(conn, player, arg)
    if npc is None:
        return f"Non trovi nessuno di nome '{arg.strip()}' da sigillare (né qui, né tra chi hai appena battuto)."
    t = tick_mod.get_tick(conn)
    return seal(conn, t, random.Random(t * 7 + npc.id), player, npc, beaten)


def seal(conn, t: int, rng: random.Random, player, npc, beaten: bool) -> str:
    from engine.systems import spirit as spmod, dao_heart
    ensure_table(conn)
    b = _blocked(conn, player, npc)
    if b:
        return b
    if len(servants(conn)) >= capacity(conn, player.id):
        return (f"Il tuo mare della coscienza regge {capacity(conn, player.id)} sigilli e sono tutti in uso. "
                "Tempra lo spirito o libera un servo ('dominio').")
    tried = state.get_json(conn, "seal_tried", {}) or {}
    if tried.get(str(npc.id)) == _day(conn):
        return f"Hai già tentato oggi: l'anima di {npc.name} è ancora in allerta. Riprova domani."
    ok, p, why = seal_odds(conn, player.id, npc.id, beaten)
    if not ok:
        return f"Non puoi sigillare {npc.name}: {why}."
    cost = max(10, int(spmod.max_spirit(conn, player.id) * 0.2))
    if not spmod.spend(conn, cost, player.id):
        return f"Ti serve più spirito per imprimere un sigillo ({cost}): riposa o medita."
    tried[str(npc.id)] = _day(conn)
    state.set_json(conn, "seal_tried", tried)
    kind = _kind(conn, npc.id)
    lines = [rng.choice([
        f"Posi due dita sulla fronte di {npc.name} e il tuo senso divino affonda nel suo mare della coscienza.",
        f"La tua anima scende su quella di {npc.name} come una montagna su un fuoco di paglia.",
        f"Tracci il sigillo nell'aria: si accende d'oro e precipita nella fronte di {npc.name}."])]
    if rng.random() >= p:
        return "\n".join(lines + _failed(conn, t, rng, player, npc, kind))
    mine, theirs = soul_scores(conn, player.id, npc.id)
    strength = 55 + 45 * min(1.0, (mine / max(1.0, theirs) - 1.0))
    lines.append(rng.choice([
        f"Il sigillo si chiude. {npc.name} china il capo: «…Padrone.»",
        f"Un'ultima resistenza, poi il silenzio. Negli occhi di {npc.name} brilla il tuo marchio.",
        f"L'anima di {npc.name} si piega. Da oggi la sua vita è un filo che tieni tu."]))
    lines += _bind(conn, t, rng, player, npc, "sigillo", strength)
    from engine.systems import race_realms
    lines += race_realms.on_defeat(conn, t, rng, player, npc, "seal") if race_realms.race_of_npc(conn, npc.id)[0] else []
    dao_heart.adjust(conn, 1, "dominio")
    return "\n".join(lines)


def _failed(conn, t, rng, player, npc, kind) -> list[str]:
    from engine.systems import dao_heart, relations, bonds
    out = [f"✖ L'anima di {npc.name} ti respinge: il sigillo si spezza e il contraccolpo ti stordisce."]
    dao_heart.adjust(conn, -1, "sigillo respinto")
    relations.adjust(conn, npc.id, -40, t, player.id)
    tr = entities.get_npc_traits(conn, npc.id) or {}
    proud = kind == "human" and (_leads(conn, npc.id) or tr.get("honor", 50) >= 70 or tr.get("pride", 50) >= 80)
    if proud and rng.random() < 0.35:
        out.append(f"«Mai.» {npc.name} brucia la propria anima piuttosto che servirti: il corpo crolla senza vita.")
        conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (t, npc.id))
        from engine.simulation import combat
        combat._succession(conn, t, rng, npc.id)
        from engine.systems import feuds
        out += feuds.on_kill(conn, t, rng, player, npc)
        return out
    if kind == "human" and rng.random() < 0.5:
        msg = bonds.add_bond(conn, player.id, npc.id, "nemesis", t, rng, "hai tentato di marchiargli l'anima")
        if msg:
            out.append(msg)
    return out


def _bind(conn, t, rng, player, npc, kind: str, seal_strength: float) -> list[str]:
    from engine.systems import bonds, karma, reputation, chronicle, feuds, relations
    ensure_table(conn)
    bonds.ensure_table(conn)
    nk = _kind(conn, npc.id)
    lead = _leads(conn, npc.id) if kind == "sigillo" else None
    role = "reggente" if lead else ("scorta" if (nk != "human" or kind == "salma") else "lavoro")
    witnesses = reputation.witnesses(conn, player.location_id, npc.id)
    conn.execute("INSERT INTO servants (npc_id, kind, role, seal, since_tick, status, faction_id) "
                 "VALUES (?, ?, ?, ?, ?, 'attivo', ?) ON CONFLICT(npc_id) DO UPDATE SET kind=excluded.kind, "
                 "role=excluded.role, seal=excluded.seal, since_tick=excluded.since_tick, status='attivo', "
                 "warned=0;", (npc.id, kind, role, seal_strength, t, lead["id"] if lead else None))
    for k in ("nemesis", "rival"):
        bonds.end_bond(conn, player.id, npc.id, k, "sigillato")
    bonds.add_bond(conn, player.id, npc.id, "servo", t, reason=kind)
    conn.execute("UPDATE npcs SET hunting=0, war_id=NULL WHERE id=?;", (npc.id,))
    relations.adjust(conn, npc.id, 100, t, player.id)
    feuds.ensure_table(conn)
    conn.execute("UPDATE feuds SET status='chiusa', note='porta il tuo sigillo' WHERE npc_id=? AND status IN "
                 "('giurata','in caccia','ignoto');", (npc.id,))
    if role != "reggente":
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, npc.id))
    _set_role_bond(conn, player.id, npc.id, role)
    out = [f"⛓ {npc.name} è tuo servo ({'salma' if kind == 'salma' else 'sigillo dell’anima'}): "
           f"{ROLE_LABEL[role]}. ('dominio')"]
    # karma e voci
    kdelta = -6 if kind == "salma" else (-3 if nk == "human" else -1)
    karma.adjust_karma(conn, "player", player.id, kdelta, f"{kind}:{npc.name}", t)
    if witnesses and nk == "human":
        reputation.apply_deed(conn, player.id, infamy=8 if kind == "salma" else 4,
                              suspicion=5 if kind == "salma" else 0)
        out.append("Gli sguardi dei presenti si fanno di pietra: la voce correrà.")
    if kind == "sigillo" and nk == "human":
        out += _seize(conn, t, rng, player, npc)
        out += feuds.on_kill(conn, t, rng, player, npc, cause="sigillo")
    if lead:
        out += make_vassal(conn, t, rng, player, lead["id"], via=npc.id)
    first = not state.flag(conn, "dominion_first", False)
    if first:
        state.set(conn, "dominion_first", "1")
        state.grant_title(conn, "Colui che Marchia le Anime" if kind == "sigillo" else "Signore delle Salme")
    chronicle.add(conn, "scelta", (f"Imprime il sigillo dell'anima su {npc.name}." if kind == "sigillo"
                                   else f"Rianima la salma di {npc.name}."))
    return out


def _seize(conn, t, rng, player, npc) -> list[str]:
    """Tutti i suoi beni passano a te: pietre, eredità, arma."""
    from engine.systems import sects, loot
    from engine.cli import loop
    tier = _tier(conn, "npc", npc.id)
    stones = rng.randint(15, 40) * tier
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    out = [f"💰 Ti consegna la sua borsa: {stones} pietre spirituali."]
    # i beni di valore (manuali, essenze, arma) seguono le regole dell'eredità — ma passano a te
    # direttamente, come se li raccogliessi
    row = conn.execute("SELECT archetype FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if (row and row["archetype"] in ("patriarca", "anziano")) or tier >= loot._LEGACY_TIER:
        if loot.on_player_kill(conn, t, rng, player, npc):
            got = loop.cmd_loot(conn, player, "")
            out.append("Ti consegna tutto ciò che possiede:")
            out += [ln for ln in got.splitlines() if ln.strip() and not ln.startswith("Tutto riposto")]
    return out


def _set_role_bond(conn, pid, npc_id, role) -> None:
    """Chi è di scorta ti segue come un compagno (bond 'scorta')."""
    from engine.systems import bonds
    if role == "scorta":
        conn.execute("INSERT INTO bonds (player_id, npc_id, kind, status, since_tick, reason) VALUES "
                     "(?, ?, 'scorta', 'active', ?, 'servo') ON CONFLICT(player_id, npc_id, kind) DO UPDATE "
                     "SET status='active';", (pid, npc_id, tick_mod.get_tick(conn)))
    else:
        bonds.end_bond(conn, pid, npc_id, "scorta")


# ============================================================ salme

def revive_command(conn, player, arg: str) -> str:
    from engine.systems import spirit as spmod, sects, absorption
    lv = art_level(conn)
    if lv <= 0:
        return ("Non conosci l'Arte del Ritorno della Salma. È un'arte proibita: la si trova nelle eredità "
                "dei coltivatori demoniaci, nei tesori dei reami segreti, o la insegna una setta demoniaca vassalla.")
    if not arg.strip():
        return "Rianimare chi? Usa: rianima <nome> (su un cadavere fresco, qui)."
    npc = entities.find_dead_npc_in_location(conn, player.location_id, arg)
    if npc is None:
        return f"Non vedi il cadavere di '{arg.strip()}' qui."
    r = conn.execute("SELECT kind, death_tick FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    t = tick_mod.get_tick(conn)
    if (r["kind"] or "human") == "spirit":
        return "Uno spirito non lascia un corpo da riportare in piedi."
    if r["death_tick"] is not None and t - r["death_tick"] > 2 * DAY:
        return f"Il corpo di {npc.name} è troppo consumato: l'arte richiede un cadavere di non più di due giorni."
    n_salme = sum(1 for s in servants(conn) if s["kind"] == "salma")
    if n_salme >= salma_capacity(conn):
        return f"Il tuo livello dell'arte ({lv}) regge solo {salma_capacity(conn)} salme insieme."
    if len(servants(conn)) >= capacity(conn, player.id):
        return "Hai già tutti i servi che la tua anima può reggere."
    tier = _tier(conn, "npc", npc.id)
    stones = 20 * tier
    if sects.get_resource(conn, "pietre_spirituali", player.id) < stones:
        return f"Servono {stones} pietre spirituali per il rito (le ossa bevono Qi)."
    cost = max(10, int(spmod.max_spirit(conn, player.id) * 0.25))
    if not spmod.spend(conn, cost, player.id):
        return f"Ti serve più spirito per il rito ({cost})."
    sects.grant_resource(conn, "pietre_spirituali", -stones, player.id)
    rng = random.Random(t * 11 + npc.id)
    was_leader = _former_throne(conn, npc.id)
    conn.execute("UPDATE npcs SET status='alive', death_tick=NULL WHERE id=?;", (npc.id,))
    lines = [rng.choice([
        f"Tracci i nove sigilli neri sul petto di {npc.name}. Le dita si muovono. Poi gli occhi si aprono: vuoti.",
        f"Il Qi grigio scivola nelle vene ferme di {npc.name}. Il cadavere si alza, e aspetta i tuoi ordini.",
        f"Le ossa scricchiolano. {npc.name} è in piedi davanti a te, e non ricorda più il proprio nome."])]
    lines += _bind(conn, t, rng, player, npc, "salma", 100)
    from engine.systems import feuds
    lines += feuds.on_kill(conn, t, rng, player, npc, cause="salma")
    if was_leader:
        lines += _puppet_throne(conn, t, rng, player, npc, was_leader)
    _ = absorption  # (il cadavere rianimato non è più assorbibile finché cammina)
    return "\n".join(lines)


def _former_throne(conn, npc_id: int):
    """Era patriarca? (la successione l'ha già sostituito, ma la sua setta è ancora lì)."""
    r = conn.execute("SELECT archetype, faction_id, death_tick FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not r or r["archetype"] != "patriarca" or not r["faction_id"]:
        return None
    if r["death_tick"] is None or tick_mod.get_tick(conn) - r["death_tick"] > DAY:
        return None
    return conn.execute("SELECT id, name FROM factions WHERE id=? AND status='active';", (r["faction_id"],)).fetchone()


def _puppet_throne(conn, t, rng, player, npc, fac) -> list[str]:
    from engine.systems import reputation
    if reputation.witnesses(conn, player.location_id, npc.id):
        return [f"Ci sono testimoni: {fac['name']} saprà che il suo patriarca è morto. Il trono resta a un altro."]
    conn.execute("UPDATE factions SET leader_id=? WHERE id=?;", (npc.id, fac["id"]))
    conn.execute("UPDATE servants SET role='reggente', faction_id=? WHERE npc_id=?;", (fac["id"], npc.id))
    _set_role_bond(conn, player.id, npc.id, "reggente")
    out = [f"👑 Nessuno ha visto. {npc.name} torna sul trono di {fac['name']} come se nulla fosse — "
           "ma è la tua mano a muoverlo. Finché nessuno se ne accorge…"]
    out += make_vassal(conn, t, rng, player, fac["id"], via=npc.id, puppet=True)
    return out


def learn_art(conn) -> str:
    lv = art_level(conn) + 1
    state.set(conn, ART, str(lv))
    if lv == 1:
        return ("☠ Apprendi l'Arte del Ritorno della Salma: ora puoi rianimare i caduti recenti come servi "
                "senza volontà ('rianima <nome>').")
    return f"☠ Approfondisci l'Arte del Ritorno della Salma: livello {lv} (salme più forti, fino a {2 * lv} insieme)."


def salma_manual(conn) -> int:
    from engine.systems import items
    return items.create_item(conn, "Canone del Ritorno della Salma", "manuale", "leggendario",
                             "Un'arte proibita: insegna a riportare in piedi i caduti come servi senza volontà.",
                             {"learn_art": "salma"})


# ============================================================ sette vassalle

def vassals(conn) -> dict:
    return state.get_json(conn, VASSALS, {}) or {}


def _save_v(conn, v: dict) -> None:
    state.set_json(conn, VASSALS, v)


def vassal_ids(conn) -> set[int]:
    return {int(k) for k in vassals(conn)}


def make_vassal(conn, t, rng, player, fid: int, via=None, puppet: bool = False, surrender: bool = False) -> list[str]:
    from engine.systems import sects, rewards, items, chronicle
    f = conn.execute("SELECT id, name, tier, alignment, wealth, influence FROM factions WHERE id=?;", (fid,)).fetchone()
    if not f:
        return []
    v = vassals(conn)
    if str(fid) in v:
        return []
    m = sects.get_membership(conn, player.id)
    if m and m["faction_id"] == fid:
        v[str(fid)] = {"since": t, "via": via, "puppet": puppet, "loyalty": 100, "acc": 0, "own": True}
        _save_v(conn, v)
        return [f"🏯 La tua stessa setta, {f['name']}, è ora nelle tue mani: il patriarca obbedisce a te."]
    tier = f["tier"] or 1
    v[str(fid)] = {"since": t, "via": via, "puppet": puppet, "loyalty": 45 if surrender else 70, "acc": 0}
    _save_v(conn, v)
    stones = int((f["wealth"] or 50) * tier * 4)
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    out = [f"🏯 {f['name']} è ora tua VASSALLA. Ti aprono il tesoro della setta: {stones} pietre spirituali."]
    out += ["   " + ln for ln in rewards.grant(conn, rng, player, rank=1, scale=1 + 0.3 * tier,
                                               kinds=["pillola", "essenza", "manuale", "tesoro"], stones=False)]
    if (f["alignment"] or "") == "demoniaca" and rng.random() < 0.6:
        items.grant(conn, "player", player.id, salma_manual(conn))
        out.append("   ☠ Canone del Ritorno della Salma (leggendario) — dagli archivi proibiti")
    out.append("Ti verserà un tributo ogni giorno, ti insegnerà le sue tecniche e combatterà per te. ('dominio')")
    state.grant_title(conn, f"Signore di {f['name']}")
    chronicle.add(conn, "scelta", f"{f['name']} diventa sua vassalla.")
    return out


def lose_vassal(conn, fid: int, why: str) -> list[str]:
    v = vassals(conn)
    e = v.pop(str(fid), None)
    if e is None:
        return []
    _save_v(conn, v)
    f = conn.execute("SELECT name FROM factions WHERE id=?;", (fid,)).fetchone()
    nm = f["name"] if f else "una setta"
    from engine.systems import chronicle
    chronicle.add(conn, "nemico", f"{nm} spezza il vassallaggio: {why}.")
    return [f"🏯✖ {nm} non è più tua vassalla: {why}."]


def tribute_per_day(conn, fid: int, e: dict) -> int:
    f = conn.execute("SELECT tier, influence FROM factions WHERE id=?;", (fid,)).fetchone()
    if not f:
        return 0
    base = (5 + 3 * (f["tier"] or 1)) * max(10, f["influence"] or 0) / 50
    via = servant(conn, e.get("via")) if e.get("via") else None
    if via and via["role"] == "reggente":
        base *= 1.5
    return int(base * (0.5 + e.get("loyalty", 70) / 200))


def collect(conn, player) -> str:
    from engine.systems import sects
    v = vassals(conn)
    tot = sum(int(e.get("acc", 0)) for e in v.values())
    if not tot:
        return "Non c'è tributo da riscuotere."
    for e in v.values():
        e["acc"] = 0
    _save_v(conn, v)
    sects.grant_resource(conn, "pietre_spirituali", tot, player.id)
    return f"💰 Riscuoti il tributo delle sette vassalle: {tot} pietre spirituali."


def techniques(conn) -> list[dict]:
    from engine.systems import guild
    out = []
    for k in vassals(conn):
        f = conn.execute("SELECT name FROM factions WHERE id=?;", (int(k),)).fetchone()
        for tq in guild.sect_techniques(conn, int(k)):
            out.append({**tq, "sect": f["name"] if f else "?", "fid": int(k), "price": tq["cost"] * 5,
                        "known": guild.is_learned(conn, tq["key"])})
    return out


def learn_technique(conn, player, arg: str) -> str:
    from engine.systems import sects
    techs = techniques(conn)
    if not techs:
        return "Non hai sette vassalle che possano insegnarti qualcosa."
    p = arg.split()
    if not p or not p[0].isdigit() or not (1 <= int(p[0]) <= len(techs)):
        return "Quale tecnica? Usa: dominio impara <n> (vedi 'dominio tecniche')."
    tq = techs[int(p[0]) - 1]
    if tq["known"]:
        return f"Conosci già {tq['name']}."
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    if have < tq["price"]:
        return f"Servono {tq['price']} pietre (ne hai {have}) per farti consegnare le scritture di {tq['name']}."
    sects.grant_resource(conn, "pietre_spirituali", -tq["price"], player.id)
    conn.execute("INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, learned_tick) "
                 "VALUES (?, ?, ?, ?, ?, ?);", (player.id, tq["fid"], tq["key"], tq["name"], tq["magnitude"],
                                                tick_mod.get_tick(conn)))
    return (f"📜 Gli anziani di {tq['sect']} ti consegnano le scritture segrete: apprendi {tq['name']} "
            f"(+{int(tq['magnitude'] * 100)}% potenza).")


def describe_techniques(conn) -> str:
    techs = techniques(conn)
    if not techs:
        return "Non hai sette vassalle."
    lines = ["Tecniche delle sette vassalle (si pagano in pietre, non in merito):"]
    for i, tq in enumerate(techs, 1):
        lines.append(f"  {i}. {tq['name']} — {tq['sect']} · +{int(tq['magnitude'] * 100)}% · "
                     + ("✔ appresa" if tq["known"] else f"{tq['price']} pietre"))
    lines.append("Usa 'dominio impara <n>'.")
    return "\n".join(lines)


def _fac_power(conn, fid: int) -> float:
    f = conn.execute("SELECT tier, influence FROM factions WHERE id=?;", (fid,)).fetchone()
    return ((f["influence"] or 0) + 20 * (f["tier"] or 1)) if f else 0.0


def war_support(conn, exclude: int | None = None) -> tuple[int, list[str]]:
    """Rinforzi delle vassalle in una guerra: (forza aggiunta, nomi)."""
    tot, names = 0.0, []
    for k, e in vassals(conn).items():
        if int(k) == exclude or e.get("own"):
            continue
        f = conn.execute("SELECT name FROM factions WHERE id=? AND status='active';", (int(k),)).fetchone()
        if not f:
            continue
        tot += _fac_power(conn, int(k)) * 0.5 * e.get("loyalty", 70) / 100
        names.append(f["name"])
    from engine.systems import race_realms
    rp, rn = race_realms.war_power(conn)
    return int(tot + rp), names + rn


def targets(conn, player) -> list:
    from engine.systems import sects
    m = sects.get_membership(conn, player.id)
    mine = {m["faction_id"]} if m else set()
    own = None
    try:
        from engine.systems import own_sect
        s = own_sect.get(conn)
        own = s.get("fid") if s else None
    except Exception:
        pass
    vs = vassal_ids(conn)
    rows = conn.execute("SELECT id, name, tier, influence FROM factions WHERE status='active' "
                        "ORDER BY tier DESC, influence DESC;").fetchall()
    from engine.systems import ascension
    plane = ascension.plane_faction_ids(conn, ascension.player_layer(conn, player.id))
    return [r for r in rows if r["id"] not in vs and r["id"] not in mine and r["id"] != own and r["id"] in plane]


def attack(conn, player, arg: str) -> str:
    from engine.systems import sects, rewards
    v = vassals(conn)
    if not [k for k, e in v.items() if not e.get("own")]:
        return "Non hai sette vassalle da mandare all'assalto."
    day = _day(conn)
    if state.get_int(conn, "vassal_raid_day", -99) > day - 3:
        return "Le tue vassalle stanno ancora leccandosi le ferite dall'ultimo assalto (una volta ogni 3 giorni)."
    low = arg.strip().lower()
    tg = next((r for r in targets(conn, player) if low and low in r["name"].lower()), None)
    if tg is None:
        return "Quale setta? Usa: dominio attacca <nome setta> (vedi i bersagli nel menu 'dominio')."
    rng = random.Random(tick_mod.get_tick(conn) * 3 + tg["id"])
    power, names = war_support(conn)
    defense = _fac_power(conn, tg["id"])
    state.set(conn, "vassal_raid_day", str(day))
    roll = power * rng.uniform(0.75, 1.25)
    lines = [f"⚔ Al tuo ordine, {', '.join(names)} marciano contro {tg['name']}."]
    if roll >= defense:
        loss = rng.randint(8, 16)
        conn.execute("UPDATE factions SET influence=MAX(0, influence-?) WHERE id=?;", (loss, tg["id"]))
        stones = int(40 * (tg["tier"] or 1) * rng.uniform(0.8, 1.4))
        sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
        lines.append(f"VITTORIA: le porte di {tg['name']} cedono. La setta perde {loss} di influenza; "
                     f"il bottino è tuo: {stones} pietre.")
        lines += ["   " + ln for ln in rewards.grant(conn, rng, player, rank=2, scale=1 + 0.2 * (tg["tier"] or 1),
                                                     stones=False)]
        for e in v.values():
            e["loyalty"] = max(0, e.get("loyalty", 70) - 4)
        _save_v(conn, v)
        left = conn.execute("SELECT influence FROM factions WHERE id=?;", (tg["id"],)).fetchone()["influence"]
        if left <= 10:
            lines.append(f"{tg['name']} è in ginocchio: i suoi anziani chiedono la resa.")
            lines += make_vassal(conn, tick_mod.get_tick(conn), rng, player, tg["id"], surrender=True)
    else:
        lines.append(f"SCONFITTA: {tg['name']} regge l'urto e respinge le tue vassalle.")
        for k, e in v.items():
            if e.get("own"):
                continue
            e["loyalty"] = max(0, e.get("loyalty", 70) - 12)
            conn.execute("UPDATE factions SET influence=MAX(0, influence-5) WHERE id=?;", (int(k),))
        _save_v(conn, v)
    return "\n".join(lines)


# ============================================================ compiti, rinsaldare, liberare

def _find_servant(conn, name: str):
    low = name.strip().lower()
    return next((s for s in servants(conn) if low and low in s["name"].lower()), None)


def servant_command(conn, player, arg: str) -> str:
    p = arg.strip().split()
    if len(p) < 2:
        return "Usa: servo <nome> scorta|lavoro|guardia|reggente|rinsalda|libera."
    what = p[-1].lower()
    s = _find_servant(conn, " ".join(p[:-1]))
    if s is None:
        return f"Nessun servo di nome '{' '.join(p[:-1])}'."
    if what in ROLES:
        return set_role(conn, player, s, what)
    if what in ("rinsalda", "rafforza"):
        return reinforce(conn, player, s)
    if what in ("libera", "liberalo", "liberala", "riposa"):
        return release(conn, player, s)
    return "Ordine sconosciuto: scorta, lavoro, guardia, reggente, rinsalda, libera."


def set_role(conn, player, s, role: str) -> str:
    if role == "reggente":
        if not s["faction_id"] or str(s["faction_id"]) not in vassals(conn):
            return f"{s['name']} non ha una setta da governare."
    elif s["role"] == "reggente" and s["faction_id"]:
        # lascia il trono: la setta resta vassalla ma senza il reggente rende meno
        pass
    if role in ("lavoro",) and s["kind"] == "salma":
        return "Una salma non sa lavorare: sa solo combattere e fare la guardia."
    conn.execute("UPDATE servants SET role=? WHERE npc_id=?;", (role, s["npc_id"]))
    _set_role_bond(conn, player.id, s["npc_id"], role)
    if role == "scorta":
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, s["npc_id"]))
    elif role == "guardia":
        from engine.systems import cave_abode
        ab = cave_abode.get(conn, player.id)
        if ab:
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (ab["loc"], s["npc_id"]))
    elif role == "reggente":
        f = conn.execute("SELECT home_location_id FROM factions WHERE id=?;", (s["faction_id"],)).fetchone()
        if f and f["home_location_id"]:
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (f["home_location_id"], s["npc_id"]))
    return f"{s['name']} china il capo: ora {ROLE_LABEL[role]}."


def reinforce(conn, player, s) -> str:
    from engine.systems import spirit as spmod
    if s["kind"] == "salma":
        return "Una salma non ha volontà da tenere a bada: il suo sigillo non si incrina."
    if s["seal"] >= 100:
        return f"Il sigillo su {s['name']} è già saldo."
    cost = max(8, int(spmod.max_spirit(conn, player.id) * 0.12))
    if not spmod.spend(conn, cost, player.id):
        return f"Ti serve più spirito ({cost}) per rinsaldare il sigillo."
    mine, theirs = soul_scores(conn, player.id, s["npc_id"])
    gain = 30 if mine > theirs else 10
    conn.execute("UPDATE servants SET seal=MIN(100, seal+?), warned=0 WHERE npc_id=?;", (gain, s["npc_id"]))
    return (f"Rinsaldi il sigillo nell'anima di {s['name']} (+{gain})."
            + ("" if mine > theirs else " Ma la sua anima ormai sfida la tua: il sigillo non reggerà a lungo."))


def release(conn, player, s) -> str:
    from engine.systems import bonds, feuds, karma
    t = tick_mod.get_tick(conn)
    rng = random.Random(t + s["npc_id"])
    conn.execute("UPDATE servants SET status='libero' WHERE npc_id=?;", (s["npc_id"],))
    for k in ("servo", "scorta"):
        bonds.end_bond(conn, player.id, s["npc_id"], k, "liberato")
    out = []
    if s["role"] == "reggente" and s["faction_id"]:
        out += lose_vassal(conn, s["faction_id"], f"hai liberato {s['name']}")
    feuds.ensure_table(conn)
    if s["kind"] == "salma":
        conn.execute("UPDATE feuds SET status='riconciliata', note='hai dato pace alla salma' "
                     "WHERE victim_id=? AND note='salma' AND status IN ('giurata','in caccia','ignoto');", (s["npc_id"],))
        conn.execute("UPDATE npcs SET status='dead', death_tick=? WHERE id=?;", (t, s["npc_id"]))
        karma.adjust_karma(conn, "player", player.id, 2, f"riposo:{s['name']}", t)
        return "\n".join([f"Sciogli i sigilli neri: la salma di {s['name']} si accascia e trova finalmente pace."] + out)
    conn.execute("UPDATE feuds SET status='riconciliata', note='hai liberato chi tenevi in catene' "
                 "WHERE victim_id=? AND note='sigillo' AND status IN ('giurata','in caccia','ignoto');", (s["npc_id"],))
    tr = entities.get_npc_traits(conn, s["npc_id"]) or {}
    if rng.random() < 0.35 + 0.004 * tr.get("honor", 50) - 0.003 * tr.get("pride", 50):
        out.insert(0, f"Spezzi il sigillo. {s['name']} ti guarda a lungo, poi si inchina: «Non lo dimenticherò.»")
        npc = entities.get_npc(conn, s["npc_id"])
        out += feuds.on_spare(conn, t, rng, player, npc, chosen=True)
    else:
        out.insert(0, f"Spezzi il sigillo. {s['name']} si massaggia la fronte, e nei suoi occhi c'è solo odio.")
        msg = bonds.add_bond(conn, player.id, s["npc_id"], "nemesis", t, rng, "lo hai tenuto in catene")
        if msg:
            out.append(msg)
    return "\n".join(out)


# ============================================================ quotidiano

def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    ensure_table(conn)
    from engine.systems import sects, cave_abode, bonds, chronicle
    out: list[str] = []
    # i servi caduti
    for s in servants(conn, active=False):
        if s["status"] == "attivo" and s["alive"] != "alive":
            conn.execute("UPDATE servants SET status='caduto' WHERE npc_id=?;", (s["npc_id"],))
            if s["role"] == "reggente" and s["faction_id"]:
                out += lose_vassal(conn, s["faction_id"], f"{s['name']} è morto")
    earned = 0
    for s in servants(conn):
        tier = _tier(conn, "npc", s["npc_id"])
        if s["role"] == "lavoro":
            earned += 5 + 3 * tier
        if s["role"] == "guardia":
            ab = cave_abode.get(conn, player.id)
            if ab and rng.random() < 0.5:
                st = ab.setdefault("stock", {})
                st["erbe"] = st.get("erbe", 0) + 1
                cave_abode._save(conn, ab)
        if s["kind"] != "sigillo":
            continue
        mine, theirs = soul_scores(conn, player.id, s["npc_id"])
        r = theirs / max(1.0, mine)
        tr = entities.get_npc_traits(conn, s["npc_id"]) or {}
        decay = max(0.0, (r - 0.8) * 25) + (0.4 if tr.get("honor", 50) >= 70 else 0.1)
        seal = max(0.0, s["seal"] - decay)
        conn.execute("UPDATE servants SET seal=? WHERE npc_id=?;", (seal, s["npc_id"]))
        if seal <= 0:
            out += _rebel(conn, t, rng, player, s)
        elif seal < 30 and not s["warned"]:
            conn.execute("UPDATE servants SET warned=1 WHERE npc_id=?;", (s["npc_id"],))
            out.append(f"⛓⚠ Il sigillo su {s['name']} vacilla ({int(seal)}): rinsaldalo ('servo {s['name'].split()[0]} "
                       "rinsalda') o si ribellerà.")
    if earned:
        sects.grant_resource(conn, "pietre_spirituali", earned, player.id)
        tally = state.get_int(conn, "servant_tally", 0) + earned
        if _day(conn) % 7 == 0:
            out.append(f"⛓ Questa settimana i tuoi servi ti hanno portato {tally} pietre spirituali.")
            tally = 0
        state.set(conn, "servant_tally", str(tally))
    # le sette vassalle
    v = vassals(conn)
    for k, e in list(v.items()):
        fid = int(k)
        f = conn.execute("SELECT name, status, leader_id FROM factions WHERE id=?;", (fid,)).fetchone()
        if not f or f["status"] != "active":
            v.pop(k)
            continue
        if e.get("via") and f["leader_id"] != e["via"]:
            v.pop(k)
            out.append(f"🏯✖ {f['name']} ha un nuovo patriarca che non porta il tuo sigillo: il vassallaggio è finito.")
            continue
        if e.get("puppet") and rng.random() < 0.03:
            v.pop(k)
            out.append(f"🏯✖ Gli anziani di {f['name']} hanno scoperto che il loro patriarca è una salma. "
                       "La setta insorge, e da oggi ti dà la caccia.")
            chronicle.add(conn, "nemico", f"{f['name']} scopre il patriarca-burattino e insorge.")
            continue
        if e.get("own"):
            continue
        e["acc"] = min(30 * tribute_per_day(conn, fid, e) + 1, int(e.get("acc", 0)) + tribute_per_day(conn, fid, e))
        e["loyalty"] = min(100, e.get("loyalty", 70) + (1 if e.get("via") else 0.5))
        if not e.get("via") and e["loyalty"] < 25 and rng.random() < 0.1:
            v.pop(k)
            out.append(f"🏯✖ {f['name']}, piegata ma mai doma, rompe il giuramento di resa.")
    _save_v(conn, v)
    _ = bonds
    return out


def _rebel(conn, t, rng, player, s) -> list[str]:
    from engine.systems import bonds, chronicle
    conn.execute("UPDATE servants SET status='ribelle' WHERE npc_id=?;", (s["npc_id"],))
    for k in ("servo", "scorta"):
        bonds.end_bond(conn, player.id, s["npc_id"], k, "ribelle")
    out = [f"⛓✖ Il sigillo si spezza! L'anima di {s['name']} è cresciuta oltre la tua presa: è libero, "
           "e non ha dimenticato."]
    msg = bonds.add_bond(conn, player.id, s["npc_id"], "nemesis", t, rng, "lo hai tenuto in catene")
    if msg:
        out.append(msg)
    if s["role"] == "reggente" and s["faction_id"]:
        out += lose_vassal(conn, s["faction_id"], f"{s['name']} ha spezzato il sigillo")
    chronicle.add(conn, "nemico", f"{s['name']} spezza il sigillo dell'anima e fugge.")
    return out


def leave_behind(conn, pid: int = 1) -> list[str]:
    """Ascendendo, servi e sette vassalle restano nel mondo inferiore."""
    from engine.systems import bonds
    out = []
    sv = servants(conn)
    for s in sv:
        conn.execute("UPDATE servants SET status='lasciato' WHERE npc_id=?;", (s["npc_id"],))
        for k in ("servo", "scorta"):
            bonds.end_bond(conn, pid, s["npc_id"], k, "lasciato")
    if sv:
        out.append(f"I tuoi {len(sv)} servi restano a terra: i sigilli si spengono mentre sali.")
    v = vassals(conn)
    if v:
        out.append(f"Le tue {len(v)} sette vassalle restano nel mondo inferiore, e presto dimenticheranno il tuo nome.")
        _save_v(conn, {})
    return out


# ============================================================ combattimento

def combat_allies(conn, player_id: int, npc_id: int, fx=None) -> list[dict]:
    from engine.simulation import combat
    out = []
    loc = conn.execute("SELECT location_id FROM players WHERE id=?;", (player_id,)).fetchone()
    loc = loc["location_id"] if loc else None
    lv = art_level(conn)
    for s in servants(conn):
        if s["role"] != "scorta" or s["npc_id"] == npc_id or s["location_id"] != loc:
            continue
        mult = (0.55 + 0.08 * lv) if s["kind"] == "salma" else 0.7
        atk = combat.combat_power(conn, "npc", s["npc_id"])["attack"] * mult
        icon = "💀" if s["kind"] == "salma" else "⛓"
        out.append({"intro": f"{icon} {s['name']} si mette tra te e il nemico, al tuo ordine.", "attack": atk,
                    "line": f"{s['name']} " + random.choice(["colpisce senza esitare.", "incalza il nemico.",
                                                             "para un colpo diretto a te.",
                                                             "attacca dal fianco."])})
        if len(out) >= 3:
            break
    return out


# ============================================================ menu

def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import soul_temper as ST, perception, spirit as spmod
    ensure_table(conn)
    secs = []
    sg = ST.grade(conn, player.id)
    sv = servants(conn)
    lv = art_level(conn)
    secs.append(section("La tua anima", [
        f"{ST.grade_name(sg)} · spirito {perception.spirit_score(conn, 'player', player.id):.0f} · "
        f"riserva {spmod.get_spirit(conn, player.id)}/{spmod.max_spirit(conn, player.id)}",
        f"Sigilli in uso: {len(sv)}/{capacity(conn, player.id)}"
        + (f" · Arte della Salma livello {lv} ({sum(1 for s in sv if s['kind'] == 'salma')}/{salma_capacity(conn)} salme)"
           if lv else "")],
        [act("Tempra lo spirito", "tempra", main=True)], icon="🌀"))
    vs = defeated_list(conn)
    if vs:
        acts = []
        for r in vs[:5]:
            ok, p, why = seal_odds(conn, player.id, r["id"], True)
            acts.append(act(f"Sigilla {r['name']}" + (f" (~{int(p * 100)}%)" if ok else ""),
                            f"sigilla {r['name'].split()[0]}", ok=ok, why=why))
        secs.append(section("Chi hai appena piegato", ["Vale per un giorno dalla vittoria."], acts, icon="💠"))
    if lv:
        corpses = conn.execute("SELECT id, name, death_tick FROM npcs WHERE location_id=? AND status='dead' "
                               "AND (kind IS NULL OR kind<>'spirit') ORDER BY death_tick DESC LIMIT 4;",
                               (player.location_id,)).fetchall()
        t = tick_mod.get_tick(conn)
        acts = [act(f"Rianima {c['name']}", f"rianima {c['name'].split()[0]}",
                    ok=c["death_tick"] is None or t - c["death_tick"] <= 2 * DAY, why="troppo consumato")
                for c in corpses]
        if acts:
            secs.append(section("Cadaveri qui", [], acts, icon="💀"))
    for s in sv:
        first = s["name"].split()[0]
        icon = "💀" if s["kind"] == "salma" else "⛓"
        try:
            from engine.simulation import cultivation
            realm = cultivation.realm_label(conn, "npc", s["npc_id"])
        except Exception:
            realm = ""
        where = "qui" if s["location_id"] == player.location_id else _loc_name(conn, s["location_id"])
        lines = [f"{realm} · {ROLE_LABEL.get(s['role'], s['role'])} · {where}"]
        roles = ["scorta", "guardia"] + (["lavoro"] if s["kind"] != "salma" else []) + \
                (["reggente"] if s["faction_id"] and str(s["faction_id"]) in vassals(conn) else [])
        acts = [act(r.capitalize(), f"servo {first} {r}", ok=s["role"] != r, why="è già il suo compito")
                for r in roles]
        bars = []
        if s["kind"] == "sigillo":
            mine, theirs = soul_scores(conn, player.id, s["npc_id"])
            lines.append(f"Anima: {theirs:.0f} contro la tua {mine:.0f}")
            acts.append(act("Rinsalda il sigillo", f"servo {first} rinsalda", ok=s["seal"] < 100, why="è saldo"))
            bars.append(bar("Sigillo", s["seal"], tone="bad" if s["seal"] < 30 else "info"))
        acts.append(act("Lascialo andare" if s["kind"] == "sigillo" else "Dagli pace", f"servo {first} libera"))
        secs.append(section(f"{icon} {s['name']}", lines, acts, bars))
    v = vassals(conn)
    if v:
        lines, bars = [], []
        for k, e in v.items():
            f = conn.execute("SELECT name, tier, influence FROM factions WHERE id=?;", (int(k),)).fetchone()
            if not f:
                continue
            tag = " (burattino)" if e.get("puppet") else " (resa)" if not e.get("via") else ""
            lines.append(f"🏯 {f['name']}{tag} · livello {f['tier']} · influenza {f['influence']} · "
                         f"tributo {tribute_per_day(conn, int(k), e)}/giorno")
            if not e.get("own"):
                bars.append(bar(f"Lealtà di {f['name']}", e.get("loyalty", 70), tone="warn" if e.get("loyalty", 70) < 40 else ""))
        acc = sum(int(e.get("acc", 0)) for e in v.values())
        acts = [act(f"Riscuoti il tributo ({acc} pietre)", "dominio riscuoti", ok=acc > 0, why="nulla da riscuotere", main=True),
                act("Tecniche delle vassalle", "dominio tecniche")]
        secs.append(section("Sette vassalle", lines, acts, bars, icon="🏯"))
        power, _n = war_support(conn)
        cool = state.get_int(conn, "vassal_raid_day", -99) > _day(conn) - 3
        t_acts = []
        for r in targets(conn, player)[:5]:
            d = _fac_power(conn, r["id"])
            odds = "favorevole" if power > d * 1.2 else "incerto" if power > d * 0.8 else "sfavorevole"
            t_acts.append(act(f"Assalta {r['name']} ({odds})", f"dominio attacca {r['name']}", ok=not cool,
                              why="le vassalle riposano (ogni 3 giorni)"))
        secs.append(section(f"Guerra (forza delle vassalle: {power})",
                            ["Le vassalle combattono anche nelle guerre di setta, nelle invasioni e nelle guerre dei regni."],
                            t_acts, icon="⚔"))
    elif not sv:
        secs.append(section("Come si comincia", [
            "Sconfiggi qualcuno senza ucciderlo (o vinci un duello e scegli di sigillarlo): se il tuo spirito è più "
            "forte del suo, puoi marchiarne l'anima con 'sigilla <nome>'.",
            "Marchia un PATRIARCA e la sua setta diventa tua vassalla.",
            "L'Arte del Ritorno della Salma (rara) ti permette di rianimare i caduti."], icon="📜"))
    return menu("dominio", "⛓ IL TUO DOMINIO",
                [f"Servi: {len(sv)} · sette vassalle: {len(v)}"], secs)


def command(conn, player, arg: str) -> str:
    from engine.systems import menus
    p = arg.strip().split(maxsplit=1)
    sub = p[0].lower() if p else ""
    rest = p[1] if len(p) > 1 else ""
    if sub in ("riscuoti", "tributo"):
        return collect(conn, player)
    if sub in ("tecniche",):
        return describe_techniques(conn)
    if sub in ("impara",):
        return learn_technique(conn, player, rest)
    if sub in ("attacca", "assalta"):
        return attack(conn, player, rest)
    return menus.show(conn, player, "dominio")
