# Jade Immortal 🗡️🐉

**Simulatore narrativo testuale di coltivazione (Wuxia / Xianxia), in italiano.**
Un mondo procedurale vivo in cui parti come coltivatore qualunque e — tra sette, Dao,
assorbimenti, tornei, guerre e tribolazioni celesti — provi a salire la *via degli immortali*
senza limiti. Gira **offline**, da riga di comando, con narrazione opzionale via LLM locale.

```bash
cd jade_immortal
python main.py
```

Al primo avvio genera il mondo, ti fa scegliere un'**origine** e lancia il gioco.
Scrivi `help` in qualsiasi momento per la lista dei comandi.

### 🖥️ Oppure: la dashboard nel browser

```bash
python dashboard.py
```

Si apre il browser su `http://127.0.0.1:8765`: è la **stessa partita** del terminale, con
- una barra di stato sempre visibile (regno ed esperienza, Qi, spirito, cuore del Dao,
  ferite, pietre, giorno, stagione, meteo, era);
- il luogo con le uscite e i presenti cliccabili (vai, parla, attacca);
- le **scelte degli incontri** e le **azioni suggerite** come pulsanti, oppure i tasti 1-8;
- i pannelli **Mete** (Vai / Partecipa), **Obiettivi** (primari, secondari, missioni),
  **Mappa** cliccabile, **Personaggio** (con le barre dei Dao), **Alleati e nemici** (con la
  loro potenza a confronto con la tua), **Tesori** (con i colori di rarità), **Storia**
  (con la cronaca delle tue vite), **Mondo** e **Partita** (salvataggi, salvataggio automatico
  ogni 5 giorni, *Reincarnati ora* e *Ricomincia da zero*);
- i **duelli a turni** con le barre della vita;
- **grafici** della tua crescita e il radar del profilo, la **rete delle relazioni** (famiglia,
  legami, nemici, faide e debiti di vita), il **Libro** illustrato di tesori, bestie, sangue,
  reliquie e nemici (con i tuoi disegni nella cartella `immagini/`), il registro **filtrabile** e
  una **legenda** dei simboli;
- i **menu** Setta, Arti, Coltivazione, Eventi, Dimora, Regni e Famiglia nella colonna di sinistra:
  ogni azione è un pulsante, e quelle non ancora possibili dicono cosa manca;
- il **pilota automatico dal vivo**, un giorno alla volta, con un pulsante per interromperlo;
- la creazione del personaggio e la rinascita in finestre guidate.

Non serve installare nulla (solo libreria standard) e ascolta solo sul tuo PC
(`python dashboard.py --rete` per usarla anche dal telefono, sulla Wi-Fi di casa). La riga di
comando resta sempre disponibile in basso. Non usare terminale e dashboard nello stesso
momento.

> Richiede solo **Python 3.11+** (usa `sqlite3` della standard library). La narrazione
> avanzata è opzionale (LLM locale via Ollama); senza, c'è un fallback testuale completo.

---

## ✨ Caratteristiche

### Una storia che è tua 🎴
- **Menu a sezioni** (`menu`): *setta* (ascesa alle sette superiori, tecniche, tesoro del merito,
  rango, stipendio, missioni, anziani, guerre), *arti* (una, alcune, tutte o nessuna),
  *coltivazione*, *dimora* (con «potenzia al massimo»), *eventi* (tutto ciò a cui partecipare), *regni* e *famiglia*. Nel terminale
  si sceglie col numero, nella dashboard coi pulsanti.
- **8 azioni rapide** numerate dopo ogni comando: scrivi da `1` a `8` per agire senza
  ricordare 70 comandi (restano tutti disponibili). In testa ciò che è urgente o a tempo,
  poi le azioni che accorpano tanti comandi in uno: `train`, `tesori cura`, `mete`,
  il pilota automatico per un giorno o una settimana, il sonno, l'esplorazione.
