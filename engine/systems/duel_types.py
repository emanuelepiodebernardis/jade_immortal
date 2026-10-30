"""
TIPI E STATI NEL DUELLO (Aggiornamento 69) — il duello «alla Pokémon».

Ogni tecnica ha un ELEMENTO (dal nome: «Folgore…» è fulmine, «Morso dell'Abisso» è abisso…).
Contro l'elemento del nemico (il suo Dao elementale più compreso) una mossa può essere:
  SUPEREFFICACE  ×1.35   (il fuoco fonde il metallo, l'acqua spegne il fuoco…)
  POCO EFFICACE  ×0.75
Se la mossa è del TUO elemento (il tuo Dao elementale migliore) colpisce un po' di più: ×1.1.

Le mosse elementali possono lasciare uno STATO, con i turni che restano:
  sul nemico   🔥 ustione · 🩸 emorragia · ☠ corrosione (perde vita ogni turno)
               ❄ gelo (colpisce più piano) · ⚡ paralisi (può saltare il turno)
               ✺ accecato (può mancarti) · 🌀 confusione (può colpirsi da solo)
  su di te     🌿 rigenerazione (recuperi vita) · ⛰ guscio (subisci meno) · 🌪 slancio (colpisci di più)
Anche il nemico, quando sferra il colpo pesante, può lasciarti addosso il suo elemento.

Tutto vive nel dizionario del duello (d["st_e"], d["st_p"]): nessuna tabella nuova.
Per aggiungere un elemento o uno stato basta una riga in BEATS / STATUS / ON_HIT.
"""

from __future__ import annotations

import random

from engine.systems import art

# chi domina chi (mossa → elementi nemici che subisce di più)
BEATS: dict[str, set[str]] = {
    "fuoco": {"metallo", "legno"}, "metallo": {"legno"}, "legno": {"terra", "acqua"}, "terra": {"acqua", "fulmine"},
    "acqua": {"fuoco"}, "fulmine": {"acqua", "metallo"}, "luce": {"oscurita"}, "oscurita": {"luce"},
    "abisso": {"luce"}, "vento": {"terra"}, "spada": {"legno"}, "sangue": {"legno"}, "anima": {"oscurita"},
}
# elementi del nemico che resistono a una mossa (mossa → elementi nemici che la smorzano)
RESISTS: dict[str, set[str]] = {
    "fuoco": {"acqua", "terra"}, "metallo": {"fuoco"}, "legno": {"metallo", "fuoco"}, "terra": {"legno"},
    "acqua": {"terra", "legno"}, "fulmine": {"terra"}, "vento": {"metallo"}, "spada": {"metallo"},
    "pugno": {"terra", "metallo"}, "corpo": {"metallo"},
}
EL_IT = {"fuoco": "Fuoco", "metallo": "Metallo", "legno": "Legno", "terra": "Terra", "acqua": "Acqua",
         "luce": "Luce", "oscurita": "Oscurità", "fulmine": "Fulmine", "vento": "Vento", "abisso": "Abisso",
         "anima": "Anima", "sangue": "Sangue", "pugno": "Pugno", "corpo": "Corpo", "spada": "Spada"}
EL_ICON = {"fuoco": "🔥", "metallo": "⚙", "legno": "🌿", "terra": "⛰", "acqua": "💧", "luce": "✺", "oscurita": "☾",
           "fulmine": "⚡", "vento": "🌪", "abisso": "🕳", "anima": "👁", "sangue": "🩸", "pugno": "✊", "corpo": "🛡",
           "spada": "🗡"}
SUPER, WEAK, STAB = 1.35, 0.75, 1.1

# stato -> (icona, nome, su chi: "e" nemico / "p" te, turni, effetti)
#   dot: vita persa per turno (frazione del massimo) · heal: vita recuperata · dmg: danno inflitto ×
#   taken: danno subito × · skip: prob. di saltare l'attacco · miss: prob. di mancare · self: prob. di colpirsi
STATUS: dict[str, tuple] = {
    "ustione": ("🔥", "ustione", 3, {"dot": 0.05}),
    "emorragia": ("🩸", "emorragia", 3, {"dot": 0.04}),
    "corrosione": ("☠", "corrosione", 4, {"dot": 0.03, "taken": 1.1}),
    "gelo": ("❄", "gelo", 2, {"dmg": 0.75}),
    "paralisi": ("⚡", "paralisi", 1, {"skip": 0.5}),
    "accecato": ("✺", "accecato", 2, {"miss": 0.3}),
    "confusione": ("🌀", "confusione", 2, {"self": 0.3}),
    "stordito": ("💫", "stordito", 1, {"skip": 0.35}),
    "rigenerazione": ("🌿", "rigenerazione", 3, {"heal": 0.05}),
    "guscio": ("⛰", "guscio", 2, {"taken": 0.75}),
    "slancio": ("🌪", "slancio", 2, {"dmg": 1.2}),
}
# elemento della mossa -> (stato, su chi)
ON_HIT: dict[str, tuple[str, str]] = {
    "fuoco": ("ustione", "e"), "fulmine": ("paralisi", "e"), "acqua": ("gelo", "e"), "luce": ("accecato", "e"),
    "oscurita": ("corrosione", "e"), "abisso": ("corrosione", "e"), "sangue": ("emorragia", "e"),
    "spada": ("emorragia", "e"), "metallo": ("emorragia", "e"), "anima": ("confusione", "e"),
    "pugno": ("stordito", "e"), "legno": ("rigenerazione", "p"), "terra": ("guscio", "p"), "corpo": ("guscio", "p"),
    "vento": ("slancio", "p"),
}
# il colpo pesante del nemico lascia il suo elemento su di te
ENEMY_ON_HIT = {"fuoco": "ustione", "fulmine": "paralisi", "acqua": "gelo", "luce": "accecato", "oscurita": "corrosione",
                "metallo": "emorragia", "legno": "emorragia", "terra": "stordito"}
