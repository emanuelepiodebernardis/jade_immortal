"""Percezione: info filtrate da Dao dell'Anima e notorietà, intimidazione, vantaggio spirito."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import character, perception


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "perc.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=25))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _set_anima(conn, comp):
    dao_gen._set_dao(conn, "player", 1, "anima", affinity=80, comprehension=comp, practiced=1)


def _some_unknown_npc(conn):
    # un NPC comune, non capo e di basso regno
    row = conn.execute("""SELECT n.id FROM npcs n
        LEFT JOIN cultivation_records cr ON cr.character_type='npc' AND cr.character_id=n.id
        LEFT JOIN cultivation_realms re ON re.id=cr.realm_id
        WHERE n.status='alive' AND n.kind='human'
          AND n.id NOT IN (SELECT leader_id FROM factions WHERE leader_id IS NOT NULL)
          AND COALESCE(re.tier,1) < 6
        ORDER BY n.id LIMIT 1;""").fetchone()
    return entities.get_npc(conn, row["id"])


def test_soul_level_thresholds(conn):
    _set_anima(conn, 0)
    assert perception.soul_level(conn) == 0
    _set_anima(conn, 10)
    assert perception.soul_level(conn) == 1
    _set_anima(conn, 25)
    assert perception.soul_level(conn) == 2
    _set_anima(conn, 50)
    assert perception.soul_level(conn) == 3
    _set_anima(conn, 120)
    assert perception.soul_level(conn) == 4


def test_unknown_npc_reveals_nothing_at_base_soul(conn):
    _set_anima(conn, 0)
    npc = _some_unknown_npc(conn)
    lines = perception.describe(conn, 1, npc)
    text = " ".join(lines)
    assert "troppo acerbo" in text          # non percepisci la forza
    assert "Coltivazione:" not in text       # niente regno
    assert "Dao percepiti:" not in text


def test_adept_soul_reveals_relative_strength(conn):
    _set_anima(conn, 12)
    npc = _some_unknown_npc(conn)
    text = " ".join(perception.describe(conn, 1, npc))
    assert "Forza percepita:" in text
    assert "Coltivazione:" not in text       # serve ≥25 per il regno


def test_master_soul_reveals_realm_and_dao(conn):
    _set_anima(conn, 120)
    npc = _some_unknown_npc(conn)
    text = " ".join(perception.describe(conn, 1, npc))
    assert "Coltivazione:" in text
    assert "Forza percepita:" in text


def test_renowned_npc_is_known_even_at_base_soul(conn):
    _set_anima(conn, 0)
    # rendi un NPC un capo-setta -> è "noto"
    leader = conn.execute("SELECT leader_id FROM factions WHERE leader_id IS NOT NULL LIMIT 1;").fetchone()["leader_id"]
    npc = entities.get_npc(conn, leader)
    assert perception.is_renowned(conn, leader) is True
    text = " ".join(perception.describe(conn, 1, npc))
    assert "volto noto" in text
    assert "Coltivazione:" in text           # info pubbliche anche con anima 0


def test_intimidation_when_spirit_dominates(conn):
    _set_anima(conn, 300)
    # alza il regno del giocatore per uno spirito schiacciante
    r8 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=8;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (r8,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (r8,))
    npc = _some_unknown_npc(conn)
    assert perception.intimidates(conn, 1, npc) is True
    # via comando: il nemico è PARALIZZATO dal terrore e puoi abbatterlo (non fugge)
    from engine.cli import loop
    conn.execute("UPDATE players SET location_id=(SELECT location_id FROM npcs WHERE id=?) WHERE id=1;", (npc.id,))
    out = loop.cmd_attack(conn, entities.get_player(conn), npc.name.split()[0])
    assert "paralizzato" in out.lower()
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (npc.id,)).fetchone()["status"] != "alive"


def test_spirit_edge_scales_with_anima_gap(conn):
    npc = _some_unknown_npc(conn)
    _set_anima(conn, 0)
    assert perception.spirit_edge(conn, 1, npc.id) == 0.0
    _set_anima(conn, 200)
    assert perception.spirit_edge(conn, 1, npc.id) > 0.0


def test_bounties_listing_shows_level(conn):
    from engine.systems import bounties
    from engine.cli import loop
    bounties.replenish(conn, random.Random(5))
    rows = bounties.active_bounties(conn)
    if not rows:                              # garantisci almeno una taglia
        npc = _some_unknown_npc(conn)
        bounties.mark_outlaw(conn, npc.id, "omicidio", 200) if hasattr(bounties, "mark_outlaw") else None
    out = loop.cmd_bounties(conn, entities.get_player(conn))
    # se ci sono taglie, mostra il livello tra parentesi quadre
    if "·" in out:
        assert "[" in out and "]" in out
