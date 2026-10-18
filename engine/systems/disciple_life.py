"""
LA VITA DEI DISCEPOLI (Aggiornamento 63) — carattere, compiti, lezioni e il demone del cuore.

Ogni discepolo ha DUE TRATTI (uno buono e uno no, o due dello stesso segno) che pesano su quello che
fa. Come i cloni, ogni discepolo fa UNA COSA al giorno:

  allena     cresce più in fretta (il compito di sempre)
  missioni   svolge incarichi per conto tuo: merito e pietre
  arti       aiuta nelle tue arti: esperienza e materiali
  esplora    va nelle fenditure: materiali, a volte un tesoro, a volte torna ferito

LEZIONE APERTA (una al giorno): domande e risposte con tutti i discepoli. Loro crescono, tu
guadagni merito, e a volte una domanda ti illumina.

IL DEMONE DEL CUORE: ogni tanto un discepolo cade nel demone (心魔). Smette di lavorare, e torna in sé
solo se lo affronti in duello e lo vinci: risparmiato o sigillato si risveglia più leale; se lo uccidi,
lo perdi. Il tratto «Ambizioso» rende più esposti, «Leale» quasi immuni. (L'idea viene dai discepoli
che si demonizzano nella setta celeste di Immortal Taoists.)

  discepoli                    il pannello (dashboard: Potere → Discepoli)
  discepolo <compito> [n]      un compito a un discepolo (o a tutti)
  discepoli lezione            la lezione aperta del giorno
  discepolo affronta <n>       affronti il discepolo caduto nel demone
"""

from __future__ import annotations

import random
import zlib

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "disciple_life"
TASKS = {"allena": ("☯", "si allena"), "missioni": ("📋", "svolge incarichi per te"),
         "arti": ("⚗", "ti aiuta nelle arti"), "esplora": ("🧭", "esplora le fenditure")}
# tratto -> (segno, descrizione, effetti)
TRAITS = {
    "Diligente": (1, "rende un terzo in più in ogni compito", {"yield": 0.33}),
    "Geniale": (1, "cresce il doppio", {"grow": 1.0}),
    "Leale": (1, "quasi immune al demone del cuore", {"demon": 0.25}),
    "Fortunato": (1, "in esplorazione trova a volte tesori", {"luck": 1}),
    "Mani d'Oro": (1, "nelle arti vale il doppio", {"arts": 1.0}),
    "Coraggioso": (1, "nelle missioni rende di più", {"missions": 0.5}),
    "Pigro": (-1, "rende un terzo in meno", {"yield": -0.33}),
    "Ambizioso": (-1, "il demone del cuore lo tenta il doppio", {"demon": 2.0}),
    "Ingenuo": (-1, "a volte si fa truffare (perde pietre)", {"naive": 1}),
    "Fragile": (-1, "in esplorazione si ferisce spesso", {"fragile": 1}),
    "Arrogante": (-1, "provoca risse: a volte torna con un nemico", {"arrogant": 1}),
}
_GOOD = [k for k, v in TRAITS.items() if v[0] > 0]
_BAD = [k for k, v in TRAITS.items() if v[0] < 0]
DEMON_DAILY = 0.012
QUESTIONS = [
    ("«Maestro, se il Dao è senza forma, come posso afferrarlo?»", "«Non afferrarlo. Cammina con lui.»"),
    ("«Perché il Cielo manda tribolazioni a chi coltiva?»", "«Perché il ferro diventa spada solo nel fuoco.»"),
    ("«È giusto uccidere chi ha ucciso?»", "«Chiediti prima chi diventerai dopo.»"),
    ("«Il talento conta più della fatica?»", "«Il talento è la strada. La fatica sono i passi.»"),
    ("«Cosa resta di un immortale, se tutti quelli che ama muoiono?»", "«Il loro ricordo nel suo Dao.»"),
    ("«Come si vince chi è più forte?»", "«Non dove è forte. Dove è solo.»"),
    ("«Il cuore va svuotato o riempito?»", "«Svuotato di paura, riempito di scopo.»"),
    ("«Perché meditiamo ogni giorno, anche quando non cambia nulla?»", "«Perché la goccia non vede la pietra scavarsi.»"),
]


