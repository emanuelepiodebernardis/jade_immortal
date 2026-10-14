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
            if a.get("auto"):                         # atto che si conclude da solo
                assert a.get("endings") or a.get("effects") is not None
                continue
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
    conn.execute("UPDATE worlds SET current_tick=current_tick+600;")   # giorno 5: le trame possono cominciare
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


def test_self_concluding_plot_ends_with_prize_by_branch(conn, monkeypatch):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))
    p = _p(conn)
    intrigues.start(conn, p, "grotta_maestro", random.Random(2))
    _pick(conn, "inchini nove volte")                    # ramo «rispetto», due indizi
    d = intrigues.get(conn); d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
    intrigues.play(conn, p, intrigues.get(conn)["active"][0])
    _pick(conn, "comprensione del Dao")                  # terzo indizio
    d = intrigues.get(conn); d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
    before = conn.execute("SELECT COUNT(*) n FROM inventories WHERE owner_type='player';").fetchone()["n"]
    out = intrigues.play(conn, p, intrigues.get(conn)["active"][0])
    assert "L'ultimo dono" in out and "discepolo prima di svanire" in out
    assert intrigues.get(conn)["done"][-1]["outcome"] == "erede"
    after = conn.execute("SELECT COUNT(*) n FROM inventories WHERE owner_type='player';").fetchone()["n"]
    assert after > before
    assert not encounters.pending(conn)                  # nessuna scelta: si è concluso da solo


def test_ignored_plot_self_concludes_with_auto_end(conn):
    p = _p(conn)
    intrigues.start(conn, p, "marea_bestie", random.Random(3))
    encounters.clear(conn)
    d = intrigues.get(conn); d["active"][0]["next_day"] = -100; intrigues._save(conn, d)
    out = intrigues.daily(conn, tick.get_tick(conn), random.Random(1), p)
    assert any("si conclude senza di te" in x for x in out)
    assert intrigues.get(conn)["done"][-1]["outcome"] == "caduta"


def test_special_rewards_relic_blood_body(conn):
    from engine.systems import rewards
    p = _p(conn)
    for k in ("reliquia", "sangue", "corpo"):
        lines = rewards.grant(conn, random.Random(5), p, rank=1, kinds=[k], stones=False)
        assert lines, k


def test_secret_realm_take_all_makes_enemies_and_a_followup_plot(conn, monkeypatch):
    from engine.systems import bonds
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))
    conn.execute("UPDATE worlds SET current_tick=current_tick+600;")
    p = _p(conn)
    intrigues.start(conn, p, "reame_mille_tesori", random.Random(8))
    _pick(conn, "Entri da solo")
    for _ in range(2):
        d = intrigues.get(conn); d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
        intrigues.play(conn, p, intrigues.get(conn)["active"][0])
        sc = encounters.pending(conn)
        if "sala" in sc["title"].lower():
            break
        _pick(conn, "Aspetti che si sfianchino")
    labels = [ch["label"] for ch in encounters.pending(conn)["choices"]]
    assert any("solo la reliquia" in x for x in labels) and any("TUTTO" in x for x in labels)
    res, _ = _pick(conn, "TUTTO")
    assert "Ora ti odiano" in res
    d = intrigues.get(conn)
    assert "reame_avido" in d["flags"] and len(d["links"]["reame_avido"]) == 3
    assert bonds.nemeses(conn, p.id) or bonds.bond_kinds(conn, d["links"]["reame_avido"][1], p.id)
    # la conseguenza: la trama della vendetta può nascere, col cast legato al reame
    d["last_start"] = -999; intrigues._save(conn, d)
    keys = [x[2].get("key") for x in intrigues.candidates(conn, p, random.Random(1)) if x[1] == "nuova"]
    assert "vendetta_reame" in keys
    encounters.clear(conn)
    intrigues.start(conn, p, "vendetta_reame", random.Random(2))
    it = next(x for x in intrigues.get(conn)["active"] if x["key"] == "vendetta_reame")
    assert it["cast"]["pedina"] in d["links"]["reame_avido"]
    assert "reame_avido" not in intrigues.get(conn)["flags"]


def test_secret_realm_take_one_keeps_the_rule(conn, monkeypatch):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))
    p = _p(conn)
    intrigues.start(conn, p, "reame_mille_tesori", random.Random(9))
    _pick(conn, "Entri da solo")
    d = intrigues.get(conn); d["active"][0]["act"] = 2; d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
    intrigues.play(conn, p, intrigues.get(conn)["active"][0])
    res, _ = _pick(conn, "solo la reliquia")
    assert "reliquia" in res.lower() and "Ora ti odiano" not in res
    assert intrigues.get(conn)["done"][-1]["outcome"] == "un_tesoro"


