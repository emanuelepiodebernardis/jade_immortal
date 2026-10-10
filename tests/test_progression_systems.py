"""Destini e talento dei rivali, demone interiore, bestie (talenti, rare, ibride),
professioni, spirito dell'arma, durata della vita e maestri segreti."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.generators import dao_gen
from engine.systems import (character, destinies, heart_demon, encounters, beasts, professions,
                            weapon_spirit, lifespan, secret_masters, state, bonds,
                            npc_factory, rebirth, combat_states)
from engine.simulation import cultivation
from engine.cli import loop


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "prog.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=8, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(2))
    c.commit()
    yield c
    c.close()


def _player(conn):
    return entities.get_player(conn)


def _set_tier(conn, tier):
    rid = cultivation.ensure_realm(conn, tier)
    conn.execute("UPDATE players SET realm_id=? WHERE id=1;", (rid,))
    conn.execute("UPDATE cultivation_records SET realm_id=? WHERE character_type='player' AND character_id=1;", (rid,))


# ---------- origini e destini ----------

def test_devourer_always_has_highest_talent(tmp_path, monkeypatch):
    others_max = max(o["aff"]["cultivation"] for k, o in character.ORIGINS.items() if k != "divoratore") + 6
    for seed in range(30):
        p = tmp_path / f"d{seed}.db"
        db.init_db(p)
        c = db.connect(p)
        generate(c, WorldGenConfig(seed=1, factions=2, static_npc_count=5))
        character.apply_origin(c, "divoratore", random.Random(seed))
        assert character.get_profile(c, "player", 1)["aff_cultivation"] > others_max
        c.close()


def test_destiny_hand_and_effects(conn):
    hand = destinies.draw_hand(random.Random(1), life_no=1)
    assert len(hand) == 6 and all(destinies.DESTINIES[k]["rarity"] != "leggendario" for k in hand)
    big = set()
    for s in range(60):
        big |= set(destinies.draw_hand(random.Random(s), life_no=2))
    assert any(destinies.DESTINIES[k]["rarity"] == "leggendario" for k in big)
    before = lifespan.max_years(conn, 1)
    destinies.apply(conn, "genio_malato")
    assert destinies.current(conn, 1) == "genio_malato"
    assert lifespan.max_years(conn, 1) == before - 20
    destinies.apply(conn, "cuore_spada")
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND dao_key='spada';").fetchone()
    assert r["comprehension"] >= 25


def test_rival_talent_setting_scales_classmates(conn):
    destinies.set_rival_level(conn, "leggendario")
    assert destinies.rival_mult(conn) == 1.6
    assert state.get(conn, "world_rival_talent") == "leggendario"


def test_phoenix_saves_once(conn):
    destinies.apply(conn, "fenice")
    conn.execute("UPDATE players SET status='dead' WHERE id=1;")
    assert rebirth.try_phoenix(conn, _player(conn))
    assert _player(conn).status == "alive"
    conn.execute("UPDATE players SET status='dead' WHERE id=1;")
    assert rebirth.try_phoenix(conn, _player(conn)) is None


# ---------- demone interiore ----------

def _ready_for_breakthrough(conn):
    conn.execute("UPDATE cultivation_records SET stage=10, progress=1.0 WHERE character_type='player' AND character_id=1;")


def test_heart_demon_scene_and_bonus(conn):
    _ready_for_breakthrough(conn)
    sc = heart_demon.scene(conn, 1, 1)
    txt = encounters.start_scene(conn, _player(conn), sc)
    assert "Demone Interiore" in txt
    assert heart_demon.should_trigger(conn, 1, 1, random.Random(1)) is False    # una volta per regno
    heart_demon.add_bonus(conn, 0.2)
    assert heart_demon.take_bonus(conn) == pytest.approx(0.2)
    assert heart_demon.take_bonus(conn) == 0.0


def test_breakthrough_bypass_and_demon_failure_spawns_nemesis(conn):
    _ready_for_breakthrough(conn)
    msg = heart_demon.spawn_demon(conn, _player(conn), 0)
    assert "NEMESI" in msg
    out = loop.dispatch(conn, "breakthrough !")
    assert "Demone Interiore" not in out


# ---------- bestie ----------

def test_rare_beast_spawn_and_tame(conn, monkeypatch):
    _set_tier(conn, 6)
    nid, loc = beasts.spawn_rare(conn, random.Random(1), _player(conn),
                                 species=next(s for s in beasts.RARE_SPECIES if s[0] == "Drago-Fenice"))
    tr = beasts.traits(conn, nid)
    assert tr["rarity"] == "ibrida" and tr["ability"] == "rinascita"
    assert tr["talent"] in ("prodigio", "divina", "rara")
    assert beasts.active_rare(conn)
    conn.execute("UPDATE players SET location_id=(SELECT location_id FROM npcs WHERE id=?) WHERE id=1;", (nid,))
    # una bestia ferita e molto più debole di te si doma facilmente
    from engine.systems import perception
    monkeypatch.setattr(perception, "relative_strength", lambda *a: "molto più debole di te")
    conn.execute("INSERT INTO injuries (character_type, character_id, severity, description, "
                 "inflicted_tick, healed, heal_tick) VALUES ('npc', ?, 3, 'x', 0, 0, 999);", (nid,))
    for s in range(20):
        text, follow = beasts.tame(conn, 0, random.Random(s), _player(conn), entities.get_npc(conn, nid))
        if beasts.pet(conn, 1):
            break
    assert beasts.pet(conn, 1)["npc_id"] == nid
    assert "tua bestia" in loop.render_location(conn, _player(conn))


def test_beast_fights_and_grants_rebirth(conn):
    _set_tier(conn, 6)
    nid, _ = beasts.spawn_rare(conn, random.Random(2), _player(conn),
                               species=next(s for s in beasts.RARE_SPECIES if s[0] == "Fenice"))
    conn.execute("UPDATE npcs SET location_id=(SELECT location_id FROM players WHERE id=1) WHERE id=?;", (nid,))
    bonds.add_bond(conn, 1, nid, "beast", 0)
    foe = npc_factory.spawn(conn, random.Random(3), archetype="vagabondo",
                            location_id=_player(conn).location_id, tier=1)
    fx = combat_states.FightCtx(conn, 1, foe, "Tu", "X", 100, 100, 10, 10)
    ally = beasts.combat_ally(conn, 1, foe, fx)
    assert ally and ally["attack"] > 0
    assert fx.p.lethal_saves >= 1


def test_common_creature_has_talent(conn):
    from engine.generators import creature_gen
    bid = creature_gen._spawn_one(conn, random.Random(1), "beast", _player(conn).location_id, 1, 1)
    assert beasts.traits(conn, bid)["talent"] in beasts.TALENT_MULT


# ---------- professioni ----------

def test_profession_gather_craft_and_level(conn):
    assert "Scegli l'arte" in professions.choose(conn, 1, "alchimia")
    professions.give(conn, 1, "erbe", 30)
    out = ""
    for _ in range(6):
        out += professions.craft(conn, 0, random.Random(_), _player(conn), "1")
    assert "Pillola di Raccolta del Qi" in out
    assert professions.level(conn, 1) >= 2
    wild = conn.execute("SELECT id FROM locations WHERE location_type='mountain' LIMIT 1;").fetchone()
    if wild:
        entities.move_player(conn, 1, wild["id"])
        assert "Raccogli" in professions.gather(conn, 0, random.Random(1), _player(conn)) or True


def test_talisman_becomes_combat_buff(conn):
    professions.choose(conn, 1, "talismani")
    professions.give(conn, 1, "erbe", 5)
    professions.give(conn, 1, "minerali", 5)
    for s in range(10):
        professions.craft(conn, 0, random.Random(s), _player(conn), "1")
    from engine.systems import items
    assert any("Talismano" in r["name"] for r in items.player_inventory(conn, 1))
    loop.dispatch(conn, "use talismano")
    assert state.get_json(conn, "combat_buffs")


def test_longevity_elixir_extends_life(conn):
    before = lifespan.max_years(conn, 1)
    from engine.systems import items
    items.apply_effects(conn, 0, random.Random(1), 1, {"lifespan_years": 30})
    assert lifespan.max_years(conn, 1) == before + 30


# ---------- spirito dell'arma ----------

def test_weapon_spirit_awakens_with_kills(conn):
    character_profiles = "UPDATE character_profiles SET weapon='spada', weapon_tier=1, weapon_rarity=3 " \
                         "WHERE character_type='player' AND character_id=1;"
    conn.execute(character_profiles)
    msgs = [weapon_spirit.on_kill(conn, random.Random(i), _player(conn)) for i in range(weapon_spirit.AWAKEN_KILLS)]
    assert any(m and "risveglia" in m for m in msgs)
    assert weapon_spirit.level(weapon_spirit.get(conn, 1)) >= 1


# ---------- durata della vita ----------

def test_lifespan_doubles_with_realm(conn):
    assert lifespan.max_years(conn, 1) == 80
    _set_tier(conn, 2)
    assert lifespan.max_years(conn, 1) == 160
    _set_tier(conn, 4)
    assert lifespan.max_years(conn, 1) == 640


def test_old_age_kills(conn):
    from engine.systems import character as ch
    conn.execute("UPDATE character_profiles SET age=79 WHERE character_type='player' AND character_id=1;")
    t = tick.get_tick(conn)
    state.set(conn, "life_start_tick", str(t - ch.YEAR_TICKS * 2))
    lines = lifespan.daily_check(conn, _player(conn), t)
    assert lines and _player(conn).status == "dead"
    row = rebirth.record_death(conn, _player(conn))
    assert row["epilogue_key"] == "vecchiaia"


# ---------- maestri segreti ----------

def test_sword_master_appears_teaches_and_points_to_next(conn):
    dao_gen._set_dao(conn, "player", 1, "spada", 60, 60, 1)
    assert any(m["key"] == "spada_1" for m in secret_masters.available(conn, 1))
    txt = secret_masters.maybe_meet(conn, _player(conn), force="spada_1")
    assert "Vecchio della Rupe" in txt
    out = loop.dispatch(conn, "1")
    assert "Nove Forme della Spada Solitaria" in out
    assert "Custode della Tomba delle Spade" in out              # indica il prossimo maestro
    assert "spada_1" in secret_masters.learned(conn)
    assert not any(m["path"] == "Spada" for m in secret_masters.available(conn, 1))
    assert state.get_json(conn, "master_procs")


def test_demonic_master_requires_kills_and_has_a_price(conn):
    assert not any(m["path"] == "Demoniaca" for m in secret_masters.available(conn, 1))
    state.set(conn, "kills_human", "10")
    assert any(m["key"] == "demone_1" for m in secret_masters.available(conn, 1))
    from engine.systems import karma
    k0 = karma.get_karma(conn, "player", 1)
    secret_masters.learn(conn, 0, _player(conn), "demone_1")
    assert karma.get_karma(conn, "player", 1) < k0
    assert "Via Demoniaca" in secret_masters.describe(conn, _player(conn))


def test_gift_master_needs_the_gift(conn):
    lines = secret_masters.learn(conn, 0, _player(conn), "giusto_1", gift={"erbe": 3})
    assert "Torna quando" in lines[0]
    professions.give(conn, 1, "erbe", 3)
    lines = secret_masters.learn(conn, 0, _player(conn), "giusto_1", gift={"erbe": 3})
    assert "Diciotto Palmi del Drago" in lines[0]
