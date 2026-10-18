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
    ("anime", "✧ Anime", None),
    ("forza", "⚖ Forza", "forza"),
]
KEYS = [k for k, _l, _s in TABS]
DEFAULT = "coltivazione"
ALIAS = {"costituzione": "corpo", "body": "corpo", "lignaggi": "sangue", "attr": "attributi",
         "fucina": "tecniche", "dao": "profondi", "bilancio": "forza", "fonti": "forza",
         "vasi": "anime", "anello": "anime", "artefatti": "anime"}


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
    from engine.systems import mounts, beasts
    if beasts.pets(conn, player.id):
        b = mounts.mounted(conn, player.id)
        secs.append(M.section("La cavalcatura", [mounts.describe(conn, player)],
                              [M.act("Smonta" if b else "Cavalca la tua bestia", "smonta" if b else "cavalca")], icon="🐎"))
    return M.menu("via:corpo", "Corpo", sections=secs)


def build(conn, player, key: str) -> dict:
    tab = tab_of(key.split(":", 1)[1] if ":" in key else "")
    src = dict((k, s) for k, _l, s in TABS)[tab]
    if tab == "anime":
        from engine.systems import soul_artifacts
        inner = M.menu("via:anime", "✧ I VASI D'ANIMA",
                       ["Oggetti con un'anima dentro: crescono, insegnano, combattono con te, e hanno una storia."],
                       soul_artifacts.menu_sections(conn, player))
    else:
        inner = _body(conn, player) if src is None else M._builders()[src](conn, player)
    if tab == "tecniche":
        from engine.systems import dantian
        inner = dict(inner)
        inner["sections"] = [dantian.menu_section(conn, player)] + list(inner.get("sections", []))
    if tab == "coltivazione":
        from engine.systems import breakthrough_fates
        fl = breakthrough_fates.lines_for_menu(conn)
        inner = dict(inner)
        from engine.systems import soul_roam
        _s = list(inner.get("sections", []))
        from engine.systems import stone_qi
        inner["sections"] = _s[:1] + [soul_roam.menu_section(conn, player), stone_qi.menu_section(conn, player)] + _s[1:] + [M.section(
            "Destini dello sfondamento", fl or ["A ogni nuovo regno il Cielo ti offre tre destini: ne scegli uno, "
                                              "per tutta la vita."], icon="✧")]
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
