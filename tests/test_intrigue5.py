"""Aggiornamento 71: le nuove trame scritte a mano si possono giocare dall'inizio alla fine."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import character, encounters, intrigues, intrigue_data5, sects


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "i5.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 4)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    yield c
    c.close()


def test_templates_are_registered():
    keys = set(intrigues._templates())
    assert {t["key"] for t in intrigue_data5.TEMPLATES} <= keys


@pytest.mark.parametrize("tpl", intrigue_data5.TEMPLATES, ids=lambda t: t["key"])
@pytest.mark.parametrize("pick", [1, 2, 3])
def test_each_new_plot_plays(conn, monkeypatch, tpl, pick):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (pick != 2, 99, 1))
    p = entities.get_player(conn)
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    out = intrigues.start(conn, p, tpl["key"], random.Random(pick))
    assert out and "{" not in out, out
    for _ in range(12):
        sc = encounters.pending(conn)
        if not sc:
            d = intrigues.get(conn)
            act = next((x for x in d["active"] if x["key"] == tpl["key"]), None)
            if not act:
                break
            if act.get("pending_end"):
                break
            intrigues.play(conn, entities.get_player(conn), act)
            if not encounters.pending(conn):
                break
            continue
        n = min(pick, len(sc["choices"]))
        txt, _cmd = encounters.choose(conn, entities.get_player(conn), n)
        assert "{" not in txt, txt
