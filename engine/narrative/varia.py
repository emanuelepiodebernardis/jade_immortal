"""
VARIA — testo che non si ripete (senza LLM).

Una piccola grammatica generativa alla Tracery: ogni SIMBOLO ha molte espansioni, che
possono contenere altri simboli (#simbolo#) e variabili del contesto ({luogo}, {nome}…).
In più il testo cambia col MONDO: ora del giorno, stagione, tempo atmosferico, tipo di
luogo, era. E una piccola memoria evita di ripetere la stessa variante a breve distanza.

Usato per le frasi che si leggono più spesso: la meditazione, l'allenamento, l'alba di
ogni giorno, l'esito delle prove, l'atmosfera degli incontri e dei luoghi.
"""

from __future__ import annotations

import random
import re
from collections import deque

DAY_TICKS = 120
YEAR_TICKS = 2000

G: dict[str, list[str]] = {
    # ---- tempo ----
    "alba": ["L'alba sorge pallida", "Il primo sole incendia l'orizzonte", "Un'alba color giada rischiara il cielo",
             "La notte si ritira lenta", "Il cielo si schiarisce a oriente", "Un gallo lontano saluta il giorno",
             "La rugiada brilla sotto il primo sole", "Il giorno nasce senza fretta"],
    "mattina": ["nel fresco del mattino", "mentre il sole sale", "nella luce chiara del mattino",
                "quando la nebbia ancora indugia"],
    "giorno": ["sotto il sole alto", "nel pieno del giorno", "nella calura del mezzogiorno", "nella luce piena"],
    "sera": ["mentre il sole tramonta", "nella luce rossa del vespro", "quando le ombre si allungano",
             "al calare della sera"],
    "notte": ["sotto un cielo di stelle", "nel silenzio della notte", "alla luce della luna",
              "nel buio più fondo della notte", "mentre il mondo dorme"],
    # ---- stagioni e meteo ----
    "primavera": ["l'aria profuma di fiori di pesco", "germogli spuntano tra le rocce", "il vento porta polline e promesse"],
    "estate": ["le cicale cantano senza sosta", "l'aria tremola di calore", "il Qi del sole è denso e caldo"],
    "autunno": ["foglie rosse cadono attorno a te", "il vento sa di terra e di raccolto", "l'aria si fa tersa e fredda"],
    "inverno": ["la brina copre ogni cosa", "il fiato si condensa in nuvole bianche", "la neve attutisce ogni suono"],
    "sereno": ["il cielo è limpido", "non c'è una nuvola", "l'aria è immobile e chiara"],
    "pioggia": ["una pioggia sottile batte sulle foglie", "piove, e il Qi dell'Acqua è più vivo", "l'acqua scorre in rivoli"],
    "nebbia": ["una nebbia lattiginosa nasconde i contorni", "la foschia sale dalla terra", "tutto è ovattato dalla nebbia"],
    "vento": ["un vento teso piega le erbe", "raffiche fredde fischiano tra le rocce", "il vento porta voci lontane"],
    "temporale": ["tuoni rotolano all'orizzonte", "lampi lontani accendono le nuvole", "l'aria sa di fulmine"],
    # ---- luoghi ----
    "luogo_city": ["tra il vociare delle strade", "nella tua stanza in locanda", "in un cortile appartato",
                   "sul tetto, sopra la città"],
    "luogo_mountain": ["su una sporgenza di roccia", "accanto a una cascata", "all'ombra di un pino antico",
                       "sulla cima, tra le nuvole"],
    "luogo_ruin": ["tra colonne spezzate", "sotto un arco in rovina", "su antiche lastre incise",
                   "accanto a una statua senza volto"],
    "luogo_forbidden_zone": ["dove il Qi è torbido e selvaggio", "in un cerchio di pietre annerite",
                             "sull'orlo di una faglia che respira", "tra ossa di bestie antiche"],
    "luogo_other": ["in un luogo tranquillo", "lontano da occhi indiscreti", "dove il Qi scorre più limpido"],
    # ---- meditazione ----
    "posa": ["Siedi a gambe incrociate", "Chiudi gli occhi", "Regoli il respiro", "Ti immergi nel silenzio",
             "Lasci che il Qi trovi la sua strada", "Guidi il Qi lungo i meridiani", "Ascolti il battito del Dao"],
    "sensazione": ["il Qi scorre caldo nel dantian", "i meridiani pulsano lenti", "il mondo si allontana",
                   "una corrente sottile ti attraversa", "il tuo mare di Qi si increspa e si placa",
                   "senti ogni filo di energia attorno a te"],
    "medita": ["#posa# #dove#, #quando#: #sensazione#.", "#Quando#, #posa_min# #dove#. #Sensazione#.",
               "#posa# #dove#; #meteo_breve#, e #sensazione#."],
    # ---- allenamento d'insieme ----
    "allena": ["☯ Allenamento d'insieme: Qi, Dao e arte crescono insieme.",
               "☯ Ti alleni in ogni cosa: il respiro, l'intento, le mani dell'artigiano.",
               "☯ Una sessione completa: mediti, contempli i tuoi Dao, eserciti la tua arte.",
               "☯ Corpo, mente e mani lavorano insieme, #quando#.",
               "☯ #Quando#, alterni respiro, intuizione e lavoro."],
    # ---- esiti delle prove ----
    "riesci": ["Riesci.", "Ce la fai.", "Va come speravi.", "Il Cielo è dalla tua parte.", "Ci riesci, e bene.",
               "Tutto si incastra al posto giusto."],
    "fallisci": ["Non va come speravi.", "Qualcosa va storto.", "Il Cielo, oggi, guarda altrove.",
                 "Non basta.", "Ti sfugge per un soffio.", "Le cose prendono un'altra piega."],
    # ---- atmosfera degli incontri ----
    "atmosfera": ["#Quando#, #meteo_breve#.", "#Meteo_breve#; #quando#.", "#Stagione_breve#.",
                  "#Quando#, #dove_aperto#."],
    "dove_aperto": ["lungo il sentiero", "a un crocevia", "poco lontano", "sulla strada"],
}

