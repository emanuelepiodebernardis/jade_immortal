"""
I COMPAGNI PERDUTI (Aggiornamento 67) — i capitoli della saga di chi è passato con te dal Varco.

Lo spunto viene da Immortal Celestial Fate: un gruppo di ragazzi in viaggio scivola dentro il Regno
Immortale, e il protagonista si risveglia da solo, con gli altri dispersi. Qui vale per tutte le origini:
il Trasmigratore viene dalla Terra (una gita di fine anno sulle montagne più alte del mondo), gli altri
erano su una carovana di giovani diretti all'esame di una setta. In mezzo, il Varco del Cielo Spezzato.

Cinque compagni, cinque destini: l'amico ridotto a servo, la santa di una setta giusta, la prigioniera di
un vecchio mostro, l'amico caduto nel sentiero demoniaco, il cacciatore che ti crede un traditore. Poi il
Varco stesso, e chi lo aprì. Li apre lost_companions.py (via soul_arcs, come i vasi d'anima); l'esito di
ogni capitolo decide il destino del compagno (fratello giurato, alleato, nemico, morto).

Segnaposto: {amico} {santa} {prigioniera} {caduto} {cacciatore} — i nomi dei compagni;
{gruppo} {viaggio} {ricordo} — come eravate, dove andavate, cosa ti è rimasto in tasca.
"""

from __future__ import annotations

_BRONZO = {"rank": 3, "kinds": ["pillola", "tesoro"]}
_ARGENTO = {"rank": 2, "kinds": ["tesoro", "manuale", "pillola"]}
_ORO = {"rank": 1, "kinds": ["tesoro", "manuale"]}
_RELIQUIA = {"rank": 1, "kinds": ["reliquia", "tesoro"]}

