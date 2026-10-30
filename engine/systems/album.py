"""
L'ALBUM DEL COLTIVATORE (Aggiornamento 72) — un'enciclopedia illustrata da completare come un album.

Sei pagine, ognuna con la sua collezione: chi trovi è a colori, chi manca è un'ombra con un indizio.
  🐾 Bestiario     le specie di bestie del mondo (comuni e rare): le incontri combattendo o domandole
  ☸ Dao            i trentuno Dao: li conosci quando ne comprendi anche un poco
  🗺 Luoghi        i luoghi del mondo che hai visitato
  🎒 Tesori        i tipi di tesoro (pillole, essenze, nuclei, manuali, reliquie…) che hai avuto in mano
  🐉 Trasformazioni le forme di sangue risvegliate (drago, fenice, qilin…)
  🧥 Equipaggiamento i set (Fenice, Tartaruga, Drago, Tigre, Qilin) di cui hai trovato almeno un pezzo

Ogni pagina dà un premio al 25, 50, 75 e 100% (pietre, poi un titolo); 'album premi' li ritira.
Le immagini sono quelle della cartella «immagini» (bestie/, dao/, luoghi/, oggetti/, trasformazioni/…).
Si legge soltanto quello che il gioco già ricorda (codex dei luoghi e delle bestie, libro dei tesori, Dao):
nessun nuovo stato da tenere in sincronia, tranne i premi ritirati.
"""

from __future__ import annotations

import re

from engine.systems import state

KEY = "album_prizes"
STEPS = (25, 50, 75, 100)
PAGES = [("bestie", "🐾 Bestiario"), ("dao", "☸ Dao"), ("luoghi", "🗺 Luoghi"), ("tesori", "🎒 Tesori"),
         ("trasformazioni", "🐉 Trasformazioni"), ("set", "🧥 Equipaggiamento")]
TREASURE_KINDS = [("pillola", "Pillole", "oggetti/pillola"), ("essenza", "Essenze", "oggetti/essenza"),
                  ("nucleo", "Nuclei di bestia", "oggetti/nucleo"), ("manuale", "Manuali", "oggetti/manuale"),
                  ("tesoro", "Tesori", "oggetti/tesoro"), ("reliquia", "Reliquie", "oggetti/reliquia"),
                  ("talismano", "Talismani", "oggetti/talismano"), ("formazione", "Formazioni", "oggetti/formazione"),
                  ("uovo", "Uova di bestia", "oggetti/uovo"), ("incenso", "Incensi", "oggetti/incenso"),
                  ("sangue", "Sangue antico", "oggetti/essenza_sangue")]
FORMS = [("drago", "Drago"), ("fenice", "Fenice"), ("qilin", "Qilin"), ("demone", "Demone"), ("silvano", "Silvano"),
         ("gigante", "Gigante"), ("leviatano", "Leviatano")]


def _base(name: str) -> str:
    return re.sub(r"\s*\d+$", "", name or "").strip()


