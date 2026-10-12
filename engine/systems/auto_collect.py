"""
RACCOLTA AUTOMATICA — meno tasti: il bottino si raccoglie e le essenze si assorbono da sole.

Due interruttori (entrambi ACCESI di base):
  · RACCOLTA AUTOMATICA   quando abbatti qualcuno, la sua eredità (manuali, essenze, pietre, arma)
                          finisce subito nello zaino, senza 'loot';
  · ASSORBIMENTO AUTOMATICO  essenze di sangue e del Dao, nuclei, manuali e incensi dell'anima si usano
                          da soli appena li ottieni (sono sempre un guadagno). Le pillole restano tue,
                          da usare quando vuoi.
Il riepilogo è di una riga ("Raccogli 4 oggetti · assorbi 3 essenze, 1 manuale"), più i passaggi di grado.

  raccogli                    raccogli tutto e assorbi tutto ciò che si assorbe, in un colpo
  autoraccolta on|off         raccolta automatica del bottino
  autoassorbi on|off          assorbimento automatico di essenze, nuclei, manuali, incensi
"""

from __future__ import annotations

from engine.systems import state

LOOT_KEY, ABSORB_KEY = "auto_loot", "auto_absorb"
_ABSORB_TYPES = ("essenza", "nucleo", "manuale")


def on(conn, key: str) -> bool:
    return state.flag(conn, key, True)


def _absorbable(conn, pid) -> list:
    from engine.systems import items
    return [r for r in items.player_inventory(conn, pid)
            if r["item_type"] in _ABSORB_TYPES or r["name"].startswith("Incenso")]


def _highlights(lines: list[str]) -> list[str]:
    """Dai risultati lunghi tiene solo ciò che conta: gradi nuovi, tecniche nuove, mutazioni."""
    keys = ("✦", "sale al grado", "Apprendi", "Nuovo titolo", "si tempra", "TECNICA INNATA", "RIVOLTA", "Nasce")
    out = []
    for raw in lines:
        body = raw.strip().lstrip("·").strip()
        body = body.split(": ", 1)[1] if ": " in body and not body.startswith(("✦", "🩸")) else body
        for ln in body.split("; "):
            ln = ln.strip()
            ln = ln if ln.endswith((".", "!", "»", "✦")) else ln + "."
            if any(k in ln for k in keys) and ln not in out:
                out.append(ln)
    return out[:6]


def absorb_all(conn, player, quiet: bool = True) -> list[str]:
    """Usa tutto ciò che si assorbe (essenze, nuclei, manuali, incensi). Ritorna un riepilogo breve."""
    from engine.cli import loop
    rows = _absorbable(conn, player.id)
    if not rows:
        return []
    counts: dict[str, int] = {}
    detail: list[str] = []
    for r in rows:
        word = "incensi" if r["name"].startswith("Incenso") else {"essenza": "essenze", "nucleo": "nuclei",
                                                                     "manuale": "manuali"}[r["item_type"]]
        counts[word] = counts.get(word, 0) + r["quantity"]
        txt = loop.cmd_use_many(conn, player, frag=r["name"], what=r["name"])
        detail += txt.splitlines()[1:]
    sing = {"essenze": "essenza", "nuclei": "nucleo", "manuali": "manuale", "incensi": "incenso"}
    head = "🩸 Assorbi " + ", ".join(f"{n} {sing[w] if n == 1 else w}" for w, n in counts.items()) + "."
    return [head] + ([f"   {h}" for h in _highlights(detail)] if quiet else detail)


def loot_here(conn, player) -> list[str]:
    from engine.systems import loot
    from engine.cli import loop
    drops = loot.drops_in_location(conn, player.location_id)
    if not drops:
        return []
    names = [d["name"] for d in drops]
    txt = loop.cmd_loot(conn, player, "")
    weapon = [ln.strip() for ln in txt.splitlines() if "Impugni" in ln]
    return ["✋ Raccogli: " + ", ".join(names[:5]) + (f" e altri {len(names) - 5}" if len(names) > 5 else "") + "."] + weapon


def after_kill(conn, player) -> list[str]:
    from engine.core import entities
    p = entities.get_player(conn, player.id)
    out = []
    if on(conn, LOOT_KEY):
        out += loot_here(conn, p)
    if on(conn, ABSORB_KEY):
        out += absorb_all(conn, p)
    return out


def daily(conn, t: int, rng, player) -> list[str]:
    """All'alba assorbe ciò che è arrivato nello zaino da altre vie (doni, premi, campioni risparmiati)."""
    if not on(conn, ABSORB_KEY):
        return []
    return absorb_all(conn, player)


def collect_everything(conn, player) -> str:
    out = loot_here(conn, player) + absorb_all(conn, player)
    return "\n".join(out) if out else "Non c'è nulla da raccogliere né da assorbire."


def toggle(conn, key: str, arg: str, label: str) -> str:
    a = arg.strip().lower()
    val = (not on(conn, key)) if a not in ("on", "si", "sì", "off", "no") else a in ("on", "si", "sì")
    state.set(conn, key, "1" if val else "0")
    return f"{label}: {'ACCESA' if val else 'SPENTA'}."