def _all(conn) -> dict:
    return state.get_json(conn, KEY, None) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def info(conn, npc_id: int) -> dict:
    d = _all(conn)
    k = str(npc_id)
    if k not in d:
        rng = random.Random(zlib.crc32(f"disc{npc_id}".encode()))
        r = rng.random()
        traits = ([rng.choice(_GOOD), rng.choice(_BAD)] if r < 0.6 else
                  rng.sample(_GOOD, 2) if r < 0.8 else rng.sample(_BAD, 2))
        d[k] = {"traits": traits, "task": "allena", "demon": False, "down": 0, "loyal": 0}
        _save(conn, d)
    return d[k]


def _set(conn, npc_id: int, v: dict) -> None:
    d = _all(conn)
    d[str(npc_id)] = v
    _save(conn, d)


def _eff(inf: dict, key: str, default=0.0):
    tot = default
    for t in inf["traits"]:
        e = TRAITS.get(t, (0, "", {}))[2]
        if key in e:
            tot = tot * e[key] if key == "demon" else tot + e[key]
    return tot


def _rows(conn, pid: int):
    from engine.systems import own_sect
    return own_sect.disciples(conn, pid)


def _pick(conn, pid: int, which: str):
    rows = list(_rows(conn, pid))
    if not rows:
        return []
    if not which:
        return rows
    if which.isdigit() and 1 <= int(which) <= len(rows):
        return [rows[int(which) - 1]]
    return [r for r in rows if which.lower() in r["name"].lower()]


def assign(conn, player, task: str, which: str = "") -> str:
    if task not in TASKS:
        return "Compiti: " + ", ".join(TASKS)
    rows = _pick(conn, player.id, which)
    if not rows:
        return "Non hai discepoli (o nessuno con quel nome)."
    for r in rows:
        inf = info(conn, r["npc_id"])
        inf["task"] = task
        _set(conn, r["npc_id"], inf)
    who = rows[0]["name"] if len(rows) == 1 else "I tuoi discepoli"
    return f"{who}: {TASKS[task][1]}."


def lecture(conn, player) -> str:
    from engine.systems import guild, npc_factory, items
    from engine.simulation import cultivation
    rows = list(_rows(conn, player.id))
    if not rows:
        return "Non hai discepoli a cui fare lezione."
    t = tick_mod.get_tick(conn)
    day = t // 120
    if state.get_int(conn, "lecture_day", -1) == day:
        return "La lezione aperta di oggi l'hai già tenuta."
    state.set(conn, "lecture_day", str(day))
    rng = random.Random(t * 13 + 7)
    q, a = rng.choice(QUESTIONS)
    asker = rng.choice(rows)["name"]
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    merit = 4 * len(rows) * tier
    guild.add_merit(conn, merit, player.id)
    grown = 0
    for r in rows:
        inf = info(conn, r["npc_id"])
        if inf["demon"]:
            continue
        if rng.random() < 0.5 + 0.25 * _eff(inf, "grow"):
            npc_factory.raise_npc(conn, r["npc_id"], 1)
            grown += 1
    out = [f"Lezione aperta. {asker} chiede: {q}", f"Rispondi: {a}",
           f"Merito +{merit}. {grown} discepoli fanno un passo avanti."]
    if rng.random() < 0.25:
        rows_d = __import__("engine.systems.dao_training", fromlist=["x"]).trainable_daos(conn, player.id)
        if rows_d:
            out.append("Rispondendo, capisci qualcosa anche tu:")
            out += items.apply_effects(conn, t, rng, player.id, {"dao_key": rows_d[0]["dao_key"], "dao_gain": 2 + tier // 2})
    return "\n".join(out)


def face(conn, player, which: str) -> str:
    from engine.systems import duel
    rows = [r for r in _pick(conn, player.id, which) if info(conn, r["npc_id"])["demon"]]
    if not rows:
        return "Nessun discepolo caduto nel demone del cuore (o nessuno con quel nome)."
    r = rows[0]
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, r["npc_id"]))
    state.set(conn, "disciple_demon_duel", str(r["npc_id"]))
    return (f"{r['name']} ti aspetta con gli occhi rossi e la voce di un altro. «Maestro… scappa.» "
            "Vincilo, e risparmialo: solo così torna in sé.\n" + (duel.start(conn, player, r["name"], arena=True) or ""))


