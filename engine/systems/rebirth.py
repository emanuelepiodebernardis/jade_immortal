"""
MORTE → EPILOGO → REINCARNAZIONE nello stesso mondo.

Prima la morte chiudeva la partita e bisognava cancellare il database. Ora:
  1. la tua vita riceve un EPILOGO, scelto dalle tue statistiche reali (regno, fama,
     infamia, karma, Abisso, Sfida al Cielo, conquiste, giorni vissuti) — come i finali
     sbloccati da condizioni nelle storie interattive;
  2. la vita entra nell'archivio `past_lives` e nel luogo della morte sorge la tua TOMBA,
     con parte delle tue pietre e una reliquia (la tecnica di chi eri);
  3. puoi RINASCERE nello stesso mondo persistente con una nuova origine e UN frammento
     ereditato (un Dao, la memoria della coltivazione, o radici temprate).

Il mondo intanto è andato avanti: sette, nemici, guerre e la tua leggenda restano.
"""

from __future__ import annotations

import json
import random
import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import state

# chiavi di game_state che appartengono al MONDO (sopravvivono alla rinascita)
_WORLD_KEYS = {"last_day", "life_no", "auto_cfg", "director", "ui_hud", "ui_suggest", "ui_colors"}   # mondo e preferenze di gioco

# tabelle di sola storia (non si cancellano: il mondo ricorda)
_HISTORY_TABLES = {"events", "event_participants", "consequences", "chronicles",
                   "simulation_ticks", "past_lives", "players", "game_state", "rumors"}


def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS past_lives ("
        "id INTEGER PRIMARY KEY, life_no INTEGER NOT NULL, name TEXT, origin TEXT, "
        "realm_tier INTEGER, realm_label TEXT, epilogue_key TEXT, epilogue_title TEXT, "
        "epilogue_text TEXT, cause TEXT, death_tick INTEGER, days_lived INTEGER, "
        "tomb_location_id INTEGER, tomb_stones INTEGER DEFAULT 0, tomb_relic TEXT, "
        "tomb_claimed INTEGER DEFAULT 0, best_dao TEXT, best_dao_comp INTEGER DEFAULT 0, "
        "best_affinity TEXT, titles TEXT, UNIQUE(life_no));")


def life_no(conn) -> int:
    return state.get_int(conn, "life_no", 1)


def lives(conn) -> list[sqlite3.Row]:
    ensure_table(conn)
    return conn.execute("SELECT * FROM past_lives ORDER BY life_no;").fetchall()


# ============================================================
# Epilogo
# ============================================================

