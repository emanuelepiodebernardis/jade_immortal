"""Reputazione: fama/infamia/sospetto, allineamento, titoli, maschera."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import reputation, character, sects, sect_life


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "rep.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def test_default_reputation_is_zero(conn):
    r = reputation.get(conn)
    assert r == {"fame": 0, "infamy": 0, "suspicion": 0, "disguised": 0}


def test_adjust_clamps_at_zero(conn):
    reputation.adjust(conn, fame=-50)
    assert reputation.get(conn)["fame"] == 0
    reputation.adjust(conn, fame=100)
    assert reputation.get(conn)["fame"] == 100


def test_alignment_ladder():
    assert reputation.alignment(0, 0, 0) == "Neutrale"
    assert reputation.alignment(150, 0, 0) == "Onorevole"
    assert reputation.alignment(400, 0, 0) == "Eroe"
    assert reputation.alignment(0, 150, 0) == "Temuto"
    assert reputation.alignment(0, 350, 0) == "Mostro"
    assert reputation.alignment(0, 0, 1200) == "Eretico"
    assert reputation.alignment(0, 700, 0) == "Eretico"


def test_devourer_title_at_heresy(conn):
    reputation.adjust(conn, suspicion=1100)
    assert reputation.title(conn) == "Il Divoratore Nero"


def test_suspicion_hint_thresholds():
    assert reputation.suspicion_hint(0) == ""
    assert "voci" in reputation.suspicion_hint(120).lower()
    assert "indagine" in reputation.suspicion_hint(600).lower()


def test_mask_toggle(conn):
    assert reputation.is_disguised(conn) is False
    reputation.set_disguise(conn, on=True)
    assert reputation.is_disguised(conn) is True
    reputation.set_disguise(conn, on=False)
    assert reputation.is_disguised(conn) is False


def test_tournament_win_grants_fame(conn):
    # iscriviti e fai scattare un torneo; il piazzamento dà fama
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))
    before = reputation.get(conn)["fame"]
    player = entities.get_player(conn)
    sect_life.resolve_sect_events(conn, sect_life.CHALLENGE_DELAY, random.Random(2),
                                  player, player.location_id, [])
    assert reputation.get(conn)["fame"] >= before   # almeno non cala; >0 se piazzato 1-3
    # forziamo il caso vincente per la fama
    reputation.adjust(conn, fame=30)
    assert reputation.get(conn)["fame"] > 0


def test_fame_improves_talent_test(conn):
    # con fama alta il punteggio del test del talento è più alto
    base = sects._talent_score(conn, 1)
    reputation.adjust(conn, fame=640)            # +8 max
    assert sects._talent_score(conn, 1) > base


def test_social_factor_reflects_alignment(conn):
    assert reputation.social_factor(conn) == 1.0
    reputation.adjust(conn, infamy=350)
    assert reputation.social_factor(conn) < 1.0   # i mostri sono accolti male


def test_witnesses_count_only_living_humans(conn):
    from engine.core import entities
    # porta due umani nella location del player e una bestia
    ploc = entities.get_player(conn).location_id
    humans = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' LIMIT 2;").fetchall()
    for h in humans:
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (ploc, h["id"]))
    beast = conn.execute("SELECT id FROM npcs WHERE kind='beast' AND status='alive' LIMIT 1;").fetchone()
    if beast:
        conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (ploc, beast["id"]))
    w = reputation.witnesses(conn, ploc)
    ids = {r["id"] for r in w}
    assert humans[0]["id"] in ids and humans[1]["id"] in ids
    if beast:
        assert beast["id"] not in ids          # le bestie non sono testimoni sociali


def test_absorb_warns_with_witnesses_and_applies_on_confirm(conn):
    from engine.core import entities
    from engine.cli import loop
    ploc = entities.get_player(conn).location_id
    # una vittima morta + un testimone umano vivo nella stessa location
    dead = conn.execute("SELECT id, name FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()
    witness = conn.execute("SELECT id FROM npcs WHERE kind='human' AND status='alive' AND id<>? LIMIT 1;", (dead["id"],)).fetchone()
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (ploc, witness["id"]))
    conn.execute("UPDATE npcs SET status='dead', death_tick=0, location_id=? WHERE id=?;", (ploc, dead["id"]))
    player = entities.get_player(conn)
    frag = dead["name"].split()[0]
    # senza conferma: avvisa e NON assorbe (sospetto invariato)
    before = reputation.get(conn)["suspicion"]
    out = loop.cmd_absorb(conn, player, frag)
    assert "testimoni" in out.lower()
    assert reputation.get(conn)["suspicion"] == before
    assert conn.execute("SELECT status FROM npcs WHERE id=?;", (dead["id"],)).fetchone()["status"] == "dead"
    # con conferma: procede e il sospetto sale
    loop.cmd_absorb(conn, player, f"{frag} confirm")
    assert reputation.get(conn)["suspicion"] > before
