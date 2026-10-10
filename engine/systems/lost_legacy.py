"""
IL RETAGGIO SPEZZATO — ciò che ti è stato tolto, e che ti riprendi pezzo dopo pezzo.

All'inizio di ogni vita una parte del tuo talento non è più tua: qualcuno l'ha rubata,
sigillata o spezzata. È il filo rosso della tua storia: ogni FRAMMENTO ritrovato ti
restituisce potere e svela un pezzo di verità. I frammenti li custodiscono persone e luoghi
che incontrerai salendo di regno; quando li hai ripresi tutti, il retaggio non torna solo
com'era: RINASCE più forte, e un nuovo ciclo di frammenti (sempre più potenti) ti attende.
Senza fine.

I retaggi (come nei grandi romanzi):
  Osso Supremo strappato        (Perfect World)        attacco e tecnica dell'osso
  Anima Primordiale frantumata  (anime in frammenti)   anima e comprensione dei Dao
  Vene Celesti sigillate        (talento sigillato)    velocità di coltivazione
  Pupilla Doppia strappata      (occhi rubati)         critici, vedere l'invisibile
  Fortuna rubata                (destino depredato)    fortuna, bottini, incontri
  Memorie sigillate             (vita precedente)      a ogni frammento una tecnica e un Dao
  Seme del Dao spezzato         (Dao interrotto)       tutti i Dao crescono più in fretta

  retaggio        cosa ti è stato tolto, cosa hai recuperato, dove cercare il prossimo frammento
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "lost_legacy"
FRAGMENTS = 5
LEGACIES = {
    "osso": ("Osso Supremo", "Il tuo Osso Supremo ti fu strappato dal petto quando eri bambino.",
             ["un cugino invidioso del clan", "il Gran Sacerdote che lo trapiantò", "il principe che lo porta in sé",
              "l'antico che ne beve l'essenza", "il Cielo stesso, che lo voleva per sé"]),
    "anima": ("Anima Primordiale", "La tua anima primordiale fu frantumata: vivi con una scheggia sola.",
              ["un collezionista di anime", "la lanterna di un tempio sepolto", "un demone che ne ha divorato un pezzo",
               "lo specchio di un re caduto", "il fiume del samsara"]),
    "vene": ("Vene Celesti", "Nascesti con Vene Celesti, ma qualcuno le sigillò strato dopo strato.",
             ["la nutrice che obbediva a un clan rivale", "un sigillo inciso dal tuo stesso padre per proteggerti",
              "l'anziano che ti dichiarò «spazzatura»", "la setta che temeva il tuo talento", "una volontà dal cielo"]),
    "pupilla": ("Pupilla Doppia", "Avevi la Pupilla Doppia, e te la strapparono dagli occhi.",
                ["un erede che la porta come sua", "un mercante d'occhi delle terre del sud",
                 "un cieco che con essa vede il futuro", "il Patriarca di una setta demoniaca", "chi vede oltre il Cielo"]),
    "fortuna": ("Fortuna", "La tua fortuna fu depredata: un rituale la travasò in qualcun altro.",
                ["il «figlio del destino» che ne vive", "lo sciamano che officiò il rito", "la tartaruga che tiene il conto",
                 "il clan che ne prospera", "la stella che la custodisce"]),
    "memorie": ("Memorie della Vita Precedente", "Eri qualcuno di grande, prima. I ricordi sono sigillati in frammenti.",
                ["un vecchio amico che ti riconosce", "la tua tomba di un'altra era", "la donna che ti aspettò",
                 "il nemico che ti uccise", "te stesso, diecimila anni fa"]),
    "seme": ("Seme del Dao", "Il tuo seme del Dao fu spezzato prima che germogliasse.",
             ["un albero che ne ha bevuto un frammento", "un eremita che lo studia da secoli",
              "una bestia che ne ha mangiato un pezzo", "la setta che lo custodisce come reliquia", "il Dao stesso"]),
}


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def assign(conn, rng: random.Random) -> list[str]:
    key = rng.choice(list(LEGACIES))
    _save(conn, {"key": key, "cycle": 1, "found": 0, "holder": None, "holder_loc": None})
    nm, intro, _h = LEGACIES[key]
    return [f"Il tuo retaggio spezzato: {nm}. {intro} ('retaggio')"]


def total(d: dict) -> int:
    return (d["cycle"] - 1) * FRAGMENTS + d["found"]


def _next_tier(d: dict) -> int:
    return 1 + total(d) + d["cycle"]          # il prossimo frammento si mostra a questo regno


def penalty(conn) -> float:
    d = get(conn)
    if not d:
        return 1.0
    return 0.85 if total(d) == 0 else 1.0


def cultivation_mult(conn) -> tuple[float, str]:
    d = get(conn)
    if not d:
        return 1.0, ""
    k = total(d)
    if k == 0:
        return 0.85, f"il retaggio perduto ({LEGACIES[d['key']][0]})"
    m = 1.0 + (0.08 if d["key"] == "vene" else 0.03) * k
    return m, f"il retaggio ritrovato ({LEGACIES[d['key']][0]})"


def dao_mult(conn) -> float:
    d = get(conn)
    if not d:
        return 1.0
    k = total(d)
    return 1.0 + (0.06 if d["key"] in ("seme", "anima") else 0.01) * k


def combat(conn, fx) -> list[str]:
    d = get(conn)
    if not d or total(d) == 0:
        return []
    k = total(d)
    pr = fx.p.prof
    if d["key"] == "osso":
        fx.p.atk_mult *= 1.0 + 0.05 * k
        fx.add_proc("p", "emorragia", min(0.45, 0.1 + 0.02 * k), 1.2 + 0.1 * k, "osso supremo")
    elif d["key"] == "pupilla":
        pr["crit"] = pr.get("crit", 0.0) + 0.02 * k
        fx.add_proc("p", "confusione", min(0.4, 0.08 + 0.02 * k), 1.0, "pupilla doppia")
    elif d["key"] == "anima":
        fx.add_proc("p", "pressione", min(0.4, 0.08 + 0.02 * k), 1.0 + 0.1 * k, "anima primordiale")
    else:
        fx.p.atk_mult *= 1.0 + 0.02 * k
    return []


def fortune_bonus(conn) -> int:
    d = get(conn)
    return 4 * total(d) if d and d["key"] == "fortuna" else 0


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import npc_factory
    from engine.simulation import cultivation
    d = get(conn)
    if not d:
        return []
    out = []
    if d.get("holder"):
        r = conn.execute("SELECT status FROM npcs WHERE id=?;", (d["holder"],)).fetchone()
        if not r or r["status"] != "alive":
            out += recover(conn, t, rng, player)
        return out
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    if tier >= _next_tier(d):
        nm, _i, holders = LEGACIES[d["key"]]
        who = holders[d["found"] % len(holders)]
        loc = conn.execute("SELECT id, name FROM locations WHERE id<>? ORDER BY RANDOM() LIMIT 1;",
                           (player.location_id,)).fetchone()
        nid = npc_factory.spawn(conn, rng, archetype="anziano", location_id=loc["id"],
                                tier=tier + (d["cycle"] - 1), stage=rng.randint(5, 9), traits={"pride": 85})
        d["holder"], d["holder_loc"] = nid, loc["id"]
        _save(conn, d)
        hn = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
        out.append(f"✦ Il tuo retaggio ({nm}) vibra: senti un frammento vicino. Lo custodisce {who} — {hn}, a {loc['name']}. "
                   "('retaggio')")
    return out


def recover(conn, t: int, rng, player) -> list[str]:
    from engine.systems import items
    d = get(conn)
    nm, _i, holders = LEGACIES[d["key"]]
    d["found"] += 1
    d["holder"] = d["holder_loc"] = None
    out = [f"✦ Hai ripreso un frammento del tuo retaggio — {nm} ({d['found']}/{FRAGMENTS}, ciclo {d['cycle']})."]
    k = total(d)
    if d["key"] == "memorie":
        out += items.apply_effects(conn, t, rng, player.id, {"learn_technique": {
            "name": f"Ricordo della Vita Precedente ({k})", "magnitude": round(0.05 + 0.01 * k, 3),
            "tech_key": f"memorie:{k}"}, "dao_key": "random", "dao_gain": 5 + k})
    elif d["key"] == "fortuna":
        out.append("La fortuna torna a scorrere verso di te: gli incontri ti sorridono di più.")
    else:
        out += items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": round(0.3 + 0.05 * k, 2)})
    if d["found"] >= FRAGMENTS:
        d["cycle"] += 1
        d["found"] = 0
        out.append(f"✦✦ Il tuo retaggio — {nm} — è INTERO — e non si ferma: rinasce più grande di prima (ciclo {d['cycle']}). "
                   "Altri frammenti, più antichi, ti chiamano da lontano.")
        state.grant_title(conn, f"{nm} Restituito" if d["cycle"] == 2 else f"{nm} Rinato ({d['cycle'] - 1})")
    _save(conn, d)
    return out


def describe(conn, player) -> str:
    from engine.cli.loop import _first_step_toward
    d = get(conn)
    if not d:
        return "Nulla ti è stato tolto, in questa vita."
    nm, intro, _h = LEGACIES[d["key"]]
    lines = [f"⚱ RETAGGIO SPEZZATO — {nm}", f"  {intro}",
             f"  Frammenti ripresi: {d['found']}/{FRAGMENTS} (ciclo {d['cycle']}, totale {total(d)})"]
    if d.get("holder"):
        hn = conn.execute("SELECT name, location_id FROM npcs WHERE id=?;", (d["holder"],)).fetchone()
        loc = hn["location_id"] or d["holder_loc"]
        ln = conn.execute("SELECT name FROM locations WHERE id=?;", (loc,)).fetchone()["name"] if loc else "?"
        step = _first_step_toward(conn, player.location_id, loc) if loc else None
        lines.append(f"  Il prossimo frammento lo custodisce {hn['name']}, a {ln}"
                     + (f" (vai verso {step})." if step else " (è qui!)."))
    else:
        lines.append(f"  Il prossimo frammento si farà sentire quando raggiungerai il regno {_next_tier(d)}.")
    if total(d) == 0:
        lines.append("  Finché non ne ritrovi almeno uno, coltivi più lentamente (×0.85).")
    return "\n".join(lines)