def _facts(conn, player) -> dict:
    from engine.simulation import cultivation
    from engine.systems import (reputation, karma, character, dao_powers, sects,
                                sect_invasion, training, storyline)
    t = tick_mod.get_tick(conn)
    prof = character.get_profile(conn, "player", player.id)
    rep = reputation.get(conn, player.id)
    m = sects.get_membership(conn, player.id)
    from engine.systems.sect_invasion import rank_index
    cause_row = conn.execute(
        "SELECT e.summary FROM consequences c JOIN events e ON e.id=c.event_id "
        "WHERE c.target_type='player' AND c.target_id=? AND c.consequence_type='death' "
        "ORDER BY c.id DESC LIMIT 1;", (player.id,)).fetchone()
    return {
        "name": player.name,
        "origin": prof["origin"] if prof else "mortale",
        "tier": cultivation.realm_tier(conn, "player", player.id) or 1,
        "realm": cultivation.realm_label(conn, "player", player.id),
        "fame": rep["fame"], "infamy": rep["infamy"], "suspicion": rep["suspicion"],
        "karma": karma.get_karma(conn, "player", player.id),
        "abyss": bool(prof and prof["anomaly"] == "abisso_divoratore"),
        "devoured": (prof["abs_human"] or 0) if prof else 0,
        "residue": (prof["soul_residue"] or 0) if prof else 0,
        "defiance": dao_powers.heaven_defiance(conn, player.id),
        "sect": m["sect_name"] if m else None,
        "rank": m["rank"] if m else None,
        "rank_idx": rank_index(m["rank"]) if m else -1,
        "conquests": sect_invasion.conquests(conn),
        "days": max(0, (t - storyline.life_start(conn)) // training.DAY_TICKS),
        "titles": state.titles(conn),
        "story_done": storyline.chapter(conn) >= len((storyline.arc_for(conn, player.id) or {"chapters": [1]})["chapters"]),
        "cause": cause_row["summary"] if cause_row else None,
        "voluntary": bool(voluntary_pending(conn)),
    }


# (chiave, titolo, condizione, testo) — il primo che combacia vince
_EPILOGUES = [
    ("ruota", "Colui che Scelse la Ruota",
     lambda f: f.get("voluntary"),
     "Nessuno ti ha sconfitto. Hai chiuso gli occhi quando hai deciso tu, come chi posa un pennello "
     "a opera finita, e la ruota delle vite ti ha accolto. Tornerai — e ricorderai."),
    ("immortale", "L'Immortale di Giada",
     lambda f: f["tier"] >= 10,
     "Pochi, in diecimila anni, salgono tanto in alto. Il tuo nome entra nelle preghiere "
     "dei coltivatori, inciso accanto a quello degli antichi."),
    ("divoratore", "Il Divoratore di Mondi",
     lambda f: f["abyss"] and (f["devoured"] >= 15 or f["residue"] >= 300),
     "L'Abisso ha mangiato bene, attraverso di te. Per generazioni le madri spaventeranno "
     "i figli col racconto di ciò che divorava i coltivatori nelle notti senza luna."),
    ("sfida_cielo", "Colui che Sfidò il Cielo",
     lambda f: f["defiance"] >= 400,
     "Hai piegato Spazio, Tempo e Destino finché il Cielo stesso non ti ha guardato con "
     "paura. Nessuna tomba potrà contenere del tutto quella sfida."),
    ("conquistatore", "Il Patriarca Conquistatore",
     lambda f: f["conquests"] >= 2,
     "Le sette che hai piegato portano ancora i tuoi stendardi. La tua setta racconterà "
     "le tue conquiste finché avrà una sede."),
    ("flagello", "Il Flagello",
     lambda f: f["infamy"] >= 300 and f["infamy"] > f["fame"],
     "Ovunque passavi, la gente sbarrava le porte. Il mondo tira un sospiro di sollievo; "
     "qualcuno, nell'ombra, giura di raccogliere la tua eredità."),
    ("eroe", "L'Eroe dei Mortali",
     lambda f: f["fame"] >= 200 and f["karma"] > 0,
     "Nei villaggi si accendono lumi in tuo ricordo. Hai combattuto per chi non poteva farlo, "
     "e questo il mondo non lo dimentica."),
    ("custode_storia", "Colui che Compì il Proprio Destino",
     lambda f: f["story_done"],
     "Hai chiuso i conti con la tua storia prima che la storia chiudesse i conti con te."),
    ("anziano_setta", "Il Pilastro della Setta",
     lambda f: f["rank_idx"] >= 5,
     "La tua setta ti seppellisce con tutti gli onori. Il tuo nome resta nella sala degli antenati."),
    ("qi_ribelle", "La Fiamma che Arse Troppo in Fretta",
     lambda f: bool(f["cause"]) and "deviazione" in (f["cause"] or "").lower(),
     "Hai inseguito il regno successivo più in fretta di quanto il tuo corpo potesse reggere. "
     "Il Qi, ribelle, ti ha reclamato."),
    ("vecchiaia", "Colui che Visse Fino in Fondo",
     lambda f: bool(f["cause"]) and "vecchiaia" in (f["cause"] or "").lower(),
     "Nessuna spada, nessun fulmine: è stato il tempo a chiudere i tuoi occhi, come per i "
     "mortali. Hai visto passare intere generazioni."),
    ("foglia", "Una Foglia nel Vento",
     lambda f: f["days"] <= 3,
     "La tua via è stata breve come un respiro. Il mondo quasi non si è accorto di te — "
     "ma il mondo è grande, e le vite sono molte."),
    ("dimenticato", "Il Coltivatore Senza Nome",
     lambda f: True,
     "Hai vissuto, coltivato, combattuto. Come tanti. Il vento sulla tua tomba non sa il tuo "
     "nome, ma la terra ricorda il tuo passo."),
]


def compute_epilogue(conn, player) -> dict:
    f = _facts(conn, player)
    for key, title, cond, text in _EPILOGUES:
        try:
            ok = cond(f)
        except Exception:
            ok = False
        if ok:
            return {"key": key, "title": title, "text": text, "facts": f}
    return {"key": "dimenticato", "title": _EPILOGUES[-1][1], "text": _EPILOGUES[-1][3], "facts": f}


def _llm_epilogue(ep: dict) -> str | None:
    """Narrazione OPZIONALE via LLM, sotto Factual Lock: solo i fatti elencati."""
    from engine.narrative import llm
    if not llm.is_enabled():
        return None
    f = ep["facts"]
    facts = [f"Nome: {f['name']}", f"Regno raggiunto: {f['realm']}",
             f"Destino: {ep['title']}", f"Giorni vissuti: {f['days']}"]
    if f["sect"]:
        facts.append(f"Setta: {f['sect']} ({f['rank']})")
    if f["cause"]:
        facts.append(f"Morte: {f['cause']}")
    if f["titles"]:
        facts.append("Titoli: " + ", ".join(f["titles"]))
    system = ("Sei il cronista di un mondo xianxia. Scrivi un epitaffio di 3 frasi, in italiano, "
              "usando SOLO i fatti forniti. Non inventare nomi, eventi o luoghi.")
    return llm.generate(system, "\n".join(facts), timeout=20.0)


# ============================================================
# Registrazione della morte e tomba
# ============================================================

def record_death(conn, player) -> sqlite3.Row:
    """Archivia la vita appena conclusa (idempotente) e ne erige la tomba."""
    ensure_table(conn)
    n = life_no(conn)
    row = conn.execute("SELECT * FROM past_lives WHERE life_no=?;", (n,)).fetchone()
    if row:
        return row
    from engine.systems import sects, dao_training, character
    ep = compute_epilogue(conn, player)
    f = ep["facts"]
    text = _llm_epilogue(ep) or ep["text"]
    stones = sects.get_resource(conn, "pietre_spirituali", player.id)
    daos = dao_training.trainable_daos(conn, player.id)
    best = max(daos, key=lambda r: r["comprehension"]) if daos else None
    prof = character.get_profile(conn, "player", player.id)
    best_aff = None
    if prof:
        best_aff = max(("cultivation", "body", "qi", "soul", "combat"),
                       key=lambda k: prof[f"aff_{k}"] or 0)
    relic = json.dumps({"name": f"Reliquia di {player.name}",
                        "magnitude": round(0.04 + 0.02 * f["tier"], 3)}, ensure_ascii=False)
    t = tick_mod.get_tick(conn)
    remember_realm(conn, f["tier"])
    conn.execute(
        "INSERT INTO past_lives (life_no, name, origin, realm_tier, realm_label, epilogue_key, "
        "epilogue_title, epilogue_text, cause, death_tick, days_lived, tomb_location_id, "
        "tomb_stones, tomb_relic, best_dao, best_dao_comp, best_affinity, titles) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
        (n, player.name, f["origin"], f["tier"], f["realm"], ep["key"], ep["title"], text,
         f["cause"], t, f["days"], player.location_id, int(stones * 0.5), relic,
         best["dao_key"] if best else None, best["comprehension"] if best else 0,
         best_aff, json.dumps(f["titles"], ensure_ascii=False)))
    from engine.systems import chronicle
    chronicle.add(conn, "morte", f"{player.name} muore: «{ep['title']}» ({f['realm']}, {f['days']} giorni vissuti).")
    from engine.simulation import event_system as ev
    ev.log_event(conn, event_type="death", tick=t, location_id=player.location_id,
                 title=f"La fine di {player.name}",
                 summary=f"{player.name}, «{ep['title']}», muore. Sorge la sua tomba.",
                 participants=[ev.Participant("player", player.id, "victim")],
                 consequences=[ev.Consequence("player", player.id, "legacy", ep["title"],
                                              visibility="public", resolve_tick=t)])
    return conn.execute("SELECT * FROM past_lives WHERE life_no=?;", (n,)).fetchone()


def epilogue_text(row: sqlite3.Row) -> str:
    bar = "═" * 40
    lines = [bar, f"  EPILOGO — {row['name']}", f"  «{row['epilogue_title']}»", bar,
             row["epilogue_text"],
             f"Regno raggiunto: {row['realm_label']}. Giorni vissuti: {row['days_lived']}."]
    if row["cause"]:
        lines.append(f"Come è finita: {row['cause']}")
    tl = json.loads(row["titles"] or "[]")
    if tl:
        lines.append("Titoli: " + ", ".join(tl))
    lines.append("Dove sei caduto sorge ora la tua tomba: custodisce parte delle tue pietre "
                 "e una reliquia della tua tecnica.")
    return "\n".join(lines)


def tombs_here(conn, location_id: int) -> list[sqlite3.Row]:
    try:
        return conn.execute("SELECT * FROM past_lives WHERE tomb_location_id=? ORDER BY life_no;",
                            (location_id,)).fetchall()
    except sqlite3.OperationalError:
        return []


def tomb_line(conn, location_id: int) -> str | None:
    rows = tombs_here(conn, location_id)
    if not rows:
        return None
    parts = []
    for r in rows:
        st = "già aperta" if r["tomb_claimed"] else "sigillata — 'loot' per reclamarne i tesori"
        parts.append(f"la tomba di {r['name']} «{r['epilogue_title']}» (tua vita n.{r['life_no']}, {st})")
    return "⚱ Qui riposa " + "; ".join(parts) + "."


def claim_tombs(conn, player) -> list[str]:
    """Reclami i tesori delle tue tombe in questo luogo."""
    out = []
    from engine.systems import sects, items
    for r in tombs_here(conn, player.location_id):
        if r["tomb_claimed"] or r["life_no"] >= life_no(conn):
            continue
        conn.execute("UPDATE past_lives SET tomb_claimed=1 WHERE id=?;", (r["id"],))
        lines = [f"Apri la tomba di {r['name']}. Qualcosa, dentro di te, la riconosce."]
        if r["tomb_stones"]:
            total = sects.grant_resource(conn, "pietre_spirituali", r["tomb_stones"], player.id)
            lines.append(f"+{r['tomb_stones']} pietre spirituali (totale: {total}).")
        relic = json.loads(r["tomb_relic"] or "{}")
        if relic:
            iid = items.create_item(
                conn, relic["name"], "manuale", "raro",
                "La tecnica di una tua vita passata.",
                {"learn_technique": {"name": f"Tecnica di {r['name']}",
                                     "magnitude": relic.get("magnitude", 0.05),
                                     "tech_key": f"pastlife:{r['life_no']}"}})
            items.grant(conn, "player", player.id, iid)
            lines.append(f"Ottieni: {relic['name']} (nello zaino — 'use').")
        out += lines
    return out


def try_phoenix(conn, player) -> str | None:
    """Corpo della Fenice: una volta per vita, risorgi dalle ceneri invece di morire.
    (Prima ancora: un clone che si sacrifica, o il Gu che riavvolge il tempo.)"""
    if voluntary_pending(conn):
        return None                    # una vita lasciata di propria scelta non va «salvata»
    from engine.systems import clones, gu
    from engine.systems import deep_dao
    saved = clones.try_save(conn, player) or gu.try_rewind(conn, player) or deep_dao.try_time_rewind(conn, player)
    if saved:
        return saved
    from engine.systems import destinies
    if not destinies.flag_value(conn, "phoenix", player.id, False):
        return None
    if destinies.flag_value(conn, "phoenix_used", player.id, False):
        return None
    destinies.set_flag(conn, "phoenix_used", True, player.id)
    conn.execute("UPDATE players SET status='alive' WHERE id=?;", (player.id,))
    conn.execute("UPDATE injuries SET healed=1 WHERE character_type='player' AND character_id=?;",
                 (player.id,))
    return ("🔥 Il tuo corpo si fa cenere… e dalla cenere RINASCI. Il Corpo della Fenice ti ha "
            "salvato — ma solo per questa volta.")


def describe_lives(conn) -> str:
    rows = lives(conn)
    if not rows:
        return "Questa è la tua prima vita. (Se morirai, potrai rinascere in questo stesso mondo.)"
    lines = [f"Le tue vite passate (ora vivi la vita n.{life_no(conn)}):"]
    for r in rows:
        loc = conn.execute("SELECT name FROM locations WHERE id=?;", (r["tomb_location_id"],)).fetchone()
        tomb = f"tomba a {loc['name']}" if loc else "tomba perduta"
        tomb += " (aperta)" if r["tomb_claimed"] else " (sigillata)"
        lines.append(f"  {r['life_no']}. {r['name']} — «{r['epilogue_title']}», {r['realm_label']}, "
                     f"{r['days_lived']} giorni; {tomb}")
    return "\n".join(lines)


# ============================================================
# Reincarnazione
# ============================================================

MAX_FRAGMENTS = 2          # quanti frammenti della vita passata puoi portare con te
MEMORY_KEY = "world_realm_memory"


def remember_realm(conn, tier: int) -> None:
    """Il regno più alto mai raggiunto (in qualunque vita): la memoria che ti fa risalire."""
    if tier > state.get_int(conn, MEMORY_KEY, 0):
        state.set(conn, MEMORY_KEY, str(tier))


def realm_memory(conn) -> int:
    return state.get_int(conn, MEMORY_KEY, 0)


def memory_cult_mult(conn, pid: int = 1) -> tuple[float, str]:
    """Sotto il regno che già conoscevi, il corpo ricorda la strada: coltivi molto più in fretta."""
    from engine.simulation import cultivation
    mem = realm_memory(conn)
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    if life_no(conn) <= 1 or tier >= mem:
        return 1.0, ""
    return 2.5, f"la memoria delle vite passate (fino al regno {mem})"


def memory_bt_bonus(conn, pid: int = 1) -> float:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    return 0.2 if life_no(conn) > 1 and tier < realm_memory(conn) else 0.0


# ------------------------------------------------------------
# Reincarnazione VOLONTARIA (ciclo del Samsara) e «ricomincia da zero»
# ------------------------------------------------------------
VOLUNTARY_KEY = "voluntary_rebirth"        # in sospeso tra la scelta e la nuova vita
SAMSARA_KEY = "world_samsara"              # merito accumulato in tutte le reincarnazioni volontarie


def merit(conn, pid: int = 1) -> dict:
    """Quanto vale ciò che hai costruito in questa vita, se scegli di lasciarla."""
    import math
    from engine.simulation import cultivation
    from engine.systems import reputation, storyline, training
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    rec = cultivation.get_record(conn, "player", pid)
    dao = conn.execute("SELECT COALESCE(SUM(comprehension),0) s FROM character_daos WHERE character_type='player' "
                       "AND character_id=?;", (pid,)).fetchone()["s"]
    titles = len(state.titles(conn))
    days = max(0, (tick_mod.get_tick(conn) - storyline.life_start(conn)) // training.DAY_TICKS)
    fame = reputation.get(conn, pid)["fame"]
    parts = {"regno": tier * 15 + (rec["stage"] if rec else 0),
             "Dao": int(20 * math.log2(1 + dao / 50)),
             "titoli": titles * 3,
             "giorni vissuti": days // 5,
             "fama": int(10 * math.log2(1 + max(0, fame) / 20))}
    pts = sum(parts.values())
    return {"punti": pts, "parti": parts, "pietre": pts * 10,
            "samsara": pts, "coltivazione": samsara_mult(state.get_int(conn, SAMSARA_KEY, 0) + pts)}


def samsara_mult(points: int) -> float:
    import math
    return 1.0 + 0.1 * math.log2(1 + max(0, points) / 50)


def samsara_cult_mult(conn) -> tuple[float, str]:
    pts = state.get_int(conn, SAMSARA_KEY, 0)
    return (samsara_mult(pts), "il ciclo del Samsara (vite lasciate di tua scelta)") if pts else (1.0, "")


def voluntary_preview(conn, player) -> str:
    if hardcore(conn):
        return ("In modalità Senza Ritorno non c'è reincarnazione: puoi solo ricominciare da zero "
                "('ricomincia conferma').")
    m = merit(conn, player.id)
    lines = ["☸ REINCARNAZIONE VOLONTARIA — lasci questa vita di tua scelta, quando vuoi tu.",
             "  Merito di questa vita: " + ", ".join(f"{k} {v}" for k, v in m["parti"].items()) + f" = {m['punti']}",
             "  Cosa ottieni, rispetto a una morte qualsiasi:",
             "   · porti con te TUTTI i frammenti della vita passata (non solo due);",
             f"   · rinasci con {m['pietre']} pietre spirituali;",
             f"   · il ciclo del Samsara si rafforza: coltivazione ×{m['coltivazione']:.2f} per sempre (cresce a ogni "
             "reincarnazione volontaria);",
             "   · la memoria del regno ti fa risalire in fretta fino a dove eri arrivato.",
             "  Nessuna tomba da saccheggiare, nessun nemico che esulta: è una scelta, non una sconfitta.",
             "Per farlo: 'reincarnati conferma'. Per azzerare tutto e cominciare un mondo nuovo: 'ricomincia conferma'."]
    return "\n".join(lines)


def voluntary(conn, player) -> str:
    """Lascia questa vita di tua scelta. Il giocatore risulta morto: segue la normale rinascita."""
    if hardcore(conn):
        return voluntary_preview(conn, player)
    from engine.simulation import event_system as ev
    m = merit(conn, player.id)
    state.set_json(conn, VOLUNTARY_KEY, {"punti": m["punti"], "pietre": m["pietre"]})
    state.set(conn, SAMSARA_KEY, str(state.get_int(conn, SAMSARA_KEY, 0) + m["samsara"]))
    t = tick_mod.get_tick(conn)
    conn.execute("UPDATE players SET status='dead' WHERE id=?;", (player.id,))
    ev.log_event(conn, event_type="death", tick=t, location_id=player.location_id,
                 title=f"{player.name} lascia questa vita",
                 summary=f"{player.name} siede nella posizione del loto e lascia andare questa vita, di sua scelta.",
                 participants=[ev.Participant("player", player.id, "subject")],
                 consequences=[ev.Consequence("player", player.id, "death",
                                              "ha scelto di reincarnarsi", visibility="public", resolve_tick=t)])
    return (f"Siedi nella posizione del loto. Respiri piano, un'ultima volta, e lasci andare questa vita "
            f"(merito {m['punti']}). La ruota gira…")


def voluntary_pending(conn) -> dict | None:
    return state.get_json(conn, VOLUNTARY_KEY)


def fragments_allowed(conn, n_options: int) -> int:
    """Due frammenti di norma; tutti se la vita è stata lasciata di tua scelta."""
    return max(MAX_FRAGMENTS, n_options) if voluntary_pending(conn) else MAX_FRAGMENTS


RESTART_KEY = "world_restart_requested"


HARDCORE_KEY = "world_senza_ritorno"


def hardcore(conn) -> bool:
    return state.get(conn, HARDCORE_KEY) == "1"


def set_hardcore(conn, on: bool) -> str:
    state.set(conn, HARDCORE_KEY, "1" if on else "0")
    return ("☠ Modalità SENZA RITORNO: la morte è definitiva. Niente reincarnazione: la tua storia finirà "
            "con te, e un nuovo mondo prenderà il suo posto." if on else
            "Modalità normale: alla morte potrai rinascere in questo mondo.")


def archive_world(db_path=None) -> str:
    """Senza Ritorno: il mondo finito va in archivio (database/saves/archivio_<data>.db) e il
    file di gioco riparte vuoto. Chiamare senza connessioni aperte."""
    import datetime
    import shutil
    from pathlib import Path
    from engine import db
    src = Path(db_path or db.DB_PATH)
    dst_dir = src.parent / "saves"
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / f"archivio_{datetime.datetime.now():%Y%m%d_%H%M%S}.db"
    if src.exists():
        shutil.move(str(src), str(dst))
    for ext in ("-journal", "-wal", "-shm"):
        p = Path(str(src) + ext)
        if p.exists():
            p.unlink()
    return dst.name


def inheritance_options(row: sqlite3.Row) -> list[dict]:
    from engine.systems.character import AFF_LABELS_IT
    opts = []
    if row["best_dao"] and (row["best_dao_comp"] or 0) > 0:
        comp = max(12, int(row["best_dao_comp"] * 0.6))
        opts.append({"key": "dao", "label": f"Frammento del Dao «{row['best_dao']}» "
                                            f"(rinasci con buona parte della sua comprensione)",
                     "dao": row["best_dao"], "comp": comp})
    start = max(1, ((row["realm_tier"] or 1) + 1) // 2)
    if start > 1:
        opts.append({"key": "tier", "label": f"Memoria della coltivazione (rinasci al regno {start})",
                     "tier": start})
    if row["best_affinity"]:
        opts.append({"key": "aff", "label": f"Radici temprate (+10 di affinità: "
                                            f"{AFF_LABELS_IT.get(row['best_affinity'], row['best_affinity'])})",
                     "aff": row["best_affinity"]})
    opts.append({"key": "none", "label": "Nulla: rinasci puro, senza debiti col passato (+karma)"})
    return opts


def _purge_player(conn, pid: int) -> None:
    # chi dava la caccia alla vita precedente non riconosce la nuova: i cacciatori si fermano
    conn.execute("UPDATE npcs SET hunting=0 WHERE hunting=1;")
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")]
    for tb in tables:
        if tb in _HISTORY_TABLES:
            continue
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tb});")}
        if "player_id" in cols:
            conn.execute(f"DELETE FROM {tb} WHERE player_id=?;", (pid,))
        if {"character_type", "character_id"} <= cols:
            conn.execute(f"DELETE FROM {tb} WHERE character_type='player' AND character_id=?;", (pid,))
        if {"owner_type", "owner_id"} <= cols:
            conn.execute(f"DELETE FROM {tb} WHERE owner_type='player' AND owner_id=?;", (pid,))
        if {"actor_type", "actor_id"} <= cols:
            conn.execute(f"DELETE FROM {tb} WHERE actor_type='player' AND actor_id=?;", (pid,))
    # i cacciatori non sanno chi sei: la caccia finisce; le guerre della vecchia setta
    # non sono più le tue
    conn.execute("UPDATE npcs SET hunting=0 WHERE hunting=1;")
    conn.execute("UPDATE sect_wars SET status='lost' WHERE status='active';")
    try:                                             # chi giurava vendetta alla vita passata non ti riconosce
        conn.execute("UPDATE feuds SET status='ignoto', knows=0, ready_day=ready_day+90 "
                     "WHERE kind='faida' AND status IN ('giurata','in caccia');")
    except Exception:
        pass
    try:                                             # i servi della vita passata tornano liberi
        conn.execute("UPDATE servants SET status='libero' WHERE status='attivo';")
    except Exception:
        pass
    for r in conn.execute("SELECT key FROM game_state;").fetchall():
        if r["key"] not in _WORLD_KEYS and not r["key"].startswith("world_"):
            conn.execute("DELETE FROM game_state WHERE key=?;", (r["key"],))


def _rebirth_location(conn, rng, avoid: int | None) -> int:
    cities = [r["id"] for r in conn.execute(
        "SELECT id FROM locations WHERE location_type='city' ORDER BY id;")]
    pool = [c for c in cities if c != avoid] or cities
    if not pool:
        pool = [r["id"] for r in conn.execute("SELECT id FROM locations ORDER BY id;")]
    return rng.choice(pool)


def reincarnate(conn: sqlite3.Connection, rng: random.Random, origin_key: str,
                name: str | None, inherit: dict | None, player_id: int = 1,
                destiny: str | None = None, body: bool = False) -> list[str]:
    """Fa rinascere il giocatore nello stesso mondo. Ritorna le righe da mostrare."""
    from engine.generators import cultivation_gen
    from engine.simulation import cultivation
    from engine.systems import character, karma
    ensure_table(conn)
    old = entities.get_player(conn, player_id)
    prev = conn.execute("SELECT * FROM past_lives WHERE life_no=?;", (life_no(conn),)).fetchone()
    n_next = life_no(conn) + 1
    from engine.systems import bloodlines
    _blood = bloodlines.legacy(conn)
    vol = voluntary_pending(conn)          # letto PRIMA che la vecchia vita venga cancellata
    _ten = state.get_int(conn, "tenacity_days", 0)
    _purge_player(conn, player_id)
    t = tick_mod.get_tick(conn)
    loc = _rebirth_location(conn, rng, prev["tomb_location_id"] if prev else None)
    r1 = cultivation.ensure_realm(conn, 1)
    conn.execute("UPDATE players SET name=?, status='alive', location_id=?, realm_id=?, "
                 "faction_id=NULL, created_tick=? WHERE id=?;",
                 (name or (old.name if old else "Viandante"), loc, r1, t, player_id))
    cultivation_gen._make_record(conn, "player", player_id, r1, 1, 0.0, stage=1)
    origin = character.apply_origin(conn, origin_key, rng, player_id)
    state.set(conn, "tenacity_days", str(_ten // 2))       # la volontà non muore col corpo
    state.set(conn, "life_no", str(n_next))
    state.set(conn, "life_start_tick", str(t))
    lines = [f"Rinasci come {origin['name']}."]
    lines += bloodlines.inherit(conn, _blood)
    if destiny:
        from engine.systems import destinies
        d = destinies.apply(conn, destiny, player_id)
        lines.append(f"Il tuo destino: {d['name']}.")
    from engine.systems import constitutions
    lines += constitutions.roll_at_birth(conn, rng, origin_key, forced=body)
    # fino a DUE frammenti dalla vita passata ('Nulla' resta una scelta a sé, col suo karma)
    picks = inherit if isinstance(inherit, list) else [inherit or {"key": "none"}]
    picks = [x for x in picks if x][:(len(picks) if vol else MAX_FRAGMENTS)] or [{"key": "none"}]
    if len(picks) > 1:
        picks = [x for x in picks if x["key"] != "none"] or [{"key": "none"}]
    for inherit in picks:
        if inherit["key"] == "dao":
            conn.execute(
                "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, "
                "comprehension, practiced) VALUES ('player', ?, ?, 70, ?, 1) "
                "ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET practiced=1, "
                "comprehension=MAX(character_daos.comprehension, excluded.comprehension), "
                "affinity=MAX(character_daos.affinity, 70);",
                (player_id, inherit["dao"], inherit["comp"]))
            lines.append(f"Il Dao «{inherit['dao']}» ti torna alla mente come un sogno ricordato.")
        elif inherit["key"] == "tier":
            cur = cultivation.realm_tier(conn, "player", player_id) or 1
            tier = max(cur, inherit["tier"])
            rid = cultivation.ensure_realm(conn, tier)
            conn.execute("UPDATE players SET realm_id=? WHERE id=?;", (rid, player_id))
            conn.execute("UPDATE cultivation_records SET realm_id=?, qi_level=?, body_level=?, "
                         "soul_level=? WHERE character_type='player' AND character_id=?;",
                         (rid, tier * 10, tier * 8, tier * 8, player_id))
            lines.append(f"Il tuo corpo ricorda la via: rinasci già al regno "
                         f"{cultivation.realm_label(conn, 'player', player_id)}.")
        elif inherit["key"] == "aff":
            col = f"aff_{inherit['aff']}"
            conn.execute(f"UPDATE character_profiles SET {col}=MIN(100, {col}+10) "
                         "WHERE character_type='player' AND character_id=?;", (player_id,))
            lines.append("Le tue radici portano la tempra di un'altra vita.")
        else:
            karma.adjust_karma(conn, "player", player_id, 60, "rinascita pura", t)
            lines.append("Rinasci leggero, senza debiti col passato.")
    if prev:
        ploc = conn.execute("SELECT name FROM locations WHERE id=?;", (prev["tomb_location_id"],)).fetchone()
        if ploc:
            lines.append(f"Da qualche parte, a {ploc['name']}, una tomba porta il nome che avevi. "
                         f"Custodisce ancora qualcosa per te.")
    if vol:
        from engine.systems import sects
        sects.grant_resource(conn, "pietre_spirituali", int(vol.get("pietre", 0)), player_id)
        lines.append(f"☸ Hai scelto tu di rinascere: porti con te {int(vol.get('pietre', 0))} pietre spirituali, e il "
                     f"ciclo del Samsara ti accompagna (coltivazione ×{samsara_cult_mult(conn)[0]:.2f}).")
    from engine.systems import chronicle
    chronicle.add(conn, "rinascita", f"Una nuova vita comincia (la n.{n_next}): {origin['name']}"
                  + (" — scelta, non subita." if vol else "."))
    from engine.simulation import event_system as ev
    ev.log_event(conn, event_type="rebirth", tick=t, location_id=loc,
                 title="Una nuova vita", summary=f"Un'anima antica rinasce: la vita n.{n_next} comincia.",
                 participants=[ev.Participant("player", player_id, "subject")],
                 consequences=[ev.Consequence("player", player_id, "rebirth", origin["name"],
                                              visibility="public", resolve_tick=t)])
    return lines
