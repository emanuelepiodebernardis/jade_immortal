"""
DAO SUPERIORI — non si scelgono: si RISVEGLIANO.

Ispirati alle "leggi" ricorrenti nella narrativa xianxia (Karma/Causalità, Samsara,
Vita e Morte, Massacro, Yin-Yang/Taiji, Caos/Wuji, Sangue, Illusione, Stelle, Vuoto,
Creazione). Ognuno ha un MODO SPECIALE per essere sbloccato, legato a ciò che fai
nel mondo — non basta meditare:

  Karma         → un karma enorme, nel bene o nel male (|karma| ≥ 300)
  Massacro      → 60 vite tolte in combattimento
  Vita e Morte  → vincere 3 volte sull'orlo della morte (meno del 15% di forze)
  Reincarnazione→ vivere la terza vita (o il Reincarnato che fonde le sue due anime)
  Yin-Yang      → Luce e Oscurità entrambe ≥ 50
  Caos          → tutti e cinque gli elementi del ciclo ≥ 25
  Sangue        → divorare 15 coltivatori (Abisso) o un fiume di sangue innocente
  Illusione     → Dao dell'Anima ≥ 100 con un'anima eccezionale
  Stelle        → Destino ≥ 50 e Spazio ≥ 25
  Vuoto         → Spazio ≥ 250
  Creazione     → Legno, Terra e Acqua ≥ 50, oppure maestria in una professione

Al risveglio il Dao entra con comprensione 10: da lì si allena con 'comprehend' come
gli altri, partecipa alle fusioni leggendarie e porta il suo stato in combattimento
(vedi combat_states.STATE_OF_DAO).
"""

from __future__ import annotations

import sqlite3

from engine.systems import state

# chiave -> (suggerimento criptico, testo del risveglio)
SUPERIOR = {
    "karma": ("Ogni azione lascia un filo. Quando i fili saranno troppi, li vedrai.",
              "Vedi i fili: ogni vita è legata alle altre da cause ed effetti. Chi ha peccato "
              "porta il peso del suo debito — e tu puoi riscuoterlo."),
    "massacro": ("Chi toglie abbastanza vite smette di contarle.",
                 "Il sangue versato non si lava: si trasforma in intento. I nemici tremano "
                 "prima ancora che tu colpisca."),
    "vita_morte": ("Cammina più volte sul confine, e torna indietro.",
                   "Sei stato sul confine tante volte da capirne la legge: vita e morte sono "
                   "due rive dello stesso fiume."),
    "samsara": ("La ruota gira. Alla terza vita, ricorderai il suo moto.",
                "Ricordi la ruota: nascere, morire, rinascere. Ciò che è tuo ritorna."),
    "yinyang": ("Luce e ombra, se le possiedi entrambe, smettono di combattersi.",
                "Luce e Oscurità si inseguono dentro di te e diventano un cerchio: il Taiji."),
    "caos": ("Prima dei Cinque Elementi c'era il nulla che li conteneva tutti.",
             "Il ciclo dei Cinque Elementi si chiude e si dissolve nel Wuji: il Caos primordiale."),
    "sangue": ("Il sangue altrui, se ne bevi abbastanza, comincia a parlarti.",
               "Il sangue che hai preso ti parla. Ora sai come chiamarlo a te."),
    "illusione": ("Un'anima abbastanza vasta può sognare il mondo.",
                  "Il mondo ti appare come un sogno — e i sogni si possono piegare."),
    "stelle": ("Chi legge il Destino e piega lo Spazio può leggere il cielo.",
               "Il firmamento è una mappa: ora sai dove il fato degli altri è debole."),
    "vuoto": ("Piega lo Spazio fino al punto in cui non resta nulla.",
              "Oltre lo Spazio c'è il Vuoto: lì nessuna legge, nessuna difesa, nessun dono vale."),
    "creazione": ("Chi nutre, sostiene e disseta — o chi plasma con le proprie mani — crea.",
                  "Comprendi come le cose nascono. Ciò che tocchi può guarire, proteggere, crescere."),
}

