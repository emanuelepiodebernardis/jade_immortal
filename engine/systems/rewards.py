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
          kinds: list[str] | None = None, stones: bool = True, n: int | None = None) -> list[str]:
    n_req = n                                     # quanti oggetti (None = secondo il piazzamento)
    tier = _tier(conn, player.id)
    ridx = RARITY.index(_rarity(rank, scale, rng))
    rar = RARITY[ridx]
    lines = []
    if stones:
        n = int((120 if rank == 1 else 70 if rank == 2 else 40 if rank == 3 else 15) * tier * scale)
        sects.grant_resource(conn, "pietre_spirituali", n, player.id)
        lines.append(f"💰 {n} pietre spirituali")
    pool = kinds or ["pillola", "essenza", "manuale", "nucleo", "tesoro", "incenso"]
    if rank >= 4:
        pool = [k for k in pool if k in ("pillola", "nucleo")] or pool
    n_items = n_req if n_req is not None else (3 if rank == 1 else 2 if rank == 2 else 1)
    for i in range(n_items):
        k = pool[i % len(pool)] if n_req is not None and n_req <= len(pool) else rng.choice(pool)
        special = _special(conn, rng, player, k, tier, ridx)
        if special is not None:
            lines += special
            continue
        it = _make(rng, k, tier, ridx, scale)
        iid = items.create_item(conn, it["name"], it["type"], rar, it["desc"], it["eff"])
        items.grant(conn, "player", player.id, iid)
        lines.append(f"{_ICON.get(k, '✧')} {it['name']} ({rar.replace('_', ' ')})")
        _remember(conn, it["name"], k, rar, it["desc"])
    if rank == 1 and rng.random() < 0.02:            # rarissimo: una reliquia delle razze antiche
        from engine.systems import race_realms
        rid, rn = race_realms.relic_item(conn, rng.choice(list(race_realms.BLOOD)), rng, 1)
        items.grant(conn, "player", player.id, rid)
        lines.append(f"🏺 {rn} (reliquia, leggendario)")
    if rank == 1 and rng.random() < 0.04:            # rarissimo: un'arte proibita
        from engine.systems import dominion
        items.grant(conn, "player", player.id, dominion.salma_manual(conn))
        lines.append("☠ Canone del Ritorno della Salma (leggendario)")
        _remember(conn, "Canone del Ritorno della Salma", "manuale", "leggendario", "Arte proibita delle salme.")
    return lines


def _special(conn, rng, player, kind: str, tier: int, ridx: int) -> list[str] | None:
    """I premi che non sono oggetti generici: reliquie delle razze, sangue nobile, corpi leggendari."""
    if kind == "reliquia":
        from engine.systems import race_realms
        rid, rn = race_realms.relic_item(conn, rng.choice(list(race_realms.BLOOD)), rng, max(1, ridx - 1))
        items.grant(conn, "player", player.id, rid)
        return [f"🏺 {rn} (reliquia)"]
    if kind == "sangue":
        from engine.systems import bloodlines
        fam = rng.choice(["drago", "fenice", "qilin", "kun", "nove code", "bai ze", "tigre bianca", "tartaruga nera",
                          "uccello vermiglio", "drago azzurro", "pixiu", "suanni"][:6 + 2 * ridx])
        sp = bloodlines.FAMILIES[fam][0]
        els = [bloodlines.FAMILY_ELEMENT.get(fam, "corpo")]
        nm = f"Essenza di Sangue di {sp}"
        iid = items.create_item(conn, nm, "essenza", RARITY[min(4, ridx + 1)], "Sangue nobile: assorbilo con 'use'.",
                                {"bloodline": {"species": sp, "elements": els, "gain": round(8 * (1 + ridx) * (1 + 0.3 * tier), 1)}})
        items.grant(conn, "player", player.id, iid)
        return [f"🩸 {nm}"]
    if kind == "corpo":
        from engine.systems import constitutions
        keys = [k for k in constitutions.BODIES if k != "spezzati"]
        key = rng.choices(keys, weights=[constitutions.BODIES[k][3] for k in keys])[0]
        nm = constitutions.BODIES[key][0]
        iid = items.create_item(conn, f"Essenza del Corpo: {nm}", "essenza_corpo", "leggendario",
                                f"L'essenza di un {nm}. Assorbila con 'use'.", {"body_essence": key})
        items.grant(conn, "player", player.id, iid)
        return [f"✦ Essenza del Corpo: {nm} (leggendario)"]
    return None


_ICON = {"pillola": "💊", "essenza": "☸", "manuale": "📜", "nucleo": "◆", "tesoro": "🏺", "incenso": "🌀"}
_INCENSE = ["Incenso del Mare Quieto", "Incenso dei Mille Pensieri", "Incenso della Lanterna d'Anima",
            "Incenso del Sonno di Giada", "Incenso del Loto Silente"]


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
    if kind == "incenso":
        return {"name": rng.choice(_INCENSE), "type": "pillola", "desc": "Tempra lo spirito (la forza dell'anima).",
                "eff": {"soul_xp": round((10 + 6 * tier) * p * min(2.0, scale), 1)}}
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
