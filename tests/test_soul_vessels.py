"""Aggiornamento 61: i vasi d'anima — l'anello in quattro capitoli, pagoda, stendardo, calderone, perla."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, intrigues, intrigue_data3, encounters, state, mentor_ring, soul_arcs,
                            soul_artifacts, sects, professions)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "v.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = c.execute("SELECT id FROM cultivation_realms WHERE tier=4;").fetchone()["id"]
    c.execute("UPDATE players SET realm_id=?;", (rid,))
    c.execute("UPDATE worlds SET current_tick=current_tick+1200;")
    c.commit()
    yield c
    c.close()


def _p(c):
    return entities.get_player(c)


def _ring(conn, lv):
    mentor_ring.awaken(conn, random.Random(1))
    d = mentor_ring.get(conn)
    d["level"] = lv
    mentor_ring._save(conn, d)


def test_arc_templates_well_formed():
    keys = {t["key"] for t in intrigue_data3.ARCS}
    for vessel, arc in soul_arcs.ARCS.items():
        for ch in arc:
            assert ch["plot"] in keys, ch["plot"]
    for t in intrigue_data3.ARCS:
        assert t.get("arc") in soul_arcs.ARCS
        for a in t["acts"]:
            if a.get("auto"):
                assert a.get("endings")
                continue
            for ch in a["choices"]:
                effs = [ch.get(k) for k in ("effects", "success", "failure") if ch.get(k)]
                assert effs and all("intrigue" in e for e in effs), (t["key"], ch["label"])
                if ch.get("check"):
                    assert not ch.get("command"), (t["key"], ch["label"])     # il duello solo se la prova fallisce


def test_director_never_picks_arc_chapters(conn):
    d = intrigues.get(conn); d["last_start"] = -999; intrigues._save(conn, d)
    keys = [x[2].get("key") for x in intrigues.candidates(conn, _p(conn), random.Random(1)) if x[1] == "nuova"]
    assert not any(k.startswith(("anello_", "pagoda_", "stendardo_", "calderone_", "perla_")) for k in keys)


@pytest.mark.parametrize("pick", [1, 2, 3])
def test_every_arc_chapter_can_be_played(conn, monkeypatch, pick):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (pick != 2, 99, 1))
    p = _p(conn)
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    _ring(conn, 10)
    for k in soul_artifacts.ORDER:
        soul_artifacts.acquire(conn, p, k, random.Random(2))
    for tpl in intrigue_data3.ARCS:
        encounters.clear(conn)
        d = intrigues.get(conn); d["active"] = []; intrigues._save(conn, d)
        txt = intrigues.start(conn, p, tpl["key"], random.Random(1))
        assert txt and "{" not in txt, (tpl["key"], txt)
        for _step in range(14):
            d = intrigues.get(conn)
            if not d["active"]:
                break
            it = d["active"][0]
            if encounters.pending(conn):
                sc = encounters.pending(conn)
                n = min(pick, len(sc["choices"]))
                _res, cmd = encounters.choose(conn, p, n)
                if cmd and cmd.startswith("duello"):
                    act = intrigues.get(conn)["active"]
                    if act:
                        intrigues.on_duel(conn, p, act[0].get("duel_npc") or 0, "ucciso")
                continue
            it["next_day"] = 0
            intrigues._save(conn, d)
            intrigues.play(conn, p, it)
        assert not intrigues.get(conn)["active"], f"{tpl['key']} non si chiude"


def test_ring_chapter_one_starts_and_gives_the_wood(conn):
    p = _p(conn)
    _ring(conn, 3)
    sects.grant_resource(conn, "pietre_spirituali", 5000, p.id)
    out = soul_arcs.daily(conn, tick.get_tick(conn), random.Random(1), p)
    assert any("Legno Nutrianime" in x for x in out)
    assert "{maestro}" not in "\n".join(out)
    sc = encounters.pending(conn)
    n = next(i for i, c in enumerate(sc["choices"], 1) if "compri" in c["label"])
    encounters.choose(conn, p, n)
    d = mentor_ring.get(conn)
    assert d["wood"] and d["level"] == 4
    assert soul_arcs.chapter(conn, "anello")[0] == 1
    professions.give(conn, p.id, "nuclei", 3)
    out = mentor_ring.feed(conn, p, "3")
    assert "raddoppia" in out


def test_ring_kidnapped_then_rescued(conn):
    p = _p(conn)
    _ring(conn, 8)
    d = soul_arcs.get(conn); d["anello"] = {"ch": 2, "running": None, "since": 0, "retry_day": 0}; soul_arcs._save(conn, d)
    soul_arcs.daily(conn, tick.get_tick(conn), random.Random(1), p)
    assert mentor_ring.get(conn)["captive"] and mentor_ring.cultivation_mult(conn)[0] == 1.0
    soul_arcs.on_finish(conn, "anello", "anello_palazzo", "assalto_perso")
    assert mentor_ring.get(conn)["captive"]                       # ancora prigioniero: si ritenta
    soul_arcs.on_finish(conn, "anello", "anello_palazzo", "riscatto")
    r = mentor_ring.get(conn)
    assert not r["captive"] and r["level"] == 10 and mentor_ring.active(conn)


def test_ring_rebirth_then_a_new_soul(conn):
    p = _p(conn)
    _ring(conn, 10)
    lines = mentor_ring.on_chapter(conn, p, "anello_corpo", "rinato", True)
    r = mentor_ring.get(conn)
    assert r["gone"] == "rinato" and r["reborn_npc"]
    assert conn.execute("SELECT 1 FROM bonds WHERE npc_id=? AND kind='master';", (r["reborn_npc"],)).fetchone()
    assert any("corpo suo" in x for x in lines)
    assert "Nessuna anima" in mentor_ring.host(conn, p)
    nid = conn.execute("SELECT id FROM npcs WHERE status='alive' AND (kind IS NULL OR kind='human') "
                       "AND archetype='anziano' LIMIT 1;").fetchone()
    nid = nid["id"] if nid else conn.execute("SELECT id FROM npcs LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE npcs SET archetype='anziano' WHERE id=?;", (nid,))
    assert mentor_ring.on_kill(conn, tick.get_tick(conn), random.Random(1), p, nid)
    out = mentor_ring.host(conn, p)
    assert "entra nell'anello" in out
    r = mentor_ring.get(conn)
    assert r["level"] == 1 and r["gen"] == 2 and soul_arcs.chapter(conn, "anello")[0] == 0


def test_artifacts_grow_and_fight(conn):
    p = _p(conn)
    for k in soul_artifacts.ORDER:
        assert soul_artifacts.acquire(conn, p, k, random.Random(4))
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    assert "livello 2" in soul_artifacts.feed(conn, p, "pagoda", "")
    nid = conn.execute("SELECT id FROM npcs WHERE (kind IS NULL OR kind='human') LIMIT 1;").fetchone()["id"]
    for _ in range(3):
        soul_artifacts.on_kill(conn, tick.get_tick(conn), random.Random(1), p, nid)
    assert soul_artifacts.get(conn, "stendardo")["souls"] >= 3 and soul_artifacts.level(conn, "stendardo") >= 2
    out = soul_artifacts.pact(conn, p, "forza")
    assert "sigillo" in out and soul_artifacts.get(conn, "perla")["atk"] > 0
    assert "Così presto" in soul_artifacts.pact(conn, p, "vita")

    class _S:
        def __init__(self):
            self.atk_mult = 1.0
            self.prof = {}

    class _F:
        p, e = _S(), _S()
    fx = _F()
    soul_artifacts.combat(conn, fx)
    assert fx.p.atk_mult > 1.0 and fx.e.atk_mult < 1.0
    assert soul_artifacts.cultivation_mult(conn)[0] > 1.0


def test_artifact_chapters_change_the_vessel(conn):
    p = _p(conn)
    for k in soul_artifacts.ORDER:
        soul_artifacts.acquire(conn, p, k, random.Random(4))
    soul_arcs.on_finish(conn, "stendardo", "stendardo_rivolta", "liberate")
    assert "stendardo" not in soul_artifacts.owned(conn)
    soul_arcs.on_finish(conn, "pagoda", "pagoda_nome", "legata")
    assert "legata" in soul_artifacts.get(conn, "pagoda")["flags"]
    soul_arcs.on_finish(conn, "perla", "perla_prezzo", "sutra")
    assert "sutra" in soul_artifacts.adapter("perla").branches(conn, "perla_possessione")


def test_vessels_menu_and_commands(conn):
    from engine.cli import loop
    from engine.systems import menus
    p = _p(conn)
    assert "Non porti" in loop.dispatch(conn, "vasi", allow_nl=False)
    soul_artifacts.acquire(conn, p, "calderone", random.Random(1))
    m = menus.build(conn, p, "via:anime")
    assert any("Calderone" in s["title"] for s in m["sections"])
    assert "erbe" in loop.dispatch(conn, "calderone nutri", allow_nl=False).lower()
