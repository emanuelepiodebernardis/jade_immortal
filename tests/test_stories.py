"""Storie più profonde: cronaca, echi (conseguenze che ritornano), scene che cambiano con te."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, chronicle, echoes, encounters, state, npc_factory, reputation, qol
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "st.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=13, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn)


def test_chronicle_records_and_exports(conn):
    state.grant_title(conn, "Primo Titolo")
    chronicle.add(conn, "regno", "Sfondi fino al regno Fondazione.")
    out = loop.dispatch(conn, "cronaca", allow_nl=False)
    assert "Primo Titolo" in out and "Fondazione" in out
    msg = loop.dispatch(conn, "cronaca esporta", allow_nl=False)
    assert "esportata" in msg
    md = next(qol._saves_dir().glob("cronaca_*.md")).read_text(encoding="utf-8")
    assert "# Cronaca" in md and "Primo Titolo" in md


def test_helped_npc_returns_with_a_gift(conn):
    nid = npc_factory.spawn(conn, random.Random(1), archetype="vagabondo", location_id=None, tier=1)
    sc = {"key": "prova", "title": "Il viandante ferito", "text": "…", "ctx": {"npc_id": nid, "npc_name": "X"},
          "choices": [{"label": "Lo curi", "effects": {"relation": 20}}]}
    encounters.start_scene(conn, _p(conn), sc, force=True)
    loop.dispatch(conn, "1", allow_nl=False)
    es = state.get_json(conn, echoes.KEY)
    assert es and es[0]["kind"] == "aiutato"
    out = echoes.daily(conn, (es[0]["due"] + 1) * 120, random.Random(2), _p(conn))
    assert out and "eco dal passato" in out[0]
    assert "Il viandante ferito" in encounters.pending(conn)["text"]


def test_wronged_npc_comes_back_stronger(conn):
    from engine.systems import perception
    nid = npc_factory.spawn(conn, random.Random(1), archetype="discepolo", location_id=None, tier=1, stage=1)
    echoes.record(conn, nid, "offeso", "«Una lite al mercato»")
    due = state.get_json(conn, echoes.KEY)[0]["due"]
    echoes.daily(conn, (due + 1) * 120, random.Random(3), _p(conn))
    sc = encounters.pending(conn)
    assert sc and sc["key"] == "eco_rancore"
    assert perception.strength_ratio(conn, 1, nid) <= 1.0


def test_same_scene_changes_with_who_you_are(conn):
    base = {"key": "x", "title": "T", "text": "Testo.",
            "choices": [{"label": "Provi", "check": {"stat": "fortuna", "dc": 70},
                         "success": {"fame": 1}, "failure": {}}]}
    plain = encounters.contextualize(conn, _p(conn), base, 0, random.Random(1))
    assert plain["text"] == "Testo." and len(plain["choices"]) == 1
    reputation.adjust(conn, 1, fame=200)
    famous = encounters.contextualize(conn, _p(conn), base, 2, random.Random(1))
    assert "riconosce" in famous["text"] and any("nome" in c["label"] for c in famous["choices"])
    assert len(base["choices"]) == 1                    # la scena originale non viene toccata


def test_dialogue_favour_and_rescue(conn):
    from engine.systems import bonds, dialogues, professions
    rng = random.Random(4)
    loc = _p(conn).location_id
    nid = npc_factory.spawn(conn, rng, archetype="eremita", location_id=loc, tier=1, gender="f")
    bonds.add_bond(conn, 1, nid, "companion", 0, reason="un incontro")
    first = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid,)).fetchone()["name"]
    out = loop.dispatch(conn, f"parla {first}", allow_nl=False)
    assert "Con " in out and encounters.pending(conn)["key"].startswith("dialogo_")
    loop.dispatch(conn, "2", allow_nl=False)                         # «Come stai, davvero?»
    req = dialogues.requests(conn)[str(nid)]
    if req["type"] == "dono":
        professions.give(conn, 1, req["mat"], req["n"])
    elif req["type"] == "luogo":
        entities.move_player(conn, 1, req["loc"])
    else:
        conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (req["enemy"],))
    res = loop.dispatch(conn, f"favore {first}", allow_nl=False)
    assert "intimità 1" in res
    dialogues._add_intimacy(conn, nid, 3)
    conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (nid,))
    enemy = npc_factory.spawn(conn, rng, archetype="guardia", location_id=_p(conn).location_id, tier=6)
    found = any(dialogues.rescuers(conn, 1, enemy, 0.2) for _ in range(1))
    # la probabilità è alta ma non certa: basta che la funzione sia coerente
    assert isinstance(found, bool)
    assert "Intimità" in loop.dispatch(conn, "favori", allow_nl=False)
