"""
DESTINI DELLO SFONDAMENTO (Aggiornamento 63) — a ogni nuovo regno, il Cielo ti offre tre strade.

Quando sfondi in un regno nuovo, nel momento in cui il corpo si ricompone, il Cielo ti mostra TRE
destini: ne scegli UNO, ed è tuo per tutta la vita. Più alto è il regno, più spesso compaiono destini
rari, epici e leggendari; alcuni hanno un prezzo. Ogni vita diventa una via diversa.
(L'idea viene dai «destini di sfondamento» di Tale of Immortal.)

Gli effetti si sommano tra loro e passano dal bilancio della potenza come gli altri doni:
  cult     coltivazione (+%)            atk      attacco (+%)
  taken    danni subiti (−%)            evade    schivata
  crit     critici                      strikes  colpi in più
  lethal   colpi mortali evitati        bt       riuscita degli sfondamenti
  years    anni di vita (subito)        stones   pietre ogni giorno (× regno)
  heart    cuore del Dao (subito)       karma    karma (subito)

  destini_sfondamento   i destini scelti in questa vita
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "bt_fates"
PENDING = "bt_fates_offer"
RARITY = ("comune", "raro", "epico", "leggendario")
ICON = {"comune": "·", "raro": "◆", "epico": "✦", "leggendario": "★"}

FATES = [
    # comuni
    ("respiro_lungo", "Respiro Lungo", "comune", "Il tuo respiro si allunga: coltivazione +6%.", {"cult": 0.06}),
    ("pugno_saldo", "Pugno Saldo", "comune", "Colpisci più a fondo: attacco +6%.", {"atk": 0.06}),
    ("pelle_coriacea", "Pelle Coriacea", "comune", "La carne si indurisce: danni subiti −5%.", {"taken": 0.05}),
    ("passo_leggero", "Passo Leggero", "comune", "Ti muovi come foglia: schivata +3%.", {"evade": 0.03}),
    ("occhio_attento", "Occhio Attento", "comune", "Vedi le crepe: critici +4%.", {"crit": 0.04}),
    ("radici_profonde", "Radici Profonde", "comune", "Il corpo ricorda: sfondamenti +3%.", {"bt": 0.03}),
    ("vita_lunga", "Vita Lunga", "comune", "Il Cielo ti concede tempo: +40 anni di vita.", {"years": 40}),
    ("mani_fortunate", "Mani Fortunate", "comune", "Le pietre ti cercano: pietre ogni giorno.", {"stones": 6}),
    # rari
    ("vento_del_dao", "Vento del Dao", "raro", "La coltivazione scorre: +12%.", {"cult": 0.12}),
    ("lama_interiore", "Lama Interiore", "raro", "Attacco +12%.", {"atk": 0.12}),
    ("ossa_di_ferro", "Ossa di Ferro", "raro", "Danni subiti −10%.", {"taken": 0.10}),
    ("ombra_fugace", "Ombra Fugace", "raro", "Schivata +6%, critici +4%.", {"evade": 0.06, "crit": 0.04}),
    ("cuore_limpido", "Cuore Limpido", "raro", "Sfondamenti +6%, e il cuore si quieta.", {"bt": 0.06, "heart": 10}),
    ("sangue_bollente", "Sangue Bollente", "raro", "Attacco +20%, ma subisci il 5% in più.", {"atk": 0.20, "taken": -0.05}),
    ("eco_doppio", "Eco Doppio", "raro", "A volte colpisci due volte: un colpo in più.", {"strikes": 1}),
    ("tesoriere", "Tesoriere del Cielo", "raro", "Pietre ogni giorno, abbondanti.", {"stones": 15}),
    ("mille_anni", "Mille Anni", "raro", "+150 anni di vita.", {"years": 150}),
    # epici
    ("corpo_immortale", "Corpo che Non Cade", "epico", "Una volta per scontro, un colpo mortale non ti uccide.", {"lethal": 1}),
    ("tempesta_di_lame", "Tempesta di Lame", "epico", "Attacco +18%, critici +8%.", {"atk": 0.18, "crit": 0.08}),
    ("sorgente_infinita", "Sorgente Infinita", "epico", "Coltivazione +22%.", {"cult": 0.22}),
    ("guscio_di_tartaruga", "Guscio della Tartaruga Nera", "epico", "Danni subiti −16%.", {"taken": 0.16}),
    ("figlio_della_fortuna", "Figlio della Fortuna", "epico", "Sfondamenti +10%, schivata +5%.", {"bt": 0.10, "evade": 0.05}),
    ("via_demoniaca", "Patto con l'Abisso", "epico", "Attacco +30%, coltivazione +10%, ma il karma precipita.",
     {"atk": 0.30, "cult": 0.10, "karma": -60}),
    ("asceta", "Voto dell'Asceta", "epico", "Coltivazione +30%, ma attacco −10%.", {"cult": 0.30, "atk": -0.10}),
    # leggendari
    ("prescelto", "Prescelto dal Cielo", "leggendario", "Coltivazione +25%, sfondamenti +10%, +300 anni.",
     {"cult": 0.25, "bt": 0.10, "years": 300}),
    ("re_della_guerra", "Re della Guerra", "leggendario", "Attacco +30%, un colpo in più, danni subiti −10%.",
     {"atk": 0.30, "strikes": 1, "taken": 0.10}),
    ("fenice", "Cuore di Fenice", "leggendario", "Due colpi mortali evitati per scontro, danni subiti −8%.",
     {"lethal": 2, "taken": 0.08}),
    ("caos_primordiale", "Scintilla del Caos", "leggendario", "Un po' di tutto: +15% coltivazione, +15% attacco, "
                                                               "−8% danni, +5% critici, +5% schivata.",
     {"cult": 0.15, "atk": 0.15, "taken": 0.08, "crit": 0.05, "evade": 0.05}),
]
BY_KEY = {f[0]: f for f in FATES}


def _weights(tier: int) -> dict:
    return {"comune": max(10, 60 - 5 * tier), "raro": 28 + tier, "epico": 6 + 2 * tier,
            "leggendario": 1 + max(0, tier - 3)}


def chosen(conn) -> list[str]:
    return [k for k in (state.get_json(conn, KEY, []) or []) if k in BY_KEY]


def total(conn, what: str) -> float:
    return sum(BY_KEY[k][4].get(what, 0) for k in chosen(conn))


def draw(rng: random.Random, tier: int, have: list[str], n: int = 3) -> list[str]:
    w = _weights(tier)
    pool = [f for f in FATES if f[0] not in have]
    out: list[str] = []
    for _ in range(n):
        cand = [f for f in pool if f[0] not in out]
        if not cand:
            break
        f = rng.choices(cand, weights=[w[f[2]] for f in cand])[0]
        out.append(f[0])
    return out


def on_realm_up(conn, player, tier: int) -> list[str]:
    """Al nuovo regno: tre destini in attesa di scelta (la scena si apre appena sei libero)."""
    t = tick_mod.get_tick(conn)
    offer = draw(random.Random(t * 31 + tier), tier, chosen(conn))
    if not offer:
        return []
    q = state.get_json(conn, PENDING, []) or []
    q.append({"tier": tier, "offer": offer})
    state.set_json(conn, PENDING, q)
    return ["✧ Mentre il corpo si ricompone, il Cielo ti mostra tre strade. (Destini dello sfondamento)"]


def after_command(conn, player) -> list[str]:
    from engine.systems import encounters
    q = state.get_json(conn, PENDING, []) or []
    if not q or encounters.pending(conn) or player is None:
        return []
    o = q[0]
    choices = []
    for k in o["offer"]:
        f = BY_KEY[k]
        choices.append({"label": f"{ICON[f[2]]} {f[1]} ({f[2]}) — {f[3]}", "effects": {"bt_fate": k}})
    sc = {"key": "destino_sfondamento", "title": f"Il destino del {o['tier']}° regno", "event_type": "fortune",
          "sticky": True,
          "text": ("Il nuovo regno si apre come un fiore. Per un istante, oltre il tuo corpo, vedi tre fili di "
                   "destino tesi nel vuoto. Puoi afferrarne uno solo, e sarà tuo per tutta la vita."),
          "choices": choices}
    txt = encounters.start_scene(conn, player, sc)
    if txt:
        state.set_json(conn, PENDING, q[1:])
        return [txt]
    return []


def take(conn, t: int, rng, player, key: str) -> list[str]:
    from engine.systems import encounters
    if key not in BY_KEY:
        return []
    have = chosen(conn)
    have.append(key)
    state.set_json(conn, KEY, have)
    f = BY_KEY[key]
    out = [f"{ICON[f[2]]} Afferri il destino «{f[1]}»: {f[3]}"]
    now = {k: v for k, v in f[4].items() if k in ("years", "heart", "karma")}
    if now.get("years"):
        out += encounters.apply_effects(conn, t, rng, player, {"lifespan_years": now["years"]}, {})
    if now.get("heart") or now.get("karma"):
        out += encounters.apply_effects(conn, t, rng, player, {k: v for k, v in now.items() if k != "years"}, {})
    if f[2] == "leggendario":
        state.grant_title(conn, f"Toccato dal Destino: {f[1]}")
    return out


# ---------------------------------------------------------------- effetti

def cultivation_mult(conn) -> tuple[float, str]:
    c = total(conn, "cult")
    return (1.0 + c, "i destini dello sfondamento") if c else (1.0, "")


def bt_bonus(conn) -> float:
    return total(conn, "bt")


def combat(conn, fx) -> list[str]:
    if not chosen(conn):
        return []
    fx.p.atk_mult *= max(0.5, 1.0 + total(conn, "atk"))
    for k, what in (("taken", "taken"), ("evade", "evade"), ("crit", "crit")):
        v = total(conn, k)
        if v:
            fx.p.prof[what] = fx.p.prof.get(what, 0.0) + v
    s = int(total(conn, "strikes"))
    if s:
        fx.p.prof["extra_strikes"] = fx.p.prof.get("extra_strikes", 0) + s
    fx.p.lethal_saves += int(total(conn, "lethal"))
    return []


def daily(conn, t: int, rng, player) -> list[str]:
    s = total(conn, "stones")
    if s and player is not None:
        from engine.systems import sects
        from engine.simulation import cultivation
        tier = cultivation.realm_tier(conn, "player", player.id) or 1
        sects.grant_resource(conn, "pietre_spirituali", int(s * tier), player.id)
    return []


def describe(conn, player=None) -> str:
    ks = chosen(conn)
    if not ks:
        return "Non hai ancora scelto destini dello sfondamento: a ogni nuovo regno il Cielo te ne offre tre."
    lines = ["✧ I DESTINI DELLO SFONDAMENTO (per questa vita)"]
    for k in ks:
        f = BY_KEY[k]
        lines.append(f"  {ICON[f[2]]} {f[1]} ({f[2]}) — {f[3]}")
    return "\n".join(lines)


def lines_for_menu(conn) -> list[str]:
    return [f"{ICON[BY_KEY[k][2]]} {BY_KEY[k][1]} — {BY_KEY[k][3]}" for k in chosen(conn)]
