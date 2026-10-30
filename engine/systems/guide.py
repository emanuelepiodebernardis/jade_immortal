"""
L'INIZIO GUIDATO E IL CODEX (Aggiornamento 70).

PRIMI PASSI — sette tappe per la prima ora, una alla volta, in cima a «Cosa fare ora». Ogni tappa ha
il suo comando e un piccolo premio (pietre) quando la completi. Finite le sette, la guida sparisce.
Si possono saltare con 'guida salta'.

CODEX — una pagina per ogni sistema del gioco (coltivazione, Dao, sangue, meridiani, equipaggiamento…).
La dashboard la mostra la prima volta che apri quella scheda; poi resta consultabile in Storia → Codex.
Per aggiungere una voce basta una riga in CODEX.
"""

from __future__ import annotations

from engine.systems import state

KEY = "guide"

# (chiave, titolo, perché, comando, premio in pietre)
STEPS = [
    ("attributi", "Assegna i tuoi punti attributo", "Forza, vitalità, agilità… decidono che coltivatore sarai.",
     "attributi", 50),
    ("allenati", "Allenati una volta", "Il qi cresce allenandosi: è il primo passo di ogni Via.", "train", 50),
    ("viaggia", "Visita un altro luogo", "Il mondo è grande: dalla mappa scegli una meta e parti.", "mappa", 80),
    ("setta", "Entra in una setta", "Una setta ti dà maestri, missioni, risorse e protezione.", "join", 120),
    ("equip", "Indossa un pezzo d'equipaggiamento", "Sei posti sul corpo: forgia il primo pezzo.", "equip", 120),
    ("duello", "Vinci un duello", "Scegli un avversario alla tua portata: 'duello <nome>'.", "duello", 150),
    ("sfonda", "Il primo sfondamento", "Quando la barra del regno è piena, sfonda: tutto si moltiplica.",
     "breakthrough", 300),
]


def get(conn) -> dict:
    d = state.get_json(conn, KEY) or {}
    d.setdefault("done", [])
    d.setdefault("off", False)
    d.setdefault("flags", {})
    return d


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def flag(conn, name: str) -> None:
    """Un evento che la guida non sa misurare da sola (es. un duello vinto)."""
    d = get(conn)
    if not d["flags"].get(name):
        d["flags"][name] = True
        _save(conn, d)


def _is_done(conn, player, key: str, d: dict) -> bool:
    try:
        if key == "attributi":
            from engine.systems import attributes
            return sum((attributes.allocated(conn) or {}).values()) > 0
        if key == "allenati":
            from engine.simulation import cultivation
            rec = cultivation.get_record(conn, "player", player.id)
            return bool(rec and ((rec["qi_level"] or 0) > 0 or (rec["progress"] or 0) > 0 or (rec["stage"] or 1) > 1))
        if key == "viaggia":
            return len(set(state.get_json(conn, "world_codex_luoghi", []) or [])) >= 2
        if key == "setta":
            from engine.systems import sects
            return sects.get_membership(conn, player.id) is not None
        if key == "equip":
            from engine.systems import gear
            return bool(gear.get(conn)["eq"])
        if key == "duello":
            return bool(d["flags"].get("duello"))
        if key == "sfonda":
            from engine.simulation import cultivation
            return (cultivation.realm_tier(conn, "player", player.id) or 1) > d.get("tier0", 1)
    except Exception:                                  # noqa: BLE001
        return False
    return False


def current(conn, player) -> tuple[int, tuple] | None:
    d = get(conn)
    if d["off"]:
        return None
    if "tier0" not in d:
        from engine.simulation import cultivation
        d["tier0"] = cultivation.realm_tier(conn, "player", player.id) or 1
        _save(conn, d)
    for i, st in enumerate(STEPS):
        if st[0] not in d["done"]:
            return i, st
    return None


def check(conn, player) -> list[str]:
    """Dopo ogni comando: le tappe completate danno il premio e la guida passa alla successiva."""
    d = get(conn)
    if d["off"]:
        return []
    out = []
    if "tier0" not in d:
        current(conn, player)
        d = get(conn)
    for key, title, _why, _cmd, prize in STEPS:
        if key in d["done"]:
            continue
        if not _is_done(conn, player, key, d):
            continue
        d["done"].append(key)
        from engine.systems import sects
        sects.grant_resource(conn, "pietre_spirituali", prize, player.id)
        out.append(f"🧭 Primi passi: «{title}» — fatto! (+{prize} pietre)")
    if out:
        if len(d["done"]) >= len(STEPS):
            d["off"] = True
            out.append("🧭 Hai completato i primi passi. Da qui in poi la Via è tua: segui le mete e «Cosa fare ora».")
        _save(conn, d)
    return out


def _live_cmd(conn, player, key: str, cmd: str, why: str) -> tuple[str, str]:
    """(Agg. 71) Il comando giusto ADESSO: lo sfondamento solo quando la barra è piena, altrimenti allenati."""
    if key == "sfonda":
        try:
            from engine.simulation import cultivation
            rec = cultivation.get_record(conn, "player", player.id)
            ready = rec and (rec["stage"] or 1) >= cultivation.STAGES_PER_REALM and (rec["progress"] or 0) >= 1.0
        except Exception:                              # noqa: BLE001
            ready = False
        if not ready:
            return "train", "Allenati finché il regno non è al decimo strato con la barra piena: poi sfonda."
    return cmd, why


