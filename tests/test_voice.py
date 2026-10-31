"""Aggiornamento 76: i comandi detti a voce diventano comandi veri (o azioni della dashboard)."""
from __future__ import annotations

import pytest

from engine.cli import voice

S = {"presenti": [{"name": "Xu Shan", "kind": "human", "rel": "", "f": False},
                  {"name": "Mei Qingrong", "kind": "human", "rel": "", "f": True},
                  {"name": "Mo Han", "kind": "demon", "rel": "nemico", "f": False}],
     "uscite": [{"dir": "east", "name": "Villaggio di Aurora"}, {"dir": "up", "name": "Città di Cenere"}],
     "todo": [{"cmd": "via attributi"}], "scena": None, "duello": None}
DUEL = dict(S, scena={"choices": [{"n": 1, "label": "Colpisci"}]},
            duello={"arena": {"finito": False, "carte": [
                {"key": "colpisci", "name": "Colpisci", "cmd": "duello_azione colpisci", "ok": True, "kind": "base"},
                {"key": "t1", "name": "Palmo di Fuoco", "cmd": "duello_azione tecnica t1", "ok": True, "kind": "tecnica"},
                {"key": "difendi", "name": "Difendi", "cmd": "duello_azione difendi", "ok": True, "kind": "base"},
                {"key": "fuggi", "name": "Fuggi", "cmd": "duello_azione fuggi", "ok": True, "kind": "base"}]}})
SCENE = dict(S, scena={"choices": [{"n": 1, "label": "Lo risparmi"}, {"n": 2, "label": "Gli marchi l'anima: diventa tuo servo"},
                                   {"n": 3, "label": "Lo finisci"}]})


@pytest.mark.parametrize("said, want", [
    ("Attacca il primo nemico.", {"cmd": "attack Mo"}),
    ("attacca su scian", {"cmd": "attack Xu"}),
    ("Parla con il secondo", {"cmd": "talk Mei"}),
    ("osserva mei qing rong", {"cmd": "osserva Mei"}),
    ("duello con xu shan", {"cmd": "duello Xu"}),
    ("attacca tutti quanti", {"cmd": "attack all"}),
    ("assorbi tutto", {"cmd": "absorb all"}),
    ("Allenati!", {"cmd": "train"}),
    ("sfonda", {"cmd": "breakthrough"}),
    ("caccia", {"cmd": "attack creatures"}),
    ("vai a est", {"cmd": "move east"}),
    ("Vai verso villaggio di aurora", {"cmd": "move east"}),
    ("sali", {"cmd": "move up"}),
    ("vai alla seconda meta", {"cmd": "vai 2"}),
    ("compra la terza cosa", {"cmd": "buy 3"}),
    ("crea un clone", {"cmd": "clone crea"}),
    ("manda il clone a esplorare", {"cmd": "clone esplora"}),
    ("fai la prossima cosa", {"cmd": "via attributi"}),
    ("Apri la sezione del Dao.", {"ui": "m:via:profondi"}),
    ("mostrami lo zaino", {"ui": "tesori:zaino"}),
    ("apri il corpo", {"ui": "m:via:corpo"}),
    ("apri le saghe", {"ui": "storia:saghe"}),
    ("vai al mercante", {"ui": "m:mercato"}),
    ("avanti", {"ui": "avanti"}),
    ("pilota per sette giorni", {"ui": "pilota 7"}),
])
def test_phrases(said, want):
    got = voice.interpret(said, S, force=True)
    assert {k: v for k, v in got.items() if k != "eco"} == want


def test_buy_follows_the_open_tab():
    assert voice.interpret("compra la seconda", S, "m:setta")["cmd"] == "setta compra 2"


@pytest.mark.parametrize("said, want", [("difenditi", "duello_azione difendi"), ("attacco due", "duello_azione tecnica t1"),
                                        ("attacco più forte", "duello_azione tecnica t1"), ("scappa", "duello_azione fuggi"),
                                        ("palmo di fuoco", "duello_azione tecnica t1")])
def test_duel(said, want):
    assert voice.interpret(said, DUEL)["cmd"] == want


def test_scene_choices_by_number_and_by_words():
    assert voice.interpret("la seconda", SCENE)["cmd"] == "2"
    assert voice.interpret("scelta tre", SCENE)["cmd"] == "3"
    assert voice.interpret("rendilo mio schiavo", SCENE)["cmd"] == "2"
    assert voice.interpret("marchiagli l'anima", SCENE)["cmd"] == "2"


def test_real_commands_pass_through_unchanged():
    for c in ("train", "move north", "attack Xu", "use pillole", "via profondi", "vai 1", "parla Mei", "setta compra 2"):
        assert voice.interpret(c, S) == {}, c
    assert voice.looks_spoken("Allenati per favore.") and voice.looks_spoken("vai a est")


MORE = [("ritirati per cinque giorni", "ritiro 5"), ("comprendi il dao della spada", "comprehend spada"),
        ("forgia una corona", "equip forgia corona"), ("crea la ricetta due", "craft 2"),
        ("fondi le tecniche uno e tre", "tecniche fondi 1 3"), ("metti tre punti in forza", "attributi FOR 3"),
        ("distribuisci i punti", "attributi auto"), ("regala cento pietre a mei", "gift Mei 100"),
        ("insegna a xu", "insegna Xu"), ("accetta la missione 2", "missioni accetta 2"),
        ("indaga sulla trama uno", "trame indaga 1"), ("teletrasportati alla formazione 2", "teletrasporto 2"),
        ("nutri la bestia", "feed"), ("libera xu", "servo Xu libera"), ("metti Xu di scorta", "servo Xu scorta"),
        ("prendi lo stipendio", "setta stipendio"), ("iscriviti alla meta 3", "iscriviti 3"),
        ("visita la famiglia", "famiglia visita"), ("dona 100 pietre alla famiglia", "famiglia dona 100"),
        ("entra nel reame", "enter"), ("chiedi la promozione", "setta promozione"), ("usa la pillola del drago", "use pillola del drago")]


@pytest.mark.parametrize("said, want", MORE)
def test_every_command_family(said, want):
    assert voice.interpret(said, S, force=True)["cmd"] == want


def test_every_spoken_command_is_a_real_command(tmp_path, monkeypatch):
    """Nessuna frase produce un comando che il gioco non conosce."""
    import random
    from engine import db
    from engine.generators.world_gen import generate, WorldGenConfig
    from engine.systems import character
    from engine.cli import loop
    p = tmp_path / "v.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=3, factions=3, static_npc_count=12))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    for _said, cmd in MORE + [("x", "attack all"), ("x", "absorb all"), ("x", "clone crea"), ("x", "clone esplora")]:
        out = loop.dispatch(c, cmd, allow_nl=False) or ""
        assert "Comando sconosciuto" not in out, (cmd, out[:80])
    assert "COMANDI A VOCE" in loop.dispatch(c, "voce", allow_nl=False)
