"""
I REGNI DELLE RAZZE ANTICHE — campioni, sangue d'alto lignaggio, reliquie, e la scala che porta
da straniero a SOVRANO (o ELETTO) di una razza.

Si innesta su `races` (rapporto e onore) e su `bloodlines` (i lignaggi di sangue).

CAMPIONI
  Nelle terre di ogni razza veglia un CAMPIONE, e quando lo batti ne sorge uno di rango più alto:
    Draghi   Guardiano della Rupe · Campione delle Scaglie · Generale del Tuono · Principe dei Draghi · RE DRAGO
    Demoni   Sentinella dell'Abisso · Campione delle Fiamme Nere · Generale Demone · Principe Demone · IMPERATORE
    Spiriti  Guardiano dei Boschi · Campione delle Radici · Generale del Vento Verde · Principe dei Boschi · CUSTODE
    Giganti  Guardiano dei Monti · Campione di Pietra · Generale dei Titani · Principe dei Giganti · RE DEI GIGANTI
    Maree    Sentinella delle Maree · Campione degli Abissi · Generale delle Correnti · Principe · REGINA DELLE MAREE
  Oltre il sovrano si risvegliano gli ANTENATI (senza fine).
  Batterlo e…
    · UCCIDERLO: ti lascia il suo SANGUE (essenza d'alto lignaggio: Drago Celeste, Demone Celeste,
      Gigante Antico, Leviatano; gli Spiriti lasciano un'essenza d'ANIMA) e a volte una RELIQUIA.
      I Demoni rispettano chi uccide; le altre razze se lo ricordano.
    · RISPARMIARLO: si inchina e ti dona una goccia del suo sangue (metà), con molto onore.
    · SIGILLARLO: diventa tuo servo; la razza si offende. Marchiare il SOVRANO ti dà il trono col terrore.
  Chi uccide creature potenti nelle loro terre raccoglie almeno una TRACCIA di sangue o di spirito.

RELIQUIE (le ossa e i tesori dei regni: Scaglia del Re Drago, Corona d'Ossidiana, Seme dell'Albero
  Madre, Martello del Primo Gigante, Perla della Regina delle Maree…)
  Si trovano sui campioni, esplorando le loro terre, raramente tra i premi più alti. Puoi:
    · ASSORBIRLE ('use <reliquia>'): un balzo enorme del sangue (o dell'anima);
    · OFFRIRLE alla razza ('razza <razza> offri'): onore, rapporto, e contano per salire di grado.

LA SCALA (razza <razza> ascendi)   — sangue = grado del tuo lignaggio di quella razza
  1 Discepolo   rapporto ≥10 e (sangue Risvegliato o onore 50)
  2 Campione    hai battuto il 2° campione e (sangue Concentrato o onore 200)
  3 Anziano     3° campione, sangue Puro, 1 reliquia offerta
  4 Principe    4° campione, sangue Ancestrale, 2 reliquie offerte
  5 ELETTO      (via della pace) sangue Sacro, 3 reliquie offerte, rapporto ≥80: il sovrano ti nomina erede
  5 SOVRANO     (via della forza) hai battuto il sovrano, sangue Ancestrale, 2 reliquie offerte
  Ogni grado: una tecnica della razza, un dono di sangue, un titolo. Dall'Anziano doni periodici;
  dal Principe i loro guerrieri combattono con te; da Sovrano/Eletto la razza ti versa tributi e
  marcia nelle tue guerre.
"""

from __future__ import annotations

import random

from engine.core import entities, tick as tick_mod
from engine.systems import state

KEY = "race_realms"
DAY = 120

# razza -> (specie del sangue, elementi, famiglie di sangue affini, tipo di creatura, cognome)
BLOOD = {
    "draghi": ("Drago Celeste", ["fulmine", "acqua"], ["drago"], "beast", "Ao"),
    "demoni": ("Demone Celeste", ["oscurita", "fuoco"], ["demone"], "demon", "Mo"),
    "spiriti": ("Spirito Silvano", ["legno", "luce"], ["silvano", "qilin"], "spirit", "Mu"),
    "giganti": ("Gigante Antico", ["terra", "corpo"], ["gigante", "orso"], "human", "Kua"),
    "maree": ("Leviatano delle Maree", ["acqua"], ["leviatano", "tartaruga", "serpente"], "beast", "Hai"),
}
_GIVEN = ["Lie", "Shun", "Qin", "Run", "Guang", "Ming", "Xuan", "Yan", "Jin", "Han", "Ling", "Wei", "Tian",
          "Zhao", "Kun", "Lan", "Feng", "Ying", "Hao", "Ruo", "Chen", "Ye", "Su", "Yao"]
