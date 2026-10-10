"""
RITIRO A PORTE CHIUSE (闭关), ILLUMINAZIONI e VITTORIE AL LIMITE.

  ritiro <giorni> [dao]
      Ti chiudi a coltivare per più giorni di fila, senza la fatica delle sessioni brevi.
      Si può fare solo in un luogo adatto: la sede della tua setta, la tua grotta-dimora,
      una montagna, delle rovine o una zona proibita. Gli anni passano davvero (la vita
      si accorcia), il mondo va avanti senza di te, e qualcuno può venire a disturbarti.
      Se indichi un Dao, ne mediti anche la comprensione.
      Il ritiro si interrompe da solo quando sei al colmo dello Strato 10.

  Illuminazione improvvisa (顿悟)
      Durante il ritiro, dopo una vittoria contro chi era più forte di te o in un reame
      segreto, a volte la mente si apre: un balzo di comprensione del Dao e di Qi.

  Vittorie al limite
      Battere un avversario più forte porta fama, titoli e la possibilità di un'illuminazione.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import state

MAX_DAYS = 120
_SPOT_TYPES = ("mountain", "ruin", "forbidden_zone")


def _place_ok(conn, player) -> tuple[bool, str]:
    from engine.systems import sects, cave_abode
    if cave_abode.is_home(conn, player.id, player.location_id):
        return True, "nella tua grotta-dimora"
    m = sects.get_membership(conn, player.id)
    if m:
        hq = conn.execute("SELECT home_location_id FROM factions WHERE id=?;",
                          (m["faction_id"],)).fetchone()
        if hq and hq["home_location_id"] == player.location_id:
            return True, "nelle stanze di meditazione della setta"
    lt = conn.execute("SELECT location_type FROM locations WHERE id=?;",
                      (player.location_id,)).fetchone()
    if lt and lt["location_type"] in _SPOT_TYPES:
        return True, "in un anfratto isolato"
    return False, ""


def illumination(conn, t: int, rng: random.Random, player, source: str,
                 dao_key: str | None = None) -> list[str]:
    """Un'illuminazione improvvisa: balzo nel Dao (quello indicato o il più profondo)."""
    from engine.systems import dao_training, items
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    rows = dao_training.trainable_daos(conn, player.id)
    if not dao_key and rows:
        dao_key = rows[0]["dao_key"] if rng.random() < 0.6 else rng.choice(rows)["dao_key"]
    lines = [f"✦ ILLUMINAZIONE ({source}) ✦ Per un istante vedi la trama del mondo."]
    eff = {"cultivation_progress": round(0.2 + 0.05 * tier, 2)}
    if dao_key:
        eff.update({"dao_key": dao_key, "dao_gain": 8 + 4 * tier + rng.randint(0, 6)})
    lines += items.apply_effects(conn, t, rng, player.id, eff)
    n = state.get_int(conn, "illuminations", 0) + 1
    state.set(conn, "illuminations", str(n))
    if n in (1, 5, 20, 100):
        title = {1: "Colui che Ha Visto", 5: "Mente Illuminata",
                 20: "Saggio dell'Illuminazione", 100: "Specchio del Cielo"}[n]
        if state.grant_title(conn, title):
            lines.append(f"✧ Nuovo titolo: «{title}» ✧")
    return lines


def on_upset_win(conn, t: int, rng: random.Random, player, npc_name: str, ratio: float) -> list[str]:
    """Hai battuto chi era più forte di te (ratio = tua forza / sua forza, < 0.87)."""
    from engine.systems import reputation
    lines = []
    fame = 4 if ratio >= 0.6 else 10
    reputation.adjust(conn, player.id, fame=fame)
    n = state.get_int(conn, "upset_wins", 0) + 1
    state.set(conn, "upset_wins", str(n))
    lines.append(f"Hai sconfitto {npc_name}, più forte di te: chi ha visto non lo dimenticherà.")
    titles = {1: "Sfidante dei Cieli", 10: "Colui che Rovescia il Destino",
              50: "Flagello dei Più Forti", 200: "Leggenda Contro Corrente"}
    if n in titles and state.grant_title(conn, titles[n]):
        lines.append(f"✧ Nuovo titolo: «{titles[n]}» ✧")
    if rng.random() < (0.30 if ratio >= 0.6 else 0.6):
        lines += illumination(conn, t, rng, player, "nel cuore della battaglia")
    return lines


