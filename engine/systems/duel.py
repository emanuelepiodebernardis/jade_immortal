"""
DUELLO A TURNI — gli scontri importanti si giocano, non si leggono soltanto.

  duello <nome>     sfidi qualcuno qui in un duello a turni (l'arcinemico, una nemesi, chi
                    torna a chiederti il conto… o chiunque tu voglia)

A ogni turno scegli (pulsanti nella dashboard, numeri nel terminale):
  · Colpisci            un colpo normale
  · <Tecnica>           le tue tecniche (arma, Dao, segrete, Abisso): più danno, costano Qi o
                        Spirito, poi devono ricaricarsi per qualche turno
  · Difendi             subisci molto meno e recuperi un po' di Qi; se lui stava caricando un
                        colpo, lo pari quasi del tutto
  · Concentrati         rinunci al colpo ora per un colpo devastante il turno dopo
  · Fuggi               più facile se sei più veloce/forte; se fallisce, ti colpisce alle spalle
Il nemico a volte RACCOGLIE IL QI per un colpo pesante: te lo dice un turno prima. Leggerlo
e difendersi al momento giusto è la differenza tra vincere e cadere.
Quando cade, decidi tu: lo FINISCI o lo RISPARMI (e il mondo se lo ricorda). Gli effetti sono
gli stessi dello scontro automatico: bottino, fama, karma, arcinemico, nemesi, echi…

TATTICA
  · ELEMENTI: il tuo Dao più forte contro il suo, secondo il ciclo dei Cinque Elementi
    (il Fuoco fonde il Metallo, il Metallo taglia il Legno, il Legno spacca la Terra, la Terra
    argina l'Acqua, l'Acqua spegne il Fuoco; Luce e Oscurità si feriscono a vicenda, il Fulmine
    domina l'Acqua). In vantaggio colpisci +25%, in svantaggio −15%.
  · STILI: ogni avversario combatte a modo suo — l'IMPETUOSO carica spesso e colpisce duro ma si
    scopre; il PRUDENTE si chiude in difesa; il SUBDOLO finge le cariche (non sempre il colpo
    pesante arriva davvero); l'EQUILIBRATO non ha punti deboli evidenti.
  · PILLOLE: a metà duello puoi ingoiare una pillola (perdi il turno, recuperi un quarto della vita;
    una Pillola Curativa la metà).
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "duel"


def get(conn) -> dict | None:
    return state.get_json(conn, KEY)


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _bar(cur: float, mx: float, n: int = 20) -> str:
    k = max(0, min(n, round(n * cur / mx))) if mx else 0
    return "█" * k + "·" * (n - k)


def start(conn, player, arg: str) -> str:
    from engine.cli import loop
    from engine.simulation import combat
    from engine.systems import encounters
    if get(conn):
        return _scene_text(conn, player)
    if encounters.pending(conn):
        return "Prima risolvi ciò che hai davanti."
    npc, _forced, target = loop._parse_attack_arg(conn, player, arg or "")
    from engine.systems import dominion
    npc, why = dominion.not_my_servant(conn, player, npc, target)
    if why:
        return why
    if npc is None:
        return f"Non vedi nessuno di nome '{target}' qui. (duello <nome>)"
    pa = combat.combat_power(conn, "player", player.id)
    pd = combat.combat_power(conn, "npc", npc.id)
    sc = combat.duel_scale(pa, pd) * _length(conn, player, npc)
    style = _style(conn, npc.id)
    adv, adv_txt = _elements(conn, player.id, npc.id)
    d = {"npc": npc.id, "name": npc.name, "hp_p": pa["vitality"] * sc, "pmax": pa["vitality"] * sc,
         "hp_e": pd["vitality"] * sc, "emax": pd["vitality"] * sc, "round": 0, "charge_e": False,
         "focus": False, "cd": {}, "crit": False, "style": style, "adv": adv, "feint": False,
         "log": [f"⚔ DUELLO: tu contro {npc.name}."]}
    _save(conn, d)
    intro = [f"Stile di {npc.name}: {STYLES[style][0]} — {STYLES[style][1]}"]
    if adv_txt:
        intro.append(adv_txt)
    return _next_turn(conn, player, intro)


# ---------------- tattica: stili ed elementi ----------------
# stile -> (nome, descrizione, prob. di caricare, moltiplicatore attacco, moltiplicatore danno subito)
STYLES = {"impetuoso": ("IMPETUOSO", "carica spesso e colpisce duro, ma si scopre", 0.38, 1.15, 1.2),
          "prudente": ("PRUDENTE", "si chiude in difesa e aspetta il tuo errore", 0.15, 0.9, 0.8),
          "subdolo": ("SUBDOLO", "finge le cariche: non sempre il colpo pesante arriva", 0.3, 1.0, 1.0),
          "equilibrato": ("EQUILIBRATO", "nessun punto debole evidente", 0.25, 1.0, 1.0)}
_BEATS = {"fuoco": "metallo", "metallo": "legno", "legno": "terra", "terra": "acqua", "acqua": "fuoco",
          "luce": "oscurita", "oscurita": "luce", "fulmine": "acqua"}
_EL_IT = {"fuoco": "Fuoco", "metallo": "Metallo", "legno": "Legno", "terra": "Terra", "acqua": "Acqua",
          "luce": "Luce", "oscurita": "Oscurità", "fulmine": "Fulmine"}


def _style(conn, npc_id: int) -> str:
    tr = entities.get_npc_traits(conn, npc_id) or {}
    if tr.get("greed", 50) >= 70 and tr.get("honor", 50) <= 40:
        return "subdolo"
    if tr.get("pride", 50) >= 75 or tr.get("ambition", 50) >= 80 or tr.get("courage", 50) >= 80:
        return "impetuoso"
    if tr.get("courage", 50) <= 35 or tr.get("compassion", 50) >= 75:
        return "prudente"
    return "equilibrato"


def _top_element(conn, ctype: str, cid: int) -> str | None:
    r = conn.execute("SELECT dao_key FROM character_daos WHERE character_type=? AND character_id=? AND dao_key IN "
                     f"({','.join('?' * len(_EL_IT))}) AND comprehension>0 ORDER BY comprehension DESC LIMIT 1;",
                     (ctype, cid, *_EL_IT)).fetchone()
    return r["dao_key"] if r else None


def _elements(conn, pid: int, npc_id: int) -> tuple[float, str]:
    a, b = _top_element(conn, "player", pid), _top_element(conn, "npc", npc_id)
    if not a or not b or a == b:
        return 1.0, ""
    if _BEATS.get(a) == b:
        return 1.25, f"☸ Il tuo {_EL_IT[a]} domina il suo {_EL_IT[b]}: colpisci +25%."
    if _BEATS.get(b) == a:
        return 0.85, f"☸ Il suo {_EL_IT[b]} domina il tuo {_EL_IT[a]}: colpisci −15%."
    return 1.0, ""


def _pills(conn, pid: int) -> list:
    from engine.systems import items
    return [r for r in items.player_inventory(conn, pid) if r["item_type"] == "pillola"]


# Durata: un duello tra pari dura 5-8 scambi; con l'arcinemico o una nemesi 10-12.
DUEL_HP = 0.3
GRUDGE_HP = 0.5


def _length(conn, player, npc) -> float:
    from engine.systems import bonds
    kinds = bonds.bond_kinds(conn, npc.id, player.id)
    from engine.systems import archrival
    a = archrival.get(conn)
    big = bool(kinds & {"nemesis", "rival"}) or bool(a and a.get("npc") == npc.id)
    return GRUDGE_HP if big else DUEL_HP


def _moves(conn, player) -> list[dict]:
    from engine.systems import moves as mvmod, qi as qimod, spirit as spmod
    out = []
    for m in mvmod.available_moves(conn, player.id):
        ok = (spmod.can_afford(conn, m["spirit_cost"], player.id) if m.get("fuel") == "spirit"
              else qimod.can_afford(conn, m["qi_cost"], player.id))
        out.append(dict(m, ok=ok))
    out.sort(key=lambda m: -m["mods"].get("attack_mult", 1.0))
    return out[:3]


def _scene_text(conn, player) -> str:
    from engine.systems import encounters
    sc = encounters.pending(conn)
    return encounters.render(conn, player, sc) if sc else ""


def _next_turn(conn, player, extra: list[str] | None = None) -> str:
    from engine.systems import encounters, qi as qimod, spirit as spmod
    d = get(conn)
    d["round"] += 1
    rng = random.Random(tick_mod.get_tick(conn) * 31 + d["round"] + d["npc"])
    # il nemico decide: a volte raccoglie il qi per un colpo pesante (e si vede)
    st = STYLES.get(d.get("style", "equilibrato"), STYLES["equilibrato"])
    d["charge_e"] = rng.random() < st[2] and d["round"] > 1
    d["feint"] = d["charge_e"] and d.get("style") == "subdolo" and rng.random() < 0.5
    _save(conn, d)
    lines = list(extra or [])
    lines.append(f"Turno {d['round']}.  Tu  {_bar(d['hp_p'], d['pmax'])}  "
                 f"{d['name']}  {_bar(d['hp_e'], d['emax'])}")
    lines.append(f"Qi {qimod.get_qi(conn, player.id)}/{qimod.max_qi(conn, player.id)} · "
                 f"Spirito {spmod.get_spirit(conn, player.id)}/{spmod.max_spirit(conn, player.id)}")
    if d["charge_e"]:
        lines.append(f"⚠ {d['name']} raccoglie il qi: il prossimo colpo sarà PESANTE.")
    if d["focus"]:
        lines.append("Sei concentrato: il tuo prossimo colpo sarà devastante.")
    choices = [{"label": "Colpisci", "effects": {}, "command": "duello_azione colpisci"}]
    for i, m in enumerate(_moves(conn, player)):
        cost = f"Spirito {m['spirit_cost']}" if m.get("fuel") == "spirit" else f"Qi {m['qi_cost']}"
        cd = d["cd"].get(m["key"], 0)
        if cd > d["round"]:
            continue
        if not m["ok"]:
            continue
        choices.append({"label": f"{m['name']} ({cost})", "effects": {}, "command": f"duello_azione tecnica {m['key']}"})
    choices.append({"label": "Difendi" + (" — para il colpo pesante!" if d["charge_e"] else ""), "effects": {},
                    "command": "duello_azione difendi"})
    if not d["focus"]:
        choices.append({"label": "Concentrati (colpo devastante al prossimo turno)", "effects": {},
                        "command": "duello_azione concentrati"})
    pills = _pills(conn, player.id)
    if pills and d["hp_p"] < d["pmax"] * 0.7:
        cur = next((x for x in pills if "Curativa" in x["name"]), pills[0])
        choices.append({"label": f"Ingoi {cur['name']} (perdi il turno, recuperi vita)", "effects": {},
                        "command": "duello_azione pillola"})
    choices.append({"label": "Fuggi", "effects": {}, "command": "duello_azione fuggi"})
    sc = {"key": "duello", "title": f"Duello con {d['name']} — turno {d['round']}", "event_type": "combat",
          "sticky": True, "text": "\n".join(lines), "choices": choices[:7],
          "ctx": {"npc_id": d["npc"], "npc_name": d["name"]}}
    return encounters.start_scene(conn, player, sc, force=True) or ""


def act(conn, player, arg: str) -> str:
    from engine.simulation import combat
    from engine.systems import qi as qimod, spirit as spmod, perception, moves as mvmod
    from engine.cli import loop
    d = get(conn)
    if not d:
        return "Non stai duellando. ('duello <nome>')"
    npc = entities.get_npc(conn, d["npc"])
    if npc is None or npc.status != "alive" or npc.location_id != player.location_id:
        state.delete(conn, KEY)
        return "Il tuo avversario non è più qui. Il duello finisce."
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 97 + d["round"] * 13 + d["npc"])
    pa = combat.combat_power(conn, "player", player.id)
    pd = combat.combat_power(conn, "npc", npc.id)
    parts = arg.split()
    what = parts[0] if parts else "colpisci"
    lines: list[str] = []
    taken = 1.0
    mods: dict = {}

    if what == "fuggi":
        ratio = perception.strength_ratio(conn, player.id, npc.id)
        if rng.random() < max(0.15, min(0.9, 0.35 + 0.4 * (ratio - 0.5))):
            state.delete(conn, KEY)
            return f"Rompi il contatto e ti dilegui. {d['name']} ti grida dietro qualcosa che preferisci non sentire."
        lines.append("Provi a fuggire, ma ti taglia la strada!")
        taken = 1.3
    elif what == "difendi":
        taken = 0.15 if d["charge_e"] else 0.45
        qimod.restore_fraction(conn, 0.1, player.id)
        lines.append("Ti chiudi in guardia." + (" Il suo colpo pesante si infrange sulla tua difesa!" if d["charge_e"] else ""))
        if rng.random() < 0.3:
            dmg, _c = combat._strike(pa["attack"] * 0.6, pd["defense"], rng)
            d["hp_e"] -= dmg
            lines.append(f"  E contrattacchi: {loop._hit_desc(dmg, d['emax'], d['name'], False, rng)}")
    elif what == "concentrati":
        d["focus"] = True
        lines.append("Respiri, raccogli tutto il tuo qi in un solo punto…")
    elif what == "pillola":
        from engine.systems import items
        pills = _pills(conn, player.id)
        if pills:
            cur = next((x for x in pills if "Curativa" in x["name"]), pills[0])
            heal = d["pmax"] * (0.5 if "Curativa" in cur["name"] else 0.25)
            d["hp_p"] = min(d["pmax"], d["hp_p"] + heal)
            items.use_item(conn, t, rng, player.id, cur["name"])
            lines.append(f"Ingoi {cur['name']}: il calore ti risale nelle vene, le ferite si richiudono.")
        else:
            lines.append("Frughi nella cintura: niente pillole.")
    else:
        mult, strikes, name = 1.0, 1, None
        if what == "tecnica" and len(parts) > 1:
            m = next((x for x in mvmod.available_moves(conn, player.id) if x["key"] == parts[1]), None)
            if m:
                if m.get("fuel") == "spirit":
                    spmod.spend(conn, m["spirit_cost"], player.id)
                else:
                    qimod.spend(conn, m["qi_cost"], player.id)
                mods = m["mods"]
                mult *= mods.get("attack_mult", 1.0)
                strikes += int(mods.get("extra_strikes", 0))
                d["cd"][m["key"]] = d["round"] + 3
                name = m["name"]
                from engine.systems import technique_forge
                technique_forge.on_use(conn, m)
                taken *= mods.get("taken_mult", 1.0)
        if d["focus"]:
            mult *= 1.9
            d["focus"] = False
        lines.append(f"⚔ Scateni {name}!" if name else loop._player_normal_line(None, rng))
        st = STYLES.get(d.get("style", "equilibrato"), STYLES["equilibrato"])
        mult *= d.get("adv", 1.0) * st[4]            # elementi e stile (l'impetuoso si scopre, il prudente no)
        dealt, crit_any = 0.0, False
        for _ in range(strikes):
            dmg, crit = combat._strike(pa["attack"] * mult, pd["defense"] * (1 - mods.get("pierce", 0.0)), rng)
            d["hp_e"] -= dmg
            dealt += dmg
            crit_any = crit_any or crit
        d["crit"] = crit_any
        lines.append("  " + loop._hit_desc(dealt, d["emax"], d["name"], crit_any, rng))

    if d["hp_e"] <= 0:
        _save(conn, d)
        return _won(conn, player, lines)
    # il nemico risponde
    st = STYLES.get(d.get("style", "equilibrato"), STYLES["equilibrato"])
    feint = d.get("feint")
    emult = (1.0 if feint else 1.7 if d["charge_e"] else 1.0) * st[3]
    if feint:
        lines.append(f"  Era una finta! {d['name']} non carica affatto: colpisce normale, e ride della tua guardia.")
        if what == "difendi":
            taken = 0.7                               # ti eri preparato al colpo sbagliato
    edmg, ecrit = combat._strike(pd["attack"] * emult, pa["defense"], rng)
    edmg *= taken
    d["hp_p"] -= edmg
    lines.append("  " + loop._enemy_line(d["name"], edmg, d["pmax"], ecrit, rng))
    if d["hp_p"] <= 0:
        state.delete(conn, KEY)
        return loop._auto_end_player(conn, t, rng, player, npc, d["round"], lines)
    _save(conn, d)
    return _next_turn(conn, player, lines)


def _won(conn, player, lines: list[str]) -> str:
    from engine.systems import encounters
    d = get(conn)
    lines.append(f"{d['name']} crolla in ginocchio. Il duello è tuo.")
    sc = {"key": "duello", "title": f"{d['name']} è a terra", "event_type": "combat", "sticky": True,
          "text": "\n".join(lines) + "\nOra decidi tu.",
          "ctx": {"npc_id": d["npc"], "npc_name": d["name"]},
          "choices": [{"label": "Lo finisci", "effects": {}, "command": "duello_azione finisci"},
                      {"label": "Lo risparmi (il mondo se lo ricorderà)", "effects": {},
                       "command": "duello_azione risparmia"}]}
    from engine.systems import dominion
    ok, p, why = dominion.seal_odds(conn, player.id, d["npc"], True)
    sc["choices"].append({"label": (f"Gli marchi l'anima: sarà tuo servo (~{int(p * 100)}%)" if ok
                                    else f"Sigillo dell'anima — impossibile: {why}"),
                          "effects": {}, "command": "duello_azione sigilla"})
    return encounters.start_scene(conn, player, sc, force=True) or ""


def finish(conn, player, kill: bool, seal: bool = False) -> str:
    from engine.cli import loop
    d = get(conn)
    if not d or d["hp_e"] > 0:
        return "Non c'è nessuno da finire."
    npc = entities.get_npc(conn, d["npc"])
    state.delete(conn, KEY)
    if npc is None or npc.status != "alive":
        return "Il tuo avversario non c'è più."
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 17 + d["npc"])
    return loop._auto_end_enemy(conn, t, rng, player, npc, d["round"], max(1.0, d["hp_p"]), d["pmax"],
                                d.get("crit", False), {}, None, [], force_died=kill, seal=seal)


def command(conn, player, arg: str) -> str:
    a = arg.strip().lower()
    if a in ("finisci", "uccidi"):
        return finish(conn, player, True)
    if a in ("risparmia", "grazia"):
        return finish(conn, player, False)
    if a in ("sigilla", "marchia"):
        from engine.systems import dominion
        d = get(conn)
        if d and d["hp_e"] <= 0:
            ok, _p, why = dominion.seal_odds(conn, player.id, d["npc"], True)
            if not ok:
                return _won(conn, player, [f"Non puoi marchiarne l'anima: {why}."])
        return finish(conn, player, False, seal=True)
    return act(conn, player, a)