RANKS = {
    "draghi": ["Guardiano della Rupe", "Campione delle Scaglie", "Generale del Tuono", "Principe dei Draghi", "Re Drago"],
    "demoni": ["Sentinella dell'Abisso", "Campione delle Fiamme Nere", "Generale Demone", "Principe Demone",
               "Imperatore Demone"],
    "spiriti": ["Guardiano dei Boschi", "Campione delle Radici", "Generale del Vento Verde", "Principe dei Boschi",
                "Custode dell'Albero Madre"],
    "giganti": ["Guardiano dei Monti", "Campione di Pietra", "Generale dei Titani", "Principe dei Giganti",
                "Re dei Giganti"],
    "maree": ["Sentinella delle Maree", "Campione degli Abissi", "Generale delle Correnti", "Principe delle Maree",
              "Regina delle Maree"],
}
RELICS = {
    "draghi": ["Scaglia del Re Drago Primordiale", "Perla del Drago Celeste", "Corno dell'Antenato Azzurro",
               "Osso del Drago del Primo Tuono"],
    "demoni": ["Sigillo dell'Imperatore Demone", "Occhio dell'Abisso Senza Fondo", "Corona d'Ossidiana",
               "Cuore della Fiamma Nera"],
    "spiriti": ["Seme dell'Albero Madre", "Lacrima della Dea dei Boschi", "Ramo del Primo Inverno",
                "Lanterna delle Lucciole Antiche"],
    "giganti": ["Martello del Primo Gigante", "Cuore di Montagna", "Elmo del Titano", "Catena del Cielo Spezzato"],
    "maree": ["Perla della Regina delle Maree", "Conchiglia del Leviatano", "Tridente Spezzato",
              "Specchio della Luna Annegata"],
}
STANDING = ["Straniero", "Discepolo", "Campione", "Anziano", "Principe"]
TOP = {  # (via della forza, via della pace)
    "draghi": ("Re Drago", "Eletto dei Draghi"), "demoni": ("Imperatore Demone", "Eletto dell'Abisso"),
    "spiriti": ("Custode dell'Albero Madre", "Eletto dei Boschi"), "giganti": ("Re dei Giganti", "Eletto dei Titani"),
    "maree": ("Sovrano delle Maree", "Eletto delle Maree"),
}
TECH = {"draghi": "Ruggito del Drago", "demoni": "Fiamma Nera dell'Abisso", "spiriti": "Respiro della Foresta",
        "giganti": "Pugno della Montagna", "maree": "Marea Furiosa"}
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def _name(key: str) -> str:
    from engine.systems import races
    return races.RACES[key][0]


def get(conn) -> dict:
    d = state.get_json(conn, KEY, {}) or {}
    for k in BLOOD:
        d.setdefault(k, {"beaten": 0, "champ": None, "champ_rank": 0, "relics": 0, "standing": 0, "path": ""})
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def rank_title(key: str, r: int) -> str:
    if r <= 5:
        return RANKS[key][r - 1]
    return f"Antenato Risvegliato {_ROMAN[r - 6] if r - 6 < len(_ROMAN) else r - 5}"


def standing_name(key: str, n: int, path: str = "") -> str:
    if n >= 5:
        return TOP[key][1 if path == "eletto" else 0]
    return STANDING[n]


def _land(conn, key):
    """Le terre della razza (se il mondo non ha il tipo di luogo previsto, ne sceglie uno selvaggio)."""
    from engine.systems import races
    d = races.all_r(conn)
    if d[key].get("land"):
        return d[key]["land"]
    taken = {r.get("land") for r in d.values()}
    rows = [r["id"] for r in conn.execute("SELECT id FROM locations WHERE location_type IN "
                                          "('forbidden_zone','ruin','mountain') ORDER BY id DESC;")]
    rows += [r["id"] for r in conn.execute("SELECT id FROM locations WHERE location_type<>'city' ORDER BY id DESC;")]
    pick = next((x for x in rows if x not in taken), rows[0] if rows else None)
    if pick:
        d[key]["land"] = pick
        races._save(conn, d)
    return pick


