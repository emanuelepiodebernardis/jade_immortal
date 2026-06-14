"""
Connection manager per SQLite.

Responsabilità:
- aprire connessioni con PRAGMA foreign_keys ON e row_factory = Row
- inizializzare lo schema (idempotente, usa schema.sql)
- fornire un context manager transazionale
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

# Percorsi relativi alla root del progetto (questo file sta in engine/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "world.db"
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema.sql"


def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    """Apre una connessione configurata correttamente."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path | str = DB_PATH, schema_path: Path | str = SCHEMA_PATH) -> None:
    """Crea il database e applica lo schema completo. Idempotente."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    schema_sql = Path(schema_path).read_text(encoding="utf-8")
    conn = connect(db_path)
    try:
        conn.executescript(schema_sql)
        _migrate(conn)
        conn.commit()
    finally:
        conn.close()


def _migrate(conn) -> None:
    """Aggiunge colonne nuove a tabelle preesistenti (salvataggi vecchi). Idempotente."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(cultivation_records);")}
    if "stage" not in cols:
        conn.execute("ALTER TABLE cultivation_records ADD COLUMN stage INTEGER DEFAULT 1;")
    mcols = {r["name"] for r in conn.execute("PRAGMA table_info(sect_memberships);")}
    if mcols and "class_tier" not in mcols:
        conn.execute("ALTER TABLE sect_memberships ADD COLUMN class_tier INTEGER DEFAULT 1;")
    if mcols and "class_rank" not in mcols:
        conn.execute("ALTER TABLE sect_memberships ADD COLUMN class_rank INTEGER;")
    # crescita fisica / conteggi assorbimento (assorbimento = identità)
    pcols = {r["name"] for r in conn.execute("PRAGMA table_info(character_profiles);")}
    for col in ("grow_strength", "grow_vitality", "grow_resistance", "grow_aura",
                "grow_soul", "abs_beast", "abs_demon", "abs_spirit", "abs_human",
                "fame", "infamy", "suspicion", "disguised",
                "dao_sessions", "cult_sessions"):
        if pcols and col not in pcols:
            conn.execute(f"ALTER TABLE character_profiles ADD COLUMN {col} INTEGER DEFAULT 0;")
    if pcols and "weapon" not in pcols:        # arma principale (TEXT, non INTEGER)
        conn.execute("ALTER TABLE character_profiles ADD COLUMN weapon TEXT;")
    if pcols and "qi_current" not in pcols:     # Qi per le mosse (-1 = pieno alla prima lettura)
        conn.execute("ALTER TABLE character_profiles ADD COLUMN qi_current INTEGER DEFAULT -1;")
    ncols = {r["name"] for r in conn.execute("PRAGMA table_info(npcs);")}
    if ncols and "kind" not in ncols:
        conn.execute("ALTER TABLE npcs ADD COLUMN kind TEXT DEFAULT 'human';")
    if ncols and "event_id" not in ncols:
        conn.execute("ALTER TABLE npcs ADD COLUMN event_id INTEGER;")
    if ncols and "hunting" not in ncols:
        conn.execute("ALTER TABLE npcs ADD COLUMN hunting INTEGER DEFAULT 0;")
    if ncols and "war_id" not in ncols:
        conn.execute("ALTER TABLE npcs ADD COLUMN war_id INTEGER;")
    # livello/elemento delle sette (sette a livelli + rappresentanti)
    fcols = {r["name"] for r in conn.execute("PRAGMA table_info(factions);")}
    if fcols and "tier" not in fcols:
        conn.execute("ALTER TABLE factions ADD COLUMN tier INTEGER DEFAULT 1;")
    if fcols and "element" not in fcols:
        conn.execute("ALTER TABLE factions ADD COLUMN element TEXT;")
    if fcols and "hunt_zone_id" not in fcols:
        conn.execute("ALTER TABLE factions ADD COLUMN hunt_zone_id INTEGER;")
    mcols = {r["name"] for r in conn.execute("PRAGMA table_info(sect_memberships);")}
    if mcols and "merit" not in mcols:
        conn.execute("ALTER TABLE sect_memberships ADD COLUMN merit INTEGER DEFAULT 0;")


def is_initialized(db_path: Path | str = DB_PATH) -> bool:
    """True se esiste almeno un mondo (cioè il DB è stato seedato)."""
    if not Path(db_path).exists():
        return False
    conn = connect(db_path)
    try:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='worlds';"
        ).fetchone()
        if row is None:
            return False
        count = conn.execute("SELECT COUNT(*) AS c FROM worlds;").fetchone()["c"]
        return count > 0
    finally:
        conn.close()


@contextmanager
def transaction(db_path: Path | str = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager: commit automatico, rollback su eccezione."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
