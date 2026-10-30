"""Aggiornamento 74: le saghe — riassunto del capitolo precedente, presagi, memoria, libro, nuove saghe."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import (character, encounters, intrigues, intrigue_data6, intrigue_data7, npc_memory, sagas,
                            sects)

STATS = {"corpo", "anima", "qi", "coltivazione", "istinto", "potenza", "fortuna", "karma"}


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "sg.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=9, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 6)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    from engine.systems import calibration
    monkeypatch.setattr(calibration, "PLOT_FIRST_DAY", 0)
    yield c
    c.close()


def test_graph_finds_the_sagas_with_their_endings():
    g = sagas.graph()
    for root in ("spada_spezzata", "maestro_eterno", "filo_rosso", "citta_dorme", "trono_giada", "mercante_destini"):
        assert root in g["sagas"], root
        assert sagas.endings_total(root) >= 3
    assert len(g["sagas"]["filo_rosso"]["chapters"]) == 5
    assert g["saga_of"]["filo_nozze"] == "filo_rosso"


def test_new_templates_well_formed():
    keys = set(intrigues._templates())
    for t in intrigue_data7.TEMPLATES:
        assert t["key"] in keys
        assert not t["key"].startswith(("anello_", "pagoda_", "stendardo_", "calderone_", "perla_", "compagni_"))
        if t.get("req_flag"):
            assert t.get("teaser"), t["key"]                       # ogni seguito si annuncia
            assert next(iter(t["cast"].values())) == "legame:" + t["req_flag"]
        for act in t["acts"]:
            if act.get("auto"):
                assert not act["endings"][-1].get("need_clues") and not act["endings"][-1].get("need_branch")
                continue
            assert [c for c in act["choices"] if not c.get("need_clues") and not c.get("need_branch")], act["title"]
            for c in act["choices"]:
                if c.get("check"):
                    assert c["check"]["stat"] in STATS
        for k in (t.get("memory") or {}).values():
            assert k.rpartition(":")[2] in npc_memory.KINDS, k
    for t in intrigue_data6.TEMPLATES:
        for k in (t.get("memory") or {}).values():
            assert k.rpartition(":")[2] in npc_memory.KINDS, k


@pytest.mark.parametrize("tpl", intrigue_data7.TEMPLATES, ids=lambda t: t["key"])
@pytest.mark.parametrize("pick", [1, 2, 3])
def test_each_new_chapter_plays(conn, monkeypatch, tpl, pick):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (pick != 2, 99, 1))
    p = entities.get_player(conn)
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    out = intrigues.start(conn, p, tpl["key"], random.Random(pick),
                          branches=["salvata", "sognato", "usurpatore", "erba", "generoso", "cuore"])
    assert out and "{" not in out, out
    for _ in range(14):
        sc = encounters.pending(conn)
        if not sc:
            d = intrigues.get(conn)
            act = next((x for x in d["active"] if x["key"] == tpl["key"]), None)
            if not act or act.get("pending_end"):
                break
            r = intrigues.play(conn, entities.get_player(conn), act)
            assert r is None or "{" not in r, r
            if not encounters.pending(conn) and not any(x["key"] == tpl["key"] for x in intrigues.get(conn)["active"]):
                break
            continue
        assert "{" not in sc["text"] and "}" not in sc["text"], sc["text"]
        n = min(pick, len(sc["choices"]))
        txt, _cmd = encounters.choose(conn, entities.get_player(conn), n)
        assert "{" not in txt, txt


def _play(conn, key, picks, ok=True, monkeypatch=None):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (ok, 99, 1))
    intrigues.start(conn, entities.get_player(conn), key, random.Random(1))
    texts = []
    for n in picks:
        if not encounters.pending(conn):
            act = next((x for x in intrigues.get(conn)["active"] if x["key"] == key), None)
            if not act:
                break
            intrigues.play(conn, entities.get_player(conn), act)
        sc = encounters.pending(conn)
        if not sc:
            break
        texts.append(sc["text"])
        labels = [c["label"] for c in sc["choices"]]
        idx = next(i for i, lab in enumerate(labels, 1) if n in lab) if isinstance(n, str) else n
        txt, _ = encounters.choose(conn, entities.get_player(conn), idx)
        texts.append(txt)
    return texts


def test_saga_recap_teaser_memory_and_book(conn, monkeypatch):
    p = entities.get_player(conn)
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    _play(conn, "filo_rosso", [1, 1, "Leghi"], monkeypatch=monkeypatch)
    d = intrigues.get(conn)
    assert "filo_fuga" in d["flags"]
    amata = d["links"]["filo_fuga"][0]
    # la memoria: lei ti ricorda come chi ama
    assert npc_memory.last(conn, amata)[1] == "amato"
    # il libro: una saga in corso, un capitolo scritto, il prossimo in attesa
    b = sagas.book(conn)
    row = next(r for r in b if r["saga"] == "filo_rosso")
    assert len(row["capitoli"]) == 1 and "prossimo capitolo" in row["stato"] and row["finali"] == 0
    # il presagio: a metà dell'attesa, una volta sola, col nome giusto
    d["flag_days"]["filo_fuga"] -= 10
    intrigues._save(conn, d)
    out = sagas.daily(conn, 0, None, p)
    nome = conn.execute("SELECT name FROM npcs WHERE id=?", (amata,)).fetchone()["name"]
    assert out and nome in out[0] and "{" not in out[0]
    assert sagas.daily(conn, 0, None, p) == []
    # il capitolo dopo si apre con «Nel capitolo precedente…»
    texts = _play(conn, "filo_inseguiti", [], monkeypatch=monkeypatch)
    sc = encounters.pending(conn)
    assert sc and "Nel capitolo precedente" in sc["text"] and "{" not in sc["text"]
    it = next(x for x in intrigues.get(conn)["active"] if x["key"] == "filo_inseguiti")
    assert it["cast"]["amata"] == amata
    labels = [c["label"] for c in sc["choices"]]
    encounters.choose(conn, entities.get_player(conn), next(i for i, lab in enumerate(labels, 1) if "finestra" in lab))
    act = next(x for x in intrigues.get(conn)["active"] if x["key"] == "filo_inseguiti")
    intrigues.play(conn, entities.get_player(conn), act)
    sc = encounters.pending(conn)
    labels = [c["label"] for c in sc["choices"]]
    txt, _ = encounters.choose(conn, entities.get_player(conn), next(i for i, lab in enumerate(labels, 1) if "Restiamo" in lab))
    assert "Finale scoperto" in txt
    row = next(r for r in sagas.book(conn) if r["saga"] == "filo_rosso")
    assert row["finali"] == 1 and row["stato"] == "conclusa" and len(row["capitoli"]) == 2
    assert "LE TUE SAGHE" in sagas.describe(conn)


def test_female_cast_and_saga_greetings(conn, monkeypatch):
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)
    intrigues.start(conn, entities.get_player(conn), "filo_rosso", random.Random(2))
    it = next(x for x in intrigues.get(conn)["active"] if x["key"] == "filo_rosso")
    g = conn.execute("SELECT gender FROM npcs WHERE id=?", (it["cast"]["amata"],)).fetchone()["gender"]
    assert g == "f"
    sc = npc_memory._saga_scene(entities.get_npc(conn, it["cast"]["amata"]), "amato", 3)
    assert sc and sc["choices"]
