"""Dao profondi (Spazio/Tempo/Destino), Heaven's Defiance e tribolazione divina."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, dao_powers, tribulation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "dp.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def _set_dao(conn, key, comp):
    from engine.generators import dao_gen
    dao_gen._set_dao(conn, "player", 1, key, 60, comp, 1)   # (.., affinity, comprehension, ..)
    conn.commit()


# ---------- Spazio ----------

def test_space_scales_pierce_and_strikes(conn):
    _set_dao(conn, "spazio", 5)
    low = dao_powers.space_combat(conn, 1)
    _set_dao(conn, "spazio", 1000)
    high = dao_powers.space_combat(conn, 1)
    assert high["pierce"] > low["pierce"]
    assert high["extra_strikes"] >= 1          # echi spaziali ad alta comprensione
    assert high["label"] is not None


# ---------- Tempo ----------

def test_time_accelerates_cultivation(conn):
    assert dao_powers.time_cultivation_mult(conn, 1) == 1.0
    _set_dao(conn, "tempo", 250)
    assert dao_powers.time_cultivation_mult(conn, 1) > 1.0
    assert dao_powers.time_evasion(conn, 1) > 0


# ---------- Destino ----------

def test_fate_helps_breakthrough(conn):
    _set_dao(conn, "destino", 250)
    succ, death = dao_powers.fate_breakthrough(conn, 1)
    assert succ > 0 and death < 1.0


# ---------- Heaven's Defiance ----------

def test_heaven_defiance_is_sum(conn):
    _set_dao(conn, "spazio", 30)
    _set_dao(conn, "tempo", 40)
    _set_dao(conn, "destino", 20)
    assert dao_powers.heaven_defiance(conn, 1) == 90


def test_tribulation_due_after_threshold(conn):
    assert dao_powers.tribulation_due(conn, 1) == 0     # nessun Dao profondo
    _set_dao(conn, "tempo", 100)                        # oltre DEFIANCE_STEP
    assert dao_powers.tribulation_due(conn, 1) > 0


# ---------- Tribolazione divina ----------

def test_tribulation_survival_purifies_and_grants_space(conn):
    # corruzione presente + forte affinità Fulmine (resistenza alta) → domi e ti purifichi
    conn.execute("UPDATE character_profiles SET soul_residue=300 "
                 "WHERE character_type='player' AND character_id=1;")
    _set_dao(conn, "fulmine", 1000)        # enorme resistenza
    _set_dao(conn, "tempo", 100)           # genera defiance
    res = tribulation.resolve_tribulation(conn, 0, random.Random(1), power=40, player_id=1)
    assert res["status"] == "survived"
    # l'Abisso è purificato
    prof = character.get_profile(conn, "player", 1)
    assert (prof["soul_residue"] or 0) == 0
    assert (prof["last_tribulation_defiance"] or 0) == dao_powers.heaven_defiance(conn, 1)
    # poteri spaziali risvegliati
    assert dao_powers.comp(conn, "spazio", 1) > 0


def test_tribulation_resets_due(conn):
    _set_dao(conn, "fulmine", 1000)
    _set_dao(conn, "spazio", 120)
    assert dao_powers.tribulation_due(conn, 1) > 0
    tribulation.resolve_tribulation(conn, 0, random.Random(2),
                                    dao_powers.tribulation_due(conn, 1), 1)
    # dopo averla affrontata, la stessa soglia non ritriggera subito
    assert dao_powers.tribulation_due(conn, 1) == 0


# ---------- integrazione CLI ----------

def test_cmd_tribulation_and_dao_display(conn):
    _set_dao(conn, "fulmine", 800)
    _set_dao(conn, "spazio", 120)
    player = entities.get_player(conn)
    out_dao = loop.cmd_dao(conn, player)
    assert "Sfida al Cielo" in out_dao
    out_trib = loop.cmd_tribulation(conn, player)
    assert "TRIBOLAZIONE" in out_trib or "heaven defiance" in out_trib.lower()