def attention_item(conn, player) -> dict | None:
    cur = current(conn, player)
    if not cur:
        return None
    i, (key, title, why, cmd, prize) = cur
    cmd, why = _live_cmd(conn, player, key, cmd, why)
    return {"icon": "🧭", "title": f"Primi passi {i + 1}/{len(STEPS)}: {title}", "why": f"{why} (+{prize} pietre)",
            "cmd": cmd, "palace": "oggi", "tab": "", "hot": True, "prio": -1}


def command(conn, player, arg: str) -> str:
    a = (arg or "").strip().lower()
    d = get(conn)
    if a in ("salta", "off", "basta"):
        d["off"] = True
        _save(conn, d)
        return "🧭 Guida chiusa. (Riaprila con 'guida riprendi'.)"
    if a in ("riprendi", "on"):
        d["off"] = False
        _save(conn, d)
    cur = current(conn, player)
    lines = ["🧭 PRIMI PASSI"]
    for i, (key, title, why, cmd, prize) in enumerate(STEPS):
        mark = "✔" if key in d["done"] else ("➤" if cur and cur[0] == i else "·")
        lines.append(f"  {mark} {title} — '{cmd}' (+{prize} pietre)")
    lines.append("'guida salta' per chiuderla.")
    return "\n".join(lines)


# ------------------------------------------------------------------ CODEX
# chiave (scheda o sistema) -> (titolo, testo)
CODEX = {
    "coltivazione": ("La coltivazione", "Il qi si accumula allenandoti ('train') e meditando. Ogni regno ha dieci strati; "
                     "a strato dieci, con la barra piena, tenti lo SFONDAMENTO: se riesce, tutta la tua forza si "
                     "moltiplica (×1,6 a regno). Il regno è la scala principale del gioco."),
    "corpo": ("Il corpo", "Il corpo si tempra con la sofferenza: allenamento fisico, bestie divorate, elisir. Dà vitalità "
              "e difesa, e apre le costituzioni leggendarie."),
    "sangue": ("Il sangue", "Un lignaggio antico (drago, fenice, qilin…) può risvegliarsi nelle tue vene. Più è puro, più "
               "doni dà; al massimo puoi TRASFORMARTI in combattimento."),
    "attributi": ("Gli attributi", "FOR, VIT, AGI, INT, SAG, FRT. A ogni livello guadagni punti da assegnare: decidono "
                  "attacco, vita, schivata, velocità di coltivazione e comprensione."),
    "tecniche": ("Le tecniche", "Manuali e arti segrete: nel duello sono le carte. Costano qi o spirito e si ricaricano. "
                 "Ogni tecnica ha un ELEMENTO: contro l'elemento giusto è superefficace."),
    "profondi": ("I Dao", "Comprendere un Dao (fuoco, spada, tempo…) amplifica la tua forza fino a oltre ×2 e apre "
                 "poteri. Si comprendono meditando, combattendo e con le essenze."),
    "spiriti": ("Gli Spiriti del Dao", "Quando un Dao matura prende forma: uno spirito che combatte al tuo fianco e "
                "allena il suo Dao mentre riposi."),
    "anime": ("Le anime", "Anelli, pagode, perle: oggetti che custodiscono anime antiche. Ti parlano, ti insegnano, a volte "
              "ti tentano."),
    "meridiani": ("I meridiani", "Dodici canali principali e otto straordinari. Aprirli costa pietre; temprarli rafforza "
                  "attacco, difesa, vitalità e coltivazione."),
    "dharma": ("Dharma e sigilli", "Dal terzo regno il tuo Dao può prendere forma alle tue spalle: il Corpo del Dharma. "
               "I sigilli ancestrali (sei casate) si incastonano nel petto e danno bonus, con set da 2 e 4."),
    "forza": ("La forza", "Da dove viene la tua potenza: regno, crescita personale (compressa), Dao. Qui vedi anche quanto "
              "vali rispetto al tuo regno e cosa conviene potenziare."),
    "zaino": ("Tesori ed equipaggiamento", "Pillole, essenze, nuclei e manuali si usano dallo zaino. L'equipaggiamento ha "
              "sei posti (veste, corona, amuleto, anello, stivali, talismano): regno, rarità e set. "
              "Si trova tra i tesori o si forgia con le pietre."),
    "mappa": ("La mappa", "Clicca un luogo per viaggiare a tappe: lungo la strada si raccoglie, si incontra, si cade in "
              "agguato. I luoghi più scuri sono più pericolosi e più ricchi. La frontiera si allarga col tuo regno."),
    "setta": ("La setta", "Missioni, contributo, gradi, maestri, politica interna. Salire di grado apre tecniche e risorse; "
              "tradirla ha un prezzo."),
    "duello": ("Il duello", "A turni, come un gioco di carte: colpisci, tecniche, difendi, concentrati, pillola, fuggi. "
               "Leggi l'INTENTO del nemico sotto il suo ritratto: se carica, difenditi; se si cura, colpisci forte. "
               "Gli ★ élite e i ♛ boss restano al tuo passo; i boss hanno tre fasi."),
    "pietre": ("Le pietre spirituali", "La moneta del mondo dei coltivatori: forgia, meridiani, aste, ricette. Puoi anche "
               "assorbirle per il qi ('pietre assorbi')."),
    "tribolazione": ("La tribolazione", "Ai grandi sfondamenti il Cielo ti mette alla prova con i fulmini. Prepararsi "
                     "(pillole, formazioni, difesa) cambia tutto; sopravvivere lascia doni."),
}


def codex(conn=None) -> list[dict]:
    return [{"key": k, "titolo": t, "testo": x} for k, (t, x) in CODEX.items()]
