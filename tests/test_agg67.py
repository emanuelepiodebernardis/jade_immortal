"""Aggiornamento 67: compagni perduti, meridiani, Corpo del Dharma, sigilli ancestrali, idle, sblocchi."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import (character, state, sects, soul_arcs, intrigues, encounters, lost_companions as lc,
                            meridians, dharma_body, ancestral_sigils as sg, idle_cultivation as idle, unlocks,
                            bonds, dao_heart)


def _world(tmp_path, monkeypatch, origin="trasmigratore", tier=6):
    p = tmp_path / f"a67_{origin}.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=7, factions=4, static_npc_count=25))
    character.apply_origin(c, origin, random.Random(3))
    rid = cultivation.ensure_realm(c, tier)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    return c


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    c = _world(tmp_path, monkeypatch)
    yield c
    c.close()


def _p(c):
    return entities.get_player(c)


# ---------------------------------------------------------------- compagni perduti

def test_saga_registered_and_names(conn):
    assert "compagni" in soul_arcs.ARCS and soul_arcs.NAMES["compagni"]
    tpls = intrigues._templates()
    for ch in soul_arcs.ARCS["compagni"]:
        assert ch["plot"] in tpls
    nid = lc.npc(conn, _p(conn), "santa")
    assert conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"] == "Giulia Ferri"
    nm = lc.names(conn)
    assert "compagni di classe" in nm["gruppo"]


def test_saga_other_origin_uses_caravan(tmp_path, monkeypatch):
    c = _world(tmp_path, monkeypatch, "divoratore")
    assert "carovana" in lc.names(c)["gruppo"]
    lc.prepare(c, _p(c), "compagni_varco")
    assert lc.names(c)["amico"] != lc.ROLE_LABEL["amico"]            # il ricordo ha già un nome


def test_found_companion_becomes_sworn(conn):
    p = _p(conn)
    lc.prepare(conn, p, "compagni_amico")
    nid = lc.get(conn)["npcs"]["amico"]
    out = lc.on_chapter(conn, p, "compagni_amico", "riscattato", True)
    assert lc.get(conn)["fate"]["amico"] == "fratello"
    assert any("fratello giurato" in ln for ln in out)
    assert conn.execute("SELECT 1 FROM bonds WHERE npc_id=? AND kind='sworn';", (nid,)).fetchone()


def test_check_success_does_not_start_the_duel(conn, monkeypatch):
    p = _p(conn)
    monkeypatch.setattr(encounters, "roll", lambda *a, **k: (True, 99, 0))
    lc.prepare(conn, p, "compagni_cacciatore")
    intrigues.start(conn, p, "compagni_cacciatore", branches=[])
    from engine.cli import loop
    loop.dispatch(conn, "2", allow_nl=False)                           # gli racconti la verità (prova riuscita)
    from engine.systems import duel
    assert duel.get(conn) is None
    done = [x for x in intrigues.get(conn)["done"] if x["key"] == "compagni_cacciatore"]
    assert done and done[-1]["outcome"] == "verita"


# ---------------------------------------------------------------- meridiani

def test_meridians_open_temper_and_effects(conn, monkeypatch):
    p = _p(conn)
    sects.grant_resource(conn, "pietre_spirituali", 200000, p.id)
    assert meridians.openable(conn) == 12 + 2
    for _ in range(12):
        meridians.open_next(conn, p)
    assert meridians.get(conn)["open"] >= 3
    b0 = meridians.bonus(conn)
    out = meridians.temper_all(conn, p, budget=20000)
    assert "livelli" in out
    b1 = meridians.bonus(conn)
    assert sum(b1.values()) > sum(b0.values())
    assert 0 < meridians.toxin_factor(conn) <= 1.0
    assert "MERIDIANI" in meridians.command(conn, p, "")


def test_meridians_respect_realm(tmp_path, monkeypatch):
    c = _world(tmp_path, monkeypatch, "mortale", tier=1)
    p = _p(c)
    sects.grant_resource(c, "pietre_spirituali", 100000, p.id)
    d = meridians.get(c)
    d["open"], d["lv"] = 3, [0, 0, 0]
    meridians._save(c, d)
    assert "non cede" in meridians.open_next(c, p)


# ---------------------------------------------------------------- Corpo del Dharma

def test_dharma_awaken_and_grow(conn):
    p = _p(conn)
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    assert "desto" in dharma_body.awaken(conn, p)
    g0 = dharma_body.get(conn)["grade"]
    dharma_body.nourish(conn, p, 20000)
    assert dharma_body.get(conn)["grade"] > g0
    assert dharma_body.atk_bonus(conn) > 0
    assert dharma_body.daily(conn, tick.get_tick(conn), random.Random(1), p) is not None


def test_dharma_needs_third_realm(tmp_path, monkeypatch):
    c = _world(tmp_path, monkeypatch, "mortale", tier=2)
    sects.grant_resource(c, "pietre_spirituali", 100000, 1)
    assert "dal 3°" in dharma_body.awaken(c, _p(c))


# ---------------------------------------------------------------- sigilli

def test_sigils_fuse_and_sets(conn):
    sg.give(conn, 0)
    assert "stelle" in sg.give(conn, 0)
    assert sg.get(conn)["owned"]["0"] == 2
    for k in (1, 2, 3):
        sg.give(conn, k)
    sg.auto(conn)
    assert any("maggiore" in s for s in sg.sets_active(conn))
    assert sg.bonus(conn)["atk"] > sg.SET4["atk"]
    hits = sum(bool(sg.maybe_drop(conn, random.Random(i), 1)) for i in range(400))
    assert 50 < hits < 150


# ---------------------------------------------------------------- idle

def test_idle_meditation(conn):
    p = _p(conn)
    r0 = cultivation.get_record(conn, "player", p.id)
    state.set(conn, idle.KEY, str(1_000_000))
    out = idle.on_open(conn, p, at=1_000_000 + 5 * 3600)
    assert out and "5 sessioni" in out[0] and "fermo" in out[0]
    r1 = cultivation.get_record(conn, "player", p.id)
    assert (r1["stage"], r1["progress"]) > (r0["stage"], r0["progress"])
    assert idle.on_open(conn, p, at=1_000_000 + 5 * 3600 + 600) == []          # meno di un'ora
    from engine.systems import autopilot
    autopilot.configure(conn, "assente no")
    state.set(conn, idle.KEY, str(1_000_000))
    assert idle.on_open(conn, p, at=1_000_000 + 9 * 3600) == []


# ---------------------------------------------------------------- sblocchi

def test_unlocks_gradual_and_announce(tmp_path, monkeypatch):
    c = _world(tmp_path, monkeypatch, "mortale", tier=1)
    lk = unlocks.locked(c)
    assert "via:profondi" in lk and "via:sangue" in lk
    assert unlocks.announce(c) == []                                    # il primo giro registra in silenzio
    rid = cultivation.ensure_realm(c, 4)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    out = unlocks.announce(c)
    assert any("Dao profondi" in ln for ln in out)
    assert unlocks.announce(c) == []                                    # una volta sola
    assert "via:profondi" not in unlocks.locked(c)
    unlocks.command(c, "tutte")
    assert unlocks.locked(c) == {}


def test_badged_tab_is_never_locked(tmp_path, monkeypatch):
    c = _world(tmp_path, monkeypatch, "mortale", tier=1)
    assert "via:sangue" not in unlocks.locked(c, {"via:sangue": 1})
