"""
IL CORPO DEL DHARMA (Aggiornamento 67) — la proiezione gigante del tuo Dao.

Lo spunto viene da Immortal Celestial Fate (i «Dharma Bodies») e dal genere (法相天地: il coltivatore
che fa sorgere alle spalle una figura alta come una montagna). Dal 3° regno puoi RISVEGLIARE il tuo
Corpo del Dharma: prende la forma del tuo Dao più forte (una spada di mille fili per il Dao della Spada,
una fenice per il Fuoco, un gigante di pietra per la Terra…) e la cambia se il tuo Dao cambia.

  · cresce di GRADO senza fine: ogni giorno da solo (un po') e quando lo NUTRI di pietre (molto);
    ogni grado costa il 50% in più del precedente;
  · in battaglia si erge alle tue spalle: attacco in più e un po' meno danni subiti (dentro il
    bilancio dei doni, come tutti gli altri doni).

  dharma                 il pannello
  dharma risveglia       risvegli il Corpo del Dharma (dal 3° regno)
  dharma nutri [pietre]  lo nutri di pietre (tutte quelle che puoi, se non dici quante)
"""

from __future__ import annotations

from engine.systems import state

KEY = "dharma_body"
FORMS = {
    "spada": "la Spada Celeste dai Mille Fili", "sciabola": "il Generale della Sciabola Insanguinata",
    "fuoco": "la Fenice del Fuoco Primordiale", "acqua": "il Drago delle Acque Profonde",
    "terra": "il Gigante di Montagna", "metallo": "il Re dalle Mille Lame", "legno": "l'Albero del Mondo",
    "vento": "il Roc delle Nove Tempeste", "fulmine": "il Signore del Tuono", "luce": "il Buddha di Luce",
    "oscurita": "l'Ombra che Divora le Stelle", "anima": "il Volto dai Mille Occhi", "corpo": "il Titano di Bronzo",
    "pugno": "l'Asura dalle Sei Braccia", "bastone": "il Re Scimmia del Bastone", "massacro": "il Dio della Strage",
    "karma": "il Giudice dalle Due Bilance", "tempo": "il Vecchio della Clessidra", "spazio": "il Viandante del Vuoto",
    "vita_morte": "la Dea dalle Due Facce", "caos": "il Caos Senza Forma", "stelle": "la Costellazione Vivente",
    "sangue": "il Re del Lago di Sangue", "illusione": "lo Specchio dei Mille Sogni",
}
DEFAULT_FORM = "il Gigante d'Oro dai Tre Volti"
AWAKEN_TIER = 3


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _tier(conn) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", 1) or 1


def _best_dao(conn, pid: int = 1) -> str | None:
    from engine.systems import dao_training
    rows = dao_training.trainable_daos(conn, pid)
    return max(rows, key=lambda r: r["comprehension"])["dao_key"] if rows else None


def form(conn) -> str:
    d = get(conn)
    return FORMS.get(d.get("dao") or "", DEFAULT_FORM)


def need(grade: int) -> int:
    return int(100 * 1.5 ** grade)


def awaken(conn, player) -> str:
    from engine.systems import sects
    if get(conn).get("awake"):
        return f"Il tuo Corpo del Dharma è già desto: {form(conn)}."
    if _tier(conn) < AWAKEN_TIER:
        return f"Il Corpo del Dharma si risveglia dal {AWAKEN_TIER}° regno: il tuo Dao è ancora troppo giovane."
    cost = 300 * _tier(conn)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Per risvegliarlo servono {cost} pietre spirituali."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    dao = _best_dao(conn, player.id)
    _save(conn, {"awake": True, "grade": 1, "exp": 0.0, "dao": dao})
    return (f"🗿 Chiudi gli occhi e il tuo Dao prende forma alle tue spalle, grande come una montagna: "
            f"{FORMS.get(dao or '', DEFAULT_FORM)} (−{cost} pietre). Il Corpo del Dharma è desto: grado 1.")


def _gain(conn, d: dict, exp: float) -> list[str]:
    out = []
    d["exp"] = d.get("exp", 0.0) + exp
    while d["exp"] >= need(d["grade"]):
        d["exp"] -= need(d["grade"])
        d["grade"] += 1
        out.append(f"🗿 Il Corpo del Dharma sale al grado {d['grade']}.")
    dao = _best_dao(conn)
    if out and dao and dao != d.get("dao"):
        d["dao"] = dao
        out.append(f"Il tuo Dao è cambiato, e il Dharma con lui: ora è {FORMS.get(dao, DEFAULT_FORM)}.")
    return out


