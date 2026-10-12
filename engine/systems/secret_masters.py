"""
MAESTRI SEGRETI — chi raggiunge certe vette in un'arte attira chi la padroneggia.

Ispirati ai grandi topoi del wuxia/xianxia:
  - il vecchio eremita nascosto sulla rupe che insegna la spada a chi è degno (Feng Qingyang
    e le Nove Spade di Dugu, in "Il sorridente, orgoglioso vagabondo");
  - la tomba delle spade e le quattro spade di Dugu Qiubai: affilata, pesante, di legno,
    nessuna spada;
  - il maestro prigioniero sotto il lago che insegna l'arte di succhiare l'energia altrui
    (la Grande Tecnica dell'Assorbimento delle Stelle) — potente ma pericolosa;
  - le arti proibite dal prezzo terribile (il Manuale del Girasole, il Pugno dei Sette Danni
    che ferisce anche chi lo usa);
  - il mendicante dalle dita mancanti che insegna i Palmi del Drago in cambio di un buon pasto
    (Hong Qigong e Guo Jing);
  - l'anima del grande alchimista nascosta in un anello (Yao Lao in "Battle Through the
    Heavens") e la caccia alle fiamme strane;
  - il monaco che spazza il cortile e nasconde un'arte suprema.

Ogni VIA ha maestri INFINITI a livelli crescenti, come i regni: il successivo appare solo
se hai appreso dal precedente E hai raggiunto una soglia più alta (e un regno più alto).
Oltre ai maestri scritti a mano, il mondo genera maestri sempre più antichi e potenti
— fino alle vette più alte. Quando le condizioni sono
soddisfatte, il maestro può comparirti davanti nei luoghi giusti (scena a scelta).
'masters' mostra chi hai incontrato e quanto manca al prossimo.
"""

from __future__ import annotations

import random
import sqlite3

from engine.core import entities
from engine.systems import state

LEARNED_KEY = "masters_learned"