def retreat(conn: sqlite3.Connection, player, arg: str) -> str:
    from engine.systems import encounters, dao_training, training, lifespan, cult_mods
    from engine.simulation import cultivation, world_tick
    parts = arg.split(maxsplit=1)
    if not parts or not parts[0].isdigit():
        return ("Usa: ritiro <giorni> [dao]  (es. 'ritiro 10' o 'ritiro 30 spada'). "
                f"Massimo {MAX_DAYS} giorni per volta.")
    if encounters.pending(conn):
        return "Prima risolvi l'incontro in corso."
    days = max(1, min(MAX_DAYS, int(parts[0])))
    ok, where = _place_ok(conn, player)
    if not ok:
        return ("Qui c'è troppo trambusto per un ritiro. Serve la sede della tua setta, la tua "
                "grotta-dimora, oppure una montagna, delle rovine o una zona proibita.")
    dao_key, dao_name = None, None
    if len(parts) > 1:
        row = dao_training.find_dao(conn, parts[1], player.id)
        if row is None or (not row["practiced"] and row["comprehension"] == 0):
            return f"Non conosci un Dao '{parts[1]}' da meditare. ('dao' per i tuoi Dao)"
        dao_key, dao_name = row["dao_key"], row["name"]
    rec0 = cultivation.get_record(conn, "player", player.id)
    st0 = rec0["stage"] or 1
    lbl0 = cultivation.realm_label(conn, "player", player.id)
    sect_bonus = training.location_bonus(conn, player.id, player.location_id)
    mult, labels = cult_mods.cultivation_mult(conn, player.id, player.location_id, seclusion=True)
    dao_gain = 0
    lines = [f"Ti chiudi in ritiro {where}" + (f", meditando il Dao «{dao_name}»" if dao_name else "") + "."]
    if labels:
        lines.append("Favoriscono il ritiro: " + ", ".join(labels) + ".")
    done = 0
    events: list[str] = []
    base_seed = tick_mod.get_tick(conn)
    for d in range(days):
        t = tick_mod.get_tick(conn)
        rng = random.Random(base_seed * 7 + d * 131 + player.id)
        res = cultivation.cultivate(conn, "player", player.id, t, rng,
                                    multiplier=3.0 * (1 + sect_bonus) * mult)
        if dao_key:
            r = dao_training.comprehend(conn, t, rng, dao_key,
                                        multiplier=2.0 * cult_mods.dao_mult(conn, player.id, dao_key),
                                        player_id=player.id)
            if r.get("status") == "ok":
                dao_gain += r["gain"]
                if r.get("unlocked"):
                    events.append(f"Giorno {d + 1}: nel Dao si schiude una tecnica — {r['unlocked']}!")
        world_tick.advance(conn, training.DAY_TICKS)
        done += 1
        p = entities.get_player(conn)
        lines_life = lifespan.daily_check(conn, p, tick_mod.get_tick(conn))
        p = entities.get_player(conn)
        if p.status != "alive":
            events += lines_life
            break
        if rng.random() < 0.03 + 0.002 * min(50, days):
            events.append(f"Giorno {d + 1}:")
            events += ["  " + x for x in illumination(conn, t, rng, p, "nel silenzio del ritiro", dao_key)]
        from engine.systems import cave_abode
        if rng.random() < 0.02 * cave_abode.disturb_factor(conn, player.id, player.location_id):
            events.append(f"Giorno {d + 1}: passi fuori dalla tua stanza, una voce che chiama il tuo nome. "
                          "Il ritiro è interrotto.")
            from engine.systems import bonds
            nems = [n for n in bonds.nemeses(conn, player.id) if n["npc_status"] == "alive"]
            if nems:
                conn.execute("UPDATE npcs SET location_id=? WHERE id=?;",
                             (player.location_id, nems[0]["npc_id"]))
                txt = encounters.start_scene(conn, p, bonds.nemesis_scene(conn, nems[0]))
                if txt:
                    events.append(txt)
            break
        if res.get("ready"):
            events.append(f"Giorno {d + 1}: sei al colmo dello Strato 10. Esci dal ritiro: "
                          "è tempo di 'breakthrough'.")
            break
    rec = cultivation.get_record(conn, "player", player.id)
    lines.append(f"Dopo {done} giorni: {lbl0} → {cultivation.realm_label(conn, 'player', player.id)} "
                 f"(esperienza {rec['progress'] * 100:.0f}%).")
    if (rec["stage"] or 1) > st0:
        lines.append(f"Hai superato {(rec['stage'] or 1) - st0} strati.")
    if dao_gain:
        lines.append(f"Comprensione del Dao «{dao_name}»: +{dao_gain}.")
    lines += events
    age = lifespan.age_years(conn, player.id)
    lines.append(f"Hai ora {int(age)} anni (su {lifespan.max_years(conn, player.id)}).")
    from engine.systems import weapon_spirit
    lines += weapon_spirit.on_days(conn, entities.get_player(conn), done)
    from engine.systems import qi as qimod, spirit as spmod
    qimod.restore_full(conn, player.id)
    spmod.restore_full(conn, player.id)
    return "\n".join(lines)