# simboli derivati dal contesto (vengono riempiti da ctx_symbols)
_CTX_SYMBOLS = ("quando", "dove", "meteo_breve", "stagione_breve", "posa_min")

_recent: dict[str, deque] = {}


def _choose(sym: str, opts: list[str], rng: random.Random) -> str:
    mem = _recent.setdefault(sym, deque(maxlen=max(1, min(4, len(opts) - 1))))
    fresh = [o for o in opts if o not in mem] or opts
    pick = rng.choice(fresh)
    mem.append(pick)
    return pick


def expand(text: str, rng: random.Random, ctx: dict | None = None, depth: int = 0) -> str:
    ctx = ctx or {}

    def rep(m):
        sym = m.group(1)
        cap = sym[:1].isupper()
        key = sym.lower()
        if key in ctx:
            val = ctx[key]
            val = _choose(key, val, rng) if isinstance(val, list) else str(val)
        elif key in G:
            val = _choose(key, G[key], rng)
        else:
            return m.group(0)
        if depth < 6:
            val = expand(val, rng, ctx, depth + 1)
        return val[:1].upper() + val[1:] if cap else val
    return re.sub(r"#([A-Za-z_]+)#", rep, text)


def say(sym: str, rng: random.Random, ctx: dict | None = None, **fmt) -> str:
    out = expand(_choose(sym, G[sym], rng), rng, ctx)
    return out.format(**fmt) if fmt else out


# ------------------------------------------------------------
# Il mondo in cui accade
# ------------------------------------------------------------

def time_of_day(tick: int) -> str:
    h = (tick % DAY_TICKS) / DAY_TICKS
    return "mattina" if h < 0.3 else "giorno" if h < 0.6 else "sera" if h < 0.8 else "notte"


def season(tick: int) -> str:
    q = (tick % YEAR_TICKS) / YEAR_TICKS
    return "primavera" if q < 0.25 else "estate" if q < 0.5 else "autunno" if q < 0.75 else "inverno"


def weather(tick: int) -> str:
    day = tick // DAY_TICKS
    r = random.Random(day * 7919 + 13).random()
    s = season(tick)
    if s == "inverno":
        return "sereno" if r < 0.4 else "nebbia" if r < 0.65 else "vento" if r < 0.9 else "temporale"
    if s == "estate":
        return "sereno" if r < 0.55 else "temporale" if r < 0.75 else "vento" if r < 0.9 else "pioggia"
    return "sereno" if r < 0.4 else "pioggia" if r < 0.65 else "nebbia" if r < 0.82 else "vento" if r < 0.94 else "temporale"


def ctx_for(tick: int, location_type: str | None = None) -> dict:
    tod = time_of_day(tick)
    lt = location_type if location_type in ("city", "mountain", "ruin", "forbidden_zone") else "other"
    return {"quando": G[tod], "dove": G["luogo_" + lt], "meteo_breve": G[weather(tick)],
            "stagione_breve": G[season(tick)], "posa_min": ["siedi", "chiudi gli occhi", "respiri piano", "mediti"]}


def _loc_type(conn, player) -> str | None:
    r = conn.execute("SELECT location_type FROM locations WHERE id=?;", (player.location_id,)).fetchone()
    return r["location_type"] if r else None


def meditation(conn, player, tick: int) -> str:
    rng = random.Random(tick * 31 + 7)
    return say("medita", rng, ctx_for(tick, _loc_type(conn, player)))


def train_header(conn, player, tick: int) -> str:
    rng = random.Random(tick * 37 + 11)
    return say("allena", rng, ctx_for(tick, _loc_type(conn, player)))


def dawn(tick: int) -> str:
    rng = random.Random(tick // DAY_TICKS * 101 + 5)
    w = weather(tick)
    return f"{_choose('alba', G['alba'], rng)}: {_choose(season(tick), G[season(tick)], rng)}, " \
           f"{_choose(w, G[w], rng)}. Qi e spirito ristabiliti."


def outcome(ok: bool, rng: random.Random) -> str:
    return say("riesci" if ok else "fallisci", rng)


def ambience(conn, player, tick: int) -> str:
    rng = random.Random(tick * 53 + 3)
    return say("atmosfera", rng, ctx_for(tick, _loc_type(conn, player)))


_TOD_LABEL = {"mattina": "Mattino", "giorno": "Pieno giorno", "sera": "Sera", "notte": "Notte"}


def weather_line(tick: int) -> str:
    """Una riga d'ambiente per 'look': ora, stagione e tempo, sempre coerenti col mondo."""
    rng = random.Random(tick // 30 * 17 + 1)
    w = weather(tick)
    return f"({_TOD_LABEL[time_of_day(tick)]} di {season(tick)}: {_choose(w, G[w], rng)}.)"
