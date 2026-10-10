"""
STORIA PERSONALE per origine + OBIETTIVI.

Ogni origine ha un arco in 4 capitoli. Un capitolo si apre quando la sua condizione
è soddisfatta (giorni vissuti, regno raggiunto, un personaggio della storia abbattuto,
una bandierina posata da una scelta precedente…) e si presenta come una SCENA A
SCELTA (stesso motore degli incontri). Le conseguenze sono meccaniche e restano nel DB.

Il comando 'goals' mostra il capitolo in corso e i traguardi vicini: risponde alla
domanda "e adesso cosa faccio?".
"""

from __future__ import annotations

import sqlite3

from engine.core import entities, tick as tick_mod
from engine.systems import state

CH_KEY = "story_chapter"
FLAGS_KEY = "story_flags"
NPCS_KEY = "story_npcs"
LIFE_START_KEY = "life_start_tick"


# ============================================================
# Archi narrativi
# ============================================================

ARCS: dict[str, dict] = {
    "mortale": {"title": "Il villaggio di cenere", "chapters": [
        {"goal": "Sopravvivi al tuo primo giorno da coltivatore.",
         "cond": {"day_min": 1},
         "scene": {"title": "Il profugo", "text": (
             "Un profugo coperto di cenere ti riconosce e cade in ginocchio. «Il villaggio… "
             "non c'è più. I Predoni del Lupo Grigio. Li guida {npc}». Il tuo villaggio natale.")
             , "choices": [
                 {"label": "Giuri vendetta",
                  "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "capo",
                                        "hops": 3, "traits": {"honor": 10, "compassion": 5}},
                              "outlaw": 150, "crime": "ha raso al suolo un villaggio",
                              "flags": ["vendetta"],
                              "text": "Stringi i pugni fino a far sanguinare i palmi."}},
                 {"label": "Prima i sopravvissuti: li aiuti a mettersi in salvo",
                  "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "capo",
                                        "hops": 3, "traits": {"honor": 10, "compassion": 5}},
                              "outlaw": 150, "crime": "ha raso al suolo un villaggio",
                              "karma": 30, "stones": -10, "flags": ["soccorso"],
                              "text": "Il sangue può aspettare. I vivi no."}}]}},
        {"goal": "Trova e abbatti {capo}, il capo dei predoni ('bounties', 'hunt {capo}').",
         "cond": {"npc_dead": "capo"},
         "scene": {"title": "Il covo dei predoni", "text": (
             "Il capo dei predoni è caduto. Nel suo covo trovi le ricchezze strappate al tuo "
             "villaggio e a molti altri."), "choices": [
                 {"label": "Restituisci tutto ai sopravvissuti",
                  "effects": {"karma": 50, "fame": 12, "flags": ["restituito"]}},
                 {"label": "Tieni il bottino: ti servirà per diventare più forte",
                  "effects": {"stones": 150, "karma": -15}}]}},
        {"goal": "Raggiungi il terzo regno di coltivazione.",
         "cond": {"tier_min": 3},
         "scene": {"title": "Ricostruire", "text": (
             "I sopravvissuti hanno trovato una valle sicura. Ti chiedono di aiutarli a "
             "ricostruire: servono pietre spirituali per le formazioni di protezione."), "choices": [
                 {"label": "Doni 150 pietre per le formazioni",
                  "effects": {"stones": -150, "fame": 15, "karma": 40, "flags": ["ricostruito"]}},
                 {"label": "Prometti di tornare quando sarai più forte",
                  "effects": {"text": "Annuiscono. Hanno imparato ad aspettare."}}]}},
        {"goal": "Raggiungi il quarto regno di coltivazione.",
         "cond": {"tier_min": 4},
         "scene": {"title": "Il villaggio rinato", "text": (
             "Torni nella valle: dove c'era cenere ora ci sono case, campi, bambini che corrono. "
             "Ti chiamano per nome. Hanno eretto una stele in tuo onore."), "choices": [
                 {"label": "Ti inchini davanti alla stele",
                  "effects": {"title": "Figlio della Cenere", "cultivation_progress": 0.5,
                              "aff_cultivation": 5, "karma": 30}}]}},
    ]},
    "clan": {"title": "Il peso del nome", "chapters": [
        {"goal": "Sopravvivi al tuo primo giorno lontano dal clan.",
         "cond": {"day_min": 1},
         "scene": {"title": "Il guanto di sfida", "text": (
             "{npc}, erede del clan rivale, ti getta ai piedi un guanto: «Tuo nonno ha umiliato "
             "il mio. Oggi il debito si salda»."), "choices": [
                 {"label": "Accetti la sfida",
                  "effects": {"spawn": {"archetype": "discepolo", "tier_offset": 0, "role": "erede",
                                        "traits": {"pride": 90}},
                              "bond": "rival", "bond_reason": "faida tra clan"},
                  "command": "attack {npc}"},
                 {"label": "Rifiuti: non combatti le guerre dei tuoi avi",
                  "effects": {"spawn": {"archetype": "discepolo", "tier_offset": 0, "role": "erede",
                                        "traits": {"pride": 90}},
                              "bond": "rival", "bond_reason": "l'hai snobbato", "karma": 15,
                              "text": "{npc} ride forte, perché tutti sentano. Non finisce qui."}}]}},
        {"goal": "Raggiungi il secondo regno di coltivazione.",
         "cond": {"tier_min": 2},
         "scene": {"title": "Il tributo", "text": (
             "Un anziano del tuo clan ti raggiunge: «Il clan ti ha cresciuto. È tempo che "
             "contribuisci: ottanta pietre, e la biblioteca ti aprirà le sue porte»."), "choices": [
                 {"label": "Paghi il tributo",
                  "effects": {"stones": -80, "learn_technique": {
                      "name": "Arte Segreta del Clan", "magnitude": 0.08, "tech_key": "story:clan"}}},
                 {"label": "Rifiuti: la tua strada è tua",
                  "effects": {"fame": 5, "aff_combat": 2, "flags": ["libero"]}}]}},
        {"goal": "Fatti un nome: raggiungi il terzo regno.",
         "cond": {"tier_min": 3},
         "scene": {"title": "Il sicario", "text": (
             "Di notte, un'ombra entra dalla finestra: {npc}, sicario del clan rivale. "
             "La lama è già sguainata."), "choices": [
                 {"label": "Combatti",
                  "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "sicario"}},
                  "command": "attack {npc}"},
                 {"label": "Lo disarmi a parole e lo costringi a confessare",
                  "check": {"stat": "anima", "dc": 75},
                  "success": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "sicario"},
                              "fame": 15, "npc_leaves": True, "flags": ["confessione"],
                              "text": "Confessa tutto. La faida del clan rivale diventa uno scandalo."},
                  "failure": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "sicario"},
                              "command": "attack {npc}"}}]}},
        {"goal": "Raggiungi il quarto regno di coltivazione.",
         "cond": {"tier_min": 4},
         "scene": {"title": "Il consiglio del clan", "text": (
             "Il consiglio del clan ti convoca. Gli anziani si alzano quando entri: ti nominano "
             "erede designato."), "choices": [
                 {"label": "Accetti l'onore",
                  "effects": {"title": "Erede del Clan", "stones": 300, "fame": 20}},
                 {"label": "Rinunci: il nome lo costruirai da solo",
                  "effects": {"title": "Colui che Rinunciò al Nome", "aff_cultivation": 4,
                              "karma": 30}}]}},
    ]},
    "genio": {"title": "L'invidia del Cielo", "chapters": [
        {"goal": "Sopravvivi al tuo primo giorno da coltivatore.",
         "cond": {"day_min": 1},
         "scene": {"title": "Lo sguardo del vecchio", "text": (
             "Un vecchio vagabondo, {npc}, ti osserva meditare. «Radici così… non le vedevo da "
             "trecento anni. Vuoi imparare davvero, ragazzo?»"), "choices": [
                 {"label": "Gli chiedi di diventare il tuo maestro",
                  "effects": {"spawn": {"archetype": "eremita", "tier_offset": 2, "role": "maestro"},
                              "relation": 60, "bond": "master",
                              "bond_reason": "ha riconosciuto il tuo talento"}},
                 {"label": "Rifiuti: preferisci trovare la tua strada",
                  "effects": {"spawn": {"archetype": "eremita", "tier_offset": 2, "role": "maestro"},
                              "relation": 25, "aff_cultivation": 2,
                              "text": "{npc} sorride. «Allora la troverai. Forse»."}}]}},
        {"goal": "Raggiungi il secondo regno di coltivazione.",
         "cond": {"tier_min": 2},
         "scene": {"title": "L'invidioso", "text": (
             "{npc}, un coltivatore più anziano, ti aspetta al varco: «Un moccioso che brucia le "
             "tappe? Qualcuno deve rimetterti al tuo posto»."), "choices": [
                 {"label": "Lo affronti",
                  "effects": {"spawn": {"archetype": "discepolo", "tier_offset": 1, "role": "invidioso",
                                        "traits": {"pride": 85}}},
                  "command": "attack {npc}"},
                 {"label": "Lo ignori e passi oltre",
                  "effects": {"spawn": {"archetype": "discepolo", "tier_offset": 1, "role": "invidioso",
                                        "traits": {"pride": 85}},
                              "bond": "rival", "bond_reason": "invidia il tuo talento", "karma": 10}}]}},
        {"goal": "Raggiungi il terzo regno di coltivazione.",
         "cond": {"tier_min": 3},
         "scene": {"title": "Il Cielo ti guarda", "text": (
             "Il cielo si oscura sopra di te soltanto. Un fulmine sottile, quasi un avvertimento, "
             "scende a cercarti. Il Cielo invidia i geni."), "choices": [
                 {"label": "Lo affronti a viso aperto",
                  "check": {"stat": "corpo", "dc": 82},
                  "success": {"dao_key": "fulmine", "dao_gain": 10, "title": "Fulminato dal Cielo"},
                  "failure": {"injury": 6, "dao_key": "fulmine", "dao_gain": 3}},
                 {"label": "Nascondi il tuo talento e lasci che passi",
                  "check": {"stat": "anima", "dc": 72},
                  "success": {"aff_soul": 3, "text": "Il Cielo distoglie lo sguardo. Per ora."},
                  "failure": {"injury": 3}}]}},
        {"goal": "Raggiungi il quinto regno di coltivazione.",
         "cond": {"tier_min": 5},
         "scene": {"title": "Oltre l'invidia", "text": (
             "Ti accorgi che non temi più il cielo che si oscura. Chi ti invidiava è rimasto "
             "indietro; chi ti guidava ti guarda con orgoglio."), "choices": [
                 {"label": "Prosegui", "effects": {"title": "Genio che Sfidò l'Invidia",
                                                   "aff_cultivation": 5,
                                                   "cultivation_progress": 0.5}}]}},
    ]},
    "reincarnato": {"title": "Due anime", "chapters": [
        {"goal": "Sopravvivi al tuo primo giorno in questo corpo.",
         "cond": {"day_min": 1},
         "scene": {"title": "Echi", "text": (
             "Nel dormiveglia vedi un'altra vita: una spada, una montagna, un nome che non è il "
             "tuo. Al risveglio le mani sanno cose che tu non hai mai imparato."), "choices": [
                 {"label": "Ti lasci guidare dai ricordi",
                  "effects": {"dao_key": "random", "dao_gain": 6, "aff_soul": -2,
                              "flags": ["ricordi"]}},
                 {"label": "Li respingi: questa vita è tua",
                  "effects": {"aff_soul": 2}}]}},
        {"goal": "Raggiungi il secondo regno di coltivazione.",
         "cond": {"tier_min": 2},
         "scene": {"title": "L'altra voce", "text": (
             "Durante una meditazione l'altra anima parla, chiara: «Questo corpo era destinato "
             "a me. Fatti da parte»."), "choices": [
                 {"label": "La sopprimi",
                  "check": {"stat": "anima", "dc": 78},
                  "success": {"aff_soul": 4, "title": "Padrone di Sé"},
                  "failure": {"injury": 4, "aff_soul": -2}},
                 {"label": "Le offri di fondervi in una sola anima",
                  "effects": {"grow_soul": 5, "aff_cultivation": 3, "flags": ["fusione"],
                              "text": "Due fiumi diventano uno. Più profondo."}}]}},
        {"goal": "Raggiungi il terzo regno di coltivazione.",
         "cond": {"tier_min": 3},
         "scene": {"title": "La tomba di chi eri", "text": (
             "I ricordi ti guidano a una tomba dimenticata. Sulla lapide, il nome che sognavi. "
             "La tua vita precedente riposa qui."), "choices": [
                 {"label": "Apri la tomba e riprendi ciò che era tuo",
                  "effects": {"stones": 200, "learn_technique": {
                      "name": "Tecnica della Vita Precedente", "magnitude": 0.12,
                      "tech_key": "story:vita_precedente"}}},
                 {"label": "La lasci sigillata: i morti riposino",
                  "effects": {"karma": 40, "aff_soul": 3}}]}},
        {"goal": "Raggiungi il quarto regno di coltivazione.",
         "cond": {"tier_min": 4},
         "scene": {"title": "Una sola strada", "text": (
             "Non sogni più l'altra vita. O forse è che, finalmente, la stai vivendo tutta."),
             "choices": [{"label": "Prosegui",
                          "effects": {"title": "Colui che Ricorda Due Vite", "grow_soul": 5}}]}},
    ]},
    "erede": {"title": "L'eredità contesa", "chapters": [
        {"goal": "Sopravvivi al tuo primo giorno da erede.",
         "cond": {"day_min": 1},
         "scene": {"title": "Chi bussa alla porta", "text": (
             "{npc}, adepto di un culto che venera l'immortale tuo predecessore, ti trova. "
             "«L'eredità non appartiene a un ragazzo. Consegnala»."), "choices": [
                 {"label": "Combatti",
                  "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "cultista"}},
                  "command": "attack {npc}"},
                 {"label": "Lo depisti con un falso indizio",
                  "check": {"stat": "istinto", "dc": 64},
                  "success": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "cultista"},
                              "bond": "nemesis", "bond_reason": "brama la tua eredità"},
                  "failure": {"spawn": {"archetype": "vagabondo", "tier_offset": 1, "role": "cultista"},
                              "command": "attack {npc}"}}]}},
        {"goal": "Raggiungi il terzo regno: il sigillo dell'eredità si allenterà.",
         "cond": {"tier_min": 3},
         "scene": {"title": "Il sigillo", "text": (
             "Il sigillo dell'eredità, dentro di te, si incrina. Puoi spezzarlo, o scioglierlo "
             "comprendendo chi l'ha posto."), "choices": [
                 {"label": "Lo spezzi con la forza",
                  "check": {"stat": "corpo", "dc": 82},
                  "success": {"learn_technique": {"name": "Eredità dell'Immortale", "magnitude": 0.15,
                                                  "tech_key": "story:eredita"}},
                  "failure": {"injury": 5, "learn_technique": {
                      "name": "Frammento dell'Eredità", "magnitude": 0.07,
                      "tech_key": "story:eredita_frammento"}}},
                 {"label": "Lo sciogli comprendendolo",
                  "check": {"stat": "coltivazione", "dc": 78},
                  "success": {"learn_technique": {"name": "Eredità dell'Immortale", "magnitude": 0.15,
                                                  "tech_key": "story:eredita"}, "aff_cultivation": 2},
                  "failure": {"text": "Non ancora. Il sigillo resiste, paziente.",
                              "learn_technique": {"name": "Frammento dell'Eredità", "magnitude": 0.07,
                                                  "tech_key": "story:eredita_frammento"}}}]}},
        {"goal": "Raggiungi il quarto regno di coltivazione.",
         "cond": {"tier_min": 4},
         "scene": {"title": "Il vero discepolo", "text": (
             "Un anziano, {npc}, si presenta: era il discepolo diretto dell'immortale. «Non voglio "
             "l'eredità. Voglio sapere se ne sei degno»."), "choices": [
                 {"label": "Gli offri di studiarla insieme",
                  "effects": {"spawn": {"archetype": "anziano", "tier_offset": 2, "role": "discepolo_vero"},
                              "relation": 65, "karma": 40,
                              "text": "(Potresti chiedergli di farti da maestro: 'disciple {npc}')"}},
                 {"label": "Gli rispondi che l'eredità è tua e basta",
                  "effects": {"spawn": {"archetype": "anziano", "tier_offset": 2, "role": "discepolo_vero"},
                              "bond": "rival", "bond_reason": "contende l'eredità"}}]}},
        {"goal": "Raggiungi il quinto regno di coltivazione.",
         "cond": {"tier_min": 5},
         "scene": {"title": "Degno", "text": (
             "Nel sonno l'immortale ti appare per un istante. Non dice nulla. Annuisce soltanto."),
             "choices": [{"label": "Prosegui",
                          "effects": {"title": "Erede dell'Immortale",
                                      "dao_key": "spada", "dao_gain": 10}}]}},
    ]},
    "divoratore": {"title": "La fame dell'Abisso", "chapters": [
        {"goal": "Sopravvivi al tuo primo giorno.",
         "cond": {"day_min": 1},
         "scene": {"title": "Il Purificatore", "text": (
             "{npc}, Purificatore della Setta del Loto Bianco, annusa l'aria e si volta verso di te. "
             "«Abisso. Lo sento da qui»."), "choices": [
                 {"label": "Lo affronti prima che dia l'allarme",
                  "effects": {"spawn": {"archetype": "guardia", "tier_offset": 1, "role": "purificatore"}},
                  "command": "attack {npc}"},
                 {"label": "Ti confondi tra la folla",
                  "check": {"stat": "istinto", "dc": 62},
                  "success": {"spawn": {"archetype": "guardia", "tier_offset": 1, "role": "purificatore"},
                              "bond": "nemesis", "bond_reason": "ha giurato di purificarti",
                              "npc_leaves": True},
                  "failure": {"spawn": {"archetype": "guardia", "tier_offset": 1, "role": "purificatore"},
                              "command": "attack {npc}"}}]}},
        {"goal": "Raggiungi il secondo regno di coltivazione.",
         "cond": {"tier_min": 2},
         "scene": {"title": "La voce dell'Abisso", "text": (
             "Per la prima volta l'Abisso ti parla con parole: «Non sono una maledizione. Sono "
             "ciò che resta di un Dao che il Cielo ha cancellato»."), "choices": [
                 {"label": "Gli chiedi chi fosse",
                  "effects": {"dao_key": "destino", "dao_gain": 5, "flags": ["verita_abisso"]}},
                 {"label": "Lo zittisci",
                  "effects": {"residue": -10, "aff_soul": 2}}]}},
        {"goal": "Raggiungi il terzo regno di coltivazione.",
         "cond": {"tier_min": 3},
         "scene": {"title": "Il giudizio del Loto Bianco", "text": (
             "La Setta del Loto Bianco dichiara pubblicamente la caccia al portatore dell'Abisso. "
             "Il tuo nome non lo conoscono ancora. Il tuo volto, forse."), "choices": [
                 {"label": "Ti presenti a volto scoperto e accetti il loro giudizio",
                  "check": {"stat": "karma", "dc": 70},
                  "success": {"suspicion": -100, "fame": 15, "title": "Giudicato e Assolto"},
                  "failure": {"injury": 5, "suspicion": 40}},
                 {"label": "Rispondi seminando il terrore",
                  "effects": {"infamy": 30, "grow_aura": 5, "karma": -40}}]}},
        {"goal": "Raggiungi il quinto regno di coltivazione.",
         "cond": {"tier_min": 5},
         "scene": {"title": "Padrone della fame", "text": (
             "La fame non ti comanda più. La scegli tu, quando servirti di lei."),
             "choices": [{"label": "Prosegui",
                          "effects": {"title": "Signore dell'Abisso", "grow_soul": 6}}]}},
    ]},
}


