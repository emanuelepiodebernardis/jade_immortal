"""
STATI DI COMBATTIMENTO — ciò che rende ogni scontro diverso.

Ogni Dao porta uno stato (Fuoco → ustione, Acqua → gelo, Fulmine → stordimento, …).
Durante il combattimento automatico, a ogni colpo andato a segno c'è una probabilità
(che cresce con la comprensione del Dao) di applicarlo. Vale per te E per i nemici:
un coltivatore dell'Acqua ti gela, uno del Metallo ti fa sanguinare.

Si aggiungono: le catene elementali e le fusioni leggendarie (elements.py), i DOMINI
(un Dao "dominatore" applica il suo stato a ogni scambio), i talismani (buff della
prossima battaglia), lo spirito dell'arma e la bestia compagna.

Il modulo gestisce un contesto di scontro (FightCtx) che il loop di combattimento
interroga in pochi punti: inizio round, chi può agire, quanto colpisce, cosa succede
dopo un colpo, colpo mortale.
"""

from __future__ import annotations

import random
import sqlite3

# stato: (nome mostrato, bersaglio 'nemico'|'sé', durata in round)
STATES = {
    "ustione":       ("Ustione", "nemico", 3),
    "veleno":        ("Veleno", "nemico", 5),
    "gelo":          ("Gelo", "nemico", 1),
    "emorragia":     ("Emorragia", "nemico", 4),
    "stordimento":   ("Stordimento", "nemico", 1),
    "accecamento":   ("Accecamento", "nemico", 2),
    "pressione":     ("Pressione Spirituale", "nemico", 3),
    "terrore":       ("Terrore", "nemico", 3),
    "confusione":    ("Confusione", "nemico", 1),
    "retribuzione":  ("Retribuzione Karmica", "nemico", 1),
    "rigenerazione": ("Rigenerazione", "sé", 3),
    "scudo":         ("Scudo", "sé", 3),
    "velocita":      ("Velocità", "sé", 2),
    "drenaggio":     ("Drenaggio", "sé", 0),
    "vita":          ("Soffio Vitale", "sé", 0),
    "equilibrio":    ("Equilibrio", "sé", 0),
}

# Dao -> stato che può applicare
STATE_OF_DAO = {
    "fuoco": "ustione", "acqua": "gelo", "metallo": "emorragia", "legno": "rigenerazione",
    "terra": "scudo", "vento": "velocita", "fulmine": "stordimento", "luce": "accecamento",
    "oscurita": "drenaggio", "anima": "pressione", "spada": "emorragia", "sciabola": "emorragia",
    "pugno": "stordimento", "bastone": "scudo", "corpo": "rigenerazione",
    # superiori
    "karma": "retribuzione", "massacro": "terrore", "vita_morte": "vita", "samsara": "vita",
    "yinyang": "equilibrio", "caos": "caos", "sangue": "drenaggio", "illusione": "confusione",
    "stelle": "accecamento", "vuoto": "pressione", "creazione": "scudo",
}
_NEGATIVE = {"veleno", "ustione", "gelo", "emorragia", "stordimento", "accecamento", "pressione",
             "terrore", "confusione"}
_SELF_BUFFS = {"rigenerazione", "scudo", "velocita"}
_CAOS_POOL = ["ustione", "gelo", "emorragia", "stordimento", "accecamento", "pressione"]


def _procs(conn, ctype: str, cid: int) -> list[tuple[str, float, float, str]]:
    """(stato, probabilità, potenza, dao) per ogni Dao con comprensione >= 10."""
    from engine.systems import dao_training as dt
    out = []
    for r in conn.execute("SELECT dao_key, comprehension FROM character_daos "
                          "WHERE character_type=? AND character_id=? AND comprehension>=10;",
                          (ctype, cid)):
        st = STATE_OF_DAO.get(r["dao_key"])
        if not st:
            continue
        idx = dt._tier_index(r["comprehension"])
        out.append((st, min(0.5, 0.10 + 0.04 * idx), 1.0 + 0.15 * idx, r["dao_key"]))
    return out


class Side:
    def __init__(self, name: str, hp: float, attack: float):
        self.name = name
        self.hp = hp
        self.max = max(1.0, hp)
        self.attack = attack
        self.states: dict[str, dict] = {}
        self.procs: list[tuple[str, float, float, str]] = []
        self.domains: list[str] = []
        self.prof: dict = {}
        self.lethal_saves = 0
        self.atk_mult = 1.0           # moltiplicatore da elementi/fusioni/karma