- **Incontri a scelta**: mini-scene con prove sulle tue qualità reali e la probabilità di
  riuscita mostrata prima di scegliere.
- **Storia personale** in 4 capitoli per ogni origine, con il diario `goals`.
- **Trama maestra in atti, senza fine** (`trama`): fidanzamento annullato e duello dei tre
  anni, l'arcinemico che ricorda e ha eredi, regni e corti, razze antiche, tradimento e
  prigionia, i Mietitori. Poi mondi superiori uno sopra l'altro, ognuno con le sue
  verità, i suoi Signori e le Leggi dell'Imperatore del Dao. Non c'è un nemico finale.
- **Ere del mondo e calamità** che ritornano sempre più forti; **gare d'arte** con corone infinite.
- **Un regista per il ritmo** (`ritmo`): poche scene importanti a settimana, mai lo stesso tipo
  a breve distanza, capitoli della storia che si alternano con il tempo di respirare.
- **Svolte** (`svolte`): salti di qualità oltre i numeri — volo e passo nel vuoto, incarnazioni
  del Dao, un Dao tutto tuo (`crea_dao`), capolavori della tua arte.
- **Un mondo che cambia sotto i tuoi occhi**: stagioni, tempo atmosferico, ora del giorno,
  testi che variano senza bisogno dell'LLM.
- **Legami**: compagni che combattono con te, un maestro, rivali e **nemesi** che tornano
  più forti.
- **Reincarnazione**: alla morte un epilogo, una tomba con i tuoi tesori e una nuova vita
  nello stesso mondo, con un frammento della precedente.
- **Riga di stato** sempre visibile e aiuto per categorie.

### Poteri che interagiscono ☯
- **Ciclo dei Cinque Elementi**: catene di 2-5 elementi con nome, vantaggio elementale sul nemico.
- **Stati di combattimento** (ustione, gelo, emorragia, stordimento, …) e scontri di più round.
- **22 fusioni leggendarie** e **Domini**; **11 Dao superiori** che si risvegliano con le imprese.
- **Destini alla nascita**, talento dei rivali, **demone interiore** al breakthrough.
- **Bestie spirituali** da domare (anche fenici, draghi e ibridi), **professioni**
  (alchimia, talismani, forgia), **spirito dell'arma**, **durata della vita** che
  raddoppia a ogni regno, **maestri segreti infiniti** che ti accompagnano fino alle vette più alte.

### Il mondo del coltivatore 🏯
- **Reami segreti** che si aprono e si richiudono, **ritiro a porte chiuse**, illuminazioni.
- **Grotta-dimora** da potenziare, **discepoli**, e la **tua setta** da fondare e difendere.
- **Classifiche del Cielo**, **Grande Assemblea** dell'Alleanza Marziale, **casa d'aste**.
- Sette **ortodosse, eterodosse e demoniache**, politica interna, faide d'onore.
- **Fratellanza giurata** e **compagno del Dao** (doppia coltivazione).
- **Radici spirituali** a punteggio infinito con effetti per **ogni combinazione**,
  metodi di coltivazione, **classi** arte × elemento (Formazioni, Domatore…).
- **Mondi superiori** infiniti oltre il nono regno; origine **Trasmigratore col Sistema**.
- **Lignaggi di sangue** delle bestie leggendarie: manifestazioni ibride, trasformazione
  completa, fusione in sangui ibridi (Drago-Fenice di Fuoco e Ghiaccio…).
- **Armi vive** che si temprano con il tempo e l'uso, si risvegliano e crescono senza tetto.
- **Costituzioni speciali**, **cuore del Dao** (deviazione del Qi), **tossine delle pillole**,
  **tribolazioni del fulmine** a ogni regno da assorbire e controllare.
- **Prodigi** che crescono senza di te, **uova e allevamento** di bestie ibride, **incarichi a catena**.
- **Poteri dei protagonisti**: retaggio spezzato da ricomporre, maestro nell'anello, spazio
  interiore, cloni, elementi celesti, famiglia, senso divino, marionette e tesori, Gu,
  bandiera delle anime: tutto coltivabile senza fine.
