"""Aggiornamento 84: i volti del destino e le voci dal mondo, leggere il nemico nel duello."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, destiny_faces, duel, duel_reading, npc_factory, npc_memory


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a84.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=14, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _foe(conn, tier=1, stage=1, arch="discepolo"):
    nid = npc_factory.spawn(conn, random.Random(5), archetype=arch, location_id=_p(conn).location_id,
                            tier=tier, stage=stage)
    return nid, conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"].split()[0]


def test_faces_collect_memories_and_news(conn):
    nid, _ = _foe(conn)
    npc_memory.remember(conn, nid, "sconfitto", "Villaggio")
    fs = destiny_faces.faces(conn, _p(conn))
    f = next(x for x in fs if x["id"] == nid)
    assert f["tono"] == "rancore" and f["qui"] and "battuto" in " ".join(f["storia"])
    assert destiny_faces.daily(conn, 0, random.Random(1), _p(conn)) == []          # la prima volta si annota soltanto
    npc_factory.raise_npc(conn, nid, 12)
    out = destiny_faces.daily(conn, 240, random.Random(1), _p(conn))
    assert out and out[0].startswith("📜 Voci dal mondo") and "ha raggiunto" in out[0]
    assert destiny_faces.news_feed(conn)[0]["npc"] == nid


def test_archrival_is_first(conn):
    from engine.systems import archrival
    nid, _ = _foe(conn)
    npc_memory.remember(conn, nid, "aiutato", "Villaggio")
    archrival.create(conn, random.Random(3), _p(conn))
    fs = destiny_faces.faces(conn, _p(conn))
    assert fs[0]["ruolo"].startswith("Arcinemico") and fs[0]["tono"] == "odio"


def test_weak_point_and_feint_reading(conn):
    nid, first = _foe(conn)
    duel.start(conn, _p(conn), first)
    d = duel.get(conn)
    d["style"], d["weak"], d["weak_known"] = "impetuoso", "impetuoso", True
    lines: list[str] = []
    assert duel_reading.attack_mult(d, "colpisci", lines, "carica") == pytest.approx(1.6) and lines
    assert duel_reading.attack_mult(d, "colpisci", [], None) == 1.0
    d["weak"] = "equilibrato"
    assert duel_reading.attack_mult(d, "tecnica", [], None) == pytest.approx(1.2)
    # un senso divino fortissimo legge la finta e scopre subito il punto debole
    conn.execute("INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
                 "VALUES ('player', 1, 'anima', 50, 5000, 1) ON CONFLICT(character_type, character_id, dao_key) "
                 "DO UPDATE SET comprehension=5000;")
    d.update({"weak_known": False, "charge_e": True, "feint": True, "round": 2, "style": "subdolo", "weak": "subdolo"})
    out = duel_reading.on_turn(conn, _p(conn), d, random.Random(1))
    assert d["weak_known"] and d["read"] == "finta" and any("FINTA" in x for x in out)
    duel._save(conn, d)
    a = duel.arena(conn, _p(conn))
    assert a["intento"]["tipo"] == "finta" and a["lettura"]["noto"]


def test_duel_still_plays_through(conn):
    from engine.cli import loop
    from engine.systems import encounters
    nid, first = _foe(conn)
    loop.dispatch(conn, f"duello {first}", allow_nl=False)
    for _ in range(80):
        sc = encounters.pending(conn)
        if not sc or not duel.get(conn):
            break
        if sc["title"].endswith("è a terra"):
            loop.dispatch(conn, "2", allow_nl=False)
            break
        loop.dispatch(conn, "1" if _ % 3 else "Difendi", allow_nl=False)
    assert duel.get(conn) is None or _p(conn).status != "alive"


def test_volti_command(conn):
    from engine.cli import loop
    assert "Nessuno" in loop.dispatch(conn, "volti", allow_nl=False)
    nid, _ = _foe(conn)
    npc_memory.remember(conn, nid, "risparmiato", "Villaggio")
    assert "VOLTI DEL DESTINO" in loop.dispatch(conn, "volti", allow_nl=False)
