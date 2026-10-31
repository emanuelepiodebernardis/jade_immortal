"""Aggiornamento 79: obiettivi guidati, ricerca, albero dei Dao, rivali con le nuove regole, bottega,
Prove del Cielo, imparare guardando e perdendo, «dove eravamo»."""
from __future__ import annotations

import collections
import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators import dao_gen
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, dao_heart, dao_insight, dao_laws, dao_tree, goals, heaven_trials, npc_crafts,
                            professions, recap, rival_laws, search, sects, state, workshop)


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a79.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=7, factions=3, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(5))
    dao_gen.seed_daos(c)
    c.commit()
    yield c
    c.close()


def _p(conn):
    return entities.get_player(conn, 1)


def _set(conn, key, comp, ctype="player", cid=1):
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES (?, ?, ?, 50, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "comprehension=excluded.comprehension, practiced=1;", (ctype, cid, key, comp))


def _stones(conn, n):
    sects.grant_resource(conn, "pietre_spirituali", n - sects.get_resource(conn, "pietre_spirituali", 1), 1)


def _npc_here(conn, archetype="anziano"):
    p = _p(conn)
    for r in conn.execute("SELECT id FROM npcs WHERE status='alive' AND (kind='human' OR kind IS NULL);"):
        conn.execute("UPDATE npcs SET archetype=?, location_id=? WHERE id=?;", (archetype, p.location_id, r["id"]))
        if npc_crafts.of_npc(conn, r["id"]):
            return entities.get_npc(conn, r["id"])
    raise AssertionError


# ---------------------------------------------------------------- obiettivi

def test_goal_plan_for_a_fusion_progresses(conn):
    p = _p(conn)
    out = goals.command(conn, p, "vapore")
    assert "OBIETTIVO" in out and "Vapore" in out
    pl = goals.plan(conn)
    assert not pl["complete"] and pl["total"] >= 4
    _set(conn, "acqua", 30)
    _set(conn, "fuoco", 30)
    _stones(conn, 10_000)
    dao_heart.adjust(conn, 60 - dao_heart.heart(conn), "t")
    assert goals.next_cmd(conn) == "fusione vapore"
    dao_laws.fuse(conn, p, ["vapore"])
    assert goals.plan(conn)["complete"]
    assert "raggiunto" in goals.describe(conn)
    assert goals.command(conn, p, "via") == "🎯 Obiettivo tolto." and goals.plan(conn) is None


def test_goal_for_a_high_dao_goes_through_the_fusion(conn):
    goals.command(conn, _p(conn), "yinyang")
    texts = [s["text"] for s in goals.plan(conn)["steps"]]
    assert any("Vapore a 1000" in t for t in texts)


def test_goal_dao_level_and_art(conn):
    p = _p(conn)
    _set(conn, "spada", 40)
    goals.command(conn, p, "spada 100")
    assert goals.next_cmd(conn) == "comprehend spada"
    goals.command(conn, p, "alchimia 3")
    assert goals.next_cmd(conn) == "arti alchimia"
    assert "Non riconosco" in goals.command(conn, p, "pippo")


def test_autopilot_follows_the_goal(conn):
    from engine.systems import autopilot
    p = _p(conn)
    _set(conn, "spada", 40)
    goals.command(conn, p, "spada 500")
    cfg = autopilot.config(conn)
    picks = collections.Counter(autopilot._choose_action_raw(conn, p, cfg, random.Random(i)) for i in range(40))
    assert picks["comprehend spada"] >= 15


# ---------------------------------------------------------------- ricerca e comandi

def test_search_and_did_you_mean(conn):
    res = search.search(conn, "veleno")
    assert res and res[0]["titolo"] == "Dao del Veleno"
    assert search.did_you_mean("fusinoe") == "fusione"
    assert any(c["cmd"] == "obiettivo" for c in search.commands())
    a = search.argomenti(conn)
    assert any(x["v"] == "tempesta" for x in a["fusione"])


def test_unknown_command_suggests(conn):
    from engine.cli import loop
    out = loop.dispatch(conn, "fusinoe", allow_nl=False)
    assert "Forse intendevi 'fusione'" in out


# ---------------------------------------------------------------- albero dei Dao

def test_dao_tree_is_a_dag_with_states(conn):
    _set(conn, "acqua", 30)
    _set(conn, "fuoco", 30)
    g = dao_tree.graph(conn)
    keys = {n["key"] for n in g["nodes"]}
    assert all(e["from"] in keys and e["to"] in keys for e in g["edges"])
    adj = collections.defaultdict(list)
    for e in g["edges"]:
        adj[e["from"]].append(e["to"])
    color = {}

    def dfs(u):
        color[u] = 1
        for v in adj[u]:
            assert color.get(v) != 1, f"ciclo su {u}->{v}"
            if not color.get(v):
                dfs(v)
        color[u] = 2
    for k in keys:
        if not color.get(k):
            dfs(k)
    st = {n["key"]: n["state"] for n in g["nodes"]}
    assert st["acqua"] == "have" and st["vapore"] == "ready"


