"""
Reputazione — lo strato SOCIALE: come il mondo ti vede.

Distinta dal karma (peso morale nascosto/cosmico). Qui tre scalari pubblici, tutti >= 0:
  - fame      : gloria (tornei vinti, giustizia, imprese davanti a testimoni)
  - infamy    : disonore (innocenti uccisi in pubblico, cadaveri divorati, tradimenti)
  - suspicion : sospetto sull'Abisso (assorbire con testimoni, divorare alleati)

Da questi emergono un ALLINEAMENTO PERCEPITO (Eroe..Eretico) e un TITOLO.
Una MASCHERA permette di agire senza che le malefatte ricadano sul tuo nome:
contiene il sospetto, non lo annulla del tutto.

Coerente con lo stile del gioco: i numeri restano nascosti, a schermo si mostrano
etichette qualitative.
"""

from __future__ import annotations

import sqlite3

CAP = 100000

# soglie di sospetto (min, messaggio)
SUSPICION_TIERS = [
    (0, ""),
    (100, "Girano strane voci sul tuo conto."),
    (250, "Gli anziani delle sette ti osservano con sospetto."),
    (500, "È stata aperta un'indagine sulla tua natura."),
    (1000, "Sei additato come eretico dell'Abisso."),
]

# reazione sociale degli NPC per allineamento (fama scalda, infamia raffredda)
_SOCIAL = {"Eroe": 1.5, "Onorevole": 1.2, "Neutrale": 1.0,
           "Temuto": 0.6, "Mostro": 0.3, "Eretico": 0.1}


def get(conn: sqlite3.Connection, player_id: int = 1) -> dict:
    r = conn.execute(
        "SELECT fame, infamy, suspicion, disguised FROM character_profiles "
        "WHERE character_type='player' AND character_id=?;", (player_id,)).fetchone()
    if r is None:
        return {"fame": 0, "infamy": 0, "suspicion": 0, "disguised": 0}
    return {"fame": r["fame"] or 0, "infamy": r["infamy"] or 0,
            "suspicion": r["suspicion"] or 0, "disguised": r["disguised"] or 0}


def adjust(conn: sqlite3.Connection, player_id: int = 1, *,
           fame: int = 0, infamy: int = 0, suspicion: int = 0) -> dict:
    cur = get(conn, player_id)
    nf = max(0, min(CAP, cur["fame"] + fame))
    ni = max(0, min(CAP, cur["infamy"] + infamy))
    ns = max(0, min(CAP, cur["suspicion"] + suspicion))
    conn.execute(
        "UPDATE character_profiles SET fame=?, infamy=?, suspicion=? "
        "WHERE character_type='player' AND character_id=?;", (nf, ni, ns, player_id))
    return {"fame": nf, "infamy": ni, "suspicion": ns, "disguised": cur["disguised"]}


def is_disguised(conn: sqlite3.Connection, player_id: int = 1) -> bool:
    return bool(get(conn, player_id)["disguised"])


def witnesses(conn: sqlite3.Connection, location_id: int,
              exclude_id: int | None = None) -> list[sqlite3.Row]:
    """NPC umani vivi che possono VEDERTI agire (le bestie/creature non fanno
    girare voci): sono questi i testimoni che contano per la reputazione."""
    rows = conn.execute(
        "SELECT id, name FROM npcs WHERE location_id=? AND status='alive' "
        "AND (kind='human' OR kind IS NULL) ORDER BY id;", (location_id,)).fetchall()
    return [r for r in rows if r["id"] != exclude_id]


def set_disguise(conn: sqlite3.Connection, player_id: int = 1, on: bool = True) -> None:
    conn.execute(
        "UPDATE character_profiles SET disguised=? "
        "WHERE character_type='player' AND character_id=?;",
        (1 if on else 0, player_id))


def alignment(fame: int, infamy: int, suspicion: int) -> str:
    if suspicion >= 1000 or infamy >= 600:
        return "Eretico"
    if infamy >= 300 and infamy >= fame:
        return "Mostro"
    if infamy >= 120 and infamy > fame:
        return "Temuto"
    if fame >= 300 and infamy < fame:
        return "Eroe"
    if fame >= 100 and infamy < fame:
        return "Onorevole"
    return "Neutrale"


def alignment_of(conn: sqlite3.Connection, player_id: int = 1) -> str:
    r = get(conn, player_id)
    return alignment(r["fame"], r["infamy"], r["suspicion"])


def social_factor(conn: sqlite3.Connection, player_id: int = 1) -> float:
    return _SOCIAL.get(alignment_of(conn, player_id), 1.0)


def suspicion_hint(suspicion: int) -> str:
    out = ""
    for thr, msg in SUSPICION_TIERS:
        if suspicion >= thr:
            out = msg
    return out


def title(conn: sqlite3.Connection, player_id: int = 1) -> str | None:
    r = get(conn, player_id)
    al = alignment(r["fame"], r["infamy"], r["suspicion"])
    from engine.systems import character
    p = character.get_profile(conn, "player", player_id)
    devourer = bool(p and p["anomaly"] == "abisso_divoratore")
    return {
        "Eretico": "Il Divoratore Nero" if devourer else "L'Eretico",
        "Mostro": "Il Flagello dell'Abisso" if devourer else "Il Mostro",
        "Temuto": "Il Temuto",
        "Eroe": "Difensore del Regno",
        "Onorevole": "Il Coltivatore Onorevole",
    }.get(al)


