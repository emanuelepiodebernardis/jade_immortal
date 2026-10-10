"""
Inizio e fine di una vita: creazione del personaggio (origine + nome) e, alla morte,
epilogo + scelta di reincarnarsi nello stesso mondo. Interazione da terminale.
"""

from __future__ import annotations

import random

from engine.core import entities
from engine.db import transaction
from engine.systems import character, rebirth


def _ask(prompt: str, default: str = "") -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        return default


def _pick(prompt: str, n: int, default: int = 1) -> int:
    while True:
        raw = _ask(prompt, str(default))
        if raw == "":
            return default
        if raw.isdigit() and 1 <= int(raw) <= n:
            return int(raw)
        print("Scelta non valida.")


def _choose_origin() -> str:
    origins = character.list_origins()
    print("Scegli la tua origine (ogni scelta ha pregi e fardelli):\n")
    for i, (_key, o) in enumerate(origins, 1):
        print(f"  {i}. {o['name']} — {o['desc']}")
    idx = _pick("\nOrigine (numero): ", len(origins))
    return origins[idx - 1][0]


def _choose_name(default: str = "Viandante") -> str:
    name = _ask(f"Come ti chiami? (invio = {default}): ", default)
    name = " ".join(name.split())[:32]
    return name or default


def create_character() -> None:
    """Primo avvio: origine e nome (o preset da config)."""
    with transaction() as conn:
        if character.has_profile(conn):
            return
        preset = character.load_default_origin()
        if preset:
            applied = character.apply_origin(conn, preset, random.Random())
            print(f"\n[Personaggio preimpostato: {applied['name']}]")
            print(character.describe_profile(conn))
            print()
            return
    print("\n=== CREAZIONE DEL PERSONAGGIO ===")
    origin = _choose_origin()
    name = _choose_name()
    with transaction() as conn:
        applied = character.apply_origin(conn, origin, random.Random())
        conn.execute("UPDATE players SET name=? WHERE id=1;", (name,))
        print(f"\nSei {name}. Hai scelto: {applied['name']}.")
        print(character.describe_profile(conn))
        print("Ogni origine porta con sé una storia: 'goals' per seguirla.\n")


def handle_death() -> bool:
    """Mostra l'epilogo e chiede se reincarnarsi. True = si continua a giocare."""
    with transaction() as conn:
        p = entities.get_player(conn)
        row = rebirth.record_death(conn, p)
        print()
        print(rebirth.epilogue_text(row))
        opts = rebirth.inheritance_options(row)
    print("\nIl mondo prosegue senza di te. Ma le anime, qui, non si spengono del tutto.")
    print("  [1] Reincarnati in questo stesso mondo")
    print("  [2] Lascia che il mondo prosegua (esci)")
    if _pick("> ", 2) != 1:
        print("(La tua vita resta negli annali. Al prossimo avvio potrai ancora rinascere.)")
        return False
    print("\n=== UNA NUOVA VITA ===")
    origin = _choose_origin()
    name = _choose_name()
    print("\nCosa porti con te dalla vita passata? (un solo frammento)")
    for i, o in enumerate(opts, 1):
        print(f"  [{i}] {o['label']}")
    inherit = opts[_pick("> ", len(opts)) - 1]
    with transaction() as conn:
        lines = rebirth.reincarnate(conn, random.Random(), origin, name, inherit)
        for ln in lines:
            print(ln)
        print(character.describe_profile(conn))
    return True


def player_is_dead() -> bool:
    with transaction() as conn:
        p = entities.get_player(conn)
        return p is None or p.status != "alive"

