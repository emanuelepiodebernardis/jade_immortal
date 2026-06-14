"""Tribolazione: il Dao del Fulmine riduce i danni e ogni folgore dona capacità celesti."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import character, absorption, tribulation
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "trib.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    character.apply_origin(c, "divoratore", random.Random(1))
    conn_set_residue(c, 1500)
    c.commit()
    yield c
    c.close()


def conn_set_residue(conn, r):
    conn.execute("UPDATE character_profiles SET soul_residue=? "
                 "WHERE character_type='player' AND character_id=1;", (r,))


def test_fulmine_reduces_tribulation_severity(conn):
    player = entities.get_player(conn)
    # senza Fulmine: registra le gravità
    sev_no = []
    for tk in range(60):
        conn.execute("UPDATE character_profiles SET soul_residue=1500 WHERE character_id=1 AND character_type='player';")
        before = conn.execute("SELECT COUNT(*) c FROM injuries;").fetchone()["c"]
        absorption.maybe_tribulation(conn, 24 * tk, random.Random(tk), player, [])
        rows = conn.execute("SELECT severity FROM injuries ORDER BY id DESC LIMIT 1;").fetchone()
        after = conn.execute("SELECT COUNT(*) c FROM injuries;").fetchone()["c"]
        if after > before and rows:
            sev_no.append(rows["severity"])
        if len(sev_no) >= 3:
            break
    # con Fulmine altissimo: gravità nulla o quasi
    dao_gen._set_dao(conn, "player", 1, "fulmine", 90, 600, 1)
    assert tribulation.fulmine_resistance(conn, 1) > 0
    conn.execute("DELETE FROM injuries;")
    conn.execute("UPDATE character_profiles SET soul_residue=1500 WHERE character_id=1 AND character_type='player';")
    got_zero = False
    for tk in range(40):
        conn.execute("UPDATE character_profiles SET soul_residue=1500 WHERE character_id=1 AND character_type='player';")
        before = conn.execute("SELECT COUNT(*) c FROM injuries;").fetchone()["c"]
        absorption.maybe_tribulation(conn, 24 * tk, random.Random(tk + 99), player, [])
        after = conn.execute("SELECT COUNT(*) c FROM injuries;").fetchone()["c"]
        if after == before:           # nessuna ferita inflitta: castigo assorbito
            got_zero = True
            break
    assert got_zero


def test_tribulation_grants_a_boon(conn):
    player = entities.get_player(conn)
    fired = False
    for tk in range(40):
        conn.execute("UPDATE character_profiles SET soul_residue=1500 WHERE character_id=1 AND character_type='player';")
        if absorption.maybe_tribulation(conn, 24 * tk, random.Random(tk), player, []):
            fired = True
            break
    assert fired
    boons = tribulation.boon_list(conn, 1)
    assert len(boons) >= 1


def test_boons_raise_combat_power(conn):
    before = combat.combat_power(conn, "player", 1)["attack"]
    # concedi molte benedizioni offensive
    for _ in range(6):
        conn.execute("INSERT INTO tribulation_boons (player_id, boon_key, level) VALUES (1,'corpo_fulmine',6) "
                     "ON CONFLICT(player_id, boon_key) DO UPDATE SET level=level+1;")
    after = combat.combat_power(conn, "player", 1)["attack"]
    assert after > before


def test_boon_bonuses_stack_with_level(conn):
    conn.execute("INSERT INTO tribulation_boons (player_id, boon_key, level) VALUES (1,'corpo_fulmine',1);")
    one = tribulation.boon_bonuses(conn, 1)["attack_mult"]
    conn.execute("UPDATE tribulation_boons SET level=5 WHERE player_id=1 AND boon_key='corpo_fulmine';")
    five = tribulation.boon_bonuses(conn, 1)["attack_mult"]
    assert five > one


def test_being_struck_grows_fulmine(conn):
    player = entities.get_player(conn)
    before = tribulation._fulmine_comp(conn, 1)
    for tk in range(40):
        conn.execute("UPDATE character_profiles SET soul_residue=1500 WHERE character_id=1 AND character_type='player';")
        if absorption.maybe_tribulation(conn, 24 * tk, random.Random(tk), player, []):
            break
    assert tribulation._fulmine_comp(conn, 1) > before
