"""
IL CORPO SUPREMO — quando il corpo leggendario e il sangue più alto diventano una cosa sola.

Sopra i corpi leggendari e sopra i lignaggi più nobili c'è qualcosa che nessuna storia nomina
due volte: il corpo che nasce dalla FUSIONE di un corpo compiuto e di un sangue ancestrale.
Si sblocca solo in cima a entrambe le vie:

  · il corpo leggendario al CORPO COMPIUTO (stadio 5);
  · un lignaggio di rango Ancestrale o più alto (le Bestie Ancestrali, il Caos, oltre il Caos)
    al grado Primordiale o più alto.

Allora il comando 'corpo supremo' apre la FUSIONE (sette giorni di ritiro). Quale corpo nasce
dipende da cosa fondi: il Drago Vero col sangue dei draghi dà il Corpo del Sovrano dei Draghi
Ancestrali, il Caos con l'Hundun il Corpo del Primo Dio, e così via. Una volta nato, il Corpo
Supremo CRESCE di livello senza fine: ogni risveglio del corpo e ogni grado del sangue in più lo
alzano, e ogni livello ne rafforza tutti i doni. Ogni 5 livelli impari un nuovo grado della sua
tecnica.

Doni (al livello 1, poi +10% a livello):
  coltivazione +40%, attacco +20%, danni subiti −12%, un colpo e una resurrezione in più per
  scontro, il sangue e i doni del corpo più forti del 30%, la tecnica suprema.
"""

from __future__ import annotations

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "supreme_body"
BODY_STAGE = 5                          # Corpo Compiuto
BLOOD_RANK = 7
BLOOD_GRADE = 6                         # Primordiale
RITUAL_DAYS = 7
_ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]

# (nome, corpi, famiglie di sangue, tecnica, racconto, dono speciale)
FORMS = [
    ("Corpo del Primo Dio", {"caos", "dao_innato"}, {"hundun"}, "Palmo che Apre il Caos",
     "Prima del Cielo c'era il Caos, e nel Caos un dio senza nome. Ora ha il tuo volto.", {"chance": 0.15}),
    ("Corpo del Sovrano dei Draghi Ancestrali", {"drago", "tuono"},
     {"drago della torcia", "drago azzurro", "drago giallo", "drago", "jiao"}, "Ruggito dei Diecimila Draghi",
     "I draghi di ogni era chinano la testa: il loro sovrano è tornato.", {"atk": 0.10}),
    ("Corpo della Fenice dell'Eterno Nirvana", {"fenice_nirvana", "nove_yang", "sole"},
     {"uccello vermiglio", "fenice"}, "Volo che Brucia le Ere",
     "Mille volte morta, mille volte rinata: la fenice non ricorda più cosa sia la fine.", {"saves": 1}),
    ("Corpo dei Mille Mondi", {"vuoto", "anima_celeste", "doppie_pupille"}, {"kunpeng", "kun"},
     "Mondo che si Apre nel Palmo", "Nel tuo corpo si aprono mondi interi, e tu cammini tra loro.", {"evade": 0.10}),
    ("Corpo del Re dei Demoni Celesti", {"ombra", "asura", "veleno"}, {"taotie", "qiongqi", "demone", "tiangou"},
     "Fauci che Divorano i Cieli", "I demoni delle nove ere ti chiamano re, e il Cielo ha fame di te.",
     {"proc": ("drenaggio", 0.18, 1.6)}),
    ("Corpo della Montagna Primordiale", {"santo_antico", "spezzati", "immortale"}, {"taowu", "gigante"},
     "Pugno che Sposta le Ere", "Sei la montagna che reggeva il cielo prima che il cielo esistesse.", {"taken": 0.08}),
    ("Corpo dell'Abisso del Nord", {"vene_yin", "luna", "giada"}, {"xiangliu", "tartaruga nera", "leviatano"},
     "Marea delle Nove Fonti", "Le acque sotto il mondo salgono quando chiami.", {"proc": ("gelo", 0.18, 1.6)}),
    ("Corpo della Spada che Precede il Cielo", {"ossa_spada", "occhi", "osso_supremo"}, {"tigre bianca", "qiongqi"},
     "Spada Prima della Creazione", "La prima cosa che il mondo vide fu una spada. Era la tua.", {"pierce": 0.12}),
]
GENERIC = ("Corpo Supremo del Cielo e della Terra", set(), set(), "Pugno del Cielo e della Terra",
           "Corpo e sangue sono diventati una cosa sola, più alta di entrambi.", {"atk": 0.06, "taken": 0.04})


