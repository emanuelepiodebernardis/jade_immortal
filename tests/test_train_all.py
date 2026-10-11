"""Allenamento d'insieme (`train` / `t`): Qi, tutti i Dao (i rari più lenti) e l'arte in una sola azione."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import character, professions, train_all
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "tr.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=3, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _comp(conn, k):
    return conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' "
                        "AND character_id=1 AND dao_key=?;", (k,)).fetchone()["comprehension"]


def test_train_grows_everything_at_once(conn):
    loop.dispatch(conn, "profession alchimia", allow_nl=False)
    for k in ("spada", "destino"):
        dao_gen._set_dao(conn, "player", 1, k, 60, 1, 1)
    p0 = cultivation.get_record(conn, "player", 1)["progress"]
    t0 = tick.get_tick(conn)
    out = loop.dispatch(conn, "t", allow_nl=False)
    assert "Allenamento d'insieme" in out
    assert tick.get_tick(conn) - t0 == tick.cost_of("cultivate")          # una sola azione
    assert cultivation.get_record(conn, "player", 1)["progress"] > p0
    for i in range(40):
        loop.dispatch(conn, "train", allow_nl=False)
        if i % 4 == 3:
            loop.dispatch(conn, "sleep", allow_nl=False)
    assert _comp(conn, "spada") > 1 and _comp(conn, "destino") > 1          # crescono tutti…
    assert _comp(conn, "spada") > _comp(conn, "destino")                    # …ma i profondi più lenti
    assert professions.xp(conn, 1) > 0


def test_rarity_order():
    r = train_all.RARITY
    assert r["narrative"] > r["elemental"] > r["systemic"] > r["superior"] > r["deep"]
    assert train_all.short("Dao della Spada") == "Spada"


def test_autopilot_uses_train_by_default(conn, monkeypatch):
    from engine.systems import autopilot
    assert autopilot.config(conn)["attivita"]["allena"] > 0
    assert autopilot.config(conn)["attivita"]["coltiva"] == 0
    autopilot.command(conn, entities_player(conn), "imposta attivita allena=5 caccia=0 raccolta=0 lavoro=0 insegna=0")
    seen = []
    orig = loop.dispatch

    def spy(c, cmd, allow_nl=True):
        seen.append(cmd)
        return orig(c, cmd, allow_nl=allow_nl)
    monkeypatch.setattr(loop, "dispatch", spy)
    dao_gen._set_dao(conn, "player", 1, "fuoco", 60, 1, 1)
    autopilot.run(conn, entities_player(conn), 3)
    assert "train" in seen and "cultivate" not in seen


def entities_player(conn):
    from engine.core import entities
    return entities.get_player(conn)
