"""
L'ARMA VIVA: esperienza, tempra, risveglio e SPIRITO DELL'ARMA (器灵) senza tetto.

L'arma che impugni cresce con te, con il TEMPO e con l'USO:
  - ESPERIENZA: ogni vittoria (di più contro chi è più forte di te), ogni sconfitta da cui
    impari, ogni sessione sul tuo Dao d'arma e ogni giorno passato con lei in pugno (anche in
    ritiro o in stato etereo) le danno esperienza. Più è lungo il LEGAME, più cresce in fretta.
  - TEMPRA: quando ha accumulato abbastanza esperienza si tempra da sola: sale di rarità
    (comune → raffinata → pregiata → divina) e poi di regno, senza mai superare il tuo.
  - RISVEGLIO: qualunque arma, prima o poi, si risveglia: le divine in fretta, le comuni
    dopo una lunga strada insieme. Nasce uno SPIRITO con l'elemento del tuo Dao elementale.
  - LO SPIRITO cresce senza fine, a gradi (Desto, Senziente, Maturo, Celeste, Primordiale,
    Spirito dell'Origine I, II…). Al grado Senziente si dà un NOME (o glielo dai tu:
    'arma nome <nome>') e sprigiona la TECNICA DELL'ARMA; da Maturo difende il padrone da
    un colpo mortale per scontro; da Celeste prende FORMA e combatte al tuo fianco.
  - Cambiare arma azzera tutto: lo spirito e il legame restano in quella vecchia.

  arma              l'arma, la sua esperienza, lo spirito e la sua storia
  arma nome <nome>  dai un nome all'arma (dal grado Senziente)
"""

from __future__ import annotations

import math
import random

from engine.systems import state

KEY = "weapon_spirit"
_ELEMENTS = ["fuoco", "acqua", "terra", "metallo", "legno", "vento", "fulmine", "luce", "oscurita"]
_NAMES = {"fuoco": "Spirito della Fiamma", "acqua": "Spirito della Marea", "terra": "Spirito della Montagna",
          "metallo": "Spirito dell'Acciaio", "legno": "Spirito della Foresta", "vento": "Spirito del Vento",
          "fulmine": "Spirito del Tuono", "luce": "Spirito dell'Aurora", "oscurita": "Spirito dell'Ombra"}
_SELF_NAMES = {"fuoco": ["Brace Eterna", "Lingua di Fenice", "Cenere Rossa"],
               "acqua": ["Marea Silente", "Lacrima del Drago", "Specchio d'Inverno"],
               "terra": ["Radice di Montagna", "Pietra Paziente", "Cuore di Roccia"],
               "metallo": ["Taglio d'Autunno", "Ferro che Canta", "Filo del Destino"],
               "legno": ["Germoglio di Giada", "Vecchia Quercia", "Spina Verde"],
               "vento": ["Fischio delle Vette", "Piuma Tagliente", "Soffio Errante"],
               "fulmine": ["Tuono Nascosto", "Saetta Viola", "Ruggito del Cielo"],
               "luce": ["Alba Prima", "Raggio Puro", "Occhio del Sole"],
               "oscurita": ["Notte Senza Luna", "Ombra Fedele", "Silenzio Nero"]}
GRADES = [(1, "Desto"), (3, "Senziente"), (6, "Maturo"), (10, "Celeste"), (15, "Primordiale")]
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
AWAKEN_XP = {1: 400, 2: 220, 3: 110, 4: 60}       # esperienza per il risveglio, per rarità


# ============================================================
# Stato
# ============================================================