# requisiti: ("dao", chiave, valore) | ("stat", contatore game_state, valore) |
#            ("prof", professione, livello) | ("fame", valore) | ("karma_ge", v) |
#            ("absorbed", v) | ("beast", rarità minima) | ("anomaly", nome)
# insegnamento: name, magnitude (+% potenza), proc (stato, prob, potenza) opzionale,
#               cost {karma, infamy, lifespan, aff_soul, ...}, bonus {prof_xp, beast_talent,
#               weapon_rarity, item, lifespan_years}, gift (materiali richiesti)
MASTERS = [
    # ---------------- VIA DELLA SPADA ----------------
    {"key": "spada_1", "path": "Spada", "tier": 1, "req": [("dao", "spada", 50)], "where": ["mountain"],
     "name": "Il Vecchio della Rupe",
     "text": "Su una rupe battuta dal vento, un vecchio dalla barba bianca osserva il tuo modo di "
             "impugnare l'arma. «Troppe forme. La spada non ha forma. Siediti.»",
     "teach": {"name": "Nove Forme della Spada Solitaria", "magnitude": 0.12,
               "proc": ("emorragia", 0.15, 1.3)}},
    {"key": "spada_2", "path": "Spada", "tier": 2, "req": [("dao", "spada", 250)], "where": ["mountain", "ruin"],
     "name": "Il Custode della Tomba delle Spade",
     "text": "Una grande aquila ti guida fino a una valle nascosta: tre tombe di spade. Sulla "
             "pietra: «Affilata a vent'anni, pesante a trenta, di legno a quaranta.»",
     "teach": {"name": "Spada Pesante Senza Filo", "magnitude": 0.20,
               "proc": ("stordimento", 0.12, 1.0)}},
    {"key": "spada_3", "path": "Spada", "tier": 3, "req": [("dao", "spada", 1000)], "where": ["mountain"],
     "name": "Colui che Non Ha Più Spada",
     "text": "Un uomo senza armi ti sbarra la strada e taglia una foglia con un filo d'erba. «Quando "
             "anche l'erba è la tua spada, non ti servirà più nient'altro.»",
     "teach": {"name": "La Spada che Non Esiste", "magnitude": 0.35,
               "proc": ("emorragia", 0.30, 2.0)}},
    # ---------------- VIA DEMONIACA (uccisioni) ----------------
    {"key": "demone_1", "path": "Demoniaca", "tier": 1, "req": [("stat", "kills_human", 10)],
     "where": ["forbidden_zone", "ruin"], "name": "Il Prigioniero sotto il Lago",
     "text": "In una cella sommersa, incatenato da anni, un uomo ride nel buio. «Hai le mani "
             "sporche, ragazzo. Bene. Ti insegnerò a prendere la forza degli altri.»",
     "teach": {"name": "Arte dell'Assorbimento delle Stelle", "magnitude": 0.10,
               "proc": ("drenaggio", 0.25, 1.5), "cost": {"karma": -100, "aff_soul": -3},
               "warn": "L'energia rubata non si accorda: la tua anima ne resta incrinata."}},
    {"key": "demone_2", "path": "Demoniaca", "tier": 2, "req": [("stat", "kills_human", 100)],
     "where": ["forbidden_zone"], "name": "Il Signore del Mare di Sangue",
     "text": "Il sangue che hai versato forma un sentiero. In fondo, su un trono d'ossa, qualcuno "
             "ti aspetta. «Cento vite. Ora sei pronto per i Sette Danni.»",
     "teach": {"name": "Pugno dei Sette Danni", "magnitude": 0.25,
               "proc": ("emorragia", 0.25, 1.8), "cost": {"lifespan": -10, "karma": -150},
               "warn": "Ogni colpo ferisce anche te: perdi dieci anni di vita."}},
    {"key": "demone_3", "path": "Demoniaca", "tier": 3, "req": [("stat", "kills_human", 1000)],
     "where": ["forbidden_zone"], "name": "L'Imperatore Demoniaco Senza Nome",
     "text": "Il cielo si fa nero a mezzogiorno. Una voce che è mille voci: «Mille vite. Il mondo "
             "ti teme già. Ora ti insegnerò a capovolgere il Cielo.»",
     "teach": {"name": "Sutra del Cielo Capovolto", "magnitude": 0.45,
               "proc": ("terrore", 0.35, 2.0), "cost": {"karma": -300, "infamy": 200},
               "warn": "Il tuo nome diventa una maledizione."}},
    # ---------------- ALCHIMIA ----------------
    {"key": "alchimia_1", "path": "Alchimia", "tier": 1, "req": [("prof", "alchimia", 3)], "where": ["ruin", "city"],
     "name": "L'Anima nell'Anello",
     "text": "Tra le rovine trovi un vecchio anello nero. Quando lo infili, una voce stanca: «Un "
             "alchimista, finalmente. Un tempo ero il primo del continente. Ti mostrerò il fuoco vero.»",
     "teach": {"name": "Arte della Fiamma Interiore", "magnitude": 0.06,
               "proc": ("ustione", 0.15, 1.3), "bonus": {"prof_xp": 20}}},
    {"key": "alchimia_2", "path": "Alchimia", "tier": 2, "req": [("prof", "alchimia", 6)],
     "where": ["mountain", "forbidden_zone"], "name": "Il Collezionista di Fiamme Strane",
     "text": "Un uomo dagli occhi color brace tiene nove fiamme in nove lanterne. «Ogni fiamma "
             "strana che domini rende la tua alchimia, e il tuo pugno, più ardenti.»",
     "teach": {"name": "Fiamma del Loto Verde", "magnitude": 0.14,
               "proc": ("ustione", 0.25, 2.0), "bonus": {"prof_xp": 35}}},
    {"key": "alchimia_3", "path": "Alchimia", "tier": 3, "req": [("prof", "alchimia", 9)], "where": ["mountain"],
     "name": "Il Dio delle Pillole",
     "text": "Una nube di profumi ti avvolge. Un vecchio sorridente ti porge una pillola che "
             "brilla come una stella. «Questa non si vende. Si merita.»",
     "teach": {"name": "Canone delle Diecimila Pillole", "magnitude": 0.15,
               "bonus": {"prof_xp": 50, "lifespan_years": 100}}},
    # ---------------- TALISMANI ----------------
    {"key": "talismani_1", "path": "Talismani", "tier": 1, "req": [("prof", "talismani", 3)], "where": ["city", "ruin"],
     "name": "Il Calligrafo Cieco",
     "text": "Un vecchio cieco dipinge sigilli perfetti senza guardare. «Il talismano non si "
             "scrive con gli occhi. Si scrive con il Qi.»",
     "teach": {"name": "Sigillo del Pennello Interiore", "magnitude": 0.06,
               "proc": ("stordimento", 0.08, 1.0), "bonus": {"prof_xp": 20}}},
    {"key": "talismani_2", "path": "Talismani", "tier": 2, "req": [("prof", "talismani", 6)], "where": ["ruin"],
     "name": "La Maestra dei Mille Sigilli",
     "text": "Mille talismani fluttuano in una sala sotterranea. Una donna li dirige come un "
             "coro. «Un talismano è una legge in miniatura. Impara a scriverne mille insieme.»",
     "teach": {"name": "Formazione dei Mille Sigilli", "magnitude": 0.12,
               "proc": ("gelo", 0.12, 1.0), "bonus": {"prof_xp": 35}}},
    {"key": "talismani_3", "path": "Talismani", "tier": 3, "req": [("prof", "talismani", 9)], "where": ["mountain"],
     "name": "Il Pennello che Scrive il Cielo",
     "text": "Sulla vetta, un pennello gigante traccia caratteri tra le nuvole. Dove scrive "
             "«tuono», cade il fulmine.",
     "teach": {"name": "Scrittura Celeste", "magnitude": 0.18,
               "proc": ("stordimento", 0.20, 1.5), "bonus": {"prof_xp": 50}}},
    # ---------------- FORGIA ----------------
    {"key": "forgia_1", "path": "Forgia", "tier": 1, "req": [("prof", "forgia", 3)], "where": ["mountain", "city"],
     "name": "Il Fabbro Muto della Montagna",
     "text": "In una fucina scavata nella roccia, un fabbro muto ti indica il martello. Per tre "
             "giorni battete il ferro insieme, senza una parola.",
     "teach": {"name": "Martello della Montagna", "magnitude": 0.07, "bonus": {"prof_xp": 20, "weapon_rarity": 1}}},
    {"key": "forgia_2", "path": "Forgia", "tier": 2, "req": [("prof", "forgia", 6)], "where": ["forbidden_zone"],
     "name": "Il Forgiatore di Spiriti",
     "text": "Le armi appese alle pareti sussurrano. «Ognuna ha un'anima. La tua sta ancora "
             "dormendo. Svegliamola.»",
     "teach": {"name": "Arte dell'Arma Viva", "magnitude": 0.12, "bonus": {"prof_xp": 35, "weapon_spirit": True}}},
    {"key": "forgia_3", "path": "Forgia", "tier": 3, "req": [("prof", "forgia", 9)], "where": ["mountain"],
     "name": "Il Fabbro degli Dei",
     "text": "Una fucina sospesa sopra le nuvole, alimentata da una stella. «Le armi degli "
             "immortali le ho forgiate io. Ora tocca a te.»",
     "teach": {"name": "Forgia della Stella Caduta", "magnitude": 0.20, "bonus": {"prof_xp": 50, "weapon_rarity": 2}}},
    # ---------------- FORMAZIONI ----------------
    {"key": "formazioni_1", "path": "Formazioni", "tier": 1, "req": [("prof", "formazioni", 3)],
     "where": ["ruin", "mountain"], "name": "Il Vecchio delle Bandiere Spezzate",
     "text": "Tra le rovine, un vecchio sposta sassi e bastoncini: all'improvviso la nebbia ti chiude "
             "in un labirinto. Ride. «Hai camminato dentro la mia formazione per un'ora. Siediti.»",
     "teach": {"name": "Labirinto delle Otto Porte", "magnitude": 0.07,
               "proc": ("confusione", 0.12, 1.0), "bonus": {"prof_xp": 20}}},
    {"key": "formazioni_2", "path": "Formazioni", "tier": 2, "req": [("prof", "formazioni", 6)],
     "where": ["forbidden_zone", "mountain"], "name": "La Signora delle Stelle Incise",
     "text": "Su un altopiano, mille pietre formano una mappa del cielo. Una donna le sposta di un "
             "dito, e le stelle sopra di voi si muovono. «Una formazione è una legge che obbedisce a te.»",
     "teach": {"name": "Formazione dei Cinque Elementi Rotanti", "magnitude": 0.15,
               "proc": ("ustione", 0.15, 1.5), "bonus": {"prof_xp": 35}}},
    {"key": "formazioni_3", "path": "Formazioni", "tier": 3, "req": [("prof", "formazioni", 9)],
     "where": ["mountain"], "name": "L'Architetto del Grande Sigillo Celeste",
     "text": "Una montagna intera è una formazione, e tu ci sei dentro da giorni senza saperlo. "
             "In cima, un uomo senza età: «Chi sigilla i cieli può sigillare chiunque.»",
     "teach": {"name": "Grande Formazione che Sigilla il Cielo", "magnitude": 0.22,
               "proc": ("pressione", 0.20, 2.0), "bonus": {"prof_xp": 50}}},
    # ---------------- DOMATORI DI BESTIE ----------------
    {"key": "domatore_1", "path": "Domatore", "tier": 1, "req": [("prof", "domatore", 3)],
     "where": ["mountain", "forbidden_zone"], "name": "La Ragazza che Parla ai Lupi",
     "text": "Un branco di lupi spirituali ti circonda… e si siede. Dietro di loro, una ragazza "
             "scalza ride: «Ti hanno annusato e dicono che hai buon cuore per le bestie.»",
     "teach": {"name": "Canto del Branco", "magnitude": 0.06, "bonus": {"prof_xp": 20, "beast_stages": 3}}},
    {"key": "domatore_2", "path": "Domatore", "tier": 2, "req": [("prof", "domatore", 6)],
     "where": ["forbidden_zone"], "name": "Il Vecchio dell'Isola delle Diecimila Bestie",
     "text": "Una tartaruga grande come un'isola emerge dal lago. Sul guscio, un vecchio pesca. "
             "«Le bestie non si domano. Si diventa loro fratelli di sangue.»",
     "teach": {"name": "Patto di Sangue delle Diecimila Bestie", "magnitude": 0.12,
               "bonus": {"prof_xp": 35, "beast_talent": 1}}},
    {"key": "domatore_3", "path": "Domatore", "tier": 3, "req": [("prof", "domatore", 9)],
     "where": ["mountain"], "name": "Il Pastore dei Draghi",
     "text": "Sulla vetta, draghi e fenici dormono intorno a un uomo che suona il flauto. "
             "«Anche loro furono cuccioli, un tempo. Ti insegnerò a far nascere una stirpe.»",
     "teach": {"name": "Flauto che Risveglia le Stirpi Antiche", "magnitude": 0.18,
               "bonus": {"prof_xp": 50, "beast_talent": 2, "beast_stages": 5}}},
    # ---------------- SANGUE ANTICO (lignaggi) ----------------
    {"key": "sangue_1", "path": "Sangue Antico", "tier": 1, "req": [("blood", 30)],
     "where": ["forbidden_zone", "mountain"], "name": "La Vecchia dagli Occhi di Serpente",
     "text": "Una vecchia ti annusa il polso e sorride con pupille verticali. «Sangue che non è tuo, "
             "e che non sai usare. Siediti: ti insegno ad ascoltarlo.»",
     "teach": {"name": "Respiro del Sangue Antico", "magnitude": 0.07,
               "proc": ("emorragia", 0.12, 1.2), "bonus": {"blood_conc": 25}}},
    {"key": "sangue_2", "path": "Sangue Antico", "tier": 2, "req": [("blood", 200)],
     "where": ["forbidden_zone"], "name": "Il Re delle Chimere",
     "text": "Ha le corna di un drago, le ali di una fenice e gli occhi di un uomo stanco. «Ho fuso "
             "nove lignaggi. Tu quanti ne reggerai?»",
     "teach": {"name": "Arte dei Nove Sangui", "magnitude": 0.14,
               "proc": ("terrore", 0.15, 1.5), "bonus": {"blood_conc": 120}}},
    {"key": "sangue_3", "path": "Sangue Antico", "tier": 3, "req": [("blood", 1200)],
     "where": ["mountain"], "name": "L'Antenato delle Bestie Sacre",
     "text": "La montagna respira. Poi apre un occhio grande come un lago: non era una montagna. "
             "«Piccolo parente. Il tuo sangue ha chiamato, e io ho risposto.»",
     "teach": {"name": "Ritorno alla Forma Ancestrale", "magnitude": 0.22,
               "proc": ("pressione", 0.20, 2.0), "bonus": {"blood_conc": 600, "lifespan_years": 200}}},
    # ---------------- FULMINE / CORPO / ANIMA ----------------
    {"key": "fulmine_1", "path": "Fulmine", "tier": 1, "req": [("dao", "fulmine", 100)], "where": ["mountain"],
     "name": "L'Eremita che Beve i Fulmini",
     "text": "Durante una tempesta, un vecchio a torso nudo apre la bocca al cielo e INGHIOTTE "
             "una folgore. Poi ti guarda: «Vuoi provare?»",
     "teach": {"name": "Respiro del Tuono", "magnitude": 0.14, "proc": ("stordimento", 0.15, 1.3)}},
    {"key": "fulmine_2", "path": "Fulmine", "tier": 2, "req": [("dao", "fulmine", 500)], "where": ["mountain"],
     "name": "Il Signore delle Tribolazioni",
     "text": "Un uomo che ha superato nove tribolazioni ti attende in un cratere di vetro. «Il "
             "Cielo ti colpirà sempre. Impara a restituirgli il colpo.»",
     "teach": {"name": "Folgore Restituita", "magnitude": 0.28, "proc": ("stordimento", 0.25, 2.0)}},
    {"key": "corpo_1", "path": "Corpo", "tier": 1, "req": [("dao", "corpo", 100)], "where": ["city", "mountain"],
     "name": "Il Monaco che Spazza il Cortile",
     "text": "Nel cortile di un tempio, un vecchio monaco spazza le foglie da quarant'anni. Una "
             "foglia ti colpisce e ti scaglia a terra. «Il corpo è un tempio. Il tuo è in rovina.»",
     "teach": {"name": "Corpo d'Oro Indistruttibile", "magnitude": 0.14, "proc": ("scudo", 0.25, 2.0)}},
    {"key": "corpo_2", "path": "Corpo", "tier": 2, "req": [("dao", "corpo", 500)], "where": ["mountain"],
     "name": "Il Gigante Dormiente",
     "text": "Quella che credevi una montagna apre gli occhi. «Piccolo. Il tuo corpo è quasi "
             "degno. Ti insegnerò a diventare montagna.»",
     "teach": {"name": "Corpo della Montagna Primordiale", "magnitude": 0.26, "proc": ("rigenerazione", 0.25, 2.0)}},
    {"key": "anima_1", "path": "Anima", "tier": 1, "req": [("dao", "anima", 100)], "where": ["forbidden_zone", "ruin"],
     "name": "La Dama del Sogno",
     "text": "Ti addormenti tra le rovine e sogni una donna che tesse fili di luce. «Nel sogno "
             "il tuo spirito è libero. Impara a portarlo con te da sveglio.»",
     "teach": {"name": "Tessitura dello Spirito", "magnitude": 0.12, "proc": ("pressione", 0.20, 1.5)}},
    {"key": "anima_2", "path": "Anima", "tier": 2, "req": [("dao", "anima", 500)], "where": ["forbidden_zone"],
     "name": "Lo Spirito Senza Corpo",
     "text": "Una presenza senza forma ti attraversa. Per un istante vedi con mille occhi.",
     "teach": {"name": "Sguardo dei Mille Occhi", "magnitude": 0.25, "proc": ("confusione", 0.20, 1.5)}},
    # ---------------- GIUSTIZIA (fama + karma) ----------------
    {"key": "giusto_1", "path": "Giustizia", "tier": 1, "req": [("fame", 200), ("karma_ge", 100)],
     "where": ["city"], "name": "Il Mendicante dalle Nove Dita",
     "text": "Un mendicante a cui manca un dito annusa l'aria. «Si dice che tu sia un eroe. Gli "
             "eroi sanno cucinare? Portami un buon pasto e ti insegno qualcosa che vale un regno.»",
     "gift": {"erbe": 3},
     "teach": {"name": "Diciotto Palmi del Drago", "magnitude": 0.20, "proc": ("stordimento", 0.15, 1.5)}},
    {"key": "giusto_2", "path": "Giustizia", "tier": 2, "req": [("fame", 1000), ("karma_ge", 300)],
     "where": ["mountain"], "name": "Il Saggio della Vetta d'Oriente",
     "text": "In cima alla vetta più alta d'oriente, cinque sedie di pietra. Quattro sono vuote "
             "da secoli. Sulla quinta, un vecchio ti sorride: «Il quinto grande, finalmente.»",
     "teach": {"name": "Arte Innata del Cielo", "magnitude": 0.35, "proc": ("vita", 0.20, 2.0)}},
    # ---------------- BESTIE ----------------
    {"key": "bestie_1", "path": "Bestie", "tier": 1, "req": [("beast", "rara")], "where": ["mountain", "forbidden_zone"],
     "name": "Il Vecchio dei Mille Animali",
     "text": "Un vecchio circondato da lupi, tigri e aquile accarezza la tua bestia. «È più "
             "dotata di quanto pensi. Lascia che le mostri chi è davvero.»",
     "teach": {"name": "Linguaggio delle Bestie", "magnitude": 0.06, "bonus": {"beast_talent": 1}}},
    {"key": "bestie_2", "path": "Bestie", "tier": 2, "req": [("beast", "leggendaria")], "where": ["mountain"],
     "name": "La Madre dei Draghi",
     "text": "Un'ombra immensa copre il sole. Una donna scende dal dorso di un drago d'argento. "
             "«Una creatura leggendaria ti ha scelto. Insegnerò a entrambi a volare.»",
     "teach": {"name": "Patto del Cielo e della Bestia", "magnitude": 0.15, "bonus": {"beast_talent": 1, "beast_stages": 5}}},
    # ---------------- ABISSO ----------------
    {"key": "abisso_1", "path": "Abisso", "tier": 1, "req": [("anomaly", "abisso_divoratore"), ("absorbed", 10)],
     "where": ["forbidden_zone", "ruin"], "name": "L'Ombra del Primo Divoratore",
     "text": "Nel buio, la tua ombra si stacca da te e prende un altro volto. «Sono stato il primo "
             "a portare l'Abisso. Ti mostrerò come si mangia senza essere mangiati.»",
     "teach": {"name": "Fauci del Primo Divoratore", "magnitude": 0.18, "proc": ("drenaggio", 0.25, 2.0),
               "bonus": {"residue": -50}}},
]




