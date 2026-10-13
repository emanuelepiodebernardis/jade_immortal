"""
LA RISONANZA CORPO-SANGUE — il corpo leggendario e il lignaggio si riconoscono.

Ogni corpo leggendario ha bestie e elementi AFFINI (il Corpo del Drago Vero e ogni sangue di drago, il
Nirvana della Fenice e la Fenice, l'Osso Supremo e il Kunpeng, la Luna Grande e il Tiangou che la divora…).
Quando nelle tue vene scorre un lignaggio affine, corpo e sangue RISUONANO:

  · piena (la bestia è affine)          il sangue si concentra +50% più in fretta, combatte più forte,
                                         e il dono del corpo scatta più spesso
  · parziale (solo un elemento affine)  metà di tutto questo
  · ogni stadio di risveglio del corpo rafforza la risonanza (+15% a stadio);
  · le EVOLUZIONI del sangue affine riescono più spesso (+15%) e, quando il sangue evolve in una
    bestia affine, il corpo si RISVEGLIA di uno stadio.
"""

from __future__ import annotations

# corpo -> (famiglie affini, elementi affini)
AFFINITY: dict[str, tuple[set, set]] = {
    "caos": ({"hundun"}, {"caos"}),
    "vene_yin": ({"leviatano", "kun", "tartaruga nera", "jiao"}, {"acqua"}),
    "ossa_spada": ({"tigre bianca", "tigre"}, {"metallo"}),
    "tuono": ({"drago", "aquila", "drago azzurro"}, {"fulmine"}),
    "ombra": ({"demone", "qiongqi", "tiangou"}, {"oscurita"}),
    "giada": ({"qilin", "bai ze", "silvano"}, {"luce", "legno"}),
    "vuoto": ({"kunpeng", "kun"}, {"spazio"}),
    "drago": ({"drago", "drago azzurro", "drago giallo", "drago della torcia", "jiao"}, set()),
    "occhi": ({"bai ze", "drago della torcia"}, {"luce"}),
    "veleno": ({"serpente", "xiangliu"}, set()),
    "spezzati": ({"taowu", "cinghiale"}, set()),                # lo scarto ostinato che non si piega
    "santo_antico": ({"gigante", "taowu", "taotie"}, {"terra"}),
    "osso_supremo": ({"kunpeng", "suanni"}, set()),            # le Arti Preziose del Kunpeng e del Suanni
    "doppie_pupille": ({"nove code", "volpe"}, {"illusione"}),
    "dao_innato": ({"hundun", "bai ze"}, set()),
    "nove_yang": ({"uccello vermiglio", "fenice", "suanni"}, {"fuoco"}),
    "luna": ({"tiangou", "nove code"}, {"acqua"}),
    "sole": ({"uccello vermiglio", "drago della torcia"}, {"fuoco", "luce"}),
    "asura": ({"tigre bianca", "qiongqi", "taotie"}, {"massacro", "sangue"}),
    "immortale": ({"silvano", "tartaruga nera", "tartaruga", "gru"}, set()),
    "fenice_nirvana": ({"fenice", "uccello vermiglio", "gru"}, {"fuoco"}),
    "anima_celeste": ({"bai ze", "kun"}, {"anima"}),
}


def _body(conn):
    from engine.systems import constitutions
    return constitutions.get(conn)


def level(body_key: str | None, ln: dict) -> float:
    """1.0 risonanza piena (bestia affine, anche come tratto minore la metà), 0.5 parziale (elemento), 0."""
    if not body_key or body_key not in AFFINITY:
        return 0.0
    fams, els = AFFINITY[body_key]
    if fams & set(ln.get("families") or []):
        return 1.0
    if fams & set(ln.get("minor") or []):
        return 0.6
    if els & set(ln.get("elements") or []):
        return 0.5
    return 0.0


def _keys(c: dict | None) -> list[str]:
    """Il tuo corpo e quelli che hai assorbito (anche loro hanno affinità di sangue)."""
    return ([c["key"]] + list(c.get("absorbed") or [])) if c else []


def strength(conn, ln: dict) -> float:
    """La risonanza di un lignaggio col tuo corpo, già rafforzata dagli stadi di risveglio (0 = nessuna)."""
    c = _body(conn)
    if not c:
        return 0.0
    lv = max(level(k, ln) * (1.0 if i == 0 else 0.6) for i, k in enumerate(_keys(c)))
    if not lv:
        return 0.0
    st = int(c.get("stage", 0))
    return lv * (0.5 if st == 0 else 1.0 + 0.15 * (st - 1))


def best(conn) -> tuple[str | None, dict | None, float]:
    """(chiave, lignaggio, forza) del lignaggio che risuona di più."""
    from engine.systems import bloodlines as B
    top = (None, None, 0.0)
    for k, ln in B.all_lines(conn).items():
        s = strength(conn, ln)
        if s > top[2]:
            top = (k, ln, s)
    return top


def gain_mult(conn, ln: dict) -> float:
    return 1.0 + 0.5 * strength(conn, ln)


def combat_mult(conn, ln: dict) -> float:
    return 1.0 + 0.2 * strength(conn, ln)


def body_proc_mult(conn) -> float:
    """Il dono del corpo scatta più spesso se un lignaggio risuona."""
    return 1.0 + 0.25 * best(conn)[2]


def on_evolved(conn, ln: dict, target: str) -> list[str]:
    from engine.systems import constitutions
    c = _body(conn)
    if not c or not any(target in AFFINITY.get(k, (set(), set()))[0] for k in _keys(c)):
        return []
    return constitutions.awaken(conn, f"il sangue è diventato {target}, la bestia del tuo corpo")


def affine_names(body_key: str) -> list[str]:
    from engine.systems import bloodlines as B
    fams, els = AFFINITY.get(body_key, (set(), set()))
    return sorted(B._fam(f)[0] for f in fams) + sorted(B.EL_ADJ.get(e, e) for e in els)


def label(conn, ln: dict) -> str:
    """Una riga per il menu del sangue ('' se non risuona)."""
    from engine.systems import constitutions
    c = _body(conn)
    s = strength(conn, ln)
    if not c or not s:
        return ""
    lv = max(level(k, ln) for k in _keys(c))
    kind = "piena" if lv >= 1 else "parziale"
    return (f"🫀 Risonanza {kind} col corpo «{constitutions.display_name(c)}»: concentrazione +{int(50 * s)}%, "
            f"forza +{int(20 * s)}%, evoluzione +15%")


def summary(conn) -> dict | None:
    """Per la dashboard e il pannello del corpo."""
    c = _body(conn)
    if not c:
        return None
    k, ln, s = best(conn)
    aff = list(dict.fromkeys(x for k in _keys(c) for x in affine_names(k)))
    return {"affini": aff, "lignaggio": ln["name"] if ln else None, "forza": round(s, 2)}
