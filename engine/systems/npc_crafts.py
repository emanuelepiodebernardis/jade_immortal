"""
I MESTIERI DEGLI ALTRI (Aggiornamento 78) — chi divori ti lascia anche ciò che sapeva fare.

Ogni persona del mondo ha un'arte che conosce (alchimia, talismani, forgia, formazioni, addomesticamento) a un
certo livello. Il mestiere nasce dall'archetipo, dal regno e da un seme stabile: nessuna colonna nuova nel
database, lo stesso NPC sa sempre le stesse cose. 'examine <nome>' lo mostra.

Con l'Abisso Divoratore, assorbire qualcuno ti dà anche l'ESPERIENZA del suo mestiere:
  · se conosci già quell'arte, cresci verso il suo livello: mai oltre (un apprendista non ti insegna nulla
    se sei già maestro, un gran maestro sì);
  · se non la conosci, ne ricavi FRAMMENTI: quando bastano, l'arte è tua (poi la pratichi con 'arti <nome>');
  · le bestie lasciano un po' della loro natura: frammenti di Addomesticamento.
Il guadagno scala con la freschezza del corpo e con un'integrazione pulita.

Aggiungere un mestiere a un archetipo = una riga in CRAFTS.
"""

from __future__ import annotations

import random

# archetipo → [(arte, peso)], probabilità di non avere alcun mestiere
CRAFTS = {
    "mercante": ([("alchimia", 3), ("forgia", 2), ("talismani", 2), ("formazioni", 1)], 0.1),
    "anziano": ([("alchimia", 3), ("formazioni", 3), ("talismani", 2)], 0.1),
    "patriarca": ([("formazioni", 3), ("talismani", 2), ("alchimia", 2), ("forgia", 1)], 0.0),
    "eremita": ([("alchimia", 3), ("formazioni", 2), ("talismani", 2), ("domatore", 1)], 0.15),
    "guardia": ([("forgia", 3), ("formazioni", 1), ("talismani", 1)], 0.35),
    "discepolo": ([("alchimia", 2), ("talismani", 2), ("forgia", 2), ("formazioni", 1), ("domatore", 1)], 0.35),
    "vagabondo": ([("domatore", 3), ("talismani", 2), ("alchimia", 1), ("forgia", 1)], 0.4),
    "cacciatore": ([("domatore", 4), ("forgia", 1), ("alchimia", 1)], 0.2),
}
DEFAULT = ([("alchimia", 1), ("talismani", 1), ("forgia", 1), ("formazioni", 1), ("domatore", 1)], 0.5)
SECOND = 0.3                   # probabilità di un secondo mestiere (a livello più basso)
SHARE = 0.25                   # quota dell'esperienza altrui che assorbi (per un corpo fresco e pulito)
LEARN_AT = 8                   # frammenti per imparare un'arte che non conosci
TITLE = {1: "apprendista", 3: "artigiano", 5: "esperto", 7: "maestro", 10: "gran maestro", 14: "leggenda"}


def _title(lv: int) -> str:
    t = "apprendista"
    for k, v in TITLE.items():
        if lv >= k:
            t = v
    return t


def of_npc(conn, npc_id: int) -> list[tuple[str, int]]:
    """I mestieri di un NPC: [(arte, livello)], il principale per primo. Stabili nel tempo."""
    from engine.simulation import cultivation
    row = conn.execute("SELECT archetype, kind FROM npcs WHERE id=?;", (npc_id,)).fetchone()
    if not row or (row["kind"] or "human") != "human":
        return []
    pool, none_p = CRAFTS.get(row["archetype"] or "", DEFAULT)
    r = random.Random(npc_id * 9973 + 17)
    if r.random() < none_p:
        return []
    tier = cultivation.realm_tier(conn, "npc", npc_id) or 1
    keys = [k for k, _w in pool]
    weights = [w for _k, w in pool]
    main = r.choices(keys, weights)[0]
    lv = max(1, int(round(tier * 1.4 + r.randint(0, 4) + (2 if row["archetype"] in ("anziano", "patriarca") else 0))))
    out = [(main, lv)]
    if r.random() < SECOND and len(keys) > 1:
        other = r.choices([k for k in keys if k != main], [w for k, w in pool if k != main])[0]
        out.append((other, max(1, int(lv * 0.6))))
    return out


def describe_npc(conn, npc_id: int) -> str:
    from engine.systems import professions
    cr = of_npc(conn, npc_id)
    if not cr:
        return ""
    return "Mestiere: " + ", ".join(f"{professions.PROFESSIONS[k]} — {_title(lv)} (liv. {lv})" for k, lv in cr)


def _frags(conn) -> dict:
    from engine.systems import state
    return state.get_json(conn, "craft_fragments", {}) or {}


def _learn_or_grow(conn, pid: int, key: str, their_lv: int, amount: float) -> str:
    from engine.systems import professions, state
    name = professions.PROFESSIONS[key]
    if not professions.has(conn, key, pid):
        f = _frags(conn)
        f[key] = round(f.get(key, 0) + max(1.0, amount), 2)
        if f[key] >= LEARN_AT:
            start = int(f.pop(key))
            state.set_json(conn, "craft_fragments", f)
            lv = professions.add_xp(conn, pid, start, key)
            return (f"⚒ I frammenti si ricompongono: conosci l'arte {name} (liv. {lv}). "
                    f"Praticala con 'arti {key}'.")
        state.set_json(conn, "craft_fragments", f)
        return f"⚒ Frammenti di {name}: {int(f[key])}/{LEARN_AT}."
    ceiling = professions.xp_for_level(their_lv)
    have = professions.xp(conn, pid, key)
    if have >= ceiling:
        return f"⚒ Sapeva di {name} meno di te: non c'è nulla da imparare."
    gain = max(1, min(int(amount), ceiling - have))
    before = professions.level(conn, pid, key)
    after = professions.add_xp(conn, pid, gain, key)
    up = f" — sali al livello {after}!" if after > before else ""
    return f"⚒ Assorbi la sua esperienza di {name}: +{gain}{up}"


def on_absorb(conn, pid: int, npc_id: int, kind: str, freshness: float, clean: bool) -> list[str]:
    """Chiamata dall'assorbimento: l'esperienza dei mestieri del bersaglio passa a te."""
    from engine.systems import professions
    q = freshness * (1.0 if clean else 0.5)
    if kind == "beast":
        from engine.simulation import cultivation
        tier = cultivation.realm_tier(conn, "npc", npc_id) or 1
        return [_learn_or_grow(conn, pid, "domatore", 2 + tier, (1 + tier) * q)]
    out = []
    for key, lv in of_npc(conn, npc_id):
        amount = professions.xp_for_level(lv) * SHARE * q + 1
        out.append(_learn_or_grow(conn, pid, key, lv, amount))
    return out


def describe(conn, pid: int = 1) -> str:
    from engine.systems import professions
    f = _frags(conn)
    if not f:
        return ""
    return "Frammenti di mestieri assorbiti: " + ", ".join(
        f"{professions.PROFESSIONS[k]} {int(v)}/{LEARN_AT}" for k, v in sorted(f.items()))
