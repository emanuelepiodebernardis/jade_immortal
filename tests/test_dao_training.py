"""Allenamento dei Dao: comprensione, affinità, tetto, attenzione divisa, effetto combat, risveglio."""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from engine import db
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, dao_training, absorption
from engine.simulation import combat, cultivation


@pytest.fixture()
def conn(tmp_path: Path, monkeypatch):
    p = tmp_path / "daot.db"
    monkeypatch.setattr(db, "DB_PATH", p)
    db.init_db(p)
    c = db.connect(p)
    generate(c, WorldGenConfig(seed=42, factions=3, static_npc_count=20))
    character.apply_origin(c, "divoratore", random.Random(1))
    c.commit()
    yield c
    c.close()


def test_comprehend_raises_practiced_dao(conn):
    before = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=1 AND dao_key='corpo';").fetchone()["comprehension"]
    res = dao_training.comprehend(conn, 0, random.Random(1), "corpo")
    assert res["status"] == "ok"
    assert res["comprehension"] > before


def test_cannot_train_latent_unawakened_dao(conn):
    # destino è latente (practiced=0, comprehension=0) per il divoratore
    res = dao_training.comprehend(conn, 0, random.Random(1), "destino")
    assert res["status"] == "locked"


def test_comprehension_has_no_cap(conn):
    # progressione SENZA tetto: oltre 100 e oltre le soglie successive
    conn.execute("UPDATE character_daos SET comprehension=99 WHERE character_type='player' AND character_id=1 AND dao_key='corpo';")
    for _ in range(200):
        dao_training.comprehend(conn, 0, random.Random(_), "corpo")
    c = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=1 AND dao_key='corpo';").fetchone()["comprehension"]
    assert c > 100        # ha superato il vecchio tetto


def test_combat_dao_increases_power(conn):
    base = combat.combat_power(conn, "player", 1)["attack"]
    conn.execute("UPDATE character_daos SET comprehension=100 WHERE character_type='player' AND character_id=1 AND dao_key='corpo';")
    boosted = combat.combat_power(conn, "player", 1)["attack"]
    assert boosted > base


def test_combat_bonus_grows_by_thresholds(conn):
    # niente più tetto fisso: il bonus cresce per soglie raggiunte.
    # un singolo Dao da combattimento a 50 -> +20%; a 100 -> +35%.
    for dk in ("fulmine", "spada"):
        conn.execute("INSERT OR IGNORE INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) VALUES ('player',1,?,60,0,1);", (dk,))
        conn.execute("UPDATE character_daos SET comprehension=0 WHERE character_type='player' AND character_id=1 AND dao_key=?;", (dk,))
    conn.execute("UPDATE character_daos SET comprehension=50 WHERE character_type='player' AND character_id=1 AND dao_key='corpo';")
    f50 = dao_training.combat_dao_factor(conn, "player", 1)
    assert abs(f50 - 1.20) < 1e-6
    conn.execute("UPDATE character_daos SET comprehension=100 WHERE character_type='player' AND character_id=1 AND dao_key='corpo';")
    f100 = dao_training.combat_dao_factor(conn, "player", 1)
    assert abs(f100 - 1.35) < 1e-6
    assert f100 > f50          # supera il vecchio cap di +20%


def test_technique_unlocks_at_threshold(conn):
    # a comprensione 100 si sblocca la prima tecnica del Dao
    assert dao_training.unlocked_technique("Dao del Fulmine", 99) is None
    assert dao_training.unlocked_technique("Dao del Fulmine", 100) == "Tecnica del Fulmine"
    assert dao_training.unlocked_technique("Dao del Fulmine", 1000) == "Legge del Fulmine"


def test_deep_dao_does_not_boost_combat(conn):
    # risvegliare 'destino' non deve cambiare il fattore di combattimento
    before = dao_training.combat_dao_factor(conn, "player", 1)
    conn.execute("UPDATE character_daos SET comprehension=100 WHERE character_type='player' AND character_id=1 AND dao_key='destino';")
    after = dao_training.combat_dao_factor(conn, "player", 1)
    assert abs(after - before) < 1e-6


def test_attention_divides_with_more_daos(conn):
    # con molti Dao praticati, il guadagno per sessione cala
    conn.execute("UPDATE character_daos SET comprehension=10 WHERE character_type='player' AND character_id=1 AND dao_key='corpo';")
    r_single = dao_training.comprehend(conn, 0, random.Random(5), "corpo")
    # aggiungi tanti dao praticati
    for dk in ("spada", "fulmine", "anima", "destino", "tempo", "spazio"):
        conn.execute("UPDATE character_daos SET practiced=1, comprehension=5 WHERE character_type='player' AND character_id=1 AND dao_key=?;", (dk,))
    conn.execute("UPDATE character_daos SET comprehension=10 WHERE character_type='player' AND character_id=1 AND dao_key='corpo';")
    r_many = dao_training.comprehend(conn, 0, random.Random(5), "corpo")
    assert r_many["comprehension"] <= r_single["comprehension"]


def test_absorption_awakens_latent_dao(conn):
    # un bersaglio col Dao del Destino: assorbendolo il giocatore lo risveglia
    ploc = conn.execute("SELECT location_id FROM players WHERE id=1;").fetchone()["location_id"]
    victim = conn.execute("SELECT id FROM npcs WHERE status='alive' LIMIT 1;").fetchone()["id"]
    conn.execute("UPDATE character_daos SET dao_key='destino', comprehension=90 WHERE character_type='npc' AND character_id=?;", (victim,))
    conn.execute("UPDATE npcs SET status='dead', death_tick=0, location_id=? WHERE id=?;", (ploc, victim))
    before = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=1 AND dao_key='destino';").fetchone()["comprehension"]
    assert before == 0
    # forza esito comprehension con seed favorevole
    for seed in range(30):
        conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (victim,))
        r = absorption.absorb(conn, tick=5, rng=random.Random(seed), target_id=victim)
        if r["status"] == "comprehension" and r.get("dao") == "destino":
            after = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=1 AND dao_key='destino';").fetchone()["comprehension"]
            assert after > 0      # risvegliato!
            # ora è allenabile
            assert dao_training.comprehend(conn, 0, random.Random(1), "destino")["status"] != "locked"
            return