# ============================================================
# Maestri INFINITI: oltre quelli scritti a mano, ogni via ne genera altri
# ============================================================

# ruolo del maestro per via (nome generato: "<ruolo>, <titolo del regno>")
_ROLE = {
    "Spada": "Il Santo della Spada", "Demoniaca": "Il Patriarca Demoniaco",
    "Alchimia": "Il Venerabile delle Pillole", "Talismani": "Il Maestro dei Sigilli",
    "Forgia": "Il Fabbro Celeste", "Fulmine": "Il Signore del Tuono", "Corpo": "Il Corpo Immortale",
    "Anima": "Lo Spirito Antico", "Giustizia": "Il Giusto Sovrano", "Bestie": "Il Re delle Bestie",
    "Abisso": "L'Eco dell'Abisso", "Formazioni": "Il Gran Maestro delle Formazioni",
    "Domatore": "Il Sovrano delle Diecimila Bestie", "Sangue Antico": "L'Antenato del Sangue",
}
# radice delle tecniche generate per via
_TECH_STEM = {
    "Spada": "Spada", "Demoniaca": "Arte Proibita", "Alchimia": "Fiamma Alchemica",
    "Talismani": "Sigillo", "Forgia": "Martello", "Fulmine": "Folgore", "Corpo": "Corpo",
    "Anima": "Intento dell'Anima", "Giustizia": "Palmo", "Bestie": "Patto", "Abisso": "Fauci",
    "Formazioni": "Formazione", "Domatore": "Patto delle Stirpi", "Sangue Antico": "Forma del Sangue",
}
_EPITHETS = ["dell'Eternità", "del Firmamento", "dei Nove Cieli", "del Vuoto Primordiale",
             "delle Diecimila Ere", "dell'Origine", "oltre il Cielo", "senza Nome", "della Fine dei Tempi"]
