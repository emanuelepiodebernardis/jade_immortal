"""Sette a livelli: tier/elemento, bonus elementale, inviti e ascesa."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import sects, sect_life, character
from engine.simulation import cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "sl2.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _join_first_sect(conn):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))
    return sect


def test_factions_have_tier_and_name(conn):
    for f in sects.joinable_sects(conn):
        assert 1 <= (f["tier"] or 1) <= sects.MAX_SECT_TIER
        assert sects.tier_name(f["tier"])  # nome non vuoto


def test_element_bonus_only_for_matching_dao(conn):
    # forza un elemento noto sulla setta del giocatore
    _join_first_sect(conn)
    m = sects.get_membership(conn)
    conn.execute("UPDATE factions SET element='fulmine' WHERE id=?;", (m["faction_id"],))
    assert sects.element_bonus(conn, "fulmine") == sects.ELEMENT_BONUS
    assert sects.element_bonus(conn, "corpo") == 1.0


def test_winning_tournament_generates_invitations(conn):
    _join_first_sect(conn)
    # forza la vittoria: rendi il giocatore nettamente più forte dei compagni
    t5 = conn.execute("SELECT id FROM cultivation_realms WHERE tier=5;").fetchone()["id"]
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (t5,))
    conn.execute("UPDATE cultivation_records SET realm_id=?, stage=10 "
                 "WHERE character_type='player' AND character_id=1;", (t5,))
    player = __import__("engine.core.entities", fromlist=["entities"]).get_player(conn)
    obs = []
    sect_life.resolve_sect_events(conn, sect_life.CHALLENGE_DELAY, random.Random(2),
                                  player, player.location_id, obs)
    m = sects.get_membership(conn)
    if m["class_rank"] == 1:
        invs = sects.pending_invitations(conn)
        assert len(invs) == 7
        # tutte di tier superiore alla setta attuale
        assert all(i["tier"] > (m["sect_tier"] or 1) for i in invs)


def test_accept_invitation_ascends_to_higher_sect(conn):
    _join_first_sect(conn)
    old = sects.get_membership(conn)
    old_tier = old["sect_tier"] or 1
    # crea manualmente un invito e accettalo
    conn.execute(
        "INSERT INTO sect_invitations (player_id, slot, name, tier, element, hint, created_tick, resolved) "
        "VALUES (1, 1, 'Corte del Cielo Frantumato', ?, 'fulmine', 'test', 0, 0);",
        (min(sects.MAX_SECT_TIER, old_tier + 2),))
    res = sects.accept_invitation(conn, tick=5, rng=random.Random(3), slot=1)
    assert res["status"] == "ascended"
    new = sects.get_membership(conn)
    assert new["faction_id"] != old["faction_id"]
    assert (new["sect_tier"] or 1) > old_tier
    assert new["sect_element"] == "fulmine"
    # l'invito è stato consumato
    assert sects.pending_invitations(conn) == []
    # ti sei trasferito alla nuova sede e hai nuovi compagni
    assert len(sect_life.classmates(conn)) == sect_life.CLASS_SIZE


def test_higher_sect_has_stronger_leader(conn):
    _join_first_sect(conn)
    fid = sects._create_greater_sect(conn, random.Random(9),
                                     "Trono dell'Astro Eterno", tier=5, element="spada", tick=0)
    leader = conn.execute("SELECT leader_id FROM factions WHERE id=?;", (fid,)).fetchone()["leader_id"]
    # leader di una setta tier 5 -> regno alto (>= 5)
    assert cultivation.realm_tier(conn, "npc", leader) >= 5
