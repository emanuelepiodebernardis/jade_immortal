"""La frontiera: la mappa di ogni mondo si allarga col livello (Aggiornamento 47)."""
import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, frontier, ascension


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "fr.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=7, factions=4, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _realm(c, tier, stage=1):
    rid = c.execute("SELECT id FROM cultivation_realms WHERE tier=?;", (tier,)).fetchone()[0]
    c.execute("UPDATE players SET realm_id=?;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=?, stage=? WHERE character_type='player';", (rid, stage))


def test_map_grows_with_level_and_is_complete_at_the_peak(conn):
    p = entities.get_player(conn)
    base = len(ascension.plane_locations(conn, 0))
    assert frontier.expand(conn, p) == []                       # all'inizio: solo il cuore del mondo
    _realm(conn, 4, 5)
    out = frontier.expand(conn, p)
    mid = len(ascension.plane_locations(conn, 0))
    assert out and mid > base
    w = frontier.world(conn, 0)
    far = [int(k) for k, r in w["loc_ring"].items() if r == w["rings"]]
    tiers = [conn.execute("SELECT r.tier FROM npcs n JOIN cultivation_realms r ON r.id=n.realm_id "
                          "WHERE n.location_id=? AND n.status='alive';", (l,)).fetchall() for l in far]
    assert any(t for t in tiers)
    _realm(conn, 9, 1)
    out = frontier.expand(conn, p)
    assert any("mappa completa" in x for x in out)
    assert frontier.world(conn, 0)["rings"] == frontier.ring_count(0)
    # coordinate uniche: nessun luogo sovrapposto
    cs = frontier.ensure_coords(conn, 0)
    assert len(set(cs.values())) == len(cs)


def test_mysteries_once_and_richer_far_away(conn):
    p = entities.get_player(conn)
    _realm(conn, 6, 1)
    frontier.expand(conn, p)
    w = frontier.world(conn, 0)
    lid = int(next(iter(w["mysteries"])))
    entities.move_player(conn, p.id, lid)
    p = entities.get_player(conn)
    assert frontier.mystery_here(conn, p)
    assert "❖" in frontier.resolve(conn, p, "prudente")
    assert frontier.mystery_here(conn, p) is None
    assert frontier.gather_mult(conn, lid) > 1.0


def test_journey_in_stages(conn):
    from engine.systems import travel
    p = entities.get_player(conn)
    _realm(conn, 1, 5)
    locs = ascension.plane_locations(conn, 0)
    far = max(locs, key=lambda l: len(travel.route(conn, p.location_id, l)))
    path = travel.route(conn, p.location_id, far)
    assert path[0] == p.location_id and path[-1] == far and len(path) >= 3
    out = travel.go(conn, p, f"#{far}")
    assert "tappe" in out
    p = entities.get_player(conn)
    assert p.location_id in path[1:]                       # arrivato, o fermato lungo la strada
