"""
I NOMI — mai più «Bai Cheng44» o «Landa Proibita di Drago62».

Un generatore unico per persone, creature, luoghi e sette, con uno spazio di nomi enorme (cognomi
semplici e composti, nomi di una o due sillabe, epiteti per le bestie, punti cardinali e qualità per i
luoghi) e una regola sola: NIENTE NUMERI. Quando una combinazione è già presa se ne cerca un'altra; se
proprio tutto è preso, si aggiunge un epiteto, mai una cifra.

  person(rng, used, female=False, surname=None)
  creature(rng, base, used)
  place(rng, base, used)          (aggiunge un determinativo solo se il nome base è già preso)
  migrate(conn)                   rinomina i nomi numerati dei salvataggi vecchi
"""

from __future__ import annotations

import random
import re

SURNAMES = ["Han", "Liu", "Zhao", "Mei", "Gao", "Wu", "Lin", "Shen", "Bai", "Tang", "Yun", "Xu", "Qin", "Su",
            "Long", "Feng", "Ye", "Mo", "Lu", "Jiang", "Song", "Hua", "Luo", "Qiao", "Shi", "Wen", "Yan", "Zhou",
            "Ling", "Xiao", "Chen", "Li", "Wang", "Zhang", "Yang", "Huang", "He", "Guo", "Ma", "Hu", "Zhu", "Sun",
            "Zheng", "Xie", "Han", "Cao", "Deng", "Peng", "Cai", "Pan", "Du", "Dai", "Xia", "Fang", "Ren", "Yuan",
            "Jin", "Qian", "Kong", "Tian", "Fu", "Gu", "Meng", "Duan", "Lei", "Hou", "Shao", "Wei", "Cui", "Kang",
            "Ji", "Ning", "Yin", "Bao", "Yue", "Chu", "Lian", "Qu",
            # cognomi composti, delle grandi casate
            "Ouyang", "Murong", "Shangguan", "Situ", "Zhuge", "Dongfang", "Nangong", "Ximen", "Huangfu", "Linghu",
            "Duanmu", "Gongsun", "Zhangsun", "Yuwen", "Helian", "Baili", "Dugu", "Wanyan", "Taishi", "Ximen"]
SYL = ["wei", "feng", "lan", "jian", "yan", "ruo", "tian", "cheng", "min", "hua", "zhi", "bo", "xue", "yu", "chen",
       "hao", "rong", "qing", "shan", "ling", "xin", "kai", "ming", "yue", "lian", "fei", "heng", "jun", "ying",
       "zhen", "wu", "ji", "chang", "ge", "mo", "ran", "xiao", "yun", "tao", "lei", "ning", "an", "rui", "hong",
       "sheng", "zhe", "yi", "shuo", "qian", "kun", "peng", "liang", "jie", "song", "he", "xuan", "chao", "fan",
       "lin", "ze", "yao", "hui", "du", "ce", "huan", "shi", "lu", "ao", "zhan", "xing"]
SYL_F = ["mei", "lan", "xue", "ling", "yue", "ying", "qing", "rou", "xiu", "yan", "zhen", "fei", "lian", "shuang",
         "yao", "ning", "wan", "yu", "ruo", "xi", "yun", "hua", "xin", "jing", "lu", "qiu", "die", "ya", "ting",
         "shan", "zhi", "yi", "wei", "an", "li", "ni", "xia", "ru", "chan", "juan"]
PERSON_EPITHETS = ["il Giovane", "il Vecchio", "il Silenzioso", "il Pallido", "il Rosso", "lo Straniero",
                   "il Mancino", "il Cieco", "il Ridente", "il Taciturno", "del Nord", "del Sud", "d'Oriente",
                   "d'Occidente", "della Montagna", "del Fiume", "delle Nebbie", "dei Salici"]

CREATURE_EPITHETS = ["dalla Cicatrice", "dagli Occhi d'Ambra", "dal Manto Nero", "dalle Zanne Spezzate",
                     "delle Paludi", "della Valle del Vento", "dei Mille Anni", "dal Respiro di Brina",
                     "dalla Coda Bianca", "dagli Artigli d'Argento", "della Luna Rossa", "del Picco Solitario",
                     "delle Ossa", "dal Corno Spezzato", "della Nebbia", "dei Monti del Nord", "del Bosco Antico",
                     "dalla Voce di Tuono", "dalle Scaglie di Giada", "del Fiume Nero", "dell'Alba", "del Tramonto",
                     "dal Passo Silenzioso", "dalla Pelle di Pietra", "delle Caverne", "della Tempesta",
                     "dagli Occhi di Brace", "della Cenere", "dal Sangue Antico", "del Lago Gelato", "delle Rovine",
                     "dalla Criniera di Fuoco", "del Deserto", "dei Salici", "dalle Ali Lacere", "del Vecchio Tempio",
                     "della Foresta Sommersa", "dal Morso Velenoso", "della Gola Profonda", "delle Mille Ferite"]

