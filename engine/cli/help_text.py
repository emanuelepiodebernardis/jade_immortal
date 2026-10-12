"""
Testo d'aiuto, diviso per categorie.

`help` mostra l'essenziale e l'elenco delle categorie; `help <categoria>` il dettaglio;
`help tutto` l'elenco completo. Lo stesso elenco alimenta il traduttore di intenti in
linguaggio naturale (engine/cli/intent.py), così i due non vanno mai fuori sincrono.
"""

from __future__ import annotations

# (chiave, titolo, righe "comando — descrizione")
CATEGORIES: list[tuple[str, str, list[str]]] = [
    ("esplorazione", "Esplorazione e viaggio", [
        "mete                          — tutto ciò che sta accadendo nel mondo, numerato, con la distanza",
        "vai <n|meta|luogo>            — raggiungi DIRETTAMENTE una meta o un luogo (es. 'vai 1', 'vai assemblea')",
        "iscriviti <n|meta>            — ci vai e partecipi subito (Assemblea, gara, reame, invasione, famiglia…)",
        "move <north|south|east|west>  (abbrev: n/s/e/w)  — ti sposti, +1 tick",
        "look                          — osservi la location corrente",
        "look <dir>                    — sbirci la location adiacente in quella direzione",
        "map                           — uscite della location corrente con destinazioni",
        "where                         — nome e pericolo della location corrente",
        "wait                          — attendi (il mondo avanza, osservi i dintorni)",
        "sleep                         — dormi fino all'alba del giorno seguente",
        "home                          — torni direttamente alla sede della tua setta",
        "warzone                       — ti porti direttamente al fronte di guerra più vicino",
        "raidtarget                    — ti porti alla sede di una setta rivale (poi 'raid')",
        "events                        — invasioni mondiali in corso (difendi un luogo)",
        "defend                        — difendi il luogo invaso (abbatti l'ondata)",
    ]),
    ("combattimento", "Combattimento e Abisso", [
        "attack <nome> [mossa]         — attacchi un NPC (puoi morire!); mossa attiva opzionale",
        "attack all                    — attacchi TUTTI i nemici presenti (creature e umani), in sequenza",
        "attack humans                 — attacchi solo gli avversari umani presenti",
        "attack creatures              — attacchi solo le creature selvagge presenti",
        "moves                         — le tue mosse attive in combattimento (cooldown)",
        "absorb <nome>                 — (Abisso Divoratore) divori i resti di un caduto",
        "absorb all                    — divori in sequenza tutti i resti presenti",
        "loot                          — raccogli l'eredità dei caduti (e i tesori della tua tomba)",
        "bounties                      — ricercati da cacciare (taglie e missioni)",
        "hunt <nome>                   — localizza un ricercato e ti indica dove andare",
        "rating                        — il tuo profilo di potenza (Qi/Corpo/Anima/Dao), classe e zona",
    ]),
    ("coltivazione", "Coltivazione e Dao", [
        "train (o 't')                 — ALLENAMENTO D'INSIEME: Qi, tutti i tuoi Dao e la tua arte in una sola azione",
        "cultivate (o 'c')             — mediti per accumulare progresso nel tuo regno",
        "breakthrough                  — tenti di salire di regno (può fallire o ucciderti!); a volte appare il demone interiore",
        "dao                           — i Dao che pratichi e la loro comprensione",
        "comprehend <nome>             — affini un Dao (i Dao da combattimento ti rendono più forte)",
        "tribulation                   — sfida al Cielo (heaven defiance) e tribolazione divina",
        "tribolazioni                  — le TRIBOLAZIONI DEL FULMINE a ogni regno: tempra, assorbimento, cariche di fulmine",
        "inventory                     — il tuo zaino (oggetti raccolti)",
        "use <oggetto> | use all       — usi un oggetto dello zaino (o tutti in sequenza)",
        "use essenze | use pillole     — assorbi TUTTE le essenze (o usi tutte le pillole) con un comando solo",
        "use tutte <oggetto>           — usi tutte le copie di quell'oggetto",
        "radici                        — le tue RADICI SPIRITUALI: punteggi, talenti, combinazioni",
        "corpo                         — costituzione speciale, CUORE DEL DAO (deviazione del Qi) e tossine delle pillole",
        "gongfa [pratica <n>|setta]    — i metodi di coltivazione: quale pratichi, cambiarlo, quello della setta",
        "ritiro <giorni> [dao]         — RITIRO a porte chiuse (montagna, rovine, sede, dimora): giorni di coltivazione",
        "classifica [giovani|sette]    — Classifica del Cielo, Lista del Drago Nascente, classifica delle sette",
        "prodigi                       — i PRODIGI della tua generazione: crescono e trovano fortune anche senza di te",
    ]),
    ("mondo", "Reami segreti, Assemblea, aste, mondi superiori", [
        "realm                         — il reame segreto aperto ora (dove, quanto resta) — 'realm esci' per uscire",
        "enter                         — entri nel reame segreto (devi essere all'ingresso)",
        "delve                         — scendi al piano successivo del reame (in fondo, la Sala dell'Eredità)",
        "assemblea [iscriviti|1|2|3]   — la GRANDE ASSEMBLEA dell'Alleanza Marziale: iscrizione e incontri",
        "asta [offri <lotto> <pietre>] — la casa d'aste (in città, quando è aperta)",
        "ascendi_mondo [conferma]      — alla Grande Perfezione del regno più alto del mondo (9, poi 12, 15…) ascendi: diventi il primo regno del mondo superiore, ma lasci indietro oggetti, materiali e 9/10 delle pietre",
        "mondi                         — gli strati di mondo raggiunti — 'up'/'down' per attraversare le porte",
        "sistema [riscuoti|negozio|compra <n>] — (Trasmigratore) missioni e negozio del Sistema",
    ]),
    ("dimora", "Grotta-dimora, discepoli e la tua setta", [
        "dimora                        — la tua grotta-dimora (o come ottenerne una)",
        "dimora reclama                — reclami il luogo selvaggio in cui sei come dimora",
        "dimora                        — il MENU DELLA DIMORA: produzione, ali e «potenzia al massimo»",
        "dimora potenzia <ala>         — erbe · qi · ritiro · alchimia · difesa · stalla (livelli infiniti)",
        "dimora potenzia max [ala]     — porta la dimora (o un'ala) al livello più alto che puoi pagare ora",
        "dimora raccogli | dimora torna — raccogli la produzione | torni a casa",
        "accogli <nome>                — (regno 3+) prendi un discepolo che ti stima ed è più debole",
        "insegna <nome> [dao]          — una lezione al giorno: lui cresce, tu comprendi meglio il Dao",
        "discepoli                     — i tuoi discepoli — 'congeda_discepolo <nome>' per congedarne uno",
        "fonda <nome>                  — (regno 4, dimora, 3 discepoli, 2000 pietre) fondi la tua setta",
        "setta mia | riscuoti | recluta | difendi — la setta che hai FONDATO: pannello, tributi, reclutamento, difesa",
    ]),
    ("setta", "Sette, guerra e mercato", [
        "setta                         — il MENU DELLA SETTA: ascesa, classe e tornei, tecniche, metodo, tesoro del merito, rango, missioni, anziani, guerre",
        "setta ascesa | ascendi <n> | rimanda | rifiuta — salire a una setta superiore (o restare per lealtà)",
        "setta compra <n>              — il tesoro del merito: pillole, pietre, materiali, essenze, stanza di coltivazione",
        "setta promozione | stipendio  — sali di rango col merito | lo stipendio del mese",
        "sects                         — sette a cui iscriversi e dove hanno sede",
        "join                          — test d'ingresso e iscrizione alla setta locale",
        "class                         — compagni di classe, classifica, prossima sfida/torneo",
        "challenge                     — sfidi un discepolo di rango superiore: se vinci, sali di categoria",
        "weapon <arma>                 — scegli l'arma principale (sblocca il Dao d'arma)",
        "arma                          — la tua ARMA VIVA: esperienza, tempra, spirito, nemici illustri",
        "arma nome <nome>              — dai un nome all'arma (quando lo spirito è senziente)",
        "huntzone                      — la zona di caccia della tua setta (mostri = merito)",
        "techniques                    — tecniche segrete della setta e merito disponibile",
        "learn <n>                     — impari una tecnica segreta spendendo merito",
        "invitations                   — inviti delle sette superiori (dopo aver vinto un torneo)",
        "accept <n>                    — accetti un invito e ascendi a una setta superiore",
        "leave                         — lascia la tua setta",
        "anziani                       — gli anziani della tua setta e il loro favore",
        "servi <anziano>               — una giornata al servizio di un anziano (favore, merito)",
        "missioni [accetta <n>|completa] — la bacheca delle missioni di setta",
        "market                        — (in città) il mercato: oggetti da comprare con le pietre",
        "buy <n>                       — compri l'oggetto n dal mercato",
        "war                           — guerra tra sette in corso: fronte, punteggio, tempo",
        "spare <nome>                  — al fronte: sottometti e risparmia un nemico (onore)",
        "raid                          — (alla sede di una setta rivale) la assalti da solo e la saccheggi",
        "invade                        — (rango alto) GUIDI la tua setta a conquistare la setta rivale qui",
        "factions                      — elenco delle fazioni (influenza, territori)",
        "faction <nome>                — dettaglio di una fazione (territori, relazioni)",
    ]),
    ("legami", "Persone e legami", [
        "examine <nome>                — esamini un NPC presente (archetipo, indole, rapporto)",
        "greet <nome>                  — saluti un NPC: prima conoscenza / migliora il rapporto",
        "talk <nome>                   — parli con qualcuno: il rapporto cresce, scopri chi è",
        "gift <nome> <pietre>          — offri pietre spirituali in dono (gli avidi apprezzano)",
        "spar <nome>                   — duello amichevole, non letale: entrambi imparate qualcosa",
        "recruit <nome>                — chiedi a un amico di viaggiare con te come compagno",
        "dismiss                       — congedi il tuo compagno di viaggio",
        "disciple <nome>               — chiedi a un anziano/eremita di farti da maestro",
        "bonds                         — i tuoi legami: compagni, maestro, rivali e nemesi",
        "masters                       — i MAESTRI SEGRETI: chi hai incontrato e cosa serve per il prossimo",
        "richieste                     — chi, qui, ha un incarico per te (catene di 3-5 passi con un grande dono finale)",
        "incarico <n> | incarichi      — accetti una richiesta | i tuoi incarichi in corso e dove andare",
        "consegna                      — consegni erbe o pillole per un incarico di guarigione",
        "giura <nome>                  — giuri fratellanza (rapporto ≥ 70) — 'chiama <nome>' per chiamarlo",
        "duello <nome>                 — DUELLO A TURNI: colpisci, tecniche, difendi, concentrati, fuggi; alla fine decidi tu",
        "parla <nome>                  — con chi ti è vicino (famiglia, compagna, maestro, fratelli…): un DIALOGO a scelta",
        "favori | favore <nome>        — i FAVORI che ti hanno chiesto | esaudiscine uno (cresce l'intimità; da 2 accorrono in tuo aiuto)",
        "proponi <nome>                — lei diventa la tua compagna del Dao (rapporto ≥ 80): doppia coltivazione",
    ]),
    ("raccolta", "Raccolta e assorbimento automatici", [
        "raccogli                      — raccogli il bottino e assorbi essenze, nuclei, manuali e incensi in un colpo",
        "autoraccolta on|off           — il bottino dei caduti finisce da solo nello zaino (acceso di base)",
        "autoassorbi on|off            — essenze, nuclei, manuali e incensi si assorbono appena li ottieni (acceso di base)",
    ]),
    ("rendite", "Rendite: come si guadagna", [
        "rendite                       — il pannello: bottega delle arti, setta, vassalle, servi, razze, corte",
        "rendite riscuoti              — riscuoti in un colpo stipendio, tesoro della tua setta e tributi",
    ]),
    ("tecniche", "Tecniche e fucina: fondere le tecniche", [
        "tecniche                      — il PANNELLO DELLE TECNICHE: tutte le tue tecniche e le fusioni proposte (un clic)",
        "tecniche fondi <n> <m> [<k>]  — fondi due o tre tecniche dell'elenco in una tecnica nuova",
        "tecniche fondi migliore       — la fusione più promettente, in un colpo",
        "tecniche allena <n>           — alleni una tecnica creata (cresce anche usandola in battaglia)",
        "tecniche rinomina <n> <nome>  — le dai il tuo nome | tecniche dimentica <n> — la lasci andare",
        "techniques                    — le tecniche segrete della setta, da apprendere col merito",
    ]),
    ("dominio", "Spirito e dominio: tempra, sigilli dell'anima, salme, sette vassalle", [
        "tempra                        — TEMPRA DELLO SPIRITO: la terza via accanto a Qi e Dao (anche 'train' la allena)",
        "tempra info                   — grado dell'anima e punteggio di spirito",
        "sigilla <nome>                — marchi l'anima di chi hai battuto (se il tuo spirito è più forte): diventa tuo servo",
        "                                (nei duelli vinti c'è la scelta 'gli marchi l'anima')",
        "dominio                       — il MENU DEL DOMINIO: servi, salme, sette vassalle, tributi, guerre",
        "servo <nome> scorta|lavoro|guardia|reggente|rinsalda|libera — il compito di un servo",
        "dominio riscuoti | tecniche | impara <n> | attacca <setta> — le sette vassalle (si ottengono marchiando un patriarca)",
        "rianima <nome>                — (Arte del Ritorno della Salma) rianimi un caduto recente come servo senza volontà",
    ]),
    ("bestie", "Bestie spirituali e lignaggi di sangue", [
        "tame <creatura>               — provi a domare una creatura (ferirla prima aiuta)",
        "beast                         — la tua bestia, il suo talento e gli avvistamenti di bestie rare",
        "feed                          — nutri la tua bestia con un nucleo (cresce)",
        "release                       — liberi la tua bestia",
        "uova                          — le uova in cova nella stalla della dimora ('use uovo' a casa per covarne uno)",
        "alleva <bestia> <bestia>      — (Domatore liv. 4) fai accoppiare due tue bestie: nasce un uovo ibrido",
        "sangue                        — il MENU DEL SANGUE: essenze, lignaggi, fusioni proposte, trasformazione",
        "sangue info                   — l'elenco testuale dei lignaggi",
        "sangue raffina <n> in <m>     — versi un lignaggio debole in uno forte (70%, o 50% se non hanno nulla in comune)",
        "use essenze                   — assorbi tutte le essenze (di sangue e del Dao) in una volta sola",
        "fondi_sangue <n> <m> [...]    — fondi due o più lignaggi Puri in un sangue ibrido",
        "trasformati [n]               — (grado Sacro) nel prossimo scontro assumi la forma della bestia sacra",
        "razze                         — I REGNI DELLE RAZZE: campioni, sangue, reliquie, la scala fino al trono",
        "razza <razza> sfida           — (nelle loro terre) duello col loro campione: uccidilo (sangue, reliquie) o risparmialo (onore)",
        "razza <razza> offri           — restituisci una loro reliquia (onore; serve per salire di grado)",
        "razza <razza> ascendi         — la cerimonia: Discepolo, Campione, Anziano, Principe, fino a Sovrano o Eletto",
        "use <reliquia>                — assorbi una reliquia: un balzo enorme del sangue (o dell'anima)",
    ]),
    ("arti", "Professioni: alchimia, talismani, forgia, formazioni, domatore", [
        "arti                          — il MENU DELLE ARTI: quali praticare (una, alcune, tutte o nessuna), ricette pronte",
        "arti <arte> | tutte | nessuna — pratichi / smetti un'arte | tutte insieme | nessuna (Qi e Dao al centro)",
        "arti principale <arte>        — l'arte principale (classe e capolavori)",
        "profession <arte>             — impari un'arte e la rendi principale (le altre restano tue)",
        "gather                        — raccogli erbe, minerali e nuclei nelle zone selvagge",
        "recipes                       — le ricette della tua arte e i materiali che hai",
        "craft [arte] <n>              — crei la ricetta n (dell'arte principale, o di quella che nomini)",
        "sintonia <elemento> [...]     — leghi la tua arte agli elementi delle tue radici: nasce la tua CLASSE",
        "classe_arte                   — la tua classe (arte × elementi) e cosa fa",
        "formazioni                    — (Formazioni) le formazioni piazzate nel mondo ('use' il disco per piazzarne)",
        "teletrasporto [n]             — viaggi all'istante tra le tue formazioni di teletrasporto",
    ]),
    ("storia", "Storia, destino e memoria", [
        "goals                         — i tuoi obiettivi: la tua storia personale e i traguardi vicini",
        "encounter                     — rivedi l'incontro in corso e le scelte possibili",
        "<numero>                      — scegli un'opzione (dell'incontro o delle azioni suggerite)",
        "lives                         — le tue vite passate e le loro tombe",
        "titles                        — i titoli che hai conquistato",
        "status                        — il tuo stato completo",
        "profilo                       — origine, età e affinità (descrizione qualitativa)",
        "reputation                    — fama, infamia, allineamento percepito, sospetto",
        "mask <on|off>                 — indossi/togli la maschera (agisci in incognito)",
        "log [n]                       — cronache recenti note al giocatore",
        "memories                      — ciò che il tuo personaggio ricorda (memoria attiva)",
        "narrate                       — rendi la scena attuale come prosa (LLM o fallback)",
        "chronicle                     — un breve passo di cronaca del mondo",
    ]),
    ("eredita", "Eredità e poteri dei protagonisti", [
        "tesori [cura|<nome>]          — TUTTI I TUOI TESORI in un pannello (arma, anello, spazio, Gu, marionette…); 'cura' li cura tutti",
        "retaggio                      — il talento che ti è stato tolto: frammenti ritrovati e dove cercare il prossimo",
        "anello [nutri <n>|forza]      — il MAESTRO NELL'ANELLO: consigli, risveglio infinito, ti presta la sua forza",
        "spazio [semina <n>|raccogli|espandi] — lo SPAZIO INTERIORE: campo accelerato, poi Mondo Interiore",
        "clone [crea|lavora|esplora|riposa] — i CLONI: una sola coltivazione, compiti divisi",
        "elementi [assorbi]            — gli ELEMENTI CELESTI: nascono nel mondo, assorbili e falli crescere",
        "famiglia [visita|difendi|dona <pietre>|resuscita <nome>] — la tua famiglia e il tuo clan",
        "scruta [nome] | cela <on|off> — SENSO DIVINO e nascondere il proprio livello",
        "marionetta crea|potenzia <n>  — MARIONETTE da combattimento (Forgia o Formazioni 3)",
        "tesoro forgia <tipo>|nutri <n> — TESORI LEGATI AL SANGUE ('marionette' o 'tesori sangue' per vederli)",
        "gu [raffina <tipo>]           — i GU nella tua apertura: nutrirli, raffinarli",
        "bandiera                      — la BANDIERA DELLE ANIME (arte demoniaca)",
    ]),
    ("trama", "La trama, i regni, le razze e le ere", [
        "cronaca [tutte|esporta]       — la CRONACA della tua vita (e delle vite passate); 'esporta' in un file .md",
        "trama                         — la tua storia: l'atto, le verità scoperte, le scelte che il mondo ricorda",
        "arcinemico                    — il rivale di una vita: cosa ricorda, le cicatrici, i suoi eredi",
        "regni | corte                 — i regni del mondo | la corte del regno in cui ti trovi",
        "sostieni <regno> | tributo <pietre> — servi un regno e sali di rango (da Suddito a Re dei Re)",
        "guerra_regni | trono          — combatti per il tuo regno | prendi il trono (da Duca, se il popolo ti segue)",
        "razze | ambasciata <razza> <dona N|prova> — le RAZZE ANTICHE (draghi, demoni, spiriti, giganti, maree)",
        "era | calamita                — l'ERA del mondo e la CALAMITÀ che ritorna: respingi le ondate",
        "gara [iscriviti|prova]        — le GARE DEI MAESTRI d'arte: corone senza fine",
        "evadi                         — (se sei prigioniero) il passo successivo della fuga",
        "ritmo                         — il ritmo degli eventi: scene della settimana, capitoli, scene in attesa",
        "svolte                        — le SVOLTE della via: ciò che cambia il modo di giocare (raggiunte e prossime)",
        "vola <luogo>                  — (2° regno) voli in un luogo già visitato; dal 6° regno è istantaneo",
        "crea_dao <nome>               — (3 Dao alla Legge) fondi un Dao TUO, mai percorso da nessuno",
        "capolavoro <nome>             — (arte 10, 20, 30…) un'opera unica: +5% coltivazione per sempre",
    ]),
    ("auto", "Pilota automatico (stato etereo)", [
        "auto                          — la configurazione del pilota automatico",
        "auto <giorni>                 — i giorni scorrono da soli (max 60); si ferma agli eventi importanti",
        "auto imposta attivita allena=5 caccia=2 raccolta=1 lavoro=1 insegna=1 — pesi (allena = train: Qi, Dao e arte insieme; coltiva/dao = una cosa sola)",
        "auto imposta bersagli <nessuno|bestie|ricercati|deboli|tutti> — chi attaccare (mai i più forti)",
        "auto imposta assorbi <si|no>  — (Divoratore) divora i caduti",
        "auto imposta loot <si|no> | oggetti <si|no> — raccogli il bottino | usa pillole ed essenze",
        "auto imposta sfonda <si|no>   — tenta da solo il breakthrough quando sei al colmo (rischioso!)",
        "auto imposta rischio <percento> — il rischio di morte che il pilota accetta per sfondare da solo (10%)",
        "auto imposta condotta <virtuosa|prudente|opportunista|spietata> — scelte negli incontri minori",
        "auto imposta fermati <reame|assemblea|asta|invasione|elemento> <si|no> — per quali occasioni fermarsi",
    ]),
    ("sistema", "Interfaccia", [
        "help [categoria|tutto]        — aiuto (anche 'h')",
        "menu                          — l'INDICE DEI MENU: setta, arti, coltivazione, eventi, regni, famiglia",
        "coltivazione | eventi | regni | famiglia — i menu a sezioni, con le azioni numerate (scrivi il numero)",
        "tutorial                      — i primi passi, con ciò che ti resta da provare",
        "senza_ritorno si|no           — modalità SENZA RITORNO: la morte è definitiva (niente reincarnazione)",
        "reincarnati [conferma]        — chiudi questa vita e RINASCI con i benefici di ciò che hai accumulato (merito → Samsara, pietre, tutti i frammenti)",
        "ricomincia [conferma]         — RICOMINCIA DA ZERO: un mondo nuovo, niente eredità (il mondo vecchio viene archiviato)",
        "salva [nome] | carica <nome>  — salvataggi in slot (più 3 automatici ogni 5 giorni) — 'salvataggi' per l'elenco",
        "mappa                         — mappa della regione intorno a te",
        "codex [sezione]               — luoghi, bestie, Dao, lignaggi, maestri e titoli scoperti",
        "colori <on|off>               — colori nel terminale",
        "hud <on|off>                  — mostra/nasconde la riga di stato dopo ogni comando",
        "suggest <on|off>              — mostra/nasconde le 8 azioni rapide numerate (scrivi 1-8 per eseguirle)",
        "quit / exit                   — esci",
    ]),
]

