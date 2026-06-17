"""Doppia reputazione della maschera (9): l'identità mascherata accumula la SUA
infamia/sospetto, mentre il vero nome resta pulito."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import reputation, character
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "mask.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


# ---------- unit: routing ----------

def test_apply_deed_unmasked_hits_real(conn):
    reputation.apply_deed(conn, infamy=20, suspicion=10)
    assert reputation.get(conn)["infamy"] == 20
    assert reputation.get_mask(conn)["infamy"] == 0


def test_apply_deed_masked_hits_mask_with_leak(conn):
    reputation.set_disguise(conn, on=True)
    reputation.apply_deed(conn, infamy=20, suspicion=10, mask_leak=4)
    real = reputation.get(conn)
    mask = reputation.get_mask(conn)
    assert mask["infamy"] == 20 and mask["suspicion"] == 10   # tutto sulla maschera
    assert real["infamy"] == 0                                 # nome pulito
    assert real["suspicion"] == 4                              # solo la piccola fuga


def test_get_still_returns_four_keys(conn):
    # contratto preesistente: reputation.get() non deve cambiare forma
    r = reputation.get(conn)
    assert set(r.keys()) == {"fame", "infamy", "suspicion", "disguised"}


# ---------- integrazione: absorb mascherato ----------

def _setup_corpse_and_witness(conn):
    ploc = entities.get_player(conn).location_id
    dead = conn.execute(
        "SELECT id, name FROM npcs WHERE kind='human' AND status='alive' LIMIT 1;").fetchone()
    witness = conn.execute(
        "SELECT id FROM npcs WHERE kind='human' AND status='alive' AND id<>? LIMIT 1;",
        (dead["id"],)).fetchone()
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (ploc, witness["id"]))
    conn.execute("UPDATE npcs SET status='dead', death_tick=0, location_id=? WHERE id=?;",
                 (ploc, dead["id"]))
    conn.commit()
    return dead


def test_masked_absorb_routes_infamy_to_mask(conn):
    dead = _setup_corpse_and_witness(conn)
    reputation.set_disguise(conn, on=True)
    player = entities.get_player(conn)
    frag = dead["name"].split()[0]
    out = loop.cmd_absorb(conn, player, frag)            # mascherato: niente gate testimoni
    # l'assorbimento è avvenuto
    assert conn.execute("SELECT status FROM npcs WHERE id=?;",
                        (dead["id"],)).fetchone()["status"] == "absorbed"
    mask = reputation.get_mask(conn)
    real = reputation.get(conn)
    assert mask["infamy"] > 0 and mask["suspicion"] > 0   # la maschera si macchia
    assert real["infamy"] == 0                            # il tuo nome resta pulito
    assert real["suspicion"] <= 5                         # solo la piccola fuga
    assert "mascherata" in out.lower()


def test_unmasked_absorb_hits_real_not_mask(conn):
    dead = _setup_corpse_and_witness(conn)
    player = entities.get_player(conn)
    frag = dead["name"].split()[0]
    loop.cmd_absorb(conn, player, f"{frag} confirm")     # a volto scoperto, con conferma
    real = reputation.get(conn)
    mask = reputation.get_mask(conn)
    assert real["infamy"] > 0 and real["suspicion"] > 0
    assert mask["infamy"] == 0 and mask["suspicion"] == 0


# ---------- titoli e display della maschera ----------

def test_mask_title_emerges_with_infamy(conn):
    reputation.set_disguise(conn, on=True)
    reputation.adjust_mask(conn, infamy=700)             # soglia Eretico
    assert reputation.mask_alignment_of(conn) == "Eretico"
    assert reputation.mask_title(conn) == "Lo Spettro dell'Abisso"
    # e il tuo vero allineamento resta Neutrale
    assert reputation.alignment_of(conn) == "Neutrale"


def test_mask_line_none_when_clean(conn):
    assert reputation.mask_line(conn) is None
    reputation.adjust_mask(conn, infamy=150)
    assert reputation.mask_line(conn) is not None