def race_of_npc(conn, npc_id: int):
    d = get(conn)
    for k, r in d.items():
        if r.get("champ") == npc_id:
            return k, r.get("champ_rank", 1)
    return None, 0


def blood_grade(conn, key: str) -> int:
    """Grado del tuo lignaggio più forte affine a quella razza (-1 = nessuno)."""
    from engine.systems import bloodlines
    fams = set(BLOOD[key][2])
    best = -1
    for ln in bloodlines.all_lines(conn).values():
        if fams & set(ln.get("families", [])) or any(f in ln.get("species", "").lower() for f in fams):
            best = max(best, bloodlines.grade_index(ln.get("conc", 0)))
    return best


def _tier(conn, ctype, cid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, ctype, cid) or 1


# ============================================================ campioni

def ensure_champion(conn, player, key: str):
    d = get(conn)
    r = d[key]
    if r.get("champ"):
        row = conn.execute("SELECT status FROM npcs WHERE id=?;", (r["champ"],)).fetchone()
        if row and row["status"] == "alive":
            return r["champ"]
    land = _land(conn, key)
    if not land:
        return None
    from engine.systems import npc_factory, beasts
    rank = r["beaten"] + 1
    rng = random.Random(tick_mod.get_tick(conn) * 7 + rank * 31 + len(key))
    used = {x["name"] for x in conn.execute("SELECT name FROM npcs;")}
    sur = BLOOD[key][4]
    nm = next((f"{sur} {g}" for g in rng.sample(_GIVEN, len(_GIVEN)) if f"{sur} {g}" not in used),
              f"{sur} {rng.choice(_GIVEN)} {rank}")
    tier = _tier(conn, "player", player.id) + (rank - 1) // 2
    nid = npc_factory.spawn(conn, rng, archetype="guardia", location_id=land, tier=tier, stage=min(10, 3 + rank),
                            name=nm, traits={"pride": 85, "honor": 70, "courage": 90})
    kind = BLOOD[key][3]
    conn.execute("UPDATE npcs SET kind=?, description=? WHERE id=?;",
                 (kind, f"{rank_title(key, rank)} dei {_name(key)}.", nid))
    if kind == "beast":
        beasts.ensure_table(conn)
        conn.execute("INSERT OR REPLACE INTO beast_traits (npc_id, species, rarity, talent, elements) VALUES "
                     "(?, ?, 'leggendaria', ?, ?);", (nid, BLOOD[key][0], ["dotata", "rara", "prodigio", "divina"][min(3, rank - 1)],
                      ",".join(BLOOD[key][1])))
    if rank > 1:
        npc_factory.raise_npc(conn, nid, 2 * (rank - 1))
    r["champ"], r["champ_rank"] = nid, rank
    _save(conn, d)
    return nid


def challenge(conn, player, key: str) -> str:
    from engine.cli import loop
    land = _land(conn, key)
    if land and player.location_id != land:
        ln = conn.execute("SELECT name FROM locations WHERE id=?;", (land,)).fetchone()
        return f"Il campione dei {_name(key)} attende nelle sue terre, a {ln['name'] if ln else '?'}. ('vai #{land}')"
    nid = ensure_champion(conn, player, key)
    if not nid:
        return "Nessun campione ti attende."
    conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, nid))
    n = entities.get_npc(conn, nid)
    d = get(conn)
    intro = (f"⚔ {n.name}, {rank_title(key, d[key]['champ_rank'])} dei {_name(key)}, scende nel cerchio di pietre.")
    return intro + "\n" + loop.dispatch(conn, f"duello {n.name.split()[1] if len(n.name.split()) > 1 else n.name}",
                                        allow_nl=False)


def _essence(conn, key: str, amount: float, title: str):
    from engine.systems import items, rewards
    sp, els, *_ = BLOOD[key]
    if key == "spiriti":
        nm = f"Essenza d'Anima del {title}"
        eff = {"soul_xp": round(amount * 3, 1), "dao_key": "anima", "dao_gain": max(2, int(amount / 3)),
               "bloodline": {"species": sp, "elements": els, "gain": round(amount * 0.5, 1)}}
        desc = "L'anima distillata di uno spirito antico: tempra lo spirito e risveglia la linfa silvana."
    else:
        nm = f"Sangue del {title}"
        eff = {"bloodline": {"species": sp, "elements": els, "gain": round(amount, 1)}}
        desc = f"Sangue d'alto lignaggio ({sp}): assorbilo con 'use'."
    rar = "leggendario" if amount >= 40 else "prezioso" if amount >= 15 else "raro"
    iid = items.create_item(conn, nm, "essenza", rar, desc, eff)
    rewards._remember(conn, nm, "sangue", rar, desc)
    return iid, nm


