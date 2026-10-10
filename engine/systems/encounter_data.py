"""
Catalogo degli INCONTRI casuali (奇遇). Solo dati: il motore è in encounters.py.

Campi:
  key, title, text (con {npc} e {luogo}), weight, repeat_gap (tick prima che possa
  ripetersi; default ~10 giorni), once (una sola volta per vita), req (types, danger_min/max, tier_min/max, anomaly, in_sect, dao),
  choices: [{label, check?, success?, failure?, effects?, command?}]
Statistiche delle prove: corpo, anima, qi, coltivazione, istinto, fortuna, karma, potenza.
"""

from __future__ import annotations

ENCOUNTERS: list[dict] = [
    {
        "key": "vecchio_morente", "title": "Il vecchio sul ciglio della strada", "weight": 10,
        "req": {"types": ["city", "mountain", "ruin"]},
        "text": ("Un vecchio coltivatore, {npc}, giace ferito ai margini del sentiero. Respira a "
                 "fatica e stringe al petto un rotolo di seta annerito. Ti guarda senza parlare."),
        "choices": [
            {"label": "Lo curi infondendogli il tuo Qi",
             "check": {"stat": "qi", "dc": 70},
             "success": {"spawn": {"archetype": "eremita", "tier_offset": 1},
                         "relation": 45, "karma": 35,
                         "text": "Il colore torna sul volto di {npc}. «Non dimentico chi mi "
                                 "tende la mano», dice, e ti spiega un passaggio del rotolo.",
                         "learn_technique": {"name": "Respiro della Vecchia Quercia",
                                             "magnitude": 0.05, "tech_key": "enc:quercia"}},
             "failure": {"karma": 20, "dao_key": "random", "dao_gain": 3,
                         "text": "Non basta. Prima di spegnersi, {npc} ti mette il rotolo tra "
                                 "le mani: qualche riga ti resta impressa."}},
            {"label": "Gli strappi il rotolo e te ne vai",
             "effects": {"karma": -45, "infamy": 4,
                         "learn_technique": {"name": "Rotolo Strappato", "magnitude": 0.04,
                                             "tech_key": "enc:rotolo"},
                         "text": "Il vecchio non ha la forza di opporsi. I suoi occhi ti seguono."}},
            {"label": "Prosegui per la tua strada",
             "effects": {"karma": -5, "text": "Il vento copre i suoi lamenti."}},
        ],
    },
    {
        "key": "mortali_bestia", "title": "Grida nella boscaglia", "weight": 10,
        "req": {"types": ["mountain", "forbidden_zone", "ruin"], "danger_min": 2},
        "text": ("Urla di terrore: una famiglia di mortali è braccata da una bestia spirituale "
                 "dalle zanne d'osso. Il padre agita un bastone, inutilmente."),
        "choices": [
            {"label": "Ti getti tra loro e la bestia",
             "check": {"stat": "potenza", "dc": 62},
             "success": {"fame": 8, "karma": 35, "stones": 15, "cultivation_progress": 0.12,
                         "text": "La bestia crolla. I mortali ti offrono tutto ciò che hanno "
                                 "e il racconto ti precede nei villaggi."},
             "failure": {"injury": 4, "karma": 25, "fame": 3,
                         "text": "La bestia ti ferisce prima di fuggire, ma la famiglia è salva."}},
            {"label": "Lasci che la bestia si sazi e la colpisci mentre mangia",
             "effects": {"karma": -60, "grow_strength": 2, "cultivation_progress": 0.12,
                         "text": "Un colpo pulito, una bestia distratta. Non guardi cosa resta."}},
            {"label": "Non è affar tuo", "effects": {"karma": -10}},
        ],
    },
    {
        "key": "frutto_spirituale", "title": "Il Frutto Spirituale", "weight": 8,
        "req": {"types": ["mountain", "forbidden_zone"], "danger_min": 3},
        "text": ("Su uno sperone di roccia matura un Frutto Spirituale che pulsa di luce. Ai piedi "
                 "della pianta dorme, arrotolato, un serpente custode grande come un tronco."),
        "choices": [
            {"label": "Lo cogli in silenzio, senza svegliare il custode",
             "check": {"stat": "istinto", "dc": 75},
             "success": {"item": {"name": "Frutto Spirituale Maturo", "item_type": "pillola",
                                  "rarity": "raro", "desc": "Un balzo nella coltivazione.",
                                  "effects": {"cultivation_progress": 0.6}}},
             "failure": {"injury": 4, "text": "Un sasso rotola. Il custode si sveglia e "
                                               "ti scaccia a frustate di coda."}},
            {"label": "Sfidi apertamente il custode",
             "check": {"stat": "potenza", "dc": 85},
             "success": {"grow_vitality": 3, "fame": 4,
                         "item": {"name": "Frutto Spirituale Maturo", "item_type": "pillola",
                                  "rarity": "raro", "desc": "Un balzo nella coltivazione.",
                                  "effects": {"cultivation_progress": 0.6}},
                         "text": "Il serpente giace immobile; ne assorbi il vigore."},
             "failure": {"injury": 6, "text": "Il custode è più forte di quanto sembrasse."}},
            {"label": "Mediti accanto al frutto, assorbendone l'aura",
             "check": {"stat": "coltivazione", "dc": 60},
             "success": {"cultivation_progress": 0.25},
             "failure": {"text": "L'aura è troppo densa: ne cogli solo un riflesso."}},
        ],
    },
    {
        "key": "caverna_eredita", "once": True, "title": "La caverna sigillata", "weight": 8,
        "req": {"types": ["ruin", "mountain"], "danger_min": 2},
        "text": ("Dietro un crollo scopri l'ingresso di una caverna sigillata. Sulla soglia, "
                 "un'iscrizione: «Il mio Dao attende chi ha cuore saldo. Gli altri restino fuori»."),
        "choices": [
            {"label": "Affronti la prova dell'anima",
             "check": {"stat": "anima", "dc": 80},
             "success": {"learn_technique": {"name": "Eredità della Caverna Sigillata",
                                             "magnitude": 0.10, "tech_key": "enc:caverna"},
                         "title": "Erede delle Rovine",
                         "text": "Visioni di una vita intera ti attraversano. Quando riapri "
                                 "gli occhi, conosci la tecnica del vecchio maestro."},
             "failure": {"injury": 3, "aff_soul": -1,
                         "text": "La prova ti respinge: la mente brucia per ore."}},
            {"label": "Forzi il sigillo con la forza bruta",
             "check": {"stat": "corpo", "dc": 85},
             "success": {"stones": 120, "text": "Il sigillo cede: dentro, un forziere di pietre."},
             "failure": {"injury": 5, "text": "Il sigillo esplode e ti travolge."}},
            {"label": "Copi le iscrizioni e studi da fuori",
             "effects": {"dao_key": "random", "dao_gain": 4}},
        ],
    },
    {
        "key": "lago_yin", "title": "Il lago di Qi gelido", "weight": 7,
        "req": {"types": ["mountain", "forbidden_zone"]},
        "text": ("Un lago d'acqua nera e immobile. Il freddo che ne sale non è naturale: è Qi yin "
                 "puro, abbastanza da temprare un corpo… o da spezzarlo."),
        "choices": [
            {"label": "Ti immergi e coltivi nell'acqua gelida",
             "check": {"stat": "corpo", "dc": 70},
             "success": {"grow_resistance": 4, "cultivation_progress": 0.15},
             "failure": {"injury": 3, "text": "Il gelo ti morde fino alle ossa."}},
            {"label": "Ne raccogli una fiala",
             "effects": {"item": {"name": "Fiala d'Acqua Yin", "item_type": "pillola",
                                  "rarity": "non_comune", "desc": "Qi yin condensato.",
                                  "effects": {"cultivation_progress": 0.2}}}},
        ],
    },
    {
        "key": "tempesta_fulmini", "title": "La tempesta viola", "weight": 6,
        "req": {"types": ["mountain"], "danger_min": 2},
        "text": ("Nubi viola si addensano sopra la cresta. Non è una tempesta qualunque: i fulmini "
                 "portano Qi celeste. Chi li regge ne esce cambiato."),
        "choices": [
            {"label": "Resti sulla cresta e lasci che i fulmini ti attraversino",
             "check": {"stat": "corpo", "dc": 82},
             "success": {"dao_key": "fulmine", "dao_gain": 8, "grow_vitality": 2},
             "failure": {"injury": 5, "dao_key": "fulmine", "dao_gain": 2,
                         "text": "Ti risvegli carbonizzato, ma qualcosa del Fulmine ti è rimasto."}},
            {"label": "Ti ripari e osservi da lontano",
             "effects": {"dao_key": "fulmine", "dao_gain": 1}},
        ],
    },
    {
        "key": "giovane_maestro", "title": "Il Giovane Maestro", "weight": 6,
        "req": {"types": ["city"]},
        "text": ("Il Giovane Maestro {npc}, rampollo di una famiglia potente, ti sbarra la strada "
                 "circondato da servitori. «Inginocchiati, plebeo, e forse ti lascerò passare»."),
        "choices": [
            {"label": "Ti inginocchi",
             "effects": {"spawn": {"archetype": "discepolo", "tier_offset": 0,
                                   "traits": {"pride": 95, "honor": 25}},
                         "relation": 5, "aff_combat": -1,
                         "text": "Ride e passa oltre. Ti resta un sapore amaro in bocca."}},
            {"label": "Lo sfidi a duello davanti a tutti",
             "effects": {"spawn": {"archetype": "discepolo", "tier_offset": 0,
                                   "traits": {"pride": 95, "honor": 25}},
                         "bond": "rival", "bond_reason": "l'hai sfidato in pubblico"},
             "command": "attack {npc}"},
            {"label": "Lo fissi negli occhi finché non abbassa lo sguardo",
             "check": {"stat": "anima", "dc": 70},
             "success": {"spawn": {"archetype": "discepolo", "tier_offset": 0,
                                   "traits": {"pride": 95, "honor": 25}},
                         "bond": "rival", "bond_reason": "l'hai umiliato con lo sguardo", "fame": 5,
                         "text": "{npc} indietreggia di un passo, livido. «Non finisce qui»."},
             "failure": {"spawn": {"archetype": "discepolo", "tier_offset": 0,
                                   "traits": {"pride": 95, "honor": 25}},
                         "bond": "rival", "bond_reason": "l'hai provocato",
                         "text": "«Insolente!» {npc} sguaina l'arma.",
                         "command": "attack {npc}"}},
        ],
    },
    {
        "key": "viandante_derubato", "title": "Il viandante derubato", "weight": 9,
        "req": {},
        "text": ("Un giovane coltivatore, {npc}, siede contro un albero con la veste strappata. "
                 "«Mi hanno preso tutto», dice, «perfino la spada di mio padre»."),
        "choices": [
            {"label": "Dividi con lui le tue provviste e lo aiuti a rimettersi in piedi",
             "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 0,
                                   "traits": {"honor": 80, "loyalty": 85}},
                         "relation": 45, "karma": 20, "stones": -10,
                         "text": "«Ti devo la vita», dice {npc}. «Se mai ti servirà una spada "
                                 "al fianco, chiamami». (Potresti chiedergli di seguirti: "
                                 "'recruit {npc}')"}},
            {"label": "Gli indichi la città più vicina e prosegui",
             "effects": {"spawn": {"archetype": "vagabondo", "tier_offset": 0},
                         "relation": 10}},
        ],
    },
    {
        "key": "patto_demoniaco", "once": True, "title": "La voce nel buio", "weight": 6,
        "req": {"types": ["forbidden_zone", "ruin"], "danger_min": 4},
        "text": ("Una voce suadente sale dalle ombre: «Ti darò il potere che il Cielo ti nega. "
                 "Chiedo soltanto un piccolo patto… nulla che ti serva davvero»."),
        "choices": [
            {"label": "Accetti il patto",
             "effects": {"cultivation_progress": 0.6, "karma": -120, "residue": 15,
                         "suspicion": 15, "title": "Segnato dal Patto",
                         "text": "Un fuoco nero ti riempie le vene. Qualcosa in te ora ha un padrone."}},
            {"label": "Rifiuti e scacci la voce dalla mente",
             "check": {"stat": "anima", "dc": 72},
             "success": {"aff_soul": 2, "karma": 20},
             "failure": {"injury": 3, "text": "La voce graffia la tua mente prima di tacere."}},
            {"label": "Provi a intrappolare il demone nella tua anima",
             "check": {"stat": "anima", "dc": 95},
             "success": {"grow_soul": 6, "title": "Domatore di Demoni",
                         "text": "Il demone urla, poi tace: la sua forza è tua."},
             "failure": {"injury": 6, "karma": -10,
                         "text": "Il demone ti si rivolta contro e ti lacera dall'interno."}},
        ],
    },
    {
        "key": "mercante_pillole", "title": "La pillola miracolosa", "weight": 8,
        "req": {"types": ["city"]},
        "text": ("{npc}, un mercante dalle vesti logore, ti mostra una pillola dorata. «Pillola "
                 "della Rinascita Celeste, l'ultima. Per te soltanto trenta pietre»."),
        "choices": [
            {"label": "La compri",
             "check": {"stat": "fortuna", "dc": 68},
             "success": {"stones": -30,
                         "item": {"name": "Pillola della Rinascita Celeste", "item_type": "pillola",
                                  "rarity": "prezioso", "desc": "Autentica, incredibilmente.",
                                  "effects": {"cultivation_progress": 0.7}},
                         "text": "Incredibilmente, è autentica."},
             "failure": {"stones": -30, "text": "A casa scopri che è fango e miele."}},
            {"label": "Lo smascheri davanti alla folla",
             "check": {"stat": "anima", "dc": 60},
             "success": {"fame": 4, "stones": 15,
                         "text": "La folla ride; {npc} ti allunga quindici pietre purché taccia."},
             "failure": {"text": "Non hai prove: il mercante sparisce tra la folla."}},
            {"label": "Lo ignori", "effects": {}},
        ],
    },
    {
        "key": "bisca", "title": "La bisca delle pietre", "weight": 6,
        "req": {"types": ["city"]},
        "text": ("In un retrobottega fumoso si gioca a dadi con pietre spirituali. Un coltivatore "
                 "dalla barba unta ti fa posto: «Una mano sola, straniero?»"),
        "choices": [
            {"label": "Punti 20 pietre",
             "check": {"stat": "fortuna", "dc": 70},
             "success": {"stones": 45}, "failure": {"stones": -20}},
            {"label": "Bari guidando i dadi con un filo di Qi",
             "check": {"stat": "qi", "dc": 75},
             "success": {"stones": 80, "karma": -15},
             "failure": {"stones": -20, "infamy": 8, "injury": 2,
                         "text": "Ti scoprono. Ti buttano in strada a calci."}},
            {"label": "Te ne vai", "effects": {}},
        ],
    },
    {
        "key": "tomba_generale", "once": True, "title": "La tomba del generale", "weight": 7,
        "req": {"types": ["ruin"]},
        "text": ("Una tomba dell'epoca dimenticata: l'effigie di un generale in armatura, il sigillo "
                 "intatto. Intorno, nessun segno di saccheggio. Strano."),
        "choices": [
            {"label": "Profani la tomba",
             "check": {"stat": "fortuna", "dc": 58},
             "success": {"stones": 80, "karma": -30},
             "failure": {"injury": 4, "karma": -30,
                         "text": "Una maledizione antica si risveglia e ti morde."}},
            {"label": "Rendi omaggio al generale",
             "effects": {"karma": 25, "dao_key": "random", "dao_gain": 3,
                         "text": "Inchinandoti, intuisci qualcosa della sua via marziale."}},
        ],
    },
    {
        "key": "ladruncolo", "title": "Il borseggiatore", "weight": 6,
        "req": {"types": ["city"]},
        "text": ("Un ragazzino ti urta e scappa via veloce: la tua borsa di pietre è più leggera."),
        "choices": [
            {"label": "Lo insegui tra i vicoli",
             "check": {"stat": "istinto", "dc": 58},
             "success": {"stones": 10, "text": "Lo raggiungi: aveva anche il bottino di altri."},
             "failure": {"stones": -15, "text": "Sparisce nella folla."}},
            {"label": "Lasci perdere: forse ne ha più bisogno di te",
             "effects": {"stones": -15, "karma": 15}},
        ],
    },
    {
        "key": "eremita_weiqi", "title": "La partita dell'eremita", "weight": 7,
        "req": {"types": ["mountain"]},
        "text": ("Su un pianoro, un eremita — {npc} — gioca a weiqi da solo. Senza alzare lo "
                 "sguardo indica la sedia vuota di fronte a sé."),
        "choices": [
            {"label": "Ti siedi e giochi",
             "check": {"stat": "coltivazione", "dc": 70},
             "success": {"spawn": {"archetype": "eremita", "tier_offset": 2},
                         "relation": 35, "dao_key": "random", "dao_gain": 6,
                         "text": "A ogni pietra posata capisci qualcosa del tuo Dao. {npc} "
                                 "annuisce: «Torna quando vuoi». (Potresti chiedergli di farti "
                                 "da maestro: 'disciple {npc}')"},
             "failure": {"spawn": {"archetype": "eremita", "tier_offset": 2}, "relation": 12,
                         "text": "Perdi malamente. {npc} sorride: «Almeno hai giocato»."}},
            {"label": "Declini con un inchino", "effects": {}},
        ],
    },
    {
        "key": "fame_abisso", "title": "La fame dell'Abisso", "weight": 9,
        "req": {"anomaly": "abisso_divoratore"},
        "text": ("L'Abisso si agita dentro di te: fiuta un coltivatore morente poco lontano. "
                 "Lo senti, nitido come un profumo. Basterebbe un passo."),
        "choices": [
            {"label": "Lo raggiungi e lo divori prima che spiri",
             "effects": {"residue": 10, "cultivation_progress": 0.3, "karma": -30,
                         "text": "La sua vita scivola nella tua. L'Abisso tace, sazio."}},
            {"label": "Stringi i denti e resisti",
             "check": {"stat": "anima", "dc": 72},
             "success": {"residue": -8, "aff_soul": 2,
                         "text": "La fame si ritira. Per ora sei tu a comandare."},
             "failure": {"residue": 5, "injury": 2,
                         "text": "La fame ti piega in due, ma non cedi del tutto."}},
        ],
    },
    {
        "key": "carovana_setta", "title": "La carovana della setta", "weight": 8,
        "req": {"in_sect": True},
        "text": ("Un messaggero della tua setta ti raggiunge trafelato: una carovana di pietre è "
                 "assalita dai predoni non lontano da {luogo}. Gli anziani contano su di te."),
        "choices": [
            {"label": "Corri a difenderla",
             "check": {"stat": "potenza", "dc": 66},
             "success": {"merit": 25, "fame": 5, "stones": 20},
             "failure": {"merit": 6, "injury": 3,
                         "text": "Salvi metà del carico, a caro prezzo."}},
            {"label": "Rifiuti: hai altro da fare",
             "effects": {"text": "Il messaggero annota il tuo nome. Gli anziani ricorderanno."}},
        ],
    },
    {
        "key": "fiore_anima", "title": "Il Fiore dell'Anima", "weight": 5,
        "req": {"types": ["forbidden_zone"], "danger_min": 3},
        "text": ("Tra le pietre nere cresce un fiore pallido che canta piano. Chi ne respira il "
                 "polline sente la propria anima allargarsi — o sgretolarsi."),
        "choices": [
            {"label": "Ne respiri il polline",
             "check": {"stat": "anima", "dc": 74},
             "success": {"grow_soul": 4, "aff_soul": 1},
             "failure": {"injury": 3, "text": "Il canto diventa un urlo dentro il cranio."}},
            {"label": "Lo cogli per più tardi",
             "effects": {"item": {"name": "Fiore dell'Anima", "item_type": "nucleo",
                                  "rarity": "raro", "desc": "Rafforza l'anima.",
                                  "effects": {"grow_soul": 3}}}},
        ],
    },
    {
        "key": "duello_spada", "once": True, "title": "La spada nella roccia", "weight": 5,
        "req": {"types": ["mountain", "ruin"]},
        "text": ("Una spada arrugginita è conficcata in un masso fino all'elsa. Attorno, decine "
                 "di impronte: in molti ci hanno provato."),
        "choices": [
            {"label": "Provi a estrarla con la forza",
             "check": {"stat": "corpo", "dc": 88},
             "success": {"dao_key": "spada", "dao_gain": 8, "title": "Colui che Estrasse la Spada",
                         "text": "La roccia si apre come burro. La ruggine cade: sotto, la lama canta."},
             "failure": {"grow_strength": 1, "text": "Non si muove. Almeno le braccia ringraziano."}},
            {"label": "Mediti sulla spada senza toccarla",
             "check": {"stat": "coltivazione", "dc": 65},
             "success": {"dao_key": "spada", "dao_gain": 4},
             "failure": {"text": "La spada tace."}},
        ],
    },
]