_SCENES = [
    "Il cielo si apre come una porta. Qualcuno ti attendeva da molto prima che tu nascessi: {name}.",
    "Un vecchio siede su una nuvola immobile. «Hai salito molto. Ora vedrai quanto ancora resta.» È {name}.",
    "Il tempo si ferma. Tra un respiro e l'altro compare {name}: «La via non finisce mai. Nemmeno io.»",
    "Una stella cade e si fa uomo. {name} ti guarda come si guarda un fratello minore.",
]
_WHERE_ALL = ["mountain", "forbidden_zone", "ruin", "city"]


def _authored(path: str) -> list[dict]:
    return sorted((m for m in MASTERS if m["path"] == path), key=lambda m: m["tier"])


def _slug(path: str) -> str:
    return _authored(path)[0]["key"].rsplit("_", 1)[0]


def _scale_req(req: tuple, k: int):
    kind = req[0]
    # soglie che crescono senza fine, ma con passo sostenibile (il regno richiesto fa il resto)
    if kind == "dao":
        return ("dao", req[1], int(req[2] * (1.5 ** k)))
    if kind == "stat":
        return ("stat", req[1], int(req[2] * (1.6 ** k)))
    if kind == "prof":
        return ("prof", req[1], req[2] + 3 * k)
    if kind == "fame":
        return ("fame", min(90000, int(req[1] * (1.6 ** k))))
    if kind == "karma_ge":
        return ("karma_ge", min(900, int(req[1] * (1.3 ** k))))
    if kind == "absorbed":
        return ("absorbed", int(req[1] * (1.6 ** k)))
    if kind == "beast":
        return ("beast_tier", 3 + 2 * k)
    if kind == "blood":
        return ("blood", int(req[1] * (2.5 ** k)))
    return req