def on_duel(conn, player, npc_id: int, outcome: str) -> list[str]:
    """Il duello con un discepolo demonizzato: vinto e risparmiato, torna in sé."""
    if state.get_int(conn, "disciple_demon_duel", 0) != npc_id:
        return []
    state.delete(conn, "disciple_demon_duel")
    inf = info(conn, npc_id)
    nm = conn.execute("SELECT name FROM npcs WHERE id=?;", (npc_id,)).fetchone()["name"]
    if outcome in ("risparmiato", "sigillato"):
        inf["demon"] = False
        inf["loyal"] = inf.get("loyal", 0) + 1
        if "Ambizioso" in inf["traits"] and inf["loyal"] >= 2:
            inf["traits"] = [("Leale" if t == "Ambizioso" else t) for t in inf["traits"]]
        _set(conn, npc_id, inf)
        from engine.systems import own_sect
        home = own_sect._home(conn, player.id)
        if home:
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (home, npc_id))
        return [f"✦ {nm} crolla in ginocchio, e quando rialza gli occhi sono di nuovo i suoi. «Maestro… perdonami.» "
                "È tornato in sé, e ti è più legato di prima."]
    if outcome == "ucciso":
        return [f"Hai ucciso {nm}. Il demone è morto con lui. Nella tua dimora c'è un posto vuoto."]
    return [f"{nm} è ancora preda del demone. Riprova quando sarai pronto ('discepolo affronta')."]


