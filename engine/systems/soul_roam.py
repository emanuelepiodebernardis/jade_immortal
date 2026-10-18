"""
IL VIAGGIO DELL'ANIMA e le DUE MEDITAZIONI (Aggiornamento 63).

VIAGGIO DELL'ANIMA (元神出窍) — dall'Anima Nascente (4° regno) l'anima può uscire dal corpo e vagare
lontano mentre il corpo resta seduto. Ogni viaggio costa un po' di spirito; al giorno se ne fanno
3 più uno ogni tre regni. L'anima trova tesori, erbe che nessun piede raggiunge, altre anime erranti
che ti insegnano qualcosa, frammenti delle Note del Tao… o qualcosa che la ferisce: un'anima ferita
rallenta la coltivazione per due giorni. (Spunto: il «Soul Wandering» di Immortal Taoists.)

LE DUE MEDITAZIONI — una volta al giorno ciascuna:
  meditazione mente   lo spirito si tempra e il Dao si schiarisce; ogni 10 meditazioni, una NOTA
                      DEL TAO: venti frammenti che raccontano la storia antica del mondo
  meditazione corpo   il corpo si rinforza; ogni 10 meditazioni, un punto attributo in più
(Spunto: la Stanza della Meditazione di Immortal Taoists, coi suoi appunti taoisti.)

  vaga                 l'anima esce e vaga
  meditazione mente|corpo
  note                 le Note del Tao che hai ritrovato
"""

from __future__ import annotations

import random

from engine.core import tick as tick_mod
from engine.systems import state

KEY = "soul_roam"
MIN_TIER = 4
TRIP_COST = 0.06
WOUND_DAYS = 2

NOTES = [
    ("Il Primo Respiro", "Prima delle sette, prima dei regni, c'era solo il Qi, e il Qi non aveva nome. Il primo uomo "
                         "che respirò sapendo di respirare fu il primo coltivatore. Nessuno ricorda il suo nome: lui "
                         "stesso lo dimenticò, per poter salire."),
    ("I Nove Gradini", "I nove regni del Mondo Mortale non li ha creati il Cielo. Li tracciarono nove maestri, uno "
                       "per gradino, perché chi veniva dopo non si perdesse. Il nono maestro non tornò mai indietro."),
    ("La Giada che Ricorda", "La giada assorbe ciò che le accade intorno. Per questo gli antichi incidevano le tecniche "
                             "nella giada: non perché duri, ma perché ricorda chi l'ha toccata."),
    ("Il Primo Tradimento", "Il primo allievo che avvelenò il maestro lo fece per una tecnica. Il maestro, morendo, "
                            "rise: la tecnica era incompleta. Da allora ogni maestro tiene per sé l'ultimo passo."),
    ("Le Razze che Caddero", "Draghi, fenici, qilin: un tempo regnavano. Poi gli uomini impararono a coltivare il "
                             "loro sangue. Le razze antiche non furono vinte in battaglia, ma bevute."),
    ("La Guerra con il Cielo", "Il Cielo non odia chi sale. Odia chi tocca Spazio, Tempo e Destino, perché sono le sue "
                               "ossa. Ogni tribolazione è il Cielo che si accerta di avere ancora tutte le ossa."),
    ("Il Palazzo delle Anime", "Il Palazzo delle Anime nacque da un alchimista che non voleva morire. Raccolse anime "
                               "come altri raccolgono erbe. Oggi i suoi eredi non ricordano più perché lo fanno."),
    ("Lo Stendardo", "Il primo stendardo delle diecimila anime fu cucito da una madre che non voleva lasciar andare i "
                     "figli caduti in guerra. Le sette demoniache ne copiarono la forma, non il motivo."),
    ("La Porta Celeste", "Chi ascende lascia tutto. Non è una regola del Cielo: è che le cose del mondo di sotto non "
                         "sanno respirare lassù. Solo ciò che è legato all'anima sopravvive al passaggio."),
    ("I Fili del Destino", "A ogni regno il Cielo mostra tre fili. Gli antichi dicevano che il quarto, quello che non "
                           "vedi, è il filo che scegli rifiutando gli altri tre."),
    ("Il Demone del Cuore", "Il demone del cuore non viene da fuori. È la parte di te che ha fretta. Per questo colpisce "
                            "i discepoli ambiziosi e risparmia quelli che sanno aspettare."),
    ("Le Due Bilance", "Il karma non è una bilancia sola. Il bene che fai e il male che fai non si annullano: pesano "
                       "entrambi, su due piatti diversi, e un giorno ti chiederanno conto di tutti e due."),
    ("Il Mondo di Sotto", "Gli immortali credono di aver lasciato il mondo di sotto. Ma il mondo di sotto non li ha "
                          "lasciati: ogni preghiera è un filo, e i fili tirano."),
    ("La Pagoda dei Nove Piani", "Ogni piano della pagoda tiene un prigioniero. L'ultimo piano tiene il nome di chi la "
                                 "costruì: lo spirito della pagoda è quel nome, che si è dimenticato di sé."),
    ("La Fiamma Strana", "Esistono fiamme nate dal cuore della terra, dalle stelle, dal dolore. Un alchimista vale "
                         "quanto la fiamma che ha osato domare."),
    ("Il Corpo Supremo", "Corpo e sangue sono due fiumi. Chi li fa scorrere nello stesso letto diventa qualcosa che "
                         "il mondo non ha ancora nominato."),
    ("Gli Strati del Mondo", "Sopra il Mondo Mortale c'è lo Spirituale, poi l'Immortale, il Celeste, il Divino, il "
                             "Primordiale e il Caos. Nessuno sa cosa ci sia oltre: chi lo ha scoperto non è tornato a dirlo."),
    ("Chi Rinasce", "La morte non è la fine della Via, solo di una vita. L'anima porta con sé ciò che ha capito; il "
                    "corpo, solo ciò che ha sofferto."),
    ("Il Nono Maestro", "Il nono maestro dei Nove Gradini non tornò indietro perché trovò, in cima, un decimo gradino. "
                        "E sopra il decimo, un altro. La Via non finisce: è per questo che si chiama Via."),
    ("La Giada Immortale", "Si dice che il primo coltivatore, quello senza nome, sia diventato giada. Che ogni pezzo di "
                           "giada del mondo sia un frammento di lui. E che chi raccoglie tutti i frammenti… ma la nota "
                           "si interrompe qui."),
]


