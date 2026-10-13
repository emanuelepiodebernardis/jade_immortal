"""Chi ti insegue cresce con te.

Cacciatori di taglie, campioni delle specie, nemesi, l'arcinemico e i vendicatori «alla pari»
(fratelli, sorelle, figli, fratelli giurati, allievi) non devono essere un muro: se la tua
potenza è 200, chi ti dà la caccia non può averne 10 000. Ogni inseguitore ha una FASCIA di
forza rispetto alla tua (per esempio tra 0,85 e 1,25 volte) e ci viene riportato:
  · alla nascita, subito;
  · ogni giorno: se cresci, crescono con te; se restano indietro, si allenano; se sono
    troppo avanti, aspettano (la loro forza «si ferma» finché non li raggiungi).

Le faide degli ANZIANI della famiglia e della setta (padre, madre, maestro, la setta stessa)
sono un'altra storia: possono essere molto più forti di te, è giusto così. Non vengono mai
indeboliti; se però li superi di molto, si allenano per non restare indietro.

Il motore: un fattore di potenza per NPC (tabella npc_power_scale) che `combat.combat_power`
applica a tutte le statistiche. Il regno dell'inseguitore viene anche avvicinato al tuo, così
il nome del regno che vedi resta coerente con la forza.
"""
from __future__ import annotations

import sqlite3

# fascia di forza (sua / tua) per tipo di inseguitore
BANDS = {
    "cacciatore": (0.8, 1.2),
    "campione": (0.95, 1.35),
    "nemesi": (0.9, 1.3),
    "arcinemico": (0.85, 1.25),
    "vendicatore": (0.75, 1.15),
    "anziano": (0.8, None),          # faide degli anziani: mai indeboliti, solo tenuti al passo
}
PEER_RELATIONS = {"fratello", "sorella", "figlio", "figlia", "giurato", "allievo"}
SENIOR_RELATIONS = {"padre", "madre", "maestro", "setta"}
MIN_F, MAX_F = 0.01, 50.0


def ensure_table(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS npc_power_scale ("
                 "npc_id INTEGER PRIMARY KEY, factor REAL NOT NULL DEFAULT 1.0);")


def factor(conn, npc_id: int) -> float:
    try:
        r = conn.execute("SELECT factor FROM npc_power_scale WHERE npc_id=?;", (npc_id,)).fetchone()
    except sqlite3.OperationalError:
        return 1.0
    return float(r["factor"]) if r else 1.0


def _set_factor(conn, npc_id: int, f: float) -> None:
    ensure_table(conn)
    f = max(MIN_F, min(MAX_F, f))
    conn.execute("INSERT INTO npc_power_scale (npc_id, factor) VALUES (?, ?) "
                 "ON CONFLICT(npc_id) DO UPDATE SET factor=excluded.factor;", (npc_id, f))


def _overall(p: dict) -> float:
    return p["attack"] + p["defense"] * 0.6 + p["vitality"] * 0.4


def ratio(conn, player_id: int, npc_id: int) -> float:
    """Sua forza / tua forza (>1 = è più forte di te)."""
    from engine.simulation import combat
    me = _overall(combat.combat_power(conn, "player", player_id))
    him = _overall(combat.combat_power(conn, "npc", npc_id))
    return him / max(1.0, me)


def _align_realm(conn, player_id: int, npc_id: int, offset: int = 0) -> None:
    """Porta il regno dell'inseguitore vicino al tuo (stesso regno, o uno sopra per i campioni)."""
    from engine.simulation import cultivation
    from engine.systems import npc_factory
    pt = cultivation.realm_tier(conn, "player", player_id) or 1
    rec = conn.execute("SELECT stage FROM cultivation_records WHERE character_type='npc' AND character_id=?;",
                       (npc_id,)).fetchone()
    if not rec:
        return
    nt = cultivation.realm_tier(conn, "npc", npc_id) or 1
    want = max(1, pt + offset)
    if nt == want:
        return
    rid = npc_factory.realm_id_for(conn, want)
    st = rec["stage"] or 1
    conn.execute(
        "UPDATE cultivation_records SET realm_id=?, qi_level=?, body_level=?, soul_level=?, dao_understanding=? "
        "WHERE character_type='npc' AND character_id=?;",
        (rid, want * 10 + st * 2, want * 8 + st, want * 8 + st, want * 5, npc_id))
    conn.execute("UPDATE npcs SET realm_id=? WHERE id=?;", (rid, npc_id))


def fit(conn, player_id: int, npc_id: int, kind: str, *, align: bool = False,
        offset: int = 0, target: float | None = None) -> float:
    """Riporta l'inseguitore nella sua fascia. Ritorna il nuovo rapporto sua/tua forza."""
    lo, hi = BANDS.get(kind, BANDS["vendicatore"])
    if align:
        _align_realm(conn, player_id, npc_id, offset)
    r = ratio(conn, player_id, npc_id)
    if r <= 0:
        return r
    if target is None:
        if r < lo:
            target = lo
        elif hi is not None and r > hi:
            target = hi
        else:
            return r
    f = factor(conn, npc_id) * target / r
    _set_factor(conn, npc_id, f)
    return ratio(conn, player_id, npc_id)


def on_spawn(conn, player_id: int, npc_id: int, kind: str, offset: int = 0) -> float:
    """Alla nascita: stesso regno (o +offset) e una forza nel mezzo della fascia."""
    lo, hi = BANDS.get(kind, BANDS["vendicatore"])
    mid = (lo + (hi if hi is not None else lo * 1.25)) / 2
    return fit(conn, player_id, npc_id, kind, align=True, offset=offset, target=mid)


def tracked(conn) -> list[tuple[int, str]]:
    """Tutti gli inseguitori vivi, col loro tipo."""
    out: dict[int, str] = {}
    for r in conn.execute("SELECT id, kind FROM npcs WHERE hunting=1 AND status='alive';"):
        out[r["id"]] = "campione" if (r["kind"] or "human") != "human" else "cacciatore"
    try:
        from engine.systems import bonds
        for nm in bonds.nemeses(conn, 1):
            out[nm["npc_id"]] = "nemesi"
    except sqlite3.OperationalError:
        pass
    try:
        from engine.systems import feuds
        for f in feuds.feuds(conn):
            rel = f["relation"] or ""
            out[f["npc_id"]] = "anziano" if rel in SENIOR_RELATIONS else "vendicatore"
    except sqlite3.OperationalError:
        pass
    try:
        from engine.systems import deep_dao             # i Messaggeri del Cielo
        for nid in deep_dao.messenger_ids(conn):
            out[nid] = "campione"
    except sqlite3.OperationalError:
        pass
    try:
        from engine.systems import archrival
        d = archrival.get(conn)
        if d and d.get("npc"):
            r = conn.execute("SELECT status FROM npcs WHERE id=?;", (d["npc"],)).fetchone()
            if r and r["status"] == "alive":
                out[d["npc"]] = "arcinemico"
    except sqlite3.OperationalError:
        pass
    return list(out.items())


def kind_of(conn, npc_id: int, default: str = "cacciatore") -> str:
    return dict(tracked(conn)).get(npc_id, default)


def daily(conn, t: int, rng, player) -> list[str]:
    """Ogni giorno chi ti insegue resta al tuo passo (in silenzio)."""
    if player is None:
        return []
    for nid, kind in tracked(conn):
        try:
            fit(conn, player.id, nid, kind)
        except Exception:
            continue
    return []