def relic_item(conn, key: str, rng, power: int = 1):
    from engine.systems import items, rewards
    nm = rng.choice(RELICS[key])
    desc = (f"Reliquia del regno dei {_name(key)}. Assorbila ('use') per un balzo del sangue, "
            f"o offrila ('razza {key} offri') per onore e per salire di grado.")
    iid = items.create_item(conn, nm, "reliquia", "leggendario", desc, {"race_relic": key, "power": int(power)})
    rewards._remember(conn, nm, "reliquia", "leggendario", desc)
    return iid, nm


def on_defeat(conn, t, rng, player, npc, mode: str) -> list[str]:
    """mode: 'kill' | 'spare' | 'seal'. Vale per i campioni e per le creature delle terre delle razze."""
    from engine.systems import items, races
    key, rank = race_of_npc(conn, npc.id)
    out: list[str] = []
    if not key:
        if mode == "kill":
            out += _trace(conn, t, rng, player, npc)
        return out
    d = get(conn)
    r = d[key]
    r["beaten"] = max(r["beaten"], rank)
    r["champ"] = None
    _save(conn, d)
    tier = _tier(conn, "npc", npc.id)
    title = rank_title(key, rank)
    amount = 12 * rank * (1 + 0.3 * tier)
    if mode == "kill":
        iid, nm = _essence(conn, key, amount, title)
        items.grant(conn, "player", player.id, iid)
        out.append(f"🩸 Dal corpo del {title} raccogli: {nm}! ('use essenze')")
        if rng.random() < 0.3 + 0.1 * rank:
            rid, rn = relic_item(conn, key, rng, rank)
            items.grant(conn, "player", player.id, rid)
            out.append(f"🏺 Tra i suoi resti brilla una RELIQUIA: {rn}.")
        out += races.adjust(conn, key, rel=3 if key == "demoni" else -5 * rank, honor=40 * rank)
        out.append("I Demoni ruggiscono di approvazione: la forza è legge." if key == "demoni"
                   else f"I {_name(key)} piangono il loro {title}. Ricorderanno.")
    elif mode == "spare":
        iid, nm = _essence(conn, key, amount * 0.5, title)
        items.grant(conn, "player", player.id, iid)
        out.append(f"🤝 Il {title} si inchina e si incide il palmo: «Il mio sangue riconosce il tuo.» Ricevi: {nm}.")
        out += races.adjust(conn, key, rel=10, honor=70 * rank)
    else:  # sigillo
        out += races.adjust(conn, key, rel=-25, honor=20 * rank)
        out.append(f"I {_name(key)} vedono il loro {title} con il tuo marchio nell'anima: un affronto che non dimenticheranno.")
        if rank >= 5:
            d = get(conn)
            d[key]["standing"], d[key]["path"] = 5, "sigillo"
            _save(conn, d)
            out.append(f"👑 Con il loro sovrano in catene, i {_name(key)} si piegano: sei {TOP[key][0]}, per terrore.")
            state.grant_title(conn, TOP[key][0])
    out.append(f"Un nuovo campione sorgerà nelle terre dei {_name(key)}: {rank_title(key, rank + 1)}.")
    return out


def _land_key(conn, loc):
    for k in BLOOD:
        if _land(conn, k) == loc:
            return k
    return None


def _trace(conn, t, rng, player, npc) -> list[str]:
    """Una creatura potente uccisa nelle terre di una razza lascia una traccia di sangue o spirito."""
    from engine.systems import items
    key = _land_key(conn, player.location_id)
    if not key:
        return []
    k = conn.execute("SELECT kind FROM npcs WHERE id=?;", (npc.id,)).fetchone()
    if not k or k["kind"] not in ("beast", "demon", "spirit") and key != "giganti":
        return []
    tier = _tier(conn, "npc", npc.id)
    if tier < _tier(conn, "player", player.id) - 1 or rng.random() > 0.45:
        return []
    iid, nm = _essence(conn, key, 3 * (1 + 0.3 * tier), "Traccia dei " + _name(key))
    items.grant(conn, "player", player.id, iid)
    return [f"🩸 Raccogli una traccia: {nm}."]


