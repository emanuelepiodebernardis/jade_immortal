"""Pilota automatico: configurazione, giorni che scorrono, scelte per condotta, interruzioni."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, autopilot, state, encounters, secret_realms, professions
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=6, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def test_configure(conn):
    assert "PILOTA" in autopilot.command(conn, _p(conn), "")
    autopilot.command(conn, _p(conn), "imposta bersagli tutti")
    autopilot.command(conn, _p(conn), "imposta condotta spietata")
    autopilot.command(conn, _p(conn), "imposta attivita coltiva=5 caccia=0")
    autopilot.command(conn, _p(conn), "imposta assorbi si")
    c = autopilot.config(conn)
    assert c["bersagli"] == "tutti" and c["condotta"] == "spietata"
    assert c["attivita"]["coltiva"] == 5 and c["attivita"]["caccia"] == 0 and c["assorbi"]
    assert "Non ho capito" in autopilot.command(conn, _p(conn), "imposta boh")


def test_run_days_advances_and_reports(conn):
    autopilot.command(conn, _p(conn), "imposta attivita coltiva=5 dao=2 caccia=0 raccolta=0 lavoro=0 insegna=0")
    d0 = tick.get_tick(conn) // 120
    out = autopilot.run(conn, _p(conn), 3)
    assert "STATO ETEREO" in out
    if "si ferma" not in out:
        assert tick.get_tick(conn) // 120 >= d0 + 3


def test_conduct_choice():
    sc = {"choices": [
        {"label": "aiuta", "effects": {"karma": 30, "fame": 5}},
        {"label": "deruba", "effects": {"karma": -40, "infamy": 5, "stones": 200}},
        {"label": "combatti", "effects": {}, "command": "attack x"}]}
    assert autopilot.pick_choice(sc, "virtuosa") == 1
    assert autopilot.pick_choice(sc, "spietata") in (2, 3)
    assert autopilot.pick_choice(sc, "opportunista") == 2


def test_stops_for_secret_realm(conn):
    autopilot.command(conn, _p(conn), "imposta attivita coltiva=5 dao=0 caccia=0 raccolta=0 lavoro=0 insegna=0")
    state.set(conn, "secret_realm_day", "-100")
    tick.advance_tick(conn, 120 * 4)
    out = autopilot.run(conn, _p(conn), 20)
    assert "reame segreto" in out or "si ferma" in out


def test_stops_on_important_scene(conn):
    sc = {"key": "nemesi", "title": "La nemesi", "text": "x", "choices": [{"label": "a", "effects": {}}]}
    encounters.start_scene(conn, _p(conn), sc)
    assert "risolvila" in autopilot.run(conn, _p(conn), 5)


def test_random_encounter_resolved_automatically(conn):
    encounters.maybe_trigger(conn, _p(conn), force_key="vecchio_morente")
    assert encounters.pending(conn)
    autopilot.command(conn, _p(conn), "imposta condotta virtuosa")
    # una scena casuale aperta all'avvio blocca; il pilota le risolve solo mentre gira
    assert "risolvila" in autopilot.run(conn, _p(conn), 1)
    encounters.clear(conn)
    out = autopilot.run(conn, _p(conn), 2)
    assert "STATO ETEREO" in out
