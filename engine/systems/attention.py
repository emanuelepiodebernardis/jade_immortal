"""
COSA CHIEDE ATTENZIONE (Aggiornamento 64) — i pallini rossi e «Cosa fare ora» della dashboard.

Come nei giochi idle del genere (Immortal Taoists, Overmortal): ogni palazzo della dashboard mostra un
numero quando dentro c'è qualcosa da fare, e al centro tre schede dicono cosa fare adesso e perché.
Qui si raccoglie tutto in una lista sola: {icona, titolo, perché, comando, palazzo, scheda, urgente}.
Ogni voce è indipendente: se un sistema non risponde, la sua voce semplicemente non c'è.

Palazzi: oggi · via · setta · seguaci · mondo · tesori · storia · opzioni
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state


def _item(out, icon, title, why, cmd, palace, tab="", hot=False, prio=5):
    out.append({"icon": icon, "title": title, "why": why, "cmd": cmd, "palace": palace, "tab": tab,
                "hot": bool(hot), "prio": prio})


def items(conn, player) -> list[dict]:
    out: list[dict] = []
    day = tick_mod.get_tick(conn) // 120
    checks = (_cultivation, _growth, _followers, _world, _story, _body)
    for fn in checks:
        try:
            fn(conn, player, day, out)
        except Exception:                                  # noqa: BLE001 — una voce non deve mai far cadere la pagina
            pass
    out.sort(key=lambda x: (not x["hot"], x["prio"]))
    return out


def badges(lst: list[dict]) -> dict:
    b: dict = {}
    for it in lst:
        b[it["palace"]] = b.get(it["palace"], 0) + 1
        if it["tab"]:
            b[f"{it['palace']}:{it['tab']}"] = b.get(f"{it['palace']}:{it['tab']}", 0) + 1
    return b


# ---------------------------------------------------------------- le voci

def _cultivation(conn, player, day, out):
    from engine.systems import dao_powers, deep_dao
    from engine.simulation import cultivation
    if dao_powers.tribulation_due(conn, player.id) > 0:
        _item(out, "⚡", "Una tribolazione incombe", "Il Cielo ti aspetta: affrontala quando sei pronto.",
              "tribulation", "via", "profondi", True, 0)
    rec = cultivation.get_record(conn, "player", player.id)
    if rec and (rec["stage"] or 1) >= cultivation.STAGES_PER_REALM and rec["progress"] >= 1.0:
        odds = cultivation.breakthrough_odds(conn, "player", player.id)
        _item(out, "⇑", "Pronto allo sfondamento", f"Riuscita stimata {int(odds['success'] * 100)}%.",
              "breakthrough", "via", "coltivazione", True, 1)
    d = deep_dao.get(conn)
    if d.get("pending_judgment"):
        _item(out, "⚖", "Il Giudizio del Cielo è aperto", "Piegarti, sfidarlo o ingannarlo.", "cielo", "via", "profondi", True, 0)


def _growth(conn, player, day, out):
    from engine.systems import attributes, soul_roam, dao_heart, mentor_ring, soul_arcs, breakthrough_fates
    pts = attributes.free(conn, player.id)
    if pts:
        _item(out, "✦", f"{pts} punti attributo", "Non ancora assegnati.", "via attributi", "via", "attributi", True, 2)
    r = soul_roam.get(conn)
    if r.get("mind_day") != day:
        _item(out, "🧘", "Meditazione della mente", "Una al giorno; ogni dieci, una Nota del Tao.",
              "meditazione mente", "via", "coltivazione", False, 7)
    if r.get("body_day") != day:
        _item(out, "🧘", "Meditazione del corpo", "Una al giorno; ogni dieci, un punto attributo.",
              "meditazione corpo", "via", "coltivazione", False, 8)
    if dao_heart.toxin(conn) >= 60:
        _item(out, "☠", "Meridiani avvelenati", f"Tossine {dao_heart.toxin(conn):.0f}: la coltivazione rallenta.",
              "purifica", "via", "corpo", True, 2)
    if mentor_ring.get(conn) and mentor_ring.get(conn).get("gone") and mentor_ring.soul_candidate(conn):
        _item(out, "💍", "Un'anima vaga qui", "L'anello vuoto può accoglierla, solo oggi.", "anello accogli", "via", "anime", True, 3)
    for v in ("anello", "pagoda", "stendardo", "calderone", "perla"):
        s = soul_arcs.get(conn).get(v) or {}
        if s.get("running"):
            _item(out, "✧", f"{soul_arcs.NAMES[v]}: un capitolo è aperto", "La sua storia continua nelle trame.",
                  "trame", "oggi", "mete", False, 4)
    if state.get_json(conn, breakthrough_fates.PENDING, []):
        _item(out, "✧", "Tre destini ti aspettano", "Scegline uno per questa vita.", "fati", "via", "coltivazione", True, 1)


def _followers(conn, player, day, out):
    from engine.systems import clones, disciple_life
    if clones.can_create(conn, player.id) is None:
        _item(out, "☯", "Puoi creare un clone", "La tua anima regge un corpo in più.", "clone crea", "seguaci", "cloni", False, 5)
    rows = list(disciple_life._rows(conn, player.id))
    for i, r in enumerate(rows, 1):
        if disciple_life.info(conn, r["npc_id"])["demon"]:
            _item(out, "☠", f"{r['name']} è nel demone del cuore", "Vincilo in duello e risparmialo.",
                  f"discepolo affronta {i}", "seguaci", "discepoli", True, 2)
    if rows and state.get_int(conn, "lecture_day", -1) != day:
        _item(out, "🎓", "Lezione aperta", "I discepoli crescono, tu guadagni merito.", "discepoli lezione",
              "seguaci", "discepoli", False, 6)


def _world(conn, player, day, out):
    from engine.systems import lower_world, deification_tower as tower
    if lower_world.active(conn):
        g = lower_world.get(conn)
        if g["prayers"]:
            _item(out, "🙏", f"{len(g['prayers'])} preghiere dal mondo di sotto", "Esaudiscile per la fede del tempio.",
                  "preghiere", "mondo", "sotto", False, 4)
        if g.get("sermon_day") != day:
            _item(out, "⛩", "Predica ai mortali", "Una al giorno: fede e merito.", "predica", "mondo", "sotto", False, 8)
    from engine.systems import grand_tournament as gt, fengshui, dantian
    g2 = gt._cur(conn)
    if gt.is_open(day) and not g2["out"] and g2["round"] < len(gt.RATIOS):
        _item(out, "🏟", "Il Gran Torneo è aperto", gt.status_line(conn), "torneo combatti", "oggi", "eventi", True, 3)
    if fengshui.ready_count(conn):
        _item(out, "🌸", "L'orto è maturo", f"{fengshui.ready_count(conn)} riquadri da raccogliere (a casa).",
              "orto raccogli", "setta", "dimora", False, 6)
    if not dantian.get(conn)["pieces"]:
        _item(out, "☯", "Il dantian è vuoto", "Incastra le tecniche: attacco e coltivazione.", "dantian auto",
              "via", "tecniche", False, 5)
    t = tower.get(conn)
    tries = t["tries"] if t.get("tries_day") == day else 0
    if tries < tower.TRIES:
        _item(out, "🗼", "Torre della Deificazione", f"Ti restano {tower.TRIES - tries} tentativi oggi.",
              "torre sfida", "oggi", "eventi", False, 9)


def _story(conn, player, day, out):
    from engine.systems import intrigues, system_daily
    d = intrigues.get(conn)
    ready = [x for x in d["active"] if day >= x.get("next_day", 0) and not x.get("pending_end")]
    if ready:
        _item(out, "🕸", "Una trama va avanti", f"{len(ready)} atti pronti.", "trame", "oggi", "mete", False, 3)
    sd = system_daily.data(conn, player.id)
    if not sd["fatta"]:
        miss = [f"{g['icon']} {g['have']}/{g['need']}" for g in sd["obiettivi"] if not g["ok"]]
        _item(out, "☸", "Missione quotidiana", " · ".join(miss) or "quasi fatta", "missione", "oggi", "mete", False, 5)


def _body(conn, player, day, out):
    from engine.systems import mounts, beasts
    if beasts.pets(conn, player.id) and not mounts.mounted(conn, player.id):
        _item(out, "🐎", "La tua bestia può portarti", "Cavalcarla dà attacco e difesa.", "cavalca", "via", "corpo", False, 9)
