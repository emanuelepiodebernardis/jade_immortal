"""
TARATURA — una partita automatica di N giorni, con la misura di scontri, imboscate, morti e scene.

Uso (dalla cartella del gioco):
    python strumenti/taratura.py <origine> <seme> <giorni> <uscita.json>
    python strumenti/taratura_analisi.py strumenti/taratura_out/*.json

Il pilota automatico gioca con i comandi veri; un mondo nuovo per ogni seme, in una cartella a parte
(il tuo salvataggio non viene toccato). Le manopole da regolare stanno in engine/systems/calibration.py.
"""
import json, random, sys, time
from pathlib import Path as _P
sys.path.insert(0, str(_P(__file__).resolve().parent.parent))
from pathlib import Path
from engine import db
from engine.core import entities, tick
from engine.generators.world_gen import generate, WorldGenConfig
from engine.systems import character, encounters, state, captivity, autopilot, archrival, rankings
from engine.simulation import cultivation, combat
from engine.cli import loop, story_cmds
import engine.narrative.llm as llm
llm.load_llm_config = lambda path=None: {"enabled": False, "host": "", "model": ""}

origin, seed, days, outp = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
S = Path(__file__).resolve().parent / "taratura_out"
S.mkdir(exist_ok=True)
p = S / f"{origin}_{seed}.db"; p.unlink(missing_ok=True)
db.DB_PATH = p; db.init_db(p); c = db.connect(p)
generate(c, WorldGenConfig(seed=seed, factions=4, static_npc_count=40))
character.apply_origin(c, origin, random.Random(seed)); c.commit()
for cmd in ["attributi auto on", "auto imposta sfonda si", "auto imposta rischio 25", "auto imposta fermati reame no", "auto imposta fermati invasione no",
            "auto imposta fermati elemento no", "auto imposta fermati assemblea no",
            "profession " + random.Random(seed).choice(["alchimia", "forgia", "formazioni", "talismani"])]:
    loop.dispatch(c, cmd, allow_nl=False)
if origin == "divoratore":
    loop.dispatch(c, "auto imposta assorbi si", allow_nl=False)

# ---------------- strumentazione (Agg. 55): scontri, scene, fasi
from engine.systems import power as _pw, duel as _duel
FIGHTS, SCENE_LOG, PHASE_DAYS = [], [], {}
def _phase(tier):
    return "A(1-3)" if tier <= 3 else "B(4-6)" if tier <= 6 else "C(7-9)" if tier <= 9 else "D(10+)"
def _inj(cid_type, cid):
    return c.execute("SELECT COUNT(*) n FROM injuries WHERE character_type=? AND character_id=?", (cid_type, cid)).fetchone()["n"]
_orig_attack = loop._attack_auto
def _wrapped(conn, player, npc, forced):
    me = max(1, _pw.combat_rating(conn, "player", player.id)); en = _pw.combat_rating(conn, "npc", npc.id)
    ip, ie = _inj("player", player.id), _inj("npc", npc.id)
    kind = conn.execute("SELECT kind FROM npcs WHERE id=?", (npc.id,)).fetchone()["kind"] or "human"
    out = _orig_attack(conn, player, npc, forced)
    st = conn.execute("SELECT status FROM npcs WHERE id=?", (npc.id,)).fetchone()["status"]
    pst = entities.get_player(conn).status
    won = st != "alive" or _inj("npc", npc.id) > ie
    lost = pst != "alive" or _inj("player", player.id) > ip
    FIGHTS.append({"day": tick.get_tick(conn)//120, "phase": _phase(cultivation.realm_tier(conn, "player", player.id)),
                   "ratio": round(en / me, 3), "forced": bool(forced), "won": bool(won and not lost), "died": pst != "alive",
                   "kind": kind, "duel": False})
    return out
