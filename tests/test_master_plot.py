"""Trama maestra: fidanzamento e duello, arcinemico, regni, razze, ere e calamità, gare, prigionia, prove del cuore."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, master_plot, archrival, kingdoms, races, eras, contests, captivity,
                            heart_trials, encounters, state, sects, professions, storyline, npc_factory)
from engine.simulation import cultivation
from engine.cli import loop, story_cmds


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "mp.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=9, factions=3, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def _set_tier(conn, tier):
    rid = cultivation.ensure_realm(conn, tier)
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))


def _choose(conn, n):
    return loop.dispatch(conn, str(n), allow_nl=False)


def test_engagement_vow_and_duel(conn):
    assert master_plot.maybe_advance(conn, _p(conn)) is None        # troppo presto
    tick.advance_tick(conn, 120 * 3)
    txt = master_plot.maybe_advance(conn, _p(conn))
    assert "fidanzamento" in txt
    _choose(conn, 2)
    d = master_plot.get(conn)
    assert "giuramento" in d["flags"] and d["duel_day"]
    tick.advance_tick(conn, 120 * (d["duel_day"] + 1))
    encounters.clear(conn)
    d = master_plot.get(conn)
    d["done"] = [k for k in d["done"]] + ["arcinemico"]
    master_plot._save(conn, d)
    txt = master_plot.maybe_advance(conn, _p(conn))
    assert "patto" in txt
    out = _choose(conn, 1)
    assert "Mantenne il Patto" in out or "Torna fra un anno" in out


def test_archrival_memory_and_heir(conn):
    archrival.create(conn, random.Random(1), _p(conn))
    d = archrival.get(conn)
    archrival.on_fight(conn, _p(conn), d["npc"], True, False)
    assert archrival.get(conn)["scars"]
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (d["npc"],))
    assert archrival.daily(conn, 0, random.Random(2), _p(conn)) == []      # l'erede cresce nell'ombra
    out = archrival.daily(conn, 120 * 60, random.Random(2), _p(conn))
    assert any("generazione" in x for x in out) and archrival.get(conn)["gen"] == 2
    assert "Hai ucciso" in " ".join(archrival.get(conn)["memory"])


def test_kingdoms_favor_succession_and_throne(conn):
    _set_tier(conn, 4)
    d = kingdoms.ensure(conn)
    assert d
    rk, k = next(iter(d.items()))
    entities.move_player(conn, 1, k["capital"])
    assert "Suddito" in kingdoms.court(conn, _p(conn))
    out = kingdoms.back(conn, _p(conn), "")
    sects.grant_resource(conn, "pietre_spirituali", 50000, 1)
    out = kingdoms.tribute(conn, _p(conn), "20000")
    assert "Duca" in out or kingdoms.all_k(conn)[rk]["favor"] >= 1500
    lines = kingdoms._succession(conn, random.Random(1), _p(conn), rk, kingdoms.all_k(conn))
    assert any("trono" in x for x in lines)


def test_races_relations_alliance(conn):
    d = races.all_r(conn)
    assert set(d) == set(races.RACES)
    out = races.adjust(conn, "draghi", rel=70, honor=250)
    assert any("ALLEATO" in x for x in out)
    assert "draghi" in races.allies(conn)


def test_eras_and_calamity(conn):
    e = eras.get(conn)
    e["n"] = 3
    e["start"] = -200
    eras._save(conn, e)
    out = eras.daily(conn, 0, random.Random(1), _p(conn))
    assert eras.get(conn)["key"] == "calamita" and any("CALAMITÀ" in x for x in out)
    races.adjust(conn, "giganti", rel=80)
    assert "Giganti" in " ".join(eras.allies(conn, 1))
    txt = eras.fight_wave(conn, _p(conn))
    assert "Giganti" in txt
    w = eras.get(conn)["waves"]
    eras.wave_won(conn)
    assert eras.get(conn)["waves"] == w - 1


def test_contest(conn):
    state.set(conn, "profession", "alchimia")
    state.set(conn, "profession_xp", "5000")
    for d in range(40, 400):
        contests.daily(conn, d * 120, random.Random(d), _p(conn))
        c = contests.current(conn)
        if c and c["art"] == "alchimia":
            break
        state.delete(conn, contests.KEY)
    c = contests.current(conn)
    entities.move_player(conn, 1, c["loc"])
    assert "lista" in contests.register(conn, _p(conn))
    outs = [contests.trial(conn, _p(conn)) for _ in range(3)]
    assert any("Prova" in o or "vinto" in o for o in outs)


def test_captivity_blocks_and_escape(conn):
    captivity.imprison(conn, _p(conn), "il clan nemico")
    assert captivity.active(conn)
    assert "prigioniero" in loop.dispatch(conn, "move north", allow_nl=False)
    for step in (1, 2):
        captivity.set_step(conn, step)
    out = captivity.free(conn, _p(conn))
    assert not captivity.active(conn) and any("LIBERO" in x for x in out)


def test_heart_trial_then_chain(conn):
    sc = heart_trials.scene(random.Random(1), 3, then={"key": "x", "title": "Dopo", "text": "ok",
                                                       "choices": [{"label": "a", "effects": {}}]})
    encounters.start_scene(conn, _p(conn), sc)
    _choose(conn, 1)
    assert encounters.pending(conn)["title"] == "Dopo"


def test_upper_world_beats_are_endless(conn):
    state.set(conn, "world_layer", "4")
    _set_tier(conn, 6 + 3 * 4 + 2)
    keys = [k for k, ok, _f in master_plot._beats(conn, _p(conn))]
    assert "verita_5" in keys and "signore_4" in keys
    assert "Cerchio" in master_plot.order_rank(9)


def test_story_tick_runs_master_plot(conn):
    tick.advance_tick(conn, 120 * 3)
    d = master_plot.get(conn)
    txt = story_cmds.story_tick(conn, _p(conn))
    assert txt


def test_autopilot_stops_for_calamity_and_captivity(conn):
    from engine.systems import autopilot, suggestions
    d = eras.get(conn)
    d.update({"key": "calamita", "waves": 3, "calamity": "la Marea Oscura", "n": 4})
    state.set_json(conn, eras.KEY, d)
    before = autopilot._snapshot(conn, 1)
    before["t0"] = tick.get_tick(conn)
    r = autopilot._stop_reason(conn, _p(conn), before, set(), autopilot.config(conn))
    assert r and "calamità" in r
    assert autopilot._stop_reason(conn, _p(conn), before, set(), autopilot.config(conn)) != r   # una volta sola
    assert any(c == "calamita" for _l, c in suggestions.compute(conn, _p(conn)))
    captivity.imprison(conn, _p(conn), "il Clan Nero")
    assert "Sei prigioniero" in autopilot.run(conn, _p(conn), 3)
    assert suggestions.compute(conn, _p(conn))[0][1] == "evadi"
