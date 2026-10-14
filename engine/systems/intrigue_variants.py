"""
VARIANTI DI TESTO DELLE TRAME (Aggiornamento 59).

La stessa trama, giocata due volte, non deve raccontarsi con le stesse parole. Per ogni trama e
per ogni atto si possono scrivere versioni alternative del testo d'apertura: il motore ne sceglie
una in modo deterministico (dall'identità della trama e dall'atto), quindi rileggere la scena non
la cambia, ma una partita nuova sì.

    VARIANTS = {"chiave_trama": {indice_atto: ["testo alternativo", ...]}}

Il testo originale del modello resta sempre tra le possibilità. Valgono gli stessi segnaposto
({vittima}, {mandante}, {la_setta}, {luogo}…) più quelli del mondo:
    {stagione}   primavera, estate, autunno, inverno
    {quando}     un'ora del giorno detta a parole («mentre il sole tramonta»)
    {atmo}       una frase d'atmosfera sulla stagione, già con la maiuscola e il punto

Il primo atto di ogni trama si apre comunque con una riga d'atmosfera (a meno che il testo non
usi già {atmo}, o il modello abbia "no_atmo": True).

Aggiungere varianti è solo scrivere righe qui: nessun codice da toccare.
"""

VARIANTS = {
    "mano_ombra": {0: [
        "Il discepolo {della_setta} lo ripescano dal pozzo di {luogo} quando ormai è freddo. Ha la gola aperta "
        "da una lama di Qi, e stretto nel pugno un ciondolo di giada: quello che porti tu, o uno identico. "
        "Gli sguardi si voltano verso di te prima ancora delle domande.",
        "Di {stagione} i pozzi di {luogo} gelano piano, e quello di stamattina custodisce un morto: un discepolo "
        "{della_setta}, sgozzato con un filo di Qi. Accanto, un ciondolo di giada uguale al tuo. Qualcuno ha "
        "voluto che lo trovassero proprio così.",
    ]},
    "torneo_truccato": {0: [
        "Le bandiere delle Cento Sette sventolano su {luogo}: domani comincia il Torneo, e il vincitore siederà "
        "ai piedi dei Venerabili. Stanotte però {pedina} bussa alla tua stanza con un sacchetto che tintinna e "
        "una proposta che non si dice ad alta voce.",
        "Cento giovani, un'arena sola, un solo posto tra i Venerabili: il Torneo delle Cento Sette si apre a "
        "{luogo}. Mentre affili la spada, {pedina} si siede di fronte a te senza invito. «Parliamo di come "
        "andrà a finire», dice.",
    ]},
    "debito_oltretomba": {0: [
        "La fiamma della candela diventa verde e smette di tremare. {pedina} è già dentro la stanza, la "
        "lanterna in mano e nessuna ombra ai piedi: «Una vita fa hai preso in prestito qualcosa. L'Oltretomba "
        "tiene i conti meglio dei vivi.»",
        "Senti bussare tre volte, poi altre tre, e nessuno sulla soglia. Solo quando ti volti vedi {pedina}, "
        "con una lanterna verde e un rotolo di pelle nera: un debito di una vita passata, scritto col tuo "
        "nome di allora.",
    ]},
    "maledizione": {0: [
        "Ti svegli col sapore del ferro in bocca. Nel sogno un filo nero ti usciva dal petto e correva verso "
        "nord, e al risveglio il segno sul polso è ancora lì, più scuro di ieri. Il Qi ti obbedisce con un "
        "attimo di ritardo.",
        "Tre notti, lo stesso sogno: un filo nero, teso dal tuo cuore verso il nord. Stamattina il filo non "
        "è più solo un sogno. Lo vedi quando chiudi gli occhi, e ogni respiro di Qi lo fa vibrare.",
    ]},
    "traditore_setta": {0: [
        "Il vecchio custode del tesoro {della_mia_setta} ti chiama da parte e non ti guarda negli occhi: "
        "da tre mesi spariscono pillole, e due discepoli sono morti in agguati che il nemico conosceva in "
        "anticipo. «C'è una lingua che parla troppo, tra noi.»",
        "Due tumuli nuovi dietro la sala {della_mia_setta}, e un registro del tesoro che non torna. Il custode "
        "lo ha ricontato sette volte. «Pillole sparite, missioni tradite», sussurra. «Non è sfortuna. È uno "
        "di noi.»",
    ]},
    "reame_mille_tesori": {0: [
        "Per un attimo la cascata vicino a {luogo} scorre all'indietro, e dietro l'acqua si apre una porta di "
        "luce. Un reame sigillato da mille anni: sette giorni, poi si richiuderà. Le sette stanno già "
        "mandando i loro migliori.",
        "La notizia corre più veloce dei cavalli: dietro la cascata di {luogo} si è aperto un reame segreto. "
        "Sette giorni prima che il sigillo torni a chiudersi, e mille tesori per chi arriva primo, o per chi "
        "esce vivo.",
    ]},
    "marea_bestie": {0: [
        "I cani di {luogo} ululano da tre notti, e gli stormi passano bassi verso sud. {mandante}, che governa "
        "la città, non ha dormito: «Scende una marea di bestie dalle montagne. Mi servono coltivatori sulle "
        "mura, e mi servono adesso.»",
        "La terra trema sotto {luogo} come se respirasse. Sulle mura {mandante} conta i difensori e non gli "
        "bastano: «Una marea di bestie. Prima che arrivino ci restano pochi giorni. Combatterai con noi?»",
    ]},
    "sigillo_asta": {0: [
        "L'ultimo lotto della casa d'aste di {luogo} non ha nome né descrizione: un sigillo di bronzo nero, "
        "venduto «così com'è». Quando lo sollevano, il Qi della sala si raffredda di colpo. {mandante} alza la "
        "mano prima che il banditore finisca.",
        "«Lotto finale», annuncia il banditore, senza entusiasmo: un sigillo di bronzo nero, origine ignota. "
        "In prima fila {mandante} sorride, come chi sa esattamente cosa sta comprando. E tu senti il sigillo "
        "chiamarti.",
    ]},
    "grotta_maestro": {0: [
        "Una volpe bianca ti guarda, ti sfida, scappa. La segui fino al crepaccio, e il crepaccio ti inghiotte. "
        "In fondo, una grotta asciutta e uno scheletro seduto nel loto, con un anello al dito che ancora "
        "brilla.",
        "Il terreno cede sotto i tuoi piedi mentre insegui una volpe bianca. Cadi a lungo. Quando la polvere "
        "si posa, davanti a te c'è un vecchio maestro: o meglio, quello che ne resta, seduto nel loto da "
        "secoli, con un anello al dito.",
    ]},
    "sacrificio_sangue": {0: [
        "Le porte di {luogo} restano aperte di notte, e la mattina le case sono vuote. Prima i mendicanti, poi i "
        "bambini. Su ogni soglia, un occhio disegnato col sangue.",
        "Nessuno a {luogo} parla più ad alta voce. Le case vuote si contano sulle dita di due mani, e su "
        "ognuna c'è lo stesso segno: un occhio di sangue, fresco come se l'avessero tracciato stanotte.",
    ]},
    "carovana": {0: [
        "{mandante}, della Lega Dorata, ti offre il triplo del prezzo per scortare una carovana fino al passo. "
        "«E niente domande.» Uno dei carri è coperto da un telo nero, e quando passi accanto senti qualcosa "
        "muoversi sotto.",
        "La paga è troppo alta, e lo sai. {mandante} la conta davanti a te: «Fino al passo, e non toccare il "
        "carro nero.» Il telo che lo copre è legato con corde intrecciate di talismani.",
    ]},
    "pillola_contraffatta": {0: [
        "Tre discepoli morti a {luogo}, tutti dopo una Pillola della Fondazione comprata al mercato. La Gilda "
        "degli Alchimisti nega, i mercanti negano, e i parenti dei morti cercano qualcuno da impiccare.",
        "La pillola sembra perfetta: colore, profumo, venatura. Eppure tre discepoli di {luogo} l'hanno presa "
        "e non si sono più svegliati. La Gilda degli Alchimisti giura che non è uscita dai suoi forni.",
    ]},
    "tesoro_cielo": {0: [
        "Una stella si stacca dal cielo e cade dietro le colline di {luogo}, lenta come una lacrima. All'alba "
        "metà della regione è già in cammino verso il cratere: dentro, dicono, c'è un tesoro dei Cieli "
        "Superiori.",
        "Il boato sveglia tutta {luogo}. Oltre le colline il cielo è ancora rosso, e una colonna di luce sale "
        "dal cratere. Prima di mezzogiorno le strade sono piene di coltivatori che corrono nella stessa "
        "direzione.",
    ]},
    "citta_fantasmi": {0: [
        "A mezzanotte, accanto a {luogo}, la nebbia prende forma: strade, case, lanterne accese, e voci che "
        "chiamano nomi dimenticati. {spettro} ti prende per la manica: «Hai visto chi ha chiuso le porte?»",
        "Le lanterne si accendono una a una dove al tramonto non c'era niente. Una città intera, fatta di "
        "nebbia, accanto a {luogo}. {spettro} ti aspetta al cancello, e non ha ombra.",
    ]},
}
