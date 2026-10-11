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


def _choose_destiny(life_no: int = 1) -> str:
    from engine.systems import destinies
    rng = random.Random()
    rerolls = 2
    while True:
        hand = destinies.draw_hand(rng, life_no)
        print("\nIl tuo DESTINO alla nascita (scegline uno):")
        for i, k in enumerate(hand, 1):
            print(f"  {i}. {destinies.label(k)}")
        extra = f"  0. Rimescola il destino ({rerolls} rimasti)" if rerolls else ""
        if extra:
            print(extra)
        raw = _ask("Destino (numero): ", "1")
        if raw == "0" and rerolls:
            rerolls -= 1
            continue
        if raw.isdigit() and 1 <= int(raw) <= len(hand):
            return hand[int(raw) - 1]
        if raw == "":
            return hand[0]
        print("Scelta non valida.")


def _choose_rivals() -> str:
    from engine.systems import destinies
    keys = list(destinies.RIVAL_LEVELS)
    print("\nQuanto sono TALENTUOSI i tuoi rivali (compagni di setta, nemesi)?")
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k.capitalize()} — {destinies.RIVAL_LEVELS[k][1]}")
    return keys[_pick("Rivali (numero, invio = normale): ", len(keys), default=2) - 1]


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
    destiny = _choose_destiny(1)
    name = _choose_name()
    rivals = _choose_rivals()
    hard = _ask("\nModalità SENZA RITORNO (la morte è definitiva)? [s/N]: ", "n").lower().startswith("s")
    with transaction() as conn:
        from engine.systems import destinies
        if hard:
            rebirth.set_hardcore(conn, True)
        applied = character.apply_origin(conn, origin, random.Random())
        d = destinies.apply(conn, destiny)
        destinies.set_rival_level(conn, rivals)
        conn.execute("UPDATE players SET name=? WHERE id=1;", (name,))
        print(f"\nSei {name}. Hai scelto: {applied['name']}, destino «{d['name']}».")
        from engine.systems import constitutions
        for ln in constitutions.roll_at_birth(conn, random.Random(), origin):
            print(ln)
        print(character.describe_profile(conn))
        print("Ogni origine porta con sé una storia: 'goals' per seguirla. Prima volta? Scrivi 'tutorial'.\n")


def handle_death() -> bool:
    """Mostra l'epilogo e chiede se reincarnarsi. True = si continua a giocare."""
    with transaction() as conn:
        p = entities.get_player(conn)
        saved = rebirth.try_phoenix(conn, p)
        if saved:
            print(saved)
            return True
        row = rebirth.record_death(conn, p)
        life_next = rebirth.life_no(conn) + 1
        print()
        print(rebirth.epilogue_text(row))
        opts = rebirth.inheritance_options(row)
        hard = rebirth.hardcore(conn)
    if hard:
        print("\n☠ SENZA RITORNO: la tua storia finisce qui. Il mondo va negli annali.")
        print("  [1] Comincia un NUOVO MONDO")
        print("  [2] Esci")
        if _pick("> ", 2) != 1:
            print("(Al prossimo avvio potrai cominciare un nuovo mondo.)")
            return False
        name = rebirth.archive_world()
        print(f"Il vecchio mondo è conservato in database/saves/{name}.")
        from engine.db import init_db
        from engine.generators.world_gen import generate_if_empty
        init_db()
        generate_if_empty()
        create_character()
        return True
    print("\nIl mondo prosegue senza di te. Ma le anime, qui, non si spengono del tutto.")
    print("  [1] Reincarnati in questo stesso mondo")
    print("  [2] Lascia che il mondo prosegua (esci)")
    if _pick("> ", 2) != 1:
        print("(La tua vita resta negli annali. Al prossimo avvio potrai ancora rinascere.)")
        return False
    print("\n=== UNA NUOVA VITA ===")
    origin = _choose_origin()
    destiny = _choose_destiny(life_next)
    name = _choose_name()
    with transaction() as conn:
        nfr = rebirth.fragments_allowed(conn, len(opts) - 1)
    print(f"\nCosa porti con te dalla vita passata? (fino a {nfr} frammenti)")
    for i, o in enumerate(opts, 1):
        print(f"  [{i}] {o['label']}")
    inherit = [opts[_pick("Primo frammento: ", len(opts)) - 1]]
    while inherit[0]["key"] != "none" and len(inherit) < nfr and len(opts) > 2:
        raw = _ask("Un altro frammento (numero, invio = basta così): ", "")
        if not (raw.isdigit() and 1 <= int(raw) <= len(opts)):
            break
        o = opts[int(raw) - 1]
        if o not in inherit and o["key"] != "none":
            inherit.append(o)
    with transaction() as conn:
        lines = rebirth.reincarnate(conn, random.Random(), origin, name, inherit,
                                    destiny=destiny)
        for ln in lines:
            print(ln)
        print(character.describe_profile(conn))
    return True


def player_is_dead() -> bool:
    with transaction() as conn:
        p = entities.get_player(conn)
        return p is None or p.status != "alive"



def restart_requested() -> bool:
    from engine.systems import state
    with transaction() as conn:
        return state.get(conn, rebirth.RESTART_KEY) == "1"


def restart_world() -> None:
    """'ricomincia conferma': il mondo va in archivio e ne nasce uno nuovo, con un nuovo personaggio."""
    name = rebirth.archive_world()
    print(f"Il vecchio mondo è conservato in database/saves/{name}.")
    from engine.db import init_db
    from engine.generators.world_gen import generate_if_empty
    init_db()
    generate_if_empty()
    create_character()