def get(conn) -> dict | None:
    return state.get_json(conn, KEY, None)


def _best_blood(conn) -> tuple[dict | None, int, int]:
    from engine.systems import bloodlines as B
    best = (None, 0, 0)
    for _k, ln in B.all_lines(conn).items():
        r, g = B.line_rank(ln), B.grade_index(ln["conc"])
        if (r, g) > (best[1], best[2]):
            best = (ln, r, g)
    return best


def requirements(conn) -> dict:
    from engine.systems import constitutions
    c = constitutions.get(conn)
    st = int(c.get("stage", 0)) if c else 0
    ln, r, g = _best_blood(conn)
    missing = []
    if not c:
        missing.append("un corpo leggendario")
    elif st < BODY_STAGE:
        missing.append(f"il corpo compiuto (stadio {st}/{BODY_STAGE})")
    if r < BLOOD_RANK:
        missing.append("un lignaggio di rango Ancestrale (fondi o evolvi il tuo sangue)")
    elif g < BLOOD_GRADE:
        missing.append("il grado Primordiale nel lignaggio ancestrale")
    return {"ok": not missing, "missing": missing, "body": c, "stage": st, "line": ln, "rank": r, "grade": g}


def form_for(body_key, line: dict | None) -> tuple:
    """body_key: la chiave del corpo, o l'elenco (il tuo corpo e quelli assorbiti)."""
    keys = set(body_key) if isinstance(body_key, (list, tuple, set)) else {body_key}
    fams = set((line or {}).get("families") or []) | set((line or {}).get("minor") or [])
    scored = []
    for f in FORMS:
        s = (2 if keys & f[1] else 0) + (2 if fams & f[2] else 0)
        scored.append((s, f))
    s, f = max(scored, key=lambda x: x[0])
    return f if s >= 2 else GENERIC


def level(conn) -> int:
    sb = get(conn)
    if not sb:
        return 0
    rq = requirements(conn)
    return max(1, 1 + (rq["stage"] - BODY_STAGE) + (rq["grade"] - BLOOD_GRADE) + int(sb.get("bonus", 0)))


def _mult(conn) -> float:
    return 1.0 + 0.10 * (level(conn) - 1)


