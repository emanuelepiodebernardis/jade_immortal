"""
FACCIA E ONORE (面子) — le sfide pubbliche e le faide che crescono.

Quando la tua fama sale, in città qualcuno vuole farsi un nome a tue spese: un GIOVANE
MAESTRO arrogante ti sfida davanti a tutti. Puoi accettare il duello (non all'ultimo
sangue), umiliarlo, oppure rifiutare (e perdere la faccia).

Umiliare qualcuno ha un prezzo: il suo clan non dimentica. La FAIDA cresce di livello:
il giovane maestro → il suo protettore → l'anziano del clan → il patriarca → l'antenato
in ritiro → … senza fine, ogni volta più forte. Puoi chiudere la faida chiedendo scusa
(e pagando), oppure abbattendo chi viene a cercarti fino a quando il clan non osa più.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

_CLANS = ["Clan Mu", "Clan Long", "Clan Ye", "Famiglia Bai", "Clan Xiao", "Famiglia Tang", "Clan Lei"]
_RANKS = ["il giovane maestro", "il protettore", "l'anziano", "il patriarca", "l'antenato in ritiro"]


def _rank(level: int) -> str:
    if level <= len(_RANKS):
        return _RANKS[level - 1]
    return f"un antenato di {level - len(_RANKS) + 1}ª generazione"


def duel(conn, t: int, rng: random.Random, player, npc_id: int) -> tuple[bool, list[str]]:
    """Duello d'onore non letale (come all'Assemblea)."""
    from engine.systems import perception, reputation, seclusion
    ratio = perception.strength_ratio(conn, player.id, npc_id)
    name = conn.execute("SELECT name FROM npcs WHERE id=?;", (npc_id,)).fetchone()["name"]
    won = ratio * rng.uniform(0.8, 1.2) >= 1.0
    if won:
        reputation.adjust(conn, player.id, fame=4)
        lines = [f"Il duello è breve: {name} finisce a terra, davanti a tutti."]
        if ratio < 0.87:
            lines += seclusion.on_upset_win(conn, t, rng, player, name, ratio)
    else:
        reputation.adjust(conn, player.id, fame=-2)
        lines = [f"{name} ha la meglio. La folla ride: hai perso la faccia."]
    return won, lines


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import reputation, encounters, npc_factory
    if encounters.pending(conn):
        return []
    day = t // 120
    feud = state.get_json(conn, "face_feud")
    if feud and day >= feud["next_day"]:
        return _feud_scene(conn, rng, player, feud)
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    fame = reputation.get(conn, player.id)["fame"]
    if (not feud and lt and lt["location_type"] == "city" and fame >= 40
            and day - state.get_int(conn, "face_day", -999) >= 8 and rng.random() < 0.18):
        state.set(conn, "face_day", str(day))
        clan = rng.choice(_CLANS)
        sc = {"key": "sfida_pubblica", "title": "Una sfida in piazza", "event_type": "social",
              "text": (f"In mezzo alla piazza, {{npc}} del {clan} ti punta il ventaglio contro: «Tu saresti il "
                       "famoso…? Sembri una cosa da nulla. Ti sfido, qui, davanti a tutti!»"),
              "spawn": {"archetype": "discepolo", "tier_offset": 0, "stage": 9, "traits": {"pride": 98}},
              "choices": [
                  {"label": "Accetti il duello", "effects": {"face_duel": True, "clan": clan}},
                  {"label": "Lo umili con un solo gesto", "check": {"stat": "potenza", "dc": 62},
                   "success": {"fame": 8, "face_humiliate": clan, "npc_leaves": True,
                               "text": "Un dito, e lui vola tra le bancarelle. La piazza esplode."},
                   "failure": {"face_duel": True, "clan": clan, "text": "Schiva, e il duello comincia."}},
                  {"label": "Rifiuti con un sorriso", "effects": {"fame": -3, "npc_leaves": True,
                                                                  "text": "«Codardo!» gli fa eco la folla."}},
              ]}
        sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
        txt = encounters.start_scene(conn, player, sc)
        return [txt] if txt else []
    return []


def apply(conn, t: int, rng, player, eff: dict, ctx: dict) -> list[str]:
    """Effetti delle scene d'onore (chiamati dal motore degli incontri)."""
    lines = []
    clan = eff.get("clan") or eff.get("face_humiliate")
    if eff.get("face_duel") and ctx.get("npc_id"):
        won, ls = duel(conn, t, rng, player, ctx["npc_id"])
        lines += ls
        conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (ctx["npc_id"],))
        if won:
            _escalate(conn, t, clan, 1)
            lines.append(f"Il {clan} non dimenticherà questa umiliazione.")
    if eff.get("face_humiliate"):
        _escalate(conn, t, clan, 1)
        lines.append(f"Il {clan} non dimenticherà questa umiliazione.")
    if eff.get("feud_end"):
        state.delete(conn, "face_feud")
        lines.append("La faida è chiusa.")
    if eff.get("feud_win"):
        f = state.get_json(conn, "face_feud")
        if f:
            if f["level"] >= 5 and rng.random() < 0.5:
                state.delete(conn, "face_feud")
                lines.append(f"Il {f['clan']} non osa più mandare nessuno. Il tuo nome fa tremare il clan.")
                state.grant_title(conn, f"Terrore del {f['clan']}")
            else:
                _escalate(conn, t, f["clan"], f["level"] + 1)
    return lines


def _escalate(conn, t: int, clan: str, level: int) -> None:
    rng = random.Random(t + level)
    state.set_json(conn, "face_feud", {"clan": clan, "level": level,
                                       "next_day": t // 120 + rng.randint(4, 9)})


def _feud_scene(conn, rng, player, feud: dict) -> list[str]:
    from engine.systems import encounters, npc_factory
    lvl = feud["level"] + 1
    feud["next_day"] = 10 ** 9                     # in attesa dell'esito
    state.set_json(conn, "face_feud", feud)
    who = _rank(lvl)
    pay = 150 * lvl * lvl
    sc = {"key": "faida", "title": f"La faida col {feud['clan']}", "event_type": "combat", "sticky": True,
          "text": (f"{who.capitalize()} del {feud['clan']}, {{npc}}, ti sbarra la strada. «Hai umiliato il nostro "
                   "sangue. Oggi lo laverai col tuo.»"),
          "spawn": {"archetype": "anziano" if lvl > 2 else "discepolo", "tier_offset": max(0, lvl - 2),
                    "stage": 5 + lvl, "traits": {"pride": 95}},
          "choices": [
              {"label": "Combatti", "effects": {"feud_win": True}, "command": "attack {npc}"},
              {"label": f"Chiedi scusa e offri {pay} pietre", "effects": {"stones": -pay, "fame": -5,
                                                                         "feud_end": True, "npc_leaves": True}},
          ]}
    sc = encounters.format_scene(sc, {"npc_name": npc_factory.unique_name(rng, conn=conn)})
    txt = encounters.start_scene(conn, player, sc)
    return [txt] if txt else []