loop._attack_auto = _wrapped
_orig_rc = combat.resolve_combat
def _rc(conn, tk, rng_, atk, dfn, *a, **k):
    if "player" not in (atk[0], dfn[0]):
        return _orig_rc(conn, tk, rng_, atk, dfn, *a, **k)
    pid = atk[1] if atk[0] == "player" else dfn[1]
    other = dfn if atk[0] == "player" else atk
    me = max(1, _pw.combat_rating(conn, "player", pid)); en = _pw.combat_rating(conn, other[0], other[1])
    r = _orig_rc(conn, tk, rng_, atk, dfn, *a, **k)
    won = r["winner"][0] == "player"
    kind = conn.execute("SELECT kind FROM npcs WHERE id=?", (other[1],)).fetchone()
    FIGHTS.append({"day": tk // 120, "phase": _phase(cultivation.realm_tier(conn, "player", pid)), "ratio": round(en / me, 3),
                   "forced": atk[0] != "player", "won": won, "died": entities.get_player(conn).status != "alive",
                   "kind": "agguato:" + ((kind["kind"] if kind else None) or "human"), "duel": False})
    return r
combat.resolve_combat = _rc
LAST = [0]

rng = random.Random(seed * 7)
day = lambda: tick.get_tick(c) // 120
samples, deaths, stops, scenes = [], [], {}, {}
last_sample = -1
t0 = time.time()
guard = 0
while day() < days and guard < 6000:
    guard += 1
    pl = entities.get_player(c)
    if pl.status != "alive":
        ev = c.execute("SELECT summary FROM events WHERE summary LIKE '%te %' OR summary LIKE '%Tu %' "
                       "ORDER BY id DESC LIMIT 1").fetchone()
        deaths.append([day(), cultivation.realm_tier(c, "player", pl.id), (ev["summary"] if ev else "?")[:70]])
        from engine.systems import rebirth, encounters as _enc
        _enc.clear(c)
        row = rebirth.record_death(c, pl)
        opts = rebirth.inheritance_options(row)
        rebirth.reincarnate(c, random.Random(seed + len(deaths)), origin, None, opts[0] if opts else None)
        c.commit()
        if len(deaths) > 8:
            break
        continue
    _t = cultivation.realm_tier(c, "player", pl.id)
    PHASE_DAYS[_phase(_t)] = PHASE_DAYS.get(_phase(_t), 0) + (day() - LAST[0]); LAST[0] = day()
    dd = _duel.get(c)
    if dd and not encounters.pending(c):
        if not dd.get("_logged"):
            me = max(1, _pw.combat_rating(c, "player", pl.id)); en = _pw.combat_rating(c, "npc", dd["npc"])
            dd["_logged"] = True; dd["_ratio"] = round(en / me, 3); _duel._save(c, dd)
        r = loop.dispatch(c, "duello_azione 1", allow_nl=False) or ""
        d2 = _duel.get(c)
        if not d2 or d2.get("hp_e", 1) <= 0 or d2.get("hp_p", 1) <= 0:
            FIGHTS.append({"day": day(), "phase": _phase(_t), "ratio": dd.get("_ratio", 1), "forced": False,
                           "won": bool(d2 and d2.get("hp_e", 1) <= 0) or "crolla" in r, "died": entities.get_player(c).status != "alive",
                           "kind": "duel", "duel": True})
            if d2 and d2.get("hp_p", 1) <= 0:
                _duel.state.delete(c, _duel.KEY)
        story_cmds.after_command(c, entities.get_player(c)); c.commit(); continue
    sc = encounters.pending(c)
    if sc:
        k = (sc.get("key") or "?")
        SCENE_LOG.append([day(), _phase(_t), k])
        scenes[k] = scenes.get(k, 0) + 1
        chs = sc.get("choices", [])
        n = rng.randint(1, max(1, len(chs)))
        nid = (sc.get("ctx") or {}).get("npc_id")
        if nid and len(chs) > 1:
            from engine.systems import perception
            try:
                weak = perception.strength_ratio(c, 1, nid) < 0.9
            except Exception:
                weak = False
            if weak:    # un giocatore vero non affronta chi è più forte, se può evitarlo
                safe = [i for i, ch in enumerate(chs, 1) if not ch.get("command") and not any(
                    w in ch.get("label", "").lower() for w in ("affront", "combatt", "sfid", "attacc", "duello"))]
                if safe:
                    n = rng.choice(safe)
        loop.dispatch(c, str(n), allow_nl=False)
        story_cmds.after_command(c, entities.get_player(c)); c.commit(); continue
    if captivity.active(c):
        loop.dispatch(c, "evadi", allow_nl=False); continue
    out = loop.dispatch(c, f"auto {min(30, days - day())}", allow_nl=False) or ""
    if "sfondamento" in out and "si ferma" in out:
        bt = loop.dispatch(c, "breakthrough", allow_nl=False) or ""     # il giocatore decide di tentare
        if "Demone" in bt or encounters.pending(c):
            pass
    for ln in out.splitlines():
        if "si ferma:" in ln:
            r = ln.split("si ferma:")[1].strip()
            r = r.split("(")[0].split("«")[0].split(":")[0].strip()[:45]
            stops[r] = stops.get(r, 0) + 1
    story_cmds.after_command(c, entities.get_player(c)); c.commit()
    if day() // 50 != last_sample:
        last_sample = day() // 50
        pl = entities.get_player(c)
        cp = combat.combat_power(c, "player", pl.id)
        samples.append({"day": day(), "tier": cultivation.realm_tier(c, "player", pl.id),
                        "stage": (cultivation.get_record(c, "player", pl.id) or {"stage": 0})["stage"],
                        "atk": round(cp["attack"]), "def": round(cp["defense"]), "vit": round(cp["vitality"]),
                        "dao": c.execute("SELECT COALESCE(SUM(comprehension),0) s FROM character_daos WHERE "
                                         "character_type='player' AND character_id=?", (pl.id,)).fetchone()["s"]})
