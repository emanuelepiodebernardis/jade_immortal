"""
L'ANTEPRIMA (Aggiornamento 80) — cosa ti darebbe un Dao prima di spendere pietre.

  anteprima tempesta        (o «prova fusione tempesta», «anteprima ghiaccio»)

Il gioco prova davvero: dentro un punto di salvataggio provvisorio aggiunge il Dao alla comprensione che avresti
(per una fusione, quella di partenza; per una via nuova, 1), poi a 100 e a 1000, misura attacco, difesa, vitalità,
critici, schivata, danni subiti, coltivazione, anni di vita — e torna indietro. Nulla cambia nel salvataggio.
"""

from __future__ import annotations


def _measure(conn, pid: int) -> dict:
    from engine.simulation import combat
    from engine.systems import dao_laws, cult_mods, lifespan
    cp = combat.combat_power(conn, "player", pid)
    lv = dao_laws.levers(conn, pid)
    rec = conn.execute("SELECT location_id FROM players WHERE id=?;", (pid,)).fetchone()
    cm, _l = cult_mods.cultivation_mult(conn, pid, rec["location_id"])
    return {"attacco": cp["attack"], "difesa": cp["defense"], "vitalità": cp["vitality"],
            "critici": lv.get("crit", 0.0), "schivata": lv.get("evade", 0.0), "danni subiti": -lv.get("taken", 0.0),
            "perforazione": lv.get("pierce", 0.0), "colpi in più": lv.get("strikes", 0.0), "coltivazione": cm, "anni di vita": lifespan.max_years(conn, pid)}


def _with(conn, pid: int, key: str, comp: int) -> dict:
    conn.execute("SAVEPOINT anteprima;")
    try:
        conn.execute(
            "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
            "VALUES ('player', ?, ?, 50, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
            "comprehension=excluded.comprehension, practiced=1;", (pid, key, comp))
        return _measure(conn, pid)
    finally:
        conn.execute("ROLLBACK TO anteprima;")
        conn.execute("RELEASE anteprima;")


def _fmt(k: str, a: float, b: float) -> str | None:
    d = b - a
    if abs(d) < 1e-6:
        return None
    if k in ("critici", "schivata", "danni subiti", "perforazione"):
        return f"{k} {'+' if d > 0 else ''}{d * 100:.0f}%"
    if k == "coltivazione":
        return f"{k} {'+' if d > 0 else ''}{(b / a - 1) * 100:.0f}%" if a else None
    if k in ("anni di vita", "colpi in più"):
        return f"{k} {'+' if d > 0 else ''}{int(d)}"
    return f"{k} {'+' if d > 0 else ''}{(b / a - 1) * 100:.1f}%" if a else None


def preview(conn, player, arg: str) -> str:
    from engine.systems import dao_laws
    words = [w for w in (arg or "").lower().split() if w not in ("fusione", "via", "dao", "del", "della")]
    if not words:
        return "Anteprima di cosa? 'anteprima <fusione o via>' — per esempio 'anteprima tempesta', 'anteprima ghiaccio'."
    key = dao_laws.find(" ".join(words)) or dao_laws._key_of(words[0])
    if not key or (key not in dao_laws.FUSED and key not in dao_laws.BY_KEY):
        return f"Non trovo una fusione o una via nuova chiamata «{' '.join(words)}». ('fusione', 'vie')"
    pid = player.id
    have = dao_laws._comp(conn, key, pid) if dao_laws._has(conn, key, pid) else None
    if key in dao_laws.FUSED:
        name = dao_laws.FUSED[key][1]
        start = max(10, sum(dao_laws._comp(conn, c, pid) for c in dao_laws.FUSED[key][2]) // 4)
        cost_note = dao_laws.FUSED[key][5]
    else:
        row = dao_laws.BY_KEY[key]
        name, start, cost_note = row[1], 1, row[9]
    base = _measure(conn, pid)
    if have is not None:
        conn.execute("SAVEPOINT senza;")
        try:
            conn.execute("DELETE FROM character_daos WHERE character_type='player' AND character_id=? AND dao_key=?;",
                         (pid, key))
            base = _measure(conn, pid)
        finally:
            conn.execute("ROLLBACK TO senza;")
            conn.execute("RELEASE senza;")
    lines = [f"🔍 ANTEPRIMA — {name}" + (f" (lo hai già: comprensione {have})" if have is not None else ""),
             "Rispetto a come sei adesso, senza questo Dao:"]
    for label, comp in (("all'inizio", have if have is not None else start), ("a 100 (maestro)", 100),
                        ("a 1000 (legislatore)", 1000)):
        after = _with(conn, pid, key, comp)
        parts = [x for x in (_fmt(k, base[k], after[k]) for k in base) if x]
        lines.append(f"  {label} [{comp}]: " + (", ".join(parts) if parts else "nessun effetto ancora"))
    if cost_note:
        lines.append("  Il costo, da adepto in su: " + ", ".join(
            f"{dao_laws.LEVER_IT.get(k, k)} {v:+.0%}" if abs(v) < 5 else f"{dao_laws.LEVER_IT.get(k, k)} {int(v):+d}"
            for k, v in cost_note.items()))
    if key in dao_laws.INSIGHT:
        from engine.systems.dao_techniques import _dao_label
        lines.append("  In fondo apre: " + ", ".join(f"{_dao_label(d)} (a {t})" for t, d in dao_laws.INSIGHT[key]))
    lines.append("(Nessuna pietra spesa: è solo una prova.) " + (f"'obiettivo {key}' per puntarci." if have is None else ""))
    return "\n".join(lines)
