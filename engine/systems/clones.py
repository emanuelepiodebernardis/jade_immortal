"""
CLONI (分身) — dividi l'anima in più corpi.

Dal quarto regno, con un Dao dell'Anima a 40 (o con la guida del maestro nell'anello al
livello 5), puoi separare un CLONE. La coltivazione è UNA SOLA, condivisa: ciò che uno impara,
lo sa anche l'altro. Ma ogni clone fa UNA COSA SOLA alla volta (Aggiornamento 62):

  missioni   all'alba ha già cacciato per la Missione Quotidiana del Sistema e svolto una missione
             della bacheca della tua setta (merito, pietre, favore degli anziani)
  allena     medita e si allena: coltivazione e il tuo Dao più debole crescono ogni giorno
  arti       sta al forno, alla forgia, al tavolo dei talismani: le tue arti crescono, e raccoglie
             i materiali che servono
  esplora    va per il mondo: pietre, materiali, bestie (a volte torna ferito)
  guardia    resta al tuo fianco: in battaglia combatte con te

  clone crea               un clone nuovo (uno in più ogni 3 regni)
  clone <compito> [n]      assegna un compito (a tutti, o al clone n)
  clone dispiega           ogni clone al compito più utile che manca (missioni, allena, arti…)
  cloni                    il pannello dei cloni (nella dashboard: Potere → Cloni)

Ogni clone ha un LIVELLO che cresce lavorando, senza fine: più è alto, più rende. Se il tuo
corpo principale muore, un clone sacrifica se stesso e la tua anima vi si trasferisce.
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "clones"
TASKS = {"missioni": ("📋", "svolge le missioni del giorno"), "allena": ("☯", "si allena e medita"),
         "arti": ("⚗", "pratica le tue arti"), "esplora": ("🧭", "esplora il mondo"),
         "guardia": ("🛡", "ti fa da guardia")}
ALIAS = {"lavora": "arti", "riposa": "guardia", "missione": "missioni", "allenati": "allena", "allenamento": "allena",
         "arte": "arti", "esplorare": "esplora", "difendi": "guardia", "scorta": "guardia"}
DEPLOY_ORDER = ("missioni", "allena", "arti", "esplora", "guardia")
_TASKS = {k: v[1] for k, v in TASKS.items()}          # (compatibilità)


def clones(conn) -> list[dict]:
    cs = state.get_json(conn, KEY, []) or []
    for c in cs:                                        # vecchi compiti → nuovi
        c["task"] = ALIAS.get(c.get("task"), c.get("task"))
        if c["task"] not in TASKS:
            c["task"] = "allena"
    return cs


def _save(conn, c: list[dict]) -> None:
    state.set_json(conn, KEY, c)


def max_clones(conn, pid: int) -> int:
    from engine.simulation import cultivation
    tier = cultivation.realm_tier(conn, "player", pid) or 1
    return 0 if tier < 4 else 1 + (tier - 4) // 3


def can_create(conn, pid: int) -> str | None:
    from engine.systems import mentor_ring
    from engine.simulation import cultivation
    if (cultivation.realm_tier(conn, "player", pid) or 1) < 4:
        return "Dividere l'anima richiede almeno il quarto regno."
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key='anima';", (pid,)).fetchone()
    if (not r or (r["comprehension"] or 0) < 40) and mentor_ring.level(conn) < 5:
        return "Serve un Dao dell'Anima almeno a 40 (o un maestro nell'anello di livello 5 che ti guidi)."
    if len(clones(conn)) >= max_clones(conn, pid):
        return f"La tua anima regge al massimo {max_clones(conn, pid)} cloni a questo regno (uno in più ogni 3 regni)."
    return None


_can_create = can_create


def _best_free_task(cs: list[dict], skip: dict | None = None) -> str:
    used = {c["task"] for c in cs if c is not skip}
    return next((t for t in DEPLOY_ORDER if t not in used), "allena")


def create(conn, player) -> str:
    from engine.systems import dao_heart
    why = can_create(conn, player.id)
    if why:
        return why
    cs = clones(conn)
    n = max([c["n"] for c in cs], default=0) + 1
    task = _best_free_task(cs)
    cs.append({"n": n, "task": task, "level": 1, "xp": 0, "down_until": 0})
    _save(conn, cs)
    dao_heart.adjust(conn, -3)
    state.grant_title(conn, "Anima Divisa")
    return (f"Ti siedi, chiudi gli occhi e strappi un lembo della tua anima: davanti a te apre gli occhi il "
            f"tuo CLONE n.{n}. La coltivazione resta una sola. Lo mandi subito dove serve: {TASKS[task][1]}.")


def assign(conn, task: str, which: str = "") -> str:
    task = ALIAS.get(task, task)
    cs = clones(conn)
    if not cs:
        return "Non hai cloni. ('clone crea')"
    if task not in TASKS:
        return "Compiti: " + ", ".join(TASKS)
    idx = [c for c in cs if not which or str(c["n"]) == which] or cs
    for c in idx:
        c["task"] = task
    _save(conn, cs)
    who = f"Il clone n.{idx[0]['n']}" if len(idx) == 1 else "I cloni"
    return f"{who} {TASKS[task][1]}."


def deploy(conn, player) -> str:
    """Ogni clone a un compito diverso, nell'ordine di utilità: missioni, allenamento, arti, esplora, guardia."""
    from engine.systems import sects, professions
    cs = clones(conn)
    if not cs:
        return "Non hai cloni. ('clone crea')"
    order = list(DEPLOY_ORDER)
    if not sects.get_membership(conn, player.id):
        pass                                            # senza setta le missioni sono solo quelle del Sistema
    if not professions.profession(conn, player.id):
        order.remove("arti")
        order.insert(3, "arti")                         # senza arti scelte: prima esplorare
    ranked = sorted(cs, key=lambda c: -c["level"])
    out = []
    for i, c in enumerate(ranked):
        c["task"] = order[i] if i < len(order) else "allena"
        out.append(f"  {TASKS[c['task']][0]} Clone n.{c['n']} (liv. {c['level']}) {TASKS[c['task']][1]}")
    _save(conn, cs)
    return "Dispieghi i tuoi cloni:\n" + "\n".join(out)


