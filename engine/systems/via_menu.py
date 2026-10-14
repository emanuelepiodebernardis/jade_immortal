"""
LA TUA VIA (Aggiornamento 59) — un pannello solo per tutto ciò che fa crescere il personaggio.

Prima c'erano sette menu separati nella barra (coltivazione, attributi, forza, tecniche, Dao
profondi, spiriti, sangue) più il corpo leggendario sparso nei testi. Ora sono SCHEDE di un unico
menu «via»: nella dashboard un pulsante e una fila di schede; nel terminale 'via', 'via sangue'…
I vecchi comandi ('sangue', 'tecniche', 'forza'…) continuano a funzionare.

Le schede sono un registro: aggiungerne una è una riga in TABS.
"""

from __future__ import annotations

from engine.systems import menus as M

# chiave → (etichetta, menu sorgente in menus._builders oppure funzione locale)
TABS = [
    ("coltivazione", "☯ Coltivazione", "coltivazione"),
    ("corpo", "✦ Corpo", None),
    ("sangue", "🩸 Sangue", "sangue"),
    ("attributi", "🪟 Attributi", "attributi"),
    ("tecniche", "⚒ Tecniche", "tecniche"),
    ("profondi", "🌌 Dao profondi", "profondi"),
    ("spiriti", "✺ Spiriti", "spiriti"),
    ("forza", "⚖ Forza", "forza"),
]
KEYS = [k for k, _l, _s in TABS]
DEFAULT = "coltivazione"
ALIAS = {"costituzione": "corpo", "body": "corpo", "lignaggi": "sangue", "attr": "attributi",
         "fucina": "tecniche", "dao": "profondi", "bilancio": "forza", "fonti": "forza"}


def tab_of(arg: str) -> str:
    a = (arg or "").strip().lower().split(" ")[0]
    a = ALIAS.get(a, a)
    return a if a in KEYS else DEFAULT


def _body(conn, player) -> dict:
    from engine.systems import constitutions, supreme_body
    txt = constitutions.describe_full(conn).split("\n")
    acts = []
    if supreme_body.ready_note(conn):
        acts.append(M.act("⇑ Fondi corpo e sangue nel Corpo Supremo", "corpo supremo", main=True))
    secs = [M.section(txt[0].strip().lstrip("✦ ").strip(), [ln.strip() for ln in txt[1:]], acts, icon="✦")]
    try:
        from engine.systems import dao_heart
        h = dao_heart.describe(conn, player).split("\n")[1:]
        own = [ln.strip() for ln in h if ln.startswith("  ") and not ln.startswith("   ") and not ln.startswith("  ✦")]
        from engine.systems import dao_heart as dh
        tox_act = [M.act("Purifica i meridiani (pillole, poi un bagno di Qi)", "purifica", dh.toxin(conn) >= 1,
                         "i meridiani sono puliti", main=dh.toxin(conn) >= 30)]
        secs.append(M.section("Cuore e tossine", own, tox_act, icon="♥"))   # solo cuore e tossine: il corpo è già sopra
    except Exception:
        pass
    return M.menu("via:corpo", "Corpo", sections=secs)


def build(conn, player, key: str) -> dict:
    tab = tab_of(key.split(":", 1)[1] if ":" in key else "")
    src = dict((k, s) for k, _l, s in TABS)[tab]
    inner = _body(conn, player) if src is None else M._builders()[src](conn, player)
    m = M.menu("via", "La tua Via", sub=inner.get("sub"), sections=inner.get("sections"), foot=inner.get("foot", ""))
    m["key"] = "via:" + tab
    m["tab"] = tab
    m["tabs"] = [{"key": "via:" + k, "label": lab, "on": k == tab} for k, lab, _s in TABS]
    m["inner_title"] = inner.get("title", "")
    return m


def show(conn, player, arg: str) -> str:
    m = build(conn, player, "via:" + tab_of(arg))
    head = "Schede: " + " · ".join(("[" + t["label"] + "]") if t["on"] else t["label"] for t in m["tabs"]) \
           + "   (via <scheda>)"
    m = dict(m)
    m["sub"] = [head] + ([m["inner_title"]] if m["inner_title"] else []) + list(m["sub"])
    return M.render(conn, m)
