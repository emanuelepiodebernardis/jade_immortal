"""
L'INTRODUZIONE GRADUALE (Aggiornamento 80) — ogni sistema si presenta quando diventa utile, una volta sola.

Invece di trovarsi davanti centinaia di comandi, il giocatore scopre le cose al momento giusto: le fusioni quando
due Dao sono abbastanza avanti, la bottega la prima volta che incontra un maestro, le Prove del Cielo quando nessuno
gli tiene più testa. Un paragrafo breve, con i due o tre comandi che servono; al massimo una presentazione per
comando. 'novita' rilegge quelle già viste; 'novita no' le spegne.

Aggiungere una presentazione = una riga in INTROS (chiave, titolo, testo, condizione).
"""

from __future__ import annotations

from engine.systems import state

KEY = "intro_seen"
OFF = "intro_off"


def _day(conn) -> int:
    from engine.core import tick
    return tick.get_tick(conn) // 120


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def _loc_type(conn, player) -> str:
    from engine.core import entities
    loc = entities.get_location(conn, player.location_id)
    return loc.location_type if loc else ""


def _c_obiettivi(conn, p):
    return _day(conn) >= 3


def _c_vie(conn, p):
    from engine.systems import dao_laws, sects
    return _day(conn) >= 5 and sects.get_resource(conn, "pietre_spirituali", p.id) >= dao_laws.learn_cost(conn)


def _c_fusioni(conn, p):
    from engine.systems import dao_laws
    return any(not dao_laws.recipe_status(conn, k, p.id)["missing"] and not dao_laws._has(conn, k, p.id)
               for k in dao_laws.FUSED if dao_laws.is_light(k))


def _c_reperti(conn, p):
    from engine.systems import dao_insight
    return _loc_type(conn, p) in dao_insight.RELIC_PLACES and dao_insight.can_search(conn, p.location_id)


def _c_bottega(conn, p):
    from engine.core import entities
    from engine.systems import npc_crafts
    return _day(conn) >= 2 and any(npc_crafts.of_npc(conn, n.id) and npc_crafts.of_npc(conn, n.id)[0][1] >= 4
                                   for n in entities.npcs_in_location(conn, p.location_id))


def _c_assisti(conn, p):
    return _day(conn) >= 7 and _loc_type(conn, p) in ("sect", "city")


def _c_prove(conn, p):
    above = state.get_json(conn, "prodigies_above", []) or []
    return _day(conn) >= 20 and _tier(conn, p.id) >= 2 and not above


def _c_albero(conn, p):
    from engine.systems import dao_laws
    return any(dao_laws._has(conn, k, p.id) for k in list(dao_laws.BY_KEY) + list(dao_laws.FUSED))


def _c_laboratorio(conn, p):
    from engine.systems import professions
    return professions.best_level(conn, p.id) >= 5 and _loc_type(conn, p) == "city"


def _c_rivali(conn, p):
    return bool(state.get_json(conn, "prodigies_above", []) or [])