def _level_up(c: dict, xp: float) -> str | None:
    c["xp"] = c.get("xp", 0) + xp
    need = 10 * c["level"]
    if c["xp"] >= need:
        c["xp"] -= need
        c["level"] += 1
        return f"Il clone n.{c['n']} si rafforza: livello {c['level']}."
    return None


def _missions(conn, t: int, rng, player, c: dict) -> str:
    """La Missione Quotidiana (la caccia, la tempra) e una missione della bacheca della setta."""
    from engine.systems import system_daily, sects, guild, soul_temper, sect_politics
    lv = c["level"]
    done = []
    sd = system_daily.get(conn, player.id)               # (il giorno nuovo comincia prima del lavoro del clone)
    need = sd["goals"]["kills"]
    state.set(conn, "kills_total", str(state.get_int(conn, "kills_total", 0) + need))
    done.append(f"{need} prede per il Sistema")
    try:
        soul_temper.add_xp(conn, 0.2 + 0.05 * lv)
        done.append("la tempra dello spirito")
    except Exception:                                   # noqa: BLE001
        pass
    if sects.get_membership(conn, player.id):
        try:
            b = sect_politics._board(conn, player)
        except Exception:                               # noqa: BLE001
            b = []
        if b:
            m = b[c["n"] % len(b)]
            eff = 0.6 + 0.08 * lv
            merit, stones = int(m["merit"] * eff), int(m["stones"] * eff)
            guild.add_merit(conn, merit, player.id)
            sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
            done.append(f"«{m['text']}» (merito +{merit}, +{stones} pietre)")
    return "; ".join(done)


def _train(conn, t: int, rng, player, c: dict) -> str:
    from engine.systems import dao_training, items
    lv = c["level"]
    rows = dao_training.trainable_daos(conn, player.id)
    txt = []
    if rows:
        weak = min(rows, key=lambda r: r["comprehension"])
        dao_training.comprehend(conn, t, rng, weak["dao_key"], multiplier=0.6 + 0.12 * lv, player_id=player.id,
                                carry=True)
        txt.append(f"il Dao {weak['name']}")
    items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": round(0.04 + 0.012 * lv, 3)})
    txt.append("la coltivazione")
    return "allena " + " e ".join(txt)