- Salvataggi in slot, mappa, colori, codex e tutorial.
- **Pilota automatico** (`auto <giorni>`): lo «stato etereo» in cui il personaggio vive da
  solo le parti monotone e si ferma davanti agli eventi importanti.

### Coltivazione **infinita**
- Regni di coltivazione con **10 strati** ciascuno e breakthrough come evento di regno.
- **Ogni mondo ha il suo tetto**: il Mondo Mortale regge nove regni (Condensazione del Qi,
  Fondazione, Nucleo d'Oro, Anima Nascente, Trasformazione dello Spirito, Raffinamento del Vuoto,
  Unione del Corpo, Grande Veicolo, Superamento della Tribolazione). Alla Grande Perfezione
  del nono si **ascende** (lasciando indietro gli oggetti del mondo inferiore) e si diventa
  *Immortale di Giada*; ogni mondo superiore aggiunge tre regni (Immortale Celeste, Immortale
  d'Oro, Santo, Imperatore del Dao, Caos Primordiale…), senza fine.
- Breakthrough con probabilità di **fallimento** (che tempra il corpo) e di **morte**;
  ogni fallimento ti rende più pronto al tentativo successivo.

### I Dao — il cuore della potenza
- Decine di Dao: armi (spada, lancia, arco…), Corpo, Anima, Fulmine, gli **elementi base**
  (fuoco, acqua, terra, vento, metallo, legno) e **superiori** (luce, oscurità), più i tre
  **Dao profondi**.
- **Tecniche FUSE**: ogni Dao che supera la soglia si **unisce** alla tua tecnica dominante,
  rendendola più forte (3, 4, … Dao senza limite).
- **Potenza dei Dao**: la forza cresce molto col **numero** di Dao e (super-linearmente) col
  loro **livello** — conoscere più Dao rende molto più forti.

### I tre Dao profondi + Heaven's Defiance
- **Spazio** = Dao distruttivo: ignora la difesa, colpi critici e colpi multipli (echi).
- **Tempo** = Dao della coltivazione: accelera la crescita e dà schivata/iniziativa.
- **Destino** = Dao della fortuna: breakthrough più probabili e meno letali, bottini migliori.
- **Sfida al Cielo** (`heaven_defiance`): più padroneggi i Dao profondi, più il Cielo ti vuole
  cancellare → **tribolazioni divine**.

### Tribolazioni divine ⚡
- Scattano salendo nella Sfida al Cielo, **al breakthrough** e **divorando troppi cadaveri**.
- Le **domi** col Dao del **Fulmine**: ogni folgore assorbita dà benedizioni, **risveglia
  poteri spaziali** e **purifica l'Abisso** (azzera la corruzione da assorbimento).
- Sopravvivere sblocca la **Folgore della Tribolazione**, un colpo più forte del Fulmine base.

### L'Abisso Divoratore
- Divora i cadaveri per assorbirne **corpo, anima, qi** e **frammenti dei loro Dao** (più Dao
  ha la vittima, più Dao carpisci → tecniche fuse più ricche).
- L'assorbimento lascia **corruzione** (residuo dell'Abisso), con rischi se esageri.

### Combattimento
- Scontri a round non lineari, ferite persistenti, morte, critici e finisher variati, con
  **descrizioni ricche** e colore ambientale.
- `attack all` travolge **tutti** i nemici presenti; `attack humans` / `attack creatures` per
  mirare; il bottino resta **dove combatti**, sempre raccoglibile.

### Sette
- Test d'ingresso sul talento, ranghi di discepolo, **economia giornaliera** di sessioni.
- **Livelli di setta infiniti** (nomi auto-generati).
- **Tornei mensili giocati**: combattimenti coi compagni, classifica, premiazione e
  **promozione di categoria** (in alternativa, `challenge` sfida un anziano di rango
  superiore: se vinci, ne prendi il posto); i **compagni di classe crescono ogni giorno** in base al
  talento (più alto nelle sette potenti).
