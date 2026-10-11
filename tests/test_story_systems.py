"""Nuovi sistemi narrativi: aiuto per categorie, HUD, azioni suggerite, incontri a scelta,
legami (compagni/maestro/nemesi), storia per origine e reincarnazione."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import (character, encounters, encounter_data, bonds, storyline, rebirth,
                            suggestions, relations, sects, state, npc_factory, training)
from engine.simulation import world_tick, cultivation
from engine.cli import loop, intent, help_text, hud, story_cmds


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "story.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=11, factions=3, static_npc_count=20))
    character.apply_origin(c, "mortale", random.Random(1))
    c.commit()
    yield c
    c.close()


def _player(conn):
    return entities.get_player(conn)


def _spawn_here(conn, archetype="vagabondo", tier_offset=0, **kw):
    p = _player(conn)
    tier = (cultivation.realm_tier(conn, "player", 1) or 1) + tier_offset
    return npc_factory.spawn(conn, random.Random(3), archetype=archetype,
                             location_id=p.location_id, tier=tier, **kw)


# ---------- rifiniture ----------

def test_help_is_categorized_and_complete():
    short = help_text.help_for("")
    assert "legami" in short and "storia" in short
    assert "recruit" in help_text.help_for("legami")
    full = help_text.help_for("tutto")
    for w in ("attack", "cultivate", "talk", "goals", "lives", "challenge"):
        assert w in full


def test_intent_knows_every_command():
    for w in ("talk", "recruit", "goals", "challenge", "invade", "market", "absorb", "lives"):
        assert w in intent.KNOWN_COMMANDS
    assert "recruit" in intent.SYSTEM_PROMPT


def test_location_is_in_italian(conn):
    out = loop.render_location(conn, _player(conn))
    assert out.startswith("Ti trovi a:")
    assert "Uscite:" in out and "You see" not in out


def test_hud_line(conn):
    line = hud.hud_line(conn, _player(conn))
    assert "Giorno 1" in line and "Qi" in line


def test_outlaw_is_tagged_in_look(conn):
    p = _player(conn)
    nid = _spawn_here(conn)
    conn.execute("INSERT INTO outlaws (npc_id, crime, reward) VALUES (?, 'furto', 77);", (nid,))
    out = loop.render_location(conn, p)
    assert "RICERCATO, taglia 77" in out


# ---------- azioni suggerite ----------

def test_suggestions_are_computed_and_executable_by_number(conn):
    p = _player(conn)
    sugg = suggestions.compute(conn, p)
    assert 1 <= len(sugg) <= suggestions.MAX
    suggestions.store(conn, sugg)
    out = loop.dispatch(conn, "1")
    assert out.startswith(f"(→ {sugg[0][1]})")


def test_after_command_shows_hud_and_suggestions(conn):
    tail = story_cmds.after_command(conn, _player(conn))
    assert "Azioni suggerite" in tail and "──" in tail
    loop.dispatch(conn, "suggest off")
    loop.dispatch(conn, "hud off")
    assert story_cmds.after_command(conn, _player(conn)) == ""


# ---------- incontri ----------

def test_encounter_catalog_is_well_formed():
    keys = set()
    for e in encounter_data.ENCOUNTERS:
        assert e["key"] not in keys
        keys.add(e["key"])
        assert 2 <= len(e["choices"]) <= 4
        e["text"].format(npc="X", luogo="Y")
        for ch in e["choices"]:
            ch["label"].format(npc="X", luogo="Y")
            if "check" in ch:
                assert ch["check"]["stat"] in encounters.STAT_LABEL
                assert "success" in ch and "failure" in ch
    for arc in storyline.ARCS.values():
        assert len(arc["chapters"]) == 4
        for chp in arc["chapters"]:
            for ch in chp["scene"]["choices"]:
                if "check" in ch:
                    assert ch["check"]["stat"] in encounters.STAT_LABEL


def test_forced_encounter_and_choice_apply_effects(conn):
    p = _player(conn)
    txt = encounters.maybe_trigger(conn, p, force_key="lago_yin")
    assert "[1]" in txt and encounters.pending(conn)
    out = loop.dispatch(conn, "2")                 # raccogli la fiala: nessuna prova
    assert "Fiala d'Acqua Yin" in out
    assert encounters.pending(conn) is None
    from engine.systems import items
    assert any("Fiala" in r["name"] for r in items.player_inventory(conn, 1))


def test_every_encounter_choice_resolves_without_errors(conn):
    p = _player(conn)
    for e in encounter_data.ENCOUNTERS:
        for i in range(len(e["choices"])):
            encounters.clear(conn)
            state.delete(conn, encounters.SEEN_KEY)
            encounters.maybe_trigger(conn, _player(conn), force_key=e["key"])
            text, _cmd = encounters.choose(conn, _player(conn), i + 1)
            assert text.startswith("»")
            conn.execute("UPDATE players SET status='alive', location_id=? WHERE id=1;",
                         (p.location_id,))


def test_leaving_dismisses_encounter_but_not_story(conn):
    p = _player(conn)
    encounters.maybe_trigger(conn, p, force_key="bisca")
    other = next(iter(entities.get_exits(conn, p.location_id).values()))
    entities.move_player(conn, 1, other)
    assert "svanisce" in encounters.dismiss_if_moved(conn, _player(conn))
    encounters.start_scene(conn, _player(conn), {"title": "S", "text": "t", "sticky": True,
                                                 "choices": [{"label": "ok", "effects": {}}]})
    entities.move_player(conn, 1, p.location_id)
    assert encounters.dismiss_if_moved(conn, _player(conn)) is None
    assert encounters.pending(conn)["location_id"] == p.location_id


def test_scene_spawn_shows_strength_hint(conn):
    p = _player(conn)
    txt = encounters.maybe_trigger(conn, p, force_key="giovane_maestro")
    assert "scontro all'ultimo sangue" in txt
    assert encounters.pending(conn)["ctx"]["npc_id"]


# ---------- legami ----------

def test_talk_raises_relation_and_recruit_needs_trust(conn):
    nid = _spawn_here(conn, traits={"pride": 40})
    npc = entities.get_npc(conn, nid)
    out = loop.dispatch(conn, f"recruit {npc.name}")
    assert "non ti conosce abbastanza" in out
    loop.dispatch(conn, f"talk {npc.name}")
    assert relations.get_disposition(conn, nid).score > 0
    relations.adjust(conn, nid, 60, 0)
    out = loop.dispatch(conn, f"recruit {npc.name}")
    assert "viaggia con te" in out
    assert bonds.companion(conn, 1)["npc_id"] == nid


def test_companion_follows_and_is_spared_by_attack_all(conn):
    p = _player(conn)
    nid = _spawn_here(conn)
    relations.adjust(conn, nid, 80, 0)
    bonds.recruit(conn, 0, p, entities.get_npc(conn, nid))
    dest = next(iter(entities.get_exits(conn, p.location_id).values()))
    loop.dispatch(conn, "move " + next(iter(entities.get_exits(conn, p.location_id).keys())))
    assert entities.get_npc(conn, nid).location_id == _player(conn).location_id == dest
    # 'attack all' non colpisce il compagno
    conn.execute("UPDATE npcs SET location_id=NULL WHERE id<>? AND location_id=?;", (nid, dest))
    assert loop.dispatch(conn, "attack all") == "Non c'è nessuno da attaccare qui."


def test_companion_fights_alongside(conn):
    p = _player(conn)
    ally = _spawn_here(conn, tier_offset=2)
    relations.adjust(conn, ally, 80, 0)
    bonds.recruit(conn, 0, p, entities.get_npc(conn, ally))
    foe = _spawn_here(conn, archetype="discepolo", tier_offset=0)
    out = loop.dispatch(conn, f"attack {entities.get_npc(conn, foe).name}")
    assert entities.get_npc(conn, ally).name in out


def test_master_boosts_cultivation(conn):
    nid = _spawn_here(conn, archetype="eremita", tier_offset=2)
    npc = entities.get_npc(conn, nid)
    assert "Non ti conosco" in loop.dispatch(conn, f"disciple {npc.name}")
    relations.adjust(conn, nid, 70, 0)
    assert "discepolo" in loop.dispatch(conn, f"disciple {npc.name}")
    assert bonds.cultivation_bonus(conn, 1) > 0
    assert "maestro" in loop.dispatch(conn, "cultivate")


def test_fled_enemy_can_become_nemesis_and_returns(conn):
    p = _player(conn)
    nid = _spawn_here(conn, traits={"pride": 95, "ambition": 95})
    bonds.add_bond(conn, 1, nid, "rival", 0)
    msg = bonds.on_enemy_fled(conn, 0, random.Random(1), p, entities.get_npc(conn, nid))
    assert "NEMESI" in msg
    assert entities.get_npc(conn, nid).location_id is None        # si ritira ad allenarsi
    row = bonds.nemeses(conn, 1)[0]
    # passa il tempo: torna, ti trova e si apre la scena a scelta
    conn.execute("UPDATE bonds SET ready_tick=0;")
    for _ in range(60):
        world_tick.advance(conn, 1, rng=random.Random(2))
        if encounters.pending(conn):
            break
        n = entities.get_npc(conn, nid)
        if n.location_id is not None and _ == 30:
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (_player(conn).location_id, nid))
    sc = encounters.pending(conn)
    assert sc and sc["key"] == "nemesi" and row["name"] in sc["title"]


def test_killing_nemesis_closes_the_account(conn):
    p = _player(conn)
    nid = _spawn_here(conn)
    bonds.add_bond(conn, 1, nid, "nemesis", 0)
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (nid,))
    lines = bonds.on_npc_killed(conn, 0, random.Random(1), p, nid)
    assert any("chiuso" in ln for ln in lines)
    assert "Colui che Chiude i Conti" in state.titles(conn)


# ---------- storia personale ----------

def test_story_chapter_opens_after_first_day(conn):
    p = _player(conn)
    assert storyline.maybe_advance(conn, p) is None
    world_tick.advance(conn, training.DAY_TICKS, rng=random.Random(1))
    txt = storyline.maybe_advance(conn, _player(conn))
    assert "capitolo 1/4" in txt
    out = loop.dispatch(conn, "1")                   # giura vendetta
    assert "taglia" in out
    capo = storyline.story_npc(conn, "capo")
    assert capo is not None and capo["status"] == "alive"
    assert capo["name"] in storyline.goals(conn, _player(conn))
    # il capitolo 2 si apre solo quando il capo cade
    assert storyline.maybe_advance(conn, _player(conn)) is None
    conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (capo["id"],))
    assert "capitolo 2/4" in storyline.maybe_advance(conn, _player(conn))


@pytest.mark.parametrize("origin", list(storyline.ARCS))
def test_every_origin_first_chapter_resolves(conn, origin):
    conn.execute("DELETE FROM character_profiles;")
    character.apply_origin(conn, origin, random.Random(2))
    world_tick.advance(conn, training.DAY_TICKS, rng=random.Random(1))
    assert storyline.maybe_advance(conn, _player(conn))
    out = loop.dispatch(conn, "2")
    assert out and "»" in out


# ---------- reincarnazione ----------

def test_death_epilogue_and_rebirth_in_same_world(conn):
    sects.grant_resource(conn, "pietre_spirituali", 200, 1)
    state.grant_title(conn, "Prova")
    npcs_before = conn.execute("SELECT COUNT(*) c FROM npcs;").fetchone()["c"]
    conn.execute("UPDATE players SET status='dead' WHERE id=1;")
    row = rebirth.record_death(conn, _player(conn))
    assert row["epilogue_title"] and row["tomb_stones"] == 100
    assert "EPILOGO" in rebirth.epilogue_text(row)
    assert rebirth.record_death(conn, _player(conn))["id"] == row["id"]   # idempotente
    opts = rebirth.inheritance_options(row)
    rebirth.reincarnate(conn, random.Random(5), "genio", "Yun", opts[0])
    q = _player(conn)
    assert q.status == "alive" and q.name == "Yun"
    assert rebirth.life_no(conn) == 2
    assert sects.get_resource(conn, "pietre_spirituali", 1) == 0          # ricominci da zero
    assert state.titles(conn) == []
    assert character.get_profile(conn, "player", 1)["origin"] == "genio"
    assert conn.execute("SELECT COUNT(*) c FROM npcs;").fetchone()["c"] == npcs_before
    # la tomba custodisce le pietre della vita passata
    entities.move_player(conn, 1, row["tomb_location_id"])
    assert "tomba di" in loop.render_location(conn, _player(conn))
    out = loop.dispatch(conn, "loot")
    assert "+100 pietre" in out
    assert "Reliquia" in out
    assert "vita n.2" in rebirth.describe_lives(conn)


def test_eight_quick_actions_urgent_first_routine_always_there(conn):
    p = _player(conn)
    sugg = suggestions.compute(conn, p)
    assert suggestions.MAX == 8
    assert 4 <= len(sugg) <= 8
    cmds = [c for _l, c in sugg]
    assert len(set(cmds)) == len(cmds)
    assert "auto 1" in cmds                       # il pilota automatico è sempre a portata di tasto
    suggestions.store(conn, sugg)
    out = loop.dispatch(conn, str(len(sugg)))
    assert out.startswith(f"(→ {sugg[-1][1]})")
    # ciò che è urgente resta in testa
    from engine.systems import state
    state.set_json(conn, "captivity", {"captor": "x", "since": 0})
    first = suggestions.compute(conn, _player(conn))[0][1]
    assert first != "auto 1"
