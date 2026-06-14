"""
Narrazione dei combattimenti.

Genera frasi preimpostate in base alla DIFFERENZA di potenza tra i contendenti:
divari enormi -> vittoria in un istante; forze vicine -> lungo scontro incerto.
Così il combattimento "racconta" la differenza statistica, senza bisogno dell'LLM.
"""

from __future__ import annotations

import random


def power_of(conn, ctype, cid) -> float:
    from engine.simulation import combat
    p = combat.combat_power(conn, ctype, cid)
    return p["attack"] * 1.2 + p["defense"] + p["vitality"] * 0.5


def clash_line(conn, winner_name, loser_name, winner_pc, loser_pc,
               rounds: int = 0, rng: random.Random | None = None) -> str:
    """Frase che descrive uno scontro già risolto, dal punto di vista del vincitore."""
    rng = rng or random.Random()
    wp = power_of(conn, *winner_pc)
    lp = power_of(conn, *loser_pc)
    ratio = wp / max(1.0, lp)
    if ratio >= 2.0:
        flavor = rng.choice([
            f"{loser_name} viene travolto: un solo colpo e tutto è finito.",
            f"La distanza è abissale: {loser_name} cade prima ancora di reagire.",
        ])
    elif ratio >= 1.4:
        flavor = rng.choice([
            f"Pochi scambi e {loser_name} è a terra: nessuna vera contesa.",
            f"{winner_name} domina con colpi devastanti; {loser_name} non tiene il ritmo.",
        ])
    elif ratio >= 1.12:
        flavor = rng.choice([
            f"Dopo un confronto acceso, {winner_name} trova l'apertura e piega {loser_name}.",
            f"{winner_name} è più rapido nei momenti decisivi e ha la meglio su {loser_name}.",
        ])
    else:
        flavor = rng.choice([
            f"Decine di scambi, entrambi feriti: alla fine {winner_name} la spunta per un soffio.",
            f"Una lotta lunga e incerta; {winner_name} prevale a fatica su {loser_name}.",
        ])
    return flavor


def match_line(conn, me_name, opp_name, me_pc, opp_pc,
               rng: random.Random | None = None) -> tuple[bool, str]:
    """Esito (vinco?) + frase, per un incontro di torneo. Varianza inclusa."""
    rng = rng or random.Random()
    mp = power_of(conn, *me_pc) * rng.uniform(0.85, 1.15)
    op = power_of(conn, *opp_pc) * rng.uniform(0.85, 1.15)
    win = mp >= op
    ratio = (mp / max(1.0, op)) if win else (op / max(1.0, mp))
    if win:
        if ratio >= 1.6:
            t = f"Travolgi {opp_name}: non regge il tuo slancio."
        elif ratio >= 1.2:
            t = f"Sconfiggi {opp_name} dopo uno scambio deciso."
        else:
            t = f"Lotti alla pari con {opp_name} e vinci per un soffio."
    else:
        if ratio >= 1.6:
            t = f"{opp_name} ti travolge: troppo più forte."
        elif ratio >= 1.2:
            t = f"{opp_name} ha la meglio dopo un buon scambio."
        else:
            t = f"Cedi a {opp_name} per un soffio, dopo una lotta lunga."
    return win, t
