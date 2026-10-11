"""
CRONACA — la storia della tua vita (e delle tue vite), da rileggere ed esportare.

Il motore annota da solo i momenti che contano: i regni raggiunti, i titoli, i capitoli
della storia e le scelte fatte, i nemici giurati caduti, le persone care perdute, le svolte,
le conseguenze che tornano, la morte e la rinascita. La cronaca ha una tabella sua: la
manutenzione non la tocca mai.

  cronaca              la vita attuale
  cronaca tutte        tutte le vite, dalla prima
  cronaca esporta      scrive la cronaca completa in database/saves/cronaca_<nome>.md
"""

from __future__ import annotations

from engine.core import tick as tick_mod

ICON = {"regno": "⇑", "titolo": "✧", "storia": "☯", "scelta": "»", "nemico": "⚔", "lutto": "✝",
        "svolta": "✦", "eco": "↺", "morte": "☠", "rinascita": "☀", "legame": "♥", "impresa": "★"}


def ensure_table(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS chronicle_entries (id INTEGER PRIMARY KEY, life_no INTEGER, "
                 "tick INTEGER, kind TEXT, text TEXT);")


def add(conn, kind: str, text: str) -> None:
    from engine.systems import state
    try:
        ensure_table(conn)
        life = state.get_int(conn, "life_no", 1)
        t = tick_mod.get_tick(conn)
        last = conn.execute("SELECT text FROM chronicle_entries ORDER BY id DESC LIMIT 1;").fetchone()
        if last and last["text"] == text:
            return
        conn.execute("INSERT INTO chronicle_entries (life_no, tick, kind, text) VALUES (?, ?, ?, ?);",
                     (life, t, kind, text))
    except Exception:
        pass                      # la cronaca non deve mai rompere il gioco


def entries(conn, all_lives: bool = False) -> list:
    from engine.systems import state
    ensure_table(conn)
    if all_lives:
        return conn.execute("SELECT * FROM chronicle_entries ORDER BY id;").fetchall()
    return conn.execute("SELECT * FROM chronicle_entries WHERE life_no=? ORDER BY id;",
                        (state.get_int(conn, "life_no", 1),)).fetchall()


def _line(r) -> str:
    day = r["tick"] // 120 + 1
    return f"  Giorno {day:>4}  {ICON.get(r['kind'], '·')} {r['text']}"


def describe(conn, player, arg: str = "") -> str:
    a = arg.strip().lower()
    if a in ("esporta", "export"):
        return export(conn, player)
    all_lives = a in ("tutte", "all", "vite")
    rows = entries(conn, all_lives)
    if not rows:
        return "La tua cronaca è ancora bianca: vivi, e il mondo scriverà."
    lines = [f"📜 CRONACA — {player.name}" + (" (tutte le vite)" if all_lives else "")]
    life = None
    for r in rows[-200:]:
        if all_lives and r["life_no"] != life:
            life = r["life_no"]
            lines.append(f" — Vita n.{life} —")
        lines.append(_line(r))
    lines.append("('cronaca tutte' per le vite passate, 'cronaca esporta' per salvarla in un file)")
    return "\n".join(lines)


def export(conn, player) -> str:
    from engine.systems import qol, rebirth
    rows = entries(conn, True)
    out = [f"# Cronaca di {player.name}", ""]
    life = None
    for r in rows:
        if r["life_no"] != life:
            life = r["life_no"]
            row = conn.execute("SELECT name, epilogue_title FROM past_lives WHERE life_no=?;", (life,)).fetchone() \
                if conn.execute("SELECT name FROM sqlite_master WHERE name='past_lives';").fetchone() else None
            title = f" — {row['name']}, «{row['epilogue_title']}»" if row else ""
            out += ["", f"## Vita {life}{title}", ""]
        out.append(f"- **Giorno {r['tick'] // 120 + 1}** {ICON.get(r['kind'], '·')} {r['text']}")
    safe = "".join(ch for ch in player.name if ch.isalnum() or ch in "_-") or "viandante"
    path = qol._saves_dir() / f"cronaca_{safe}.md"
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return f"Cronaca esportata in {path} ({len(rows)} momenti, {rebirth.life_no(conn)} vite)."
