"""
ALLENAMENTO D'INSIEME — `train` (o solo `t`): un'unica sessione in cui fai crescere tutto.

In una sola azione:
  · coltivi il Qi (un po' meno di una meditazione dedicata: l'attenzione è divisa);
  · affini OGNI Dao che conosci, un poco ciascuno. I Dao comuni crescono più in fretta,
    quelli rari e profondi più lentamente:
        Dao d'arma (narrativi)     ×1.00
        Dao elementali             ×0.85
        Dao sistemici              ×0.75
        Dao superiori              ×0.50
        Dao profondi (Destino, Tempo, Spazio) ×0.35
    I progressi frazionari non si perdono: si accumulano sessione dopo sessione.
  · pratichi la tua arte (alchimia, forgia, formazioni…): un po' di esperienza a ogni sessione.

Anche qui valgono il rendimento decrescente della giornata, la setta affine, il Dao del Tempo,
le ere, la dimora e tutto ciò che accelera la coltivazione. Le meditazioni dedicate
('cultivate', 'comprehend <dao>', 'craft') restano più efficaci su una cosa sola.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

QI_SHARE = 0.7          # il Qi rende il 70% di una meditazione dedicata
DAO_SHARE = 0.6         # quota di attenzione per i Dao (poi divisa fra tutti)
PROF_XP = 0.6           # esperienza d'arte per sessione (a rendimento pieno)
RARITY = {"narrative": 1.0, "elemental": 0.85, "systemic": 0.75, "superior": 0.5, "deep": 0.35}


def short(name: str) -> str:
    import re
    return re.sub(r"^Dao (dell'|della|dello|delle|degli|dei|del) ?", "", name)


def rarity_mult(level: str | None) -> float:
    return RARITY.get(level or "", 0.6)


def train(conn, player) -> str:
    from engine.cli import loop
    from engine.systems import (training, dao_training, sects, absorption, dao_powers, cult_mods,
                                professions, progression, weapons, weapon_spirit)
    from engine.simulation import world_tick
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 37 + player.id)

    # 1) Qi — la meditazione condivide la sessione con il resto
    qi_txt = loop.cmd_cultivate(conn, player, share=QI_SHARE, advance=False)
    y = training.session_yield(training.sessions_today(conn, t, "player", player.id))
    out = ["☯ Allenamento d'insieme: Qi, Dao e arte crescono insieme.", qi_txt.splitlines()[0]]
    extra_qi = [ln for ln in qi_txt.splitlines()[1:] if ln.startswith(("Avanzi", "Sei al colmo", "Sei sfinito"))
                or "cuore" in ln.lower() or "deviazione" in ln.lower()]

    # 2) Tutti i Dao conosciuti, ognuno secondo la sua rarità
    daos = dao_training.trainable_daos(conn, player.id)
    common = y * DAO_SHARE * (1.0 + absorption.evolution_bonuses(conn, player.id).get("dao_gain", 0.0)) \
        * dao_powers.time_cultivation_mult(conn, player.id)
    grown, notes = [], []
    weapon_key = weapons.get_weapon(conn, player.id)
    weapon_dao = weapons.WEAPONS[weapon_key][0] if weapon_key else None
    for d in daos:
        m = common * rarity_mult(d["level"]) * sects.element_bonus(conn, d["dao_key"], player.id) \
            * cult_mods.dao_mult(conn, player.id, d["dao_key"])
        res = dao_training.comprehend(conn, t, rng, d["dao_key"], multiplier=m, player_id=player.id, carry=True)
        if res["status"] == "ok":
            grown.append(f"{short(d['name'])} +{res['gain']}")
            if res.get("unlocked"):
                notes.append(f"★ Hai sbloccato una tecnica: {res['unlocked']}!")
            elif res.get("tier_up"):
                notes.append(f"La tua maestria nel {d['name']} si eleva: ora sei {res['label']}.")
            if d["dao_key"] == weapon_dao:
                notes += weapon_spirit.on_weapon_dao(conn, player)
    if daos:
        progression.record_dao_training(conn, player.id)
        if grown:
            out.append("Dao: " + ", ".join(grown) + ".")
        else:
            out.append(f"Dao: mediti su {len(daos)} Dao; la comprensione matura in silenzio (crescerà nelle prossime sessioni).")
    else:
        out.append("Dao: non ne hai ancora risvegliato nessuno.")

    # 3) L'arte
    if professions.profession(conn, player.id):
        lv0 = professions.level(conn, player.id)
        fr = state.get_json(conn, "prof_frac", 0.0) or 0.0
        fr += PROF_XP * y
        gain = int(fr)
        state.set_json(conn, "prof_frac", round(fr - gain, 4))
        if gain:
            state.set(conn, "profession_xp", str(professions.xp(conn, player.id) + gain))
        lv1 = professions.level(conn, player.id)
        line = f"Arte ({professions.profession(conn, player.id)}): livello {lv1}"
        line += f" — sali al livello {lv1}!" if lv1 > lv0 else (f", +{gain} esperienza." if gain else ", eserciti la mano.")
        out.append(line)

    world_tick.advance(conn, tick_mod.cost_of("cultivate"))
    out += extra_qi + notes
    return "\n".join(out)