# ============================================================ la scala

def requirements(conn, key: str, n: int) -> list[tuple[str, bool]]:
    from engine.systems import races, bloodlines
    d = get(conn)[key]
    rr = races.all_r(conn)[key]
    bg = blood_grade(conn, key)
    g = lambda i: bloodlines.GRADES[i][1] if i < len(bloodlines.GRADES) else "Caos"  # noqa: E731
    if n == 1:
        return [("rapporto ≥ 10", rr["rel"] >= 10), (f"sangue {g(1)} oppure onore 50", bg >= 1 or rr["honor"] >= 50)]
    if n == 2:
        return [(f"battere il {rank_title(key, 2)}", d["beaten"] >= 2),
                (f"sangue {g(2)} oppure onore 200", bg >= 2 or rr["honor"] >= 200)]
    if n == 3:
        return [(f"battere il {rank_title(key, 3)}", d["beaten"] >= 3), (f"sangue {g(3)}", bg >= 3),
                ("1 reliquia offerta", d["relics"] >= 1)]
    if n == 4:
        return [(f"battere il {rank_title(key, 4)}", d["beaten"] >= 4), (f"sangue {g(4)}", bg >= 4),
                ("2 reliquie offerte", d["relics"] >= 2)]
    return []


def top_paths(conn, key: str) -> dict:
    from engine.systems import races, bloodlines
    d = get(conn)[key]
    rr = races.all_r(conn)[key]
    bg = blood_grade(conn, key)
    G = bloodlines.GRADES
    return {"sovrano": [(f"battere il {rank_title(key, 5)}", d["beaten"] >= 5), (f"sangue {G[4][1]}", bg >= 4),
                        ("2 reliquie offerte", d["relics"] >= 2)],
            "eletto": [(f"sangue {G[5][1]}", bg >= 5), ("3 reliquie offerte", d["relics"] >= 3),
                       ("rapporto ≥ 80", rr["rel"] >= 80)]}


def ascend(conn, player, key: str) -> str:
    from engine.systems import races, bloodlines, chronicle
    d = get(conn)
    r = d[key]
    n = r["standing"] + 1
    if r["standing"] >= 5:
        return f"Sei già {standing_name(key, 5, r['path'])}: non c'è trono più alto tra i {_name(key)}."
    if races.all_r(conn)[key]["rel"] <= -60:
        return f"I {_name(key)} sono in guerra con te: nessuna cerimonia, solo battaglia."
    path = ""
    if n == 5:
        tp = top_paths(conn, key)
        path = "eletto" if all(ok for _l, ok in tp["eletto"]) else "sovrano" if all(ok for _l, ok in tp["sovrano"]) else ""
        if not path:
            miss = "; ".join(f"{p}: " + ", ".join(lbl for lbl, ok in req if not ok) for p, req in tp.items())
            return f"Il trono dei {_name(key)} non è ancora tuo. Ti manca — {miss}."
    else:
        miss = [lbl for lbl, ok in requirements(conn, key, n) if not ok]
        if miss:
            return f"Per diventare {STANDING[n]} dei {_name(key)} ti manca: " + ", ".join(miss) + "."
    r["standing"], r["path"] = n, path or r.get("path", "")
    _save(conn, d)
    t = tick_mod.get_tick(conn)
    rng = random.Random(t + n)
    title = f"{standing_name(key, n, path)}" + ("" if n >= 5 else f" dei {_name(key)}")
    lines = [_CEREMONY[key][min(n, 5) - 1], f"✦ Ora sei {title}. ✦"]
    state.grant_title(conn, title)
    # tecnica della razza
    tname = f"{TECH[key]} ({_ROMAN[n - 1]})"
    conn.execute("INSERT INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, learned_tick) "
                 "VALUES (?, NULL, ?, ?, ?, ?);", (player.id, f"race:{key}:{n}", tname, 0.04 * n, t))
    lines.append(f"Ti insegnano «{tname}» (+{4 * n}% potenza).")
    lines += bloodlines.gain(conn, t, rng, player, BLOOD[key][0], BLOOD[key][1], 10.0 * n)
    lines += races.adjust(conn, key, rel=10 * n, honor=100 * n)
    if n >= 5:
        races.adjust(conn, key, rel=100)
        lines.append(("Il vecchio sovrano posa la corona sul tuo capo e ti chiama figlio." if path == "eletto" else
                      "Siedi sul trono del sovrano che hai abbattuto. Nessuno osa alzare lo sguardo.")
                     + f" I {_name(key)} ti verseranno tributo e marceranno nelle tue guerre.")
    chronicle.add(conn, "scelta", f"Diventa {title}.")
    return "\n".join(lines)