ARCS: list[dict] = [
    # ================================================================== 0. IL RICORDO
    {
        "key": "compagni_varco", "arc": "compagni", "title": "Il Varco del Cielo Spezzato", "kind": "mistero",
        "weight": 0, "tier_min": 1, "cast": {"mercante": "vagabondo"},
        "acts": [
            {"title": "Un oggetto che non dovrebbe esistere", "focus": "mercante", "gap": (1, 1),
             "text": ("Su una bancarella, tra amuleti falsi e ossa di bestia, c'è {ricordo}. Lo riconosci prima ancora "
                      "di capire perché ti trema la mano: era di {amico}. Ricordi {viaggio}, {gruppo}, il cielo che si "
                      "strappa come carta, la caduta. Ti sei risvegliato da solo. Non hai mai saputo cosa ne fosse "
                      "degli altri. {mercante} sorride: «Bello, eh? L'ho preso a un servo, in una setta a est.»"),
             "choices": [
                 {"label": "Lo compri e chiedi tutto ciò che sa (200 pietre)",
                  "effects": {"stones": -200, "intrigue": {"end": "traccia"},
                              "text": ("«Una setta minore, a est. Il servo lo teneva come un tesoro. Ne girano altri, "
                                       "di oggetti strani così: uno a una santa, uno a un vecchio che compra ragazze.»")}},
                 {"label": "Gli leggi negli occhi da dove viene davvero",
                  "check": {"stat": "istinto", "dc": 45},
                  "success": {"text": "Mente sul prezzo, non sull'origine. Est, una setta minore, un servo picchiato.",
                              "intrigue": {"end": "traccia"}},
                  "failure": {"text": "Il mercante fiuta il tuo interesse e sparisce nella folla.",
                              "intrigue": {"end": "perso"}}},
                 {"label": "Lo prendi con la forza: è tuo più che suo",
                  "effects": {"karma": -5, "infamy": 2, "intrigue": {"end": "traccia"},
                              "text": "Il mercante strilla, poi parla: est, una setta minore, un servo."}},
             ]},
        ],
        "auto_end": [{"outcome": "perso", "text": "Il mercante non è più al mercato."}],
        "outcomes": {"traccia": "Hai una traccia: {gruppo} sono vivi, da qualche parte nel Regno.",
                     "perso": "La traccia si è persa. Tornerà."},
    },
    # ================================================================== 1. L'AMICO SERVO
    {
        "key": "compagni_amico", "arc": "compagni", "title": "L'amico in catene", "kind": "salvataggio",
        "weight": 0, "tier_min": 1, "cast": {"amico": "stato:lc_amico", "aguzzino": "sgherro"},
        "acts": [
            {"title": "Il servo della legnaia", "focus": "amico", "gap": (1, 2),
             "text": ("Nella setta a est i servi portano acqua dall'alba al tramonto. Uno zoppica, ha una cicatrice "
                      "sul collo e gli occhi di chi ha smesso di sperare. È {amico}. Quando ti vede lascia cadere i "
                      "secchi. Dietro di lui, {aguzzino} alza la frusta: «Chi ti ha detto di fermarti, cane?»"),
             "choices": [
                 {"label": "Fermi la frusta a mezz'aria e sfidi {aguzzino}",
                  "effects": {"intrigue": {"end": "liberato"}}, "command": "duello {aguzzino}"},
                 {"label": "Compri la sua libertà dalla setta (600 pietre)",
                  "effects": {"stones": -600, "intrigue": {"end": "riscattato"},
                              "text": "Il diacono conta le pietre e cancella un nome dal registro dei servi."}},
                 {"label": "Torni di notte e lo porti via",
                  "check": {"stat": "istinto", "dc": 50},
                  "success": {"text": "La legnaia ha una tavola marcia. All'alba siete già oltre il fiume.",
                              "intrigue": {"end": "fuga_insieme"}},
                  "failure": {"injury": 1, "text": "I cani della setta vi trovano al muro. {amico} resta dentro.",
                              "intrigue": {"end": "fallito"}}},
             ]},
        ],
        "auto_end": [{"outcome": "fallito", "text": "{amico} è stato venduto a un'altra setta. Lo ritroverai."}],
        "outcomes": {"liberato_vinto": "Hai spezzato la frusta di {aguzzino}: {amico} è libero.",
                     "liberato_perso": "{aguzzino} ti ha battuto davanti a tutti. {amico} resta un servo, per ora.",
                     "liberato_fuga": "Sei fuggito. {amico} ti ha visto andare via.",
                     "riscattato": "Hai comprato la libertà di {amico}.",
                     "fuga_insieme": "Siete fuggiti insieme, come quando eravate ragazzi.",
                     "fallito": "Non sei riuscito a portarlo via."},
    },
    # ================================================================== 2. LA SANTA
    {
        "key": "compagni_santa", "arc": "compagni", "title": "La santa che non ti riconosce", "kind": "intrigo",
        "weight": 0, "tier_min": 1, "cast": {"santa": "stato:lc_santa", "anziano": "anziano"},
        "acts": [
            {"title": "Un volto sul palanchino", "focus": "santa", "gap": (1, 2),
             "text": ("Una processione attraversa la città: veli bianchi, campane, discepoli in ginocchio. Sul "
                      "palanchino siede la Santa di una grande setta giusta. Ha il volto di {santa}. I vostri occhi si "
                      "incrociano un istante, poi lei guarda altrove come se tu fossi aria. Accanto a lei, {anziano} "
                      "ha notato tutto."),
             "choices": [
                 {"label": "Le fai arrivare un messaggio che solo lei può capire",
                  "check": {"stat": "anima", "dc": 45},
                  "success": {"text": ("La risposta arriva a mezzanotte, in una grafia che conosci: «Non posso. Ho "
                                       "giurato. Se sanno da dove vengo, mi strappano il Dao.»"),
                              "intrigue": {"clue": 1, "branch": "giuramento"}},
                  "failure": {"text": "Il messaggio torna indietro, sigillato, senza risposta.", "intrigue": {}}},
                 {"label": "Aspetti: se ti ha visto, verrà lei", "effects": {"heart": 3, "intrigue": {"branch": "attesa"}}},
             ]},
            {"title": "Il giuramento", "focus": "anziano", "gap": (2, 3),
             "text": ("{anziano} ti convoca nel padiglione della setta. {santa} è dietro di lui, immobile. «La nostra "
                      "Santa non ha passato. Chi dice il contrario mente, e chi mente su una Santa muore.» Lei non "
                      "alza gli occhi."),
             "text_branch": {"giuramento": ("{anziano} ti convoca. Ora sai perché {santa} tace: un giuramento sul "
                                            "Dao, e {anziano} è quello che lo custodisce. Lei ti guarda, una volta sola.")},
             "choices": [
                 {"label": "Sfidi {anziano}: se cade, cade anche il giuramento",
                  "effects": {"intrigue": {"end": "giuramento"}}, "command": "duello {anziano}"},
                 {"label": "Dici che hai sbagliato persona, e te ne vai: la proteggi così",
                  "effects": {"heart": 6, "karma": 8, "intrigue": {"end": "protetta"},
                              "text": "Mentre esci, senti una campana suonare due volte. Era il vostro segnale, da ragazzi."}},
                 {"label": "Parli a {santa}, davanti a tutti, di {viaggio}",
                  "check": {"stat": "anima", "dc": 60},
                  "success": {"text": ("Lei si alza. «È vero.» Il padiglione ammutolisce. «Ed è vero anche che "
                                       "resto: questa setta mi ha salvata. Ma da oggi non giuro più contro il mio "
                                       "passato.»"), "intrigue": {"end": "svelata"}},
                  "failure": {"injury": 1, "text": "{anziano} ti scaglia fuori dal padiglione con un gesto.",
                              "intrigue": {"end": "cacciato"}}},
             ]},
        ],
        "auto_end": [{"outcome": "cacciato", "text": "La processione è ripartita. {santa} non si è voltata."}],
        "outcomes": {"giuramento_vinto": "{anziano} è caduto e con lui il giuramento: {santa} è libera di riconoscerti.",
                     "giuramento_perso": "{anziano} ti ha battuto: il giuramento tiene.",
                     "giuramento_fuga": "Sei fuggito dal padiglione.",
                     "protetta": "Hai protetto {santa} facendo finta di non conoscerla. Lei lo sa.",
                     "svelata": "{santa} ha detto la verità davanti alla sua setta: resta Santa, e resta tua amica.",
                     "cacciato": "Ti hanno cacciato. Ci vorrà tempo."},
    },
    # ================================================================== 3. LA PRIGIONIERA
    {
        "key": "compagni_prigioniera", "arc": "compagni", "title": "Il calderone vivente", "kind": "salvataggio",
        "weight": 0, "tier_min": 1, "cast": {"prigioniera": "stato:lc_prigioniera", "mostro": "anziano"},
        "indagine": "istinto", "need": 2, "reveal_act": 1,
        "indizi": ["Un vecchio coltivatore compra ragazze con radici spirituali rare: le usa come calderoni viventi.",
                   "Le tiene in una valle chiusa da una formazione di nebbia, a tre giorni da qui.",
                   "La formazione si apre solo quando lui raffina: la nebbia si dirada per un'ora a ogni luna nuova."],
        "acts": [
            {"title": "Ragazze che non tornano", "focus": "mostro", "gap": (1, 2),
             "text": ("Nei villaggi raccontano di ragazze con «il dono» comprate per pochi spiccioli da {mostro}, e "
                      "mai più viste. Una di loro, dicono, parlava una lingua strana e cantava canzoni che nessuno "
                      "conosceva. Una era {prigioniera}."),
             "choices": [
                 {"label": "Fai domande nei villaggi", "check": {"stat": "istinto", "dc": 45},
                  "success": {"text": "Una madre ti dice dove portano le ragazze.", "intrigue": {"clue": 1}},
                  "failure": {"text": "Nessuno parla: hanno paura.", "intrigue": {}}},
                 {"label": "Segui il prossimo carro di {mostro}", "check": {"stat": "istinto", "dc": 55},
                  "success": {"text": "Il carro sparisce dentro la nebbia di una valle.", "intrigue": {"clue": 2}},
                  "failure": {"text": "Il carro ti semina tra i monti.", "intrigue": {}}},
             ]},
            {"title": "La valle di nebbia", "focus": "prigioniera", "gap": (2, 4),
             "text": ("La valle odora di erbe bruciate. In fondo, un calderone grande come una casa, e dentro, in "
                      "piedi nel Qi che bolle, {prigioniera}: pallida, viva, gli occhi chiusi. {mostro} ti sente arrivare."),
             "choices": [
                 {"label": "Affronti {mostro} davanti al calderone",
                  "effects": {"intrigue": {"end": "assalto"}}, "command": "duello {mostro}"},
                 {"label": "Entri nell'ora in cui la nebbia si dirada e la porti via",
                  "need_clues": 2, "check": {"stat": "istinto", "dc": 50},
                  "success": {"text": "La nebbia si apre come una tenda. Esci con {prigioniera} sulle spalle.",
                              "intrigue": {"end": "furtivo"}},
                  "failure": {"injury": 2, "text": "La nebbia si richiude su di te. Fuggi, da solo.",
                              "intrigue": {"end": "fallito"}}},
                 {"label": "Le parli dentro il calderone, nella vostra lingua, perché si svegli da sola",
                  "check": {"stat": "anima", "dc": 65},
                  "success": {"text": ("Apre gli occhi. Il Qi del calderone le obbedisce, non a lui: la formazione "
                                       "si spezza dall'interno."), "intrigue": {"end": "risvegliata"}},
                  "failure": {"text": "Non ti sente. {mostro} ride.", "intrigue": {"end": "assalto"}, "command": "duello {mostro}"}},
             ]},
        ],
        "auto_end": [{"outcome": "fallito", "text": "{mostro} ha spostato i suoi calderoni. Lo ritroverai."}],
        "outcomes": {"assalto_vinto": "Hai abbattuto {mostro} e tirato fuori {prigioniera} dal calderone.",
                     "assalto_perso": "{mostro} ti ha respinto. {prigioniera} è ancora nel calderone.",
                     "assalto_fuga": "Sei fuggito dalla valle.",
                     "furtivo": "Hai portato via {prigioniera} senza che {mostro} se ne accorgesse.",
                     "risvegliata": "{prigioniera} si è liberata da sola, e ha preso con sé il Qi del calderone.",
                     "fallito": "Non sei riuscito a liberarla."},
    },
    # ================================================================== 4. IL CADUTO
    {
        "key": "compagni_caduto", "arc": "compagni", "title": "Il sentiero del sangue", "kind": "vendetta",
        "weight": 0, "tier_min": 1, "cast": {"caduto": "stato:lc_caduto"},
        "acts": [
            {"title": "Il villaggio vuoto", "focus": "caduto", "gap": (1, 2),
             "text": ("Un villaggio senza un'anima viva, e al centro, seduto su un pozzo, {caduto}. Ha gli occhi "
                      "rossi dei coltivatori demoniaci e la stessa voce di quando scherzava con {gruppo}. «Sai cosa ho "
                      "dovuto fare per sopravvivere qui, da solo? Tutto. E adesso sono forte. Vieni con me. Insieme "
                      "non ci tocca più nessuno.»"),
             "choices": [
                 {"label": "Gli chiedi cosa gli è successo", "effects": {"intrigue": {"clue": 1, "branch": "storia"},
                  "text": ("«Mi hanno venduto a un culto il primo mese. Mi hanno insegnato a mangiare il Qi degli "
                           "altri. Ho smesso di contare.»")}},
                 {"label": "Lo attacchi subito: questo non è più lui",
                  "effects": {"intrigue": {"end": "fermato"}}, "command": "duello {caduto}"},
             ]},
            {"title": "L'ultima domanda", "focus": "caduto", "gap": (1, 2),
             "text": "{caduto} aspetta la tua risposta, con le mani ancora sporche.",
             "text_branch": {"storia": ("Ora sai cosa gli hanno fatto. {caduto} aspetta la tua risposta: in fondo agli "
                                        "occhi rossi c'è ancora il ragazzo di {viaggio}.")},
             "choices": [
                 {"label": "Lo fermi, con la forza (se lo risparmi potrà tornare indietro)",
                  "effects": {"intrigue": {"end": "fermato"}}, "command": "duello {caduto}"},
                 {"label": "Gli ricordi chi era, finché non se lo ricorda anche lui",
                  "check": {"stat": "anima", "dc": 65},
                  "success": {"heart": 8, "karma": 12, "text": "{caduto} piange sangue, poi acqua. Il rosso lascia i suoi occhi.",
                              "intrigue": {"end": "redento"}},
                  "failure": {"text": "«Le parole non mi hanno mai salvato.» Attacca.", "intrigue": {"end": "fermato"}, "command": "duello {caduto}"}},
                 {"label": "Accetti: insieme, sul sentiero del sangue",
                  "effects": {"karma": -25, "infamy": 10, "intrigue": {"end": "patto"},
                              "text": "Vi stringete la mano sopra il pozzo. Il villaggio vuoto non protesta."}},
             ]},
        ],
        "auto_end": [{"outcome": "sparito", "text": "{caduto} è sparito. Il prossimo villaggio vuoto ti dirà dov'è."}],
        "outcomes": {"fermato_vinto": "Hai fermato {caduto}.",
                     "fermato_perso": "{caduto} ti ha battuto e se n'è andato ridendo.",
                     "fermato_fuga": "Sei fuggito da {caduto}.",
                     "redento": "{caduto} ha lasciato il sentiero del sangue.",
                     "patto": "Hai stretto un patto con {caduto} sul sentiero del sangue.",
                     "sparito": "{caduto} è sparito."},
    },
    # ================================================================== 5. IL CACCIATORE
    {
        "key": "compagni_cacciatore", "arc": "compagni", "title": "Chi ti dà la caccia", "kind": "vendetta",
        "weight": 0, "tier_min": 1, "cast": {"cacciatore": "stato:lc_cacciatore"},
        "acts": [
            {"title": "La lama alle spalle", "focus": "cacciatore", "gap": (1, 2),
             "text": ("Da settimane qualcuno distrugge i luoghi dove sei appena passato. Stanotte si mostra: "
                      "{cacciatore}, con una lama nera e una voce che non è del tutto sua. «Ci hai lasciati lì. Il "
                      "Varco si è aperto per te, e tu hai lasciato cadere tutti gli altri. Me l'ha detto la Voce.»"),
             "text_branch": {"riuniti": ("Da settimane qualcuno distrugge i luoghi dove sei appena passato. Stanotte "
                                         "si mostra: {cacciatore}. Ma non sei solo: chi hai ritrovato è con te, e "
                                         "lui li vede. La lama trema.")},
             "choices": [
                 {"label": "Combatti: spezzerai la Voce spezzando la sua lama",
                  "effects": {"intrigue": {"end": "voce"}}, "command": "duello {cacciatore}"},
                 {"label": "Gli racconti cosa è successo davvero, con chi hai ritrovato a testimoniare",
                  "need_clues": 0, "check": {"stat": "anima", "dc": 55},
                  "success": {"text": ("La Voce urla dentro di lui, poi tace. {cacciatore} lascia cadere la lama: «Allora "
                                       "chi mi ha parlato, per tutto questo tempo?»"), "intrigue": {"end": "verita"}},
                  "failure": {"text": "La Voce è più forte delle tue parole. Attacca.", "intrigue": {"end": "voce"}, "command": "duello {cacciatore}"}},
                 {"label": "Fuggi: non vuoi alzare la mano su di lui",
                  "effects": {"intrigue": {"end": "inseguito"}, "text": "Lui ti seguirà. Lo sai."}},
             ]},
        ],
        "auto_end": [{"outcome": "inseguito", "text": "{cacciatore} ha perso le tue tracce. Per ora."}],
        "outcomes": {"voce_vinto": "Hai spezzato la lama nera: la Voce ha lasciato {cacciatore}.",
                     "voce_perso": "{cacciatore} ti ha battuto. La Voce ride.",
                     "voce_fuga": "Sei fuggito da {cacciatore}.",
                     "verita": "{cacciatore} sa la verità. Ora la Voce ha un nemico in più.",
                     "inseguito": "{cacciatore} ti dà ancora la caccia."},
    },
    # ================================================================== 6. IL VARCO
    {
        "key": "compagni_finale", "arc": "compagni", "title": "Chi aprì il Varco", "kind": "mistero",
        "weight": 0, "tier_min": 1, "cast": {"custode": "anziano"},
        "acts": [
            {"title": "La Voce ha un volto", "focus": "custode", "gap": (2, 3),
             "text": ("Seguite la Voce fino al punto in cui il cielo è ancora cucito male: il Varco del Cielo "
                      "Spezzato. Lì vi aspetta {custode}, un immortale caduto. «Mi servivano sei semi di un altro "
                      "destino, per riaprire la porta da cui fui cacciato. Voi eravate i semi. Siete cresciuti bene.»"),
             "text_branch": {"riuniti": ("Siete in tanti, davanti al Varco: chi hai ritrovato è al tuo fianco. "
                                         "{custode}, l'immortale caduto che vi trascinò qui, smette di sorridere. "
                                         "«Sei semi dovevano essere sparsi. Non riuniti.»")},
             "choices": [
                 {"label": "Lo affronti: il Varco si chiude con lui",
                  "effects": {"intrigue": {"end": "custode"}}, "command": "duello {custode}"},
                 {"label": "Sigillate il Varco insieme, con il Qi di tutti voi",
                  "check": {"stat": "qi", "dc": 60},
                  "success": {"text": ("Le vostre mani sulla cicatrice del cielo. Il Varco si chiude, e {custode} con "
                                       "lui, dall'altra parte."), "intrigue": {"end": "sigillato"}},
                  "failure": {"injury": 2, "text": "Il sigillo cede. {custode} ride e attacca.",
                              "intrigue": {"end": "custode"}, "command": "duello {custode}"}},
                 {"label": "Prendi tu il potere del Varco",
                  "effects": {"karma": -30, "intrigue": {"end": "preso"},
                              "text": "Il Varco ti entra nel petto come un secondo cuore. Chi è con te fa un passo indietro."}},
             ]},
        ],
        "auto_end": [{"outcome": "rimandato", "text": "Il Varco si è richiuso da solo. Si riaprirà."}],
        "outcomes": {"custode_vinto": "Hai abbattuto {custode}: il Varco del Cielo Spezzato è chiuso per sempre.",
                     "custode_perso": "{custode} ti ha respinto. Il Varco resta aperto.",
                     "custode_fuga": "Sei fuggito dal Varco.",
                     "sigillato": "Avete sigillato il Varco insieme.",
                     "preso": "Hai preso per te il potere del Varco.",
                     "rimandato": "Il Varco aspetta."},
    },
]
