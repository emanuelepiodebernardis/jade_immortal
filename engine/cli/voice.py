"""
COMANDI A VOCE (Aggiornamento 76) — il gioco si comanda parlando, senza modello linguistico.

Pensato per un dettatore locale (per esempio Handy): tieni premuto un tasto, dici «attacca il primo
nemico», il testo finisce nella barra dei comandi e parte da solo. Qui lo trasformiamo in un comando vero:

  · NORMALIZZA: maiuscole, punteggiatura, parole di cortesia, numeri detti a parole («la seconda» → 2);
  · CONTESTO: chi è presente (nell'ordine in cui lo vedi), le uscite, le scelte della scena, le carte
    del duello, le mete, ciò che il gioco ti suggerisce, la scheda aperta (per «compra la terza»);
  · NOMI DETTI MALE: «su scian» trova Xu Shan (fonetica italiana del pinyin, più somiglianza);
  · NAVIGAZIONE: «apri la sezione del Dao», «mostra lo zaino», «avanti», «chiudi»… diventano azioni
    dell'interfaccia (ui:…), che la dashboard esegue senza passare dal motore.

Tutto deterministico: interpret(testo, stato, scheda) → {"cmd": …} | {"ui": …} | {} (nessuna idea:
il testo passa così com'è). Aggiungere un modo di dire = una riga nelle tabelle qui sotto.
"""

from __future__ import annotations

import difflib
import re
import unicodedata

# ---------------------------------------------------------------- normalizzazione

NUM = {"zero": 0, "uno": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6, "sette": 7,
       "otto": 8, "nove": 9, "dieci": 10, "undici": 11, "dodici": 12, "tredici": 13, "quattordici": 14,
       "quindici": 15, "sedici": 16, "diciassette": 17, "diciotto": 18, "diciannove": 19, "venti": 20,
       "trenta": 30, "quaranta": 40, "cinquanta": 50, "sessanta": 60, "cento": 100, "mille": 1000}
ORD = {"primo": 1, "prima": 1, "secondo": 2, "seconda": 2, "terzo": 3, "terza": 3, "quarto": 4, "quarta": 4,
       "quinto": 5, "quinta": 5, "sesto": 6, "sesta": 6, "settimo": 7, "settima": 7, "ottavo": 8, "ottava": 8,
       "nono": 9, "nona": 9, "decimo": 10, "decima": 10, "ultimo": -1, "ultima": -1}
FILLER = r"\b(per favore|perfavore|grazie|ok|okay|allora|dai|ecco|ehm|eh|uhm|bene|adesso|ora|subito|su dai)\b"


