"""Rancori e debiti: chi uccidi lascia vendicatori, chi risparmi ti deve la vita."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, feuds, npc_factory, encounters, sects, menus, state
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "feuds.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=9, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _victim(conn, archetype="anziano", seed=1):
    nid = npc_factory.spawn(conn, random.Random(seed), archetype=archetype, location_id=_p(conn).location_id, tier=2)
    return entities.get_npc(conn, nid)


def test_killing_a_respected_elder_leaves_avengers_who_come_for_you(conn):
    v = _victim(conn)
    out = []
    for s in range(6):                                  # con qualche seme almeno un vendicatore giura
        out += feuds.on_kill(conn, 0, random.Random(s), _p(conn), v)
        if feuds.feuds(conn):
            break
    fs = feuds.feuds(conn)
    assert fs and "vendetta" in " ".join(out)
    conn.execute("UPDATE feuds SET ready_day=0;")
    lines = feuds.daily(conn, 120, random.Random(3), _p(conn))
    sc = encounters.pending(conn)
    assert sc and sc["key"] == "vendetta" and len(sc["choices"]) == 4, lines
    f = feuds.feuds(conn)[0]
    assert f["location_id"] == _p(conn).location_id      # ti ha raggiunto


def test_outlaw_victims_leave_few_grudges_and_payment_closes_a_feud(conn):
    v = _victim(conn, "vagabondo", 2)
    conn.execute("INSERT INTO outlaws (npc_id, crime, reward, notoriety) VALUES (?, 'rapina', 100, 1);", (v.id,))
    n, mult = feuds._prominence(conn, v)
    assert mult < 0.5
    v2 = _victim(conn, "anziano", 3)
    for s in range(8):
        feuds.on_kill(conn, 0, random.Random(s), _p(conn), v2)
        if feuds.feuds(conn):
            break
    f = feuds.feuds(conn)[0]
    conn.execute("UPDATE feuds SET intensity=50 WHERE id=?;", (f["id"],))
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)
    out = feuds.command(conn, _p(conn), f"risarcisci {f['id']}")
    assert "chiusa" in out
    assert not any(x["id"] == f["id"] for x in feuds.feuds(conn))


def test_killing_the_avenger_passes_the_feud_to_the_next_generation(conn):
    v = _victim(conn)
    for s in range(8):
        feuds.on_kill(conn, 0, random.Random(s), _p(conn), v)
        if feuds.feuds(conn):
            break
    f = feuds.feuds(conn)[0]
    av = entities.get_npc(conn, f["npc_id"])
    for s in range(10):
        feuds.on_kill(conn, 0, random.Random(100 + s), _p(conn), av)
        nxt = [x for x in feuds.feuds(conn) if x["gen"] == 2]
        if nxt:
            break
    old = conn.execute("SELECT status FROM feuds WHERE id=?;", (f["id"],)).fetchone()["status"]
    assert old == "vendicata"


def test_sparing_by_choice_creates_a_life_debt_that_is_repaid(conn):
    v = _victim(conn, "discepolo", 4)
    conn.execute("UPDATE npc_traits SET honor=95, compassion=90, pride=10 WHERE npc_id=?;", (v.id,))
    out = feuds.on_spare(conn, 0, random.Random(1), _p(conn), v, chosen=True)
    assert out and feuds.debts(conn)
    conn.execute("UPDATE feuds SET ready_day=0 WHERE kind='debito';")
    lines = feuds.daily(conn, 120, random.Random(2), _p(conn))
    assert any("🤝" in ln for ln in lines)
    m = menus.build(conn, _p(conn), "faide")
    assert any("Debiti" in s["title"] for s in m["sections"])
