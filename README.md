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

> Richiede solo **Python 3.11+** (usa `sqlite3` della standard library). La narrazione
> avanzata è opzionale (LLM locale via Ollama); senza, c'è un fallback testuale completo.

---

## ✨ Caratteristiche

### Coltivazione **infinita**
- Regni di coltivazione con **10 strati** ciascuno e breakthrough come evento di regno.
- **Nessun tetto**: oltre l'*Immortale di Giada* (regno 8) i regni si generano da soli con
  nomi ascendenti (*Sovrano Celeste*, *Re degli Immortali*, … e poi numerali romani).
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
  **promozione di categoria**; i **compagni di classe crescono ogni giorno** in base al
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
| Esplorazione | `look`, `move <dir>`, `home`, `warzone`, `raidtarget`, `events`, `map` |
| Combattimento | `attack <nome>`, `attack all`, `attack humans`, `attack creatures`, `moves`, `defend` |
| Abisso | `absorb <nome>`, `absorb all`, `loot` |
| Coltivazione | `cultivate`, `comprehend <dao>`, `breakthrough`, `dao`, `tribulation` |
| Sette | `join`, `class`, `market`, `buy <n>`, `invitations`, `accept <n>` |
| Guerra | `raid`, `invade` |
| Stato | `status`, `rating`, `inventory`, `use <oggetto>`, `use all`, `techniques` |
| Sistema | `help`, `save`/auto, `quit` |

(La lista completa e aggiornata è sempre in `help`.)

---

## 🧱 Architettura

```
jade_immortal/
├── main.py                 # entry point: init DB, genera mondo, crea personaggio, loop
├── database/schema.sql     # schema SQLite (mondo, NPC, sette, Dao, eventi, …)
├── engine/
│   ├── db.py               # connessione + migrazioni idempotenti
│   ├── core/               # entità, tick, tipi base
│   ├── generators/         # mondo, NPC, Dao, creature, regni di coltivazione
│   ├── simulation/         # combat, cultivation, world_tick, faction_engine, eventi
│   ├── systems/            # sette, mercato, assorbimento, dao_powers, tribolazione,
│   │                       #   invasioni mondiali, invasioni guidate, caccia, reputazione…
│   └── cli/loop.py         # dispatch dei comandi + resa testuale
└── tests/                  # ~345 test (pytest)
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

> Nota: un singolo test (`test_fallback_render_produces_prose`) può risultare *rosso*
> **solo** se è attivo un LLM locale: presume il fallback testuale. Non è un bug di gioco.

---

## ⚖️ Stato & bilanciamento

Il gioco è in sviluppo attivo: molti sistemi sono nuovi e alcuni **numeri** (potenza dei Dao,
soglie delle tribolazioni, prezzi del mercato, forza della fusione, ritmo dei breakthrough)
sono **prime tarature** pensate per essere rifinite col playtest. Feedback e bilanciamenti
sono benvenuti.

Per il dettaglio cronologico delle aggiunte vedi **`CHANGES.md`**.
