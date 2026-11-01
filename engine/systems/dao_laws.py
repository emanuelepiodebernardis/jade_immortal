"""
LE LEGGI NUOVE (Aggiornamento 77) — 34 Dao in più e le FUSIONI che creano un Dao nuovo.

Ispirati alla struttura dei grandi romanzi del genere (leggi elementali e profonde, Dao d'arma con il loro
intento, Dao del corpo e dell'anima, vie proibite, Dao che si fondono in uno più alto). Nomi, testi e
numeri sono originali.

OGNI DAO ha:
  · uno SBLOCCO: «scelta» (lo apri studiandolo, con un costo in pietre), «derivato» (serve un Dao di base a
    una certa comprensione) o «risveglio» (una condizione nel mondo, come i Dao superiori);
  · EFFETTI che crescono con la soglia di comprensione i (0 principiante … 10 antenato), ognuno con un tetto;
  · un COSTO vero, fisso, che arriva insieme al Dao (nessun Dao è migliore di un altro in tutto);
  · lo stato di combattimento che porta (gelo, veleno, confusione…) e la statistica che rafforza.

LE FUSIONI (fusione <a> <b> [<c>]): con i componenti abbastanza avanti e il cuore del Dao ≥ 70 nasce un Dao
nuovo, che parte da un quarto della somma delle comprensioni. Le coppie in conflitto (fuoco/ghiaccio,
luce/oscurità…) senza un ponte rischiano il fallimento: deviazione del qi, cuore −15.

Le leve (sommate tra tutti i Dao, ognuna col suo tetto):
  atk/def/vit  moltiplicatori di attacco, difesa, vitalità (combat_power)
  crit/evade/taken/pierce/strikes  in duello e in combattimento (combat_states)
  cult  coltivazione · dao  comprensione dei Dao · life  anni di vita · qi/spirit  riserve
Aggiungere un Dao = una riga in NEW; una fusione = una riga in FUSIONS.
"""

from __future__ import annotations

import random