_CEREMONY = {
    "draghi": ["Sulla rupe del vento, un vecchio drago ti fa bere una goccia del suo sangue: «Ora sei dei nostri, piccolo.»",
               "I draghi giovani ti sfidano a volare con loro nella tempesta: torni con le scaglie del tuono sulla pelle.",
               "Il consiglio degli anziani ti accoglie nella caverna delle perle: ti siedi tra loro.",
               "Il Re Drago ti posa un artiglio sulla spalla: «Sangue del mio sangue.» Le montagne tuonano.",
               "Mille draghi si levano in cielo e si inchinano nell'aria. Il tuo ruggito è ora la loro legge."],
    "demoni": ["Nell'Abisso ti marchiano la mano con la fiamma nera: brucia, poi diventa parte di te.",
               "Combatti nel Pozzo delle Ossa finché non resti l'unico in piedi: ti chiamano campione.",
               "Gli anziani demoni ti offrono una coppa di sangue nero. La bevi tutta. Ridono, e ti fanno posto.",
               "L'Imperatore Demone ti fissa a lungo con i suoi tre occhi, poi ti cede un frammento della corona.",
               "L'Abisso intero si inginocchia. Le fiamme nere cambiano colore: ora ardono del tuo."],
    "spiriti": ["Una lucciola ti si posa sulla fronte e non se ne va più: i boschi ti hanno accolto.",
                "Gli spiriti ti insegnano a parlare con le radici: la foresta ti chiama campione.",
                "Nel cerchio delle querce antiche ti fanno sedere tra gli anziani, e il vento tace per ascoltarti.",
                "La Dea dei Boschi ti bacia la fronte: dove passi, i fiori sbocciano fuori stagione.",
                "L'Albero Madre apre il suo cuore di luce e vi incide il tuo nome: ogni foglia lo sussurra."],
    "giganti": ["Un gigante ti solleva su una spalla e ti mostra le montagne: «Ora queste sono anche tue.»",
                "Spezzi a mani nude la Pietra della Prova: i giganti battono i pugni sul petto.",
                "Il consiglio di pietra ti fa sedere su un trono scolpito per un uomo: l'hanno fatto apposta per te.",
                "Il Re dei Giganti incrocia il suo martello con il tuo braccio: «Fratello di montagna.»",
                "I Giganti scolpiscono il tuo volto sul fianco della montagna più alta. Vi resterà per diecimila anni."],
    "maree": ["Il Popolo delle Maree ti regala una perla che non smette mai di essere fredda: sei dei loro.",
              "Sfidi le correnti degli abissi e torni a riva: ti chiamano campione delle onde.",
              "Gli anziani delle maree ti ammettono nella sala di corallo: le loro voci sono il suono della risacca.",
              "La Regina delle Maree ti dona una goccia dell'oceano primordiale: ora il mare ti riconosce.",
              "L'oceano intero si ritira per un istante, e torna inchinato. Le maree ora seguono il tuo respiro."],
}


def offer_relic(conn, player, key: str) -> str:
    from engine.systems import races
    row = conn.execute("SELECT v.id AS vid, v.quantity, i.name, i.effects FROM inventories v JOIN items i "
                       "ON i.id=v.item_id WHERE v.owner_type='player' AND v.owner_id=? AND i.item_type='reliquia' "
                       "AND v.quantity>0;", (player.id,)).fetchall()
    import json
    mine = [r for r in row if (json.loads(r["effects"] or "{}").get("race_relic") == key)]
    if not mine:
        return f"Non hai reliquie dei {_name(key)} da offrire."
    r = mine[0]
    power = int(json.loads(r["effects"] or "{}").get("power", 1))
    if r["quantity"] > 1:
        conn.execute("UPDATE inventories SET quantity=quantity-1 WHERE id=?;", (r["vid"],))
    else:
        conn.execute("DELETE FROM inventories WHERE id=?;", (r["vid"],))
    d = get(conn)
    d[key]["relics"] += 1
    _save(conn, d)
    out = [f"🏺 Restituisci ai {_name(key)} la {r['name']}. Un silenzio lunghissimo, poi un canto antico."]
    out += races.adjust(conn, key, rel=15, honor=150 * power)
    out.append(f"Reliquie offerte: {d[key]['relics']}.")
    return "\n".join(out)