- **Mercato delle pietre** in città: pillole, essenze, nuclei, manuali — assortimento e
  potenza scalati col livello della setta, stock giornaliero.

### Guerra, razzie e **invasioni guidate**
- Guerre tra sette, **razzie in solitaria** (`raid`) alle sedi rivali.
- Al **rango alto** (*Erede della Setta* / *Giovane Patriarca*) **guidi la tua setta** in una
  vera **invasione** (`invade`): porti alleati, travolgi i difensori e **conquisti** la sede
  rivale, ne spezzi l'influenza e razzii pietre, tesori e manuali.
- **Espansione = ritorsione**: più conquisti, più i nemici colpiscono i **tuoi** territori.

### Invasioni mondiali vive
- Maree di **bestie**, incursioni **demoniache** e **spettrali**, guidate da un **campione**.
- **Rinforzi** nel tempo se tardi, **difensori locali** che reagiscono, ricompense scalate e
  un **trofeo** se respingi un boss.

### Caccia territoriale
- Uccidere creature dà **fama** e abbassa sospetto/infamia; ma se ne stermini troppe, un
  **campione della specie** ti dà la caccia.

### Mondo & altro
- Mondo procedurale a territori, zone tematiche che si **rigenerano**, fazioni autonome che si
  espandono e confliggono, eventi e cronache tracciate.
- **Karma** nascosto, doppia identità/maschera per la **reputazione**, armi equipaggiabili
  (regno × rarità), memoria stratificata, comandi di **viaggio diretto** (`home`, `warzone`,
  `raidtarget`).
- Narrazione opzionale via **LLM locale** (Ollama) con **fallback** testuale completo, e
  linguaggio naturale come traduttore di intenti.

---

## 🎮 Comandi principali

| Categoria | Comandi |
|---|---|
| Esplorazione | `mete`, `vai <n\|meta\|luogo>`, `iscriviti <meta>`, `look`, `move <dir>`, `home`, `warzone`, `raidtarget`, `events`, `map` |
| Combattimento | `attack <nome>`, `attack all`, `attack humans`, `attack creatures`, `moves`, `defend` |
| Abisso | `absorb <nome>`, `absorb all`, `loot` |
| Coltivazione | `train` (o `t`: Qi, Dao e arte insieme), `cultivate`, `comprehend <dao>`, `breakthrough`, `dao`, `tribulation` |
| Sette | `join`, `class`, `challenge`, `market`, `buy <n>`, `invitations`, `accept <n>` |
| Legami | `talk`, `gift <nome> <pietre>`, `spar`, `recruit`, `dismiss`, `disciple`, `bonds` |
| Storia | `<numero>` (scelte), `goals`, `encounter`, `lives`, `titles`, `masters` |
| Bestie | `tame <creatura>`, `beast`, `feed`, `release` |
| Arti | `profession <alchimia\|talismani\|forgia\|formazioni\|domatore>`, `gather`, `recipes`, `craft <n>`, `sintonia`, `formazioni` |
| Mondo | `realm`, `enter`, `delve`, `assemblea`, `asta`, `classifica`, `ascendi_mondo`, `mondi`, `sistema` |
| Dimora e setta | `dimora`, `ritiro <giorni>`, `accogli`, `insegna`, `discepoli`, `fonda`, `setta`, `anziani`, `missioni` |
| Talento | `radici`, `gongfa`, `giura`, `proponi`, `chiama` |
| Arma | `weapon <arma>`, `arma`, `arma nome <nome>` |
| Sangue | `sangue`, `use essenza`, `fondi_sangue <n> <m>`, `trasformati` |
| Corpo e mondo | `corpo`, `tribolazioni`, `prodigi`, `uova`, `alleva`, `richieste`, `incarichi`, `consegna` |
| Eredità | `tesori` (pannello unico, `tesori cura`), `retaggio`, `anello`, `spazio`, `clone`, `elementi`, `famiglia`, `scruta`, `cela`, `marionetta`, `tesoro`, `gu`, `bandiera` |
| Svolte e ritmo | `svolte`, `vola <luogo>`, `crea_dao <nome>`, `capolavoro <nome>`, `ritmo` |
| Trama | `trama`, `arcinemico`, `regni`, `corte`, `sostieni`, `tributo`, `guerra_regni`, `trono`, `razze`, `ambasciata`, `era`, `calamita`, `gara`, `evadi` |
| Interfaccia | `tutorial`, `mappa`, `codex`, `salva`, `carica`, `salvataggi`, `colori` |
| Pilota automatico | `auto`, `auto <giorni>`, `auto imposta ...` |
| Guerra | `raid`, `invade` |
| Stato | `status`, `rating`, `inventory`, `use <oggetto>`, `use all`, `techniques` |
| Sistema | `help [categoria\|tutto]`, `hud on/off`, `suggest on/off`, save automatico, `quit` |

