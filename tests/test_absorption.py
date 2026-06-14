"""v1 Abisso Divoratore: Dao, affinità latenti, assorbimento (rendimento/decadimento/residuo)."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, absorption
from engine.generators import dao_gen


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "abs.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    c.commit()
    yield c
    c.close()


def test_daos_seeded_with_levels(conn):
    rows = {r["dao_key"]: r["level"] for r in conn.execute("SELECT dao_key, level FROM daos;")}
    assert rows["destino"] == "deep"
    assert rows["corpo"] == "systemic"
    assert "spada" in rows


def test_divoratore_has_anomaly_and_latent_affinities(conn):
    character.apply_origin(conn, "divoratore", random.Random(1))
    prof = character.get_profile(conn, "player", 1)
    assert prof["anomaly"] == "abisso_divoratore"
    daos = {r["dao_key"]: r for r in dao_gen.list_character_daos(conn, "player", 1)}
    # pratica corpo/anima/fulmine, latenti destino/tempo/spazio (comprensione 0)
    assert daos["corpo"]["practiced"] == 1
    assert daos["destino"]["practiced"] == 0
    assert daos["destino"]["comprehension"] == 0
    assert daos["destino"]["affinity"] >= 70  # affinità latente alta


def test_npcs_have_primary_dao(conn):
    n = conn.execute(
        "SELECT COUNT(DISTINCT character_id) c FROM character_daos WHERE character_type='npc';"
    ).fetchone()["c"]
    assert n >= 10


def _kill_npc_here(conn):
    player_loc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    npc = conn.execute(
        "SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE npcs SET status='dead', death_tick=0, location_id=? WHERE id=?;",
                 (player_loc, npc))
    return npc


def test_cannot_absorb_without_anomaly(conn):
    character.apply_origin(conn, "mortale", random.Random(1))
    npc = _kill_npc_here(conn)
    res = absorption.absorb(conn, tick=1, rng=random.Random(0), target_id=npc)
    assert res["status"] == "no_anomaly"


def test_absorb_requires_dead_target(conn):
    character.apply_origin(conn, "divoratore", random.Random(1))
    alive = conn.execute("SELECT id, location_id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()
    conn.execute("UPDATE npcs SET location_id=(SELECT location_id FROM players WHERE id=1) WHERE id=?;", (alive["id"],))
    res = absorption.absorb(conn, tick=1, rng=random.Random(0), target_id=alive["id"])
    assert res["status"] == "not_dead"


def test_absorb_marks_target_and_logs_event(conn):
    character.apply_origin(conn, "divoratore", random.Random(1))
    npc = _kill_npc_here(conn)
    res = absorption.absorb(conn, tick=5, rng=random.Random(3), target_id=npc)
    assert res["status"] in ("comprehension", "human", "trauma", "shattered")
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (npc,)).fetchone()["status"] == "absorbed"
    ev = conn.execute("SELECT id FROM events WHERE event_type='absorption';").fetchall()
    assert len(ev) == 1
    # vincolo 26
    e = ev[0]["id"]
    assert conn.execute("SELECT COUNT(*) c FROM event_participants WHERE event_id=?;", (e,)).fetchone()["c"] >= 2
    assert conn.execute("SELECT COUNT(*) c FROM consequences WHERE event_id=?;", (e,)).fetchone()["c"] >= 1


def test_absorption_accumulates_residue(conn):
    character.apply_origin(conn, "divoratore", random.Random(1))
    before = character.get_profile(conn, "player", 1)["soul_residue"]
    npc = _kill_npc_here(conn)
    res = absorption.absorb(conn, tick=5, rng=random.Random(3), target_id=npc)
    after = character.get_profile(conn, "player", 1)["soul_residue"]
    assert after > before


def test_corpse_decay_reduces_yield(conn):
    """Un cadavere più vecchio rende meno: la freschezza scala con il tempo."""
    # freshness a morte recente vs lontana (test sulla formula via due assorbimenti)
    character.apply_origin(conn, "divoratore", random.Random(1))
    ploc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    # due NPC identici, uno morto da poco, uno da molto
    ids = [r["id"] for r in conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 2;")]
    for i in ids:
        conn.execute("UPDATE npcs SET status='dead', location_id=? WHERE id=?;", (ploc, i))
    # imposta lo stesso Dao/comprensione per confronto equo
    for i in ids:
        conn.execute("UPDATE character_daos SET comprehension=80, dao_key='corpo' "
                     "WHERE character_type='npc' AND character_id=?;", (i,))
    conn.execute("UPDATE npcs SET death_tick=100 WHERE id=?;", (ids[0],))  # fresco
    conn.execute("UPDATE npcs SET death_tick=0 WHERE id=?;", (ids[1],))    # vecchio
    # forza esito 'comprehension' con anima alta e bersaglio non superiore
    r_fresh = absorption.absorb(conn, tick=110, rng=random.Random(1), target_id=ids[0])
    r_old = absorption.absorb(conn, tick=110, rng=random.Random(1), target_id=ids[1])
    # un umano dà sempre statistiche: il cadavere fresco rende >= di quello vecchio
    assert r_fresh["status"] == "human" and r_old["status"] == "human"
    assert r_fresh["strength"] >= r_old["strength"]
    assert r_fresh["dao_gain"] >= r_old["dao_gain"]


def test_default_origin_preset_loads(conn, monkeypatch, tmp_path):
    # se non configurato, nessun preset
    assert character.load_default_origin() in (None, *character.ORIGINS.keys())