def master_for(path: str, tier: int) -> dict | None:
    """Il maestro di livello `tier` della via (scritto a mano o generato). Mai None per tier>=1."""
    auth = _authored(path)
    if not auth:
        return None
    if tier <= len(auth):
        return auth[tier - 1]
    from engine.generators.cultivation_gen import realm_name_for_tier
    last = auth[-1]
    k = tier - len(auth)                     # quanti livelli oltre l'ultimo maestro scritto
    lt = last["teach"]
    req = [_scale_req(r, k) for r in last["req"]] + [("realm", 2 + tier)]
    name = f"{_ROLE[path]}, {realm_name_for_tier(4 + tier)}"
    epithet = _EPITHETS[(tier - 1) % len(_EPITHETS)]
    cycle = (tier - 1) // len(_EPITHETS)
    tname = f"{_TECH_STEM[path]} {epithet}" + (f" ({cycle + 1}° ciclo)" if cycle else "")
    teach = {"name": tname, "magnitude": round(lt["magnitude"] + 0.10 * k, 2)}
    if lt.get("proc"):
        st, ch, pw = lt["proc"]
        teach["proc"] = (st, min(0.55, ch + 0.03 * k), round(pw + 0.4 * k, 2))
    if lt.get("cost"):
        teach["cost"] = {key: (int(v * (1.5 ** k)) if isinstance(v, int) else v)
                         for key, v in lt["cost"].items() if key != "aff_soul"}
        teach["warn"] = lt.get("warn", "Il potere ha un prezzo.")
    b = dict(lt.get("bonus", {}))
    if b.get("prof_xp"):
        b["prof_xp"] = int(b["prof_xp"] * (1.5 ** k))
    if b.get("lifespan_years"):
        b["lifespan_years"] = int(b["lifespan_years"] * (2 ** k))
    if "weapon_rarity" in b or "weapon_spirit" in b:
        b = {key: v for key, v in b.items() if key not in ("weapon_rarity", "weapon_spirit")}
        b["weapon_tier"] = True
    if "beast_talent" in b or "beast_stages" in b:
        b["beast_stages"] = 5 + 3 * k
        b.pop("beast_talent", None)
    if "blood_conc" in b:
        b["blood_conc"] = int(b["blood_conc"] * (2.5 ** k))
    if "residue" in b:
        b["residue"] = int(b["residue"] * (1.5 ** k))
    if b:
        teach["bonus"] = b
    return {"key": f"{_slug(path)}_{tier}", "path": path, "tier": tier, "req": req,
            "where": last["where"] if k % 2 else _WHERE_ALL, "name": name,
            "text": _SCENES[tier % len(_SCENES)].format(name=name), "teach": teach,
            "generated": True}


