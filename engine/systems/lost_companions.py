"""
I COMPAGNI PERDUTI (Aggiornamento 67) — chi è passato con te dal Varco del Cielo Spezzato.

Lo spunto viene da Immortal Celestial Fate: un gruppo di ragazzi in viaggio viene risucchiato nel Regno
Immortale, il protagonista si risveglia da solo e parte a cercare gli altri. Qui la saga vale per ogni
origine e vive una vita intera:

  · il Trasmigratore viene dalla Terra: una gita di fine anno, {gruppo} = i compagni di classe;
  · le altre origini erano su una carovana di giovani diretti all'esame di una setta.

Sette capitoli (trame in intrigue_data4.py, aperti da soul_arcs come i vasi d'anima), legati al regno:
  1° il ricordo · 2° l'amico servo · 4° la santa · 5° la prigioniera · 7° il caduto · 8° il cacciatore
  · 10° chi aprì il Varco.
Chi ritrovi diventa un FRATELLO GIURATO (lo chiami in battaglia); la santa resta nella sua setta e ti
manda doni; il caduto può tornare indietro, restare tuo complice o cadere per mano tua; il cacciatore,
libero dalla Voce, si unisce a te. Più compagni hai riunito, più facile il finale (ramo «riuniti»).

  compagni            la saga: chi hai ritrovato, chi manca
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "lost_companions"
ROLES = ("amico", "santa", "prigioniera", "caduto", "cacciatore")
ROLE_LABEL = {"amico": "il migliore amico", "santa": "la santa", "prigioniera": "la prigioniera",
              "caduto": "il caduto", "cacciatore": "il cacciatore"}
EARTH_NAMES = {"amico": "Marco Rinaldi", "santa": "Giulia Ferri", "prigioniera": "Sara Conti",
               "caduto": "Davide Moretti", "cacciatore": "Luca Bianchi"}
ARCHETYPE = {"amico": "discepolo", "santa": "discepolo", "prigioniera": "eremita", "caduto": "vagabondo",
             "cacciatore": "anziano"}
GENDER = {"amico": "m", "santa": "f", "prigioniera": "f", "caduto": "m", "cacciatore": "m"}
TRAITS = {"amico": {"loyalty": 95, "courage": 60, "honor": 80}, "santa": {"honor": 90, "pride": 70, "compassion": 80},
          "prigioniera": {"compassion": 85, "courage": 70}, "caduto": {"honor": 15, "ambition": 90, "courage": 85},
          "cacciatore": {"courage": 95, "pride": 80, "loyalty": 70}}
FOUND_OK = {"compagni_amico": ("liberato_vinto", "riscattato", "fuga_insieme"),
            "compagni_santa": ("giuramento_vinto", "protetta", "svelata"),
            "compagni_prigioniera": ("assalto_vinto", "furtivo", "risvegliata"),
            "compagni_caduto": ("fermato_vinto", "redento", "patto"),
            "compagni_cacciatore": ("voce_vinto", "verita")}
PLOT_ROLE = {"compagni_amico": "amico", "compagni_santa": "santa", "compagni_prigioniera": "prigioniera",
             "compagni_caduto": "caduto", "compagni_cacciatore": "cacciatore"}


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _origin(conn) -> str:
    r = conn.execute("SELECT origin FROM character_profiles WHERE character_type='player' LIMIT 1;").fetchone()
    return (r["origin"] if r else None) or "mortale"


def _ensure(conn) -> dict:
    d = get(conn)
    if not d:
        d = {"variant": "terra" if _origin(conn) == "trasmigratore" else "carovana", "npcs": {}, "fate": {}}
    if "names" not in d:                                # i nomi li ricordi da sempre, anche prima di ritrovarli
        if d["variant"] == "terra":
            d["names"] = dict(EARTH_NAMES)
        else:
            from engine.systems import npc_factory
            rng = random.Random(tick_mod.get_tick(conn) + 4242)
            used = {r["name"] for r in conn.execute("SELECT name FROM npcs;")}
            d["names"] = {}
            for r in ROLES:
                nm = npc_factory.unique_name(rng, used, female=GENDER[r] == "f")
                used.add(nm)
                d["names"][r] = nm
        _save(conn, d)
    return d


def _tier(conn) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", 1) or 1


def _alive(conn, nid) -> bool:
    r = conn.execute("SELECT status FROM npcs WHERE id=?;", (nid or -1,)).fetchone()
    return bool(r and r["status"] == "alive")


def npc(conn, player, role: str) -> int:
    """Il compagno (creato la prima volta che serve, al livello giusto per il capitolo)."""
    from engine.systems import npc_factory, pursuers
    d = _ensure(conn)
    nid = d["npcs"].get(role)
    if nid and _alive(conn, nid):
        return nid
    t = tick_mod.get_tick(conn)
    rng = random.Random(t + len(role) * 97)
    tier = max(1, _tier(conn) - (1 if role in ("amico", "prigioniera") else 0))
    kw = {"name": d["names"][role]}
    nid = npc_factory.spawn(conn, rng, archetype=ARCHETYPE[role], location_id=player.location_id, tier=tier,
                            stage=5, traits=TRAITS[role], tick=t, gender=GENDER[role], **kw)
    if role in ("caduto", "cacciatore"):
        pursuers.fit(conn, player.id, nid, "campione", target=1.0 if role == "caduto" else 1.05)
    conn.execute("UPDATE npcs SET description=? WHERE id=?;",
                 (f"Uno di quelli caduti con te dal Varco del Cielo Spezzato: {ROLE_LABEL[role]}.", nid))
    d["npcs"][role] = nid
    _save(conn, d)
    return nid


def names(conn) -> dict:
    d = _ensure(conn)
    out = {}
    for r in ROLES:
        nid = d["npcs"].get(r)
        row = conn.execute("SELECT name FROM npcs WHERE id=?;", (nid or -1,)).fetchone()
        out[r] = row["name"] if row else d["names"].get(r, ROLE_LABEL[r])
    if d["variant"] == "terra":
        out.update({"gruppo": "i tuoi compagni di classe", "viaggio": "la gita di fine anno sulle montagne più alte "
                    "della Terra", "ricordo": "un braccialetto di plastica rossa con una scritta in una lingua che qui "
                    "nessuno sa leggere"})
    else:
        out.update({"gruppo": "i ragazzi della carovana", "viaggio": "la carovana che vi portava all'esame della setta",
                    "ricordo": "una tessera di legno col nome del vostro villaggio, incisa da {amico}".replace(
                        "{amico}", out["amico"])})
    return out


def found(conn) -> list[str]:
    return [r for r, f in (get(conn).get("fate") or {}).items() if f in ("fratello", "alleata", "complice")]


# ---------------------------------------------------------------- l'arco (soul_arcs)

def arc_level(conn):
    if tick_mod.get_tick(conn) // 120 < 5:
        return None                                   # i primi giorni sono tuoi
    return _tier(conn)


def prepare(conn, player, plot) -> bool:
    role = PLOT_ROLE.get(plot)
    if role:
        nid = npc(conn, player, role)
        state.set(conn, f"lc_{role}", str(nid))
        if role in ("amico", "santa", "caduto", "cacciatore"):
            conn.execute("UPDATE npcs SET location_id=? WHERE id=?;", (player.location_id, nid))
    else:
        _ensure(conn)
        if plot == "compagni_varco":
            nid = npc(conn, player, "amico")             # il ricordo è suo: deve avere già un nome
            conn.execute("UPDATE npcs SET location_id=NULL WHERE id=?;", (nid,))   # ma è lontano, a est
    return True


def branches(conn, plot) -> list:
    return ["riuniti"] if len(found(conn)) >= 3 else []


def _sworn(conn, player, nid: int, why: str) -> None:
    from engine.systems import bonds
    try:
        bonds.add_bond(conn, player.id, nid, "sworn", tick_mod.get_tick(conn), reason=why)
    except Exception:                                   # noqa: BLE001
        pass


def _gift(conn, player, eff: dict) -> list[str]:
    from engine.systems import encounters
    t = tick_mod.get_tick(conn)
    return encounters.apply_effects(conn, t, random.Random(t + 717), player, eff, {}) or []


def on_chapter(conn, player, plot, outcome, closed) -> list[str]:
    d = _ensure(conn)
    out: list[str] = []
    nm = names(conn)
    role = PLOT_ROLE.get(plot)
    if role and closed:
        nid = d["npcs"].get(role)
        alive = _alive(conn, nid)
        if role == "santa":
            d["fate"][role] = "alleata"
            out.append(f"✦ {nm['santa']} resta Santa della sua setta, ma ora è tua alleata: ogni tanto ti manderà doni.")
            out += _gift(conn, player, {"prize": _rank(2, ["pillola", "tesoro"])})
        elif role == "caduto":
            if outcome == "patto" and alive:
                d["fate"][role] = "complice"
                _sworn(conn, player, nid, "complice sul sentiero del sangue")
                out.append(f"✦ {nm['caduto']} è il tuo complice: forte, spietato, e tuo.")
            elif alive:
                d["fate"][role] = "fratello"
                conn.execute("UPDATE npcs SET description=? WHERE id=?;",
                             ("Ha lasciato il sentiero del sangue. Porta ancora gli occhi un po' rossi.", nid))
                _sworn(conn, player, nid, "tornato dal sentiero del sangue")
                out.append(f"✦ {nm['caduto']} torna indietro dal sentiero del sangue, e cammina con te.")
            else:
                d["fate"][role] = "morto"
                out.append(f"{nm['caduto']} è morto per tua mano. Il ragazzo di allora, forse, ti ringrazierebbe.")
                state.grant_title(conn, "Colui che Fermò un Amico")
        elif alive:
            d["fate"][role] = "fratello"
            _sworn(conn, player, nid, "ritrovato dopo il Varco")
            out.append(f"✦ {nm[role]} ti ha ritrovato: da oggi è tuo fratello giurato ('chiama {nm[role].split()[0]}').")
            if role == "prigioniera":
                out += _gift(conn, player, {"prize": _rank(2, ["pillola", "essenza"])})
                out.append(f"{nm['prigioniera']} ha imparato l'alchimia dentro il calderone: te ne porta i frutti.")
        else:
            d["fate"][role] = "morto"
            out.append(f"{nm[role]} non ce l'ha fatta.")
    if plot == "compagni_finale" and closed:
        d["fate"]["varco"] = outcome
        n = len(found(conn))
        if outcome == "preso":
            state.grant_title(conn, "Signore del Varco")
            out += _gift(conn, player, {"prize": _rank(1, ["reliquia", "tesoro"]), "lifespan_years": 80})
            out.append("Il Varco batte nel tuo petto. Alcuni dei tuoi compagni non ti guardano più negli occhi.")
        else:
            state.grant_title(conn, "Colui che Riunì i Compagni" if n >= 4 else "Custode del Varco Chiuso")
            out += _gift(conn, player, {"prize": _rank(1, ["reliquia", "tesoro", "manuale"]), "lifespan_years": 40 + 10 * n})
            if d["variant"] == "terra":
                out.append("Il Varco è chiuso. Prima che si spegnesse, qualcuno di voi ha visto per un istante una "
                           "strada d'asfalto sotto la pioggia. Nessuno ha detto niente. Siete rimasti.")
            else:
                out.append("Il Varco è chiuso. Ora siete in tanti, e il Regno è casa vostra.")
    _save(conn, d)
    return out


def _rank(rank: int, kinds: list) -> dict:
    return {"rank": rank, "kinds": kinds, "n": 1, "stones": False}


# ---------------------------------------------------------------- doni della santa

def daily(conn, t: int, rng, player) -> list[str]:
    d = get(conn)
    if not d or (d.get("fate") or {}).get("santa") != "alleata" or player is None:
        return []
    day = t // 120
    if day % 30 != 17:
        return []
    nm = names(conn)["santa"]
    return [f"🕊 Un discepolo vestito di bianco ti consegna un dono da parte di {nm}, senza dire una parola."] + \
        _gift(conn, player, {"prize": _rank(3, ["pillola", "tesoro"])})


# ---------------------------------------------------------------- pannello

def menu_section(conn, player):
    from engine.systems.menus import section
    from engine.systems import soul_arcs
    d = _ensure(conn)
    nm = names(conn)
    lines = [f"Dal Varco del Cielo Spezzato siete caduti in sei: tu e {nm['gruppo']}."]
    lab = {"fratello": "ritrovato · fratello giurato", "alleata": "ritrovata · alleata dalla sua setta",
           "complice": "ritrovato · complice", "morto": "perduto per sempre"}
    for r in ROLES:
        f = (d.get("fate") or {}).get(r)
        lines.append(f"{'✦' if f in ('fratello', 'alleata', 'complice') else '·'} {nm[r]} ({ROLE_LABEL[r]}): "
                     + (lab.get(f) or "disperso"))
    lines.append(soul_arcs.status_line(conn, "compagni"))
    return section("I compagni perduti", lines, icon="🌀")


def command(conn, player, arg: str = "") -> str:
    from engine.systems import menus
    return menus.render(conn, menu_build(conn, player))


def menu_build(conn, player) -> dict:
    from engine.systems.menus import menu
    return menu("compagni", "🌀 I COMPAGNI PERDUTI", ["Chi è caduto con te dal Varco, e dove l'ha portato la vita."],
                [menu_section(conn, player)])