# ---------------------------------------------------------------- rivali

def test_rivals_fuse_and_challenge(conn):
    from engine.systems import prodigies
    nid = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    _set(conn, "fulmine", 200, "npc", nid)
    _set(conn, "vento", 200, "npc", nid)
    rng = random.Random(1)
    voices = [v for v in (rival_laws.grow(conn, nid, rng) for _ in range(400)) if v]
    assert any("Tempesta" in v for v in voices)
    assert "fusioni" in rival_laws.dao_line(conn, nid)
    state.set_json(conn, prodigies.KEY, [nid])
    p = _p(conn)
    from engine.core import tick
    t0 = tick.get_tick(conn)
    state.set_json(conn, "rival_above_since", {str(nid): t0 // 120 - 20})
    out = []
    for i in range(80):
        out += rival_laws._challenge(conn, t0, random.Random(i), p, {nid})
        if out:
            break
    assert out and "sfida" in out[0].lower()


# ---------------------------------------------------------------- bottega

def test_apprentice_learns_then_grows_to_the_master(conn):
    p = _p(conn)
    npc = _npc_here(conn, "patriarca")
    key, lv = npc_crafts.of_npc(conn, npc.id)[0]
    _stones(conn, 100_000)
    first = npc.name.split()[0]
    assert "basi" in workshop.apprentice(conn, p, first)
    assert professions.has(conn, key)
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (p.location_id, npc.id))   # (i maestri si spostano)
    assert "già lavorato" in workshop.apprentice(conn, p, first)
    state.set_json(conn, "bottega_giorni", {})
    assert "Esperienza +" in workshop.apprentice(conn, p, first)


def test_commission_and_lab(conn):
    p = _p(conn)
    npc = _npc_here(conn, "anziano")
    _stones(conn, 100_000)
    first = npc.name.split()[0]
    assert "Può farti" in workshop.commission(conn, p, first)
    out = workshop.commission(conn, p, f"{first} 1")
    assert "nello zaino" in out or "non forgia" in out
    city = conn.execute("SELECT id FROM locations WHERE location_type='city' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (city,))
    p = _p(conn)
    professions.add_xp(conn, 1, 40, "alchimia")
    assert "Apri il tuo laboratorio" in workshop.lab_command(conn, p, "apri")
    workshop.daily(conn, 0, None, p)
    assert "Incassi" in workshop.lab_command(conn, p, "riscuoti")


# ---------------------------------------------------------------- prove, guardare, perdere

def test_heaven_trial_win_and_cooldown(conn):
    p = _p(conn)
    out = heaven_trials.start(conn, p, "3")
    assert "PROVA D'ORO" in out
    nid = heaven_trials._get(conn)["fighter"]
    from engine.systems import duel
    state.delete(conn, duel.KEY)
    res = heaven_trials.on_duel(conn, p, nid, "risparmiato")
    assert any("Superi" in x for x in res) and "Prescelto del Cielo" in state.titles(conn)
    assert "non ti riceve" in heaven_trials.start(conn, p, "3")


def test_defeat_and_watching_teach(conn):
    p = _p(conn)
    npc = _npc_here(conn)
    conn.execute("DELETE FROM character_daos WHERE character_type='npc' AND character_id=?;", (npc.id,))
    _set(conn, "fulmine", 300, "npc", npc.id)
    out = dao_insight.after_defeat(conn, npc.id)
    assert out and "sconfitta" in out[0]
    w = dao_insight.watch(conn, p)
    assert "guardare" in w or "allena" in w
    assert "già passato" in dao_insight.watch(conn, p)


# ---------------------------------------------------------------- dove eravamo

def test_recap(conn):
    import time
    p = _p(conn)
    recap.mark_session(conn)
    goals.command(conn, p, "vapore")
    state.set(conn, "idle_seen", str(int(time.time()) - 10 * 3600))
    out = recap.on_open(conn, p)
    assert out and "DOVE ERAVAMO" in out[0] and any("Obiettivo" in x for x in out)
    state.set(conn, "idle_seen", str(int(time.time())))
    assert recap.on_open(conn, p) == []


def test_new_commands_dispatch(conn):
    from engine.cli import story_cmds, voice
    p = _p(conn)
    for c in ("obiettivo", "cerca", "riassunto", "albero", "prova_cielo", "laboratorio", "assisti"):
        assert story_cmds.handle(conn, p, c, "") is not None, c
    assert voice.interpret("voglio arrivare alla tempesta", {}, "")["cmd"] == "obiettivo tempesta"
    assert voice.interpret("prova d'oro", {}, "")["cmd"] == "prova_cielo 3"
