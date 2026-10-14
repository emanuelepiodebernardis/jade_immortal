"""
LE ANIME NEGLI OGGETTI (Aggiornamento 61) — i capitoli dei «vasi d'anima».

Lo stesso formato delle altre trame, ma queste NON le sceglie il regista: le apre il vaso
(soul_arcs.py) quando la sua anima è cresciuta abbastanza («arc»: chiave del vaso). L'esito di
ogni capitolo lo legge soul_arcs, che applica le conseguenze sul vaso: l'anima che si risveglia,
che viene rapita, che rinasce in un corpo, che si ribella.

Il genere da cui vengono:
  · il vecchio nell'anello (l'alchimista tradito dal discepolo, che si nutre, insegna, presta la
    sua forza, viene cacciato dal Palazzo delle Anime, rapito, liberato, e alla fine riavrà un corpo);
  · lo spirito di un artefatto (器灵) che si risveglia piano per piano e ricorda chi l'ha forgiato;
  · lo stendardo delle diecimila anime (万魂幡) dei sentieri demoniaci: forza enorme, e il mondo
    giusto contro;
  · il calderone con una fiamma viva che ha fame di fiamme strane;
  · il demone sigillato in una perla che offre patti, e un giorno prova a prendersi il tuo corpo.

Cast speciale: "stato:<chiave>" — un personaggio preciso preparato dal vaso (il traditore…).
"""

from __future__ import annotations

_BRONZO = {"rank": 3, "kinds": ["pillola", "tesoro"]}
_ARGENTO = {"rank": 2, "kinds": ["tesoro", "manuale", "pillola"]}
_ORO = {"rank": 1, "kinds": ["tesoro", "manuale"]}
_RELIQUIA = {"rank": 1, "kinds": ["reliquia", "tesoro"]}

