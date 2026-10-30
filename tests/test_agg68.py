"""Aggiornamento 68: le immagini — quale quadro per oggetti, mosse, scene, equipaggiamento."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.simulation import cultivation
from engine.systems import character, art, menus, sects, dharma_body, ancestral_sigils as sg, duel, deification_tower


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "a68.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=4, static_npc_count=25))
    character.apply_origin(c, "mortale", random.Random(3))
    rid = cultivation.ensure_realm(c, 5)
    c.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    c.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))
    c.commit()
    yield c
    c.close()


def test_item_keys_cover_every_kind():
    assert art.item_keys("Lancia raffinata (regno 9)", "arma")[0] == "oggetti/arma_lancia"
    assert art.item_keys("Pillola dell'Eredità", "pillola", "leggendario")[0] == "oggetti/pillola_leggendaria"
    assert art.item_keys("Sangue del Drago", "essenza")[0] == "oggetti/essenza_sangue"
    assert art.item_keys("Essenza del Dao «fuoco»", "essenza")[0] == "oggetti/essenza_dao"
    assert art.item_keys("Cuore Demoniaco di Stirpe Maligna", "nucleo")[0] == "oggetti/nucleo_demone"
    assert art.item_keys("Borsa di Pietre Spirituali", "tesoro")[0] == "oggetti/pietre"
    assert art.item_keys("Sigillo dell'Imperatore Demone", "reliquia")[0] == "reliquie/demoni"
    for kind in ("manuale", "talismano", "formazione", "uovo", "incenso", "boh"):
        assert art.item_keys("x", kind)[-1] == "oggetti/tesoro"


def test_action_keys():
    assert art.action_key("tecnica", "Folgore della Tribolazione") == "azioni/fulmine"
    assert art.action_key("tecnica", "Arte Suprema: Antenato della Spada") == "azioni/spada"
    assert art.action_key("tecnica", "Morso dell'Abisso") == "azioni/abisso"
    assert art.action_key("tecnica", "Qualcosa di misterioso") == "azioni/colpo"
    assert art.action_key("difendi") == "azioni/difesa" and art.action_key("pillola") == "azioni/pillola"


def test_scene_keys_from_specific_to_generic():
    k = art.scene_keys("vendetta", "combat")
    assert k[0] == "scene/vendetta" and k[-1] == "scene/combat"
    k = art.scene_keys("compagni_amico", "story", "salvataggio")
    assert "scene/salvataggio" in k and k.index("scene/salvataggio") < k.index("scene/story")
    assert art.scene_keys(None, "fortune") == ["scene/fortune"]


def test_section_img_and_equipment(conn):
    s = menus.section("x", ["a"], img="oggetti/anello")
    assert s["img"] == ["oggetti/anello"]
    assert "img" not in menus.section("y")
    p = entities.get_player(conn)
    sects.grant_resource(conn, "pietre_spirituali", 10000, p.id)
    dharma_body.awaken(conn, p)
    sg.give(conn, 0)
    eq = art.equipment(conn, p)
    slots = {e["slot"] for e in eq}
    assert "Corpo del Dharma" in slots and "Sigillo" in slots
    assert all(e["img"] for e in eq)


def test_duel_records_action_image(conn):
    p = entities.get_player(conn)
    deification_tower.challenge(conn, p)
    duel.act(conn, p, "difendi")
    d = duel.get(conn)
    if d:                                                     # il duello può essere già finito
        assert d["last"]["img"] == "azioni/difesa"
        assert d["last"]["img_nemico"] in ("azioni/nemico", "azioni/carica")
