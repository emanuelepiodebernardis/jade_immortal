"""
INCONTRI A SCELTA (奇遇) — mini-scene con 2–4 opzioni.

Ispirati alle "carte scelta" delle storie interattive e agli incontri fortuiti dei
giochi di coltivazione. Regola d'oro (Factual Lock): l'ESITO lo decide il motore,
in modo deterministico dato l'rng, con una PROVA sulle tue qualità reali
(affinità, regno, karma, Dao del Destino). Il testo è scritto a mano; l'LLM, se
presente, non entra in gioco qui.

Ogni scelta può avere:
  - check: {"stat": <corpo|anima|qi|coltivazione|istinto|fortuna|karma>, "dc": int}
  - success / failure: dizionari di EFFETTI (vedi apply_effects), oppure
  - effects: effetti senza prova
  - command: un comando di gioco da eseguire (es. combattere)
Le scene possono anche essere create da altri sistemi (nemesi, storia personale)
con `start_scene`.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import state

PENDING_KEY = "encounter_pending"
LAST_KEY = "encounter_last_tick"
SEEN_KEY = "encounter_seen"
MIN_GAP = 30                  # tick minimi tra due incontri casuali
BASE_CHANCE = 0.10            # probabilità per spostamento (+ pericolo, max 30%)

STAT_LABEL = {"corpo": "Corpo", "anima": "Anima", "qi": "Qi", "coltivazione": "Talento",
              "istinto": "Istinto", "fortuna": "Fortuna", "karma": "Karma",
              "potenza": "Potenza"}


# ============================================================
# Stato in sospeso
# ============================================================

def pending(conn: sqlite3.Connection) -> dict | None:
    return state.get_json(conn, PENDING_KEY)


def clear(conn: sqlite3.Connection) -> None:
    state.delete(conn, PENDING_KEY)


def start_scene(conn: sqlite3.Connection, player: entities.Player, scene: dict,
                force: bool = False) -> str | None:
    """Mette in sospeso una scena (dict con title, text, choices, ctx). Ritorna il testo
    da mostrare, o None se c'è già un'altra scena aperta (e force=False)."""
    if pending(conn) and not force:
        return None
    if not force:
        from engine.systems import director
        if not director.gate(conn, scene):
            return None                      # il regista la rimanda (o, se è presto, non accade)
    sc = dict(scene)
    sc.setdefault("ctx", {})
    sc["location_id"] = player.location_id
    sc["tick"] = tick_mod.get_tick(conn)
    # il personaggio della scena esiste DA SUBITO: puoi valutarne la forza prima di scegliere
    if sc.get("spawn") and not sc["ctx"].get("npc_id"):
        rng = random.Random(sc["tick"] * 7577 + player.id)
        _spawn_ctx_npc(conn, rng, player, sc["ctx"], sc["spawn"], sc["tick"])
    state.set_json(conn, PENDING_KEY, sc)
    return render(conn, player, sc)


def dismiss_if_moved(conn: sqlite3.Connection, player: entities.Player) -> str | None:
    sc = pending(conn)
    if not sc or sc.get("location_id") == player.location_id:
        return None
    if sc.get("sticky"):                     # i capitoli della tua storia ti seguono
        sc["location_id"] = player.location_id
        state.set_json(conn, PENDING_KEY, sc)
        return None
    clear(conn)
    if sc.get("on_leave"):
        return sc["on_leave"]
    return f"(Ti allontani: l'occasione — «{sc.get('title', 'incontro')}» — svanisce.)"


# ============================================================
# Prove
# ============================================================

def _extra_fortune(conn) -> int:
    from engine.systems import lost_legacy, gu
    return lost_legacy.fortune_bonus(conn) + gu.fortune_bonus(conn)


def stat_value(conn: sqlite3.Connection, player_id: int, stat: str) -> int:
    from engine.systems import character, karma, dao_powers
    from engine.simulation import cultivation
    p = character.get_profile(conn, "player", player_id)
    col = {"corpo": "aff_body", "anima": "aff_soul", "qi": "aff_qi",
           "coltivazione": "aff_cultivation", "istinto": "aff_combat"}.get(stat)
    tier = cultivation.realm_tier(conn, "player", player_id) or 1
    if col:
        base = (p[col] if p and p[col] is not None else 50)
        return int(base + tier * 4)
    if stat == "fortuna":
        from engine.systems import destinies
        k = karma.get_karma(conn, "player", player_id)
        return int(45 + dao_powers.fate_idx(conn, player_id) * 12 + max(-30, min(30, k // 10))
                   + int(destinies.flag_value(conn, "fortune", player_id, 0))
                   + _extra_fortune(conn))
    if stat == "karma":
        return int(50 + max(-50, min(50, karma.get_karma(conn, "player", player_id) // 4)))
    if stat == "potenza":
        aff = (p["aff_combat"] if p and p["aff_combat"] is not None else 50)
        return int(aff * 0.5 + tier * 14)
    return 50


def chance(value: int, dc: int) -> float:
    """P(value + U[0,40] >= dc)."""
    return max(0.0, min(1.0, (value + 41 - dc) / 41.0))


def chance_word(p: float) -> str:
    if p >= 0.95:
        return "sicura"
    if p >= 0.65:
        return "favorevole"
    if p >= 0.35:
        return "incerta"
    if p >= 0.08:
        return "rischiosa"
    return "disperata"


def roll(conn, rng, player_id, check: dict) -> tuple[bool, int, int]:
    v = stat_value(conn, player_id, check.get("stat", "fortuna"))
    r = rng.randint(0, 40)
    return (v + r >= int(check.get("dc", 60)), v, r)


# ============================================================
# Rendering
# ============================================================

def render(conn: sqlite3.Connection, player: entities.Player, sc: dict | None = None) -> str:
    sc = sc or pending(conn)
    if not sc:
        return "Nessun incontro in corso."
    lines = [f"✦ {sc.get('title', 'Incontro')} ✦", sc.get("text", "")]
    for i, ch in enumerate(sc.get("choices", []), 1):
        hint = ""
        chk = ch.get("check")
        if chk:
            p = chance(stat_value(conn, player.id, chk.get("stat", "fortuna")), int(chk.get("dc", 60)))
            from engine.systems import destinies
            word = (f"{int(round(p * 100))}%" if destinies.flag_value(conn, "heaven_eyes", player.id, False)
                    else chance_word(p))
            hint = f"  [{STAT_LABEL.get(chk.get('stat'), chk.get('stat'))}: {word}]"
        cmd = ch.get("command") or ""
        if cmd.startswith("attack") and sc.get("ctx", {}).get("npc_id"):
            from engine.systems import perception
            rel = perception.relative_strength(conn, player.id, sc["ctx"]["npc_id"])
            hint += f"  [scontro all'ultimo sangue: ti sembra {rel}]"
        lines.append(f"  [{i}] {ch['label']}{hint}")
    lines.append("(scrivi il numero della tua scelta)")
    return "\n".join(ln for ln in lines if ln is not None)


# ============================================================
# Effetti
# ============================================================

def _ctx_npc(conn, ctx) -> entities.NPC | None:
    nid = ctx.get("npc_id")
    return entities.get_npc(conn, nid) if nid else None


def _spawn_ctx_npc(conn, rng, player, ctx, spec: dict, t: int) -> int:
    from engine.systems import npc_factory
    if ctx.get("npc_id"):                      # già creato a livello di scena
        return ctx["npc_id"]
    from engine.simulation import cultivation
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    tier = max(1, ptier + int(spec.get("tier_offset", 0)))
    loc = player.location_id
    for _ in range(int(spec.get("hops", 0))):           # lontano: va cercato
        ex = entities.get_exits(conn, loc)
        if not ex:
            break
        loc = rng.choice(sorted(ex.values()))
    nid = npc_factory.spawn(
        conn, rng, archetype=spec.get("archetype", "vagabondo"),
        location_id=loc, tier=tier, stage=spec.get("stage"),
        name=ctx.get("npc_name"), dao=spec.get("dao"), traits=spec.get("traits"), tick=t)
    ctx["npc_id"] = nid
    if spec.get("role"):
        from engine.systems import storyline
        storyline.remember_npc(conn, spec["role"], nid)
    return nid


def apply_effects(conn: sqlite3.Connection, t: int, rng: random.Random,
                  player: entities.Player, eff: dict, ctx: dict) -> list[str]:
    """Applica un dizionario di effetti. Ritorna righe descrittive."""
    from engine.systems import (items, reputation, karma, sects, relations, bonds,
                                guild, character)
    lines: list[str] = []
    eff = dict(eff or {})
    for ln in eff.get("text", []) if isinstance(eff.get("text"), list) else (
            [eff["text"]] if eff.get("text") else []):
        lines.append(ln.format(**_fmt(ctx)))

    if eff.get("spawn"):
        _spawn_ctx_npc(conn, rng, player, ctx, eff["spawn"], t)

    # effetti "da oggetto" (riusa items.apply_effects: progressi, Dao, corpo, tecniche, pietre)
    gift = {}
    for k in ("cultivation_progress", "dao_key", "dao_gain", "grow_strength", "grow_vitality",
              "grow_resistance", "grow_aura", "grow_soul", "aff_cultivation", "learn_technique",
              "gongfa", "root_gain"):
        if k in eff:
            gift[k] = eff[k]
    if gift.get("dao_key") == "random":
        from engine.systems import dao_training
        rows = dao_training.trainable_daos(conn, player.id)
        gift["dao_key"] = rng.choice([r["dao_key"] for r in rows]) if rows else "corpo"
    if gift:
        lines += items.apply_effects(conn, t, rng, player.id, gift)

    st = int(eff.get("stones", 0) or 0)
    if st > 0:
        total = sects.grant_resource(conn, "pietre_spirituali", st, player.id)
        lines.append(f"+{st} pietre spirituali (totale: {total}).")
    elif st < 0:
        have = sects.get_resource(conn, "pietre_spirituali", player.id)
        take = min(have, -st)
        if take:
            sects.grant_resource(conn, "pietre_spirituali", -take, player.id)
            lines.append(f"-{take} pietre spirituali.")

    if eff.get("item"):
        it = eff["item"]
        iid = items.create_item(conn, it["name"], it.get("item_type", "pillola"),
                                it.get("rarity", "non_comune"), it.get("desc", ""),
                                it.get("effects", {}))
        items.grant(conn, "player", player.id, iid)
        lines.append(f"Ottieni: {it['name']} (nello zaino — 'use').")

    fame, infamy, susp = (int(eff.get("fame", 0)), int(eff.get("infamy", 0)),
                          int(eff.get("suspicion", 0)))
    if fame or infamy or susp:
        reputation.adjust(conn, player.id, fame=fame, infamy=infamy, suspicion=susp)
        if fame > 0:
            lines.append("La voce delle tue gesta si diffonde.")
        if infamy > 0:
            lines.append("Qualcuno ha visto: il tuo nome ne esce macchiato.")

    kd = int(eff.get("karma", 0) or 0)
    if kd:
        karma.adjust_karma(conn, "player", player.id, kd, ctx.get("title", "incontro"), t)

    inj = int(eff.get("injury", 0) or 0)
    if inj:
        conn.execute(
            "INSERT INTO injuries (character_type, character_id, severity, description, "
            "inflicted_tick, healed, heal_tick) VALUES ('player', ?, ?, ?, ?, 0, ?);",
            (player.id, inj, eff.get("injury_desc", "ferita da un incontro"), t, t + inj * 15))
        lines.append("Ne esci ferito." if inj < 5 else "Ne esci gravemente ferito.")

    if eff.get("qi_full"):
        from engine.systems import qi as qimod, spirit as spmod
        qimod.restore_full(conn, player.id)
        spmod.restore_full(conn, player.id)
        lines.append("Qi e spirito ti tornano colmi.")

    res = int(eff.get("residue", 0) or 0)
    if res:
        p = character.get_profile(conn, "player", player.id)
        if p and p["anomaly"] == "abisso_divoratore":
            conn.execute(
                "UPDATE character_profiles SET soul_residue=MAX(0, soul_residue+?) "
                "WHERE character_type='player' AND character_id=?;", (res, player.id))
            lines.append("L'Abisso si nutre: la corruzione cresce." if res > 0
                         else "Un poco della corruzione dell'Abisso si dissolve.")

    for aff_key, col in (("aff_soul", "aff_soul"), ("aff_body", "aff_body"),
                         ("aff_qi", "aff_qi"), ("aff_combat", "aff_combat")):
        d = int(eff.get(aff_key, 0) or 0)
        if d:
            conn.execute(
                f"UPDATE character_profiles SET {col}=MAX(1, MIN(100, {col}+?)) "
                "WHERE character_type='player' AND character_id=?;", (d, player.id))
            word = {"aff_soul": "anima", "aff_body": "corpo", "aff_qi": "qi",
                    "aff_combat": "istinto"}[aff_key]
            lines.append(f"Qualcosa cambia nel profondo: la tua affinità di {word} "
                         f"{'si rafforza' if d > 0 else 'si incrina'}.")

    m = int(eff.get("merit", 0) or 0)
    if m and sects.get_membership(conn, player.id):
        guild.add_merit(conn, m, player.id)
        lines.append(f"Merito della setta +{m}.")

    npc = _ctx_npc(conn, ctx)
    if eff.get("dlg_request"):
        from engine.systems import dialogues
        lines.append(dialogues.make_request(conn, player, int(eff["dlg_request"])))
    if npc and (eff.get("relation") or eff.get("bond")):
        from engine.systems import echoes
        echoes.on_choice(conn, ctx, eff, ctx.get("title", "un incontro"))
    if npc and eff.get("relation"):
        d = relations.adjust(conn, npc.id, int(eff["relation"]), t, player.id)
        lines.append(f"{npc.name}: {_rel_word(d.relationship_type)}.")
    if npc and eff.get("bond"):
        msg = bonds.add_bond(conn, player.id, npc.id, eff["bond"], t, rng=rng,
                             reason=eff.get("bond_reason", ctx.get("title", "")))
        if msg:
            lines.append(msg)
    if eff.get("master_learn"):
        from engine.systems import secret_masters
        lines += secret_masters.learn(conn, t, player, eff["master_learn"], eff.get("gift"))
    if eff.get("bt_bonus"):
        from engine.systems import heart_demon
        heart_demon.add_bonus(conn, float(eff["bt_bonus"]))
    if eff.get("inner_demon"):
        from engine.systems import heart_demon
        msg = heart_demon.spawn_demon(conn, player, t)
        if msg:
            lines.append(msg)
    if eff.get("lifespan_years"):
        from engine.systems import lifespan
        lifespan.add_bonus_years(conn, int(eff["lifespan_years"]))
        _y = int(eff['lifespan_years'])
        lines.append(f"La tua vita si allunga di {_y} anni." if _y > 0
                     else f"La tua vita si accorcia di {-_y} anni.")
    if npc and eff.get("end_bond"):
        bonds.end_bond(conn, player.id, npc.id, eff["end_bond"], "riconciliata")
    if npc and eff.get("bond_delay"):
        bonds.delay_nemesis(conn, player.id, npc.id, int(eff["bond_delay"]))
    if npc and eff.get("outlaw"):
        reward = int(eff["outlaw"])
        conn.execute("INSERT OR IGNORE INTO outlaws (npc_id, crime, reward, notoriety) "
                     "VALUES (?, ?, ?, 2);", (npc.id, eff.get("crime", "ha tradito la fiducia"), reward))
        lines.append(f"Su {npc.name} ora pende una taglia di {reward} pietre.")
    if npc and eff.get("npc_leaves"):
        conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (npc.id,))
    # uccidere o risparmiare dentro una scena: le stesse conseguenze del combattimento
    if npc and eff.get("npc_dies"):
        from engine.systems import feuds, dao_superiori
        lines += feuds.on_kill(conn, t, rng, player, npc)
        conn.execute("UPDATE npcs SET status='dead' WHERE id=?;", (npc.id,))
        dao_superiori.on_kill(conn, "human")
    if npc and eff.get("spared"):
        from engine.systems import feuds
        lines += feuds.on_spare(conn, t, rng, player, npc, chosen=True)
    if eff.get("prize"):                          # premi generati (torneo, eredità, gratitudine…)
        from engine.systems import rewards
        lines += rewards.grant(conn, rng, player, **eff["prize"])

    if any(k in eff for k in ("face_duel", "face_humiliate", "feud_end", "feud_win")):
        from engine.systems import face
        lines += face.apply(conn, t, rng, player, eff, ctx)
    if any(k in eff for k in ("plot_flag", "plot_flag2", "plot_choice", "plot_vow", "plot_duel", "imprison",
                              "dao_law", "race_all")):
        from engine.systems import master_plot
        lines += master_plot.apply_effect(conn, t, rng, player, eff, ctx)
    if eff.get("escape_step"):
        from engine.systems import captivity
        captivity.set_step(conn, int(eff["escape_step"]))
    if eff.get("escape_ally") and ctx.get("npc_id"):
        from engine.systems import captivity
        captivity.set_ally(conn, ctx["npc_id"])
    if eff.get("escape_free"):
        from engine.systems import captivity
        lines += captivity.free(conn, player)
    if eff.get("kingdom_favor"):
        from engine.systems import kingdoms
        rk, n = eff["kingdom_favor"]
        lines += kingdoms.add_favor(conn, str(rk), int(n))
    if eff.get("race_honor"):
        from engine.systems import races
        k, rel, hon = eff["race_honor"]
        lines += races.adjust(conn, k, rel=int(rel) // 4, honor=int(rel)) + (races.adjust(conn, k, rel=int(hon)) if hon else [])
    if eff.get("calamity_wave"):
        from engine.systems import eras
        lines += eras.wave_won(conn)
    if eff.get("mentor_ring"):
        from engine.systems import mentor_ring
        lines += mentor_ring.awaken(conn, rng)
    if eff.get("inner_space"):
        from engine.systems import inner_space
        if inner_space.get(conn):
            d = inner_space.get(conn)
            d["level"] += 1
            inner_space._save(conn, d)
            lines.append(f"La terra della bottiglietta si fonde col tuo spazio interiore: livello {d['level']}.")
        else:
            lines.append(inner_space.grant(conn))
    if eff.get("celestial_guard") and ctx.get("npc_id"):
        from engine.systems import celestial_elements
        celestial_elements.set_guard(conn, ctx["npc_id"])
    if eff.get("celestial_free"):
        from engine.systems import celestial_elements
        celestial_elements.set_free(conn)
    if eff.get("quest_done"):
        from engine.systems import npc_quests
        npc_quests.mark_done(conn, int(eff["quest_done"]))
    if eff.get("quest_target") and ctx.get("npc_id"):
        from engine.systems import npc_quests
        npc_quests.set_target(conn, int(eff["quest_target"]), ctx["npc_id"])
    if eff.get("intrigue") is not None and ctx.get("intrigue_id"):
        from engine.systems import intrigues
        ctx["_text"] = eff.get("text") if isinstance(eff.get("text"), str) else ""
        lines += intrigues.on_effect(conn, t, rng, player, eff["intrigue"], ctx)
    if eff.get("heart"):
        from engine.systems import dao_heart
        lines += dao_heart.adjust(conn, int(eff["heart"]))
    if eff.get("sect_influence"):
        from engine.systems import own_sect
        own_sect.add_influence(conn, int(eff["sect_influence"]))
    if eff.get("realm_done"):
        from engine.systems import secret_realms
        secret_realms.on_done(conn)
        lines.append("Il reame ha dato ciò che aveva da dare: la corrente ti riporta in superficie.")
    for fl in eff.get("flags", []) or []:
        from engine.systems import storyline
        storyline.set_flag(conn, fl)
    if eff.get("title"):
        if state.grant_title(conn, eff["title"]):
            lines.append(f"✧ Nuovo titolo: «{eff['title']}» ✧")
    return lines


def _common_spawn(choices: list[dict]) -> dict | None:
    """Se OGNI scelta fa comparire lo stesso personaggio, lo si crea già all'inizio della
    scena (così puoi esaminarlo e valutarne la forza prima di decidere)."""
    specs = []
    for ch in choices:
        found = None
        for br in (ch.get("effects"), ch.get("success"), ch.get("failure")):
            if br and br.get("spawn"):
                found = br["spawn"]
                break
        if found is None:
            return None
        specs.append(found)
    if specs and all(sp.get("archetype") == specs[0].get("archetype") for sp in specs):
        return specs[0]
    return None


def format_scene(scene: dict, ctx: dict) -> dict:
    """Sostituisce {npc}/{luogo}/... nel testo e nelle etichette delle scelte."""
    f = _fmt(ctx)
    out = dict(scene)
    out["ctx"] = ctx
    if "spawn" not in out:
        hoisted = _common_spawn(scene.get("choices", []))
        if hoisted:
            out["spawn"] = hoisted
    out["text"] = scene.get("text", "").format(**f)
    out["choices"] = [dict(c, label=c["label"].format(**f)) for c in scene.get("choices", [])]
    return out


def _rel_word(rt: str) -> str:
    return {"friend": "ora ti considera un amico", "acquaintance": "ti guarda con simpatia",
            "stranger": "resta distante", "rival": "ti considera un rivale",
            "enemy": "ti è ostile"}.get(rt, rt)


def _fmt(ctx: dict) -> dict:
    d = {"npc": ctx.get("npc_name", "lo sconosciuto"), "luogo": ctx.get("luogo", "qui")}
    d.update({k: v for k, v in ctx.items() if isinstance(v, (str, int))})
    return d


# ============================================================
# Scelta
# ============================================================

def choose(conn: sqlite3.Connection, player: entities.Player, n: int) -> tuple[str, str | None]:
    """Risolve la scelta n (1-based). Ritorna (testo, comando_da_eseguire|None)."""
    sc = pending(conn)
    if not sc:
        return "Nessun incontro in corso.", None
    choices = sc.get("choices", [])
    if not (1 <= n <= len(choices)):
        return f"Scegli un numero tra 1 e {len(choices)}.", None
    ch = choices[n - 1]
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 4243 + n * 17 + player.id + (sc.get("tick") or 0))
    ctx = sc.get("ctx", {})
    ctx.setdefault("title", sc.get("title", "incontro"))
    ctx["_choice"] = ch["label"]                 # (le trame tengono il diario delle tue scelte)
    clear(conn)
    lines = [f"» {ch['label']}"]
    if ch.get("check"):
        ok, _v, _r = roll(conn, rng, player.id, ch["check"])
        branch = ch.get("success" if ok else "failure", {}) or {}
        from engine.narrative import varia
        lines.append(varia.outcome(ok, rng))
    else:
        branch = ch.get("effects", {}) or {}
    lines += apply_effects(conn, t, rng, player, branch, ctx)
    _log(conn, t, player, sc, ch)
    if branch.get("then"):
        raw = dict(branch["then"])
        spec = raw.pop("spawn", None)
        if spec and (raw.pop("respawn", False) or not ctx.get("npc_id")):
            ctx.pop("npc_id", None)               # un nuovo personaggio entra in scena: prima nasce, poi si racconta
            from engine.systems import npc_factory
            ctx["npc_name"] = npc_factory.unique_name(rng, conn=conn)
            _spawn_ctx_npc(conn, rng, player, ctx, spec, t)
        nxt = format_scene(raw, ctx)
        nxt.pop("spawn", None)
        txt = start_scene(conn, player, nxt, force=True)
        if txt:
            lines.append("")
            lines.append(txt)
    cmd = ch.get("command") or branch.get("command")
    if cmd:
        cmd = cmd.format(**_fmt(ctx))
    return "\n".join(lines), cmd


def _log(conn, t, player, sc, ch) -> None:
    from engine.simulation import event_system as ev
    etype = sc.get("event_type", "fortune")
    if etype in ("story", "bond") or (sc.get("key") or "").startswith(("trama", "eco", "dialogo")):
        from engine.systems import chronicle
        chronicle.add(conn, "storia" if etype == "story" else "scelta",
                      f"{sc.get('title', 'Incontro')}: {ch['label'].rstrip('.')}.")
    try:
        ev.log_event(
            conn, event_type=etype, tick=t, location_id=player.location_id,
            title=sc.get("title", "Incontro"),
            summary=f"{sc.get('title', 'Incontro')}: {ch['label'].rstrip('.')}.",
            participants=[ev.Participant("player", player.id, "initiator")],
            consequences=[ev.Consequence("player", player.id, "choice", ch["label"],
                                         visibility="public", resolve_tick=t)])
    except Exception:
        pass


# ============================================================
# Incontri casuali
# ============================================================

def _eligible(conn, player, enc: dict, loc, seen: dict, t: int) -> bool:
    from engine.systems import character, sects
    from engine.simulation import cultivation
    req = enc.get("req", {})
    if loc is None:
        return False
    if req.get("types") and loc.location_type not in req["types"]:
        return False
    if loc.danger_level < req.get("danger_min", 0) or loc.danger_level > req.get("danger_max", 9):
        return False
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    if tier < req.get("tier_min", 0) or tier > req.get("tier_max", 999):
        return False
    prof = character.get_profile(conn, "player", player.id)
    if req.get("anomaly") and (not prof or prof["anomaly"] != req["anomaly"]):
        return False
    if req.get("in_sect") is not None and bool(sects.get_membership(conn, player.id)) != req["in_sect"]:
        return False
    if req.get("dao"):
        row = conn.execute("SELECT 1 FROM character_daos WHERE character_type='player' "
                           "AND character_id=? AND dao_key=? AND practiced=1;",
                           (player.id, req["dao"])).fetchone()
        if not row:
            return False
    last = seen.get(enc["key"])
    if last is not None and (enc.get("once") or t - int(last) < enc.get("repeat_gap", 1200)):
        return False
    return True


def maybe_trigger(conn: sqlite3.Connection, player: entities.Player,
                  rng: random.Random | None = None, force_key: str | None = None) -> str | None:
    """Dopo uno spostamento, a volte capita qualcosa. Ritorna il testo della scena o None."""
    from engine.systems.encounter_data import ENCOUNTERS
    if pending(conn):
        return None
    t = tick_mod.get_tick(conn)
    rng = rng or random.Random(t * 6151 + player.id)
    loc = entities.get_location(conn, player.location_id)
    seen = state.get_json(conn, SEEN_KEY, {}) or {}
    if force_key is None:
        if t - state.get_int(conn, LAST_KEY, -10**6) < MIN_GAP:
            return None
        danger = loc.danger_level if loc else 1
        if rng.random() > min(0.30, BASE_CHANCE + 0.015 * danger):
            return None
        pool = [e for e in ENCOUNTERS if _eligible(conn, player, e, loc, seen, t)]
        if not pool:
            return None
        enc = rng.choices(pool, weights=[e.get("weight", 10) for e in pool])[0]
    else:
        enc = next(e for e in ENCOUNTERS if e["key"] == force_key)
    from engine.systems import npc_factory
    ctx = {"npc_name": npc_factory.unique_name(rng, conn=conn),
           "luogo": loc.name if loc else "qui", "title": enc["title"]}
    from engine.narrative import varia
    scene = format_scene({"key": enc["key"], "title": enc["title"],
                          "text": varia.ambience(conn, player, t) + " " + enc["text"],
                          "choices": enc["choices"]}, ctx)
    counts = state.get_json(conn, "encounter_counts", {}) or {}
    n_seen = counts.get(enc["key"], 0)
    counts[enc["key"]] = n_seen + 1
    state.set_json(conn, "encounter_counts", counts)
    scene = contextualize(conn, player, scene, n_seen, rng)
    state.set(conn, LAST_KEY, str(t))
    seen[enc["key"]] = t
    state.set_json(conn, SEEN_KEY, seen)
    return start_scene(conn, player, scene)


_DEJA = ["Ti sembra di aver già vissuto qualcosa di simile, ma non è la stessa storia.",
         "Il mondo ha un modo strano di ripetersi: stavolta, però, qualcosa è diverso.",
         "Hai già visto una scena così. Allora eri un altro."]


def contextualize(conn, player, scene: dict, n_seen: int, rng: random.Random) -> dict:
    """La stessa scena cambia con chi sei diventato: la tua fama, la tua infamia, il tuo regno
    rispetto al luogo, quante volte l'hai già vissuta. Nuove righe di testo e, a volte, scelte
    nuove (far valere il tuo nome, lasciar parlare la tua aura)."""
    from engine.systems import reputation
    from engine.simulation import cultivation
    sc = dict(scene)
    sc["choices"] = [dict(c) for c in scene.get("choices", [])]
    extra = []
    rep = reputation.get(conn, player.id)
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    loc = entities.get_location(conn, player.location_id)
    danger = loc.danger_level if loc else 1
    if n_seen:
        extra.append(rng.choice(_DEJA))
    if rep["infamy"] >= 60 and rep["infamy"] > rep["fame"]:
        extra.append("Chi ti vede abbassa lo sguardo: il tuo nome, da queste parti, fa paura.")
    elif rep["fame"] >= 80:
        extra.append(f"Qualcuno ti riconosce e sussurra il tuo nome: {player.name}.")
    dominant = tier >= max(3, danger // 2 + 2)
    if dominant:
        extra.append("La tua aura basta a far tacere tutto intorno: qui nessuno è alla tua altezza.")
    if extra:
        sc["text"] = sc.get("text", "") + "\n(" + " ".join(extra) + ")"
    first = next((c for c in sc["choices"] if c.get("check") and c.get("success")), None)
    if first and len(sc["choices"]) < 4:
        if rep["fame"] >= 80 and not (rep["infamy"] > rep["fame"]):
            sc["choices"].append({"label": "Fai valere il tuo nome",
                                  "check": dict(first["check"], dc=max(10, int(first["check"].get("dc", 60)) - 15)),
                                  "success": dict(first["success"]), "failure": dict(first.get("failure", {}))})
        elif dominant and not any(c.get("command") for c in sc["choices"]):
            sc["choices"].append({"label": "Lasci che sia la tua aura a parlare",
                                  "effects": dict(first["success"])})
    return sc
