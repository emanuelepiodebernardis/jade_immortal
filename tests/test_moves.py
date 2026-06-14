"""Mosse attive: disponibilità per arma/tecnica/abisso, cooldown, effetti, Morso."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.core import entities, tick as tickmod
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, sects, sect_life, weapons, guild, moves
from engine.simulation import combat


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "mv.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=4, static_npc_count=20))
    character.apply_origin(c, "genio", random.Random(1))
    c.commit()
    yield c
    c.close()


def _join(conn):
    sect = sects.joinable_sects(conn)[0]
    conn.execute("UPDATE players SET location_id=? WHERE id=1;", (sect["home_location_id"],))
    sects.join_sect(conn, tick=0)
    sect_life.setup_class(conn, 0, random.Random(1))


def test_weapon_grants_signature_move(conn):
    _join(conn)
    assert moves.available_moves(conn, 1) == []      # nessuna arma -> nessuna mossa
    weapons.choose_weapon(conn, "spada", 1)
    ms = moves.available_moves(conn, 1)
    assert any(m["key"] == "fendente" for m in ms)


def test_each_weapon_has_distinct_move(conn):
    seen = set()
    for wk in ("spada", "lancia", "sciabola", "arco", "pugno", "bastone"):
        _, _name, _cd, mods, _desc = moves._WEAPON_MOVES[wk]
        seen.add(tuple(sorted(mods.items())))
    assert len(seen) == 6        # sei effetti diversi


def test_abyss_move_for_devourer(tmp_path, monkeypatch):
    p = tmp_path / "ab.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=15))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    ms = moves.available_moves(c, 1)
    assert any(m["key"] == "morso" for m in ms)
    c.close()


def test_learned_technique_becomes_active_move(conn):
    _join(conn)
    m = sects.get_membership(conn)
    tech = guild.sect_techniques(conn, m["faction_id"])[0]
    guild.add_merit(conn, tech["cost"], 1)
    guild.learn(conn, 0, 1, 1)
    ms = moves.available_moves(conn, 1)
    assert any(x["source"] == "tecnica" for x in ms)


def test_move_goes_on_cooldown(conn):
    _join(conn)
    weapons.choose_weapon(conn, "spada", 1)
    mv = moves.find_move(conn, "fendente", 1)
    assert mv["ready"] is True
    moves.use_cost(conn, mv, tickmod.get_tick(conn), 1)
    after = moves.find_move(conn, "fendente", 1)
    assert after["ready"] is False and after["ready_in"] > 0


def test_move_modifiers_increase_effective_attack(conn):
    # un attacco con moltiplicatore uccide più facilmente: verifichiamo l'effetto
    # statistico su molti scontri (con mossa vs senza).
    _join(conn)
    weapons.choose_weapon(conn, "spada", 1)
    # bersaglio debole ripetuto
    def kills(mods):
        k = 0
        for s in range(60):
            beast = conn.execute("SELECT id FROM npcs WHERE kind='beast' AND status='alive' LIMIT 1;").fetchone()
            if not beast:
                from engine.generators import creature_gen
                beast_id = creature_gen._spawn_one(conn, random.Random(s), "beast", 1, 1, 1)
            else:
                beast_id = beast["id"]
            rng = random.Random(1000 + s)
            res = combat.resolve_combat(conn, 0, rng, ("player", 1, "Tu"),
                                        ("npc", beast_id, "B"), 1, None, [], atk_mods=mods)
            if res["died"] and res["winner"][0] == "player":
                k += 1
            # ripristina la creatura viva per il confronto equo
            conn.execute("UPDATE npcs SET status='alive' WHERE id=?;", (beast_id,))
        return k
    base = kills(None)
    boosted = kills({"attack_mult": 1.5, "death_bonus": 0.28})
    assert boosted >= base       # la mossa esecutrice uccide almeno quanto l'attacco base