# (chiave, nome, livello, descrizione, sblocco, statistica, stato, combattimento,
#  effetti per soglia {leva: (per_i, tetto)}, costo fisso {leva: valore}, vantaggio, svantaggio)
NEW = [
    # ---------------------------------------------------------------- elementali
    ("ghiaccio", "Dao del Ghiaccio", "elemental", "Il freddo come stasi: non scorre, si ferma e conserva.",
     ("derivato", {"acqua": 25}), "defense", "gelo", True,
     {"taken": (0.02, 0.15), "def": (0.02, 0.2)}, {"cult": -0.03},
     "difesa e controllo solidi", "coltivi più lentamente (il freddo rallenta anche te)"),
    ("veleno", "Dao del Veleno", "elemental", "La dose fa il Dao: ogni cosa è medicina o veleno.",
     ("scelta",), "attack", "veleno", True,
     {"pierce": (0.02, 0.2), "atk": (0.02, 0.2)}, {"vit": -0.03},
     "danno che ignora la difesa", "il tuo corpo si indebolisce un poco"),
    ("suono", "Dao del Suono", "elemental", "Onde che il corpo e l'anima non possono ignorare.",
     ("scelta",), "attack", "confusione", True,
     {"pierce": (0.03, 0.3), "crit": (0.01, 0.08)}, {"evade": -0.05},
     "aggira gli scudi", "ti rende facile da trovare: schivi meno"),
    ("gravita", "Dao della Gravità", "elemental", "La massa come legge: chi ti si avvicina diventa pesante.",
     ("derivato", {"terra": 50}), "defense", "stordimento", True,
     {"def": (0.03, 0.25), "taken": (0.015, 0.12)}, {"evade": -0.05, "spirit": -0.05},
     "rallenta e schiaccia i nemici veloci", "sei più lento e le tecniche ti costano"),
    ("nebbia", "Dao della Nebbia", "elemental", "Ciò che non si vede non si colpisce.",
     ("scelta",), "defense", "accecamento", True,
     {"evade": (0.02, 0.2)}, {"crit": -0.05, "atk": -0.04},
     "sopravvivi agli scontri persi", "colpi meno precisi"),
    ("magnetismo", "Dao del Magnetismo", "elemental", "Attrazione e repulsione: le armi nemiche non obbediscono più.",
     ("derivato", {"metallo": 25, "fulmine": 25}), "attack", "stordimento", True,
     {"atk": (0.03, 0.25)}, {"def": -0.03},
     "dominante contro chi si affida ad armi e tesori", "difesa un poco più fragile"),
    ("stagioni", "Dao delle Stagioni", "elemental", "Il movimento dell'anno che dà ordine a tutti gli elementi.",
     ("scelta",), "vitality", "rigenerazione", True,
     {"vit": (0.03, 0.25), "cult": (0.01, 0.08)}, {"atk": -0.03},
     "costante e prevedibile, cresce con la pazienza", "attacco un poco più debole"),
    # ---------------------------------------------------------------- arma
    ("scudo", "Dao dello Scudo", "narrative", "Proteggere è un'arte di combattimento, non una rinuncia.",
     ("scelta",), "defense", "scudo", True,
     {"taken": (0.03, 0.3)}, {"atk": -0.08},
     "il muro che nessuno attraversa", "la postura rigida toglie forza ai colpi"),
    ("martello", "Dao del Martello", "narrative", "Un colpo solo, abbastanza pesante da cambiare la forma delle cose.",
     ("scelta",), "attack", "stordimento", True,
     {"atk": (0.03, 0.3), "pierce": (0.02, 0.2)}, {"evade": -0.05},
     "rompe scudi e corazze", "lento: schivi meno"),
    ("catena", "Dao della Catena", "narrative", "Legare è più potente che colpire: ciò che è fermo si può decidere.",
     ("scelta",), "attack", "stordimento", True,
     {"atk": (0.02, 0.2), "evade": (0.01, 0.08)}, {"atk": -0.05},
     "controllo: il nemico non sfugge", "il primo giro serve a preparare il legame"),
    ("pugnale", "Dao del Pugnale", "narrative", "Il colpo che non sarà mai visto.",
     ("scelta",), "attack", "emorragia", True,
     {"crit": (0.04, 0.45), "pierce": (0.03, 0.3)}, {"taken": -0.08},
     "critici esplosivi", "negli scontri lunghi incassi di più"),
    ("pennello", "Dao del Pennello", "narrative", "Scrivere una legge in un segno: talismani e sigilli come armi.",
     ("scelta",), "spirit", None, False,
     {"spirit": (0.04, 0.35), "qi": (0.03, 0.25)}, {"atk": -0.03},
     "riserve di spirito e qi molto più grandi", "nessun bonus diretto d'attacco"),
    ("falce", "Dao della Falce", "narrative", "Raccogliere ciò che è maturo.",
     ("derivato", {"vita_morte": 10, "massacro": 10}), "attack", "terrore", True,
     {"atk": (0.04, 0.35)}, {"def": -0.05},
     "il colpo che finisce i nemici", "apertura debole, difesa scoperta"),
    # ---------------------------------------------------------------- corpo e anima
    ("volonta", "Dao della Volontà", "systemic", "La forza del cuore senza forma: non si ruba, non si assorbe.",
     ("risveglio", "volonta"), "spirit", "pressione", True,
     {"taken": (0.02, 0.2), "spirit": (0.03, 0.3)}, {"dao": -0.15},
     "resisti a paura, follia e tribolazioni", "disciplina totale: gli altri Dao crescono più piano"),
    ("ammaestramento", "Dao dell'Ammaestramento", "systemic", "Comprendere un animale come si comprende un elemento.",
     ("scelta",), "vitality", None, False,
     {"vit": (0.02, 0.15), "cult": (0.01, 0.06)}, {"atk": -0.05},
     "linea di gioco con le creature", "il tuo attacco personale cala"),
    ("alchimia", "Dao dell'Alchimia", "systemic", "Trasformare la materia in effetto.",
     ("scelta",), "spirit", None, False,
     {"qi": (0.03, 0.3), "cult": (0.01, 0.1)}, {"atk": -0.03},
     "coltivi meglio e hai più qi", "un poco meno di forza in battaglia"),
    ("forgia", "Dao della Forgia", "systemic", "Dare un'anima al metallo.",
     ("scelta",), "attack", None, True,
     {"atk": (0.02, 0.2), "def": (0.02, 0.2)}, {"cult": -0.03},
     "armi e armature più vive", "le ore alla forgia rubano tempo alla coltivazione"),
    ("formazioni", "Dao delle Formazioni", "systemic", "Le leggi disegnate sul terreno.",
     ("scelta",), "defense", "scudo", True,
     {"def": (0.03, 0.25), "taken": (0.01, 0.1)}, {"evade": -0.03},
     "difesa del territorio e ritiri sicuri", "ti muovi meno"),
    ("longevita", "Dao della Longevità", "systemic", "Ritardare la fine senza negarla.",
     ("scelta",), "vitality", "rigenerazione", True,
     {"life": (25, 250), "vit": (0.02, 0.2)}, {"cult": -0.06},
     "anni di vita in più", "ti spendi meno: coltivi più lentamente"),
    ("sguardo", "Dao dello Sguardo", "systemic", "Vedere ciò che c'è davvero.",
     ("scelta",), "spirit", "accecamento", True,
     {"crit": (0.02, 0.2), "evade": (0.01, 0.1)}, {"spirit": -0.06},
     "vedi i punti deboli", "la fatica di vedere: meno spirito"),
    # ---------------------------------------------------------------- profondi
    ("annientamento", "Dao dell'Annientamento", "deep", "Disfare: ridurre a niente il disegno di ciò che tocchi.",
     ("risveglio", "annientamento"), "attack", "pressione", True,
     {"pierce": (0.05, 0.5), "atk": (0.03, 0.3)}, {"vit": -0.08},
     "rompe qualsiasi difesa", "ogni uso ti consuma"),
    ("ordine", "Dao dell'Ordine", "deep", "La regola come forza: ciò che hai promesso vincola tutti.",
     ("risveglio", "ordine"), "defense", "retribuzione", True,
     {"taken": (0.02, 0.2), "def": (0.02, 0.2)}, {"atk": -0.05},
     "autorità e difesa", "non colpisci mai per primo chi non è ostile"),
    ("numeri", "Dao dei Numeri", "deep", "Il mondo ha una forma calcolabile.",
     ("derivato", {"destino": 25}), "attack", None, True,
     {"crit": (0.02, 0.2), "evade": (0.02, 0.15)}, {"atk": -0.03},
     "precisione: leggi il ritmo del nemico", "lento nei primi scambi"),
    ("ciclo", "Dao del Ciclo", "deep", "Tutto ritorna: il ricorso come sorgente di potere.",
     ("risveglio", "ciclo"), "vitality", "rigenerazione", True,
     {"vit": (0.02, 0.2), "cult": (0.015, 0.12)}, {"atk": -0.05},
     "efficienza e durata", "devi «iniziare il giro»: attacco più debole"),
    ("origine", "Dao dell'Origine", "deep", "La fonte da cui nascono tutte le vie.",
     ("risveglio", "origine"), "spirit", None, False,
     {"dao": (0.02, 0.25), "cult": (0.01, 0.1)}, {"spirit": -0.05},
     "tutti i Dao crescono più in fretta", "il Cielo ti guarda con sospetto"),
    ("mondo", "Dao del Mondo", "deep", "Un mondo interiore con le tue leggi.",
     ("derivato", {"spazio": 100}), "spirit", "scudo", True,
     {"cult": (0.02, 0.2), "def": (0.02, 0.2)}, {"spirit": -0.08},
     "coltivazione e domini più forti", "tenerlo in piedi costa spirito"),
    ("memoria", "Dao della Memoria", "deep", "Ciò che si ricorda non è perso.",
     ("scelta",), "spirit", None, False,
     {"dao": (0.015, 0.15), "qi": (0.02, 0.15)}, {"spirit": -0.03},
     "impari più in fretta", "i ricordi dolorosi pesano"),
    ("confine", "Dao del Confine", "deep", "Un limite stabilisce cosa può entrare.",
     ("derivato", {"spazio": 50}), "defense", "scudo", True,
     {"taken": (0.02, 0.2)}, {"evade": -0.05},
     "barriere e immunità", "le barriere ti tengono fermo"),
    ("specchio", "Dao dello Specchio", "deep", "Ciò che arriva a te torna al mittente.",
     ("derivato", {"illusione": 25, "luce": 25}), "defense", "retribuzione", True,
     {"taken": (0.02, 0.2), "crit": (0.01, 0.08)}, {"atk": -0.08},
     "rimandi i colpi", "nessuna forza propria"),
    # ---------------------------------------------------------------- proibiti
    ("divoramento", "Dao del Divoramento", "forbidden", "Consumare per crescere: ciò che inghiotti diventa tuo.",
     ("risveglio", "divoramento"), "attack", "drenaggio", True,
     {"atk": (0.03, 0.3), "vit": (0.02, 0.2)}, {"spirit": -0.05},
     "crescita rapida, ti curi colpendo", "la fame non finisce mai"),
    ("maledizione", "Dao della Maledizione", "forbidden", "Un augurio che non si ritira.",
     ("risveglio", "maledizione"), "attack", "terrore", True,
     {"atk": (0.03, 0.3), "pierce": (0.02, 0.15)}, {"vit": -0.05},
     "colpisce anche da lontano", "una parte del male torna a te"),
    ("morti", "Dao dei Morti", "forbidden", "Il confine non è un muro, ma una porta.",
     ("risveglio", "morti"), "attack", "drenaggio", True,
     {"atk": (0.03, 0.3), "strikes": (5, 1)}, {"spirit": -0.08},
     "i caduti combattono per te", "evocare costa spirito"),
    ("follia", "Dao della Follia", "forbidden", "Spezzare la mente per liberarne la forza.",
     ("risveglio", "follia"), "attack", "terrore", True,
     {"atk": (0.06, 0.5)}, {"taken": -0.15},
     "danno enorme", "incassi molto di più"),
    ("sacrificio", "Dao del Sacrificio", "forbidden", "La potenza si paga con ciò che ti appartiene.",
     ("scelta",), "attack", "vita", True,
     {"atk": (0.05, 0.45), "crit": (0.02, 0.15)}, {"life": -30},
     "un picco di potenza decisivo", "anni di vita davvero perduti"),
]

