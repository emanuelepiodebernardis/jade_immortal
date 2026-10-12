"""
SAGHE — incontri a più atti (2-3 scene concatenate con 'then').

Ogni atto ha le sue scelte; l'ultimo decide anche la sorte di chi hai davanti:
UCCIDERE ('npc_dies') lascia vendicatori, RISPARMIARE ('spared') crea debiti di vita
(vedi feuds.py). I premi escono dal generatore comune ('prize', vedi rewards.py).
"""

from __future__ import annotations

_BANDIT = {"archetype": "vagabondo", "tier_offset": 0, "traits": {"honor": 20, "pride": 75, "greed": 85}}
_YOUNG_MASTER = {"archetype": "discepolo", "tier_offset": 0, "traits": {"pride": 95, "honor": 35}}
_DEMONIC = {"archetype": "eremita", "tier_offset": 1, "traits": {"honor": 10, "compassion": 5, "ambition": 90}}

SAGAS: list[dict] = [
    # ------------------------------------------------------------------ 1
    {
        "key": "saga_sposa", "title": "La sposa rapita — I. Il palanchino vuoto", "weight": 6, "repeat_gap": 3600,
        "req": {"types": ["city"]}, "spawn": _BANDIT,
        "text": ("Fuori dalle mura di {luogo} trovi un palanchino rosso rovesciato nel fango. Le portantine "
                 "sono spezzate, i servitori legati agli alberi. Una serva in lacrime ti afferra la manica: "
                 "«La giovane padrona! L'hanno presa i Lupi del Passo, il giorno stesso delle nozze! Li guida "
                 "{npc}: dice che la riporterà solo in cambio del peso della sposa in pietre spirituali.»"),
        "choices": [
            {"label": "Segui le tracce dei rapitori nella boscaglia",
             "check": {"stat": "istinto", "dc": 55},
             "success": {"text": "Rami spezzati, un nastro rosso impigliato: le tracce portano a una gola nascosta.",
                         "then": {
                             "key": "saga_sposa_2", "title": "La sposa rapita — II. L'accampamento",
                             "text": ("Nella gola fumano i fuochi dei Lupi del Passo. La sposa è legata a un palo; "
                                      "{npc} conta le pietre di un altro riscatto e ride. Le sentinelle sono "
                                      "distratte dal vino."),
                             "choices": [
                                 {"label": "Ti mostri e lo sfidi davanti ai suoi uomini",
                                  "effects": {"fame": 4, "text": "«Un eroe!» ride {npc}. «Vediamo quanto pesa il tuo coraggio.»"},
                                  "command": "duello {npc}"},
                                 {"label": "Liberi la sposa in silenzio, col favore della notte",
                                  "check": {"stat": "istinto", "dc": 65},
                                  "success": {"karma": 30, "fame": 6, "relation": -20,
                                              "prize": {"rank": 2, "kinds": ["pillola", "tesoro"]},
                                              "text": ("Tagli le corde, la sposa ti segue senza un respiro. All'alba, "
                                                       "la sua famiglia ti accoglie come un figlio e apre il forziere.")},
                                  "failure": {"injury": 3, "text": "Un ramo secco si spezza: {npc} ti ha visto.",
                                              "command": "duello {npc}"}},
                                 {"label": "Tratti: paghi il riscatto e ti fai promettere che lasceranno la strada",
                                  "check": {"stat": "anima", "dc": 60},
                                  "success": {"stones": -150, "karma": 15, "relation": 25, "spared": True,
                                              "text": ("{npc} pesa le pietre, poi te. «Uno che paga invece di uccidere. "
                                                       "Non ne ho mai visti.» Libera la sposa e si toglie la fascia del clan.")},
                                  "failure": {"stones": -150, "text": "{npc} prende le pietre… e chiede il doppio. Si combatte.",
                                              "command": "duello {npc}"}},
                             ]}},
             "failure": {"text": "Le tracce si perdono nel torrente. Torni in città a mani vuote; la serva piange."}},
            {"label": "Corri in città ad avvisare la famiglia della sposa",
             "effects": {"karma": 10, "fame": 2, "stones": 30,
                         "text": "La famiglia ti ringrazia e assolda mercenari. Ti lasciano una borsa per il disturbo."}},
            {"label": "Non è affar tuo", "effects": {"karma": -15}},
        ],
    },
    # ------------------------------------------------------------------ 2
    {
        "key": "saga_fossa", "title": "La Fossa delle Mille Ossa — I. L'invito", "weight": 6, "repeat_gap": 3000,
        "req": {"types": ["city"], "tier_min": 2},
        "text": ("Un uomo dal viso incipriato ti ferma in un vicolo di {luogo}. «Ho visto come cammini. Sotto la "
                 "taverna del Gatto Nero c'è la Fossa: tre combattimenti, nessuna regola, nessun anziano a "
                 "fermarli. Chi vince tutto porta via il montepremi… e la sua vita.»"),
        "choices": [
            {"label": "Scendi nella Fossa",
             "check": {"stat": "potenza", "dc": 55},
             "success": {"fame": 3, "stones": 60, "text": "Il primo avversario, un gigante dei monti, cade al terzo scambio.",
                         "then": {
                             "key": "saga_fossa_2", "title": "La Fossa delle Mille Ossa — II. Il campione",
                             "spawn": {"archetype": "guardia", "tier_offset": 1, "traits": {"pride": 90}},
                             "respawn": True,
                             "text": ("La folla urla. Nel secondo girone ti aspetta il campione della Fossa, {npc}, "
                                      "imbattuto da trenta notti. Si scrocchia il collo e sputa sabbia: «Arrenditi "
                                      "ora e uscirai camminando.»"),
                             "choices": [
                                 {"label": "Combatti fino in fondo (duello a turni)", "command": "duello {npc}",
                                  "effects": {"text": "La sabbia beve il primo sangue."}},
                                 {"label": "Combatti di astuzia: lo stanchi e colpisci quando sbaglia",
                                  "check": {"stat": "istinto", "dc": 70},
                                  "success": {"fame": 10, "prize": {"rank": 1, "kinds": ["manuale", "pillola", "nucleo"]},
                                              "spared": True,
                                              "text": ("{npc} crolla in ginocchio, esausto. Gli porgi la mano invece del "
                                                       "colpo finale: la Fossa ammutolisce, poi esplode.")},
                                  "failure": {"injury": 5, "stones": 40,
                                              "text": "Ti legge come un libro aperto. Esci sulle tue gambe, a malapena."}},
                                 {"label": "Ti ritiri col premio del primo girone", "effects": {"fame": -2,
                                  "text": "Fischi e ossa di pollo ti seguono fino alla scala."}},
                             ]}},
             "failure": {"injury": 4, "stones": 20, "text": "Il gigante dei monti è più duro del previsto. Un premio di consolazione e molte ossa doloranti."}},
            {"label": "Scommetti sugli altri invece di combattere",
             "check": {"stat": "fortuna", "dc": 55},
             "success": {"stones": 120, "text": "Il tuo campione vince contro ogni pronostico."},
             "failure": {"stones": -60, "text": "Il tuo campione inciampa nella sabbia. Addio pietre."}},
            {"label": "Rifiuti: i coltivatori non combattono per divertire i mortali",
             "effects": {"karma": 5}},
        ],
    },
    # ------------------------------------------------------------------ 3
    {
        "key": "saga_tomba", "title": "La tomba del Patriarca Senza Nome — I. Il sigillo", "weight": 5, "repeat_gap": 4000,
        "req": {"types": ["ruin", "forbidden_zone"], "danger_min": 2},
        "text": ("Tra le rovine un terremoto ha aperto una crepa: sotto c'è una porta di bronzo coperta di "
                 "rune. Il sigillo è ancora caldo, come se qualcuno dall'altra parte respirasse. Sulla soglia, "
                 "un'iscrizione: «Chi entra con avidità, resti con me».")
        ,
        "choices": [
            {"label": "Studi le rune prima di toccare il sigillo",
             "check": {"stat": "anima", "dc": 60},
             "success": {"dao_key": "random", "dao_gain": 3,
                         "text": "Le rune sono una prova, non una trappola. La porta si apre senza un suono.",
                         "then": {
                             "key": "saga_tomba_2", "title": "La tomba del Patriarca Senza Nome — II. Il guardiano",
                             "text": ("Un corridoio di statue. L'ultima apre gli occhi: un guardiano di giada, con "
                                      "la spada ancora sguainata dopo diecimila anni. «Dimostra di essere degno.»"),
                             "choices": [
                                 {"label": "Affronti il guardiano a viso aperto",
                                  "check": {"stat": "potenza", "dc": 72},
                                  "success": {"text": "La giada si incrina e il guardiano si inchina.",
                                              "then": {
                                                  "key": "saga_tomba_3",
                                                  "title": "La tomba del Patriarca Senza Nome — III. L'eredità",
                                                  "text": ("Nella sala finale, su un trono di ossa, siede ciò che resta del "
                                                           "Patriarca. Davanti a lui tre doni: un rotolo, una pillola d'oro, "
                                                           "una ciotola vuota con scritto «per chi verrà dopo di te»."),
                                                  "choices": [
                                                      {"label": "Prendi il rotolo della sua tecnica",
                                                       "effects": {"prize": {"rank": 1, "kinds": ["manuale"], "scale": 1.5},
                                                                   "text": "Il rotolo si scioglie nella tua mente."}},
                                                      {"label": "Prendi la pillola d'oro",
                                                       "effects": {"prize": {"rank": 1, "kinds": ["pillola", "tesoro"], "scale": 1.5},
                                                                   "text": "La pillola pulsa come un cuore."}},
                                                      {"label": "Lasci tutto e riempi la ciotola con le tue pietre",
                                                       "effects": {"stones": -100, "karma": 60, "lifespan_years": 20,
                                                                   "dao_key": "random", "dao_gain": 8,
                                                                   "text": ("Il Patriarca sorride, nella polvere. Una voce ti "
                                                                            "attraversa: «Finalmente uno che dà invece di prendere.» "
                                                                            "Il suo Dao ti sfiora come una benedizione.")}},
                                                  ]}},
                                  "failure": {"injury": 6, "text": "La lama di giada ti respinge fino all'ingresso."}},
                                 {"label": "Ti inchini e dichiari di non volere nulla",
                                  "effects": {"karma": 25, "dao_key": "random", "dao_gain": 5,
                                              "text": "Il guardiano abbassa la spada e ti lascia meditare un giorno nella tomba."}},
                             ]}},
             "failure": {"injury": 3, "text": "Una runa si accende: una scarica ti scaraventa fuori. Il sigillo si richiude."}},
            {"label": "Forzi il sigillo con il Qi",
             "check": {"stat": "qi", "dc": 75},
             "success": {"prize": {"rank": 3, "kinds": ["pillola", "nucleo"]}, "karma": -10,
                         "text": "Il sigillo cede. Nell'anticamera arraffi ciò che puoi prima che la volta crolli."},
             "failure": {"injury": 5, "heart": -5, "text": "«Chi entra con avidità…» Il soffitto ti cade addosso."}},
            {"label": "Lasci la tomba in pace", "effects": {"karma": 10}},
        ],
    },
    # ------------------------------------------------------------------ 4
    {
        "key": "saga_giovane_signore", "title": "Il Giovane Signore — I. L'affronto", "weight": 7, "repeat_gap": 2400,
        "req": {"types": ["city"]}, "spawn": _YOUNG_MASTER,
        "text": ("In una locanda di {luogo} il Giovane Signore {npc}, figlio di un clan potente, rovescia il "
                 "vino su un vecchio cantastorie e pretende che gli lecchi gli stivali. Poi nota te: «E tu? "
                 "Abbassa gli occhi, campagnolo, o te li strappo.»"),
        "choices": [
            {"label": "Lo sfidi sulla piazza, davanti a tutti",
             "effects": {"fame": 5, "text": "La locanda si svuota sulla piazza. Tutti vogliono vedere."},
             "command": "duello {npc}"},
            {"label": "Gli spezzi il polso senza estrarre l'arma, e lo lasci andare",
             "check": {"stat": "potenza", "dc": 60},
             "success": {"fame": 8, "spared": True, "text": ("Un movimento solo. {npc} urla, il polso piegato al contrario. "
                                                            "«Vattene, e impara a chinare il capo.» Il cantastorie ti "
                                                            "dedica una canzone che girerà per mesi."),
                         "then": {
                             "key": "saga_giovane_signore_2", "title": "Il Giovane Signore — II. Il clan",
                             "spawn": {"archetype": "anziano", "tier_offset": 1, "traits": {"pride": 80, "honor": 55}},
                             "respawn": True,
                             "text": ("Tre giorni dopo, alle porte di {luogo}, ti aspetta un anziano del clan: {npc}. "
                                      "«Hai umiliato il mio erede. Ma hai anche risparmiato la sua vita.» Ti studia "
                                      "a lungo. «Il mio clan sta decidendo se odiarti o rispettarti.»"),
                             "choices": [
                                 {"label": "Spieghi cosa stava facendo il ragazzo",
                                  "check": {"stat": "anima", "dc": 55},
                                  "success": {"relation": 40, "karma": 15, "prize": {"rank": 3, "kinds": ["pillola"]},
                                              "text": "L'anziano chiude gli occhi. «Lo sapevo. Grazie per avergli dato una lezione e non una tomba.»"},
                                  "failure": {"relation": -20, "text": "«Parole.» L'anziano se ne va. Il clan ti terrà d'occhio."}},
                                 {"label": "Gli dici che non ti interessa cosa pensa il suo clan",
                                  "effects": {"fame": 4, "relation": -40, "infamy": 2,
                                              "text": "«Come vuoi.» Da quel giorno il clan ti guarda come un nemico."}},
                             ]}},
             "failure": {"injury": 2, "text": "È più svelto di quanto sembrasse: si sfila e ti promette vendetta.",
                         "bond": "nemesis", "bond_reason": "l'affronto nella locanda"}},
            {"label": "Abbassi gli occhi (per ora)", "effects": {"heart": -4, "karma": -5,
                                                                 "text": "Bruci dentro. Il cantastorie ti guarda deluso."}},
        ],
    },
    # ------------------------------------------------------------------ 5
    {
        "key": "saga_villaggio", "title": "Il villaggio che non si sveglia — I. Il sonno", "weight": 5, "repeat_gap": 3600,
        "req": {"types": ["city", "mountain"]}, "spawn": _DEMONIC,
        "text": ("Nel villaggio vicino a {luogo} nessuno si è svegliato stamattina. Contadini addormentati nei "
                 "campi, bambini nelle culle, un fabbro con il martello alzato. Respirano, ma sono freddi. Sui "
                 "tetti, sottile come seta, una nebbia viola."),
        "choices": [
            {"label": "Segui la nebbia fino alla sua origine",
             "check": {"stat": "anima", "dc": 60},
             "success": {"text": "La nebbia sale da una grotta sopra il villaggio, dove qualcuno salmodia.",
                         "then": {
                             "key": "saga_villaggio_2", "title": "Il villaggio che non si sveglia — II. Il coltivatore demoniaco",
                             "text": ("Nella grotta, {npc} siede al centro di un cerchio di sangue: dalla nebbia "
                                      "beve la vita dei dormienti, un respiro alla volta. Apre un occhio. «Un altro "
                                      "giorno e avrei sfondato. Vuoi una parte? C'è vita per due.»"),
                             "choices": [
                                 {"label": "Spezzi il cerchio e lo affronti (duello a turni)",
                                  "effects": {"karma": 20, "text": "Il cerchio si spegne: nel villaggio, qualcuno tossisce."},
                                  "command": "duello {npc}"},
                                 {"label": "Lo uccidi mentre è legato al rituale",
                                  "check": {"stat": "istinto", "dc": 65},
                                  "success": {"npc_dies": True, "karma": 35, "fame": 10,
                                              "prize": {"rank": 2, "kinds": ["essenza", "nucleo"]},
                                              "text": ("Un colpo solo, prima che possa sciogliere le mani. Il villaggio si "
                                                       "risveglia all'unisono, come un unico respiro.")},
                                  "failure": {"injury": 5, "text": "Si libera all'ultimo istante.", "command": "duello {npc}"}},
                                 {"label": "Accetti la sua offerta",
                                  "effects": {"karma": -120, "infamy": 15, "cultivation_progress": 0.8,
                                              "dao_key": "sangue", "dao_gain": 6,
                                              "text": ("Bevi con lui. È dolce. Nel villaggio, tre culle si fermano per sempre. "
                                                       "Lo saprai per il resto delle tue vite.")}},
                             ]}},
             "failure": {"text": "La nebbia ti confonde. Quando ritrovi la strada, il villaggio è vuoto. Qualcuno l'ha preso."}},
            {"label": "Porti via i bambini, prima di tutto",
             "effects": {"karma": 40, "fame": 3, "text": "Ne salvi undici. I loro genitori non si svegliano più."}},
            {"label": "Te ne vai: è una trappola troppo evidente", "effects": {"karma": -20}},
        ],
    },
    # ------------------------------------------------------------------ 6
    {
        "key": "saga_carovana", "title": "La carovana delle erbe — I. Il contratto", "weight": 6, "repeat_gap": 2400,
        "req": {"types": ["city"]}, "spawn": _BANDIT,
        "text": ("Il mercante Bao ti offre un contratto: scortare la sua carovana di erbe spirituali fino al "
                 "passo, tre giorni di strada. «Pago bene. I briganti di {npc} hanno già preso due carovane questo mese.»"),
        "choices": [
            {"label": "Accetti la scorta",
             "effects": {"text": "Partite all'alba: otto carri, dodici mercanti, e tu.",
                         "then": {
                             "key": "saga_carovana_2", "title": "La carovana delle erbe — II. L'imboscata",
                             "text": ("Al secondo giorno, nella stretta del Dente di Lupo, una pioggia di frecce. "
                                      "{npc} scende dalla rupe con venti uomini: «Le erbe, e nessuno si fa male.»"),
                             "choices": [
                                 {"label": "Difendi la carovana affrontando il capo (duello a turni)",
                                  "effects": {"fame": 3}, "command": "duello {npc}"},
                                 {"label": "Fai scudo ai mercanti e guidi la ritirata",
                                  "check": {"stat": "istinto", "dc": 58},
                                  "success": {"karma": 25, "stones": 150, "fame": 5,
                                              "prize": {"rank": 3, "kinds": ["pillola"]},
                                              "text": "Perdete due carri ma nessuna vita. Bao paga il doppio."},
                                  "failure": {"injury": 4, "stones": 60, "text": "Salvate i mercanti, non le erbe."}},
                                 {"label": "Ti accordi con {npc}: metà del carico, e la strada libera",
                                  "effects": {"karma": -25, "stones": 220, "spared": True, "infamy": 3,
                                              "text": "Bao non ti guarderà più in faccia. {npc} ti saluta come un socio."}},
                             ]}}},
            {"label": "Rifiuti", "effects": {}},
        ],
    },
]