PLACE_DETERMINERS = ["del Nord", "del Sud", "d'Oriente", "d'Occidente", "Superiore", "Inferiore", "Antica",
                     "Nuova", "Alta", "Bassa", "Interna", "Esterna", "Vecchia", "Lontana", "Velata", "Sommersa",
                     "dei Pini", "dei Salici", "delle Nebbie", "del Vento", "della Brina", "della Cenere"]
SECT_DETERMINERS = ["del Nord", "del Sud", "d'Oriente", "d'Occidente", "Superiore", "Celeste", "Antica",
                    "dei Nove Picchi", "delle Tre Lune", "del Mare Interno", "della Montagna Nascosta"]


def _given(rng: random.Random, female: bool) -> str:
    pool = SYL_F if female else SYL
    g = rng.choice(pool)
    if rng.random() < 0.55:
        g2 = rng.choice(SYL if not female or rng.random() < 0.3 else SYL_F)
        if g2 != g:
            g = g + g2
    return g.capitalize()


def person(rng: random.Random, used: set[str] | None = None, female: bool = False,
           surname: str | None = None) -> str:
    used = used if used is not None else set()
    for _ in range(400):
        n = f"{surname or rng.choice(SURNAMES)} {_given(rng, female)}"
        if n not in used:
            used.add(n)
            return n
    base = f"{surname or rng.choice(SURNAMES)} {_given(rng, female)}"
    for ep in rng.sample(PERSON_EPITHETS, len(PERSON_EPITHETS)):
        n = f"{base} {ep}"
        if n not in used:
            used.add(n)
            return n
    n = f"{base} {rng.choice(PERSON_EPITHETS)} {rng.choice(PERSON_EPITHETS)}"
    used.add(n)
    return n


def creature(rng: random.Random, base: str, used: set[str] | None = None) -> str:
    used = used if used is not None else set()
    if base not in used:
        used.add(base)
        return base
    for ep in rng.sample(CREATURE_EPITHETS, len(CREATURE_EPITHETS)):
        n = f"{base} {ep}"
        if n not in used:
            used.add(n)
            return n
    for _ in range(400):
        a, b = rng.sample(CREATURE_EPITHETS, 2)
        n = f"{base} {a} e {b}"
        if n not in used:
            used.add(n)
            return n
    n = f"{base} {rng.choice(CREATURE_EPITHETS)} {rng.choice(PLACE_DETERMINERS)}"
    used.add(n)
    return n


def place(rng: random.Random, base: str, used: set[str] | None = None, dets: list[str] | None = None) -> str:
    used = used if used is not None else set()
    if base not in used:
        used.add(base)
        return base
    dets = dets or PLACE_DETERMINERS
    for d in rng.sample(dets, len(dets)):
        n = f"{base} {d}"
        if n not in used:
            used.add(n)
            return n
    n = f"{base} {rng.choice(dets)} {rng.choice(PLACE_DETERMINERS)}"
    used.add(n)
    return n


_NUM = re.compile(r"^(.*?)\s*(\d+)$")


def migrate(conn) -> int:
    """Rinomina i nomi con numeri (persone, creature, luoghi, sette). Idempotente."""
    rng = random.Random(4242)
    n = 0
    used = {r[0] for r in conn.execute("SELECT name FROM npcs WHERE status='alive' OR COALESCE(kind,'human')='human';")}
    for r in conn.execute("SELECT id, name, COALESCE(kind,'human') k, gender FROM npcs;").fetchall():
        m = _NUM.match(r[1] or "")
        if not m:
            continue
        base = m.group(1).strip()
        if r[2] == "human":
            sur = base.split(" ")[0] if base else None
            new = person(rng, used, female=(r[3] == "f"), surname=sur if sur in SURNAMES else None)
        else:
            new = creature(rng, base, used)
        conn.execute("UPDATE npcs SET name=? WHERE id=?;", (new, r[0]))
        n += 1
    used = {r[0] for r in conn.execute("SELECT name FROM locations;")}
    for r in conn.execute("SELECT id, name FROM locations;").fetchall():
        m = _NUM.match(r[1] or "")
        if m:
            conn.execute("UPDATE locations SET name=? WHERE id=?;", (place(rng, m.group(1).strip(), used), r[0]))
            n += 1
    used = {r[0] for r in conn.execute("SELECT name FROM factions;")}
    for r in conn.execute("SELECT id, name FROM factions;").fetchall():
        m = _NUM.match(r[1] or "")
        if m:
            conn.execute("UPDATE factions SET name=? WHERE id=?;",
                         (place(rng, m.group(1).strip(), used, SECT_DETERMINERS), r[0]))
            n += 1
    return n
