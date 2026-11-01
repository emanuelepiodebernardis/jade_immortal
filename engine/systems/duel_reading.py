"""
LEGGERE IL NEMICO (Aggiornamento 84) — nel duello si vince anche guardando.

PUNTI DEBOLI — ogni stile ha il suo, e all'inizio non lo conosci. Lo scopri studiandolo: ogni turno c'è una piccola
probabilità, più alta se hai appena difeso o ti sei concentrato (guardi invece di colpire), e un senso divino forte
lo vede subito. Una volta scoperto vale per tutto il duello:
  impetuoso   dopo il colpo pesante resta scoperto: il colpo seguente fa ×1,6
  prudente    la guardia ha un varco: quando è in guardia non ti frena più (anzi, ×1,15)
  subdolo     le finte gli rubano il fiato: dopo una finta il colpo seguente fa ×1,4
  equilibrato il qi gli scorre storto in un meridiano: le tue tecniche fanno ×1,2

LE FINTE — quando raccoglie il qi, un senso divino abbastanza forte (anima ≥ 25 × il suo regno) sente se il qi si
addensa davvero: «è una FINTA, colpiscilo» oppure «arriverà davvero». Senza senso divino, contro il subdolo a volte
noti da solo un indizio (i piedi che non si piantano).

Tutto vive nel dizionario del duello (d["weak"], d["weak_known"], d["opened"], d["read"]): nessuna tabella nuova.
"""

from __future__ import annotations

# stile -> (chiave breve, nome, scoperta, effetto in una riga)
WEAK = {"impetuoso": ("scoperto", "Si scopre dopo la carica",
                      "dopo ogni colpo pesante resta scoperto per un istante", "il colpo dopo la sua carica fa ×1,6"),
        "prudente": ("varco", "Un varco nella guardia",
                     "la sua guardia lascia un varco sul fianco sinistro", "la sua guardia non ti frena più"),
        "subdolo": ("fiato", "Le finte gli rubano il fiato",
                    "ogni finta gli costa il fiato", "il colpo dopo una sua finta fa ×1,4"),
        "equilibrato": ("meridiano", "Un meridiano storto",
                        "il qi gli scorre storto nel meridiano del cuore", "le tue tecniche fanno ×1,2")}


def _sense(conn, player_id: int) -> int:
    try:
        from engine.systems import divine_sense
        return divine_sense._sense(conn, player_id)
    except Exception:                                    # noqa: BLE001
        return 0


def _tier(conn, npc_id: int) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "npc", npc_id) or 1


def init(d: dict) -> None:
    d.setdefault("weak", d.get("style") if d.get("style") in WEAK else "equilibrato")
    d.setdefault("weak_known", False)


def on_turn(conn, player, d: dict, rng) -> list[str]:
    """All'inizio di ogni turno: forse scopri il punto debole; se carica, forse leggi la finta."""
    init(d)
    out: list[str] = []
    sense = _sense(conn, player.id)
    tier = _tier(conn, d["npc"])
    if not d["weak_known"] and d["round"] > 1:
        watched = (d.get("last") or {}).get("mossa") in ("difendi", "concentrati")
        p = 0.12 + (0.25 if watched else 0.0) + min(0.3, sense / (200.0 * tier))
        if sense >= 50 * tier or rng.random() < p:
            d["weak_known"] = True
            w = WEAK.get(d["weak"], WEAK["equilibrato"])
            out.append(f"🔎 Studiandolo, scopri il suo punto debole: {w[2]}. ({w[3]})")
    d["read"] = ""
    if d.get("charge_e"):
        if sense >= 25 * tier:
            d["read"] = "finta" if d.get("feint") else "vera"
            out.append("👁 Il tuo senso divino non sente il qi addensarsi: è una FINTA. Colpiscilo!" if d.get("feint")
                       else "👁 Il tuo senso divino sente il qi addensarsi davvero: il colpo arriverà. Difenditi.")
        elif d.get("feint") and rng.random() < 0.25:
            d["read"] = "indizio"
            out.append("…i suoi piedi però non si piantano a terra. Forse finge?")
    return out


def attack_mult(d: dict, what: str, lines: list[str], opened: str | None) -> float:
    """Il moltiplicatore del tuo colpo dato dal punto debole (se lo conosci). `opened`: come si è scoperto."""
    if not d.get("weak_known"):
        return 1.0
    w = d.get("weak")
    if w == "impetuoso" and opened == "carica":
        m, txt = 1.6, "Colpisci nel varco che lascia dopo la carica!"
    elif w == "subdolo" and opened == "finta":
        m, txt = 1.4, "Senza fiato dopo la finta, non riesce a coprirsi!"
    elif w == "equilibrato" and what == "tecnica":
        m, txt = 1.2, "La tecnica affonda nel suo meridiano storto."
    elif w == "prudente" and d.get("guard_e"):
        m, txt = 1.15 / 0.6, "Trovi il varco nella sua guardia!"         # annulla il ×0,6 della guardia e va oltre
    else:
        return 1.0
    lines.append("  ✧ " + txt)
    return m


def after_enemy(d: dict, charged: bool, feint: bool) -> None:
    """Dopo la sua mossa: si è scoperto?"""
    if feint:
        d["opened"] = "finta"
    elif charged:
        d["opened"] = "carica"


def view(d: dict) -> dict:
    init(d)
    w = WEAK.get(d.get("weak") or "equilibrato", WEAK["equilibrato"])
    return {"noto": bool(d.get("weak_known")), "nome": w[1] if d.get("weak_known") else "",
            "testo": w[3] if d.get("weak_known") else "studialo: difendere o concentrarti aiuta a scoprirlo",
            "lettura": d.get("read", ""),
            "aperto": bool((d.get("weak"), d.get("opened")) in (("impetuoso", "carica"), ("subdolo", "finta")))}
