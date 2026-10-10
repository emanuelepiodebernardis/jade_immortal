"""
SPIRITO DELL'ARMA (器灵).

Un'arma di qualità (pregiata o divina) che ti accompagna in molte battaglie si
RISVEGLIA: nasce uno spirito con un elemento proprio (preso dal tuo Dao elementale più
forte). Lo spirito cresce di livello con le uccisioni, aumenta l'attacco e porta il suo
stato in combattimento. Se cambi arma, lo spirito resta in quella vecchia: si riparte.
Anche la Forgia (livello 6) può risvegliarlo.
"""

from __future__ import annotations

import random

from engine.systems import state

AWAKEN_KILLS = 25
KILLS_PER_LEVEL = 25
_ELEMENTS = ["fuoco", "acqua", "terra", "metallo", "legno", "vento", "fulmine", "luce", "oscurita"]
_NAMES = {"fuoco": "Spirito della Fiamma", "acqua": "Spirito della Marea", "terra": "Spirito della Montagna",
          "metallo": "Spirito dell'Acciaio", "legno": "Spirito della Foresta", "vento": "Spirito del Vento",
          "fulmine": "Spirito del Tuono", "luce": "Spirito dell'Aurora", "oscurita": "Spirito dell'Ombra"}


def _sig(conn, pid) -> str | None:
    from engine.systems import weapons
    eq = weapons.get_equipped(conn, pid)
    if not eq:
        return None
    return f"{eq['type']}:{eq['tier']}:{eq['rarity']}"


def get(conn, pid: int = 1) -> dict:
    data = state.get_json(conn, "weapon_spirit", {}) or {}
    sig = _sig(conn, pid)
    if data.get("sig") != sig:
        # arma nuova (o raffinata): lo spirito resta indietro, si ricomincia
        keep = data.get("awakened") and data.get("sig", "").split(":")[0] == (sig or "").split(":")[0] \
            and data.get("refined_ok")
        data = data if keep else {"sig": sig, "kills": 0, "awakened": False}
        data["sig"] = sig
        state.set_json(conn, "weapon_spirit", data)
    return data


def level(data: dict) -> int:
    if not data.get("awakened"):
        return 0
    return min(9, 1 + max(0, data.get("kills", 0) - data.get("awaken_kills", 0)) // KILLS_PER_LEVEL)


def _element(conn, pid, rng) -> str:
    r = conn.execute("SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key IN (%s) ORDER BY comprehension DESC LIMIT 1;" % ",".join("?" * len(_ELEMENTS)),
                     (pid, *_ELEMENTS)).fetchone()
    return r["dao_key"] if r else rng.choice(_ELEMENTS)


def awaken(conn, rng: random.Random, player, forced: bool = False) -> str:
    data = get(conn, player.id)
    if not data.get("sig"):
        return "Non impugni un'arma da risvegliare."
    if data.get("awakened"):
        return f"Lo spirito della tua arma è già desto: {data['name']} (livello {level(data)})."
    el = _element(conn, player.id, rng)
    data.update({"awakened": True, "element": el, "name": _NAMES[el], "awaken_kills": data.get("kills", 0),
                 "refined_ok": True})
    state.set_json(conn, "weapon_spirit", data)
    state.grant_title(conn, "Portatore di un'Arma Viva")
    how = "Il fuoco della forgia" if forced else "Il sangue di cento scontri"
    return f"✦ {how} risveglia la tua arma: nasce lo {_NAMES[el]}! L'arma vibra di vita propria."


def on_kill(conn, rng: random.Random, player) -> str | None:
    from engine.systems import weapons
    data = get(conn, player.id)
    if not data.get("sig"):
        return None
    data["kills"] = data.get("kills", 0) + 1
    state.set_json(conn, "weapon_spirit", data)
    eq = weapons.get_equipped(conn, player.id)
    if not data.get("awakened") and eq and eq["rarity"] >= 3 and data["kills"] >= AWAKEN_KILLS:
        return awaken(conn, rng, player)
    if data.get("awakened") and (data["kills"] - data.get("awaken_kills", 0)) % KILLS_PER_LEVEL == 0:
        return f"Lo {data['name']} cresce: livello {level(data)}."
    return None


def describe(conn, pid: int = 1) -> str | None:
    data = get(conn, pid)
    if data.get("awakened"):
        return f"Spirito dell'arma: {data['name']} (livello {level(data)}, elemento {data['element']})"
    if data.get("sig"):
        from engine.systems import weapons
        eq = weapons.get_equipped(conn, pid)
        if eq and eq["rarity"] >= 3:
            return (f"La tua arma sonnecchia ({data.get('kills', 0)}/{AWAKEN_KILLS} vittorie "
                    f"per risvegliarne lo spirito)")
    return None


def combat_ally(conn, player_id: int, fx) -> dict | None:
    from engine.systems import combat_states
    data = get(conn, player_id)
    lv = level(data)
    if lv <= 0:
        return None
    fx.p.atk_mult *= 1.0 + 0.04 * lv
    st = combat_states.STATE_OF_DAO.get(data["element"])
    if st:
        fx.add_proc("p", st, 0.10 + 0.03 * lv, 1.0 + 0.15 * lv, "spirito dell'arma")
    return {"intro": f"Lo {data['name']} si desta nella tua arma (livello {lv}).", "attack": 0,
            "line": ""}