def get(conn, pid: int = 1) -> dict:
    d = state.get_json(conn, KEY, {}) or {}
    if "xp" not in d:                         # salvataggi vecchi (o prima arma)
        d = {"uid": d.get("uid", 1), "xp": 10 * d.get("kills", 0), "bank": 0, "days": 0,
             "kills": d.get("kills", 0), "awakened": d.get("awakened", False),
             "element": d.get("element"), "name": d.get("name"), "spirit_xp": 0,
             "custom_name": None, "feats": [], "tempers": 0}
        state.set_json(conn, KEY, d)
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def on_new_weapon(conn) -> None:
    """Hai impugnato un'arma diversa: lo spirito e il legame restano in quella vecchia."""
    old = get(conn)
    _save(conn, {"uid": old.get("uid", 1) + 1, "xp": 0, "bank": 0, "days": 0, "kills": 0,
                 "awakened": False, "element": None, "name": None, "spirit_xp": 0,
                 "custom_name": None, "feats": [], "tempers": 0})


def level(data: dict) -> int:
    if not data.get("awakened"):
        return 0
    return 1 + int((max(0, data.get("spirit_xp", 0)) / 40.0) ** 0.6)


def grade(lv: int) -> str:
    if lv <= 0:
        return "dormiente"
    g = "Desto"
    for th, nm in GRADES:
        if lv >= th:
            g = nm
    if lv >= 21:
        k = 1 + (lv - 21) // 6
        g = f"Spirito dell'Origine {_ROMAN[k - 1] if k <= len(_ROMAN) else k}"
    return g


def bond_mult(data: dict) -> float:
    return 1.0 + min(1.0, data.get("days", 0) / 365.0)


def weapon_name(data: dict) -> str | None:
    return data.get("custom_name") or (data.get("self_name") if level(data) >= 3 else None)


def temper_need(tier: int, rarity: int) -> int:
    return int(80 * rarity * (1 + 0.6 * (tier - 1)))


# ============================================================
# Crescita
# ============================================================

def add_xp(conn, player, amount: float, rng: random.Random | None = None) -> list[str]:
    from engine.systems import weapons
    from engine.simulation import cultivation
    eq = weapons.get_equipped(conn, player.id)
    if not eq or amount <= 0:
        return []
    d = get(conn, player.id)
    gain = amount * bond_mult(d)
    d["xp"] = d.get("xp", 0) + gain
    d["bank"] = d.get("bank", 0) + gain
    out = []
    if d.get("awakened"):
        lv0 = level(d)
        d["spirit_xp"] = d.get("spirit_xp", 0) + gain
        lv1 = level(d)
        if lv1 > lv0:
            out += _spirit_up(d, lv0, lv1)
    # tempra: rarità prima (se il regno è al passo), poi il regno, mai oltre il tuo
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    tier, rar = eq["tier"], eq["rarity"]
    while True:
        need = temper_need(tier, rar)
        if d["bank"] < need:
            break
        if tier < ptier - 1:
            tier += 1
        elif rar < weapons.RARITY_MAX:
            rar += 1
        elif tier < ptier:
            tier += 1
        else:
            d["bank"] = need                    # al passo con te: aspetta il tuo prossimo regno
            break
        d["bank"] -= need
        d["tempers"] = d.get("tempers", 0) + 1
        out.append(f"⚒ La tua arma si tempra da sola nel fuoco degli scontri: ora è "
                   f"{weapons.describe_weapon(eq['type'], tier, rar)}.")
    if (tier, rar) != (eq["tier"], eq["rarity"]):
        weapons._set_equipped(conn, player.id, tier, rar)
    if not d.get("awakened") and d["xp"] >= AWAKEN_XP.get(rar, 400):
        _save(conn, d)
        out.append(awaken(conn, rng or random.Random(int(d["xp"])), player))
        return out
    _save(conn, d)
    return out