class FightCtx:
    def __init__(self, conn: sqlite3.Connection, player_id: int, npc_id: int,
                 p_name: str, e_name: str, hp_p: float, hp_e: float,
                 atk_p: float, atk_e: float):
        from engine.systems import elements, karma, state as gstate
        self.p = Side("Tu", hp_p, atk_p)
        self.e = Side(e_name, hp_e, atk_e)
        self.lines_intro: list[str] = []
        # --- giocatore: stati dai Dao, catene, leggendarie, domini ---
        self.p.procs = _procs(conn, "player", player_id)
        self.p.prof = elements.profile(conn, "player", player_id)
        self.p.domains = [STATE_OF_DAO[k] for k in self.p.prof["domains"] if k in STATE_OF_DAO]
        self.e.procs = _procs(conn, "npc", npc_id)
        self.e.prof = {"state_chance": {}, "state_power": {}, "chance_mult": 1.0, "special": set()}
        from engine.systems import power_budget
        trk = power_budget.Tracker(self)                 # (Agg. 58) quanto pesa ogni fonte, e i tetti
        mp, me, phrase = elements.matchup(conn, player_id, npc_id)
        self.p.atk_mult *= mp * (1.0 + max(-0.3, self.p.prof["attack"]))
        trk.mark("elementi")
        self.e.atk_mult *= me
        if phrase:
            self.lines_intro.append(phrase)
        pr = self.p.prof
        if pr.get("chain_name"):
            self.lines_intro.append(f"☯ I tuoi elementi si generano a vicenda: «{pr['chain_name']}».")
        if pr.get("legendary"):
            self.lines_intro.append("✦ Fusioni leggendarie: " + ", ".join(pr["legendary"]) + ".")
        for k in pr.get("domains", []):
            from engine.systems.dao_techniques import _dao_label
            self.lines_intro.append(f"◎ Apri il DOMINIO {_dao_label(k)[4:]}: lo spazio attorno "
                                    f"a voi obbedisce al tuo Dao.")
        self.p.lethal_saves = (1 if "survive_lethal" in pr["special"] else 0) + \
                              (1 if "survive_lethal_2" in pr["special"] else 0)
        # karma: la retribuzione colpisce chi ha peccato
        self.enemy_karma = karma.get_karma(conn, "npc", npc_id)
        # talismani preparati per questo scontro (consumati)
        buffs = gstate.get_json(conn, "combat_buffs", []) or []
        if buffs:
            gstate.delete(conn, "combat_buffs")
        self.buffs = buffs
        for b in buffs:
            self.lines_intro.append(f"Il tuo talismano si accende: {b.get('name', 'talismano')}.")
            if b.get("lethal_save"):
                self.p.lethal_saves += 1
            st = b.get("state")
            if st and STATES.get(st, ("", "nemico"))[1] == "sé":
                self._apply(self.p, st, b.get("power", 1.5))
            elif st:
                self._apply(self.e, st, b.get("power", 1.5))
        # tecniche dei MAESTRI SEGRETI: ognuna porta uno stato
        for st, ch, pw, nm in gstate.get_json(conn, "master_procs", []) or []:
            self.p.procs.append((st, ch, pw, nm))
        # RADICI SPIRITUALI: talenti (stati elementali) e combinazioni
        from engine.systems import spirit_roots
        rp = spirit_roots.combat_profile(conn, "player", player_id)
        self.p.procs += rp["procs"]
        self.p.atk_mult *= 1.0 + rp["attack"] + rp["strike"] * 0.5
        trk.mark("radici")
        if rp["taken"]:
            pr["taken"] = pr.get("taken", 0.0) + rp["taken"]
        # CLASSE (arte + elementi): formazioni mobili/piazzate, aure elementali
        from engine.systems import classes
        self.lines_intro += classes.combat(conn, player_id, npc_id, self)
        trk.mark("classe")
        # LIGNAGGI DI SANGUE: manifestazioni, tecnica innata, doni, trasformazione
        from engine.systems import bloodlines
        self.lines_intro += bloodlines.combat(conn, player_id, self)
        trk.mark("sangue")
        from engine.systems import prodigies, heaven_trib
        self.lines_intro += prodigies.enemy_bonus(conn, npc_id, self)
        trk.mark("prodigi")
        self.lines_intro += heaven_trib.combat(conn, self)
        trk.mark("tribolazione_celeste")
        from engine.systems import mentor_ring, celestial_elements, lost_legacy, gu, soul_war, svolte
        for _m in (mentor_ring, celestial_elements, lost_legacy, gu, soul_war, svolte):
            self.lines_intro += _m.combat(conn, self)
        trk.mark("anello e altri")
        # COSTITUZIONE SPECIALE
        from engine.systems import constitutions
        self.lines_intro += constitutions.combat(conn, self)
        trk.mark("corpo")
        _c = constitutions.get(conn)
        if _c and _c["key"] == "ombra" and conn.execute(
                "SELECT 1 FROM character_daos WHERE character_type='npc' AND character_id=? AND dao_key='luce' "
                "AND comprehension>0;", (npc_id,)).fetchone():
            self.e.atk_mult *= 1.2                 # la luce brucia il Corpo dell'Ombra
        # extra (spirito dell'arma, bestia): aggiunti dal chiamante via add_proc
        if "nullify" in pr["special"]:
            self.e.procs = [x for x in self.e.procs if STATES.get(x[0], ("", "nemico"))[1] != "sé"]
        trk.finish(conn)

    # ---------- utilità ----------
    def add_proc(self, side: str, state: str, chance: float, power: float, source: str) -> None:
        (self.p if side == "p" else self.e).procs.append((state, chance, power, source))

    def _apply(self, target: Side, st: str, power: float) -> bool:
        info = STATES.get(st)
        if not info:
            return False
        if st == "emorragia":
            cur = target.states.get(st, {"turns": 0, "stacks": 0, "power": power})
            cur["stacks"] = min(5, cur["stacks"] + 1)
            cur["turns"] = info[2]
            cur["power"] = max(cur["power"], power)
            target.states[st] = cur
            return True
        new = st not in target.states
        target.states[st] = {"turns": info[2], "stacks": 1, "power": power}
        return new

    def _other(self, side: Side) -> Side:
        return self.e if side is self.p else self.p

    # ---------- inizio round: danni nel tempo, rigenerazione, domini ----------
    def round_start(self, rng: random.Random) -> list[str]:
        out = []
        for side in (self.p, self.e):
            foe = self._other(side)
            for st, data in list(side.states.items()):
                if st == "ustione":
                    dmg = foe.attack * 0.10 * data["power"]
                    side.hp -= dmg
                    out.append("  ↳ Le fiamme ti bruciano." if side is self.p
                               else f"  ↳ {side.name} brucia.")
                elif st == "veleno":
                    side.hp -= side.max * 0.03 * data["power"]
                    out.append("  ↳ Il veleno ti scorre nelle vene." if side is self.p
                               else f"  ↳ Il veleno consuma {side.name}.")
                elif st == "emorragia":
                    side.hp -= side.max * 0.025 * data["stacks"] * data["power"]
                    if data["stacks"] >= 3:
                        out.append(f"  ↳ {'Sanguini' if side is self.p else side.name + ' sanguina'} "
                                   f"copiosamente ({data['stacks']} ferite).")
                elif st == "rigenerazione":
                    side.hp = min(side.max, side.hp + side.max * 0.04 * data["power"])
                data["turns"] -= 1
                if data["turns"] <= 0 and st not in ("gelo", "stordimento", "confusione"):
                    side.states.pop(st, None)
        # i domini applicano il loro stato a ogni scambio
        for st in self.p.domains:
            tgt = self.p if STATES.get(st, ("", "nemico"))[1] == "sé" else self.e
            self._apply(tgt, st, 2.0)
        if "cycle_states" in self.p.prof.get("special", set()):
            st = rng.choice(["ustione", "gelo", "emorragia", "scudo", "rigenerazione"])
            tgt = self.p if STATES[st][1] == "sé" else self.e
            if self._apply(tgt, st, 1.5):
                out.append(f"  ☯ Il Ciclo dei Cinque Elementi ruota: {STATES[st][0]}.")
        return out

    # ---------- chi può agire ----------
    def blocked(self, who: str, rng: random.Random) -> str | None:
        side = self.p if who == "p" else self.e
        for st, msg_p, msg_e in (("stordimento", "Sei stordito: perdi il turno!",
                                  "{n} è stordito e non reagisce."),
                                 ("gelo", "Il gelo ti blocca le membra!",
                                  "{n} è intrappolato nel gelo.")):
            if st in side.states:
                side.states.pop(st)
                return msg_p if side is self.p else msg_e.format(n=side.name)
        if "confusione" in side.states and rng.random() < 0.7:
            side.states.pop("confusione")
            return ("Colpisci un'illusione!" if side is self.p
                    else f"{side.name} colpisce un'illusione e manca il bersaglio.")
        return None

    def attack_factor(self, who: str) -> float:
        side = self.p if who == "p" else self.e
        f = side.atk_mult
        if "pressione" in side.states:
            f *= 0.8
        if "terrore" in side.states:
            f *= 0.75
        if who == "p" and "retribuzione" in [p[0] for p in self.p.procs] and self.enemy_karma < 0:
            f *= 1.0 + min(0.5, -self.enemy_karma / 600) * self.p.prof.get("state_power", {}).get("retribuzione", 1.0)
        return f

    def missed(self, who: str, rng: random.Random) -> bool:
        side = self.p if who == "p" else self.e
        if who == "e" and rng.random() < self.p.prof.get("evade", 0.0):
            return True                       # le ali del sangue: schivi
        return "accecamento" in side.states and rng.random() < 0.45

    def extra_strikes(self, who: str) -> int:
        side = self.p if who == "p" else self.e
        n = 1 if "velocita" in side.states else 0
        if who == "p":
            n += int(self.p.prof.get("extra_strikes", 0))
        return n

    def pierce(self, who: str) -> float:
        return self.p.prof.get("pierce", 0.0) if who == "p" else 0.0

    def crit_bonus(self, who: str) -> float:
        return self.p.prof.get("crit", 0.0) if who == "p" else 0.0

    def taken_mult(self, who: str) -> float:
        return max(0.4, 1.0 - self.p.prof.get("taken", 0.0)) if who == "p" else 1.0

    def absorb(self, target: str, dmg: float) -> float:
        side = self.p if target == "p" else self.e
        sh = side.states.get("scudo")
        if not sh:
            return dmg
        cap = side.max * 0.12 * sh["power"]
        used = min(dmg, cap)
        side.states.pop("scudo")
        return dmg - used

    # ---------- dopo un colpo andato a segno ----------
    def on_hit(self, who: str, rng: random.Random, dealt: float) -> list[str]:
        side = self.p if who == "p" else self.e
        foe = self._other(side)
        out = []
        pr = side.prof
        cm = pr.get("chance_mult", 1.0)
        for st, ch, power, _src in side.procs:
            chance = ch * cm + pr.get("state_chance", {}).get(st, 0.0) + pr.get("state_chance", {}).get("*", 0.0)
            if rng.random() >= chance:
                continue
            power *= pr.get("state_power", {}).get(st, 1.0)
            if st == "caos":
                st = rng.choice(_CAOS_POOL)
            if st == "drenaggio":
                heal = dealt * 0.20 * power
                side.hp = min(side.max, side.hp + heal)
                if who == "p":
                    out.append("  ↳ Drenaggio: bevi la sua forza vitale.")
                continue
            if st == "vita":
                side.hp = min(side.max, side.hp + side.max * 0.06 * power)
                if who == "p":
                    out.append("  ↳ Soffio Vitale: le tue ferite si richiudono.")
                continue
            if st == "equilibrio":
                for neg in list(side.states):
                    if neg in _NEGATIVE:
                        side.states.pop(neg)
                side.hp = min(side.max, side.hp + side.max * 0.04)
                if who == "p":
                    out.append("  ↳ Equilibrio: Yin e Yang tornano in armonia.")
                continue
            if st == "retribuzione":
                continue          # passiva (attack_factor)
            target = side if STATES[st][1] == "sé" else foe
            if self._apply(target, st, power):
                tname = "te" if target is self.p else target.name
                if STATES[st][1] == "sé":
                    out.append(f"  ↳ {STATES[st][0]}{'' if who == 'p' else ' per ' + side.name}.")
                else:
                    out.append(f"  ↳ {STATES[st][0]} su {tname}.")
        return out[:2]

    # ---------- colpo mortale ----------
    def lethal(self, who: str) -> str | None:
        side = self.p if who == "p" else self.e
        if side.hp > 0 or side.lethal_saves <= 0:
            return None
        side.lethal_saves -= 1
        side.hp = side.max * 0.25
        return ("✧ Il colpo mortale non è mai accaduto: il Fato ti riporta in piedi!"
                if side is self.p else f"{side.name} si rialza contro ogni legge.")
