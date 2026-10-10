"""
BATTAGLIE DELL'ANIMA e la BANDIERA DELLE ANIME.

  - Quando divori coltivatori molto potenti, o tocchi eredità antichissime, a volte un'anima
    antica tenta di IMPOSSESSARSI di te: una battaglia nel mare della coscienza. Se vinci,
    divori quell'anima (Dao dell'Anima, corpo spirituale più forte). Se perdi, ne esci
    sconvolto: cuore del Dao incrinato e una parte della tua coltivazione persa.
  - La BANDIERA DELLE ANIME (arte demoniaca, come Wang Lin): raccoglie le anime di chi
    uccidi. Più anime contiene, più è forte in battaglia (terrore, potenza) — senza fine.
    Ogni anima catturata pesa sul karma.

  bandiera            la tua bandiera delle anime
"""

from __future__ import annotations

import math
import random

from engine.core import tick as tick_mod
from engine.systems import state


def possession_scene(conn, player, source: str, power: int) -> str | None:
    from engine.systems import encounters
    if encounters.pending(conn):
        return None
    dc = 55 + 4 * power
    sc = {"key": "battaglia_anima", "title": "Battaglia nel mare della coscienza", "event_type": "fortune",
          "text": (f"Qualcosa ti segue dentro, da {source}: un'anima antica, affamata. «Il tuo corpo è giovane… "
                   "sarà mio.» Il tuo mare della coscienza diventa un campo di battaglia."),
          "choices": [
              {"label": "La affronti con tutta la tua anima", "check": {"stat": "anima", "dc": dc},
               "success": {"dao_key": "anima", "dao_gain": 6 + 2 * power, "grow_soul": 2 + power // 2, "heart": 3,
                           "text": "La schiacci e la divori: la sua forza ora è tua."},
               "failure": {"heart": -10, "injury": 4,
                           "text": "La cacci a fatica: ne esci sconvolto, e con una parte della tua forza strappata."}},
              {"label": "La sigilli in un angolo della mente", "check": {"stat": "karma", "dc": dc - 10},
               "success": {"heart": 1, "text": "Resta lì, sigillata. A volte, nei sogni, ti sussurra segreti."},
               "failure": {"heart": -6, "text": "Il sigillo cede in parte: ti restano incubi e una crepa nel cuore."}}]}
    return encounters.start_scene(conn, player, sc)


def maybe_possession(conn, rng, player, victim_tier: int, ptier: int) -> str | None:
    if victim_tier < ptier or rng.random() > 0.15 + 0.1 * (victim_tier - ptier):
        return None
    return possession_scene(conn, player, "l'eredità che hai divorato", victim_tier)


# ---------- bandiera delle anime ----------

def flag(conn) -> dict | None:
    return state.get_json(conn, "soul_flag")


def grant_flag(conn) -> str:
    if flag(conn):
        return ""
    state.set_json(conn, "soul_flag", {"souls": 0})
    return "Ottieni la BANDIERA DELLE ANIME: un drappo nero che sussurra. Raccoglierà le anime di chi uccidi. ('bandiera')"


def on_kill(conn, t: int, player, npc_kind: str | None) -> list[str]:
    from engine.systems import karma
    f = flag(conn)
    if not f or npc_kind not in (None, "human", "demon", "spirit"):
        return []
    f["souls"] += 1
    state.set_json(conn, "soul_flag", f)
    karma.adjust_karma(conn, "player", player.id, -1, "anima catturata", t)
    if f["souls"] in (10, 100, 1000, 10000):
        return [f"La Bandiera delle Anime ruggisce: ora contiene {f['souls']} anime."]
    return []


def combat(conn, fx) -> list[str]:
    f = flag(conn)
    if not f or f["souls"] <= 0:
        return []
    s = math.log10(1 + f["souls"])
    fx.p.atk_mult *= 1.0 + 0.06 * s
    fx.add_proc("p", "terrore", min(0.45, 0.1 + 0.06 * s), 1.0 + 0.3 * s, "bandiera delle anime")
    return [f"La Bandiera delle Anime si dispiega: {f['souls']} anime urlano contro il nemico."]


def describe(conn, player) -> str:
    f = flag(conn)
    if not f:
        return ("Non possiedi una Bandiera delle Anime. È un'arte demoniaca: i maestri della via demoniaca e le "
                "zone proibite ne custodiscono.")
    s = math.log10(1 + f["souls"])
    return (f"🏴 BANDIERA DELLE ANIME — {f['souls']} anime\n"
            f"  In battaglia: attacco +{int(6 * s)}%, terrore più frequente e più forte. Ogni anima pesa sul karma.")


def maybe_find_flag(conn, rng, player) -> str | None:
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    if flag(conn) or not lt or lt["location_type"] != "forbidden_zone" or rng.random() > 0.03:
        return None
    return grant_flag(conn)