INTROS = [
    ("obiettivi", "Un obiettivo", "Hai tante strade davanti. Scegline una e il gioco ti mostrerà i passi: 'obiettivo "
     "spada 100', 'obiettivo tempesta', 'obiettivo alchimia 5'. Il pilota automatico ci lavorerà per te. Se non sai "
     "dove trovare qualcosa: 'cerca <parola>'.", _c_obiettivi),
    ("vie", "Le vie nuove", "Oltre ai Dao che conosci ce ne sono altri 34: ghiaccio, veleno, suono, scudo, pugnale, "
     "alchimia, longevità… Ognuno ha un vantaggio e un costo. 'vie' li elenca; 'anteprima ghiaccio' ti dice cosa ti "
     "darebbe senza spendere; 'comprehend ghiaccio' lo apre.", _c_vie),
    ("fusioni", "La prima fusione", "Due dei tuoi Dao sono abbastanza avanti per fondersi in uno nuovo. 'fusione' "
     "mostra le ricette, 'anteprima <ricetta>' cosa ti darebbe. Una fusione allenata va sempre più a fondo e alla fine "
     "ti mostra un Dao più alto. 'albero' le mostra tutte.", _c_fusioni),
    ("reperti", "I reperti dei maestri", "Luoghi come questo custodiscono stele, rotoli, spade nella roccia lasciati da "
     "maestri del passato. 'reperti' li cerca: approfondiscono un tuo Dao, ti fanno intravedere vie nuove, ti danno "
     "intuizioni sulle fusioni. Una volta per luogo ogni trenta giorni.", _c_reperti),
    ("bottega", "Chi sa fare qualcosa", "Qui c'è qualcuno che è un maestro nella sua arte ('examine <nome>' per "
     "vederlo). 'bottega <nome>': una giornata al suo fianco ti insegna il mestiere. 'commissiona <nome>': ti fa un "
     "oggetto per pietre.", _c_bottega),
    ("assisti", "Guardare per imparare", "Intorno a te c'è chi si allena. 'assisti': ti fermi a guardare il più bravo, e "
     "a volte capisci qualcosa del suo Dao. Anche perdere un duello insegna.", _c_assisti),
    ("albero", "L'albero dei Dao", "Ora le tue vie cominciano a ramificarsi. 'albero' mostra tutti i Dao e come si "
     "collegano: quali puoi aprire, quali fondere, quali Dao alti ti aspettano in fondo.", _c_albero),
    ("rivali", "Qualcuno ti ha superato", "I prodigi della tua generazione crescono con le tue stesse regole: aprono vie, "
     "fondono Dao, trovano reperti. Uno di loro ora è più forte di te ('prodigi'). Se resti indietro a lungo, verrà a "
     "sfidarti davanti a tutti.", _c_rivali),
    ("prove", "Le Prove del Cielo", "Ormai pochi ti tengono testa. Il Cielo offre tre prove contro avversari più forti "
     "di te: 'prova_cielo 1', '2', '3' (Bronzo, Argento, Oro). Perdere non uccide; vincere paga bene.", _c_prove),
    ("laboratorio", "Un laboratorio tuo", "La tua arte è abbastanza matura per farne un mestiere. In città puoi aprire un "
     "laboratorio ('laboratorio apri'): rende pietre ogni giorno, di più con i discepoli della tua setta.",
     _c_laboratorio),
]


def seen(conn) -> list[str]:
    return state.get_json(conn, KEY, []) or []


def check(conn, player) -> list[str]:
    """Dopo ogni comando: al massimo una presentazione nuova."""
    if player is None or player.status != "alive" or state.flag(conn, OFF, False) or _day(conn) < 1:
        return []
    done = seen(conn)
    for key, title, text, cond in INTROS:
        if key in done:
            continue
        try:
            ok = cond(conn, player)
        except Exception:                                # noqa: BLE001 — mai bloccare un comando per questo
            ok = False
        if ok:
            state.set_json(conn, KEY, done + [key])
            return [f"✦ NOVITÀ — {title} ✦\n{text}"]
    return []


def command(conn, player, arg: str) -> str:
    a = (arg or "").strip().lower()
    if a in ("no", "off", "spegni"):
        state.set(conn, OFF, "1")
        return "Le presentazioni delle novità sono spente ('novita si' per riaccenderle)."
    if a in ("si", "sì", "on", "accendi"):
        state.delete(conn, OFF)
        return "Le presentazioni delle novità sono accese."
    done = seen(conn)
    lines = [f"✦ LE NOVITÀ CHE HAI SCOPERTO ({len(done)}/{len(INTROS)}) ✦"]
    for key, title, text, _c in INTROS:
        if key in done:
            lines.append(f"• {title}: {text}")
    if len(done) < len(INTROS):
        lines.append(f"Ne restano {len(INTROS) - len(done)} da scoprire, quando verrà il momento.")
    return "\n".join(lines)
