"""
IL BILANCIO DELLA POTENZA — tante fonti, una forza sola.

Il personaggio prende forza da decine di sistemi: regno, crescita del corpo, tecniche, Dao, sangue,
corpo leggendario e i suoi poteri, Corpo Supremo, spiriti del Dao, attributi, tribolazioni, sigilli…
Prima si moltiplicavano tutti tra loro senza freno (un salvataggio arrivava a 68.000 di potenza
contro 2.700 degli avversari del suo regno). Ora:

  · il REGNO resta la scala principale (×1,6 a regno);
  · la crescita personale (corpo, tecniche, attributi, tribolazioni) si comprime in modo logaritmico
    (com'era già);
  · i DAO amplificano con un tetto morbido (DAO_AMP_MAX, in calibration.py): crescono sempre, ma
    sempre più piano;
  · in combattimento i DONI (sangue, corpo, poteri, Corpo Supremo, radici, classe, elementi…) si
    sommano in un solo moltiplicatore con un tetto morbido (GIFTS_ATK_CAP): ognuno conta, nessuno
    da solo spezza il gioco. Anche colpi extra, resurrezioni, schivata e riduzione dei danni hanno
    un tetto;
  · ogni fonte resta visibile nella schermata «Da dove viene la tua forza» ('forza').
"""

from __future__ import annotations

import math

from engine.systems import state

LAST_KEY = "last_fight_sources"


def soft(m: float, cap: float) -> float:
    """Tetto morbido: quasi lineare per valori piccoli, mai oltre `cap` (sopra 1)."""
    if m <= 1.0 or cap <= 1.0:
        return m
    lc = math.log(cap)
    return math.exp(lc * math.tanh(math.log(m) / lc))


def dao_amp(dao_power: float, vessel: float) -> float:
    """L'amplificatore dei Dao: 1 senza Dao, ~1,3 col vaso del regno pieno, poi sempre più piano
    verso DAO_AMP_MAX."""
    from engine.systems import calibration as cal
    r = max(0.0, dao_power) / max(1.0, vessel)
    x = math.log2(1.0 + r)
    span = cal.DAO_AMP_MAX - 1.0
    return 1.0 + span * (1.0 - 1.0 / (1.0 + 0.4 * x / span))   # all'inizio come prima (0,4 per raddoppio)


# ---------------------------------------------------------------- in combattimento

class Tracker:
    """Registra quanto ogni fonte moltiplica l'attacco del giocatore mentre si prepara uno scontro."""

    def __init__(self, fx):
        self.fx = fx
        self.sources: dict[str, float] = {}
        self._last = fx.p.atk_mult

    def mark(self, name: str) -> None:
        cur = self.fx.p.atk_mult
        if self._last > 0 and abs(cur / self._last - 1.0) > 1e-6:
            self.sources[name] = self.sources.get(name, 1.0) * (cur / self._last)
        self._last = cur

    def finish(self, conn) -> None:
        """Applica i tetti e ricorda le fonti dell'ultimo scontro (per la schermata 'forza')."""
        from engine.systems import calibration as cal
        fx = self.fx
        raw = fx.p.atk_mult
        fx.p.atk_mult = soft(raw, cal.GIFTS_ATK_CAP)
        pr = fx.p.prof
        pr["extra_strikes"] = min(int(pr.get("extra_strikes", 0)), cal.MAX_EXTRA_STRIKES)
        fx.p.lethal_saves = min(int(fx.p.lethal_saves), cal.MAX_LETHAL_SAVES)
        pr["taken"] = min(float(pr.get("taken", 0.0)), cal.MAX_DAMAGE_REDUCTION)
        pr["evade"] = min(float(pr.get("evade", 0.0)), cal.MAX_EVADE)
        pr["crit"] = min(float(pr.get("crit", 0.0)), cal.MAX_CRIT)
        try:
            state.set_json(conn, LAST_KEY, {
                "sources": {k: round(v, 3) for k, v in self.sources.items()},
                "raw": round(raw, 3), "final": round(fx.p.atk_mult, 3),
                "strikes": pr["extra_strikes"], "saves": fx.p.lethal_saves,
                "taken": round(pr["taken"], 3), "evade": round(pr["evade"], 3), "crit": round(pr["crit"], 3)})
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- la schermata

_LABEL = {"elementi": "Elementi e scontro tra elementi", "radici": "Radici spirituali", "classe": "Classe e formazioni",
          "sangue": "Lignaggi di sangue", "prodigi": "Prodigi", "tribolazione_celeste": "Doni della tribolazione celeste",
          "anello e altri": "Anello, elementi celesti, retaggio, gu, guerra delle anime, svolte",
          "corpo": "Corpo leggendario, poteri e Corpo Supremo"}