# ============================================================
# Stato
# ============================================================

def chapter(conn) -> int:
    return state.get_int(conn, CH_KEY, 0)


def flags(conn) -> list[str]:
    return list(state.get_json(conn, FLAGS_KEY, []) or [])


def set_flag(conn, fl: str) -> None:
    cur = flags(conn)
    if fl not in cur:
        cur.append(fl)
        state.set_json(conn, FLAGS_KEY, cur)


def remember_npc(conn, role: str, npc_id: int) -> None:
    d = state.get_json(conn, NPCS_KEY, {}) or {}
    d[role] = npc_id
    state.set_json(conn, NPCS_KEY, d)


def story_npc(conn, role: str) -> sqlite3.Row | None:
    d = state.get_json(conn, NPCS_KEY, {}) or {}
    nid = d.get(role)
    if not nid:
        return None
    return conn.execute("SELECT id, name, status, location_id FROM npcs WHERE id=?;", (nid,)).fetchone()


def life_start(conn) -> int:
    return state.get_int(conn, LIFE_START_KEY, 0)


def _origin(conn, player_id) -> str | None:
    from engine.systems import character
    p = character.get_profile(conn, "player", player_id)
    return p["origin"] if p else None


def arc_for(conn, player_id: int = 1) -> dict | None:
    return ARCS.get(_origin(conn, player_id) or "")


