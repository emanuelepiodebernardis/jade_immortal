"""
I tre Dao profondi, differenziati per RUOLO (impianto xianxia).

  • SPAZIO  = Dao DISTRUTTIVO. Non fa "più danni": rende inutile la difesa. A
    comprensione crescente perfora la difesa, poi i colpi arrivano istantanei
    (critico/precisione), poi un attacco genera ECHI (colpi multipli), fino al
    dominio in cui la difesa è irrilevante.
  • TEMPO   = Dao della COLTIVAZIONE. Accelera la crescita (più comprendi, più in
    fretta sali). In combattimento aiuta come ausilio: ti muovi "prima" (schivata).
  • DESTINO = Dao della FORTUNA. Piega le probabilità a tuo favore: breakthrough più
    probabili e meno letali, bottini migliori, meno catastrofi.

Più questi Dao salgono, più il Cielo ti percepisce: vedi heaven_defiance() e il
modulo tribulation.py (le tribolazioni divine sono il prezzo del potere).
"""

from __future__ import annotations

import sqlite3

from engine.systems import dao_training as dt


def comp(conn: sqlite3.Connection, dao_key: str, player_id: int = 1) -> int:
    r = conn.execute(
        "SELECT comprehension FROM character_daos WHERE character_type='player' "
        "AND character_id=? AND dao_key=?;", (player_id, dao_key)).fetchone()
    return (r["comprehension"] or 0) if r else 0


def _idx(c: int) -> int:
    """Indice di soglia 0..7 (principiante..legislatore)."""
    return dt._tier_index(c or 0)


# ============================================================
# SPAZIO — supremazia marziale (la difesa non conta)
# ============================================================

def space_combat(conn: sqlite3.Connection, player_id: int = 1) -> dict:
    """Effetti passivi dello Spazio in combattimento, scalati con la comprensione."""
    c = comp(conn, "spazio", player_id)
    if c <= 0:
        return {"pierce": 0.0, "extra_strikes": 0, "crit": 0.0, "label": None}
    i = _idx(c)
    pierce = min(0.95, i * 0.12)            # ignora una quota crescente di difesa
    crit = min(0.45, i * 0.05)              # colpi istantanei: più critici
    # ECHI spaziali: un attacco genera più impatti (idx 4→+1, 6→+2, 7→+3)
    extra = 0
    if i >= 7:
        extra = 3
    elif i >= 6:
        extra = 2
    elif i >= 4:
        extra = 1
    labels = ["", "Distorsione", "Taglio Spaziale", "Frattura dello Spazio",
              "Moltiplicazione Spaziale", "Dominio Spaziale", "Annientamento Spaziale",
              "Spazio Reciso"]
    return {"pierce": pierce, "extra_strikes": extra, "crit": crit,
            "label": labels[min(i, len(labels) - 1)] or None}


# ============================================================
# TEMPO — supremazia nella coltivazione
# ============================================================

def time_cultivation_mult(conn: sqlite3.Connection, player_id: int = 1) -> float:
    """Moltiplicatore di resa della coltivazione/affinamento dato dal Dao del Tempo."""
    c = comp(conn, "tempo", player_id)
    if c <= 0:
        return 1.0
    return 1.0 + _idx(c) * 0.18             # idx 1..7 → +18%..+126%


def time_evasion(conn: sqlite3.Connection, player_id: int = 1) -> float:
    """Frazione di danno schivata in combattimento (il mondo ti sembra lento)."""
    c = comp(conn, "tempo", player_id)
    if c <= 0:
        return 0.0
    return min(0.6, _idx(c) * 0.08)


def time_label(conn, player_id=1) -> str | None:
    c = comp(conn, "tempo", player_id)
    if c <= 0:
        return None
    return ["", "Coltivazione Accelerata", "Compressione Temporale", "Accelerazione Biologica",
            "Camera Temporale", "Breakthrough Temporali", "Dominio Temporale",
            "Eternità in un Battito"][min(_idx(c), 7)] or None


# ============================================================
# DESTINO — supremazia nella causalità (fortuna)
# ============================================================

def fate_idx(conn: sqlite3.Connection, player_id: int = 1) -> int:
    return _idx(comp(conn, "destino", player_id))


def fate_breakthrough(conn: sqlite3.Connection, player_id: int = 1) -> tuple[float, float]:
    """(bonus al successo, moltiplicatore alla morte) del breakthrough dato dal Destino."""
    i = fate_idx(conn, player_id)
    if i <= 0:
        return (0.0, 1.0)
    return (min(0.30, i * 0.04), max(0.25, 1.0 - i * 0.11))


def fate_loot_bonus(conn: sqlite3.Connection, player_id: int = 1) -> float:
    """Probabilità che un drop salga di una classe di rarità (fortuna)."""
    return min(0.6, fate_idx(conn, player_id) * 0.08)


def fate_label(conn, player_id=1) -> str | None:
    i = fate_idx(conn, player_id)
    if i <= 0:
        return None
    return ["", "Piccoli Favori", "Catastrofi Ridotte", "Il Mondo ti Favorisce",
            "Nemici Sfortunati", "Prescelto dei Cieli", "Signore del Fato",
            "Sentenza Inappellabile"][min(i, 7)] or None


# ============================================================
# HEAVEN'S DEFIANCE — la somma che attira il castigo del Cielo
# ============================================================

def heaven_defiance(conn: sqlite3.Connection, player_id: int = 1) -> int:
    """Quanto sfidi le leggi fondamentali: somma delle comprensioni di Spazio+Tempo+Destino.
    Più è alta, più le tribolazioni divine sono frequenti e potenti."""
    return (comp(conn, "spazio", player_id)
            + comp(conn, "tempo", player_id)
            + comp(conn, "destino", player_id))


def defiance_label(d: int) -> str:
    if d <= 0:
        return "nessuna (il Cielo ti ignora)"
    if d < 50:
        return "lieve (qualche presagio)"
    if d < 150:
        return "notevole (il Cielo ti osserva)"
    if d < 400:
        return "grave (il Cielo ti teme)"
    if d < 900:
        return "estrema (il Cielo vuole cancellarti)"
    return "assoluta (sei un nemico delle leggi dell'universo)"


# soglia oltre la quale, salendo, scatta una nuova tribolazione
DEFIANCE_STEP = 80


def tribulation_due(conn: sqlite3.Connection, player_id: int = 1) -> int:
    """Ritorna la POTENZA della tribolazione dovuta (0 se nessuna).
    Scatta quando la sfida al Cielo supera un nuovo gradino dall'ultima tribolazione."""
    from engine.systems import character
    d = heaven_defiance(conn, player_id)
    if d <= 0:
        return 0
    prof = character.get_profile(conn, "player", player_id)
    last = (prof["last_tribulation_defiance"] or 0) if prof else 0
    if d - last < DEFIANCE_STEP:
        return 0
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player_id) or 1
    return tier * 10 + d // 10
