"""Regni delle razze: campioni, sangue d'alto lignaggio, reliquie, la scala fino al trono."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, race_realms as RR, races, bloodlines, items, menus, sects
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "rr.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=13, factions=3, static_npc_count=15))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _go_land(conn, key):
    land = RR._land(conn, key)
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (land,))
    return land


def test_champion_spawns_in_the_land_with_a_title_and_kind(conn):
    _go_land(conn, "draghi")
    nid = RR.ensure_champion(conn, _p(conn), "draghi")
    r = conn.execute("SELECT kind, description, name FROM npcs WHERE id=?;", (nid,)).fetchone()
    assert r["kind"] == "beast" and "Guardiano della Rupe" in r["description"] and r["name"].startswith("Ao ")
    assert RR.race_of_npc(conn, nid) == ("draghi", 1)
    assert RR.ensure_champion(conn, _p(conn), "draghi") == nid      # uno alla volta


def test_killing_a_champion_leaves_high_blood_and_raises_the_next(conn):
    _go_land(conn, "demoni")
    nid = RR.ensure_champion(conn, _p(conn), "demoni")
    npc = entities.get_npc(conn, nid)
    out = RR.on_defeat(conn, 0, random.Random(2), _p(conn), npc, "kill")
    assert any("Sangue del Sentinella" in ln or "Sangue del" in ln for ln in out), out
    inv = conn.execute("SELECT i.name, i.effects FROM inventories v JOIN items i ON i.id=v.item_id "
                       "WHERE v.owner_type='player' AND i.item_type='essenza';").fetchall()
    assert any("Demone Celeste" in r["effects"] for r in inv)
    assert RR.get(conn)["demoni"]["beaten"] == 1
    nid2 = RR.ensure_champion(conn, _p(conn), "demoni")
    assert nid2 != nid and RR.race_of_npc(conn, nid2) == ("demoni", 2)


def test_sparing_gives_honor_and_half_blood_spirits_give_soul(conn):
    _go_land(conn, "spiriti")
    nid = RR.ensure_champion(conn, _p(conn), "spiriti")
    h0 = races.all_r(conn)["spiriti"]["honor"]
    out = RR.on_defeat(conn, 0, random.Random(3), _p(conn), entities.get_npc(conn, nid), "spare")
    assert races.all_r(conn)["spiriti"]["honor"] > h0
    assert any("Essenza d'Anima" in ln for ln in out)
    out = loop.dispatch(conn, "use essenze", allow_nl=False)
    assert "Spirito" in out or "spirito" in out
    assert RR.blood_grade(conn, "spiriti") >= 0


def test_relics_absorb_or_offer_and_the_ladder_to_the_throne(conn):
    _go_land(conn, "giganti")
    p = _p(conn)
    # discepolo
    races.adjust(conn, "giganti", rel=20, honor=60)
    assert "Discepolo" in RR.ascend(conn, p, "giganti")
    # reliquie: offerta e assorbimento
    rng = random.Random(5)
    for _ in range(4):
        rid, _n = RR.relic_item(conn, "giganti", rng, 2)
        items.grant(conn, "player", 1, rid)
    assert "Reliquie offerte: 1" in RR.offer_relic(conn, p, "giganti")
    out = loop.dispatch(conn, "use " + conn.execute(
        "SELECT i.name FROM inventories v JOIN items i ON i.id=v.item_id WHERE i.item_type='reliquia' "
        "AND v.owner_type='player' LIMIT 1;").fetchone()["name"], allow_nl=False)
    assert "Gigante Antico" in out
    RR.offer_relic(conn, p, "giganti")
    RR.offer_relic(conn, p, "giganti")
    # sangue alto e campioni battuti → fino al trono (via della forza)
    bloodlines.gain(conn, 0, rng, p, "Gigante Antico", ["terra", "corpo"], 300)
    d = RR.get(conn)
    d["giganti"]["beaten"] = 5
    RR._save(conn, d)
    for n in ("Campione", "Anziano", "Principe"):
        assert n in RR.ascend(conn, p, "giganti")
    out = RR.ascend(conn, p, "giganti")
    assert "Re dei Giganti" in out, out
    assert RR.get(conn)["giganti"]["standing"] == 5
    assert RR.war_power(conn)[0] > 0
    txt = menus.render(conn, menus.build(conn, p, "razze"))
    assert "Re dei Giganti" in txt and "Draghi" in txt


def test_requirements_block_and_challenge_needs_the_land(conn):
    p = _p(conn)
    assert "ti manca" in RR.ascend(conn, p, "draghi")
    conn.execute("UPDATE players SET location_id=(SELECT id FROM locations WHERE id<>? LIMIT 1) WHERE id=1;",
                 (RR._land(conn, "draghi"),))
    assert "attende nelle sue terre" in RR.challenge(conn, _p(conn), "draghi")
    _go_land(conn, "draghi")
    sects.grant_resource(conn, "pietre_spirituali", 0, 1)
    out = RR.challenge(conn, _p(conn), "draghi")
    assert "DUELLO" in out.upper() or "Duello" in out
