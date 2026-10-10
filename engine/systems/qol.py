"""
QUALITÀ DI VITA: salvataggi, mappa, colori, codex, tutorial.

  salva [nome]        salva la partita in uno slot (cartella database/saves)
  carica <nome>       ricarica uno slot (la partita attuale viene sostituita!)
  salvataggi          gli slot disponibili (compresi i salvataggi automatici)
  mappa               mappa della regione intorno a te
  colori <on|off>     colori nel terminale
  codex [sezione]     ciò che hai scoperto: luoghi, bestie, Dao, lignaggi, maestri, titoli…
  tutorial            i primi passi, con ciò che ti resta da provare

Ogni 5 giorni di gioco la partita si salva da sola (3 salvataggi a rotazione: auto_1..3).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from engine.core import entities, tick as tick_mod
from engine.systems import state

AUTOSAVE_EVERY = 5


# ============================================================
# Salvataggi
# ============================================================

def _saves_dir() -> Path:
    from engine import db
    d = Path(db.DB_PATH).parent / "saves"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _slot(name: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_\-]", "_", name.strip())[:40]
    return name or "slot"


def save(conn, name: str = "") -> str:
    name = _slot(name or f"giorno_{tick_mod.get_tick(conn) // 120 + 1}")
    path = _saves_dir() / f"{name}.db"
    conn.commit()
    dst = sqlite3.connect(path)
    try:
        conn.backup(dst)
    finally:
        dst.close()
    return f"Partita salvata nello slot «{name}»."


def load(conn, name: str) -> str:
    if not name.strip():
        return "Usa: carica <nome> ('salvataggi' per l'elenco)."
    path = _saves_dir() / f"{_slot(name)}.db"
    if not path.exists():
        return f"Nessun salvataggio «{name}». ('salvataggi' per l'elenco)"
    conn.commit()
    src = sqlite3.connect(path)
    try:
        src.backup(conn)
    finally:
        src.close()
    return f"Hai ricaricato «{_slot(name)}». Il mondo torna com'era."


def list_saves() -> str:
    files = sorted(_saves_dir().glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return "Nessun salvataggio. 'salva <nome>' per crearne uno."
    import datetime
    lines = ["Salvataggi:"]
    for f in files[:20]:
        ts = datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%d/%m %H:%M")
        lines.append(f"  · {f.stem:<24} ({ts})")
    lines.append("'carica <nome>' per ricaricarne uno.")
    return "\n".join(lines)


def autosave(conn, day: int) -> list[str]:
    if day <= 0 or day % AUTOSAVE_EVERY:
        return []
    k = (day // AUTOSAVE_EVERY) % 3 + 1
    try:
        save(conn, f"auto_{k}")
    except Exception:
        return []
    return []


# ============================================================
# Mappa
# ============================================================

_D = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}
_ICON = {"city": "▣", "mountain": "▲", "ruin": "▒", "forbidden_zone": "☠"}


def map_text(conn, player, radius: int = 3) -> str:
    from collections import deque
    from engine.systems import cave_abode, secret_realms
    start = player.location_id
    pos = {start: (0, 0)}
    q = deque([start])
    while q:
        cur = q.popleft()
        x, y = pos[cur]
        for d, nxt in entities.get_exits(conn, cur).items():
            if d not in _D or nxt in pos:
                continue
            nx, ny = x + _D[d][0], y + _D[d][1]
            if abs(nx) > radius or abs(ny) > radius or (nx, ny) in pos.values():
                continue
            pos[nxt] = (nx, ny)
            q.append(nxt)
    cells = {v: k for k, v in pos.items()}
    home = (cave_abode.get(conn, player.id) or {}).get("loc")
    realm = (secret_realms.current(conn) or {}).get("loc")
    lines = ["MAPPA (tu = @, ⌂ dimora, ✧ reame segreto; ▣ città ▲ montagna ▒ rovine ☠ zona proibita)"]
    legend = []
    for y in range(-radius, radius + 1):
        row = ""
        link = ""
        for x in range(-radius, radius + 1):
            lid = cells.get((x, y))
            if lid is None:
                row += "    "
                link += "    "
                continue
            lt = conn.execute("SELECT name, location_type FROM locations WHERE id=?;", (lid,)).fetchone()
            ic = "@" if lid == start else ("⌂" if lid == home else ("✧" if lid == realm else _ICON.get(lt["location_type"], "·")))
            row += f"[{ic}]"
            ex = entities.get_exits(conn, lid)
            row += "─" if "east" in ex and cells.get((x + 1, y)) == ex["east"] else " "
            link += " │  " if "south" in ex and cells.get((x, y + 1)) == ex["south"] else "    "
            if lid in (start, home, realm) or abs(x) + abs(y) <= 1:
                legend.append((abs(x) + abs(y), f"{ic} {lt['name']}"))
        lines.append(row.rstrip())
        if link.strip():
            lines.append(link.rstrip())
    lines.append("Vicino a te: " + ", ".join(n for _d, n in sorted(set(legend))[:8]))
    return "\n".join(ln for ln in lines if ln.strip())


# ============================================================
# Colori
# ============================================================

_COLORS = [("⚠", "\033[33m"), ("☠", "\033[31m"), ("✝", "\033[31m"), ("✦", "\033[96m"), ("✧", "\033[95m"),
           ("★", "\033[93m"), ("⚡", "\033[94m"), ("🩸", "\033[91m"), ("[Ding!]", "\033[92m"),
           ("✔", "\033[92m"), ("⏸", "\033[33m")]


def colors_on(conn) -> bool:
    return state.flag(conn, "ui_colors", True)


def colorize(text: str) -> str:
    out = []
    for ln in text.split("\n"):
        col = next((c for k, c in _COLORS if k in ln), None)
        if col is None and re.match(r"^\s*\[\d+\]", ln):
            col = "\033[36m"
        out.append(f"{col}{ln}\033[0m" if col else ln)
    return "\n".join(out)


# ============================================================
# Codex
# ============================================================

def note(conn, key: str, value: str) -> None:
    cur = state.get_json(conn, f"world_codex_{key}", []) or []
    if value not in cur:
        cur.append(value)
        state.set_json(conn, f"world_codex_{key}", cur)


def codex(conn, player, arg: str = "") -> str:
    from engine.systems import bloodlines, secret_masters, constitutions, heaven_trib
    places = state.get_json(conn, "world_codex_luoghi", []) or []
    beasts = state.get_json(conn, "world_codex_bestie", []) or []
    total = conn.execute("SELECT COUNT(*) c FROM locations;").fetchone()["c"]
    daos = [r["name"] for r in conn.execute(
        "SELECT d.name FROM character_daos cd JOIN daos d ON d.dao_key=cd.dao_key WHERE cd.character_type='player' "
        "AND cd.character_id=? AND (cd.practiced=1 OR cd.comprehension>0) ORDER BY cd.comprehension DESC;",
        (player.id,))]
    sections = {
        "luoghi": (f"Luoghi visitati ({len(places)}/{total})", places),
        "bestie": (f"Bestie incontrate in battaglia ({len(beasts)})", beasts),
        "dao": (f"Dao conosciuti ({len(daos)})", daos),
        "sangue": ("Lignaggi di sangue", [ln["name"] for _k, ln in bloodlines.ordered(conn)]),
        "maestri": ("Maestri segreti", [k for k in secret_masters.learned(conn)]),
        "titoli": ("Titoli", state.titles(conn)),
    }
    a = arg.strip().lower()
    if a in sections:
        title, items_ = sections[a]
        return title + ":\n" + ("\n".join(f"  · {x}" for x in items_) if items_ else "  (ancora nulla)")
    lines = ["📜 CODEX — ciò che hai scoperto ('codex <sezione>' per i dettagli)"]
    for k, (title, items_) in sections.items():
        prev = ", ".join(items_[:4]) + ("…" if len(items_) > 4 else "")
        lines.append(f"  {k:<8} {title}" + (f": {prev}" if items_ else ""))
    cl = constitutions.describe_line(conn)
    if cl:
        lines.append("  " + cl)
    lines.append(f"  Tribolazioni del fulmine affrontate: {heaven_trib.count(conn)}")
    return "\n".join(lines)


# ============================================================
# Tutorial
# ============================================================

def tutorial(conn, player) -> str:
    from engine.systems import sects, cave_abode, bonds
    cult, dao = conn.execute("SELECT COALESCE(cult_sessions,0) c, COALESCE(dao_sessions,0) d FROM character_profiles "
                             "WHERE character_type='player' AND character_id=?;", (player.id,)).fetchone()
    steps = [
        (cult > 0, "cultivate", "Medita ('cultivate' o 'c'): riempi lo strato; al 10° strato colmo, 'breakthrough'."),
        (len(state.get_json(conn, "world_codex_luoghi", []) or []) >= 2, "move north",
         "Esplora: 'look' per guardarti attorno, 'move <n|s|e|w>' per viaggiare, 'mappa' per orientarti."),
        (bool(conn.execute("SELECT 1 FROM npc_player_relations WHERE player_id=? LIMIT 1;", (player.id,)).fetchone()),
         "talk <nome>", "Parla con le persone ('talk <nome>'): nascono amicizie, maestri, compagni, incarichi ('richieste')."),
        (state.get_int(conn, "kills_total", 0) > 0, "attack creatures",
         "Combatti: 'attack <nome>' o 'attack creatures'. Esamina prima chi hai davanti ('examine <nome>')."),
        (dao > 0, "comprehend corpo", "Affina un Dao ('dao', poi 'comprehend <dao>'): è il cuore della tua forza."),
        (sects.get_membership(conn, player.id) is not None, "sects",
         "Entra in una setta ('sects' per sapere dove, poi 'join' alla sede): arma, tornei, tecniche."),
        (bool(state.get(conn, "profession")), "profession alchimia",
         "Scegli un'arte ('profession <alchimia|talismani|forgia|formazioni|domatore>'), poi 'gather' e 'craft'."),
        (cave_abode.get(conn, player.id) is not None, "dimora",
         "Fatti una casa: 'dimora reclama' in montagna, rovine o zona proibita."),
        (bool(state.get_json(conn, "auto_cfg")), "auto",
         "Quando vuoi far scorrere i giorni monotoni: 'auto' (pilota automatico)."),
    ]
    done = sum(1 for ok, _c, _t in steps if ok)
    lines = [f"📖 TUTORIAL — {done}/{len(steps)} passi compiuti"]
    for ok, cmd, txt in steps:
        lines.append(f"  [{'✔' if ok else ' '}] {txt}")
    nxt = next(((c, t) for ok, c, t in steps if not ok), None)
    if nxt:
        lines.append(f"Prossimo passo consigliato: '{nxt[0]}'. Ricorda: 'help' per tutto, 'goals' per la tua storia, "
                     "e i numeri delle azioni suggerite.")
    else:
        lines.append("Conosci le basi. Ora la Via è tua: 'goals', 'classifica', 'prodigi'…")
    return "\n".join(lines)
