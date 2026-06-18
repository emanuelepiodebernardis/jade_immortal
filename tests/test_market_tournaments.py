"""Mercato delle pietre, tornei 'giocati' e crescita dei compagni di classe."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, sects, sect_life, market, reports


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "mkt.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _join(conn):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))
    return sects.get_membership(conn, 1)["faction_id"]


# ---------- mercato ----------

def _city(conn):
    return conn.execute("SELECT id FROM locations WHERE location_type='city' LIMIT 1;").fetchone()["id"]


def test_market_only_in_cities(conn):
    city = _city(conn)
    noncity = conn.execute("SELECT id FROM locations WHERE location_type<>'city' LIMIT 1;").fetchone()["id"]
    assert market.is_market_here(conn, city)
    assert not market.is_market_here(conn, noncity)


def test_market_generates_and_sells(conn):
    _join(conn)
    city = _city(conn)
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (city,))
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)
    market.ensure_stock(conn, 1, city)
    rows = market.offers(conn, 1, city)
    assert len(rows) >= 5
    before = sects.get_resource(conn, "pietre_spirituali", 1)
    res = market.buy(conn, 1, city, 1)
    assert res["status"] == "bought"
    assert sects.get_resource(conn, "pietre_spirituali", 1) == before - res["price"]
    # l'oggetto è nello zaino
    from engine.systems import items
    assert any(res["name"] == r["name"] for r in items.player_inventory(conn, 1))
    # e non è più in vendita
    assert len(market.offers(conn, 1, city)) == len(rows) - 1


def test_market_refuses_when_poor(conn):
    city = _city(conn)
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (city,))
    # azzera le pietre
    conn.execute("DELETE FROM player_resources WHERE player_id=1 AND resource='pietre_spirituali';")
    market.ensure_stock(conn, 1, city)
    res = market.buy(conn, 1, city, 1)
    assert res["status"] == "poor"


def test_higher_sect_richer_market(conn):
    _join(conn)
    fac = sects.get_membership(conn, 1)["faction_id"]
    city = _city(conn)
    conn.execute("UPDATE factions SET tier=1 WHERE id=?;", (fac,))
    market.ensure_stock(conn, 1, city)
    low = len(market.offers(conn, 1, city))
    # nuovo giorno + setta tier 5 → mercato più ricco
    conn.execute("DELETE FROM market_offers;")
    conn.execute("UPDATE factions SET tier=5 WHERE id=?;", (fac,))
    market.ensure_stock(conn, 1, city)
    high = len(market.offers(conn, 1, city))
    assert high > low


# ---------- tornei giocati ----------

def test_tournament_produces_report_and_rewards(conn):
    fac = _join(conn)
    before = sects.get_resource(conn, "pietre_spirituali", 1)
    obs = []
    sect_life._run_tournament(conn, 100, random.Random(3), 1, fac,
                              "monthly_tournament", None, obs)
    # report accodato (verrà mostrato comunque)
    queued = reports.drain(conn, 1)
    assert queued and "Classifica finale" in queued[0]
    assert "MENSILE" in queued[0] or "CLASSIFICA" in queued[0].upper()
    # piazzamento e premio
    assert sects.get_membership(conn, 1)["class_rank"] is not None
    assert sects.get_resource(conn, "pietre_spirituali", 1) >= before


def test_tournament_fires_on_time_advance(conn):
    fac = _join(conn)
    # porta l'evento di classifica a scadenza immediata
    conn.execute("UPDATE sect_events SET fire_tick=0 WHERE player_id=1 AND resolved=0;")
    conn.commit()
    from engine.simulation import world_tick
    obs = []
    world_tick.advance(conn, 5)         # qualunque avanzamento fa scattare il torneo
    # il report è in coda anche se le osservazioni non fossero state mostrate
    queued = reports.drain(conn, 1)
    assert any("Classifica finale" in q for q in queued)


# ---------- crescita dei compagni ----------

def test_classmates_grow_by_talent(conn):
    _join(conn)
    mates = [r["npc_id"] for r in conn.execute(
        "SELECT npc_id FROM sect_cohort WHERE player_id=1;").fetchall()]
    assert len(mates) >= 2
    dull, gifted = mates[0], mates[1]
    conn.execute("UPDATE sect_cohort SET talent=10 WHERE npc_id=?;", (dull,))
    conn.execute("UPDATE sect_cohort SET talent=100 WHERE npc_id=?;", (gifted,))
    # azzera le comprensioni per un confronto pulito
    conn.execute("UPDATE character_daos SET comprehension=0 WHERE character_type='npc' AND character_id IN (?,?);",
                 (dull, gifted))
    conn.commit()
    for d in range(10):
        sect_life.daily_cohort_growth(conn, random.Random(d), 1)
    cd = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='npc' AND character_id=?;",
                      (dull,)).fetchone()["comprehension"]
    cg = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='npc' AND character_id=?;",
                      (gifted,)).fetchone()["comprehension"]
    assert cg > cd                       # il più dotato cresce più in fretta
