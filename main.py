"""
Jade Immortal — entry point CLI.

Avvio: inizializza schema, genera il mondo se vuoto, fa creare il personaggio
(scelta dell'origine) se non esiste ancora, poi lancia il loop.
"""

from __future__ import annotations

from engine.db import init_db
from engine.generators.world_gen import generate_if_empty
from engine.cli.lifecycle import create_character
from engine.cli.loop import run


def main() -> None:
    init_db()
    if generate_if_empty():
        print("[Nuovo mondo generato]")
    create_character()
    run()


if __name__ == "__main__":
    main()