# (chiave, nome, componenti {dao: comprensione minima}, ponti (basta uno), effetti per soglia, costo, descrizione)
FUSIONS = [
    # --- fusioni LEGGERE: componenti appena avviati, cuore ≥ 50, poche pietre. Portate in fondo aprono Dao più alti.
    ("vapore", "Dao del Vapore", {"acqua": 25, "fuoco": 25}, [], {"atk": (0.02, 0.2), "evade": (0.01, 0.1)},
     {"def": -0.02}, "Acqua e fuoco che smettono di combattersi e diventano nube."),
    ("linfa", "Dao della Linfa", {"legno": 25, "acqua": 25}, [], {"vit": (0.02, 0.2), "cult": (0.01, 0.08)},
     {"atk": -0.02}, "L'acqua che sale nel tronco e diventa vita."),
    ("ferro_rovente", "Dao del Ferro Rovente", {"metallo": 25, "fuoco": 25}, [], {"atk": (0.02, 0.2), "pierce": (0.01, 0.1)},
     {"vit": -0.02}, "Il metallo nel momento in cui accetta una forma."),
    ("sabbia", "Dao della Sabbia", {"terra": 25, "vento": 25}, [], {"def": (0.02, 0.15), "evade": (0.01, 0.1)},
     {"atk": -0.02}, "La montagna che il vento ha fatto in polvere."),
    ("tempesta", "Dao della Tempesta", {"fulmine": 100, "vento": 100}, [], {"atk": (0.05, 0.4), "strikes": (4, 1)},
     {"def": -0.1}, "Il tuono e il vento diventano una cosa sola."),
    ("magma", "Dao del Magma", {"fuoco": 100, "terra": 100}, [], {"atk": (0.03, 0.3), "def": (0.03, 0.3)},
     {"evade": -0.05}, "La pietra che brucia e scorre."),
    ("fuoco_gelido", "Dao del Fuoco Gelido", {"fuoco": 150, "ghiaccio": 150}, ["yinyang", "acqua"],
     {"atk": (0.04, 0.35), "pierce": (0.03, 0.3)}, {"cult": -0.03}, "Una fiamma che congela ciò che tocca."),
    ("spaziotempo", "Dao dello Spaziotempo", {"spazio": 250, "tempo": 250}, [],
     {"evade": (0.02, 0.2), "strikes": (3, 1), "cult": (0.02, 0.2)}, {"spirit": -0.05},
     "Il luogo e l'istante come un solo tessuto."),
    ("fili_fato", "Dao dei Fili del Fato", {"karma": 250, "destino": 250}, [],
     {"crit": (0.03, 0.3), "taken": (0.02, 0.2)}, {"atk": -0.03}, "Cause, effetti e ciò che deve accadere."),
    ("ruota", "Dao della Ruota Completa", {"samsara": 250, "vita_morte": 250, "ciclo": 100}, [],
     {"vit": (0.05, 0.5), "life": (40, 400)}, {"atk": -0.05}, "Nascere, morire, tornare."),
    ("singolarita", "Dao della Singolarità", {"gravita": 150, "spazio": 250, "vuoto": 250}, [],
     {"pierce": (0.04, 0.4), "evade": (0.02, 0.2)}, {"spirit": -0.1}, "Un punto che tutto attira."),
    ("lama_atemporale", "Dao della Lama Atemporale", {"spada": 250, "spaziotempo": 250}, [],
     {"crit": (0.03, 0.3), "pierce": (0.04, 0.4), "strikes": (3, 2)}, {"vit": -0.05}, "Tagli fuori dal tempo."),
    ("intento_assoluto", "Dao dell'Intento Assoluto", {"spada": 250, "volonta": 150}, [],
     {"atk": (0.05, 0.4), "crit": (0.02, 0.2)}, {"dao": -0.05}, "L'ultimo stadio dell'intento della spada."),
    ("canto_anima", "Dao del Canto dell'Anima", {"suono": 100, "anima": 100}, [],
     {"pierce": (0.03, 0.3), "evade": (0.02, 0.15)}, {"def": -0.03}, "Una voce che entra nell'anima."),
    ("putrefazione", "Dao della Putrefazione", {"veleno": 100, "legno": 100, "morti": 50}, [],
     {"pierce": (0.04, 0.35), "atk": (0.03, 0.25)}, {"vit": -0.05}, "Ciò che vive marcisce, ciò che marcisce nutre."),
    ("regno", "Dao del Regno Interiore", {"mondo": 250, "spazio": 250}, [],
     {"cult": (0.03, 0.3), "def": (0.03, 0.25), "atk": (0.02, 0.15)}, {"spirit": -0.1}, "Il tuo mondo, le tue leggi."),
    ("legge_vincolante", "Dao della Legge Vincolante", {"ordine": 250, "karma": 250}, [],
     {"taken": (0.03, 0.3), "def": (0.02, 0.2)}, {"atk": -0.05}, "Ciò che è giurato non si spezza."),
    ("calcolo_fato", "Dao del Calcolo del Fato", {"numeri": 150, "destino": 150}, [],
     {"evade": (0.02, 0.2), "crit": (0.02, 0.2)}, {"atk": -0.03}, "Prevedere la mossa prima del gesto."),
    ("mille_specchi", "Dao dei Mille Specchi", {"specchio": 150, "illusione": 150, "luce": 100}, [],
     {"taken": (0.03, 0.3), "evade": (0.02, 0.15)}, {"atk": -0.08}, "Il nemico combatte contro se stesso."),
    ("rimembranza", "Dao della Rimembranza", {"memoria": 250, "tempo": 250}, [],
     {"dao": (0.02, 0.2), "cult": (0.02, 0.15)}, {"spirit": -0.05}, "Nulla di ciò che hai vissuto si perde."),
    ("fame_nulla", "Dao della Fame del Nulla", {"divoramento": 250, "vuoto": 250}, [],
     {"atk": (0.05, 0.45), "vit": (0.03, 0.3)}, {"cult": -0.05}, "Inghiottire anche il vuoto."),
    ("fiamma_vita", "Dao della Fiamma della Vita", {"alchimia": 100, "fuoco": 100, "legno": 100}, [],
     {"vit": (0.04, 0.35), "qi": (0.03, 0.3), "cult": (0.01, 0.1)}, {"atk": -0.03}, "Il fuoco che guarisce."),
    ("fortezza", "Dao della Fortezza Immobile", {"scudo": 150, "terra": 150, "gravita": 100}, [],
     {"taken": (0.04, 0.35), "def": (0.04, 0.4)}, {"evade": -0.1, "atk": -0.05}, "Ciò che non si muove non cade."),
    ("anno_eterno", "Dao dell'Anno Eterno", {"stagioni": 150, "ciclo": 150, "tempo": 150}, [],
     {"vit": (0.03, 0.3), "atk": (0.03, 0.25), "cult": (0.02, 0.15)}, {"def": -0.05}, "Tutte le stagioni in una."),
    ("oblio", "Dao dell'Oblio", {"annientamento": 250, "creazione": 250, "ciclo": 250}, [],
     {"pierce": (0.05, 0.5), "vit": (0.04, 0.35)}, {"life": -20}, "Disfare e rifare."),
    ("fiume_giorni", "Dao del Fiume dei Giorni", {"tempo": 250, "destino": 250, "memoria": 150}, [],
     {"evade": (0.03, 0.25), "dao": (0.02, 0.15)}, {"vit": -0.03}, "Vedere il corso del mondo."),
    ("via_unica", "La Via Unica", {"origine": 500}, [],
     {"atk": (0.06, 0.6), "def": (0.05, 0.5), "vit": (0.05, 0.5), "cult": (0.03, 0.3), "dao": (0.03, 0.3)},
     {}, "Tutte le vie diventano una."),
]
# LA PROFONDITÀ DI UNA FUSIONE: cresce con la comprensione del Dao fuso (comprehend <fusione>).
GRADES = [(0, "leggera"), (50, "salda"), (250, "profonda"), (1000, "estrema")]
# e, portata avanti, ti dà l'INTUIZIONE di un Dao più alto: (comprensione della fusione, Dao che si apre)
INSIGHT = {
    "vapore": [(250, "nebbia"), (1000, "yinyang")], "linfa": [(100, "longevita"), (1000, "creazione")],
    "ferro_rovente": [(50, "forgia"), (500, "magnetismo")], "sabbia": [(100, "gravita"), (1000, "stagioni")],
    "tempesta": [(500, "suono"), (1000, "caos")], "magma": [(500, "creazione")], "fuoco_gelido": [(250, "yinyang")],
    "spaziotempo": [(250, "mondo"), (1000, "origine")], "fili_fato": [(500, "samsara"), (1000, "numeri")],
    "singolarita": [(500, "annientamento")], "putrefazione": [(250, "vita_morte")],
    "fiamma_vita": [(100, "longevita"), (500, "vita_morte")], "fortezza": [(500, "confine")],
    "anno_eterno": [(500, "samsara")], "mille_specchi": [(250, "sguardo")], "rimembranza": [(500, "samsara")],
    "intento_assoluto": [(1000, "annientamento")], "canto_anima": [(500, "illusione")],
}
LIGHT_HEART = 50
CONFLICTS = [({"fuoco", "ghiaccio"}, ["yinyang", "acqua"]), ({"luce", "oscurita"}, ["yinyang"]),
             ({"ordine", "follia"}, ["yinyang"]), ({"annientamento", "creazione"}, ["ciclo", "yinyang"])]