# ============================================================
# Condizioni e avanzamento
# ============================================================

def _cond_met(conn, player, cond: dict) -> bool:
    from engine.simulation import cultivation
    from engine.systems import training, reputation, sects
    t = tick_mod.get_tick(conn)
    if "day_min" in cond:
        days = (t - life_start(conn)) // training.DAY_TICKS
        if days < cond["day_min"]:
            return False
    if "tier_min" in cond and (cultivation.realm_tier(conn, "player", player.id) or 1) < cond["tier_min"]:
        return False
    if "fame_min" in cond and reputation.get(conn, player.id)["fame"] < cond["fame_min"]:
        return False
    if cond.get("in_sect") and not sects.get_membership(conn, player.id):
        return False
    if "flag" in cond and cond["flag"] not in flags(conn):
        return False
    if "npc_dead" in cond:
        n = story_npc(conn, cond["npc_dead"])
        if n is None or n["status"] == "alive":
            return False
    return True


def maybe_advance(conn: sqlite3.Connection, player: entities.Player) -> str | None:
    """Se il prossimo capitolo è pronto (e non c'è un'altra scena aperta), lo apre."""
    from engine.systems import encounters
    arc = arc_for(conn, player.id)
    if not arc or encounters.pending(conn):
        return None
    idx = chapter(conn)
    if idx >= len(arc["chapters"]):
        return None
    ch = arc["chapters"][idx]
    if not _cond_met(conn, player, ch.get("cond", {})):
        return None
    from engine.systems import npc_factory
    import random
    rng = random.Random(tick_mod.get_tick(conn) * 313 + idx)
    ctx = {"npc_name": npc_factory.unique_name(rng, conn=conn), "story": True}
    sc = dict(ch["scene"])
    sc["title"] = f"{arc['title']} — {sc['title']} (capitolo {idx + 1}/{len(arc['chapters'])})"
    sc["event_type"] = "story"
    sc["sticky"] = True
    scene = encounters.format_scene(sc, ctx)
    scene["sticky"] = True
    scene["event_type"] = "story"
    state.set(conn, CH_KEY, str(idx + 1))
    return encounters.start_scene(conn, player, scene)