def _plain(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normalize(text: str) -> str:
    t = (text or "").strip().lower().replace("’", "'")
    t = re.sub(r"[«»\"“”!?¿¡.,;:…]+", " ", t)
    t = re.sub(FILLER, " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    words = []
    for w in t.split(" "):
        b = _plain(w)
        if b in NUM:
            w = str(NUM[b])
        words.append(w)
    return " ".join(words)


def _ordinal(t: str) -> int | None:
    """Il numero detto nella frase: «il secondo», «numero 3», «la 2», «l'ultimo»."""
    for w in t.split():
        b = _plain(w.split("'")[-1])
        if b in ORD:
            return ORD[b]
        if b.isdigit():
            return int(b)
    return None


# ---------------------------------------------------------------- nomi detti a voce

_PINYIN = [("zh", "g"), ("ch", "c"), ("sh", "sc"), ("x", "sc"), ("q", "ci"), ("j", "gi"), ("z", "z"),
           ("ao", "ao"), ("ou", "ou"), ("iu", "iu"), ("ui", "uei"), ("w", "u"), ("y", "i"), ("h", "")]


def _phon(s: str) -> str:
    s = _plain(s.lower())
    for a, b in _PINYIN:
        s = s.replace(a, b)
    s = re.sub(r"[^a-z ]", "", s)
    s = re.sub(r"(.)\1+", r"\1", s)                      # doppie
    return s.replace("k", "c").replace("gn", "n")


def match_name(spoken: str, names: list[str]) -> str | None:
    """Il nome più vicino a ciò che è stato detto (nome intero, solo il nome proprio, o «come suona»)."""
    sp = _plain(spoken.lower()).strip()
    if not sp or not names:
        return None
    best, score = None, 0.0
    for n in names:
        nl = _plain(n.lower())
        parts = nl.split()
        cands = [nl] + parts
        for c in cands:
            if sp == c:
                return n
            r = max(difflib.SequenceMatcher(None, sp, c).ratio(),
                    difflib.SequenceMatcher(None, _phon(sp), _phon(c)).ratio())
            if c in sp.split() or (len(c) > 2 and sp.startswith(c)):
                r = max(r, 0.9)
            if r > score:
                best, score = n, r
    return best if score >= 0.72 else None


def first(n: str) -> str:
    return n.split()[0]


# ---------------------------------------------------------------- l'interfaccia (ui:…)

# «apri il Dao» → la scheda della dashboard (stesse chiavi di app.js: m:via:…, tesori:zaino, storia:saghe…)
UI_SECTIONS = [
    (r"dao|daoi|profond", "m:via:profondi"), (r"spirit", "m:via:spiriti"), (r"tecnich|dantian", "m:via:tecniche"),
    (r"corpo", "m:via:corpo"), (r"sangue|lignagg", "m:via:sangue"), (r"meridian", "m:via:meridiani"),
    (r"regno|coltivazion|compression|sfondament", "m:via:coltivazione"), (r"anim[ae]|vasi", "m:via:anime"),
    (r"dharma|sigill", "m:via:dharma"), (r"pilastr|forza", "m:via:forza"), (r"attribut", "m:via:attributi"),
    (r"eroe|personaggio|stato|finestra|scheda personale", "personaggio"), (r"via\b", "m:via:coltivazione"),
    (r"mappa|carta del mondo", "mappa"), (r"mercat|negozi|bottega", "m:mercato"), (r"ast[ae]", "m:asta"),
    (r"bacheca|missioni", "m:bacheca"), (r"ricett", "m:ricette"), (r"\barti\b|mestier", "m:arti"),
    (r"dimora|grotta|casa", "m:dimora"), (r"rendit|entrat", "m:rendite"), (r"domini|serv[io]|schiav", "m:dominio"),
    (r"setta", "m:setta"), (r"clon", "m:cloni"), (r"discepol", "m:discepoli"), (r"legam|persone|relazion", "persone"),
    (r"compagn", "m:compagni"), (r"famigli", "m:famiglia"), (r"faid|nemic", "m:faide"),
    (r"regni|corte", "m:regni"), (r"razz", "m:razze"), (r"mondo di sotto|sotto", "m:sotto"),
    (r"zaino|inventari|borsa|oggetti|equipaggiament|tesor", "tesori:zaino"), (r"album|collezion", "tesori:album"),
    (r"libro", "tesori:libro"), (r"saghe|saga", "storia:saghe"), (r"cronac|diario", "storia:cronaca"),
    (r"scelte", "storia:scelte"), (r"trama|trame|storia", "storia:trama"), (r"codex|enciclopedi", "storia:codex"),
    (r"mondo", "storia:mondo"), (r"stagion|traguard", "m:stagione"), (r"pilota|impostazion|opzion", "pilota"),
    (r"oggi|mete|obiettiv|cosa fare", "oggi"),
]
OPEN = r"^(apri|aprimi|mostra|mostrami|fammi vedere|vai a|vai al|vai alla|vai alle|vai ai|vai in|vai nel|vai nella|guarda|" \
       r"visualizza|entra in|entra nel|entra nella|passa a|passa al|passa alla|scheda|sezione|pannello|menu)\b"


def _section(t: str) -> str | None:
    t = re.sub(OPEN, "", t).strip()
    t = re.sub(r"^(la |il |lo |le |i |gli |l'|del |della |dello |dei |delle |degli |sezione |scheda |pannello |menu |"
               r"del |di )+", "", t).strip()
    t = re.sub(r"^(sezione|scheda|pannello|menu) (del |della |dello |dei |delle |degli |di )?", "", t).strip()
    if not t:
        return None
    for pat, key in UI_SECTIONS:
        if re.search(r"\b(" + pat + ")", t):
            return key
    return None


# ---------------------------------------------------------------- le direzioni

DIRS = {"nord": "north", "settentrione": "north", "sud": "south", "meridione": "south", "est": "east", "oriente": "east",
        "ovest": "west", "occidente": "west", "su": "up", "sopra": "up", "giu": "down", "sotto": "down",
        "north": "north", "south": "south", "east": "east", "west": "west", "up": "up", "down": "down"}


# ---------------------------------------------------------------- l'interprete

SPEECH = re.compile(r"\b(il|lo|la|l|i|gli|le|un|una|con|a|ad|al|alla|allo|ai|alle|verso|del|della|dello|dei|delle|"
                    r"di|tutti|tutto|quanti|per|mio|mia|me|mi|ti|si|ci|cosa|che|primo|prima|secondo|seconda|terzo|"
                    r"terza|ultimo|ultima|sezione|scheda|pannello|menu)\b")
_KNOWN: set = set()


def _known() -> set:
    if not _KNOWN:
        try:
            from engine.cli import help_text, loop
            _KNOWN.update(w.lower() for w in help_text.command_words())
            _KNOWN.update(loop.VERB_ALIAS)
        except Exception:                                # noqa: BLE001
            pass
    return _KNOWN


def looks_spoken(raw: str) -> bool:
    """Un comando del gioco scritto come si deve passa così com'è; una frase parlata no."""
    t = normalize(raw)
    if not t:
        return False
    w = t.split(" ")[0]
    r = (raw or "").strip()
    dictated = bool(re.search(r"\w[.!?…]+$", r)) or bool(re.search(FILLER, r.lower()))   # «Allenati.», «… per favore»
    return dictated or (w not in _known() and not w.isdigit()) or bool(SPEECH.search(t))


def interpret(text: str, s: dict | None = None, tab: str = "", force: bool = False) -> dict:
    """{"cmd": comando} | {"ui": azione dell'interfaccia} | {} — più "eco": come l'abbiamo capita.
    Senza force, un comando già valido («attack Xu», «vai 2») passa invariato ({})."""
    s = s or {}
    t = normalize(text)
    if not t or (not force and not looks_spoken(text)):
        return {}
    out = _interpret(t, s, tab or "")
    if out and (out.get("cmd") or out.get("ui")):
        out["eco"] = out.get("cmd") or out.get("ui")
    return out or {}


def _people(s: dict, enemies: bool = False) -> list[dict]:
    pr = list(s.get("presenti") or [])
    if enemies:
        foes = [p for p in pr if p.get("rel") == "nemico"] or [p for p in pr if p.get("kind") not in (None, "human")]
        return foes or pr
    return pr


def _pick(lst: list, n: int | None):
    if not lst or n is None:
        return None
    if n == -1:
        return lst[-1]
    return lst[n - 1] if 1 <= n <= len(lst) else None


def _who(t: str, s: dict, enemies: bool = False) -> str | None:
    """Il nome di chi è indicato: per numero d'ordine («il secondo») o per nome (anche detto male)."""
    lst = _people(s, enemies)
    p = _pick(lst, _ordinal(t))
    if p:
        return first(p["name"])
    rest = re.sub(r"\b(il|lo|la|l|i|gli|le|un|una|con|a|al|alla|contro|quel|quello|quella|tizio|tipo|signore|signora|"
                  r"nemico|nemica|creatura|bestia|persona|ragazzo|ragazza|vecchio|vecchia)\b", " ", t)
    rest = re.sub(r"\s+", " ", rest).strip()
    n = match_name(rest, [p["name"] for p in _people(s)])
    return first(n) if n else None


def _choice_by_words(t: str, choices: list[dict]) -> int | None:
    """In una scena: la scelta le cui parole somigliano di più a ciò che hai detto («marchiagli l'anima»)."""
    words = {w for w in re.findall(r"[a-zà-ù]{4,}", _plain(t))}
    if not words:
        return None
    best, score = None, 0.0
    for c in choices:
        cw = {w for w in re.findall(r"[a-zà-ù]{4,}", _plain(c.get("label", "").lower()))}
        if not cw:
            continue
        hit = 0.0
        for w in words:
            m = max((difflib.SequenceMatcher(None, w[:6], x[:6]).ratio() for x in cw), default=0)
            hit += 1 if m >= 0.83 else 0
        sc = hit / max(1, min(len(words), 4))
        if sc > score:
            best, score = c.get("n"), sc
    return best if score >= 0.5 else None


SYN = {   # frase → comando semplice
    r"^(allenati|allenamento|alleniamoci|allena|alleniamo|coltiva|coltivazione|comprimi|comprimi il qi|accumula)$": "train",
    r"^(medita|meditazione|meditiamo)$": "meditazione",
    r"^(medita|meditazione) (della |sulla )?(mente)$": "meditazione mente",
    r"^(medita|meditazione) (del |sul )?(corpo)$": "meditazione corpo",
    r"^(sfonda|sfondamento|sfondiamo|tenta lo sfondamento|supera il (livello|regno)|sali di (livello|regno)|breakthrough)$": "breakthrough",
    r"^(tribolazione|affronta la tribolazione)$": "tribulation",
    r"^(tempra|tempra lo spirito|tempra l'anima)$": "tempra",
    r"^(allena gli spiriti|spiriti allena|allenati con gli spiriti)$": "spiriti allena",
    r"^(dormi|vai a dormire|riposa|riposati|a dormire|andiamo a dormire)$": "sleep",
    r"^(aspetta|attendi|aspettiamo)$": "wait",
    r"^(raccogli|raccogli tutto|prendi tutto|raccogli il bottino)$": "raccogli",
    r"^(raccogli (le )?(erbe|materiali|risorse)|raccolta)$": "gather",
    r"^(saccheggia|prendi il bottino|bottino|loot)$": "loot",
    r"^(caccia|vai a caccia|caccia le creature|attacca le (creature|bestie)|attacca gli animali)$": "attack creatures",
    r"^(attacca (tutti|tutti quanti|chiunque|tutto)|attacco generale)$": "attack all",
    r"^(attacca gli umani|attacca le persone)$": "attack humans",
    r"^(assorbi|divora) (tutto|tutti|tutti quanti|i resti|tutti i resti)$": "absorb all",
    r"^(usa|prendi) (tutte )?(le )?pillole$": "use pillole",
    r"^(usa|assorbi) (tutte )?(le )?essenze$": "use essenze",
    r"^(usa tutto|usa tutti gli oggetti)$": "use all",
    r"^(equipaggia(ti)?|indossa|vestiti) (tutto|il meglio|i migliori|il migliore)$": "equip auto",
    r"^(cura (i )?tesori|cura tutti i tesori)$": "tesori cura",
    r"^(salva|salva la partita|salvataggio)$": "salva",
    r"^(guarda|guardati) (in giro|intorno|attorno)$|^(osserva il luogo|dove sono)$": "look",
    r"^(crea|fai|genera) (un |il )?clone$": "clone crea",
    r"^(dispiega|schiera|manda) (i |il )?clon[ei]$": "clone dispiega",
    r"^(riscuoti|riscuoti (tutto|le rendite|i tributi))$": "rendite riscuoti",
    r"^(torna a casa|vai a casa|torna in setta|torna alla setta)$": "home",
    r"^(purifica|purificati|purifica i meridiani)$": "purifica",
    r"^(apri (un |il )?meridiano)$": "meridiani apri",
    r"^(missione (del giorno|quotidiana)|quotidiana)$": "quotidiana",
    r"^(fai la (prima|prossima) cosa|segui il consiglio|cosa devo fare)$": "@todo",
}


def _interpret(t: str, s: dict, tab: str) -> dict:
    # 0) la lettura e l'interfaccia
    if re.fullmatch(r"(avanti|continua|prosegui|vai avanti|next|leggi avanti)", t):
        return {"ui": "avanti"}
    if re.fullmatch(r"(mostra|leggi) tutto|salta( tutto)?", t):
        return {"ui": "tutto"}
    if re.fullmatch(r"(chiudi|chiudi tutto|esci dal menu|basta)", t):
        return {"ui": "chiudi"}
    if re.fullmatch(r"(ripeti|rileggi|cosa hai detto|leggi di nuovo)", t):
        return {"ui": "ripeti"}
    m = re.fullmatch(r"(pilota|pilota automatico|vai avanti|avanza|fai passare|lascia passare) (per |di )?(\d+) (giorni|giorno)", t)
    if m:
        return {"ui": f"pilota {m.group(3)}"}
    if re.fullmatch(r"(ferma|stop|interrompi)( il pilota)?", t):
        return {"ui": "ferma"}

    duel = s.get("duello") and (s.get("duello") or {}).get("arena")
    scene = s.get("scena")

    # 1) nel duello: le carte
    if duel and not duel.get("finito"):
        cards = duel.get("carte") or []
        by = {c.get("key"): c for c in cards}
        simple = [(r"^(colpisci|colpo|attacca|attacco|picchia|colpiscilo)$", "colpisci"),
                  (r"^(difenditi|difendi|difesa|para|parata|in guardia|guardia|proteggiti)$", "difendi"),
                  (r"^(concentrati|concentrazione|carica|raccogli il qi)$", "concentrati"),
                  (r"^(pillola|curati|cura|prendi una pillola|usa una pillola)$", "pillola"),
                  (r"^(fuggi|scappa|ritirata|ritirati|fuga)$", "fuggi")]
        for pat, k in simple:
            if re.match(pat, t) and k in by and by[k].get("ok"):
                return {"cmd": by[k]["cmd"]}
        if re.match(r"^(attacco|tecnica|carta|mossa|colpo|usa|usa la|usa il|arte|attacca con la|attacca con il)\b", t) \
                or re.fullmatch(r"(il |la )?\w+ (attacco|tecnica|carta|mossa)", t):
            c = _pick(cards, _ordinal(t))
            if c and c.get("ok"):
                return {"cmd": c["cmd"]}
        if re.search(r"\b(piu forte|più forte|speciale|suprema|finale|migliore)\b", t):
            tech = [c for c in cards if c.get("ok") and c.get("kind") not in ("base",)]
            if tech:
                return {"cmd": tech[0]["cmd"]}
        # una tecnica detta per nome
        names = {c["name"]: c for c in cards if c.get("ok")}
        n = match_name(re.sub(r"^(usa|tecnica|attacco)\s+", "", t), list(names))
        if n and len(t) > 4:
            return {"cmd": names[n]["cmd"]}

    # 2) in una scena: «scelta 2», «la seconda», oppure le parole della scelta
    if scene and scene.get("choices"):
        ch = scene["choices"]
        if re.match(r"^(scelta|scelgo|opzione|risposta|numero|la|il|voglio la|voglio il|prendo la|scegli la|scegli il)\b", t) \
                or re.fullmatch(r"\d+", t) or _plain(t.split()[0]) in ORD:
            n = _ordinal(t)
            if n is not None:
                c = _pick(ch, n)
                if c:
                    return {"cmd": str(c["n"])}
        n = _choice_by_words(t, ch)
        if n is not None and not duel:
            return {"cmd": str(n)}

    # 3) frasi fisse
    for pat, cmd in SYN.items():
        if re.fullmatch(pat, t):
            if cmd == "@todo":
                todo = s.get("todo") or []
                return {"cmd": todo[0]["cmd"]} if todo else {"cmd": "guida"}
            return {"cmd": cmd}

    # 4) muoversi
    m = re.match(r"^(vai|va|andiamo|spostati|muoviti|cammina|dirigiti|prosegui|sali|scendi)( verso| a| ad| al| alla| in| nel| nella)? (.+)$", t)
    if m or t in DIRS or re.fullmatch(r"(sali|scendi)", t):
        dest = (m.group(3) if m else t).strip()
        if t == "sali":
            dest = "su"
        if t == "scendi":
            dest = "giu"
        d = DIRS.get(_plain(dest))
        if d:
            return {"cmd": f"move {d}"}
        md = re.fullmatch(r"(meta|obiettivo|destinazione) (\S+)|(?:la |il )?(\S+) (meta|destinazione|obiettivo)", dest)
        if md:
            n = _ordinal(dest)
            if n:
                return {"cmd": f"vai {n}"}
        ex = s.get("uscite") or []
        hit = match_name(dest, [e["name"] for e in ex])
        if hit:
            return {"cmd": "move " + next(e["dir"] for e in ex if e["name"] == hit)}
        if re.search(r"\b(mercante|mercato|negozio)\b", dest):
            return {"ui": "m:mercato"}
        if m and not _section(dest):
            return {"cmd": f"vai {dest}"}
    m = re.match(r"^vola (a|verso|in|al|alla)? ?(.+)$", t)
    if m:
        return {"cmd": f"vola {m.group(2)}"}

    # 5) comprare: dipende da dove sei (setta, sistema, mercato)
    m = re.match(r"^(compra|compro|acquista|prendo|prendi)\b(.*)$", t)
    if m:
        n = _ordinal(m.group(2))
        if n and n > 0:
            if "setta" in tab:
                return {"cmd": f"setta compra {n}"}
            if "sistema" in tab:
                return {"cmd": f"sistema compra {n}"}
            return {"cmd": f"buy {n}"}

    # 6) persone: attaccare, parlare, osservare, sfidare, domare, sigillare, accogliere, giurare
    verbs = [(r"^(attacca|attacchiamo|colpisci|aggredisci|uccidi|ammazza|combatti contro|combatti con|combatti)\b", "attack", True),
             (r"^(sfida|duella|duello)( a duello)?( con| contro)?\b", "duello", False),
             (r"^(parla|parliamo|chiacchiera)( con| a)?\b", "talk", False),
             (r"^(osserva|guarda|esamina|analizza|studia|scruta)\b", "osserva", False),
             (r"^(saluta)\b", "greet", False),
             (r"^(doma|addomestica)\b", "tame", True),
             (r"^(sigilla|marchia|schiavizza|rendi (mio |suo )?schiavo|rendilo (mio )?schiavo|fallo (mio )?schiavo)\b", "sigilla", True),
             (r"^(assorbi|divora)\b", "absorb", False),
             (r"^(accogli|prendi come discepolo)\b", "accogli", False),
             (r"^(giura fratellanza con|giura con|giura)\b", "giura", False),
             (r"^(recluta|porta con te)\b", "recruit", False),
             (r"^(risparmia)\b", "spare", True)]
    for pat, verb, foes in verbs:
        mm = re.match(pat, t)
        if not mm:
            continue
        rest = t[mm.end():].strip()
        if verb == "osserva" and (not rest or re.fullmatch(r"(in giro|intorno|attorno)", rest)):
            return {"cmd": "look"}
        if verb == "attack" and re.fullmatch(r"(tutti|tutti quanti|tutto)", rest):
            return {"cmd": "attack all"}
        who = _who(rest, s, enemies=foes) if rest else None
        if not who and verb == "sigilla":
            ch = (scene or {}).get("choices") or []
            c = next((c for c in ch if re.search(r"anima|marchi|servo", c.get("label", ""), re.I)), None)
            if c:
                return {"cmd": str(c["n"])}
        if who:
            return {"cmd": f"{verb} {who}"}

    # 6b) tutti gli altri verbi del gioco, all'imperativo (tabella VERBI qui sotto)
    hit = _verbs(t, s)
    if hit:
        return hit

    # 7) cloni e servi
    m = re.match(r"^(manda|metti|assegna|dispiega) (il )?clone (\S+ )?(a |ad |in )?(lavorare|esplorare|allenarsi|riposare|"
                 r"fare (le )?missioni|fare la guardia|guardia|missioni|esplora|lavora|allena|arti)\b", t)
    if m:
        task = {"lavorare": "lavora", "esplorare": "esplora", "allenarsi": "allena", "riposare": "riposa", "guardia": "guardia",
                "missioni": "missioni"}.get(m.group(5).split()[-1], m.group(5).split()[-1])
        n = _ordinal(m.group(3) or "")
        return {"cmd": f"clone {task}" + (f" {n}" if n else "")}
    m = re.match(r"^(metti|manda) (\S+(?: \S+)?) (di |a |al |alla |come )?(scorta|guardia|lavoro|lavorare|reggente)\b", t)
    if m:
        who = _who(m.group(2), s)
        if who:
            task = {"lavorare": "lavoro"}.get(m.group(4), m.group(4))
            return {"cmd": f"servo {who} {task}"}

    # 8) aprire le sezioni della dashboard
    if re.match(OPEN, t) or re.match(r"^(il |la |lo |le |i |gli )?(sezione|scheda|pannello|menu)\b", t):
        key = _section(t)
        if key:
            return {"ui": key}

    # 9) un numero da solo: la scena, o le azioni suggerite
    if re.fullmatch(r"\d+", t):
        return {"cmd": t}
    return {}


def context(conn, player) -> dict:
    """Il contesto minimo per il terminale (senza la dashboard): presenti e uscite."""
    from engine.core import entities
    out = {"presenti": [], "uscite": []}
    try:
        for n in entities.npcs_in_location(conn, player.location_id)[:30]:
            out["presenti"].append({"name": n.name, "kind": getattr(n, "kind", None) or "human", "rel": ""})
        for d, lid in entities.get_exits(conn, player.location_id).items():
            loc = entities.get_location(conn, lid)
            out["uscite"].append({"dir": d, "name": loc.name if loc else ""})
    except Exception:                                    # noqa: BLE001
        pass
    return out


# ---------------------------------------------------------------- l'imperativo di ogni comando del gioco
# (regex sulla frase normalizzata, modello del comando). Nei modelli: {n} il numero detto (anche «il terzo»),
# {who} il nome di chi è presente (per ordine o per nome), {rest} il resto della frase, {g} i giorni.
ATTR = {"forza": "FOR", "vitalita": "VIT", "vitalità": "VIT", "agilita": "AGI", "agilità": "AGI", "intelletto": "INT",
        "intelligenza": "INT", "saggezza": "SAG", "fortuna": "FRT", "for": "FOR", "vit": "VIT", "agi": "AGI",
        "int": "INT", "sag": "SAG", "frt": "FRT"}
SLOTS = ("veste", "corona", "amuleto", "anello", "stivali", "talismano")
VERBI = [
    # (Agg. 79) obiettivi, ricerca, bottega, prove, albero, riassunto
    (r"^(apri |mostra )?(l'|l |lo )?albero( dei dao)?$", "albero"),
    (r"^(riassunto|dove eravamo|ricordami dove eravamo|fammi il riassunto)$", "riassunto"),
    (r"^(togli|cancella|annulla) (l'|l )?obiettivo$", "obiettivo via"),
    (r"^(qual e|qual è|mostra|mostrami)? ?(il |l'|l )?(mio )?obiettivo$", "obiettivo"),
    (r"^(obiettivo|punta|voglio arrivare|voglio ottenere|voglio raggiungere)( a| al| alla| allo| all'| il| la| lo| l')? (?P<rest>.+)$",
     "obiettivo {rest}"),
    (r"^(vai |va )?(a )?bottega (da |dal |dalla )?(?P<rest>.+)$", "bottega {who}"),
    (r"^(impara|lavora) (da|dal|dalla|con) (?P<rest>.+)$", "bottega {who}"),
    (r"^(commissiona|ordina)( a| al| alla)? (?P<rest>.+)$", "commissiona {rest}"),
    (r"^(assisti|guarda (gli |l')?allenament[oi]|osserva (gli )?allenament[oi])$", "assisti"),
    (r"^(riscuoti|incassa)( dal| il)? laboratorio$", "laboratorio riscuoti"),
    (r"^(apri |mostra )?(il )?(mio )?laboratorio$", "laboratorio"),
    (r"^(affronta |tenta |fai )?(la )?prova (del cielo )?(di |d')?(bronzo|uno|1)$", "prova_cielo 1"),
    (r"^(affronta |tenta |fai )?(la )?prova (del cielo )?(di |d')?(argento|due|2)$", "prova_cielo 2"),
    (r"^(affronta |tenta |fai )?(la )?prova (del cielo )?(di |d')?(oro|tre|3)$", "prova_cielo 3"),
    (r"^(le )?prove del cielo$", "prova_cielo"),
    (r"^(cerca|trova) (?!(i |le )?(reperti|stele|rovine|insegnamenti))(?P<rest>.+)$", "cerca {rest}"),
    # (Agg. 77) le leggi nuove, le fusioni, i reperti
    (r"^(cerca|esamina|studia|fruga)( tra)? (i |le )?(reperti|stele|rovine|insegnamenti)( dei maestri)?$", "reperti"),
    (r"^(mostra |elenca |quali )?(le )?(fusioni|ricette di fusione)( possibili)?$", "fusione"),
    (r"^(mostra |elenca |quali )?(le )?(vie nuove|leggi nuove)$", "vie"),
    (r"^(mostra |quali )?(le )?(mie )?(intuizioni|scorci)$", "intuizioni"),
    (r"^(fondi|fondere|unisci|fusione( di| tra)?) (?!(le |la |i |il )?(tecnic|arm|oggett|anim|pietr|clon))(?P<rest>.+)$",
     "fusione {rest}"),
    (r"^(apri|impara|intraprendi) (la via|il dao|la legge) (del |della |dello |dell'|dei |delle )(?P<rest>.+)$", "comprehend {rest}"),
    # coltivazione e Dao
    (r"^(comprendi|studia|contempla|medita sul) (il )?(dao )?(del |della |dello |dell')?(?P<rest>.+)$", "comprehend {rest}"),
    (r"^(ritirati|vai in ritiro|ritiro|chiuditi in ritiro)( per| di)? (?P<g>\d+) (giorni|giorno)$", "ritiro {g}"),
    (r"^(apri|sblocca) (il |un )?meridian[oi]$", "meridiani apri"),
    (r"^(tempra|rafforza) (i )?meridian[oi]$", "meridiani tempra"),
    (r"^(risveglia|desta) (il )?(corpo del )?dharma$", "dharma risveglia"),
    (r"^(fondi|unisci) (il )?(corpo e (il )?sangue|corpo supremo)$", "corpo supremo"),
    (r"^(evolvi|fai evolvere) (il )?(sangue|lignaggio) (?P<n>\S+)$", "sangue evolvi {n}"),
    (r"^(trasformati|assumi la forma della bestia)$", "trasformati"),
    (r"^(fondi|unisci) (le )?tecniche (la |il )?(?P<a>\S+) e (la |il )?(?P<b>\S+)$", "tecniche fondi {a} {b}"),
    (r"^(fondi|unisci) (le )?(tecniche|la fusione) (migliore|migliori)$", "tecniche fondi migliore"),
    (r"^(allena|esercita) (la )?tecnica (?P<n>\S+)$", "tecniche allena {n}"),
    (r"^(impara|apprendi) (la )?tecnica (?P<n>\S+)$", "learn {n}"),
    (r"^(riempi|incastra|sistema) (il )?dantian$", "dantian auto"),
    (r"^(distribuisci|assegna) (i )?(punti|attributi)( automaticamente| da solo| in automatico)?$", "attributi auto"),
    (r"^(metti|assegna|aggiungi) (?P<n>\d+ )?(punt[oi] )?(in |a |su |alla |all'|al )?(?P<attr>forza|vitalita|vitalità|agilita|agilità|intelletto|intelligenza|saggezza|fortuna)$", "attributi {attr} {n}"),
    # oggetti, forgia, arti
    (r"^(forgia|crea|fabbrica) (un |una |la |il |lo |l')?(?P<slot>veste|corona|amuleto|anello|stivali|talismano)$", "equip forgia {slot}"),
    (r"^(forgia|crea|prepara|fabbrica|distilla) (la )?(ricetta|pillola|oggetto) (numero )?(?P<n>\S+)$", "craft {n}"),
    (r"^(scomponi|distruggi) (?P<rest>.+)$", "equip scomponi {rest}"),
    (r"^(raccogli|prendi) (il )?(raccolto|la produzione)( della dimora)?$", "dimora raccogli"),
    (r"^(potenzia|migliora) (la )?dimora( al massimo)?$", "dimora potenzia max"),
    # bestie e cavalcature
    (r"^(nutri|sfama) (la |il )?(bestia|animale|famiglio)$", "feed"),
    (r"^(cavalca|monta|sali in sella)( la bestia| il destriero)?$", "cavalca"),
    (r"^(smonta|scendi da cavallo|scendi dalla bestia|scendi di sella)$", "smonta"),
    (r"^(libera|rilascia) (la )?(bestia|animale)$", "release"),
    # setta
    (r"^(unisciti|iscriviti|entra)( alla| nella| in)? setta$", "join"),
    (r"^(lascia|abbandona) (la )?setta$", "leave"),
    (r"^(prendi|ritira|riscuoti) (lo )?stipendio$", "setta stipendio"),
    (r"^(chiedi|richiedi) (la )?promozione|^(fatti promuovere|sali di rango)$", "setta promozione"),
    (r"^(accetta|prendi) (la )?missione (?P<n>\S+)$", "missioni accetta {n}"),
    (r"^(completa|consegna|chiudi) (la |le )?mission[ei]$", "missioni completa"),
    (r"^(accetta) (l'|l )?invito (?P<n>\S+)$", "accept {n}"),
    (r"^(accetta|prendi) (l'|l )?incarico (?P<n>\S+)$", "incarico {n}"),
    (r"^(fonda|crea) (la |una )?(mia )?setta (?P<rest>.+)$", "fonda {rest}"),
    (r"^(sfida|affronta) (un )?(compagno|discepolo) (di rango |piu forte|più forte)?.*$", "challenge"),
    (r"^(difendi|proteggi) (il luogo|la citta|la città|il villaggio|dall'invasione)$", "defend"),
    (r"^(iscriviti|partecipa)( a| alla| al)? (meta |evento )?(?P<n>\d+)$", "iscriviti {n}"),
    # persone e famiglia
    (r"^(insegna|dai lezione)( a)? (?P<rest>.+)$", "insegna {who}"),
    (r"^(proponi|dichiarati|chiedi la mano)( a)? (?P<rest>.+)$", "proponi {who}"),
    (r"^(chiama|evoca) (?P<rest>.+)$", "chiama {who}"),
    (r"^(congeda|manda via) (il )?(compagno)$", "dismiss"),
    (r"^(visita|vai a trovare) (la )?famiglia$", "famiglia visita"),
    (r"^(difendi|proteggi) (la )?famiglia$", "famiglia difendi"),
    (r"^(dona|manda|regala) (?P<n>\d+) (pietre )?(alla )?famiglia$", "famiglia dona {n}"),
    (r"^(libera|lascia andare) (?P<rest>.+)$", "servo {who} libera"),
    (r"^(rinsalda|rafforza) (il sigillo (di |su )?)?(?P<rest>.+)$", "servo {who} rinsalda"),
    (r"^(rianima|resuscita) (?P<rest>.+)$", "rianima {who}"),
    # trame e saghe
    (r"^(indaga|investiga)( sulla)?( trama)? (?P<n>\S+)$", "trame indaga {n}"),
    (r"^(accusa|smaschera)( il colpevole)?( della)?( trama)? (?P<n>\S+)$", "trame accusa {n}"),
    (r"^(continua|prosegui) (la )?trama (?P<n>\S+)$", "trame continua {n}"),
    # viaggi e mondo
    (r"^(teletrasportati|teletrasporto)( al| alla| a)?( formazione)? (?P<n>\S+)$", "teletrasporto {n}"),
    (r"^(entra|entriamo)( nel)? reame$", "enter"),
    (r"^(scendi|esplora)( al)?( piano successivo| nel reame| il reame| piu a fondo| più a fondo)$", "delve"),
    (r"^(esci|lascia) (dal |il )?reame$", "realm esci"),
    (r"^(ascendi|sali al mondo superiore)$", "ascendi_mondo"),
    # i generici, per ultimi
    (r"^(regala|dona|offri) (?P<n>\d+) (pietre )?(a |al |alla )(?P<rest>.+)$", "gift {who} {n}"),
    (r"^(usa|prendi|bevi|mangia|ingoia|assorbi) (la |il |lo |l'|un |una )?(?P<rest>.+)$", "use {rest}"),
    # partita
    (r"^(carica|carica la partita) (?P<rest>.+)$", "carica {rest}"),
    (r"^(salva|salva la partita) (come |in |nello slot )?(?P<rest>.+)$", "salva {rest}"),
]


def _verbs(t: str, s: dict) -> dict | None:
    for pat, tpl in VERBI:
        m = re.match(pat, t)
        if not m:
            continue
        g = m.groupdict()
        rest = (g.get("rest") or "").strip()
        vals = {"rest": rest, "g": g.get("g") or "", "slot": g.get("slot") or "", "a": "", "b": "", "attr": "", "n": ""}
        for k in ("a", "b"):
            if g.get(k):
                v = g[k]
                vals[k] = str(ORD.get(_plain(v), v))
        if g.get("n") is not None:
            nn = _ordinal(g["n"])
            vals["n"] = str(nn) if nn else g["n"].strip()
        if g.get("attr"):
            vals["attr"] = ATTR.get(_plain(g["attr"]), g["attr"].upper()[:3])
        if "{who}" in tpl:
            who = _who(rest, s) or (rest.split(" ")[0] if rest else "")
            if not who:
                continue
            vals["who"] = who
        cmd = tpl.format(**vals).strip()
        return {"cmd": re.sub(r"\s+", " ", cmd)}
    return None


# ---------------------------------------------------------------- il prontuario (comando «voce»)
CHEATSHEET = """🎙 COMANDI A VOCE — si dicono come ordini, senza formule di cortesia
  Muoverti:      «vai a est» · «sali» · «scendi» · «vai a Città di Cenere» · «vai alla seconda meta» · «torna a casa»
  Coltivare:     «allenati» · «medita» · «sfonda» · «tempra lo spirito» · «ritirati per 5 giorni» · «comprendi il Dao della spada»
  Persone:       «osserva il primo» · «parla con Mei» · «attacca il primo nemico» · «attacca tutti» · «caccia»
                 «sfida a duello Xu» · «doma la bestia» · «sigilla Xu» · «regala 100 pietre a Mei» · «insegna a Lin»
  Duello:        «colpisci» · «difenditi» · «concentrati» · «pillola» · «scappa» · «attacco due» · «tecnica tre» · «attacco più forte»
  Scene:         «la seconda» · «scelta tre» · oppure le parole della scelta («risparmialo», «marchiagli l'anima»)
  Oggetti:       «raccogli» · «saccheggia» · «assorbi tutto» · «usa le pillole» · «usa le essenze» · «equipaggia il meglio»
                 «forgia una corona» · «crea la ricetta 2» · «compra la terza» (al mercato, al tesoro della setta…)
  Setta:         «accetta la missione 2» · «completa la missione» · «prendi lo stipendio» · «chiedi la promozione»
  Seguaci:       «crea un clone» · «dispiega i cloni» · «manda il clone 2 a esplorare» · «metti Xu di scorta» · «libera Xu»
  Trame:         «indaga sulla trama 1» · «accusa 1» · «continua la trama 2»
  Dashboard:     «apri il Dao» · «apri il corpo» · «apri il sangue» · «apri i pilastri» · «apri l'eroe» · «apri la mappa»
                 «apri lo zaino» · «apri le saghe» · «apri la setta» · «apri i cloni» · «apri le opzioni» · «oggi»
  Lettura:       «avanti» · «mostra tutto» · «ripeti» · «chiudi» · «pilota per 7 giorni» · «ferma»
  Sempre:        «fai la prossima cosa» (la prima voce di «Cosa fare ora»)
Ogni comando scritto continua a funzionare uguale."""