UNIQUE_NEEDS = 4                       # la Via Unica chiede almeno quattro Dao fusi
FUSE_HEART = 70

BY_KEY = {r[0]: r for r in NEW}
FUSED = {r[0]: r for r in FUSIONS}
LEVEL_IT = {"elemental": "elementale", "narrative": "arma", "systemic": "corpo e anima", "deep": "profondo",
            "forbidden": "proibito", "fused": "fuso"}
LEVER_IT = {"atk": "attacco", "def": "difesa", "vit": "vitalità", "crit": "critici", "evade": "schivata",
            "taken": "danni subiti ridotti", "pierce": "perforazione", "strikes": "colpi in più", "cult": "coltivazione",
            "dao": "comprensione dei Dao", "life": "anni di vita", "qi": "riserva di qi", "spirit": "riserva di spirito"}


# ---------------------------------------------------------------- registri (letti da dao_gen e dao_training)

def dao_rows() -> list[tuple]:
    return [(k, n, lv, d) for k, n, lv, d, *_ in NEW] + [(k, n, "fused", d) for k, n, _c, _b, _e, _x, d in FUSIONS]


COMBAT = {r[0] for r in NEW if r[7]} | {r[0] for r in FUSIONS}
STAT = {r[0]: r[5] for r in NEW} | {f[0]: "attack" for f in FUSIONS}
STATE = {r[0]: r[6] for r in NEW if r[6]}
_FUSION_STATE = {"tempesta": "stordimento", "magma": "ustione", "fuoco_gelido": "gelo", "spaziotempo": "pressione",
                 "fili_fato": "retribuzione", "ruota": "vita", "singolarita": "pressione", "lama_atemporale": "emorragia",
                 "intento_assoluto": "pressione", "canto_anima": "confusione", "putrefazione": "veleno",
                 "regno": "scudo", "legge_vincolante": "retribuzione", "calcolo_fato": "accecamento",
                 "mille_specchi": "confusione", "fame_nulla": "drenaggio", "fiamma_vita": "rigenerazione",
                 "fortezza": "scudo", "anno_eterno": "rigenerazione", "oblio": "pressione", "via_unica": "equilibrio"}
