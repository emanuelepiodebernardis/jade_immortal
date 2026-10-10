"""
TRIBOLAZIONE DEL FULMINE CELESTE (天劫) — a ogni nuovo regno, dal terzo in su.

Ogni volta che sfondi a un nuovo regno, il Cielo ti mette alla prova con le sue folgori.
Ogni tribolazione è PIÙ FORTE della precedente e cade in PIÙ ONDATE (3, 5, 7, 9… folgori),
come le «tribolazioni a nove ondate» dei romanzi. Cosa ti fa dipende dal tuo DAO DEL FULMINE:

  Dao del Fulmine < 30      il fulmine ti è estraneo: ogni folgore che non reggi ti FERISCE,
                            brucia l'esperienza accumulata, incrina il cuore.
  Dao del Fulmine ≥ 30      TEMPRA: ogni folgore retta purifica e rinforza il corpo
                            (forza, vitalità), brucia le tossine delle pillole e la corruzione.
  Dao del Fulmine ≥ 100     ASSORBIMENTO: una parte delle folgori la bevi direttamente —
                            cresce il Dao del Fulmine, la radice del Fulmine e l'affinità,
                            e ne trattieni una parte come FULMINE DELLA TRIBOLAZIONE:
                            cariche che scateni in battaglia (stordimento e potenza).
                            Più alto il Dao, più folgori assorbi.

  Alla 1ª, 3ª, 6ª, 9ª tribolazione (e poi ogni 9) il fulmine ti lascia una TECNICA speciale,
  sempre più forte. Più tribolazioni affronti, più forte diventi (e più forte torna il Cielo).

  tribolazioni      quante ne hai affrontate, le cariche di fulmine, la prossima prova
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

MIN_TIER = 3
_TECHS = {1: "Pelle Temprata dal Tuono", 3: "Palmo della Folgore Celeste", 6: "Corpo del Tuono Tribolazionale",
          9: "Nove Ondate del Castigo Celeste"}


def count(conn) -> int:
    return state.get_int(conn, "trib_count", 0)


def charges(conn) -> int:
    return state.get_int(conn, "trib_charges", 0)


def _fulmine(conn, pid: int) -> int:
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key='fulmine';", (pid,)).fetchone()
    return (r["comprehension"] or 0) if r else 0


def preview(conn, pid: int, tier: int | None = None) -> tuple[int, float]:
    from engine.simulation import cultivation
    n = count(conn)
    tier = tier or (cultivation.realm_tier(conn, "player", pid) or 1)
    return 3 + 2 * n, (20 + 12 * tier) * (1 + 0.15 * n)


def absorb_fraction(comp: int) -> float:
    if comp < 100:
        return 0.0
    return min(0.9, 0.2 + (comp - 100) / (comp + 400))


def on_realm_up(conn, t: int, rng: random.Random, player, new_tier: int) -> list[str]:
    if new_tier < MIN_TIER:
        return []
    from engine.simulation import combat
    from engine.systems import items, dao_heart, character, spirit_roots, tribulation
    n = count(conn) + 1
    bolts, per = preview(conn, player.id, new_tier)
    comp = _fulmine(conn, player.id)
    cp = combat.combat_power(conn, "player", player.id)
    resist = cp["defense"] * 0.5 + cp["vitality"] * 0.3 + comp * 0.6
    resist *= 1.0 + 0.05 * sum(1 for _ in tribulation.boon_list(conn, player.id))
    from engine.systems import celestial_elements
    frac = min(0.95, absorb_fraction(comp) + (celestial_elements.tribulation_bonus(conn) if comp >= 100 else 0.0))
    lines = [f"⚡ TRIBOLAZIONE DEL FULMINE CELESTE (la {n}ª): il cielo si oscura, {bolts} folgori si "
             f"preparano a cadere su di te."]
    absorbed = endured = failed = 0
    for i in range(bolts):
        p = per * (1 + 0.08 * i)                     # ogni ondata più forte della precedente
        if rng.random() < frac:
            absorbed += 1
        elif resist * rng.uniform(0.7, 1.3) >= p:
            endured += 1
        else:
            failed += 1
    lines.append(f"  Folgori: {absorbed} assorbite, {endured} rette, {failed} che ti travolgono.")
    eff: dict = {}
    if comp >= 30 and endured + absorbed:
        g = endured + absorbed
        eff.update({"grow_strength": max(1, g // 2), "grow_vitality": max(1, g // 2)})
        lines.append("  Il fulmine TEMPRA il tuo corpo: carne e ossa si purificano.")
        lines.append("  " + dao_heart.purify(conn, 10.0 * g))
        prof = character.get_profile(conn, "player", player.id)
        if prof and (prof["soul_residue"] or 0) > 0:
            conn.execute("UPDATE character_profiles SET soul_residue=MAX(0, soul_residue-?) "
                         "WHERE character_type='player' AND character_id=?;", (15 * g, player.id))
            lines.append("  Il tuono brucia parte della corruzione dell'Abisso.")
    if absorbed:
        eff.update({"dao_key": "fulmine", "dao_gain": 3 * absorbed + n})
        spirit_roots.add(conn, "player", player.id, "fulmine", 2.0 * absorbed)
        conn.execute("UPDATE character_daos SET affinity=MIN(100, affinity+?) WHERE character_type='player' "
                     "AND character_id=? AND dao_key='fulmine';", (absorbed, player.id))
        keep = max(1, absorbed // 2)
        state.set(conn, "trib_charges", str(charges(conn) + keep))
        lines.append(f"  Bevi {absorbed} folgori: il Dao e la radice del Fulmine crescono, e ne trattieni "
                     f"{keep} come FULMINE DELLA TRIBOLAZIONE (cariche: {charges(conn)}).")
    if failed:
        if comp < 30:
            sev = min(10, 2 + failed)
            conn.execute(
                "INSERT INTO injuries (character_type, character_id, severity, description, inflicted_tick, "
                "healed, heal_tick) VALUES ('player', ?, ?, 'ustioni del fulmine celeste', ?, 0, ?);",
                (player.id, sev, t, t + sev * 15))
            conn.execute("UPDATE cultivation_records SET progress=MAX(0, progress-?) WHERE character_type='player' "
                         "AND character_id=?;", (0.1 * failed, player.id))
            lines.append(f"  Il fulmine non ti riconosce: ustioni (gravità {sev}) e parte dell'esperienza bruciata.")
            lines += ["  " + x for x in dao_heart.adjust(conn, -2 * failed)]
        else:
            lines.append("  Le folgori che non reggi ti scottano, ma il tuo Dao del Fulmine ne attutisce il colpo.")
    if failed == 0:
        lines += ["  " + x for x in dao_heart.adjust(conn, 4)]
    if eff:
        lines += ["  " + x for x in items.apply_effects(conn, t, rng, player.id, eff)]
    tech_at = n if n in _TECHS else (n if n % 9 == 0 else None)
    if tech_at and failed <= bolts // 2:
        nm = _TECHS.get(tech_at, f"Castigo Celeste dell'{n}ª Tribolazione")
        lines += ["  " + x for x in items.apply_effects(conn, t, rng, player.id, {"learn_technique": {
            "name": nm, "magnitude": round(0.06 + 0.02 * n, 3), "tech_key": f"tribolazione:{n}"}})]
    state.set(conn, "trib_count", str(n))
    titles = {1: "Sopravvissuto al Fulmine", 3: "Temprato dal Cielo", 9: "Signore delle Nove Ondate",
              27: "Colui che Beve il Castigo"}
    if n in titles and state.grant_title(conn, titles[n]):
        lines.append(f"✧ Nuovo titolo: «{titles[n]}» ✧")
    return lines


def combat(conn, fx) -> list[str]:
    """Il fulmine trattenuto: in ogni scontro ne scateni una carica."""
    c = charges(conn)
    if c <= 0:
        return []
    state.set(conn, "trib_charges", str(c - 1))
    n = count(conn)
    fx.p.atk_mult *= 1.15 + 0.03 * n
    fx.add_proc("p", "stordimento", min(0.5, 0.2 + 0.02 * n), 1.5 + 0.1 * n, "fulmine della tribolazione")
    return [f"⚡ Scateni il FULMINE DELLA TRIBOLAZIONE che custodisci (cariche rimaste: {c - 1})."]


def describe(conn, player) -> str:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    bolts, per = preview(conn, player.id, max(MIN_TIER, tier + 1))
    comp = _fulmine(conn, player.id)
    mode = ("ASSORBIMENTO (bevi il {:.0%} delle folgori)".format(absorb_fraction(comp)) if comp >= 100
            else "TEMPRA (le folgori rette rinforzano il corpo)" if comp >= 30
            else "il fulmine ti è ESTRANEO (ogni folgore non retta ferisce)")
    return ("⚡ TRIBOLAZIONI DEL FULMINE CELESTE\n"
            f"  Affrontate: {count(conn)}   Cariche di fulmine trattenute: {charges(conn)}\n"
            f"  Dao del Fulmine: {comp} — {mode}\n"
            f"  Prossima (al prossimo regno, dal {MIN_TIER}° in su): {bolts} folgori, potenza {per:.0f} crescente")