pl = entities.get_player(c)
from engine.systems import cult_mods, dao_training
mult, labels = cult_mods.cultivation_mult(c, pl.id, pl.location_id)
ar = archrival.get(c) or {}
res = {"origin": origin, "seed": seed, "days": day(), "deaths": deaths, "samples": samples, "stops": stops,
       "scenes": scenes, "cult_mult": round(mult, 2), "cult_labels": labels,
       "dao_power": round(dao_training.dao_power(c, "player", pl.id), 2),
       "dao_factor": round(dao_training.combat_dao_factor(c, "player", pl.id), 2),
       "archrival": {k: ar.get(k) for k in ("gen", "wins", "losses", "level")},
       "titles": state.titles(c), "kills": state.get_int(c, "kills_total", 0),
       "plot": state.get_json(c, "master_plot", {}).get("done", []),
       "secs": round(time.time() - t0)}
from engine.systems import attributes, deep_dao, dao_spirits, frontier, pursuers, ascension
res["extra"] = {"attr": attributes.allocated(c), "combat_mults": {k: round(v, 2) for k, v in attributes.combat_mults(c).items()},
    "seal_mult": round(deep_dao.seal_mult(c), 2), "spirits": len(dao_spirits.spirits(c, pl.id)),
    "rings": frontier.world(c, ascension.player_layer(c, pl.id))["rings"], "layer": ascension.player_layer(c, pl.id),
    "pursuers": [[k, round(pursuers.ratio(c, pl.id, n), 2)] for n, k in pursuers.tracked(c)][:8],
    "power": round(__import__("engine.systems.power", fromlist=["x"]).combat_rating(c, "player", pl.id))}
res["fights"] = FIGHTS
res["scene_log"] = SCENE_LOG
res["phase_days"] = PHASE_DAYS
from engine.systems import intrigues as _intr
res["intrigues"] = [[x["key"], x["outcome"], x["day"]] for x in _intr.get(c)["done"]]
Path(outp).write_text(json.dumps(res, ensure_ascii=False))
print(origin, seed, "days", day(), "deaths", deaths, "secs", res["secs"])