STATE.update(_FUSION_STATE)


# ---------------------------------------------------------------- comprensione → soglia

def tier_index(comp: int) -> int:
    from engine.systems import dao_training
    i = 0
    for n, (th, *_r) in enumerate(dao_training.DAO_THRESHOLDS):
        if comp >= th:
            i = n
    return i


def _rows(conn, pid: int = 1) -> dict[str, int]:
    keys = set(BY_KEY) | set(FUSED)
    return {r["dao_key"]: int(r["comprehension"] or 0) for r in conn.execute(
        "SELECT dao_key, comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
        "AND (practiced=1 OR comprehension>0);", (pid,)) if r["dao_key"] in keys}


def levers(conn, pid: int = 1) -> dict[str, float]:
    """Tutte le leve sommate: gli effetti (con i loro tetti) e i costi fissi di ogni Dao nuovo o fuso."""
    out: dict[str, float] = {}
    for k, comp in _rows(conn, pid).items():
        row = BY_KEY.get(k)
        eff, cost = (row[8], row[9]) if row else (FUSED[k][4], FUSED[k][5])
        i = tier_index(comp)
        for lv, (per, cap) in eff.items():
            if lv == "strikes":                         # (soglia, colpi): dalla soglia in su
                v = cap if i >= per else 0
            else:
                v = min(cap, per * i) if per >= 0 else max(cap, per * i)
            out[lv] = out.get(lv, 0.0) + v
        if i >= 1:
            for lv, v in cost.items():
                out[lv] = out.get(lv, 0.0) + v
    from engine.systems import personal_fusion          # (Agg. 80) le fusioni a cui hai dato tu il nome
    for lv, v in personal_fusion.levers(conn, pid, tier_index).items():
        out[lv] = out.get(lv, 0.0) + v
    return out


def combat_mults(conn) -> dict[str, float]:
    lv = levers(conn)
    return {"attack": max(0.5, 1.0 + lv.get("atk", 0.0)), "defense": max(0.5, 1.0 + lv.get("def", 0.0)),
            "vitality": max(0.5, 1.0 + lv.get("vit", 0.0))}


def combat(conn, fx) -> list[str]:
    lv = levers(conn)
    pr = fx.p.prof
    for k in ("crit", "evade", "pierce"):
        if lv.get(k):
            pr[k] = max(0.0, pr.get(k, 0.0) + lv[k])
    if lv.get("taken"):
        pr["taken"] = pr.get("taken", 0.0) + lv["taken"]
    if lv.get("strikes"):
        pr["extra_strikes"] = pr.get("extra_strikes", 0) + int(lv["strikes"])
    return []


def cultivation_mult(conn) -> tuple[float, str]:
    v = levers(conn).get("cult", 0.0)
    return (max(0.5, 1.0 + v), "le leggi che comprendi") if v else (1.0, "")


def dao_gain_mult(conn) -> float:
    return max(0.5, 1.0 + levers(conn).get("dao", 0.0))


def life_years(conn) -> int:
    return int(levers(conn).get("life", 0))


def qi_mult(conn) -> float:
    return max(0.5, 1.0 + levers(conn).get("qi", 0.0))


def spirit_mult(conn) -> float:
    return max(0.5, 1.0 + levers(conn).get("spirit", 0.0))


# ---------------------------------------------------------------- sbloccare un Dao nuovo

def _comp(conn, k: str, pid: int = 1) -> int:
    r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=? "
                     "AND dao_key=?;", (pid, k)).fetchone()
    return int(r["comprehension"] or 0) if r else 0


def _has(conn, k: str, pid: int = 1) -> bool:
    return conn.execute("SELECT 1 FROM character_daos WHERE character_type='player' AND character_id=? AND dao_key=? "
                        "AND (practiced=1 OR comprehension>0);", (pid, k)).fetchone() is not None