AWAKEN_COMP = 10


def _comp(conn, pid, key) -> int:
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' "
                     "AND character_id=? AND dao_key=?;", (pid, key)).fetchone()
    return (r["comprehension"] or 0) if r else 0


def has(conn, pid, key) -> bool:
    return _comp(conn, pid, key) > 0


# ---------- contatori ----------

def bump(conn, key: str, n: int = 1) -> int:
    v = state.get_int(conn, key, 0) + n
    state.set(conn, key, str(v))
    return v


def on_kill(conn, npc_kind: str | None) -> None:
    bump(conn, "kills_total")
    if npc_kind in (None, "human"):
        bump(conn, "kills_human")


def on_win(conn, hp_frac: float) -> None:
    if hp_frac < 0.15:
        bump(conn, "near_death_wins")


# ---------- condizioni ----------

def _cond(conn, pid, key) -> bool:
    from engine.systems import karma, character, rebirth, storyline
    c = lambda k: _comp(conn, pid, k)  # noqa: E731
    if key == "karma":
        return abs(karma.get_karma(conn, "player", pid)) >= 300
    if key == "massacro":
        return state.get_int(conn, "kills_total") >= 60
    if key == "vita_morte":
        return state.get_int(conn, "near_death_wins") >= 3
    if key == "samsara":
        prof = character.get_profile(conn, "player", pid)
        return rebirth.life_no(conn) >= 3 or bool(
            prof and prof["origin"] == "reincarnato" and "fusione" in storyline.flags(conn))
    if key == "yinyang":
        return c("luce") >= 50 and c("oscurita") >= 50
    if key == "caos":
        return all(c(e) >= 25 for e in ("legno", "fuoco", "terra", "metallo", "acqua"))
    if key == "sangue":
        prof = character.get_profile(conn, "player", pid)
        devoured = (prof["abs_human"] or 0) if prof else 0
        return devoured >= 15 or (state.get_int(conn, "kills_human") >= 40
                                  and karma.get_karma(conn, "player", pid) <= -200)
    if key == "illusione":
        prof = character.get_profile(conn, "player", pid)
        return c("anima") >= 100 and bool(prof and (prof["aff_soul"] or 0) >= 80)
    if key == "stelle":
        return c("destino") >= 50 and c("spazio") >= 25
    if key == "vuoto":
        return c("spazio") >= 250
    if key == "creazione":
        if all(c(e) >= 50 for e in ("legno", "terra", "acqua")):
            return True
        from engine.systems import professions
        return professions.best_level(conn, pid) >= 5
    return False


def check_awakenings(conn: sqlite3.Connection, pid: int = 1) -> list[str]:
    """Risveglia i Dao superiori le cui condizioni sono soddisfatte. Ritorna i testi."""
    out = []
    for key, (_hint, text) in SUPERIOR.items():
        if has(conn, pid, key) or not _cond(conn, pid, key):
            continue
        conn.execute(
            "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, "
            "comprehension, practiced) VALUES ('player', ?, ?, 70, ?, 1) "
            "ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET practiced=1, "
            "comprehension=MAX(character_daos.comprehension, excluded.comprehension);",
            (pid, key, AWAKEN_COMP))
        from engine.systems.dao_techniques import _dao_label
        name = _dao_label(key)
        state.grant_title(conn, f"Risvegliato al {name}")
        out.append(f"✺ RISVEGLIO — {name.upper()} ✺\n{text}\n"
                   f"(Nuovo Dao superiore: allenalo con 'comprehend {key}'.)")
    return out


def sealed_hints(conn, pid: int = 1) -> list[str]:
    from engine.systems.dao_techniques import _dao_label
    return [f"  · {_dao_label(k)}: «{hint}»" for k, (hint, _t) in SUPERIOR.items()
            if not has(conn, pid, k)]
