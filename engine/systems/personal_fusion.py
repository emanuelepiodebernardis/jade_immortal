"""
LE FUSIONI PERSONALI (Aggiornamento 80) — una via che non esiste in nessun libro, e il nome glielo dai tu.

Oltre alle ricette conosciute, quando due tuoi Dao sono entrambi a 250 (e non formano già una fusione nota), può
venirti — raramente — un'intuizione: quelle due vie potrebbero diventare una cosa sola, mai vista. Allora:

  battezza <nome>      fai nascere la fusione con il nome che scegli («battezza Fiamma del Lupo Bianco»):
                       cuore del Dao ≥ 70 e pietre per il ritiro. Nasce a un quarto della somma delle comprensioni.
  battezza no          lasci perdere l'intuizione

I suoi effetti nascono dai componenti: le leve dei due Dao (se sono vie nuove o fusioni), oppure la statistica che
ognuno rafforza; il costo è la media dei loro costi. Al massimo tre fusioni personali per vita. Le vedi con le
altre nell'albero e in 'fusione'.
"""

from __future__ import annotations

import random
import re

from engine.systems import state

KEY = "personal_fusions"
PENDING = "personal_fusion_idea"
MIN_COMP = 250
P_DAILY = 0.02
MAX = 3
_STAT_LEVER = {"attack": "atk", "defense": "def", "vitality": "vit", "spirit": "spirit"}


def all_(conn) -> list[dict]:
    lst = state.get_json(conn, KEY, []) or []
    _register(lst)
    return lst


def _register(lst: list[dict]) -> None:
    """Nel processo: il nome nell'elenco dei Dao (per le etichette) e la statistica per i punti."""
    from engine.generators import dao_gen
    from engine.systems import dao_training
    have = {r[0] for r in dao_gen.DAOS}
    for f in lst:
        if f["key"] not in have:
            dao_gen.DAOS.append((f["key"], f["name"], "fused", f.get("desc", "Una fusione che nessuno aveva mai visto.")))
        dao_training.DAO_STAT.setdefault(f["key"], f.get("stat", "attack"))
        dao_training.COMBAT_DAOS.add(f["key"])


def _comp(conn, k: str, pid: int) -> int:
    from engine.systems import dao_laws
    return dao_laws._comp(conn, k, pid)


def _effects(a: str, b: str) -> tuple[dict, dict, str]:
    from engine.systems import dao_laws, dao_training
    eff: dict[str, tuple[float, float]] = {}
    costs: list[dict] = []
    for k in (a, b):
        row = dao_laws.BY_KEY.get(k)
        src = row[8] if row else (dao_laws.FUSED[k][4] if k in dao_laws.FUSED else None)
        if row:
            costs.append(row[9])
        elif k in dao_laws.FUSED:
            costs.append(dao_laws.FUSED[k][5])
        if src:
            for lv, (per, cap) in src.items():
                if lv == "strikes":
                    eff[lv] = (min(per, eff.get(lv, (9, 0))[0]), max(cap, eff.get(lv, (9, 0))[1]))
                else:
                    p0, c0 = eff.get(lv, (0.0, 0.0))
                    eff[lv] = (round(max(p0, per) * 1.1, 3), round(max(c0, cap) * 1.1, 3))
        else:
            lv = _STAT_LEVER.get(dao_training.DAO_STAT.get(k, "attack"), "atk")
            p0, c0 = eff.get(lv, (0.0, 0.0))
            eff[lv] = (max(p0, 0.035), max(c0, 0.35))
    cost: dict[str, float] = {}
    for c in costs:
        for k, v in c.items():
            cost[k] = round(cost.get(k, 0) + v / 2, 3)
    if not cost:
        cost = {"spirit": -0.05}
    stat = dao_training.DAO_STAT.get(a, "attack")
    return eff, cost, stat