def _fill(text: str, conn) -> str:
    d = state.get_json(conn, NPCS_KEY, {}) or {}
    out = text
    for role in d:
        n = story_npc(conn, role)
        if n:
            out = out.replace("{" + role + "}", n["name"])
    return out


def goals(conn: sqlite3.Connection, player: entities.Player) -> str:
    """Il diario degli obiettivi: storia personale + traguardi vicini."""
    from engine.simulation import cultivation
    from engine.systems import sects, sect_life, bonds, bounties, training
    t = tick_mod.get_tick(conn)
    lines = []
    arc = arc_for(conn, player.id)
    if arc:
        idx = chapter(conn)
        n = len(arc["chapters"])
        lines.append(f"☯ La tua storia — «{arc['title']}»")
        if idx >= n:
            lines.append("  Compiuta. Da qui in poi scrivi la tua leggenda.")
        else:
            goal = _fill(arc["chapters"][idx]["goal"], conn)
            lines.append(f"  Capitolo {idx + 1}/{n}: {goal}")
            for role in ("capo",):
                sn = story_npc(conn, role)
                if sn and sn["status"] == "alive" and "{" + role + "}" in arc["chapters"][idx]["goal"]:
                    ln = conn.execute("SELECT name FROM locations WHERE id=?;", (sn["location_id"],)).fetchone()
                    if ln:
                        lines.append(f"  (Ultimo avvistamento: {ln['name']})")
    lines.append("Traguardi vicini:")
    rec = cultivation.get_record(conn, "player", player.id)
    if rec:
        st = rec["stage"] or 1
        if st >= 10 and rec["progress"] >= 1.0:
            lines.append("  · Sei al colmo del regno: tenta il 'breakthrough'.")
        else:
            lines.append(f"  · Coltivazione: Strato {st}/10 ({rec['progress']*100:.0f}%). "
                         f"Allo Strato 10 colmo potrai sfondare al regno successivo.")
    m = sects.get_membership(conn, player.id)
    if not m:
        lines.append("  · Non hai una setta: 'sects' per vedere dove entrare, poi 'join' alla sede.")
    else:
        nxt = sect_life.next_event(conn, t, player.id)
        if nxt:
            days = max(0, (nxt["fire_tick"] - t + training.DAY_TICKS - 1) // training.DAY_TICKS)
            label = "Sfida di Classifica" if nxt["kind"] == "ranking_challenge" else "Torneo Mensile"
            lines.append(f"  · {label} della setta: {'oggi' if days == 0 else f'tra {days} giorni'}.")
        lines.append(f"  · Rango: {m['rank']} — 'challenge' per scalare la gerarchia.")
    for nm in bonds.nemeses(conn, player.id):
        lines.append(f"  · Nemesi: {nm['name']} ti cerca ({nm['reason']}).")
    comp = bonds.companion(conn, player.id)
    if comp:
        lines.append(f"  · In viaggio con {comp['name']}.")
    ab = bounties.active_bounties(conn)
    if ab:
        lines.append(f"  · {len(ab)} ricercati con una taglia: 'bounties'.")
    tl = state.titles(conn)
    if tl:
        lines.append(f"Titoli: {', '.join(tl)}")
    return "\n".join(lines)