def daily(conn, t: int, rng, player) -> list[str]:
    from engine.systems import npc_factory, sects, guild, professions, dao_heart
    from engine.simulation import cultivation
    if player is None:
        return []
    rows = list(_rows(conn, player.id))
    if not rows:
        return []
    day = t // 120
    ptier = cultivation.realm_tier(conn, "player", player.id) or 1
    out, work = [], []
    for r in rows:
        inf = info(conn, r["npc_id"])
        nm = r["name"].split()[0]
        if inf["demon"]:
            work.append(f"{nm} è nel demone")
            continue
        if inf.get("down", 0) > day:
            work.append(f"{nm} è ferito")
            continue
        p_demon = DEMON_DAILY * _eff(inf, "demon", 1.0) * (1.5 if dao_heart.heart(conn) < 40 else 1.0)
        if rng.random() < p_demon:
            inf["demon"] = True
            _set(conn, r["npc_id"], inf)
            out.append(f"☠ {r['name']} è caduto nel demone del cuore: non lavora più, e guarda gli altri come prede. "
                       f"Solo tu puoi riportarlo in sé ('discepolo affronta {nm}').")
            continue
        y = max(0.2, 1.0 + _eff(inf, "yield"))
        ntier = cultivation.realm_tier(conn, "npc", r["npc_id"]) or 1
        task = inf["task"]
        if task == "allena":
            if ntier < ptier and rng.random() < 0.35 * y * (1 + _eff(inf, "grow")):
                npc_factory.raise_npc(conn, r["npc_id"], 1)
            work.append(f"☯ {nm}")
        elif task == "missioni":
            m = int((6 + 3 * ntier) * y * (1 + _eff(inf, "missions")))
            s = int(20 * ntier * y * (1 + _eff(inf, "missions")))
            guild.add_merit(conn, m, player.id)
            sects.grant_resource(conn, "pietre_spirituali", s, player.id)
            work.append(f"📋 {nm} (+{m} merito, +{s} pietre)")
        elif task == "arti":
            arts = professions.practiced(conn) or ([professions.profession(conn, player.id)]
                                                   if professions.profession(conn, player.id) else [])
            for k in arts:
                professions.add_xp(conn, player.id, max(1, int((1 + ntier // 2) * y * (1 + _eff(inf, "arts")))), k)
            professions.give(conn, player.id, "erbe", max(1, int(ntier * y)))
            work.append(f"⚗ {nm}")
        elif task == "esplora":
            professions.give(conn, player.id, rng.choice(["erbe", "minerali", "nuclei"]), max(1, int(ntier * y)))
            if _eff(inf, "luck") and rng.random() < 0.08:
                from engine.systems import rewards
                out += [f"🍀 {r['name']} torna dalla fenditura con un tesoro:"] + \
                    rewards.grant(conn, rng, player, rank=2, kinds=["tesoro", "pillola"], n=1, stones=False)
            if rng.random() < (0.12 if _eff(inf, "fragile") else 0.04):
                inf["down"] = day + 3
                out.append(f"{r['name']} torna ferito dalla fenditura: riposerà 3 giorni.")
            work.append(f"🧭 {nm}")
        if _eff(inf, "naive") and rng.random() < 0.05:
            lost = min(sects.get_resource(conn, "pietre_spirituali", player.id), 30 * ntier)
            if lost:
                sects.grant_resource(conn, "pietre_spirituali", -lost, player.id)
                out.append(f"{r['name']}, ingenuo, si è fatto truffare al mercato: −{lost} pietre.")
        if _eff(inf, "arrogant") and rng.random() < 0.02:
            out.append(f"{r['name']} ha umiliato il discepolo di un'altra setta. Qualcuno verrà a chiederne conto.")
        _set(conn, r["npc_id"], inf)
    if work:
        out.insert(0, "🎓 I tuoi discepoli: " + " · ".join(work))
    return out


def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, menu, section
    from engine.systems import own_sect
    from engine.simulation import cultivation
    rows = list(_rows(conn, player.id))
    mx = own_sect.max_disciples(conn, player.id)
    day = tick_mod.get_tick(conn) // 120
    secs = [section("La scuola", [
        f"Discepoli: {len(rows)}/{mx}. Ognuno ha due tratti e fa un compito al giorno.",
        "Si accolgono con 'accogli <nome>' (qualcuno più debole di te che ti stima)."],
        [act("Lezione aperta (merito, e i discepoli crescono)", "discepoli lezione",
             bool(rows) and state.get_int(conn, "lecture_day", -1) != day,
             "nessun discepolo" if not rows else "già tenuta oggi", main=True)], icon="🎓")]
    for i, r in enumerate(rows, 1):
        inf = info(conn, r["npc_id"])
        lines = [cultivation.realm_label(conn, "npc", r["npc_id"]),
                 "Tratti: " + ", ".join(f"{t} ({TRAITS[t][1]})" for t in inf["traits"] if t in TRAITS)]
        if inf["demon"]:
            lines.append("☠ Caduto nel demone del cuore: non lavora finché non lo vinci in duello.")
            acts = [act("Affrontalo e riportalo in sé", f"discepolo affronta {i}", main=True)]
        else:
            lines.append(f"{TASKS[inf['task']][0]} {TASKS[inf['task']][1]}"
                         + (f" (ferito, ancora {inf['down'] - day} giorni)" if inf.get("down", 0) > day else ""))
            acts = [act(f"{TASKS[k][0]} {k.capitalize()}", f"discepolo {k} {i}", k != inf["task"], "lo sta già facendo")
                    for k in TASKS]
            acts.append(act("Insegnagli (una lezione privata)", f"insegna {r['name'].split()[0]}"))
        secs.append(section(f"{i}. {r['name']}", lines, acts, icon="☠" if inf["demon"] else "🎓"))
    return menu("discepoli", "🎓 DISCEPOLI", ["Carattere, compiti, lezioni, e il demone del cuore."], secs)


def command(conn, player, arg: str) -> str:
    from engine.systems import menus
    parts = (arg or "").split()
    sub = parts[0].lower() if parts else ""
    rest = " ".join(parts[1:])
    if sub in ("lezione", "lezioni", "domande"):
        return lecture(conn, player)
    if sub in ("affronta", "duello", "salva"):
        return face(conn, player, rest)
    if sub in TASKS:
        return assign(conn, player, sub, rest)
    return menus.render(conn, menu_build(conn, player))