_ALIASES = {
    "esplora": "esplorazione", "viaggio": "esplorazione",
    "combat": "combattimento", "lotta": "combattimento", "abisso": "combattimento",
    "coltiva": "coltivazione", "dao": "coltivazione", "cultivation": "coltivazione",
    "sette": "setta", "sect": "setta", "guerra": "setta", "mercato": "setta",
    "social": "legami", "persone": "legami", "compagni": "legami", "bonds": "legami",
    "destino": "storia", "story": "storia", "obiettivi": "storia",
    "beast": "bestie", "pet": "bestie", "professioni": "arti", "alchimia": "arti",
    "talismani": "arti", "forgia": "arti", "maestri": "legami",
    "ui": "sistema", "interfaccia": "sistema",
    "reame": "mondo", "reami": "mondo", "assemblea": "mondo", "aste": "mondo", "asta": "mondo",
    "casa": "dimora", "discepoli": "dimora", "grotta": "dimora", "radici": "coltivazione",
    "formazioni": "arti", "domatore": "arti", "sangue": "bestie", "lignaggi": "bestie",
    "spirito": "dominio", "anima": "dominio", "servi": "dominio", "sigillo": "dominio", "salme": "dominio",
    "vassalle": "dominio", "tempra": "dominio", "fucina": "tecniche", "soldi": "rendite", "guadagni": "rendite", "pietre": "rendite", "fusione": "tecniche", "mosse": "tecniche", "reliquie": "bestie", "campioni": "bestie",
    "autopilota": "auto", "pilota": "auto", "etereo": "auto", "anello": "eredita", "cloni": "eredita",
    "famiglia": "eredita", "gu": "eredita", "elementi": "eredita", "retaggio": "eredita",
    "regni": "trama", "razze": "trama", "era": "trama", "ere": "trama", "calamita": "trama",
    "arcinemico": "trama", "gare": "trama", "prigionia": "trama", "plot": "trama",
}

