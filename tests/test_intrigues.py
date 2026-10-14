"""Il regista delle trame: cast dal mondo, atti, indizi, rami, finali che cambiano con ciò che sai."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, intrigues, intrigue_data, encounters, state, menus


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "i.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=5, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = c.execute("SELECT id FROM cultivation_realms WHERE tier=5;").fetchone()["id"]
    c.execute("UPDATE players SET realm_id=?;", (rid,))
    c.commit()
    yield c
    c.close()


def _p(c):
    return entities.get_player(c)


class Good(random.Random):
    def random(self):
        return 0.0


def _pick(conn, label_part):
    sc = encounters.pending(conn)
    i = next(i for i, ch in enumerate(sc["choices"], 1) if label_part in ch["label"])
    return encounters.choose(conn, _p(conn), i)


def test_templates_are_well_formed():
    keys = set()
    for t in intrigue_data.TEMPLATES:
        assert t["key"] not in keys
        keys.add(t["key"])
        assert t["acts"] and t["cast"]
        for a in t["acts"]:
            assert a["choices"]
            assert a.get("focus") is None or a["focus"] in t["cast"]
            for ch in a["choices"]:
                effs = [ch.get(k) for k in ("effects", "success", "failure") if ch.get(k)]
                assert effs and all("intrigue" in e for e in effs), (t["key"], ch["label"])


def test_hidden_hand_full_story_with_clues(conn, monkeypatch):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))   # ogni prova riesce
    txt = intrigues.start(conn, _p(conn), "mano_ombra", random.Random(1))
    assert "atto 1/3" in txt and "cadavere" in txt.lower()
    _pick(conn, "Esamini il corpo")
    it = intrigues.get(conn)["active"][0]
    assert it["clues"] == 1 and it["act"] == 1
    it["next_day"] = 0                                   # l'atto è maturo: il regista lo sceglie
    d = intrigues.get(conn); d["active"][0] = it; intrigues._save(conn, d)
    out = intrigues.daily(conn, tick.get_tick(conn), random.Random(2), _p(conn))
    assert any("terra rossa" in x for x in out)
    _pick(conn, "informatore")
    d = intrigues.get(conn); d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
    out = intrigues.daily(conn, tick.get_tick(conn), random.Random(3), _p(conn))
    labels = [ch["label"] for ch in encounters.pending(conn)["choices"]]
    assert any("Smascheri" in x for x in labels)          # due indizi: puoi smascherarlo
    res, _cmd = _pick(conn, "Smascheri")
    assert "Hai smascherato" in res
    assert not intrigues.get(conn)["active"] and intrigues.get(conn)["done"][-1]["outcome"] == "smascherato"


def test_without_clues_the_reveal_is_hidden_and_branch_choices_gate(conn, monkeypatch):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (False, 1, 99))
    intrigues.start(conn, _p(conn), "torneo_truccato", random.Random(4))
    _pick(conn, "Accetti il denaro")
    it = intrigues.get(conn)["active"][0]
    assert "venduto" in it["branches"]
    d = intrigues.get(conn); d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
    intrigues.play(conn, _p(conn), intrigues.get(conn)["active"][0])
    _pick(conn, "mostri il veleno")                       # fallita: nessun indizio
    d = intrigues.get(conn); intrigues.play(conn, _p(conn), d["active"][0])
    labels = [ch["label"] for ch in encounters.pending(conn)["choices"]]
    assert any("Perdi apposta" in x for x in labels)      # il ramo «venduto» apre la scelta
    res, _ = _pick(conn, "Perdi apposta")
    assert "venduto" in intrigues.get(conn)["done"][-1]["outcome"]


def test_director_scores_due_acts_above_new_plots(conn):
    p = _p(conn)
    intrigues.start(conn, p, "maledizione", random.Random(5))
    encounters.clear(conn)
    d = intrigues.get(conn)
    d["active"][0]["next_day"] = 0
    d["last_start"] = -999
    intrigues._save(conn, d)
    c = intrigues.candidates(conn, p, random.Random(1))
    assert c[0][1] == "atto"
    assert any(k == "nuova" for _s, k, _d in c)


def test_forgotten_plots_close_and_menu_shows_them(conn):
    p = _p(conn)
    intrigues.start(conn, p, "isola_spada", random.Random(6))
    encounters.clear(conn)
    assert "Trame e intrighi" in [s["title"] for s in menus.build(conn, p, "eventi")["sections"]]
    d = intrigues.get(conn)
    d["active"][0]["next_day"] = -100
    intrigues._save(conn, d)
    out = intrigues.daily(conn, tick.get_tick(conn), random.Random(1), p)
    assert any("chiusa senza di te" in x for x in out)
    assert intrigues.get(conn)["done"][-1]["outcome"] == "sfumata"