def awakened(conn, key: str, pid: int = 1) -> bool:
    """Le condizioni di risveglio dei Dao nuovi."""
    from engine.systems import dao_heart, karma, character, state, sects
    from engine.simulation import cultivation
    c = lambda k: _comp(conn, k, pid)  # noqa: E731
    heart = dao_heart.heart(conn)
    if key == "volonta":
        return heart >= 80 and (cultivation.realm_tier(conn, "player", pid) or 1) >= 3
    if key == "annientamento":
        return c("massacro") >= 100 and c("vuoto") >= 25
    if key == "ordine":
        return heart >= 90 and bool(sects.get_membership(conn, pid))
    if key == "ciclo":
        return c("stagioni") >= 50 or all(c(e) >= 25 for e in ("legno", "fuoco", "terra", "metallo", "acqua"))
    if key == "origine":
        return heart >= 90 and sum(1 for r in conn.execute(
            "SELECT comprehension FROM character_daos WHERE character_type='player' AND character_id=?;", (pid,))
            if (r["comprehension"] or 0) >= 1000) >= 2
    if key == "divoramento":
        prof = character.get_profile(conn, "player", pid)
        return bool(prof and (prof["abs_human"] or 0) >= 8)
    if key == "maledizione":
        return karma.get_karma(conn, "player", pid) <= -150
    if key == "morti":
        return c("vita_morte") >= 25 and c("oscurita") >= 25
    if key == "follia":
        return c("massacro") >= 50 and karma.get_karma(conn, "player", pid) <= -100 and state.get_int(conn, "kills_total") >= 30
    return False


def requirement(conn, key: str, pid: int = 1) -> tuple[bool, str]:
    row = BY_KEY[key]
    kind = row[4][0]
    if kind == "scelta":
        return True, ""
    if kind == "derivato":
        need = row[4][1]
        ok = any(_comp(conn, k, pid) >= v for k, v in need.items())
        from engine.systems.dao_techniques import _dao_label
        return ok, " oppure ".join(f"{_dao_label(k)} ≥ {v}" for k, v in need.items())
    return awakened(conn, key, pid), "una condizione del mondo (si risveglia da solo)"


def learn_cost(conn) -> int:
    from engine.simulation import cultivation
    return 300 * (cultivation.realm_tier(conn, "player", 1) or 1)


def _plainname(n: str) -> str:
    t = n.lower()
    for pre in ("dao dell'", "dao della ", "dao dello ", "dao delle ", "dao dei ", "dao del ", "la ", "dao "):
        if t.startswith(pre):
            t = t[len(pre):]
            break
    return t.replace("à", "a").replace("ò", "o").replace("è", "e").replace("ù", "u").replace("ì", "i")


def find(text: str) -> str | None:
    import difflib
    t = (text or "").strip().lower().replace("dao del ", "").replace("dao della ", "").replace("dao dello ", "") \
        .replace("dao dell'", "").replace("dao dei ", "").replace("dao delle ", "").replace("dao ", "")
    for art in ("del ", "della ", "dello ", "dell'", "dei ", "delle ", "il ", "la ", "lo ", "l'"):
        if t.startswith(art):
            t = t[len(art):]
    t = t.replace("à", "a").replace("ò", "o").replace("è", "e").replace("ù", "u").replace("ì", "i")
    names = {k: k for k in list(BY_KEY) + list(FUSED)}
    for k, n, *_r in NEW + FUSIONS:
        names[_plainname(n)] = k
    if t in names:
        return names[t]
    m = difflib.get_close_matches(t, list(names), n=1, cutoff=0.75)
    return names[m[0]] if m else None


def _key_of(word: str) -> str | None:
    """Una parola → chiave di Dao (nuovo, fuso o di base); None per «e», «del», «con»…"""
    w = (word or "").strip().lower().strip(",.;")
    if len(w) < 3 or w in ("del", "della", "dello", "dell", "dei", "delle", "con", "dao", "tra", "fra", "nel"):
        return None
    k = find(w)
    if k:
        return k
    from engine.generators import dao_gen
    plain = w.replace("à", "a").replace("ò", "o")
    for key, name, *_r in dao_gen.DAOS:
        if plain == key or plain == name.lower().split(" ")[-1].replace("à", "a").replace("ò", "o").replace("'", ""):
            return key
        if "'" in name and plain == name.lower().split("'")[-1].replace("à", "a").replace("ò", "o"):
            return key
    return None


# (Agg. 80) i sei elementi di base si possono anche STUDIARE (prima solo scorci o assorbimento): la taratura su
# 200 giorni mostrava la prima fusione al giorno 130 per chi non divora. Costano il doppio di una via nuova.
BASE_STUDY = {"fuoco", "acqua", "terra", "vento", "metallo", "legno"}


def unlock_base(conn, player, key: str) -> str | None:
    from engine.systems import sects
    from engine.systems.dao_techniques import _dao_label
    if key not in BASE_STUDY or _has(conn, key, player.id):
        return None
    cost = 2 * learn_cost(conn)
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return (f"Studiare da zero il {_dao_label(key)} costa {cost} pietre (manuali e maestri); non ti bastano. "
                "Oppure: scorci da chi lo usa meglio di te, reperti, o assorbire chi lo conosce.")
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    grant(conn, key, 1, player.id)
    return (f"☯ Studi le basi del {_dao_label(key)}: ora lo pratichi (−{cost} pietre). "
            f"Allenalo con 'comprehend {key}'.")


def unlock(conn, player, text: str) -> str | None:
    """«comprehend <Dao nuovo>» quando non lo pratichi ancora: se puoi, lo apri (pagando)."""
    key = find(text) or _key_of(text)
    if key in BASE_STUDY:
        return unlock_base(conn, player, key)
    if not key or key not in BY_KEY:
        return None
    from engine.systems import sects, dao_heart
    from engine.generators import dao_gen
    dao_gen.seed_daos(conn)
    row = BY_KEY[key]
    if _has(conn, key, player.id):
        return None
    ok, why = requirement(conn, key, player.id)
    if not ok:
        return f"La via del {row[1].replace('Dao del ', '').replace('Dao della ', '')} ti è ancora chiusa: serve {why}."
    if row[4][0] == "risveglio":
        cost = 0
    else:
        cost = learn_cost(conn)
        if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
            return f"Aprire il {row[1]} costa {cost} pietre spirituali (manuali, maestri, mesi di studio): non ti bastano."
        sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES ('player', ?, ?, 50, 1, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET practiced=1, "
        "comprehension=MAX(character_daos.comprehension, 1);", (player.id, key))
    dao_heart.adjust(conn, 1, "nuova via")
    return (f"☯ Apri il {row[1]} ({LEVEL_IT[row[2]]}). {row[3]}\n"
            f"  ✔ {row[10]} · ✘ {row[11]}" + (f"\n  (costo: {cost} pietre)" if cost else "") +
            f"\nAllenalo con 'comprehend {key}'.")