def _spirit_up(d: dict, lv0: int, lv1: int) -> list[str]:
    nm = weapon_name(d) or d.get("name", "lo spirito")
    out = [f"Lo spirito della tua arma cresce: livello {lv1} ({grade(lv1)})."]
    if lv0 < 3 <= lv1:
        el = d.get("element") or "metallo"
        d["self_name"] = random.Random(d.get("uid", 1) * 31 + lv1).choice(_SELF_NAMES.get(el, ["Senza Nome"]))
        out.append(f"✦ L'arma è SENZIENTE: ti sussurra il suo nome — «{d['self_name']}» — e ti rivela "
                   f"la sua tecnica. ('arma nome <nome>' se preferisci darglielo tu)")
    if lv0 < 6 <= lv1:
        out.append(f"✦ {nm} è MATURA: ora para per te un colpo mortale in ogni scontro.")
    if lv0 < 10 <= lv1:
        out.append(f"✦ {nm} diventa CELESTE: lo spirito prende forma e combatte al tuo fianco!")
    return out


def _element(conn, pid, rng) -> str:
    r = conn.execute("SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key IN (%s) ORDER BY comprehension DESC LIMIT 1;" % ",".join("?" * len(_ELEMENTS)),
                     (pid, *_ELEMENTS)).fetchone()
    return r["dao_key"] if r else rng.choice(_ELEMENTS)


def awaken(conn, rng: random.Random, player, forced: bool = False) -> str:
    from engine.systems import weapons
    if not weapons.get_equipped(conn, player.id):
        return "Non impugni un'arma da risvegliare."
    d = get(conn, player.id)
    if d.get("awakened"):
        return f"Lo spirito della tua arma è già desto: {d['name']} (livello {level(d)}, {grade(level(d))})."
    el = _element(conn, player.id, rng)
    d.update({"awakened": True, "element": el, "name": _NAMES[el], "spirit_xp": 0})
    _save(conn, d)
    state.grant_title(conn, "Portatore di un'Arma Viva")
    how = "Il fuoco della forgia" if forced else "La lunga strada percorsa insieme"
    return f"✦ {how} risveglia la tua arma: nasce lo {_NAMES[el]}! L'arma vibra di vita propria."


def on_kill(conn, rng: random.Random, player) -> str | None:
    d = get(conn, player.id)
    d["kills"] = d.get("kills", 0) + 1
    _save(conn, d)
    out = add_xp(conn, player, 3, rng)
    return "\n".join(out) if out else None


def on_fight(conn, rng, player, won: bool, enemy_name: str, ratio: float) -> list[str]:
    """Esito di uno scontro: chi batte un avversario più forte insegna molto alla sua arma."""
    if not won:
        return add_xp(conn, player, 1, rng)
    amt = 1.0
    if ratio < 0.87:
        amt += 6 if ratio >= 0.6 else 12
        d = get(conn, player.id)
        feats = d.get("feats", [])
        feats.append(enemy_name)
        d["feats"] = feats[-10:]
        _save(conn, d)
    return add_xp(conn, player, amt, rng)


def on_days(conn, player, days: int = 1) -> list[str]:
    from engine.systems import weapons
    if not weapons.get_equipped(conn, player.id) or days <= 0:
        return []
    d = get(conn, player.id)
    d["days"] = d.get("days", 0) + days
    _save(conn, d)
    return add_xp(conn, player, 0.6 * days)


def on_weapon_dao(conn, player) -> list[str]:
    return add_xp(conn, player, 1.0)


def rename(conn, player, name: str) -> str:
    d = get(conn, player.id)
    name = name.strip().strip('"«»')
    if level(d) < 3:
        return "L'arma non è ancora senziente: non risponderebbe a nessun nome."
    if len(name) < 2:
        return "Usa: arma nome <nome>"
    d["custom_name"] = name[:40]
    _save(conn, d)
    return f"Sussurri il nome all'arma: «{d['custom_name']}». Vibra, e lo accetta."


# ============================================================
# Combattimento e descrizione
# ============================================================