CHANCE, CHANCE_SUPER, CHANCE_BUFF, CHANCE_ENEMY = 0.35, 0.65, 0.5, 0.35


def move_element(name: str | None, what: str = "tecnica") -> str | None:
    if what != "tecnica" or not name:
        return None
    return art.element_of(name)


def effectiveness(move_el: str | None, foe_el: str | None, my_el: str | None = None) -> tuple[float, str]:
    """(moltiplicatore, "super"/"poco"/"") della mossa contro il nemico."""
    if not move_el:
        return 1.0, ""
    m, tag = 1.0, ""
    if foe_el and foe_el in BEATS.get(move_el, set()):
        m, tag = SUPER, "super"
    elif foe_el and (foe_el in RESISTS.get(move_el, set()) or move_el == foe_el):
        m, tag = WEAK, "poco"
    if my_el and my_el == move_el:
        m *= STAB
    return m, tag


def eff_line(tag: str) -> str:
    return {"super": "  È SUPEREFFICACE!", "poco": "  Non è molto efficace…"}.get(tag, "")


def mod(sts: dict | None, key: str, default: float = 1.0) -> float:
    """Il prodotto (dmg/taken) o la somma (dot/heal/skip/miss/self) degli effetti attivi."""
    sts = sts or {}
    mult = key in ("dmg", "taken")
    v = default if mult else 0.0
    for s, turns in sts.items():
        if turns <= 0 or s not in STATUS:
            continue
        x = STATUS[s][3].get(key)
        if x is None:
            continue
        v = v * x if mult else v + x
    return v if mult else min(0.9, v)


def apply(d: dict, side: str, status: str) -> str:
    """Mette lo stato (o rinfresca i turni). Ritorna la riga del diario."""
    k = "st_e" if side == "e" else "st_p"
    sts = d.setdefault(k, {})
    icon, nome, turns, _fx = STATUS[status]
    fresh = sts.get(status, 0) <= 0
    sts[status] = max(sts.get(status, 0), turns)
    who = d["name"] if side == "e" else "Tu"
    if side == "e":
        return f"  {icon} {who} è colpito da {nome} ({turns} turni)." if fresh else f"  {icon} La {nome} di {who} si rinnova."
    return f"  {icon} {nome.capitalize()} su di te ({turns} turni)." if fresh else f"  {icon} La tua {nome} si rinnova."


def maybe_on_hit(d: dict, move_el: str | None, tag: str, rng: random.Random) -> str:
    if not move_el or move_el not in ON_HIT:
        return ""
    status, side = ON_HIT[move_el]
    p = CHANCE_BUFF if side == "p" else (CHANCE_SUPER if tag == "super" else CHANCE)
    if rng.random() >= p:
        return ""
    d["_stato"] = status
    return apply(d, side, status)


def enemy_on_hit(d: dict, foe_el: str | None, rng: random.Random) -> str:
    st = ENEMY_ON_HIT.get(foe_el or "")
    if not st or rng.random() >= CHANCE_ENEMY:
        return ""
    return apply(d, "p", st)


def tick(d: dict) -> list[str]:
    """Fine turno: danni e cure degli stati, poi scendono i turni. Gli stati non ti uccidono mai (resti a 1)."""
    lines: list[str] = []
    dot_e = mod(d.get("st_e"), "dot")
    if dot_e and d["hp_e"] > 0:
        x = d["emax"] * dot_e
        d["hp_e"] -= x
        lines.append(f"  {d['name']} perde {round(x)} per i suoi stati.")
    dot_p, heal_p = mod(d.get("st_p"), "dot"), mod(d.get("st_p"), "heal")
    if dot_p:
        x = min(d["pmax"] * dot_p, max(0.0, d["hp_p"] - 1))
        d["hp_p"] -= x
        if x:
            lines.append(f"  Perdi {round(x)} per i tuoi stati.")
    if heal_p:
        x = min(d["pmax"] * heal_p, d["pmax"] - d["hp_p"])
        d["hp_p"] += x
        if x > 0:
            lines.append(f"  🌿 Recuperi {round(x)}.")
    for k in ("st_e", "st_p"):
        sts = d.get(k) or {}
        d[k] = {s: t - 1 for s, t in sts.items() if t - 1 > 0}
    return lines


def badges(sts: dict | None) -> list[dict]:
    return [{"k": s, "icon": STATUS[s][0], "nome": STATUS[s][1], "turni": t}
            for s, t in (sts or {}).items() if s in STATUS and t > 0]


def card_info(name: str | None, foe_el: str | None, my_el: str | None) -> dict:
    el = move_element(name)
    m, tag = effectiveness(el, foe_el, my_el)
    out = {"el": el or "", "el_icon": EL_ICON.get(el or "", ""), "el_nome": EL_IT.get(el or "", ""), "eff": tag}
    if el and el in ON_HIT:
        s, side = ON_HIT[el]
        out["stato"] = f"{STATUS[s][0]} {STATUS[s][1]}" + (" (su di te)" if side == "p" else "")
    return out