def _candidates(conn, pid: int) -> list[tuple[str, str]]:
    from engine.systems import dao_laws
    mine = sorted(k for k, c in ((r["dao_key"], int(r["comprehension"] or 0)) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos WHERE character_type='player' AND character_id=?;", (pid,)))
        if c >= MIN_COMP)
    known = [set(r[2]) for r in dao_laws.FUSED.values()] + [set(f["comps"]) for f in all_(conn)]
    out = []
    for i, a in enumerate(mine):
        for b in mine[i + 1:]:
            if not any({a, b} <= s for s in known):
                out.append((a, b))
    return out


def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems.dao_techniques import _dao_label
    if player is None or state.get_json(conn, PENDING, None) or len(all_(conn)) >= MAX:
        return []
    cands = _candidates(conn, player.id)
    if not cands or rng.random() >= P_DAILY:
        return []
    a, b = rng.choice(cands)
    state.set_json(conn, PENDING, {"a": a, "b": b})
    return [f"✺ UN'INTUIZIONE MAI AVUTA DA NESSUNO ✺\nMeditando, il {_dao_label(a)} e il {_dao_label(b)} smettono di "
            f"essere due cose. Non è nessuna delle fusioni scritte nei libri: è una via nuova, e ancora non ha un nome.\n"
            f"Scrivi 'battezza <nome>' per farla nascere (cuore del Dao ≥ 70, pietre per il ritiro), o 'battezza no'."]


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower().replace("à", "a").replace("è", "e").replace("ò", "o")
               .replace("ù", "u").replace("ì", "i")).strip("_")
    return "pf_" + (s[:24] or "via")


def baptize(conn, player, arg: str) -> str:
    from engine.systems import dao_heart, sects, dao_laws
    from engine.simulation import cultivation
    from engine.systems.dao_techniques import _dao_label
    idea = state.get_json(conn, PENDING, None)
    a = (arg or "").strip()
    if not idea:
        lst = all_(conn)
        if lst:
            return "Le tue fusioni personali: " + "; ".join(
                f"{f['name']} ({_dao_label(f['comps'][0])} + {_dao_label(f['comps'][1])})" for f in lst)
        return ("Non hai nessuna intuizione da battezzare. Arrivano da sole, di rado, quando due tuoi Dao sono entrambi "
                f"a {MIN_COMP} e non formano già una fusione nota.")
    if a.lower() in ("no", "lascia", "rinuncia"):
        state.delete(conn, PENDING)
        return "Lasci che l'intuizione svanisca. Forse un giorno tornerà."
    if len(a) < 3 or len(a) > 40:
        return "Dai un nome alla tua via (da 3 a 40 lettere): 'battezza Fiamma del Lupo Bianco'."
    if dao_heart.heart(conn) < dao_laws.FUSE_HEART:
        return f"Il tuo cuore del Dao è troppo agitato per far nascere una via nuova: serve almeno {dao_laws.FUSE_HEART}."
    cost = 1500 * (cultivation.realm_tier(conn, "player", player.id) or 1)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Il ritiro per far nascere una via nuova chiede {cost} pietre: non ti bastano."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    name = a if a.lower().startswith("dao ") else f"Dao «{a}»"
    key = _slug(a)
    while any(f["key"] == key for f in all_(conn)):
        key += "_"
    eff, cst, stat = _effects(idea["a"], idea["b"])
    f = {"key": key, "name": name, "comps": [idea["a"], idea["b"]], "eff": {k: list(v) for k, v in eff.items()},
         "cost": cst, "stat": stat, "desc": f"La via di {player.name}: {_dao_label(idea['a'])} e {_dao_label(idea['b'])} "
                                            "diventati una cosa sola."}
    lst = all_(conn) + [f]
    state.set_json(conn, KEY, lst)
    state.delete(conn, PENDING)
    _register(lst)
    conn.execute("INSERT OR IGNORE INTO daos (dao_key, name, level, description) VALUES (?, ?, 'fused', ?);",
                 (key, name, f["desc"]))
    start = max(10, (_comp(conn, idea["a"], player.id) + _comp(conn, idea["b"], player.id)) // 4)
    dao_laws.grant(conn, key, start, player.id)
    state.grant_title(conn, f"Padre del {name}")
    return (f"☯ NASCE UNA VIA NUOVA — {name.upper()} ☯\nNessuno l'aveva mai percorsa. Comprensione di partenza: "
            f"{start}. Effetti: " + ", ".join(dao_laws.LEVER_IT.get(k, k) for k in eff) + ". Costo: "
            + ", ".join(dao_laws.LEVER_IT.get(k, k) for k in cst) + f".\nAllenala con 'comprehend {key}'. "
            f"✧ Titolo: «Padre del {name}»")


def levers(conn, pid: int, tier_index) -> dict[str, float]:
    """Gli effetti delle fusioni personali, per dao_laws.levers."""
    out: dict[str, float] = {}
    for f in all_(conn):
        r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                         "AND dao_key=?;", (pid, f["key"])).fetchone()
        if not r:
            continue
        i = tier_index(int(r["comprehension"] or 0))
        for lv, (per, cap) in f["eff"].items():
            v = (cap if i >= per else 0) if lv == "strikes" else min(cap, per * i)
            out[lv] = out.get(lv, 0.0) + v
        if i >= 1:
            for lv, v in f["cost"].items():
                out[lv] = out.get(lv, 0.0) + v
    return out