def combat_ally(conn, player_id: int, fx) -> dict | None:
    from engine.systems import combat_states
    from engine.simulation import combat
    d = get(conn, player_id)
    lv = level(d)
    if lv <= 0:
        return None
    bm = bond_mult(d)
    fx.p.atk_mult *= 1.0 + 0.03 * lv
    st = combat_states.STATE_OF_DAO.get(d.get("element"))
    nm = weapon_name(d) or d["name"]
    if st:
        ch = min(0.5, 0.10 + 0.02 * lv * bm)
        pw = 1.0 + (0.15 + (0.1 if lv >= 3 else 0.0)) * lv
        fx.add_proc("p", st, ch, pw, "tecnica dell'arma" if lv >= 3 else "spirito dell'arma")
    if lv >= 6:
        fx.p.lethal_saves += 1
    if lv >= 10:
        atk = combat.combat_power(conn, "player", player_id)["attack"] * min(0.8, 0.3 + 0.02 * lv)
        return {"intro": f"✦ {nm} si stacca dalla tua mano: lo spirito prende forma e combatte con te "
                         f"({grade(lv)}).",
                "attack": atk,
                "line": f"{nm} " + random.choice(["colpisce da solo, in un lampo.", "taglia l'aria al tuo fianco.",
                                                 "si avventa sul nemico come una bestia fedele."])}
    return {"intro": f"{nm} si desta nella tua mano (livello {lv}, {grade(lv)}).", "attack": 0, "line": ""}


def describe(conn, pid: int = 1) -> str | None:
    from engine.systems import weapons
    eq = weapons.get_equipped(conn, pid)
    if not eq:
        return None
    d = get(conn, pid)
    if d.get("awakened"):
        nm = weapon_name(d) or d["name"]
        return f"Spirito dell'arma: {nm} (livello {level(d)}, {grade(level(d))}, elemento {d['element']})"
    return (f"La tua arma sonnecchia (risveglio {int(d.get('xp', 0))}/{AWAKEN_XP.get(eq['rarity'], 400)})")


def full(conn, player) -> str:
    from engine.systems import weapons
    eq = weapons.get_equipped(conn, player.id)
    if not eq:
        return "Non impugni ancora un'arma ('weapon <arma>' quando entri in una setta)."
    d = get(conn, player.id)
    lines = [f"⚔ {weapons.describe_weapon(eq['type'], eq['tier'], eq['rarity'])} — +{int(eq['bonus'] * 100)}% attacco"]
    nm = weapon_name(d)
    if nm:
        lines[0] += f" — «{nm}»"
    lines.append(f"  Legame: {d.get('days', 0)} giorni insieme (crescita ×{bond_mult(d):.2f}) · "
                 f"vittorie {d.get('kills', 0)} · tempre {d.get('tempers', 0)}")
    lines.append(f"  Prossima tempra: {int(d.get('bank', 0))}/{temper_need(eq['tier'], eq['rarity'])} esperienza")
    if d.get("awakened"):
        lv = level(d)
        nxt = next((th for th, _n in GRADES if th > lv), None) or (21 + 6 * ((max(0, lv - 21)) // 6 + 1))
        lines.append(f"  Spirito: {d['name']} — livello {lv}, grado {grade(lv)} (prossimo grado al livello {nxt})")
        powers = ["aumenta l'attacco", f"stato elementale ({d['element']})"]
        if lv >= 3:
            powers.append("tecnica dell'arma")
        if lv >= 6:
            powers.append("para un colpo mortale")
        if lv >= 10:
            powers.append("combatte in forma di spirito")
        lines.append("  Poteri: " + ", ".join(powers))
    else:
        lines.append(f"  Lo spirito dorme: risveglio a {AWAKEN_XP.get(eq['rarity'], 400)} esperienza "
                     f"(ora {int(d.get('xp', 0))}).")
    if d.get("feats"):
        lines.append("  Nemici illustri abbattuti: " + ", ".join(d["feats"][-6:]))
    return "\n".join(lines)


def command(conn, player, arg: str) -> str:
    a = arg.strip()
    if a.lower().startswith(("nome ", "name ")):
        return rename(conn, player, a.split(maxsplit=1)[1])
    return full(conn, player)
