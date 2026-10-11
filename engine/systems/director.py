"""
IL REGISTA — regola il RITMO delle scene, perché il mondo non ti travolga di eventi simili.

Ispirato al «director» dei giochi a storylet (e all'AI Director di Left 4 Dead): gli eventi
non arrivano appena le loro condizioni sono vere, ma quando c'è spazio per goderseli.

Regole:
  · le scene AMBIENTALI (quelle che il mondo ti porta durante la giornata: arcinemico,
    famiglia minacciata, elementi celesti, emissari…) hanno un BUDGET: al massimo
    WEEK_BUDGET a settimana;
  · lo stesso TIPO di scena non torna prima di FAMILY_GAP giorni;
  · una scena che non trova spazio non va persa: entra in CODA e arriva appena c'è posto
    (le più vecchie prima). Se aspetta troppo (MAX_WAIT giorni) svanisce — il mondo è
    andato avanti senza di te;
  · alcune scene «di reazione» (le battaglie dell'anima dopo aver divorato un potente, le
    prove del cuore) rispettano la distanza tra scene dello stesso tipo anche quando nascono
    da un tuo comando: se è troppo presto, semplicemente non accadono;
  · le scene URGENTI o che decidi tu (calamità, fuga, demone interiore che sbarra lo
    sfondamento, difesa della setta…) passano sempre;
  · i CAPITOLI della storia hanno il loro passo: almeno STORY_GAP giorni tra un capitolo e
    il successivo, e le varie trame si alternano invece di accavallarsi.

  ritmo            il budget della settimana, la coda delle scene in attesa
"""

from __future__ import annotations

from contextlib import contextmanager

from engine.core import tick as tick_mod
from engine.systems import state

WEEK_BUDGET = 4          # scene ambientali per settimana (7 giorni)
FAMILY_GAP = 8           # giorni minimi tra due scene dello stesso tipo
REACTIVE_GAP = 12       # le scene di reazione (battaglie dell'anima…) tornano ancora più di rado
MAX_WAIT = 25            # giorni dopo cui una scena in coda svanisce
STORY_GAP = 2            # giorni minimi tra due capitoli della storia
KEY = "director"

# tipi di scena che passano sempre
EXEMPT = {"trama", "demone_interiore", "calamita", "fuga", "difesa_setta", "trib_strike", "prova_razza",
          "guerra_regni", "reame_eredita", "incarico_recupero", "duello"}
# scene di reazione: distanza minima anche se nate da un comando
REACTIVE = {"battaglia_anima", "prova_cuore", "provocazione", "sfida_pubblica"}
# prefissi che raggruppano scene sorelle in un solo tipo
_PREFIXES = ("eco_", "dialogo", "prova_cuore", "fuga", "demone_interiore", "battaglia_anima", "arcinemico", "nemesi",
             "famiglia", "elemento", "maestro", "anello", "fame_abisso", "dao")

_AMBIENT = [False]


@contextmanager
def ambient():
    """Le scene avviate qui dentro sono ambientali (soggette a budget e coda)."""
    prev = _AMBIENT[0]
    _AMBIENT[0] = True
    try:
        yield
    finally:
        _AMBIENT[0] = prev


def family(key: str | None) -> str:
    k = (key or "scena").lower()
    for p in _PREFIXES:
        if k.startswith(p):
            return p
    return k


def _get(conn) -> dict:
    d = state.get_json(conn, KEY) or {}
    d.setdefault("shown", [])        # [[giorno, tipo], ...] delle scene regolate mostrate
    d.setdefault("queue", [])        # [{"day": d, "fam": f, "scene": {...}}]
    d.setdefault("story_day", -99)
    d.setdefault("story_turn", 0)
    return d


def _save(conn, d: dict) -> None:
    d["shown"] = d["shown"][-40:]
    d["queue"] = d["queue"][-12:]
    state.set_json(conn, KEY, d)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _blocked(d: dict, fam: str, day: int, budget: bool = True) -> str | None:
    gap = REACTIVE_GAP if fam in REACTIVE else FAMILY_GAP
    if any(f == fam and day - dd < gap for dd, f in d["shown"]):
        return "family"
    if budget and sum(1 for dd, _f in d["shown"] if day - dd < 7) >= WEEK_BUDGET:
        return "budget"
    return None


def gate(conn, scene: dict) -> bool:
    """Chiamata da encounters.start_scene (scene non forzate). True = può partire ora."""
    fam = family(scene.get("key") or scene.get("title"))
    if fam in EXEMPT:
        return True
    is_amb = _AMBIENT[0]
    if not is_amb and fam not in REACTIVE:
        return True                       # nata da un tuo comando: passa
    d = _get(conn)
    day = _day(conn)
    why = _blocked(d, fam, day, budget=is_amb)
    if why:
        if is_amb and not any(q["fam"] == fam for q in d["queue"]):
            d["queue"].append({"day": day, "fam": fam, "scene": scene})
            _save(conn, d)
        return False
    d["shown"].append([day, fam])
    _save(conn, d)
    return True


def release(conn, player) -> str | None:
    """A inizio giornata: se c'è spazio, fa arrivare la scena in coda più vecchia."""
    from engine.systems import encounters
    d = _get(conn)
    day = _day(conn)
    d["queue"] = [q for q in d["queue"] if day - q["day"] <= MAX_WAIT]
    if not d["queue"] or encounters.pending(conn):
        _save(conn, d)
        return None
    for i, q in enumerate(d["queue"]):
        if _blocked(d, q["fam"], day):
            continue
        sc = q["scene"]
        nid = (sc.get("ctx") or {}).get("npc_id")
        if nid:
            r = conn.execute("SELECT status FROM npcs WHERE id=?;", (nid,)).fetchone()
            if not r or r["status"] != "alive":
                d["queue"].pop(i)
                _save(conn, d)
                return None
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, nid))
        d["queue"].pop(i)
        d["shown"].append([day, q["fam"]])
        _save(conn, d)
        return encounters.start_scene(conn, player, sc, force=True)
    _save(conn, d)
    return None


# ------------------------------------------------------------
# Passo della storia
# ------------------------------------------------------------

def story_ready(conn) -> bool:
    return _day(conn) - _get(conn)["story_day"] >= STORY_GAP


def story_order(conn, n: int) -> list[int]:
    s = _get(conn)["story_turn"] % max(1, n)
    return list(range(s, n)) + list(range(0, s))


def story_shown(conn, idx: int) -> None:
    d = _get(conn)
    d["story_day"] = _day(conn)
    d["story_turn"] = idx + 1
    _save(conn, d)


def describe(conn) -> str:
    d = _get(conn)
    day = _day(conn)
    week = sum(1 for dd, _f in d["shown"] if day - dd < 7)
    lines = [f"🎭 Ritmo degli eventi: {week}/{WEEK_BUDGET} scene questa settimana."]
    left = max(0, STORY_GAP - (day - d["story_day"]))
    lines.append("  Prossimo capitolo della storia: " + ("appena pronto." if not left else f"tra almeno {left} giorni."))
    if d["queue"]:
        lines.append("  In attesa: " + ", ".join(q["scene"].get("title", q["fam"]) for q in d["queue"]))
    return "\n".join(lines)