def master_by_key(key: str) -> dict | None:
    slug, _, n = key.rpartition("_")
    for path in {m["path"] for m in MASTERS}:
        if _slug(path) == slug and n.isdigit():
            return master_for(path, int(n))
    return None


def paths() -> list[str]:
    return sorted({m["path"] for m in MASTERS})

# ============================================================
# Requisiti
# ============================================================

def learned(conn) -> list[str]:
    return list(state.get_json(conn, LEARNED_KEY, []) or [])


def _progress(conn, pid: int, req: tuple) -> tuple[bool, str]:
    from engine.systems import professions, reputation, karma, character, beasts
    kind = req[0]
    if kind == "dao":
        r = conn.execute("SELECT comprehension FROM character_daos WHERE character_type='player' "
                         "AND character_id=? AND dao_key=?;", (pid, req[1])).fetchone()
        v = (r["comprehension"] or 0) if r else 0
        return v >= req[2], f"Dao «{req[1]}» {v}/{req[2]}"
    if kind == "stat":
        v = state.get_int(conn, req[1], 0)
        label = {"kills_human": "vite umane tolte", "kills_total": "vite tolte"}.get(req[1], req[1])
        return v >= req[2], f"{label} {v}/{req[2]}"
    if kind == "prof":
        v = professions.level(conn, pid, req[1])
        return v >= req[2], f"{req[1]} livello {v}/{req[2]}"
    if kind == "fame":
        v = reputation.get(conn, pid)["fame"]
        return v >= req[1], f"fama {v}/{req[1]}"
    if kind == "karma_ge":
        v = karma.get_karma(conn, "player", pid)
        return v >= req[1], f"karma {'sufficiente' if v >= req[1] else 'ancora insufficiente'}"
    if kind == "absorbed":
        p = character.get_profile(conn, "player", pid)
        v = (p["abs_human"] or 0) if p else 0
        return v >= req[1], f"coltivatori divorati {v}/{req[1]}"
    if kind == "anomaly":
        p = character.get_profile(conn, "player", pid)
        return bool(p and p["anomaly"] == req[1]), "portatore dell'Abisso"
    if kind == "beast":
        order = beasts.RARITY_ORDER
        pt = beasts.pet(conn, pid)
        v = beasts.traits(conn, pt["npc_id"])["rarity"] if pt else None
        ok = bool(v) and order.index(v) >= order.index(req[1])
        return ok, f"una bestia {req[1]} al tuo fianco"
    if kind == "realm":
        from engine.simulation import cultivation
        from engine.generators.cultivation_gen import realm_name_for_tier
        v = cultivation.realm_tier(conn, "player", pid) or 1
        return v >= req[1], f"regno {realm_name_for_tier(req[1])}"
    if kind == "blood":
        from engine.systems import bloodlines
        o = bloodlines.ordered(conn)
        v = int(o[0][1]["conc"]) if o else 0
        return v >= req[1], f"lignaggio di sangue {v}/{req[1]}"
    if kind == "beast_tier":
        from engine.systems import npc_factory
        pt = beasts.pet(conn, pid)
        v = npc_factory.npc_tier(conn, pt["npc_id"]) if pt else 0
        return v >= req[1], f"una bestia al regno {req[1]} (ora {v})"
    return False, "?"