def _arts(conn, t: int, rng, player, c: dict) -> str:
    from engine.systems import professions
    lv = c["level"]
    arts = professions.practiced(conn) or ([professions.profession(conn, player.id)] if professions.profession(conn, player.id) else [])
    for k in arts:
        professions.add_xp(conn, player.id, 2 + lv, k)
    professions.give(conn, player.id, "erbe", 1 + lv // 2)
    professions.give(conn, player.id, "minerali", 1 + lv // 3)
    return ("pratica " + ", ".join(professions.art(k) if hasattr(professions, "art") else k for k in arts)
            if arts else "raccoglie erbe e minerali (scegli un'arte per farla crescere)")


def _explore(conn, t: int, rng, player, c: dict, day: int) -> tuple[str, str | None]:
    from engine.systems import sects, professions, dao_superiori
    lv = c["level"]
    stones = rng.randint(8, 24) * lv
    sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
    mat = rng.choice(["erbe", "minerali", "nuclei"])
    professions.give(conn, player.id, mat, 1 + lv // 2)
    if rng.random() < 0.4:
        dao_superiori.bump(conn, "kills_total")
    hurt = None
    if rng.random() < max(0.03, 0.15 - 0.01 * lv):
        c["down_until"] = day + 3
        hurt = f"Il clone n.{c['n']} torna ferito da un'esplorazione: riposerà 3 giorni."
    return f"porta {stones} pietre e {mat}", hurt


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    cs = clones(conn)
    if not cs or player is None:
        return []
    day = t // 120
    out, work = [], []
    for c in cs:
        if c.get("down_until", 0) > day:
            work.append(f"n.{c['n']} è ferito")
            continue
        task = c["task"]
        if task == "missioni":
            work.append(f"{TASKS[task][0]} n.{c['n']}: " + _missions(conn, t, rng, player, c))
            msg = _level_up(c, 1.2)
        elif task == "allena":
            work.append(f"{TASKS[task][0]} n.{c['n']}: " + _train(conn, t, rng, player, c))
            msg = _level_up(c, 1)
        elif task == "arti":
            work.append(f"{TASKS[task][0]} n.{c['n']}: " + _arts(conn, t, rng, player, c))
            msg = _level_up(c, 1)
        elif task == "esplora":
            w, hurt = _explore(conn, t, rng, player, c, day)
            work.append(f"{TASKS[task][0]} n.{c['n']}: {w}")
            if hurt:
                out.append(hurt)
            msg = _level_up(c, 1.5)
        else:
            msg = _level_up(c, 0.4)
        if msg:
            out.append(msg)
    _save(conn, cs)
    if work:
        out.insert(0, "☯ I tuoi cloni: " + " · ".join(work))
    return out


def combat_allies(conn, player_id: int) -> list[dict]:
    from engine.simulation import combat
    day = tick_mod.get_tick(conn) // 120
    out = []
    for c in clones(conn):
        if c["task"] != "guardia" or c.get("down_until", 0) > day:
            continue
        atk = combat.combat_power(conn, "player", player_id)["attack"] * min(0.9, 0.35 + 0.03 * c["level"])
        out.append({"intro": f"Il tuo clone n.{c['n']} si mette spalla a spalla con te.", "attack": atk,
                    "line": f"Il clone n.{c['n']} colpisce in perfetta sincronia con te."})
    return out


def try_save(conn, player) -> str | None:
    """Il corpo principale muore: un clone si sacrifica e l'anima vi si trasferisce."""
    cs = clones(conn)
    if not cs:
        return None
    c = max(cs, key=lambda x: x["level"])
    cs.remove(c)
    _save(conn, cs)
    conn.execute("UPDATE players SET status='alive' WHERE id=?;", (player.id,))
    conn.execute("UPDATE injuries SET healed=1 WHERE character_type='player' AND character_id=?;", (player.id,))
    return (f"☯ Il tuo corpo cade… ma la tua anima fugge nel CLONE n.{c['n']}, che si fa carne della tua carne. "
            "Riapri gli occhi altrove: vivo. Quel clone non c'è più.")


def describe(conn, player) -> str:
    from engine.systems import menus
    return menus.render(conn, menu_build(conn, player))


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    cs = clones(conn)
    mx = max_clones(conn, player.id)
    day = tick_mod.get_tick(conn) // 120
    why = can_create(conn, player.id)
    head = [f"Cloni: {len(cs)}/{mx}. Una sola coltivazione, compiti divisi: ogni clone fa una cosa sola.",
            "Lavorano all'alba di ogni giorno."]
    secs = [section("Il tuo esercito di te stesso", [
        "📋 missioni: la caccia della Missione Quotidiana, la tempra, una missione della bacheca di setta",
        "☯ allena: coltivazione e il tuo Dao più debole · ⚗ arti: le tue arti e i loro materiali",
        "🧭 esplora: pietre e materiali (a volte torna ferito) · 🛡 guardia: combatte al tuo fianco"],
        [act("✦ Crea un clone", "clone crea", why is None, why or "", main=True),
         act("Dispiega tutti (ogni clone al compito più utile)", "clone dispiega", bool(cs), "non hai cloni")],
        icon="☯")]
    for c in sorted(cs, key=lambda x: x["n"]):
        hurt = c.get("down_until", 0) > day
        st = f"ferito: riposa ancora {c['down_until'] - day} giorni" if hurt else f"{TASKS[c['task']][0]} {TASKS[c['task']][1]}"
        acts = [act(f"{TASKS[k][0]} {k.capitalize()}", f"clone {k} {c['n']}", k != c["task"], "lo sta già facendo")
                for k in TASKS]
        secs.append(section(f"Clone n.{c['n']} — livello {c['level']}", [st], acts,
                            [bar("Esperienza", 100 * c.get("xp", 0) / (10 * c["level"]),
                                 f"{c.get('xp', 0):.0f}/{10 * c['level']}", tone="info")], icon="👤"))
    return menu("cloni", "☯ CLONI", head, secs)


def command(conn, player, arg: str) -> str:
    parts = arg.split()
    sub = parts[0].lower() if parts else ""
    which = parts[1] if len(parts) > 1 else ""
    sub = ALIAS.get(sub, sub)
    if sub in ("crea", "create", "dividi", "nuovo"):
        return create(conn, player)
    if sub in ("dispiega", "schiera", "deploy", "auto"):
        return deploy(conn, player)
    if sub in TASKS:
        return assign(conn, sub, which)
    return describe(conn, player)