def breakdown(conn, player) -> dict:
    """Da dove viene la forza: le fonti del rating e i doni dell'ultimo scontro."""
    import math as m
    from engine.simulation import combat as cb, cultivation as cv
    from engine.systems import character, dao_training, guild, tribulation, attributes, deep_dao, power, calibration
    pid = player.id
    tier = cv.realm_tier(conn, "player", pid) or 1
    rf = cb._realm_factor(conn, "player", pid)
    caf = character.affinity_factor(conn, "player", pid, "combat")
    daf = 1.0 + 0.5 * m.log2(dao_training.combat_dao_factor(conn, "player", pid))
    tf = guild.technique_combat_factor(conn, "player", pid)
    bb = tribulation.boon_bonuses(conn, pid)
    am = attributes.combat_mults(conn).get("attack", 1.0)
    raw_growth = caf * daf * tf * bb["attack_mult"] * am
    growth = cb.compress(raw_growth)
    amp = cb.dao_amplifier(dao_training.dao_power(conn, "player", pid), tier)
    seal = deep_dao.seal_mult(conn)
    rows = [
        ("Regno", rf, f"{tier}° regno: la scala principale (×{calibration_step():.1f} a regno)"),
        ("Crescita personale", growth, f"corpo, tecniche (×{tf:.1f}), tribolazioni (×{bb['attack_mult']:.1f}), "
                                       f"attributi (×{am:.2f}), Dao da combattimento (×{daf:.2f}): "
                                       f"×{_n(raw_growth)} grezzi, compressi a ×{growth:.2f}"),
        ("Dao", amp, f"amplificatore dei Dao (tetto ×{calibration.DAO_AMP_MAX:.1f})"),
        ("Sigilli della Sfida", seal, "i sigilli spezzati del Cielo"),
    ]
    last = state.get_json(conn, LAST_KEY, None)
    gifts = []
    if last:
        for k, v in sorted(last["sources"].items(), key=lambda kv: -kv[1]):
            gifts.append((_LABEL.get(k, k), v))
    return {"rating": power.combat_rating(conn, "player", pid), "fonti": rows, "doni": gifts,
            "doni_grezzi": last["raw"] if last else None, "doni_finali": last["final"] if last else None,
            "tetto": calibration.GIFTS_ATK_CAP, "ultimo": last}


def _n(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")


def calibration_step() -> float:
    from engine.simulation import combat as cb
    return cb.REALM_STEP


def menu_build(conn, player) -> dict:
    from engine.systems.menus import bar, menu, section, act
    b = breakdown(conn, player)
    secs = []
    total = 1.0
    for _nm, v, _d in b["fonti"]:
        total *= v
    lines = [f"Potenza complessiva: {_n(b['rating'])} · le fonti moltiplicano ×{_n(total)}"]
    bars = []
    lt = math.log(max(1.0001, total))
    for n, v, d in b["fonti"]:
        share = 100 * math.log(max(1.0, v)) / lt if lt > 0 else 0
        bars.append(bar(f"{n} ×{v:.2f}", share, d, tone="rare" if n == "Regno" else ""))
    secs.append(section("Da dove viene la tua forza", lines + [
        "Ogni barra è la quota della tua potenza che viene da quella fonte. Il regno è la scala principale; "
        "il resto cresce sempre, ma con rendimenti decrescenti."], [act("Potenza e classe (dettaglio)", "rating")],
        bars, icon="⚖"))
    if b["doni"]:
        lt2 = math.log(max(1.0001, b["doni_grezzi"]))
        gb = [bar(f"{n} ×{v:.2f}", 100 * math.log(max(1.0, v)) / lt2 if lt2 > 0 else 0, "") for n, v in b["doni"]]
        u = b["ultimo"]
        secs.append(section("I doni in combattimento (ultimo scontro)", [
            f"Tutti insieme: ×{b['doni_grezzi']:.2f}, con il tetto ×{b['doni_finali']:.2f} (massimo ×{b['tetto']:.1f}).",
            f"Colpi in più {u['strikes']} · resurrezioni {u['saves']} · danni subiti −{int(100 * u['taken'])}% · "
            f"schivata {int(100 * u['evade'])}% · critici +{int(100 * u['crit'])}%"], [], gb, icon="⚔"))
    else:
        secs.append(section("I doni in combattimento", ["Combatti una volta: qui vedrai quanto pesa ogni dono "
                                                         "(sangue, corpo, radici, elementi…)."], icon="⚔"))
    return menu("forza", "⚖ DA DOVE VIENE LA TUA FORZA",
                ["Tante fonti, una forza sola: cosa conta davvero, e quanto."], secs)