def _slug(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def _beast_img(name: str) -> list[str]:
    low = _slug(name)
    for w in ("drago", "fenice", "tigre", "tartaruga", "qilin", "gru", "volpe", "serpente", "kun"):
        if w in low:
            return [f"bestie/{w}", "creature/beast"]
    if any(w in low for w in ("spettro", "spirito", "anima", "eco")):
        return ["creature/spirit"]
    if any(w in low for w in ("demon", "maligna", "ombra")):
        return ["creature/demon"]
    return ["creature/beast"]


def pages(conn, player) -> dict:
    from engine.systems import beasts, gear
    out: dict = {}
    # bestiario
    seen = {_base(n) for n in (state.get_json(conn, "world_codex_bestie", []) or [])}
    try:
        for r in beasts.pets(conn, player.id):
            seen.add(_base(r["name"]))
    except Exception:                                  # noqa: BLE001
        pass
    species = list(beasts.COMMON_ELEMENT) + [s[0] for s in beasts.RARE_SPECIES]
    out["bestie"] = [{"nome": s, "visto": s in seen, "img": _beast_img(s),
                      "sub": next((r[1] for r in beasts.RARE_SPECIES if r[0] == s), "comune")} for s in species]
    # dao
    known = {r["dao_key"] for r in conn.execute(
        "SELECT dao_key FROM character_daos WHERE character_type='player' AND character_id=? AND comprehension>0;",
        (player.id,))}
    out["dao"] = [{"nome": r["name"], "visto": r["dao_key"] in known, "img": [f"dao/{r['dao_key']}"],
                   "sub": r["level"] or ""} for r in conn.execute("SELECT dao_key, name, level FROM daos ORDER BY name;")]
    # luoghi
    visited = set(state.get_json(conn, "world_codex_luoghi", []) or [])
    out["luoghi"] = [{"nome": r["name"], "visto": r["name"] in visited,
                      "img": [f"luoghi/{r['location_type']}", "mondi/0"], "sub": r["location_type"] or ""}
                     for r in conn.execute("SELECT name, location_type FROM locations ORDER BY name;")]
    # tesori: i tipi
    book = state.get_json(conn, "world_book_items", {}) or {}
    have_kinds = {e.get("kind") for e in book.values()}
    try:
        from engine.systems import items
        have_kinds |= {r["item_type"] for r in items.player_inventory(conn, player.id)}
    except Exception:                                  # noqa: BLE001
        pass
    out["tesori"] = [{"nome": lab, "visto": k in have_kinds, "img": [img], "sub": ""} for k, lab, img in TREASURE_KINDS]
    # trasformazioni: le forme di sangue
    forms = set()
    try:
        from engine.systems import bloodlines
        for _k, ln in bloodlines.ordered(conn):
            sp = _slug(str(ln.get("species", "")) + " " + str(ln.get("name", "")))
            forms |= {f for f, _l in FORMS if f in sp}
    except Exception:                                  # noqa: BLE001
        pass
    out["trasformazioni"] = [{"nome": lab, "visto": f in forms, "img": [f"trasformazioni/{f}"], "sub": "sangue"}
                             for f, lab in FORMS]
    # set dell'equipaggiamento
    g = gear.get(conn)
    sets = {x.get("set") for x in list(g["eq"].values()) + g["bag"] if x.get("set")}
    out["set"] = [{"nome": "Set " + name.split(" ", 1)[-1], "visto": k in sets,
                   "img": [f"oggetti/sigillo_{k}", "oggetti/eq_amuleto"], "sub": ""} for k, (name, _fx) in gear.SETS.items()]
    return out


def progress(entries: list[dict]) -> int:
    return round(100 * sum(1 for e in entries if e["visto"]) / max(1, len(entries)))


def view(conn, player) -> dict:
    p = pages(conn, player)
    got = state.get_json(conn, KEY) or {}
    out = []
    for k, title in PAGES:
        pct = progress(p[k])
        claim = [s for s in STEPS if pct >= s and s not in got.get(k, [])]
        out.append({"key": k, "titolo": title, "pct": pct, "voci": p[k], "premi": claim,
                    "visti": sum(1 for e in p[k] if e["visto"]), "totale": len(p[k])})
    return {"pagine": out, "totale": round(sum(x["pct"] for x in out) / len(out))}


def claim(conn, player) -> str:
    from engine.simulation import cultivation
    from engine.systems import sects
    v = view(conn, player)
    got = state.get_json(conn, KEY) or {}
    tier = max(1, cultivation.realm_tier(conn, "player", player.id) or 1)
    lines = []
    for pg in v["pagine"]:
        for s in pg["premi"]:
            got.setdefault(pg["key"], []).append(s)
            stones = 100 * tier * (s // 25)
            sects.grant_resource(conn, "pietre_spirituali", stones, player.id)
            lines.append(f"📖 {pg['titolo']} al {s}%: +{stones} pietre.")
            if s == 100:
                t = f"Custode dell'Album — {pg['titolo'].split(' ', 1)[1]}"
                if state.grant_title(conn, t):
                    lines.append(f"✧ Nuovo titolo: «{t}» ✧")
    state.set_json(conn, KEY, got)
    return "\n".join(lines) if lines else "Nessun premio da ritirare: completa le pagine dell'album."


def command(conn, player, arg: str) -> str:
    a = (arg or "").strip().lower()
    if a in ("premi", "ritira", "riscuoti"):
        return claim(conn, player)
    v = view(conn, player)
    lines = [f"📖 ALBUM DEL COLTIVATORE — {v['totale']}% completo"]
    for pg in v["pagine"]:
        lines.append(f"  {pg['titolo']}: {pg['visti']}/{pg['totale']} ({pg['pct']}%)"
                     + (f" — premi da ritirare: {', '.join(str(s) + '%' for s in pg['premi'])}" if pg["premi"] else ""))
    lines.append("'album premi' ritira i premi · nella dashboard: Tesori → Album")
    return "\n".join(lines)
