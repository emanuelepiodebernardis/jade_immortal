"""Aggiornamento 73: le saghe lunghe a capitoli — ogni capitolo si gioca, e i capitoli si legano tra loro."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import character, encounters, intrigues, intrigue_data5, intrigue_data6, sects

STATS = {"corpo", "anima", "qi", "coltivazione", "istinto", "potenza", "fortuna", "karma"}


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "i6.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 6)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    yield c
    c.close()


def _choices(tpl):
    for act in tpl["acts"]:
        for ch in act.get("choices", []):
            yield act, ch


def test_registered_and_well_formed():
    keys = set(intrigues._templates())
    mine = {t["key"] for t in intrigue_data6.TEMPLATES}
    assert mine <= keys
    flags_set = set()
    for t in intrigue_data5.TEMPLATES + intrigue_data6.TEMPLATES:
        for act, ch in _choices(t):
            for part in (ch.get("effects", {}), ch.get("success", {}), ch.get("failure", {})):
                if part.get("intrigue", {}).get("flag"):
                    flags_set.add(part["intrigue"]["flag"])
        for act in t["acts"]:
            for e in act.get("endings", []):
                if e.get("flag"):
                    flags_set.add(e["flag"])
    for t in intrigue_data6.TEMPLATES:
        assert not t["key"].startswith(("anello_", "pagoda_", "stendardo_", "calderone_", "perla_", "compagni_"))
        if t.get("req_flag"):
            assert t["req_flag"] in flags_set, t["key"]           # ogni capitolo ha qualcuno che lo accende
            first = next(iter(t["cast"].values()))
            assert first == "legame:" + t["req_flag"]             # e ritrova lo stesso personaggio
        for act in t["acts"]:
            if act.get("auto"):
                assert act["endings"][-1].keys() & {"outcome"} and not act["endings"][-1].get("need_clues")
                continue
            free = [c for c in act["choices"] if not c.get("need_clues") and not c.get("need_branch")]
            assert free, (t["key"], act["title"])                 # c'è sempre almeno una strada aperta
        for act, ch in _choices(t):
            if ch.get("check"):
                assert ch["check"]["stat"] in STATS
    # ogni saga ha almeno tre finali diversi
    assert len({t["key"] for t in intrigue_data6.TEMPLATES if t["key"].startswith("spada_")}) >= 7
    assert len({t["key"] for t in intrigue_data6.TEMPLATES if t["key"].startswith("maestro_")}) >= 5


@pytest.mark.parametrize("tpl", intrigue_data6.TEMPLATES, ids=lambda t: t["key"])
@pytest.mark.parametrize("pick", [1, 2, 3])
def test_each_chapter_plays(conn, monkeypatch, tpl, pick):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (pick != 2, 99, 1))
    p = entities.get_player(conn)
    sects.grant_resource(conn, "pietre_spirituali", 100000, p.id)
    out = intrigues.start(conn, p, tpl["key"], random.Random(pick), branches=["ascoltato", "erede", "calmo", "lezioni"])
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
            if not encounters.pending(conn):
                d = intrigues.get(conn)
                if not any(x["key"] == tpl["key"] for x in d["active"]):
                    break
            continue
        n = min(pick, len(sc["choices"]))
        txt, _cmd = encounters.choose(conn, entities.get_player(conn), n)
        assert "{" not in txt, txt


def _play_through(conn, key, picks, monkeypatch, ok=True):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (ok, 99, 1))
    p = entities.get_player(conn)
    intrigues.start(conn, p, key, random.Random(1))
    for n in picks:
        if not encounters.pending(conn):
            d = intrigues.get(conn)
            act = next((x for x in d["active"] if x["key"] == key), None)
            if not act:
                break
            intrigues.play(conn, entities.get_player(conn), act)
        sc = encounters.pending(conn)
        if not sc:
            break
        labels = [c["label"] for c in sc["choices"]]
        idx = next(i for i, lab in enumerate(labels, 1) if n in lab) if isinstance(n, str) else n
        encounters.choose(conn, entities.get_player(conn), idx)


def test_sworn_brother_returns_in_the_next_chapters(conn, monkeypatch):
    from engine.systems import calibration
    monkeypatch.setattr(calibration, "PLOT_FIRST_DAY", 0)
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)
    _play_through(conn, "spada_spezzata", [1, 1, "strappi"], monkeypatch)
    d = intrigues.get(conn)
    assert "spada_fratelli" in d["flags"]
    bro = d["links"]["spada_fratelli"][0]
    first = next(x for x in d["done"] if x["key"] == "spada_spezzata")
    assert first["outcome"] == "giurati"
    # il capitolo dopo arriva solo quando è passato il tempo, e con lo stesso fratello
    p = entities.get_player(conn)
    keys = [x[2].get("key") for x in intrigues.candidates(conn, p, random.Random(1)) if x[1] == "nuova"]
    assert "spada_fratello_accusato" not in keys
    d["flag_days"]["spada_fratelli"] -= 30
    d["last_start"] = -999
    d["done"] = []
    intrigues._save(conn, d)
    keys = [x[2].get("key") for x in intrigues.candidates(conn, p, random.Random(1)) if x[1] == "nuova"]
    assert "spada_fratello_accusato" in keys
    _play_through(conn, "spada_fratello_accusato", [2, "colpa"], monkeypatch)
    d = intrigues.get(conn)
    it = next(x for x in d["done"] if x["key"] == "spada_fratello_accusato")
    assert it["outcome"] == "colpa"
    assert d["links"]["spada_vincolo"][0] == bro
    # il finale: se il colpo fallisce, il fratello muore per te (senza faide: non l'hai ucciso tu)
    d["flag_days"]["spada_vincolo"] -= 40
    intrigues._save(conn, d)
    _play_through(conn, "spada_ricomposta", [2, 1], monkeypatch, ok=False)
    st = conn.execute("SELECT status FROM npcs WHERE id=?;", (bro,)).fetchone()["status"]
    assert st == "dead"
    assert intrigues.get(conn)["done"][-1]["outcome"] == "caduto"


def test_mercante_partner_leads_to_the_bill(conn, monkeypatch):
    sects.grant_resource(conn, "pietre_spirituali", 100000, 1)
    _play_through(conn, "mercante_destini", [3, 2, "affare"], monkeypatch)
    d = intrigues.get(conn)
    assert "mercante_socio" in d["flags"]
    merc = d["links"]["mercante_socio"][0]
    intrigues.start(conn, entities.get_player(conn), "mercante_conto", random.Random(2))
    it = next(x for x in intrigues.get(conn)["active"] if x["key"] == "mercante_conto")
    assert it["cast"]["mandante"] == merc
