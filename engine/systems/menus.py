"""
MENU A SEZIONI — un posto solo per ogni parte del gioco, con le azioni già pronte.

Ogni menu è fatto di SEZIONI; ogni sezione ha qualche riga di stato, a volte una barra di
avanzamento, e le AZIONI che puoi fare da lì. Le stesse strutture vengono mostrate:
  · nel terminale: le azioni sono numerate — scrivi il numero per eseguirla;
  · nella dashboard: ogni azione è un pulsante (quelle non ancora possibili dicono perché).

  menu            l'indice di tutti i menu
  setta           la tua setta: ascesa, tecniche, tesoro del merito, rango, missioni, anziani, guerre
  arti            le arti (alchimia, forgia…): quali praticare, ricette pronte
  regni           regni e corti, guerre, trono, razze antiche
  eventi          tutto ciò a cui puoi partecipare ora nel mondo
  coltivazione    allenamento, sfondamento, Dao, metodo, grotta-dimora
  dimora          la grotta-dimora: produzione, ali, «potenzia al massimo» in un colpo
  famiglia        la famiglia, i legami (parla, favori, duelli con rivali e nemesi), i discepoli
"""

from __future__ import annotations

from engine.systems import state

OPEN_KEY = "menu_open"


def act(label: str, cmd: str, ok: bool = True, why: str = "", main: bool = False) -> dict:
    return {"label": label, "cmd": cmd, "ok": bool(ok), "why": why if not ok else "", "main": main}


def bar(label: str, pct: float, text: str = "", tone: str = "") -> dict:
    """tone: '' (verde) · 'bad' (rosso: rancore, pericolo) · 'warn' · 'info' · 'rare'."""
    return {"label": label, "pct": max(0, min(100, int(pct))), "text": text, "tone": tone}


def section(title: str, lines: list[str] | None = None, actions: list[dict] | None = None,
            bars: list[dict] | None = None, icon: str = "") -> dict:
    return {"title": title, "icon": icon, "lines": [ln for ln in (lines or []) if ln],
            "actions": actions or [], "bars": bars or []}


def menu(key: str, title: str, sub: list[str] | None = None, sections: list[dict] | None = None,
         foot: str = "") -> dict:
    return {"key": key, "title": title, "sub": [s for s in (sub or []) if s],
            "sections": [s for s in (sections or []) if s and (s["lines"] or s["actions"] or s["bars"])],
            "foot": foot}


# ---------------------------------------------------------------- registro

def _builders() -> dict:
    from engine.systems import sect_menu, world_menus, professions
    return {"setta": sect_menu.build, "arti": world_menus.arts, "regni": world_menus.realms,
            "eventi": world_menus.events, "menu": world_menus.hub, "coltivazione": world_menus.growth,
            "famiglia": world_menus.family_menu, "dimora": world_menus.abode, "faide": world_menus.grudges}


NAMES = {"setta": "Setta", "arti": "Arti", "regni": "Regni", "eventi": "Eventi", "menu": "Menu",
         "coltivazione": "Coltivazione", "famiglia": "Famiglia", "dimora": "Dimora", "faide": "Faide"}


def build(conn, player, key: str) -> dict:
    return _builders()[key](conn, player)


# ---------------------------------------------------------------- terminale

def _txtbar(pct: int, n: int = 16) -> str:
    k = round(n * pct / 100)
    return "█" * k + "·" * (n - k)


def render(conn, m: dict) -> str:
    """Il menu come testo numerato; i numeri restano validi finché non scrivi un altro comando."""
    out = [m["title"]] + [f"  {s}" for s in m["sub"]]
    cmds: list[str] = []
    for sec in m["sections"]:
        out.append(f"── {sec['icon'] + ' ' if sec['icon'] else ''}{sec['title']} ──")
        for b in sec["bars"]:
            out.append(f"  {b['label']} [{_txtbar(b['pct'])}] {b['pct']}%" + (f" — {b['text']}" if b["text"] else ""))
        out += [f"  {ln}" for ln in sec["lines"]]
        for a in sec["actions"]:
            if a["ok"]:
                cmds.append(a["cmd"])
                out.append(f"  [{len(cmds)}] {a['label']}")
            else:
                out.append(f"   ·  {a['label']} — {a['why']}")
    if m["foot"]:
        out.append(m["foot"])
    if cmds:
        out.append("(scrivi il numero dell'azione, o un altro comando)")
    from engine.systems import suggestions
    suggestions.store(conn, [("", c) for c in cmds])
    state.set(conn, OPEN_KEY, "1")
    return "\n".join(out)


def consume_open(conn) -> bool:
    """True se l'ultimo comando ha aperto un menu (le azioni numerate sono le sue)."""
    if state.flag(conn, OPEN_KEY, False):
        state.delete(conn, OPEN_KEY)
        return True
    return False


def show(conn, player, key: str) -> str:
    return render(conn, build(conn, player, key))