ARCS: list[dict] = [
    # ================================================================== L'ANELLO — 1. IL LEGNO NUTRIANIME
    {
        "key": "anello_legno", "arc": "anello", "title": "Il Legno Nutrianime", "kind": "anima", "weight": 0,
        "tier_min": 1, "cast": {"guardiano": "anziano"},
        "acts": [
            {"title": "Un'anima che si sfilaccia", "focus": "guardiano", "gap": (1, 1),
             "text": ("Di notte l'anello si fa freddo. {Maestro} parla piano, come chi ha paura di consumare le "
                      "parole: «I nuclei mi tengono in vita, ragazzo, ma non mi ricuciono. Mi serve il Legno "
                      "Nutrianime: un albero che cresce solo dove sono morte molte anime.» Ne esiste un ramo, e lo "
                      "custodisce {guardiano}, che non lo cederebbe nemmeno al Cielo."),
             "choices": [
                 {"label": "Sfidi {guardiano} per il ramo",
                  "effects": {"intrigue": {"end": "legno"}}, "command": "duello {guardiano}"},
                 {"label": "Lo compri: tutte le pietre che servono (800)",
                  "effects": {"stones": -800, "text": "{guardiano} conta le pietre due volte, poi ti porge il ramo.",
                              "intrigue": {"end": "comprato"}}},
                 {"label": "Lasci che {maestro} guidi le tue mani: lo rubi senza farti vedere",
                  "check": {"stat": "anima", "dc": 55},
                  "success": {"text": "Per un istante non sei tu a muoverti. Il ramo è nella tua manica prima che "
                                      "{guardiano} apra gli occhi.", "intrigue": {"end": "rubato"}},
                  "failure": {"injury": 1, "text": "{guardiano} ti afferra il polso. Fuggi, a mani vuote.",
                              "intrigue": {"end": "fallito"}}},
             ]},
        ],
        "auto_end": [{"outcome": "fallito", "text": "Il ramo è finito in altre mani."}],
        "outcomes": {"comprato": "Hai comprato il Legno Nutrianime.", "rubato": "Hai rubato il Legno Nutrianime.",
                     "legno_vinto": "Hai strappato il Legno Nutrianime a {guardiano}.",
                     "legno_perso": "{guardiano} ti ha respinto: il ramo resta suo.",
                     "legno_fuga": "Sei fuggito senza il ramo.", "fallito": "Il ramo non è tuo. Per ora."},
    },
    # ================================================================== L'ANELLO — 2. IL DISCEPOLO TRADITORE
    {
        "key": "anello_traditore", "arc": "anello", "title": "Il discepolo che uccise il maestro", "kind": "vendetta",
        "weight": 0, "tier_min": 1, "cast": {"traditore": "stato:vaso_traditore", "spia": "sgherro"},
        "acts": [
            {"title": "Gli occhi nella folla", "focus": "spia", "gap": (1, 1),
             "text": ("Da tre giorni la stessa faccia ti segue: {spia}. {Maestro} trema dentro l'anello: «È uno dei "
                      "cani di {traditore}. Il mio discepolo, quello a cui ho insegnato a tenere un pennello. Ha "
                      "sentito che sono tornato.»"),
             "choices": [
                 {"label": "Prendi la spia e la fai parlare",
                  "check": {"stat": "istinto", "dc": 50},
                  "success": {"text": "{spia} parla: {traditore} usa ancora la tecnica del veleno che rubò al maestro, "
                                      "e ha un punto cieco a sinistra.", "intrigue": {"clue": 1, "branch": "segreto"}},
                  "failure": {"text": "{spia} ti scivola via come acqua.", "intrigue": {}}},
                 {"label": "Lasci che riferisca: vuoi che {traditore} venga da te",
                  "effects": {"heart": 3, "intrigue": {"branch": "attesa"}}},
             ]},
            {"title": "L'allievo e il maestro", "focus": "traditore", "gap": (2, 4),
             "text": ("{traditore} arriva da solo, con le mani dietro la schiena come un vecchio maestro. «Dammi "
                      "l'anello e vivrai. Lui ti ha raccontato la sua storia, immagino. Ti ha detto anche perché "
                      "l'ho fatto?» Nell'anello, {maestro} non risponde."),
             "text_branch": {"segreto": ("{traditore} arriva. Questa volta sai dove guardare: il punto cieco a "
                                         "sinistra, il veleno nella manica. {Maestro} sussurra: «Adesso.»")},
             "choices": [
                 {"label": "Combatti: è la vendetta {di_maestro}",
                  "effects": {"intrigue": {"end": "vendetta"}}, "command": "duello {traditore}"},
                 {"label": "Chiedi a {traditore} la sua versione",
                  "effects": {"intrigue": {"clue": 1, "branch": "verita"},
                              "text": ("«Mi lasciò morire in una grotta per un'erba. Io gli presi il Dao. Siamo pari.» "
                                       "{Maestro} tace a lungo, poi: «È vero. Ma resta un assassino.»")}},
                 {"label": "Fuggi con l'anello", "effects": {"intrigue": {"end": "fuga"}}},
             ]},
            {"title": "Ciò che resta da dire", "focus": "traditore", "gap": (0, 1),
             "text": "Ora sai entrambe le storie. {traditore} aspetta la tua risposta.",
             "choices": [
                 {"label": "Combatti comunque", "effects": {"intrigue": {"end": "vendetta"}},
                  "command": "duello {traditore}"},
                 {"label": "Convinci {maestro} a perdonare: «Non vale la tua anima»",
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"heart": 10, "karma": 10, "text": "Il maestro piange, per la prima volta in diecimila anni.",
                              "intrigue": {"end": "perdono"}},
                  "failure": {"text": "«No.» Il maestro prende il controllo delle tue mani per un istante.",
                              "intrigue": {"end": "vendetta"}}, "command": "duello {traditore}"},
             ]},
        ],
        "auto_end": [{"outcome": "fuga", "text": "{traditore} ha perso le vostre tracce. Per ora."}],
        "outcomes": {"vendetta_vinto": "Hai vendicato {maestro}: {traditore} non insegnerà più a nessuno.",
                     "vendetta_perso": "{traditore} ti ha sconfitto; per poco l'anello non è suo.",
                     "vendetta_fuga": "Sei fuggito da {traditore}.", "fuga": "Hai rimandato la resa dei conti.",
                     "perdono": "Maestro e discepolo si sono lasciati andare: nessuno dei due è più prigioniero."},
    },
    # ================================================================== L'ANELLO — 3. IL PALAZZO DELLE ANIME
    {
        "key": "anello_palazzo", "arc": "anello", "title": "Il Palazzo delle Anime", "kind": "salvataggio",
        "weight": 0, "tier_min": 1, "cast": {"cacciatore": "anziano", "custode": "anziano"},
        "indagine": "istinto", "need": 1, "reveal_act": 1,
        "indizi": ["Le catene che hanno usato sono incise col sigillo del Palazzo delle Anime.",
                   "Il Palazzo tiene le anime rapite sulla Montagna delle Anime Perdute, sotto una formazione.",
                   "La formazione si apre solo quando {custode} cambia la guardia, all'ora del topo."],
        "acts": [
            {"title": "La mano nel buio", "focus": "cacciatore", "gap": (1, 1),
             "text": ("Ti svegli con un gelo nel dito. Una mano senza peso è entrata nell'anello e ne ha strappato "
                      "{Maestro} come si strappa un'erba. Sulla soglia, {cacciatore} avvolge una catena luminosa: "
                      "dentro, un grido che conosci. «Il Palazzo delle Anime ringrazia.»"),
             "choices": [
                 {"label": "Lo insegui subito e combatti", "effects": {"intrigue": {}}, "command": "duello {cacciatore}"},
                 {"label": "Segui le tracce delle catene, senza farti vedere",
                  "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "Le catene lasciano una scia di brina che porta a nord.", "intrigue": {"clue": 1}},
                  "failure": {"text": "Perdi la scia al primo fiume.", "intrigue": {}}},
             ]},
            {"title": "La Montagna delle Anime Perdute", "focus": "custode", "gap": (2, 4),
             "text": ("Sulla montagna il vento è fatto di voci. In mezzo a mille lanterne di anime, una brilla più "
                      "debole delle altre: {maestro}. Davanti alla formazione, {custode}."),
             "choices": [
                 {"label": "Assalti la formazione e affronti {custode}",
                  "effects": {"intrigue": {"end": "assalto"}}, "command": "duello {custode}"},
                 {"label": "Entri al cambio della guardia, quando la formazione si apre",
                  "need_clues": 2, "check": {"stat": "istinto", "dc": 50},
                  "success": {"text": "Passi tra due battiti di formazione. Prendi la lanterna e corri.",
                              "intrigue": {"end": "furtivo"}},
                  "failure": {"text": "La formazione si chiude su di te: devi combattere.",
                              "intrigue": {"end": "assalto"}}, "command": "duello {custode}"},
                 {"label": "Tratti: duemila pietre per un'anima",
                  "effects": {"stones": -2000, "text": "{custode} ride, ma prende le pietre.",
                              "intrigue": {"end": "riscatto"}}},
                 {"label": "Te ne vai: non puoi salvarlo", "effects": {"heart": -10, "intrigue": {"end": "abbandonato"}}},
             ]},
        ],
        "auto_end": [{"outcome": "rimandato", "text": "Il Palazzo ha spostato le lanterne. Dovrai cercarle di nuovo."}],
        "outcomes": {"assalto_vinto": "Hai strappato {maestro} al Palazzo delle Anime.",
                     "assalto_perso": "{custode} ti ha respinto dalla montagna.", "assalto_fuga": "Sei fuggito dalla montagna.",
                     "furtivo": "Hai liberato {maestro} senza che il Palazzo se ne accorgesse.",
                     "riscatto": "Hai ricomprato l'anima {di_maestro}.", "abbandonato": "Hai lasciato {maestro} al Palazzo.",
                     "rimandato": "La prigione {di_maestro} è di nuovo nascosta."},
    },
    # ================================================================== L'ANELLO — 4. UN CORPO NUOVO
    {
        "key": "anello_corpo", "arc": "anello", "title": "Un corpo per un'anima antica", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {},
        "acts": [
            {"title": "La richiesta", "gap": (1, 1),
             "text": ("«Sono forte abbastanza», dice {maestro}, e per la prima volta la sua voce ha un peso. «Un'anima "
                      "senza carne è una candela al vento. Forgiami un corpo, ragazzo, e ti restituirò tutto quello "
                      "che mi hai dato.»"),
             "choices": [
                 {"label": "Forgi un corpo di giada (3000 pietre)",
                  "effects": {"stones": -3000, "intrigue": {"branch": "giada"},
                              "text": "Giorni di fuoco e giada. Il corpo ha gli occhi chiusi, e aspetta."}},
                 {"label": "Gli offri la salma di un nemico forte",
                  "effects": {"karma": -5, "intrigue": {"branch": "salma"},
                              "text": "{Maestro} esita: «Un corpo che ha già un passato…» Poi accetta."}},
                 {"label": "Gli chiedi di aspettare ancora", "effects": {"intrigue": {"end": "attesa"}}},
             ]},
            {"title": "La notte della rinascita", "gap": (1, 2),
             "text": ("L'anima {di_maestro} scivola nel corpo nuovo. Per tutta la notte il corpo trema. Verso l'alba "
                      "senti una pressione strana dietro gli occhi: qualcosa ti guarda da dentro."),
             "choices": [
                 {"label": "Vegli su di lui fino all'alba", "check": {"stat": "anima", "dc": 65},
                  "success": {"text": "Lo tieni per mano finché il tremito passa. Nessuna ombra ti tocca.",
                              "intrigue": {"branch": "fedele"}},
                  "failure": {"text": "Ti addormenti. Nel sogno, una mano cerca la porta della tua anima.",
                              "intrigue": {"branch": "tentazione"}}},
                 {"label": "Ti fidi di lui: dormi", "effects": {"intrigue": {"branch": "fiducia"}}},
             ]},
            {"title": "L'alba", "auto": True,
             "text": "Il sole sorge. Uno dei due apre gli occhi per primo.",
             "endings": [
                 {"need_branch": "tentazione", "outcome": "tradimento",
                  "effects": {"heart": -5, "injury": 2},
                  "text": ("Il corpo nuovo era debole, il tuo era forte. Per un attimo {maestro} ha provato a prendersi "
                           "il tuo. Lo respingi; la sua anima si spezza, e nella tua restano solo i suoi ricordi.")},
                 {"outcome": "rinato", "effects": {"heart": 8},
                  "text": ("{Maestro} apre gli occhi nel corpo nuovo, si guarda le mani e ride come un ragazzo. "
                           "«Diecimila anni. E un ragazzo che non sapeva nemmeno tenere un nucleo.»")},
             ]},
        ],
        "auto_end": [{"outcome": "attesa", "text": "Il corpo non è stato forgiato. {Maestro} aspetta."}],
        "outcomes": {"attesa": "{Maestro} aspetterà ancora un corpo."},
    },
    # ================================================================== LA PAGODA — 1. IL PRIMO RICORDO
    {
        "key": "pagoda_ricordo", "arc": "pagoda", "title": "Il primo ricordo della pagoda", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {"guardiano": "spettro"},
        "acts": [
            {"title": "Il terzo piano", "focus": "guardiano", "gap": (1, 1),
             "text": ("Al terzo piano della pagoda c'è una porta che prima non c'era. {Spirito} la guarda con occhi "
                      "da bambina: «Lì dietro c'è una cosa che ho dimenticato. Ma c'è anche lui.» Davanti alla porta, "
                      "{guardiano}: l'eco di un vecchio prigioniero della pagoda, che non sa di essere morto."),
             "choices": [
                 {"label": "Affronti il prigioniero", "effects": {"intrigue": {"end": "porta"}},
                  "command": "duello {guardiano}"},
                 {"label": "Gli dici la verità: è morto da mille anni", "check": {"stat": "anima", "dc": 55},
                  "success": {"karma": 8, "text": "L'eco si guarda le mani trasparenti, sorride, e si dissolve.",
                              "intrigue": {"end": "liberato"}},
                  "failure": {"text": "«Bugiardo!» L'eco si scaglia su di te.", "intrigue": {"end": "porta"}},
                  "command": "duello {guardiano}"},
             ]},
        ],
        "auto_end": [{"outcome": "chiusa", "text": "La porta del terzo piano si è richiusa."}],
        "outcomes": {"porta_vinto": "Hai aperto la porta del terzo piano.", "liberato": "Hai liberato l'eco del prigioniero.",
                     "porta_perso": "Il prigioniero della pagoda ti ha respinto.", "porta_fuga": "Sei fuggito dal terzo piano.",
                     "chiusa": "La porta del terzo piano si è richiusa."},
    },
    # ================================================================== LA PAGODA — 2. I PADRONI DI UN TEMPO
    {
        "key": "pagoda_padroni", "arc": "pagoda", "title": "I padroni di un tempo", "kind": "intrigo",
        "weight": 0, "tier_min": 1, "cast": {"erede": "anziano"},
        "acts": [
            {"title": "La setta che forgiò la pagoda", "focus": "erede", "gap": (1, 1),
             "text": ("{erede} si presenta con un rotolo antico: lo schema della tua pagoda, con il sigillo della sua "
                      "setta. «Fu forgiata dai nostri antenati. Restituiscila.» {Spirito}, dentro, si nasconde: "
                      "«Quelli mi chiudevano al buio per anni. Non voglio tornare.»"),
             "choices": [
                 {"label": "Rifiuti: la pagoda ha scelto te", "effects": {"intrigue": {"end": "rifiuto"}},
                  "command": "duello {erede}"},
                 {"label": "Chiedi a {spirito} di decidere", "check": {"stat": "anima", "dc": 45},
                  "success": {"heart": 6, "text": ("{Spirito} esce, per la prima volta, e si mette davanti a te. "
                                                   "{erede} abbassa lo sguardo: lo spirito ha scelto."),
                              "intrigue": {"end": "scelta"}},
                  "failure": {"text": "{Spirito} non riesce a parlare. {erede} prende il silenzio per un sì.",
                              "intrigue": {"end": "rifiuto"}}, "command": "duello {erede}"},
                 {"label": "Restituisci la pagoda", "effects": {"karma": 10, "fame": 5, "intrigue": {"end": "restituita"}}},
             ]},
        ],
        "auto_end": [{"outcome": "rimandato", "text": "{erede} tornerà."}],
        "outcomes": {"rifiuto_vinto": "Hai difeso la pagoda dai suoi vecchi padroni.",
                     "rifiuto_perso": "{erede} ti ha sconfitto, ma lo spirito non l'ha seguito.",
                     "rifiuto_fuga": "Sei fuggito con la pagoda.", "scelta": "Lo spirito della pagoda ha scelto te.",
                     "restituita": "Hai restituito la pagoda alla setta che la forgiò.", "rimandato": "{erede} tornerà."},
    },
    # ================================================================== LA PAGODA — 3. IL NOME DELLA PAGODA
    {
        "key": "pagoda_nome", "arc": "pagoda", "title": "Il nome della pagoda", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {},
        "acts": [
            {"title": "Il nono piano", "gap": (1, 1),
             "text": ("Il nono piano si apre. Dentro non c'è un tesoro: c'è un nome, inciso al contrario sul soffitto. "
                      "{Spirito} lo legge e cresce davanti ai tuoi occhi, da bambina a donna. «Ora ricordo tutto. "
                      "Posso restare con te, legata alla pagoda per sempre. Oppure puoi lasciarmi andare.»"),
             "choices": [
                 {"label": "Le chiedi di restare: la pagoda diventa il tuo tesoro vitale",
                  "effects": {"intrigue": {"end": "legata"}}},
                 {"label": "La lasci libera", "effects": {"karma": 20, "heart": 10, "intrigue": {"end": "libera"}}},
             ]},
        ],
        "auto_end": [{"outcome": "legata", "text": "Lo spirito resta, senza che tu abbia chiesto nulla."}],
        "outcomes": {"legata": "Lo spirito della pagoda è legato a te per sempre.",
                     "libera": "Hai lasciato libero lo spirito della pagoda: ti ha lasciato in dono il suo ultimo piano."},
    },
    # ================================================================== LO STENDARDO — 1. LE VOCI
    {
        "key": "stendardo_voci", "arc": "stendardo", "title": "Le voci nello stendardo", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {},
        "acts": [
            {"title": "Una bambina tra le anime", "gap": (1, 1),
             "text": ("Tra le anime che lo stendardo ha bevuto ce n'è una che non grida: una bambina, finita lì per "
                      "errore con il bandito che l'aveva rapita. «Voglio andare dalla mamma.» Le altre anime ridono."),
             "choices": [
                 {"label": "La liberi", "effects": {"karma": 10, "heart": 5, "intrigue": {"end": "liberata"}}},
                 {"label": "Liberi tutte le anime innocenti", "effects": {"karma": 20, "heart": 8,
                                                                        "intrigue": {"end": "innocenti"}}},
                 {"label": "Lo stendardo non restituisce nulla", "effects": {"karma": -15, "heart": -5,
                                                                            "intrigue": {"end": "tenuta"}}},
             ]},
        ],
        "auto_end": [{"outcome": "tenuta", "text": "Hai lasciato che la voce si spegnesse da sola."}],
        "outcomes": {"liberata": "Hai liberato la bambina dallo stendardo.",
                     "innocenti": "Hai liberato tutte le anime innocenti: lo stendardo è più leggero, e tu anche.",
                     "tenuta": "Lo stendardo non restituisce nulla."},
    },
    # ================================================================== LO STENDARDO — 2. I GIUSTI
    {
        "key": "stendardo_giusti", "arc": "stendardo", "title": "I giusti ti cercano", "kind": "caccia",
        "weight": 0, "tier_min": 1, "cast": {"giustiziere": "anziano"},
        "acts": [
            {"title": "Il sentiero ortodosso", "focus": "giustiziere", "gap": (1, 1),
             "text": ("{giustiziere}, della Lega dei Giusti, ti sbarra la strada con la spada sguainata. «Sento "
                      "piangere le anime che porti con te. Brucia lo stendardo, o brucerò te.»"),
             "choices": [
                 {"label": "Combatti", "effects": {"intrigue": {"end": "scontro"}}, "command": "duello {giustiziere}"},
                 {"label": "Liberi metà delle anime davanti a lui", "effects": {"karma": 15,
                                                                               "intrigue": {"end": "tregua"}}},
                 {"label": "Lo inganni: nascondi lo stendardo", "check": {"stat": "istinto", "dc": 60},
                  "success": {"text": "{giustiziere} non sente più nulla e ti lascia passare, perplesso.",
                              "intrigue": {"end": "nascosto"}},
                  "failure": {"text": "«Le anime non mentono.»", "intrigue": {"end": "scontro"}},
                  "command": "duello {giustiziere}"},
             ]},
        ],
        "auto_end": [{"outcome": "nascosto", "text": "{giustiziere} ha perso le tue tracce."}],
        "outcomes": {"scontro_vinto": "Hai abbattuto {giustiziere}: la Lega dei Giusti ricorderà il tuo nome.",
                     "scontro_perso": "{giustiziere} ti ha sconfitto e ha strappato metà dello stendardo.",
                     "scontro_fuga": "Sei fuggito da {giustiziere}.", "tregua": "Hai comprato la tregua con metà delle anime.",
                     "nascosto": "Hai nascosto lo stendardo ai giusti."},
    },
    # ================================================================== LO STENDARDO — 3. LA RIVOLTA
    {
        "key": "stendardo_rivolta", "arc": "stendardo", "title": "La rivolta delle anime", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {"capo": "spettro"},
        "acts": [
            {"title": "Diecimila voci", "focus": "capo", "gap": (1, 1),
             "text": ("Lo stendardo si gonfia senza vento. Le anime si sono unite attorno alla più forte: {capo}, che "
                      "fu un tuo nemico da vivo. «Siamo in troppi, padrone. Stanotte siamo noi a tenere te.»"),
             "choices": [
                 {"label": "Le domini con la forza dell'anima", "check": {"stat": "anima", "dc": 70},
                  "success": {"text": "Pianti lo stendardo a terra e lo stringi come una gola. Le voci tacciono.",
                              "intrigue": {"end": "dominate"}},
                  "failure": {"injury": 3, "text": "Le anime ti trascinano giù. Devi abbattere {capo}.",
                              "intrigue": {"end": "battaglia"}}, "command": "duello {capo}"},
                 {"label": "Abbatti {capo}, e le altre si piegheranno",
                  "effects": {"intrigue": {"end": "battaglia"}}, "command": "duello {capo}"},
                 {"label": "Le liberi tutte: lo stendardo torna un pezzo di stoffa",
                  "effects": {"karma": 40, "heart": 15, "intrigue": {"end": "liberate"}}},
             ]},
        ],
        "auto_end": [{"outcome": "dominate", "text": "La rivolta si spegne da sola, per stanchezza."}],
        "outcomes": {"dominate": "Hai piegato le anime: lo stendardo diventa lo Stendardo del Re delle Anime.",
                     "battaglia_vinto": "Hai abbattuto {capo}: lo stendardo diventa lo Stendardo del Re delle Anime.",
                     "battaglia_perso": "Le anime hanno vinto: metà sono fuggite.",
                     "battaglia_fuga": "Hai lasciato cadere lo stendardo e sei fuggito; metà delle anime sono scappate.",
                     "liberate": "Hai liberato diecimila anime. Il mondo, per una volta, ti benedice."},
    },
    # ================================================================== IL CALDERONE — 1. LA FIAMMA HA FAME
    {
        "key": "calderone_fame", "arc": "calderone", "title": "La fiamma ha fame", "kind": "caccia",
        "weight": 0, "tier_min": 1, "cast": {"bestia": "anziano"},
        "acts": [
            {"title": "Una fiamma strana", "focus": "bestia", "gap": (1, 1),
             "text": ("La fiamma del calderone si allunga verso est come un cane da caccia. {Spirito}: «Là c'è una "
                      "Fiamma Strana, nata dal cuore di un vulcano. Se la mangio, i tuoi forni non sbaglieranno più.» "
                      "La fiamma però ha già un padrone: {bestia}."),
             "choices": [
                 {"label": "Strappi la fiamma a {bestia}", "effects": {"intrigue": {"end": "fiamma"}},
                  "command": "duello {bestia}"},
                 {"label": "Lasci che sia il calderone a chiamarla", "check": {"stat": "qi", "dc": 55},
                  "success": {"text": "La Fiamma Strana sente il richiamo e salta nel calderone da sola.",
                              "intrigue": {"end": "richiamo"}},
                  "failure": {"injury": 2, "text": "La fiamma ti morde le mani e torna da {bestia}.",
                              "intrigue": {"end": "fallito"}}},
             ]},
        ],
        "auto_end": [{"outcome": "fallito", "text": "La Fiamma Strana si è spenta prima che arrivassi."}],
        "outcomes": {"fiamma_vinto": "Il calderone ha divorato la Fiamma Strana di {bestia}.",
                     "richiamo": "La Fiamma Strana è venuta da sola.", "fiamma_perso": "{bestia} ha tenuto la sua fiamma.",
                     "fiamma_fuga": "Sei fuggito senza la fiamma.", "fallito": "Il calderone resta affamato."},
    },
    # ================================================================== IL CALDERONE — 2. IL VECCHIO ALCHIMISTA
    {
        "key": "calderone_maestro", "arc": "calderone", "title": "L'alchimista che forgiò il calderone", "kind": "prova",
        "weight": 0, "tier_min": 1, "cast": {},
        "acts": [
            {"title": "L'esame del calderone", "gap": (1, 1),
             "text": ("Dentro la fiamma compare il volto di un vecchio: l'alchimista che forgiò il calderone, o ciò "
                      "che di lui è rimasto. «Il mio calderone non serve a chi non sa cucinare. Raffina una pillola "
                      "con me, adesso, senza pietre e senza erbe: solo fiamma e volontà.»"),
             "choices": [
                 {"label": "Raffini con lui", "check": {"stat": "qi", "dc": 60},
                  "success": {"text": "Nove giri di fiamma. La pillola esce con nove venature. Il vecchio annuisce.",
                              "intrigue": {"end": "superato"}},
                  "failure": {"text": "La pillola esplode. «Torna quando saprai ascoltare il fuoco.»",
                              "intrigue": {"end": "bocciato"}}},
                 {"label": "Gli chiedi di insegnarti prima", "effects": {"heart": 4, "intrigue": {"end": "allievo"}}},
             ]},
        ],
        "auto_end": [{"outcome": "bocciato", "text": "Il volto nella fiamma si è stancato di aspettare."}],
        "outcomes": {"superato": "Hai superato l'esame del vecchio alchimista.",
                     "allievo": "Il vecchio alchimista ti ha preso come allievo, anche se brontola.",
                     "bocciato": "Il vecchio alchimista ti ha bocciato. Per ora."},
    },
    # ================================================================== IL CALDERONE — 3. LA FIAMMA CELESTE
    {
        "key": "calderone_fiamma", "arc": "calderone", "title": "La fiamma celeste", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {"rivale": "rivale"},
        "acts": [
            {"title": "Il fuoco che cade dal cielo", "focus": "rivale", "gap": (1, 1),
             "text": ("Una notte cade dal cielo una scintilla bianca: una Fiamma Celeste. Il calderone urla di fame. "
                      "Anche {rivale} l'ha vista, e corre."),
             "choices": [
                 {"label": "Arrivi prima tu, e combatti chi ti segue", "effects": {"intrigue": {"end": "celeste"}},
                  "command": "duello {rivale}"},
                 {"label": "Lasci che il calderone la ingoi in volo", "check": {"stat": "qi", "dc": 70},
                  "success": {"text": "Il calderone salta dalle tue mani e inghiotte la scintilla in volo.",
                              "intrigue": {"end": "ingoiata"}},
                  "failure": {"text": "Manchi la scintilla. {rivale} è già lì.", "intrigue": {"end": "celeste"}},
                  "command": "duello {rivale}"},
             ]},
        ],
        "auto_end": [{"outcome": "persa", "text": "La Fiamma Celeste è finita a qualcun altro."}],
        "outcomes": {"celeste_vinto": "Il calderone ha divorato la Fiamma Celeste.", "ingoiata": "Il calderone ha divorato la Fiamma Celeste.",
                     "celeste_perso": "{rivale} ti ha strappato la Fiamma Celeste.", "celeste_fuga": "Hai lasciato la fiamma a {rivale}.",
                     "persa": "La Fiamma Celeste è finita a qualcun altro."},
    },
    # ================================================================== LA PERLA — 1. LA VOCE GENTILE
    {
        "key": "perla_voce", "arc": "perla", "title": "La voce gentile nella perla", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {},
        "acts": [
            {"title": "Il primo regalo", "gap": (1, 1),
             "text": ("{Spirito} ha una voce gentile, e sa tutto. Ti ha già indicato due erbe e un nemico nascosto. "
                      "Stanotte ti chiede una cosa sola: «Toglimi uno dei nove sigilli. Solo uno. Ti farò un regalo.»"),
             "choices": [
                 {"label": "Togli un sigillo", "effects": {"intrigue": {"end": "sigillo"}}},
                 {"label": "Prima chiedi chi l'ha sigillato, e perché", "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": ("Ride. «Un monaco con paura del buio.» Ma sotto la risata senti un nome: "
                                       "{Spirito} fu sigillato per aver divorato una città."),
                              "intrigue": {"end": "verita"}},
                  "failure": {"text": "«Un malinteso, caro. Solo un malinteso.»", "intrigue": {"end": "sigillo"}}},
                 {"label": "Rifiuti", "effects": {"heart": 4, "intrigue": {"end": "rifiuto"}}},
             ]},
        ],
        "auto_end": [{"outcome": "rifiuto", "text": "{Spirito} tace, offeso. Per ora."}],
        "outcomes": {"sigillo": "Hai tolto il primo sigillo della perla.", "verita": "Hai scoperto chi c'è nella perla.",
                     "rifiuto": "Hai lasciato i sigilli dove sono."},
    },
    # ================================================================== LA PERLA — 2. IL PREZZO
    {
        "key": "perla_prezzo", "arc": "perla", "title": "Il prezzo dei patti", "kind": "intrigo",
        "weight": 0, "tier_min": 1, "cast": {"monaco": "anziano"},
        "acts": [
            {"title": "Il monaco senza sonno", "focus": "monaco", "gap": (1, 1),
             "text": ("{monaco}, un monaco con gli occhi cerchiati di chi non dorme da secoli, ti ferma sul ponte. "
                      "«Mio maestro sigillò quella perla. Ogni patto che fai scioglie un sigillo. Quando cadrà "
                      "l'ultimo, lui avrà il tuo corpo e la tua città. Dammela, e la porterò al tempio.»"),
             "choices": [
                 {"label": "Gli dai la perla", "effects": {"karma": 15, "intrigue": {"end": "consegnata"}}},
                 {"label": "Gli chiedi di insegnarti a rinforzare i sigilli", "check": {"stat": "anima", "dc": 55},
                  "success": {"text": "Il monaco ti insegna il Sutra del Sigillo: ora puoi rifiutare la perla quando vuoi.",
                              "intrigue": {"end": "sutra"}},
                  "failure": {"text": "Non riesci a imparare. Il monaco se ne va scuotendo la testa.",
                              "intrigue": {"end": "tenuta"}}},
                 {"label": "Lo cacci: la perla è tua", "effects": {"intrigue": {"end": "cacciato"}},
                  "command": "duello {monaco}"},
             ]},
        ],
        "auto_end": [{"outcome": "tenuta", "text": "Il monaco non è più tornato."}],
        "outcomes": {"consegnata": "Hai consegnato la perla al tempio.", "sutra": "Hai imparato il Sutra del Sigillo.",
                     "tenuta": "Hai tenuto la perla.", "cacciato_vinto": "Hai cacciato il monaco. La perla ride.",
                     "cacciato_perso": "Il monaco ti ha battuto, ma non ha preso la perla: «Te ne pentirai.»",
                     "cacciato_fuga": "Sei fuggito dal monaco."},
    },
    # ================================================================== LA PERLA — 3. LA POSSESSIONE
    {
        "key": "perla_possessione", "arc": "perla", "title": "La notte in cui la perla si aprì", "kind": "anima",
        "weight": 0, "tier_min": 1, "cast": {},
        "acts": [
            {"title": "Il mare dentro la tua testa", "gap": (1, 1),
             "text": ("Cade l'ultimo sigillo. {Spirito} non ha più una voce gentile: entra nel tuo mare della coscienza "
                      "come una marea nera. «Grazie del corpo.»"),
             "choices": [
                 {"label": "Combatti nel mare della coscienza", "check": {"stat": "anima", "dc": 70},
                  "success": {"text": "Lo afferri per la gola, dentro di te, e lo divori pezzo per pezzo.",
                              "intrigue": {"end": "divorato"}},
                  "failure": {"injury": 3, "heart": -10, "text": "Ti strappa via mezzo mare. Riesci solo a ricacciarlo nella perla.",
                              "intrigue": {"end": "respinto"}}},
                 {"label": "Recita il Sutra del Sigillo", "need_branch": "sutra",
                  "effects": {"intrigue": {"end": "risigillato"}}},
                 {"label": "Gli offri un patto: metà del corpo, metà della forza",
                  "effects": {"karma": -20, "intrigue": {"end": "simbiosi"}}},
             ]},
        ],
        "auto_end": [{"outcome": "respinto", "text": "La marea nera si ritira da sola."}],
        "outcomes": {"divorato": "Hai divorato il demone della perla: i suoi diecimila anni sono tuoi.",
                     "respinto": "Hai ricacciato il demone nella perla, a caro prezzo.",
                     "risigillato": "Hai risigillato la perla per sempre.",
                     "simbiosi": "Tu e il demone della perla ora condividete un corpo."},
    },
]


# Una scelta con prova e duello: il duello parte solo se la prova fallisce (il comando va nel ramo
# «failure», altrimenti partirebbe anche dopo un successo).
for _t in ARCS:
    for _a in _t["acts"]:
        for _c in _a.get("choices", []):
            if _c.get("check") and _c.get("command"):
                _c.setdefault("failure", {})["command"] = _c.pop("command")