# ============================================================ quotidiano, alleati, guerra

def daily(conn, t: int, rng: random.Random, player) -> list[str]:
    from engine.systems import items, races, sects, master_plot
    if not master_plot.flag(conn, "razze"):
        return []
    out: list[str] = []
    d = get(conn)
    here = _land_key(conn, player.location_id)
    if here:
        ensure_champion(conn, player, here)
        last = state.get_int(conn, f"relic_find_{here}", -99)
        if t // DAY - last >= 10 and rng.random() < 0.08:
            state.set(conn, f"relic_find_{here}", str(t // DAY))
            rid, rn = relic_item(conn, here, rng, 1)
            items.grant(conn, "player", player.id, rid)
            out.append(f"🏺 Tra le rocce delle terre dei {_name(here)} qualcosa brilla: una reliquia, {rn}!")
    for k, r in d.items():
        st = r.get("standing", 0)
        if st >= 3 and rng.random() < 0.05 * (st - 2):
            iid, nm = _essence(conn, k, 4 * st, f"Dono dei {_name(k)}")
            items.grant(conn, "player", player.id, iid)
            out.append(f"🎁 I {_name(k)} ti mandano un dono di sangue: {nm}.")
        if st >= 5:
            n = 30 * _tier(conn, "player", player.id)
            sects.grant_resource(conn, "pietre_spirituali", n, player.id)
            if races.all_r(conn)[k]["rel"] < 60 and r.get("path") != "sigillo":
                races.adjust(conn, k, rel=5)
    return out


def combat_allies(conn, player_id: int, npc_id: int, ratio: float) -> list[dict]:
    """Dal grado di Principe, nei combattimenti difficili accorrono i guerrieri delle razze."""
    if ratio >= 1.0:
        return []
    d = get(conn)
    from engine.simulation import combat
    rng = random.Random(tick_mod.get_tick(conn) * 41 + npc_id)
    tier = _tier(conn, "player", player_id)
    for k, r in d.items():
        if r.get("standing", 0) >= 4 and rng.random() < 0.3:
            atk = combat.combat_power(conn, "player", player_id)["attack"] * (0.3 + 0.1 * (r["standing"] - 4)) * (1 + 0.02 * tier)
            return [{"intro": f"🐉 Un guerriero dei {_name(k)} scende dal cielo al tuo fianco: «Per il nostro "
                              f"{standing_name(k, r['standing'], r.get('path', ''))}!»",
                     "attack": atk, "line": f"Il guerriero dei {_name(k)} " + rng.choice(
                         ["colpisce con forza antica.", "travolge il nemico.", "ti copre il fianco."])}]
    return []


def war_power(conn) -> tuple[int, list[str]]:
    d = get(conn)
    tot, names = 0, []
    for k, r in d.items():
        if r.get("standing", 0) >= 5:
            tot += 80
            names.append(_name(k))
    return tot, names


# ============================================================ menu e comandi

def menu_build(conn, player) -> dict:
    from engine.systems.menus import act, bar, menu, section
    from engine.systems import races, bloodlines
    rr = races.all_r(conn)
    d = get(conn)
    secs = []
    for k in BLOOD:
        r, x = d[k], rr[k]
        land = _land(conn, k)
        here = land == player.location_id
        lname = conn.execute("SELECT name FROM locations WHERE id=?;", (land,)).fetchone()["name"] if land else "?"
        bg = blood_grade(conn, k)
        st = r.get("standing", 0)
        lines = [f"Terre: {lname}" + (" (sei qui)" if here else "") + f" · il tuo grado: {standing_name(k, st, r.get('path', ''))}",
                 f"Sangue affine ({BLOOD[k][0]}): " + (bloodlines.GRADES[bg][1] if 0 <= bg < len(bloodlines.GRADES)
                                                      else "Caos" if bg >= 0 else "nessuno")
                 + f" · campioni battuti: {r['beaten']} · reliquie offerte: {r['relics']}"]
        nxt = st + 1
        if nxt <= 4:
            req = requirements(conn, k, nxt)
            lines.append(f"Per {STANDING[nxt]}: " + " · ".join(("✔ " if ok else "✖ ") + lbl for lbl, ok in req))
        elif st < 5:
            for p, req in top_paths(conn, k).items():
                lines.append(f"Per {TOP[k][1 if p == 'eletto' else 0]} ({'pace' if p == 'eletto' else 'forza'}): "
                             + " · ".join(("✔ " if ok else "✖ ") + lbl for lbl, ok in req))
        champ = r.get("champ")
        crow = conn.execute("SELECT name, status FROM npcs WHERE id=?;", (champ,)).fetchone() if champ else None
        ctitle = rank_title(k, r["beaten"] + 1)
        if crow and crow["status"] == "alive":
            lines.append(f"Campione in attesa: {crow['name']}, {ctitle}")
        else:
            lines.append(f"Prossimo campione: {ctitle} (si presenta quando sei nelle loro terre)")
        acts = [act(f"Sfida il {ctitle}", f"razza {k} sfida", ok=here and x["rel"] > -60,
                    why="devi essere nelle loro terre" if not here else "sono in guerra con te")]
        can_up = st < 5 and (all(ok for _l, ok in requirements(conn, k, nxt)) if nxt <= 4 else
                             any(all(ok for _l, ok in req) for req in top_paths(conn, k).values()))
        if st < 5:
            acts.append(act(f"Cerimonia: diventa {standing_name(k, nxt) if nxt < 5 else 'Sovrano/Eletto'}",
                            f"razza {k} ascendi", ok=can_up, why="requisiti mancanti", main=can_up))
        acts.append(act("Offri una reliquia", f"razza {k} offri", ok=_has_relic(conn, player.id, k),
                        why="nessuna loro reliquia nello zaino"))
        acts.append(act("Dona 200 pietre", f"ambasciata {k} dona 200", ok=here or k == "maree", why="devi essere nelle loro terre"))
        if not here and land:
            acts.append(act("Vai nelle loro terre", f"vai #{land}"))
        rel = x["rel"]
        bars = [bar("Rapporto", (rel + 100) / 2, f"{rel:+d}", tone="bad" if rel <= -60 else "" if rel >= 60 else "info"),
                bar("Grado", st * 20, standing_name(k, st, r.get("path", "")), tone="rare")]
        icon = {"draghi": "🐉", "demoni": "😈", "spiriti": "🌿", "giganti": "⛰", "maree": "🌊"}[k]
        secs.append(section(f"{icon} {_name(k)}", lines, acts, bars))
    return menu("razze", "🐉 I REGNI DELLE RAZZE ANTICHE",
                ["Batti i loro campioni, raccogli il loro sangue e le loro reliquie, sali fino al trono."], secs)


def _has_relic(conn, pid, key) -> bool:
    import json
    for r in conn.execute("SELECT i.effects FROM inventories v JOIN items i ON i.id=v.item_id WHERE "
                          "v.owner_type='player' AND v.owner_id=? AND i.item_type='reliquia' AND v.quantity>0;", (pid,)):
        if json.loads(r["effects"] or "{}").get("race_relic") == key:
            return True
    return False


def command(conn, player, arg: str) -> str:
    from engine.systems import races, menus
    p = arg.strip().split()
    key = races._find(p[0]) if p else None
    if not key or key not in BLOOD:
        return menus.show(conn, player, "razze")
    sub = p[1].lower() if len(p) > 1 else ""
    if sub in ("sfida", "prova", "campione"):
        return challenge(conn, player, key)
    if sub in ("ascendi", "cerimonia", "sali"):
        return ascend(conn, player, key)
    if sub in ("offri", "reliquia"):
        return offer_relic(conn, player, key)
    return menus.show(conn, player, "razze")


def absorb_relic(conn, t, rng, player_id: int, key: str, power: int) -> list[str]:
    """'use <reliquia>': un balzo del sangue (o dell'anima, per gli Spiriti)."""
    from engine.systems import bloodlines, soul_temper
    p = entities.get_player(conn, player_id)
    out = [f"Spezzi il sigillo della reliquia: l'eredità dei {_name(key)} ti travolge."]
    if key == "spiriti":
        out += soul_temper.add_xp(conn, 60.0 * power)
        out.append(f"Spirito +{60 * power}.")
    out += bloodlines.gain(conn, t, rng, p, BLOOD[key][0], BLOOD[key][1], 25.0 * power)
    return out