def check_awakenings(conn, pid: int = 1) -> list[str]:
    """Chiamata con i risvegli dei Dao superiori: i Dao nuovi a risveglio."""
    from engine.generators import dao_gen
    out = []
    for key, row in BY_KEY.items():
        if row[4][0] != "risveglio" or _has(conn, key, pid) or not awakened(conn, key, pid):
            continue
        dao_gen.seed_daos(conn)
        conn.execute(
            "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
            "VALUES ('player', ?, ?, 60, 10, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
            "practiced=1, comprehension=MAX(character_daos.comprehension, 10);", (pid, key))
        out.append(f"✺ RISVEGLIO — {row[1].upper()} ✺\n{row[3]}\n  ✔ {row[10]} · ✘ {row[11]}\n"
                   f"(Allenalo con 'comprehend {key}'.)")
    out += fusion_insights(conn, pid)
    return out


def grant(conn, key: str, comp: int = 10, pid: int = 1) -> bool:
    """Apre un Dao (qualsiasi, anche base o superiore) senza costi. False se lo avevi già."""
    from engine.generators import dao_gen
    if _has(conn, key, pid):
        return False
    dao_gen.seed_daos(conn)
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES ('player', ?, ?, 60, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "practiced=1, comprehension=MAX(character_daos.comprehension, excluded.comprehension);", (pid, key, comp))
    return True


def fusion_insights(conn, pid: int = 1) -> list[str]:
    """Una fusione portata in profondità ti mostra un Dao più alto (acqua+fuoco all'estremo → Yin-Yang)."""
    from engine.systems.dao_techniques import _dao_label
    out = []
    for fkey, steps in INSIGHT.items():
        if not _has(conn, fkey, pid):
            continue
        c = _comp(conn, fkey, pid)
        for th, dao in steps:
            if c >= th and grant(conn, dao, 10, pid):
                out.append(f"✺ INTUIZIONE — {_dao_label(dao).upper()} ✺\nIl {FUSED[fkey][1]} è arrivato a una "
                           f"profondità {grade(c)}: in fondo alle due vie ne vedi una terza, più alta. "
                           f"Si apre il {_dao_label(dao)}. (Allenalo con 'comprehend {dao}'.)")
    return out


# ---------------------------------------------------------------- le fusioni

def grade(comp: int) -> str:
    g = GRADES[0][1]
    for th, name in GRADES:
        if comp >= th:
            g = name
    return g


def is_light(key: str) -> bool:
    return all(v <= 50 for v in FUSED[key][2].values())


def hints(conn) -> set[str]:
    from engine.systems import state
    return set(state.get_json(conn, "dao_fusion_hints", []) or [])


def add_hint(conn, key: str) -> bool:
    from engine.systems import state
    h = hints(conn)
    if key in h:
        return False
    h.add(key)
    state.set_json(conn, "dao_fusion_hints", sorted(h))
    return True


def requirement_of(conn, key: str) -> dict[str, int]:
    """Con un'intuizione (reperto o nemico osservato) le soglie dei componenti scendono di un quinto."""
    comps = FUSED[key][2]
    if key in hints(conn):
        return {c: max(10, int(v * 0.8)) for c, v in comps.items()}
    return dict(comps)


def recipe_status(conn, key: str, pid: int = 1) -> dict:
    k, name, _c, bridges, eff, cost, desc = FUSED[key]
    comps = requirement_of(conn, key)
    missing = [(c, v, _comp(conn, c, pid)) for c, v in comps.items() if _comp(conn, c, pid) < v]
    if key == "via_unica":
        n_fused = sum(1 for f in FUSED if f != "via_unica" and _has(conn, f, pid))
        if n_fused < UNIQUE_NEEDS:
            missing.append(("fusi", UNIQUE_NEEDS, n_fused))
    conflict = next((br for pair, br in CONFLICTS if pair <= set(comps)), None)
    bridged = not conflict or any(_has(conn, b, pid) for b in conflict) or key in hints(conn)
    return {"key": key, "name": name, "comps": comps, "missing": missing, "have": _has(conn, key, pid),
            "risk": 0.0 if bridged else 0.35, "desc": desc}


