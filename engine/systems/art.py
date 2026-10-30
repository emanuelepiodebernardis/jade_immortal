"""
LE IMMAGINI DEL GIOCO (Aggiornamento 68) — quale quadro mostrare per un oggetto, una mossa, una scena.

Le immagini stanno nella cartella «immagini» (oggetti/, azioni/, scene/, trasformazioni/, reliquie/…).
Qui si decide soltanto il NOME da cercare: per ogni cosa una lista di candidati, dal più preciso al più
generico. La dashboard mostra il primo che esiste; se nessuno esiste, non mostra nulla (o il suo disegno).

  item_keys(nome, tipo)         «Spada raffinata (regno 4)» → oggetti/arma_spada, oggetti/arma
  action_key(mossa, nome)       «Scateni Folgore della Tribolazione» → azioni/fulmine
  scene_keys(scena, tipo_trama) «vendetta» → scene/vendetta, scene/combat
"""

from __future__ import annotations

import unicodedata

# parole nel nome → elemento dell'azione (l'ordine conta: la prima che compare vince)
ELEMENT_WORDS = [
    ("tribolazione", "fulmine"), ("folgore", "fulmine"), ("fulmine", "fulmine"), ("tuono", "fulmine"),
    ("fuoco", "fuoco"), ("fiamm", "fuoco"), ("fenice", "fuoco"), ("sole", "fuoco"),
    ("ghiaccio", "acqua"), ("gelo", "acqua"), ("acqua", "acqua"), ("mare", "acqua"), ("onda", "acqua"),
    ("vento", "vento"), ("tempesta", "vento"),
    ("terra", "terra"), ("montagna", "terra"), ("roccia", "terra"), ("pietra", "terra"),
    ("metallo", "metallo"), ("oro", "metallo"), ("lame", "metallo"),
    ("legno", "legno"), ("foresta", "legno"), ("radic", "legno"),
    ("luce", "luce"), ("sacro", "luce"), ("stell", "luce"),
    ("oscur", "oscurita"), ("ombra", "oscurita"), ("notte", "oscurita"),
    ("abisso", "abisso"), ("divora", "abisso"), ("morso", "abisso"),
    ("anima", "anima"), ("spirito", "anima"), ("mente", "anima"),
    ("sangue", "sangue"), ("lignaggio", "sangue"),
    ("pugn", "pugno"), ("palmo", "pugno"),
    ("corpo", "corpo"), ("titano", "corpo"), ("bronzo", "corpo"),
    ("spada", "spada"), ("lama", "spada"), ("sciabola", "spada"), ("lancia", "spada"),
]
BASE_ACTION = {"colpisci": "colpo", "difendi": "difesa", "concentrati": "concentrazione", "pillola": "pillola",
               "fuggi": "fuga"}
WEAPON_WORDS = [("spada", "spada"), ("lancia", "lancia"), ("sciabola", "sciabola"), ("arco", "arco"),
                ("pugn", "pugno"), ("guant", "pugno"), ("bastone", "bastone")]