# ============================================================
# IDENTITÀ MASCHERATA — una reputazione SEPARATA.
# Le malefatte commesse col volto coperto non ricadono sul tuo nome: alimentano
# invece l'infamia di un alter ego (la "maschera"). Karma e progressi restano sul
# vero te; ciò che il mondo teme è una figura che non sa essere te.
# ============================================================

MASK_NAME = "Coltivatore Misterioso"


def get_mask(conn: sqlite3.Connection, player_id: int = 1) -> dict:
    r = conn.execute(
        "SELECT mask_fame, mask_infamy, mask_suspicion FROM character_profiles "
        "WHERE character_type='player' AND character_id=?;", (player_id,)).fetchone()
    if r is None:
        return {"fame": 0, "infamy": 0, "suspicion": 0}
    return {"fame": r["mask_fame"] or 0, "infamy": r["mask_infamy"] or 0,
            "suspicion": r["mask_suspicion"] or 0}


def adjust_mask(conn: sqlite3.Connection, player_id: int = 1, *,
                fame: int = 0, infamy: int = 0, suspicion: int = 0) -> dict:
    cur = get_mask(conn, player_id)
    nf = max(0, min(CAP, cur["fame"] + fame))
    ni = max(0, min(CAP, cur["infamy"] + infamy))
    ns = max(0, min(CAP, cur["suspicion"] + suspicion))
    conn.execute(
        "UPDATE character_profiles SET mask_fame=?, mask_infamy=?, mask_suspicion=? "
        "WHERE character_type='player' AND character_id=?;", (nf, ni, ns, player_id))
    return {"fame": nf, "infamy": ni, "suspicion": ns}


def apply_deed(conn: sqlite3.Connection, player_id: int = 1, *,
               fame: int = 0, infamy: int = 0, suspicion: int = 0,
               mask_leak: int = 0) -> dict:
    """Registra una malefatta/impresa ROUTANDOLA all'identità giusta.
    - a volto scoperto: tutto ricade sul tuo nome (reputazione reale);
    - mascherato: fama/infamia/sospetto vanno alla MASCHERA; solo una piccola
      frazione di sospetto (`mask_leak`) trapela sul vero te — la maschera contiene,
      non annulla l'impronta dell'Abisso.
    Ritorna {'identity': 'real'|'mask', ...valori aggiornati...}.
    """
    if is_disguised(conn, player_id):
        vals = adjust_mask(conn, player_id, fame=fame, infamy=infamy, suspicion=suspicion)
        if mask_leak:
            adjust(conn, player_id, suspicion=mask_leak)
        return {"identity": "mask", **vals}
    vals = adjust(conn, player_id, fame=fame, infamy=infamy, suspicion=suspicion)
    return {"identity": "real", **vals}


def mask_alignment_of(conn: sqlite3.Connection, player_id: int = 1) -> str:
    r = get_mask(conn, player_id)
    return alignment(r["fame"], r["infamy"], r["suspicion"])


def mask_title(conn: sqlite3.Connection, player_id: int = 1) -> str | None:
    r = get_mask(conn, player_id)
    al = alignment(r["fame"], r["infamy"], r["suspicion"])
    return {
        "Eretico": "Lo Spettro dell'Abisso",
        "Mostro": "Il Demone Mascherato",
        "Temuto": "L'Ombra Temuta",
        "Eroe": "L'Eroe Senza Volto",
        "Onorevole": "Il Cavaliere Mascherato",
    }.get(al)


def mask_line(conn: sqlite3.Connection, player_id: int = 1) -> str | None:
    """Riga qualitativa sull'identità mascherata (None se la maschera non ha storia)."""
    r = get_mask(conn, player_id)
    if not (r["fame"] or r["infamy"] or r["suspicion"]):
        return None
    al = alignment(r["fame"], r["infamy"], r["suspicion"])
    t = mask_title(conn, player_id)
    name = f'{MASK_NAME}' + (f' — "{t}"' if t else "")
    extra = ""
    sh = suspicion_hint(r["suspicion"])
    if sh:
        extra = " " + sh
    return f"Identità mascherata ({name}): allineamento {al}.{extra}"


def fame_talent_bonus(conn: sqlite3.Connection, player_id: int = 1) -> int:
    """La fama apre le porte: piccolo bonus al test del talento delle sette."""
    return min(8, get(conn, player_id)["fame"] // 80)


def fame_word(value: int) -> str:
    if value <= 0:
        return "ignota"
    if value < 60:
        return "modesta"
    if value < 180:
        return "discreta"
    if value < 400:
        return "notevole"
    return "leggendaria"


def line(conn: sqlite3.Connection, player_id: int = 1) -> str | None:
    """Riga qualitativa per status/profilo (None se tutto a zero e volto scoperto)."""
    r = get(conn, player_id)
    if not (r["fame"] or r["infamy"] or r["suspicion"] or r["disguised"]):
        return None
    al = alignment(r["fame"], r["infamy"], r["suspicion"])
    t = title(conn, player_id)
    parts = [f"Reputazione: {al}" + (f' — "{t}"' if t else "")]
    sh = suspicion_hint(r["suspicion"])
    if sh:
        parts.append(sh)
    if r["disguised"]:
        parts.append("(in incognito)")
    return " ".join(parts)