def test_investigation_reveals_one_clue_at_a_time_then_accuse(conn, monkeypatch):
    p = _p(conn)
    intrigues.start(conn, p, "mano_ombra", random.Random(1))
    encounters.clear(conn)
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))
    out = intrigues.command(conn, p, "indaga 1")
    assert "Indizio 1" in out and "colpo dall'alto" in out
    assert "già indagato" in intrigues.command(conn, p, "indaga 1")      # una volta al giorno
    assert "Non sai ancora abbastanza" in intrigues.command(conn, p, "accusa 1")
    conn.execute("UPDATE worlds SET current_tick=current_tick+120;")
    out = intrigues.command(conn, p, "indaga 1")
    assert "Indizio 2" in out and "affrontare il colpevole" in out
    j = intrigues.journal(conn, p)[0]
    assert len(j["indizi"]) == 2 and j["accusa"] and j["servono"] == 2
    out = intrigues.command(conn, p, "accusa 1")
    assert "Il terzo giorno" in out                                     # dritto all'atto della resa dei conti
    labels = [ch["label"] for ch in encounters.pending(conn)["choices"]]
    assert any("Smascheri" in x for x in labels)


def test_failed_investigation_and_journal_logs_choices(conn, monkeypatch):
    p = _p(conn)
    intrigues.start(conn, p, "maledizione", random.Random(1))
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (False, 1, 99))
    _pick(conn, "Bruci incenso")
    out = intrigues.command(conn, p, "indaga 1")
    assert "non portano da nessuna parte" in out
    j = intrigues.journal(conn, p)[0]
    assert any("Bruci incenso" in x for x in j["diario"]) and not j["indizi"]


def _duel_win(conn, monkeypatch, outcome="risparmiato"):
    """Simula la fine del duello acceso dalla trama."""
    from engine.systems import duel
    d = intrigues.get(conn)
    nid = next(x["duel_npc"] for x in d["active"] if x.get("duel_npc"))
    return intrigues.on_duel(conn, _p(conn), nid, outcome)


def test_final_duel_decides_the_ending(conn, monkeypatch):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))
    p = _p(conn)
    intrigues.start(conn, p, "mano_ombra", random.Random(1))
    d = intrigues.get(conn); d["active"][0]["act"] = 2; intrigues._save(conn, d)
    encounters.clear(conn)
    intrigues.play(conn, p, intrigues.get(conn)["active"][0])
    res, cmd = _pick(conn, "Lo sfidi a duello")
    assert cmd.startswith("duello") and "lo deciderà il duello" in res
    assert intrigues.get(conn)["active"]                        # la trama aspetta l'esito
    out = _duel_win(conn, monkeypatch, "ucciso")
    assert any("Hai battuto" in x for x in out)
    assert intrigues.get(conn)["done"][-1]["outcome"] == "duello_vinto"


def test_losing_a_tournament_duel_eliminates_you(conn, monkeypatch):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))
    p = _p(conn)
    intrigues.start(conn, p, "torneo_truccato", random.Random(1))
    _pick(conn, "Rifiuti")
    d = intrigues.get(conn); d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
    intrigues.play(conn, p, intrigues.get(conn)["active"][0])
    _pick(conn, "Combatti lo stesso")
    out = _duel_win(conn, monkeypatch, "sconfitta")
    assert intrigues.get(conn)["done"][-1]["outcome"] == "eliminato"


def test_spared_opponent_talks_and_changes_next_act(conn, monkeypatch):
    monkeypatch.setattr(encounters, "roll", lambda c, r, pid, chk: (True, 99, 1))
    p = _p(conn)
    intrigues.start(conn, p, "torneo_truccato", random.Random(1))
    _pick(conn, "Rifiuti")
    d = intrigues.get(conn); d["active"][0]["next_day"] = 0; intrigues._save(conn, d)
    intrigues.play(conn, p, intrigues.get(conn)["active"][0])
    _pick(conn, "Combatti lo stesso")
    out = _duel_win(conn, monkeypatch, "risparmiato")
    assert any("parla per salvarsi" in x for x in out)
    it = intrigues.get(conn)["active"][0]
    assert "duello_risparmiato" in it["branches"] and it["clues"] == 1
    it["next_day"] = 0
    d = intrigues.get(conn); d["active"][0] = it; intrigues._save(conn, d)
    txt = intrigues.play(conn, p, intrigues.get(conn)["active"][0])
    assert "hai risparmiato" in txt