def get(conn) -> dict:
    return state.get_json(conn, KEY, None) or {"trips_day": -1, "trips": 0, "wound_until": -1, "notes": [],
                                               "mind": 0, "body": 0, "mind_day": -1, "body_day": -1, "body_pts": 0}


def _save(conn, d: dict) -> None:
    state.set_json(conn, KEY, d)


def _day(conn) -> int:
    return tick_mod.get_tick(conn) // 120


def _tier(conn, pid) -> int:
    from engine.simulation import cultivation
    return cultivation.realm_tier(conn, "player", pid) or 1


def trips_max(conn, pid: int) -> int:
    return 3 + _tier(conn, pid) // 3


def _note(conn, d: dict, out: list) -> None:
    have = set(d["notes"])
    nxt = next((i for i in range(len(NOTES)) if i not in have), None)
    if nxt is None:
        return
    d["notes"].append(nxt)
    title, _txt = NOTES[nxt]
    out.append(f"📜 Ritrovi una NOTA DEL TAO ({len(d['notes'])}/{len(NOTES)}): «{title}». ('note' per leggerla)")
    if len(d["notes"]) == len(NOTES):
        state.grant_title(conn, "Custode delle Note del Tao")


def roam(conn, player) -> str:
    from engine.systems import deep_dao, rewards, items, professions, dao_training
    if _tier(conn, player.id) < MIN_TIER:
        return "L'anima può uscire dal corpo solo dall'Anima Nascente (4° regno)."
    d = get(conn)
    day = _day(conn)
    if d["trips_day"] != day:
        d["trips_day"], d["trips"] = day, 0
    if d["trips"] >= trips_max(conn, player.id):
        return f"L'anima è stanca: oggi ha già vagato {d['trips']} volte."
    if d["wound_until"] >= day:
        return "L'anima è ferita: deve riposare prima di uscire di nuovo."
    ok, why = deep_dao._pay(conn, player.id, TRIP_COST)
    if not ok:
        return why
    d["trips"] += 1
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 7 + d["trips"] * 31 + player.id)
    roll = rng.random()
    out = [f"Il corpo resta seduto. L'anima si stacca come un filo di fumo e vola lontano. {why}"]
    if roll < 0.30:
        out.append("Tra le rovine di un mondo dimenticato, l'anima vede ciò che gli occhi non vedono:")
        out += rewards.grant(conn, rng, player, rank=3, kinds=["tesoro", "pillola", "essenza"], n=1, stones=True)
    elif roll < 0.50:
        k = rng.choice(["erbe", "nuclei", "minerali"])
        n = 2 + _tier(conn, player.id)
        professions.give(conn, player.id, k, n)
        out.append(f"Su una cima che nessun piede ha toccato, l'anima raccoglie {n} {k}.")
    elif roll < 0.68:
        rows = dao_training.trainable_daos(conn, player.id)
        dk = rng.choice(rows)["dao_key"] if rows else "anima"
        out.append("Incontri un'altra anima errante, vecchia di mille anni. Parlate fino all'alba:")
        out += items.apply_effects(conn, t, rng, player.id, {"dao_key": dk, "dao_gain": 2 + _tier(conn, player.id) // 2})
    elif roll < 0.80:
        out.append("In una biblioteca crollata, una pagina si muove da sola verso di te.")
        _note(conn, d, out)
        if len(out) == 2:
            out.append("Hai già tutte le Note del Tao: la pagina è bianca.")
    elif roll < 0.90:
        out.append("Qualcosa di antico e affamato ti vede. L'anima torna nel corpo a fatica: è FERITA "
                   f"(coltivazione rallentata per {WOUND_DAYS} giorni).")
        d["wound_until"] = day + WOUND_DAYS - 1
    else:
        from engine.systems import soul_temper
        out.append("Voli così in alto che vedi la curva del mondo. Torni più grande di come sei partito.")
        out += soul_temper.add_xp(conn, 0.6)
    _save(conn, d)
    out.append(f"(Viaggi di oggi: {d['trips']}/{trips_max(conn, player.id)})")
    return "\n".join(out)


def meditate(conn, player, which: str) -> str:
    from engine.systems import soul_temper, dao_training, items, spirit
    d = get(conn)
    day = _day(conn)
    w = (which or "").strip().lower()
    t = tick_mod.get_tick(conn)
    rng = random.Random(t * 17 + 3)
    if w.startswith(("ment", "anim", "spir")):
        if d["mind_day"] == day:
            return "La meditazione della mente l'hai già fatta oggi."
        d["mind_day"] = day
        d["mind"] += 1
        out = [f"Siedi e svuoti la mente. (Meditazione della mente n.{d['mind']})"]
        out += soul_temper.add_xp(conn, 0.25)
        spirit.restore_fraction(conn, 0.2, player.id)
        rows = dao_training.trainable_daos(conn, player.id)
        if rows:
            out += items.apply_effects(conn, t, rng, player.id, {"dao_key": rows[0]["dao_key"], "dao_gain": 1})
        if d["mind"] % 10 == 0:
            _note(conn, d, out)
    elif w.startswith(("corp", "fis", "carne")):
        if d["body_day"] == day:
            return "La meditazione del corpo l'hai già fatta oggi."
        d["body_day"] = day
        d["body"] += 1
        out = [f"Fai scorrere il Qi nelle ossa, una per una. (Meditazione del corpo n.{d['body']})"]
        items.apply_effects(conn, t, rng, player.id, {"cultivation_progress": 0.03})
        if d["body"] % 10 == 0:
            d["body_pts"] += 1
            out.append("✦ Il corpo si apre a un nuovo limite: +1 punto attributo.")
    else:
        return "meditazione mente | meditazione corpo (una volta al giorno ciascuna)"
    _save(conn, d)
    return "\n".join(out)


def bonus_points(conn) -> int:
    return int(get(conn).get("body_pts", 0))


def cultivation_mult(conn) -> tuple[float, str]:
    d = get(conn)
    if d["wound_until"] >= _day(conn):
        return 0.8, "l'anima ferita nel viaggio"
    return 1.0, ""


def notes_text(conn) -> str:
    d = get(conn)
    if not d["notes"]:
        return ("Non hai ancora ritrovato Note del Tao. Si trovano meditando con la mente (una ogni dieci "
                "meditazioni) e viaggiando con l'anima.")
    lines = [f"📜 LE NOTE DEL TAO ({len(d['notes'])}/{len(NOTES)})"]
    for i in sorted(d["notes"]):
        title, txt = NOTES[i]
        lines.append(f"\n{i + 1}. {title}\n   {txt}")
    return "\n".join(lines)


def menu_section(conn, player):
    from engine.systems.menus import act, section
    d = get(conn)
    day = _day(conn)
    tier = _tier(conn, player.id)
    trips = d["trips"] if d["trips_day"] == day else 0
    lines = [f"Meditazioni: mente {d['mind']} (prossima nota alla {(d['mind'] // 10 + 1) * 10}ª), "
             f"corpo {d['body']} (prossimo punto alla {(d['body'] // 10 + 1) * 10}ª).",
             f"Note del Tao: {len(d['notes'])}/{len(NOTES)}."]
    if tier >= MIN_TIER:
        lines.append(f"Viaggi dell'anima oggi: {trips}/{trips_max(conn, player.id)}"
                     + (" — l'anima è ferita" if d["wound_until"] >= day else "") + ".")
    acts = [act("Meditazione della mente", "meditazione mente", d["mind_day"] != day, "già fatta oggi"),
            act("Meditazione del corpo", "meditazione corpo", d["body_day"] != day, "già fatta oggi"),
            act("L'anima esce e vaga", "vaga", tier >= MIN_TIER and trips < trips_max(conn, player.id)
                and d["wound_until"] < day, "dall'Anima Nascente" if tier < MIN_TIER else "non oggi"),
            act("Leggi le Note del Tao", "note", bool(d["notes"]), "nessuna ancora")]
    return section("Meditazioni e viaggi dell'anima", lines, acts, icon="🧘")