def _learned_in_path(conn, path: str) -> int:
    slug = _slug(path)
    return sum(1 for k in learned(conn) if k.rpartition("_")[0] == slug)


def _next_in_path(conn, path: str) -> dict | None:
    """Il prossimo maestro della via: non finiscono mai."""
    return master_for(path, _learned_in_path(conn, path) + 1)


def available(conn, pid: int = 1) -> list[dict]:
    out = []
    for path in paths():
        m = _next_in_path(conn, path)
        if m and all(_progress(conn, pid, r)[0] for r in m["req"]):
            out.append(m)
    return out


# ============================================================
# Incontro
# ============================================================

def maybe_meet(conn: sqlite3.Connection, player, rng: random.Random | None = None,
               force: str | None = None) -> str | None:
    """Se un maestro è "pronto" e sei in un luogo adatto, a volte compare."""
    from engine.systems import encounters
    if encounters.pending(conn):
        return None
    loc = entities.get_location(conn, player.location_id)
    t = __import__("engine.core.tick", fromlist=["get_tick"]).get_tick(conn)
    rng = rng or random.Random(t * 9091 + player.id)
    seen = state.get_json(conn, "master_seen", {}) or {}
    day = t // 120
    # un maestro che hai già incontrato (e non hai seguito) torna solo dopo un po'
    cands = [m for m in available(conn, player.id) if loc and loc.location_type in m["where"]
             and day - seen.get(m["key"], -999) >= 12]
    if force:
        cands = [m for m in [master_by_key(force)] if m]
    elif not cands or t - state.get_int(conn, "master_last_tick", -999) < 24 or rng.random() > 0.35:
        return None
    m = cands[0]
    state.set(conn, "master_last_tick", str(t))
    seen[m["key"]] = day
    state.set_json(conn, "master_seen", seen)
    return encounters.start_scene(conn, player, _scene(m))


def _scene(m: dict) -> dict:
    teach = m["teach"]
    learn_eff = {"master_learn": m["key"]}
    choices = []
    if m.get("gift"):
        from engine.systems.professions import MATERIALS
        cost = ", ".join(f"{v} {MATERIALS[k]}" for k, v in m["gift"].items())
        choices.append({"label": f"Gli offri ciò che chiede ({cost})",
                        "effects": dict(learn_eff, gift=m["gift"])})
    else:
        choices.append({"label": "Ti inginocchi e chiedi di essere istruito", "effects": learn_eff})
    if teach.get("warn"):
        choices[0]["label"] += f" — {teach['warn']}"
    choices.append({"label": "Declini con rispetto: non è ancora il momento",
                    "effects": {"text": "Il maestro scompare come era venuto. Forse tornerà."}})
    return {"key": f"maestro_{m['key']}", "title": f"Maestro segreto — {m['name']}",
            "event_type": "story", "text": m["text"], "choices": choices,
            "on_leave": f"(Ti allontani: {m['name']} non c'è più. Forse lo ritroverai.)"}


