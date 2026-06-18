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
    # nuove tabelle (per salvataggi creati prima della loro introduzione)
    conn.execute("CREATE TABLE IF NOT EXISTS pending_reports ("
                 "id INTEGER PRIMARY KEY, player_id INTEGER NOT NULL, tick INTEGER NOT NULL, "
                 "text TEXT NOT NULL, shown INTEGER DEFAULT 0);")
    conn.execute("CREATE TABLE IF NOT EXISTS market_offers ("
                 "id INTEGER PRIMARY KEY, player_id INTEGER NOT NULL, location_id INTEGER NOT NULL, "
                 "day INTEGER NOT NULL, name TEXT NOT NULL, item_type TEXT NOT NULL, "
                 "rarity TEXT NOT NULL, price INTEGER NOT NULL, effects TEXT NOT NULL, "
                 "sold INTEGER DEFAULT 0);")
    wecols = {r["name"] for r in conn.execute("PRAGMA table_info(world_events);")}
    if wecols and "champion_id" not in wecols:
        conn.execute("ALTER TABLE world_events ADD COLUMN champion_id INTEGER;")
    if wecols and "reinforce_tick" not in wecols:
        conn.execute("ALTER TABLE world_events ADD COLUMN reinforce_tick INTEGER DEFAULT 0;")
    chcols = {r["name"] for r in conn.execute("PRAGMA table_info(sect_cohort);")}
    if chcols and "talent" not in chcols:
        conn.execute("ALTER TABLE sect_cohort ADD COLUMN talent INTEGER DEFAULT 50;")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(cultivation_records);")}
    if "stage" not in cols:
        conn.execute("ALTER TABLE cultivation_records ADD COLUMN stage INTEGER DEFAULT 1;")
    if "bt_failures" not in cols:
        conn.execute("ALTER TABLE cultivation_records ADD COLUMN bt_failures INTEGER DEFAULT 0;")
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
                "mask_fame", "mask_infamy", "mask_suspicion",
                "last_tribulation_defiance",
                "dao_sessions", "cult_sessions"):
        if pcols and col not in pcols:
            conn.execute(f"ALTER TABLE character_profiles ADD COLUMN {col} INTEGER DEFAULT 0;")
    if pcols and "weapon" not in pcols:        # arma principale (TEXT, non INTEGER)
        conn.execute("ALTER TABLE character_profiles ADD COLUMN weapon TEXT;")
    for col in ("weapon_tier", "weapon_rarity"):    # arma-oggetto: regno + rarità
        if pcols and col not in pcols:
            conn.execute(f"ALTER TABLE character_profiles ADD COLUMN {col} INTEGER DEFAULT 0;")
    if pcols and "qi_current" not in pcols:     # Qi per le mosse (-1 = pieno alla prima lettura)
        conn.execute("ALTER TABLE character_profiles ADD COLUMN qi_current INTEGER DEFAULT -1;")
    if pcols and "spirit_current" not in pcols:  # Spirito per le tecniche Dao (-1 = pieno)
        conn.execute("ALTER TABLE character_profiles ADD COLUMN spirit_current INTEGER DEFAULT -1;")
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
