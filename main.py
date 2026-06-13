"""
Jade Immortal — entry point CLI.

Avvio: inizializza schema, genera il mondo se vuoto, fa creare il personaggio
(scelta dell'origine) se non esiste ancora, poi lancia il loop.
"""

from __future__ import annotations

import random

from engine.db import init_db, transaction
from engine.generators.world_gen import generate_if_empty
from engine.systems import character
from engine.cli.loop import run


def _create_character() -> None:
    """Chiede l'origine al primo avvio (o usa il preset da config) e applica gli effetti."""
    with transaction() as conn:
        if character.has_profile(conn):
            return
        # preset: origine di default da config -> salta la scelta
        preset = character.load_default_origin()
        if preset:
            applied = character.apply_origin(conn, preset, random.Random())
            print(f"\n[Personaggio preimpostato: {applied['name']}]")
            print(character.describe_profile(conn))
            print()
            return
        origins = character.list_origins()
        print("\n=== CREAZIONE DEL PERSONAGGIO ===")
        print("Scegli la tua origine (ogni scelta ha pregi e fardelli):\n")
        for i, (key, o) in enumerate(origins, 1):
            print(f"  {i}. {o['name']} — {o['desc']}")
        choice = None
        while choice is None:
            try:
                raw = input("\nOrigine (numero): ").strip()
            except (EOFError, KeyboardInterrupt):
                raw = "1"
            if raw.isdigit() and 1 <= int(raw) <= len(origins):
                choice = origins[int(raw) - 1][0]
            else:
                print("Scelta non valida.")
        applied = character.apply_origin(conn, choice, random.Random())
        print(f"\nHai scelto: {applied['name']}.")
        print(character.describe_profile(conn))
        print()


def main() -> None:
    init_db()
    if generate_if_empty():
        print("[Nuovo mondo generato]")
    _create_character()
    run()


if __name__ == "__main__":
    main()
