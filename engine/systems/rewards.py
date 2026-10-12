"""
PREMI — un solo generatore per tornei, eredità, gratitudine, saghe.

  grant(conn, rng, player, rank=1, scale=1.0, kinds=None)

  rank   1 = il premio più alto (oro), 2 argento, 3 bronzo, 4+ partecipazione
  scale  moltiplicatore (sette più alte, mondi superiori, fasi finali)
  kinds  quali tipi possono uscire (default: tutti)

Tutto cresce col regno del giocatore: senza tetto, come il resto del gioco.
"""

from __future__ import annotations

import random

from engine.systems import items, sects, state

RARITY = ["comune", "non_comune", "raro", "prezioso", "leggendario"]
_PILL_ADJ = ["della Nebbia Azzurra", "dei Nove Soli", "del Loto di Giada", "della Fenice Rossa",
             "del Respiro Celeste", "della Montagna Antica", "dei Mille Fiumi", "del Drago Assopito"]
_PILL_NOUN = ["Pillola", "Elisir", "Perla", "Sfera"]
_MANUAL = ["Rotolo", "Canone", "Manuale", "Scrittura"]
_MANUAL_OF = ["della Spada che Fende le Nubi", "del Pugno delle Sette Montagne", "del Passo d'Ombra",
              "del Respiro del Tuono", "della Lancia Solitaria", "del Palmo di Brace", "delle Mille Foglie"]
_TREASURE = [("Specchio", "della Luna Rovesciata"), ("Campana", "del Tempio Sommerso"),
             ("Ventaglio", "delle Tre Tempeste"), ("Sigillo", "del Re dei Monti"),
             ("Fiasca", "della Sorgente Infinita"), ("Pagoda", "delle Nove Prigioni")]


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def _rarity(rank: int, scale: float, rng) -> str:
    base = {1: 3, 2: 2, 3: 1}.get(rank, 0) + (1 if scale >= 2 else 0)
    if rng.random() < 0.2:
        base += 1
    return RARITY[max(0, min(len(RARITY) - 1, base))]


def grant(conn, rng: random.Random, player, rank: int = 1, scale: float = 1.0,
          kinds: list[str] | None = None, stones: bool = True) -> list[str]:
    tier = _tier(conn, player.id)
    ridx = RARITY.index(_rarity(rank, scale, rng))
    rar = RARITY[ridx]
    lines = []
    if stones:
        n = int((120 if rank == 1 else 70 if rank == 2 else 40 if rank == 3 else 15) * tier * scale)
        sects.grant_resource(conn, "pietre_spirituali", n, player.id)
        lines.append(f"💰 {n} pietre spirituali")
    pool = kinds or ["pillola", "essenza", "manuale", "nucleo", "tesoro"]
    if rank >= 4:
        pool = [k for k in pool if k in ("pillola", "nucleo")] or pool
    n_items = 3 if rank == 1 else 2 if rank == 2 else 1
    for _ in range(n_items):
        k = rng.choice(pool)
        it = _make(rng, k, tier, ridx, scale)
        iid = items.create_item(conn, it["name"], it["type"], rar, it["desc"], it["eff"])
        items.grant(conn, "player", player.id, iid)
        lines.append(f"{_ICON.get(k, '✧')} {it['name']} ({rar.replace('_', ' ')})")
        _remember(conn, it["name"], k, rar, it["desc"])
    return lines


_ICON = {"pillola": "💊", "essenza": "☸", "manuale": "📜", "nucleo": "◆", "tesoro": "🏺"}


def _make(rng, kind: str, tier: int, ridx: int, scale: float) -> dict:
    p = 1 + 0.35 * ridx
    if kind == "pillola":
        return {"name": f"{rng.choice(_PILL_NOUN)} {rng.choice(_PILL_ADJ)}", "type": "pillola",
                "desc": "Fa avanzare la coltivazione.",
                "eff": {"cultivation_progress": round((0.2 + 0.06 * tier) * p * min(2.0, scale), 2)}}
    if kind == "essenza":
        dao = rng.choice(["spada", "fuoco", "fulmine", "anima", "corpo", "vento", "acqua", "terra", "luce"])
        return {"name": f"Essenza del Dao «{dao}»", "type": "essenza", "desc": f"Approfondisce il Dao «{dao}».",
                "eff": {"dao_key": dao, "dao_gain": int((4 + 2 * tier) * p)}}
    if kind == "manuale":
        nm = f"{rng.choice(_MANUAL)} {rng.choice(_MANUAL_OF)}"
        mag = round((0.05 + 0.02 * tier) * p, 3)
        return {"name": nm, "type": "manuale", "desc": f"Insegna una tecnica (+{int(mag * 100)}% potenza).",
                "eff": {"learn_technique": {"name": nm, "magnitude": mag,
                                            "tech_key": f"prize:{rng.randint(1, 10 ** 9)}"}}}
    if kind == "nucleo":
        stat = rng.choice(["grow_strength", "grow_vitality", "grow_resistance", "grow_soul"])
        word = {"grow_strength": "Forza", "grow_vitality": "Vitalità", "grow_resistance": "Resistenza",
                "grow_soul": "Anima"}[stat]
        return {"name": f"Nucleo di {word}", "type": "nucleo", "desc": f"Innesta {word.lower()} permanente.",
                "eff": {stat: int((2 + tier) * p)}}
    a, b = rng.choice(_TREASURE)
    return {"name": f"{a} {b}", "type": "tesoro", "desc": "Un tesoro antico: usarlo ne libera l'essenza.",
            "eff": {"cultivation_progress": round((0.15 + 0.05 * tier) * p, 2), "grow_soul": int(tier * p),
                    "dao_key": rng.choice(["anima", "spazio", "tempo", "destino", "luce"]), "dao_gain": int(3 * p)}}


def _remember(conn, name: str, kind: str, rarity: str, desc: str) -> None:
    """Il Libro (codex) ricorda ogni tesoro ottenuto."""
    book = state.get_json(conn, "world_book_items", {}) or {}
    e = book.get(name) or {"kind": kind, "rarity": rarity, "desc": desc, "n": 0}
    e["n"] = e.get("n", 0) + 1
    book[name] = e
    state.set_json(conn, "world_book_items", book)