def nourish(conn, player, stones: int | None = None) -> str:
    from engine.systems import sects
    d = get(conn)
    if not d.get("awake"):
        return "Prima risveglialo. ('dharma risveglia')"
    have = sects.get_resource(conn, "pietre_spirituali", player.id)
    amount = have if stones is None else min(have, max(0, stones))
    rate = 5 * _tier(conn)                              # pietre per punto
    if amount < rate:
        return f"Ti servono almeno {rate} pietre per nutrirlo."
    amount -= amount % rate
    sects.grant_resource(conn, "pietre_spirituali", -amount, player.id)
    lines = _gain(conn, d, amount / rate)
    _save(conn, d)
    return (f"Il Corpo del Dharma beve il Qi di {amount} pietre. Grado {d['grade']}, "
            f"{int(d['exp'])}/{need(d['grade'])}.") + ("\n" + "\n".join(lines) if lines else "")


def daily(conn, t: int, rng, player) -> list[str]:
    d = get(conn)
    if not d.get("awake") or player is None:
        return []
    lines = _gain(conn, d, 3 + _tier(conn))
    _save(conn, d)
    return lines


def atk_bonus(conn) -> float:
    d = get(conn)
    return 0.08 * d.get("grade", 0) ** 0.75 if d.get("awake") else 0.0


def combat(conn, fx) -> list[str]:
    d = get(conn)
    if not d.get("awake"):
        return []
    fx.p.atk_mult *= 1.0 + atk_bonus(conn)
    fx.p.prof["taken"] = fx.p.prof.get("taken", 0.0) + min(0.15, 0.01 * d["grade"])
    return [f"🗿 Alle tue spalle si erge {form(conn)} (grado {d['grade']})."]


def menu_section(conn, player):
    from engine.systems.menus import act, bar, section
    from engine.systems import sects
    d = get(conn)
    if not d.get("awake"):
        ok = _tier(conn) >= AWAKEN_TIER
        cost = 300 * _tier(conn)
        return section("Il Corpo del Dharma", [
            "La proiezione del tuo Dao, alta come una montagna: prende la forma del tuo Dao più forte, cresce senza "
            "fine e combatte alle tue spalle."],
            [act(f"Risveglia il Corpo del Dharma ({cost} pietre)", "dharma risveglia",
                 ok and sects.get_resource(conn, "pietre_spirituali", player.id) >= cost,
                 f"dal {AWAKEN_TIER}° regno" if not ok else f"servono {cost} pietre", main=ok)], icon="🗿",
            img="oggetti/dharma")
    pct = 100 * d.get("exp", 0) / need(d["grade"])
    return section(f"Il Corpo del Dharma — grado {d['grade']}", [
        f"Forma: {form(conn)}.",
        f"In battaglia: attacco +{atk_bonus(conn) * 100:.0f}%, danni subiti −{min(15, d['grade'])}%.",
        "Cresce da solo ogni giorno; nutrirlo di pietre lo fa crescere molto più in fretta."],
        [act("Nutrilo con tutte le pietre", "dharma nutri", main=True),
         act("Nutrilo con 1000 pietre", "dharma nutri 1000")],
        [bar("Verso il grado successivo", pct, f"{int(d.get('exp', 0))}/{need(d['grade'])}", tone="rare")], icon="🗿",
        img="oggetti/dharma")


def command(conn, player, arg: str) -> str:
    p = (arg or "").split()
    sub = p[0].lower() if p else ""
    if sub in ("risveglia", "sveglia", "evoca"):
        return awaken(conn, player)
    if sub in ("nutri", "nutrisci", "alimenta"):
        return nourish(conn, player, int(p[1]) if len(p) > 1 and p[1].isdigit() else None)
    from engine.systems import menus
    return menus.render(conn, menu_build(conn, player))


def menu_build(conn, player) -> dict:
    """La scheda «Dharma» della Via: il Corpo del Dharma e i Sigilli ancestrali."""
    from engine.systems.menus import menu
    from engine.systems import ancestral_sigils
    return menu("dharma", "🗿 DHARMA E SIGILLI", ["Il tuo Dao alle tue spalle, e le rune degli antichi nel petto."],
                [menu_section(conn, player)] + ancestral_sigils.menu_sections(conn, player))