def learn(conn: sqlite3.Connection, t: int, player, key: str, gift: dict | None = None) -> list[str]:
    """Applica l'insegnamento del maestro. Chiamato dagli effetti della scena."""
    from engine.systems import professions, karma, reputation, lifespan, weapons, beasts, npc_factory
    m = master_by_key(key)
    if not m or key in learned(conn):
        return []
    if gift and not professions.spend(conn, player.id, gift):
        return ["«Torna quando avrai ciò che ti ho chiesto.» Il maestro si allontana."]
    tch = m["teach"]
    lines = [f"{m['name']} ti istruisce per giorni. Apprendi: {tch['name']}! "
             f"(+{int(tch['magnitude'] * 100)}% potenza)"]
    conn.execute("INSERT OR IGNORE INTO learned_techniques (player_id, faction_id, tech_key, name, "
                 "magnitude, learned_tick) VALUES (?, NULL, ?, ?, ?, ?);",
                 (player.id, f"maestro:{key}", tch["name"], tch["magnitude"], t))
    if tch.get("proc"):
        procs = state.get_json(conn, "master_procs", []) or []
        st, ch, pw = tch["proc"]
        procs.append([st, ch, pw, tch["name"]])
        state.set_json(conn, "master_procs", procs)
        from engine.systems.combat_states import STATES
        lines.append(f"In battaglia, la tecnica può infliggere: {STATES.get(st, (st,))[0]}.")
    cost = tch.get("cost", {})
    if cost.get("karma"):
        karma.adjust_karma(conn, "player", player.id, cost["karma"], tch["name"], t)
    if cost.get("infamy"):
        reputation.adjust(conn, player.id, infamy=cost["infamy"])
    if cost.get("lifespan"):
        lifespan.add_bonus_years(conn, cost["lifespan"])
        lines.append(f"Il prezzo: {-cost['lifespan']} anni della tua vita.")
    if cost.get("aff_soul"):
        conn.execute("UPDATE character_profiles SET aff_soul=MAX(1, aff_soul+?) "
                     "WHERE character_type='player' AND character_id=?;", (cost["aff_soul"], player.id))
    b = tch.get("bonus", {})
    if b.get("prof_xp") and professions.profession(conn, player.id):
        professions.add_xp(conn, player.id, b["prof_xp"])
        lines.append(f"La tua arte fa un balzo: ora sei al livello {professions.level(conn, player.id)}.")
    if b.get("lifespan_years"):
        lifespan.add_bonus_years(conn, b["lifespan_years"])
        lines.append(f"La pillola che ti dona allunga la tua vita di {b['lifespan_years']} anni.")
    if b.get("weapon_rarity"):
        eq = weapons.get_equipped(conn, player.id)
        if eq:
            weapons._set_equipped(conn, player.id, eq["tier"], min(4, eq["rarity"] + b["weapon_rarity"]))
            lines.append("La tua arma esce dalla fucina trasformata.")
    if b.get("weapon_tier"):
        eq = weapons.get_equipped(conn, player.id)
        if eq:
            from engine.simulation import cultivation
            ptier = cultivation.realm_tier(conn, "player", player.id) or 1
            weapons._set_equipped(conn, player.id, max(eq["tier"], ptier), 4)
            lines.append("La tua arma viene riforgiata alla perfezione, all'altezza del tuo regno.")
    if b.get("weapon_spirit"):
        from engine.systems import weapon_spirit
        lines.append(weapon_spirit.awaken(conn, random.Random(t), player, forced=True))
    if b.get("beast_talent") or b.get("beast_stages"):
        pt = beasts.pet(conn, player.id)
        if pt:
            tr = beasts.traits(conn, pt["npc_id"])
            names = [x[0] for x in beasts.TALENTS]
            new = names[min(len(names) - 1, names.index(tr["talent"]) + b.get("beast_talent", 0))]
            conn.execute("UPDATE beast_traits SET talent=? WHERE npc_id=?;", (new, pt["npc_id"]))
            if b.get("beast_stages"):
                npc_factory.raise_npc(conn, pt["npc_id"], b["beast_stages"])
            lines.append(f"{pt['name']} risveglia il suo vero talento: ora è «{new}».")
    if b.get("blood_conc"):
        from engine.systems import bloodlines
        o = bloodlines.ordered(conn)
        if o:
            lines += bloodlines.gain(conn, t, random.Random(t + 7), player, o[0][1]["species"],
                                     o[0][1]["elements"], float(b["blood_conc"]))
    if b.get("residue"):
        conn.execute("UPDATE character_profiles SET soul_residue=MAX(0, soul_residue+?) "
                      "WHERE character_type='player' AND character_id=?;", (b["residue"], player.id))
        lines.append("L'Abisso dentro di te si fa docile.")
    done = learned(conn)
    done.append(key)
    state.set_json(conn, LEARNED_KEY, done)
    state.grant_title(conn, f"Allievo di {m['name']}")
    from engine.simulation import world_tick
    from engine.systems import training
    world_tick.advance(conn, training.DAY_TICKS)
    nxt = _next_in_path(conn, m["path"])
    if nxt:
        hint = "; ".join(_progress(conn, player.id, r)[1] for r in nxt["req"])
        lines.append(f"«Quando sarai pronto, cerca {nxt['name']}.» (Requisiti: {hint})")
    return lines


def describe(conn, player) -> str:
    lines = ["Maestri segreti — infiniti come i regni: si mostrano solo a chi raggiunge certe vette:"]
    for path in paths():
        n = _learned_in_path(conn, path)
        nxt = _next_in_path(conn, path)
        if any(r[0] == "anomaly" and not _progress(conn, player.id, r)[0] for r in nxt["req"]):
            continue                              # via riservata (es. all'Abisso)
        got = [master_for(path, i)["teach"]["name"] for i in range(1, n + 1)]
        status = (", ".join(got[-3:]) + (f" (+{len(got) - 3} prima)" if len(got) > 3 else "")) \
            if got else "nessuna tecnica"
        prog = "; ".join(_progress(conn, player.id, r)[1] for r in nxt["req"])
        ready = all(_progress(conn, player.id, r)[0] for r in nxt["req"])
        where = "/".join({"mountain": "montagne", "city": "città", "ruin": "rovine",
                          "forbidden_zone": "zone proibite"}[w] for w in nxt["where"])
        lines.append(f"  · Via {path} [maestri: {n}] — {status}. Prossimo ({nxt['name']}): "
                     + (f"PRONTO, cercalo tra {where}" if ready else f"«{prog}»"))
    return "\n".join(lines)
