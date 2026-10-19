"""
LO SBLOCCO PROGRESSIVO (Aggiornamento 67) — la dashboard si apre poco a poco.

La critica più comune agli idle del genere (Immortal Celestial Fate compreso): all'inizio l'interfaccia
è un muro di pulsanti. Qui le schede dei palazzi si aprono con il regno o quando c'è qualcosa dentro:
chi comincia vede l'essenziale, chi è avanti vede tutto. Ogni scheda nuova si annuncia una volta sola.

  · una scheda con un pallino rosso (qualcosa da fare) non è mai nascosta;
  · per i salvataggi già avanzati è tutto aperto fin da subito;
  · dalle opzioni si può mostrare tutto sempre ('schede tutte' / 'schede graduali').

Le regole sono un registro: aggiungerne una è una riga in GATES.
"""

from __future__ import annotations

from engine.systems import state

KEY = "unlocked_tabs"
ALL_KEY = "show_all_tabs"


def _tier(conn) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", 1) or 1


def _has_vessel(conn) -> bool:
    try:
        from engine.systems import mentor_ring, soul_artifacts
        return bool(mentor_ring.get(conn)) or bool(soul_artifacts.owned(conn))
    except Exception:                                   # noqa: BLE001
        return True


def _has_feud(conn) -> bool:
    try:
        from engine.systems import feuds
        return bool(feuds.feuds(conn, active=False))
    except Exception:                                   # noqa: BLE001
        return True


def _below(conn) -> bool:
    try:
        from engine.systems import lower_world
        return bool(lower_world.active(conn))
    except Exception:                                   # noqa: BLE001
        return True


def _saga(conn) -> bool:
    try:
        from engine.systems import soul_arcs
        s = soul_arcs.get(conn).get("compagni") or {}
        return bool(s.get("ch") or s.get("running"))
    except Exception:                                   # noqa: BLE001
        return True


# scheda → (condizione, quando si apre, etichetta)
GATES = {
    "via:sangue": (lambda c: _tier(c) >= 2, "dal 2° regno", "🩸 Sangue"),
    "via:anime": (lambda c: _tier(c) >= 3 or _has_vessel(c), "dal 3° regno, o con un vaso d'anima", "✧ Anime"),
    "via:forza": (lambda c: _tier(c) >= 3, "dal 3° regno", "⚖ Forza"),
    "via:dharma": (lambda c: _tier(c) >= 3, "dal 3° regno", "🗿 Dharma"),
    "via:profondi": (lambda c: _tier(c) >= 4, "dal 4° regno", "🌌 Dao profondi"),
    "via:spiriti": (lambda c: _tier(c) >= 5, "dal 5° regno", "✺ Spiriti"),
    "setta:dimora": (lambda c: _tier(c) >= 2, "dal 2° regno", "⌂ Dimora"),
    "setta:rendite": (lambda c: _tier(c) >= 3, "dal 3° regno", "💰 Rendite"),
    "setta:dominio": (lambda c: _tier(c) >= 5, "dal 5° regno", "⛓ Dominio"),
    "seguaci:discepoli": (lambda c: _tier(c) >= 3, "dal 3° regno", "🎓 Discepoli"),
    "seguaci:cloni": (lambda c: _tier(c) >= 4, "dal 4° regno", "☯ Cloni"),
    "seguaci:compagni": (_saga, "quando ritrovi la prima traccia", "🌀 Compagni"),
    "seguaci:faide": (_has_feud, "alla prima faida", "⚔ Faide"),
    "mondo:asta": (lambda c: _tier(c) >= 2, "dal 2° regno", "⚖ Aste"),
    "mondo:regni": (lambda c: _tier(c) >= 3, "dal 3° regno", "👑 Regni"),
    "mondo:razze": (lambda c: _tier(c) >= 5, "dal 5° regno", "🐉 Razze"),
    "mondo:sotto": (_below, "quando ascendi", "🙏 Mondo di sotto"),
}
PALACE_IT = {"via": "La tua Via", "setta": "Setta e potere", "seguaci": "Seguaci", "mondo": "Il mondo"}


def show_all(conn) -> bool:
    return state.get(conn, ALL_KEY, "0") == "1"


def locked(conn, badges: dict | None = None) -> dict:
    """{scheda: quando si apre} per le schede ancora chiuse."""
    if show_all(conn):
        return {}
    seen = set(state.get_json(conn, KEY, []) or [])
    badges = badges or {}
    out = {}
    for k, (cond, when, _lab) in GATES.items():
        if k in seen or badges.get(k):
            continue
        try:
            ok = cond(conn)
        except Exception:                               # noqa: BLE001
            ok = True
        if not ok:
            out[k] = when
    return out


def announce(conn, badges: dict | None = None) -> list[str]:
    """Le schede appena aperte (una volta sola). Al primo giro registra in silenzio ciò che è già aperto."""
    raw = state.get_json(conn, KEY, None)
    lk = locked(conn, badges)
    open_now = [k for k in GATES if k not in lk]
    if raw is None:
        state.set_json(conn, KEY, open_now)
        return []
    seen = set(raw)
    new = [k for k in open_now if k not in seen]
    if not new:
        return []
    state.set_json(conn, KEY, sorted(seen | set(new)))
    if show_all(conn):
        return []
    return [f"✦ Si apre una nuova scheda: {GATES[k][2]} ({PALACE_IT.get(k.split(':')[0], '')})." for k in new]


def command(conn, arg: str) -> str:
    a = (arg or "").strip().lower()
    if a in ("tutte", "tutto", "sempre"):
        state.set(conn, ALL_KEY, "1")
        return "Da ora la dashboard mostra tutte le schede, sempre."
    if a in ("graduali", "gradual", "poco"):
        state.set(conn, ALL_KEY, "0")
        return "Da ora le schede si aprono poco a poco, con il regno."
    lk = locked(conn)
    if not lk:
        return "Tutte le schede sono aperte. ('schede graduali' per farle aprire poco a poco)"
    return "Schede ancora chiuse:\n" + "\n".join(f"  {GATES[k][2]} — {w}" for k, w in lk.items()) + \
        "\n('schede tutte' per vederle subito)"