(La lista completa e aggiornata è sempre in `help`.)

---

## 🧱 Architettura

```
jade_immortal/
├── main.py                 # entry point: init DB, genera mondo, crea personaggio, loop
├── dashboard.py            # la stessa partita nel browser (http://127.0.0.1:8765)
├── database/schema.sql     # schema SQLite (mondo, NPC, sette, Dao, eventi, …)
├── engine/
│   ├── db.py               # connessione + migrazioni idempotenti
│   ├── core/               # entità, tick, tipi base
│   ├── generators/         # mondo, NPC, Dao, creature, regni di coltivazione
│   ├── simulation/         # combat, cultivation, world_tick, faction_engine, eventi
│   ├── systems/            # sette, mercato, assorbimento, dao_powers, tribolazione,
│   │                       #   invasioni mondiali, invasioni guidate, caccia, reputazione,
│   │                       #   suggestions, encounters, bonds, storyline, rebirth…
│   ├── cli/                # loop.py (dispatch), story_cmds.py, lifecycle.py, hud.py, help_text.py
│   └── web/                # dashboard: game.py (ponte col motore), server.py, static/ (HTML/CSS/JS)
└── tests/                  # ~430 test (pytest)
```

I dati di gioco vivono in un singolo file **SQLite**. Le migrazioni sono idempotenti: i
salvataggi vecchi si aggiornano da soli all'avvio.

---

## ✅ Test

```bash
pip install pytest pyyaml
python -m pytest -q
```

La suite copre combattimento, coltivazione, Dao/fusione, assorbimento, sette/tornei, mercato,
invasioni (mondiali e guidate), caccia territoriale e i fix di gameplay.

> I test forzano la narrazione LLM spenta (`tests/conftest.py`), quindi l'esito è lo
> stesso con o senza Ollama attivo.

---

## ⚖️ Stato & bilanciamento

Il gioco è in sviluppo attivo. Dall'Aggiornamento 23 il bilanciamento si verifica con
**simulazioni lunghe**: il pilota automatico gioca 500 giorni con ogni origine e si misura
quando si muore, quanto si sale e quali sistemi dominano.

Il modello di potenza in breve:
- il **regno** è la scala principale: ×1,6 a regno, continuo strato per strato;
- i **Dao** amplificano in proporzione al «vaso» del regno, con un moltiplicatore
  logaritmico senza tetto;
- tutta la **crescita personale** (corpo, tecniche, arma, sangue, Abisso) è compressa in
  modo logaritmico: cresce sempre, senza schiacciare il regno.

I parametri stanno in cima a `engine/simulation/combat.py` (`REALM_STEP`, `DAO_VESSEL`,
`DAO_AMP`, `GROWTH_LOG`). Feedback e bilanciamenti sono benvenuti.

Per il dettaglio cronologico delle aggiunte vedi **`CHANGES.md`**.
