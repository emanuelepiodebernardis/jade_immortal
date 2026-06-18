"""Caccia territoriale: uccidere creature dà fama e lava i sospetti; sterminarne troppe
evoca un CAMPIONE della specie che ti dà la caccia."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import creature_gen
from engine.systems import character, hunters, reputation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "terr.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    character.apply_origin(c, "genio", random.Random(1))
    # giocatore fortissimo (abbatte tutto)
    r8 = c.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (r8,))
    c.execute("UPDATE cultivation_records SET realm_id=?, stage=8 WHERE character_type='player' AND character_id=1;", (r8,))
    c.execute("UPDATE character_profiles SET grow_strength=4000, grow_vitality=4000, grow_resistance=4000 WHERE character_type='player' AND character_id=1;")
    c.commit()
    yield c
    c.close()


def test_creature_kills_raise_fame_and_clear_suspicion(conn):
    # parto con sospetto/infamia alti
    reputation.adjust(conn, 1, suspicion=50, infamy=30)
    s0 = reputation.get(conn, 1)
    loc = entities.get_player(conn).location_id
    bid = creature_gen._spawn_one(conn, random.Random(1), "beast", loc, 2, 2)
    conn.execute("UPDATE npcs SET status='dead', death_tick=0 WHERE id=?;", (bid,))
    conn.commit()
    loop._after_player_kill(conn, 5, random.Random(2), entities.get_player(conn),
                            entities.get_npc(conn, bid), None)
    s1 = reputation.get(conn, 1)
    assert s1["fame"] > s0["fame"]
    assert s1["suspicion"] < s0["suspicion"]


def test_champion_summoned_after_threshold(conn):
    player = entities.get_player(conn)
    msg = None
    for _ in range(hunters.SPECIES_KILL_THRESHOLD):
        msg = hunters.record_creature_kill(conn, 10, random.Random(3), player, "beast")
    assert msg is not None and "tracce" in msg.lower()
    # esiste ora un campione bestiale in caccia
    champ = conn.execute(
        "SELECT id, kind, hunting FROM npcs WHERE name=? AND hunting=1;",
        (hunters._CHAMPION_NAME["beast"],)).fetchone()
    assert champ is not None and champ["kind"] == "beast"


def test_below_threshold_no_champion(conn):
    player = entities.get_player(conn)
    out = hunters.record_creature_kill(conn, 10, random.Random(4), player, "demon")
    assert out is None
    cnt = conn.execute("SELECT value FROM game_state WHERE key='species_kills:demon';").fetchone()
    assert int(cnt["value"]) == 1


def test_defeating_champion_grants_fame(conn):
    loc = entities.get_player(conn).location_id
    cid = creature_gen._spawn_one(conn, random.Random(5), "beast", loc, 3, 3)
    conn.execute("UPDATE npcs SET hunting=1, name='Re Bestiale' WHERE id=?;", (cid,))
    conn.commit()
    f0 = reputation.get(conn, 1)["fame"]
    msg = hunters.on_hunter_defeated(conn, cid, entities.get_player(conn))
    assert msg is not None and "fama" in msg.lower()
    assert reputation.get(conn, 1)["fame"] > f0


def test_hit_desc_varies(conn):
    # la descrizione del colpo pesca da più formulazioni
    seen = set()
    for s in range(12):
        seen.add(loop._hit_desc(50, 100, "Tizio", False, random.Random(s)))
    assert len(seen) >= 2


def test_enemy_line_varies(conn):
    seen = set()
    for s in range(14):
        seen.add(loop._enemy_line("Nemico", 40, 100, False, random.Random(s)))
    assert len(seen) >= 2


def test_combat_flavor_pool_nonempty():
    assert len(loop._COMBAT_FLAVOR) >= 4