ESSENTIALS = """Nuovo? Scrivi 'tutorial'.
Comandi essenziali:
  look · move <n|s|e|w> · train (t) · attack <nome> · status · goals · auto <giorni>
  Dopo ogni comando trovi delle AZIONI SUGGERITE numerate: scrivi il numero per eseguirle.
  Quando capita un INCONTRO, scegli scrivendo il numero dell'opzione.

Categorie ('help <categoria>', oppure 'help tutto'):"""


def _section(title: str, lines: list[str]) -> str:
    return title + ":\n" + "\n".join("  " + ln for ln in lines)


def full_help() -> str:
    parts = ["Comandi disponibili:"]
    for _key, title, lines in CATEGORIES:
        parts.append(_section(title, lines))
    parts.append('(con Ollama attivo puoi anche scrivere in linguaggio naturale, '
                 'es. "esamina il vecchio")')
    return "\n\n".join(parts)


# Categorie che si SVELANO man mano (aiuto progressivo): finché non le hai toccate, l'aiuto
# le mostra in fondo, in breve, con il modo per scoprirle. 'help tutto' mostra sempre tutto.
_ALWAYS = {"esplorazione", "combattimento", "coltivazione", "storia", "legami", "setta", "auto", "sistema"}
_HINT = {"mondo": "dal 2° regno, o quando si apre un reame segreto o un'Assemblea",
         "dimora": "quando reclami una grotta-dimora o hai un discepolo",
         "bestie": "quando domi una bestia o un sangue antico scorre in te",
         "arti": "quando scegli un'arte ('profession <arte>')",
         "eredita": "quando trovi il tuo primo tesoro vivo (anello, spazio interiore, Gu…)",
         "trama": "quando la tua storia comincia davvero (il primo capitolo della trama)"}