def unite(conn, player) -> str:
    from engine.simulation import world_tick
    if get(conn):
        return describe(conn)
    rq = requirements(conn)
    if not rq["ok"]:
        return ("Il CORPO SUPREMO nasce solo in cima a entrambe le vie: corpo leggendario compiuto e sangue "
                "ancestrale al grado Primordiale. Ti manca: " + "; ".join(rq["missing"]) + ".")
    form = form_for([rq["body"]["key"]] + list(rq["body"].get("absorbed") or []), rq["line"])
    world_tick.advance(conn, 120 * RITUAL_DAYS)
    state.set_json(conn, KEY, {"name": form[0], "tech": form[3], "body": rq["body"]["key"],
                               "line": rq["line"]["name"], "day": tick_mod.get_tick(conn) // 120, "techs": 0})
    out = [f"Per {RITUAL_DAYS} giorni il tuo corpo e il tuo sangue si combattono, poi si riconoscono, poi smettono "
           f"di essere due.",
           f"✦✦ NASCE IL {form[0].upper()} ✦✦", form[4],
           "Coltivazione, attacco, difesa, sangue e doni del corpo salgono tutti insieme; un colpo e una "
           "resurrezione in più per scontro."]
    out += _grant_techs(conn, player)
    state.grant_title(conn, form[0])
    out.append(f"✧ Nuovo titolo: «{form[0]}» ✧")
    return "\n".join(out)


def _grant_techs(conn, player) -> list[str]:
    """La tecnica suprema: un grado ogni 5 livelli (I al livello 1, II al 5, III al 10…)."""
    sb = get(conn)
    if not sb:
        return []
    lv = level(conn)
    want = 1 + lv // 5
    out = []
    t = tick_mod.get_tick(conn)
    while int(sb.get("techs", 0)) < want:
        n = int(sb.get("techs", 0)) + 1
        name = f"{sb['tech']} ({_ROMAN[n - 1] if n <= len(_ROMAN) else n})"
        mag = round(0.25 * (1 + 0.5 * (n - 1)), 3)
        conn.execute("INSERT OR IGNORE INTO learned_techniques (player_id, faction_id, tech_key, name, magnitude, "
                     "learned_tick) VALUES (?, NULL, ?, ?, ?, ?);", (player.id, f"supremo:{n}", name, mag, t))
        sb["techs"] = n
        out.append(f"✧ Tecnica suprema: «{name}» (+{int(100 * mag)}% potenza).")
    state.set_json(conn, KEY, sb)
    return out


def check_growth(conn, player) -> list[str]:
    """Dopo ogni comando: se il livello è salito, nuove tecniche supreme."""
    sb = get(conn)
    if not sb:
        return []
    lv = level(conn)
    last = int(sb.get("last_level", 1))
    if lv <= last:
        return []
    sb["last_level"] = lv
    state.set_json(conn, KEY, sb)
    return [f"✦ Il {sb['name']} cresce: livello {lv}."] + _grant_techs(conn, player)


def ready_note(conn) -> str | None:
    if get(conn):
        return None
    return "Il tuo corpo e il tuo sangue sono pronti a fondersi: 'corpo supremo'." if requirements(conn)["ok"] else None


def after_command(conn, player) -> list[str]:
    """Il giro dopo ogni comando: poteri del corpo raggiunti, crescita del Corpo Supremo, e l'annuncio
    (una volta sola) che la fusione è possibile."""
    from engine.systems import body_powers
    out = body_powers.sync(conn)
    out += check_growth(conn, player)
    note = ready_note(conn)
    if note and not state.flag(conn, "supreme_ready_told", False):
        state.set(conn, "supreme_ready_told", "1")
        out.append("✦ " + note)
    return out


# ---------------------------------------------------------------- effetti

def form_of(conn) -> tuple | None:
    sb = get(conn)
    if not sb:
        return None
    return next((f for f in FORMS if f[0] == sb["name"]), GENERIC)


def combat(conn, fx) -> list[str]:
    f = form_of(conn)
    if not f:
        return []
    m = _mult(conn)
    pr = fx.p.prof
    fx.p.atk_mult *= 1.0 + 0.20 * m
    pr["taken"] = pr.get("taken", 0.0) + min(0.3, 0.12 * m)
    pr["extra_strikes"] = pr.get("extra_strikes", 0) + 1 + (level(conn) // 10)
    fx.p.lethal_saves += 1 + int(f[5].get("saves", 0))
    sp = f[5]
    for k in ("crit", "evade", "pierce", "taken"):
        if sp.get(k):
            pr[k] = pr.get(k, 0.0) + sp[k] * m
    if sp.get("atk"):
        fx.p.atk_mult *= 1.0 + sp["atk"] * m
    if sp.get("chance"):
        pr["chance_mult"] = pr.get("chance_mult", 1.0) * (1.0 + sp["chance"] * m)
    if sp.get("proc"):
        s, ch, pw = sp["proc"]
        fx.add_proc("p", s, min(0.5, ch * m), pw, f"supremo:{f[0]}")
    return [f"✦ Il tuo {f[0]} si desta."]


def cultivation_mult(conn) -> float:
    return 1.0 + 0.40 * _mult(conn) if get(conn) else 1.0


def blood_mult(conn) -> float:
    """Il sangue e i doni del corpo, nel Corpo Supremo, valgono il 30% in più (e crescono col livello)."""
    return 1.0 + 0.30 * _mult(conn) if get(conn) else 1.0


def describe(conn) -> str:
    sb = get(conn)
    if not sb:
        rq = requirements(conn)
        return ("✦ CORPO SUPREMO — non ancora nato. "
                + ("Puoi fondere corpo e sangue ora: 'corpo supremo'." if rq["ok"] else
                   "Serve: " + "; ".join(rq["missing"]) + "."))
    f = form_of(conn)
    lv = level(conn)
    return (f"✦ {sb['name']} — livello {lv} (doni ×{_mult(conn):.1f}). {f[4]}\n"
            f"  Nato dal corpo e dal {sb['line']}. Tecnica: {sb['tech']} ({sb.get('techs', 1)}° grado). "
            f"Prossimo grado della tecnica al livello {5 * (lv // 5 + 1)}.")


def summary(conn) -> dict | None:
    sb = get(conn)
    if sb:
        return {"nome": sb["name"], "livello": level(conn), "testo": form_of(conn)[4], "pronto": False}
    rq = requirements(conn)
    return {"nome": None, "pronto": rq["ok"], "manca": rq["missing"]}