def _low(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def element_of(name: str) -> str | None:
    n = _low(name)
    for w, el in ELEMENT_WORDS:
        if w in n:
            return el
    return None


def action_key(what: str, name: str | None = None) -> str:
    """L'immagine della mossa del giocatore."""
    if what in BASE_ACTION:
        return "azioni/" + BASE_ACTION[what]
    return "azioni/" + (element_of(name or "") or "colpo")


def item_keys(name: str, kind: str, rarity: str = "") -> list[str]:
    n = _low(name)
    k = (kind or "").lower()
    out: list[str] = []
    if k == "arma":
        w = next((v for word, v in WEAPON_WORDS if word in n), None)
        if w:
            out.append(f"oggetti/arma_{w}")
        out.append("oggetti/arma_spada")
    elif k == "pillola":
        if rarity in ("leggendario", "prezioso") or "erede" in n or "dao" in n:
            out.append("oggetti/pillola_leggendaria")
        out.append("oggetti/pillola")
    elif k == "essenza":
        if "sangue" in n or "lignaggio" in n:
            out.append("oggetti/essenza_sangue")
        if "dao" in n:
            out.append("oggetti/essenza_dao")
        out.append("oggetti/essenza")
    elif k == "nucleo":
        if "demon" in n or "cuore" in n:
            out.append("oggetti/nucleo_demone")
        if "spiritual" in n or "anima" in n or "spettr" in n:
            out.append("oggetti/nucleo_spirito")
        out.append("oggetti/nucleo")
    elif k == "tesoro":
        if "pietre" in n:
            out.append("oggetti/pietre")
        out.append("oggetti/tesoro")
    elif k == "reliquia":
        for race in ("drag", "demon", "spirit", "gigant", "mare", "leviat"):
            if race in n:
                out.append("reliquie/" + {"drag": "draghi", "demon": "demoni", "spirit": "spiriti", "gigant": "giganti",
                                          "mare": "maree", "leviat": "maree"}[race])
        out.append("oggetti/reliquia")
    elif k in ("manuale", "talismano", "formazione", "uovo", "incenso"):
        out.append("oggetti/" + k)
    out.append("oggetti/tesoro")
    return out


# i capitoli e le scene più note hanno un quadro loro; poi il tipo di trama; poi il tipo di scena
SCENE_ALIAS = {"duello": "momenti/duello", "giudizio_cielo": "scene/giudizio", "demone_interiore": "scene/demone_interiore",
               "destino_sfondamento": "scene/destino_sfondamento", "marea_bestie": "scene/marea_bestie",
               "invasione": "scene/assedio", "tempesta_fulmini": "scene/tribolazione", "tribolazione_altrui": "scene/tribolazione",
               "trib_strike": "azioni/tribolazione_colpo", "battaglia_anima": "scene/anima", "vendetta": "scene/vendetta",
               "vendetta_reame": "scene/vendetta", "nemesi": "scene/vendetta", "arcinemico": "scene/vendetta",
               "caverna_eredita": "scene/eredita", "tomba_generale": "scene/eredita", "reame": "scene/reame",
               "reame_eredita": "scene/reame", "possessione": "scene/possessione", "maledizione": "scene/maledizione",
               "patto_demoniaco": "scene/demoniaco", "mercante_pillole": "scene/social", "bisca": "scene/social",
               "frutto_spirituale": "scene/fortune", "fiore_anima": "scene/fortune", "lago_yin": "scene/grotta"}
PREFIX = {"compagni": "scene/reame", "anello": "scene/anima", "pagoda": "scene/anima", "stendardo": "scene/anima",
          "calderone": "scene/anima", "perla": "scene/possessione", "vaso": "scene/anima", "saga": "scene/story",
          "intrigo": "scene/intrigo", "eco": "scene/story", "trama": "scene/intrigo", "torre": "scene/torre",
          "dimora": "scene/dimora"}


def scene_keys(key: str | None, event_type: str | None = None, plot_kind: str | None = None) -> list[str]:
    out: list[str] = []
    k = (key or "").lower()
    if k:
        out.append("scene/" + k)
        if k in SCENE_ALIAS:
            out.append(SCENE_ALIAS[k])
        p = k.split("_")[0]
        if plot_kind:
            out.append("scene/" + plot_kind)
        if p in PREFIX:
            out.append(PREFIX[p])
    elif plot_kind:
        out.append("scene/" + plot_kind)
    if event_type:
        out.append("scene/" + event_type)
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


FAMILY_IMG = {"drago": "drago", "fenice": "fenice", "qilin": "qilin", "demone": "demone", "silvano": "silvano",
              "gigante": "gigante", "leviatano": "leviatano"}


def equipment(conn, player) -> list[dict]:
    """Ciò che porti addosso: l'arma, i vasi d'anima, i sigilli, la cavalcatura, il Corpo del Dharma."""
    out: list[dict] = []
    try:
        from engine.systems import weapons
        wk = weapons.get_weapon(conn, player.id)
        if wk:
            info = weapons.describe(conn, player.id) if hasattr(weapons, "describe") else ""
            out.append({"slot": "Arma", "nome": weapons.WEAPONS.get(wk, (wk, wk.capitalize()))[1],
                        "nota": (info.splitlines()[0] if info else ""), "img": [f"oggetti/arma_{wk}", "oggetti/arma_spada"],
                        "cmd": "arma"})
    except Exception:                                   # noqa: BLE001
        pass
    try:
        from engine.systems import mentor_ring, soul_artifacts, soul_arcs
        if mentor_ring.get(conn) and not (mentor_ring.get(conn) or {}).get("gone"):
            out.append({"slot": "Anello", "nome": soul_arcs.NAMES["anello"], "nota": "un'anima ti parla dall'anello",
                        "img": ["oggetti/anello"], "cmd": "via anime"})
        for k in soul_artifacts.owned(conn):
            out.append({"slot": "Vaso d'anima", "nome": soul_arcs.NAMES.get(k, k), "nota": "",
                        "img": [f"oggetti/{k}"], "cmd": "via anime"})
    except Exception:                                   # noqa: BLE001
        pass
    try:
        from engine.systems import ancestral_sigils as sg
        d = sg.get(conn)
        for k in d["eq"][: sg.slots(conn)]:
            h = sg.HOUSES[k // 4][0]
            out.append({"slot": "Sigillo", "nome": sg.sigil_name(k), "nota": f"★{d['owned'].get(str(k), 1)}",
                        "img": [f"oggetti/sigillo_{h}"], "cmd": "sigilli"})
    except Exception:                                   # noqa: BLE001
        pass
    try:
        from engine.systems import dharma_body
        dd = dharma_body.get(conn)
        if dd.get("awake"):
            out.append({"slot": "Corpo del Dharma", "nome": dharma_body.form(conn).capitalize(),
                        "nota": f"grado {dd['grade']}", "img": ["oggetti/dharma"], "cmd": "dharma"})
    except Exception:                                   # noqa: BLE001
        pass
    try:
        from engine.systems import mounts
        m = mounts.mounted(conn, player.id)
        if m:
            nm = m["name"] if isinstance(m, dict) and "name" in m else str(m)
            low = _low(nm)
            w = next((b for b in ("drago", "fenice", "tigre", "tartaruga", "qilin", "gru", "volpe", "serpente", "kun")
                      if b in low), None)
            out.append({"slot": "Cavalcatura", "nome": nm, "nota": "", "img": [f"bestie/{w}"] if w else ["creature/beast"],
                        "cmd": "smonta"})
    except Exception:                                   # noqa: BLE001
        pass
    return out