def _unlocked(conn, key: str) -> bool:
    if key in _ALWAYS or conn is None:
        return True
    try:
        from engine.systems import state, professions, beasts, bloodlines, cave_abode, treasury
        from engine.simulation import cultivation
        from engine.core import entities
        p = entities.get_player(conn)
        if key == "mondo":
            return (cultivation.realm_tier(conn, "player", p.id) or 1) >= 2 or bool(state.get(conn, "secret_realm"))
        if key == "dimora":
            return bool(cave_abode.get(conn, p.id))
        if key == "bestie":
            return bool(beasts.pets(conn, p.id)) or bool(bloodlines.ordered(conn))
        if key == "arti":
            return bool(professions.profession(conn, p.id))
        if key == "eredita":
            return bool(treasury._lines(conn, p))
        if key == "trama":
            return bool((state.get_json(conn, "master_plot") or {}).get("done"))
    except Exception:
        return True
    return True


def help_for(arg: str, conn=None) -> str:
    a = (arg or "").strip().lower()
    if not a:
        open_ = [(k, t) for k, t, _ in CATEGORIES if _unlocked(conn, k)]
        hidden = [(k, t) for k, t, _ in CATEGORIES if not _unlocked(conn, k)]
        cats = "\n".join(f"  {key:<14} — {title}" for key, title in open_)
        if hidden:
            cats += "\nAncora da scoprire:\n" + "\n".join(
                f"  {key:<14} — si svela {_HINT.get(key, 'più avanti')}" for key, _t in hidden)
        return f"{ESSENTIALS}\n{cats}"
    if a in ("tutto", "all", "completo", "full"):
        return full_help()
    a = _ALIASES.get(a, a)
    for key, title, lines in CATEGORIES:
        if key.startswith(a):
            return _section(title, lines)
    return f"Categoria '{arg}' sconosciuta. " + help_for("")


def command_lines() -> list[str]:
    return [ln for _k, _t, lines in CATEGORIES for ln in lines]


def command_words() -> set[str]:
    """Primo token di ogni riga d'aiuto: i verbi che il motore accetta."""
    out = set()
    for ln in command_lines():
        w = ln.split()[0]
        if w.startswith("<"):
            continue
        out.add(w)
    return out


HELP = full_help()