def fuse(conn, player, args: list[str], rng: random.Random | None = None) -> str:
    """«fusione spada volonta» oppure «fusione tempesta»: crea il Dao fuso."""
    from engine.systems import dao_heart, sects, state
    from engine.generators import dao_gen
    from engine.simulation import cultivation
    from engine.systems.dao_techniques import _dao_label
    rng = rng or random.Random()
    if not args:
        return describe_fusions(conn, player)
    keys = {k for k in (_key_of(w) for w in args) if k}
    key = next((f for f in FUSED if f in keys), None)
    if not key:
        key = next((f for f, row in FUSED.items() if set(row[2]) == keys), None)
    if not key:
        key = next((f for f, row in FUSED.items() if keys and keys <= set(row[2])), None)
    if not key:
        return "Questi Dao non si fondono in nulla che tu possa intravedere. ('fusione' per le ricette possibili)"
    st = recipe_status(conn, key, player.id)
    name = st["name"]
    if st["have"]:
        return f"Hai già il {name}."
    if st["missing"]:
        return f"Per il {name} ti manca: " + ", ".join(
            f"{_dao_label(c) if c != 'fusi' else 'Dao fusi'} {have}/{v}" for c, v, have in st["missing"]) + "."
    heart = dao_heart.heart(conn)
    need_heart = LIGHT_HEART if is_light(key) else FUSE_HEART
    if heart < need_heart:
        return f"Il tuo cuore del Dao ({heart}) è troppo agitato per una fusione: serve almeno {need_heart}."
    tier = cultivation.realm_tier(conn, "player", player.id) or 1
    cost = (300 if is_light(key) else 1500) * tier
    if sects.get_resource(conn, "pietre_spirituali", player.id) < cost:
        return f"Una fusione chiede {cost} pietre spirituali per sostenere il ritiro: non ti bastano."
    sects.grant_resource(conn, "pietre_spirituali", -cost, player.id)
    if rng.random() < st["risk"]:
        lines = dao_heart.adjust(conn, -15, "fusione fallita")
        return (f"Le leggi si respingono: il {name} ti esplode nel dantian prima di nascere. Deviazione del qi "
                f"(cuore del Dao −15). Senza un ponte tra le due vie il rischio era alto.\n" + "\n".join(lines))
    dao_gen.seed_daos(conn)
    start = max(10, sum(_comp(conn, c, player.id) for c in st["comps"]) // 4)
    conn.execute(
        "INSERT INTO character_daos (character_type, character_id, dao_key, affinity, comprehension, practiced) "
        "VALUES ('player', ?, ?, 60, ?, 1) ON CONFLICT(character_type, character_id, dao_key) DO UPDATE SET "
        "practiced=1, comprehension=MAX(character_daos.comprehension, excluded.comprehension);", (player.id, key, start))
    state.grant_title(conn, f"Fondatore del {name}")
    eff = FUSED[key][4]
    return (f"☯ FUSIONE — {name.upper()} ☯\n{FUSED[key][6]} Le vie che conoscevi si piegano l'una verso l'altra e "
            f"diventano una: il {name} nasce con comprensione {start}.\n"
            f"  Effetti (crescono con la comprensione): " + ", ".join(LEVER_IT[k] for k in eff) + "\n"
            f"  Profondità: {grade(start)}. Allenalo con 'comprehend {key}': più va a fondo, più è forte"
            + (", e un giorno ti mostrerà " + " e ".join(_dao_label(d) for _t, d in INSIGHT[key]) if key in INSIGHT else "")
            + ".\n"
            f"  ✧ Nuovo titolo: «Fondatore del {name}»")


def describe_fusions(conn, player) -> str:
    from engine.systems.dao_techniques import _dao_label
    lines = ["☯ LE FUSIONI DEI DAO — 'fusione <ricetta>' (servono i componenti, cuore del Dao ≥ 70 — ≥ 50 per le "
             "leggere — e pietre). Una fusione ha una PROFONDITÀ (leggera → salda → profonda → estrema) che cresce "
             "allenandola, e in fondo apre Dao più alti. Reperti e nemici forti danno intuizioni: soglie −20%, "
             "nessun rischio di conflitto."]
    for key in FUSED:
        st = recipe_status(conn, key, player.id)
        mark = "✔" if st["have"] else ("◆" if not st["missing"] else "·")
        comps = " + ".join(f"{_dao_label(c)} {v}" for c, v in requirement_of(conn, key).items())
        risk = " · conflitto: serve un ponte" if st["risk"] else ""
        extra = " · leggera" if is_light(key) else ""
        if key in hints(conn):
            extra += " · ✧ intuizione"
        if st["have"]:
            extra += f" · profondità {grade(_comp(conn, key, player.id))}"
        nxt = [(t, d) for t, d in INSIGHT.get(key, []) if not _has(conn, d, player.id)]
        if nxt:
            extra += f" · a {nxt[0][0]} → {_dao_label(nxt[0][1])}"
        lines.append(f"  {mark} {st['name']} ({key}) ← {comps}{risk}{extra}")
    from engine.systems import personal_fusion
    for f in personal_fusion.all_(conn):
        lines.append(f"  ✔ {f['name']} ({f['key']}) ← {_dao_label(f['comps'][0])} + {_dao_label(f['comps'][1])} · "
                     f"la TUA via, profondità {grade(_comp(conn, f['key'], player.id))}")
    return "\n".join(lines)


def menu_section(conn, player):
    from engine.systems.menus import act, section
    lines, acts = [], []
    ready = [k for k in FUSED if not recipe_status(conn, k, player.id)["missing"] and not _has(conn, k, player.id)]
    have = [FUSED[k][1] for k in FUSED if _has(conn, k, player.id)]
    if have:
        lines.append("Dao fusi: " + ", ".join(have) + ".")
    if ready:
        lines.append("Puoi fondere: " + ", ".join(FUSED[k][1] for k in ready) + ".")
        acts += [act(f"Fondi: {FUSED[k][1].replace('Dao del ', '').replace('Dao della ', '').replace('Dao dello ', '')}",
                     f"fusione {k}", main=True) for k in ready[:4]]
    open_new = [k for k in BY_KEY if not _has(conn, k, player.id) and BY_KEY[k][4][0] != "risveglio"
                and requirement(conn, k, player.id)[0]]
    if open_new:
        lines.append(f"Vie nuove che puoi aprire ({learn_cost(conn)} pietre l'una): "
                     + ", ".join(BY_KEY[k][1].split(" ", 2)[-1] for k in open_new[:12]) + ("…" if len(open_new) > 12 else "") + ".")
        acts += [act(f"Apri: {BY_KEY[k][1].split(' ', 2)[-1]}", f"comprehend {k}") for k in open_new[:3]]
    lines.append("Ogni Dao ha un vantaggio e un costo; le fusioni chiedono i componenti avanti e un cuore saldo.")
    acts.append(act("🌳 L'albero dei Dao", "albero", main=not ready))
    acts.append(act("Tutte le ricette di fusione", "fusione"))
    acts.append(act("Tutte le vie nuove", "vie"))
    return section("Le leggi nuove e le fusioni", lines, acts, icon="☯", img="scene/fusione")


def describe_new(conn, player) -> str:
    lines = ["☯ LE VIE NUOVE — 'comprehend <nome>' per aprirle (o si risvegliano da sole)"]
    for lv in ("elemental", "narrative", "systemic", "deep", "forbidden"):
        lines.append(f"  — {LEVEL_IT[lv]} —")
        for k, n, lvl, d, unl, *_r, adv, dis in NEW:
            if lvl != lv:
                continue
            mark = "✔" if _has(conn, k, player.id) else ("◆" if requirement(conn, k, player.id)[0] else "·")
            how = {"scelta": "da studiare", "derivato": "derivato", "risveglio": "risveglio"}[unl[0]]
            lines.append(f"  {mark} {n} ({how}): ✔ {adv} · ✘ {dis}")
    return "\n".join(lines)
