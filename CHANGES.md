
---

## Aggiornamento — Armi equipaggiabili (regno × rarità)

**Nuovo modello.** La VIA marziale (tipo d'arma) resta la scelta permanente di setta;
ora però l'arma ha una QUALITÀ data dal **regno** (livello di coltivazione per cui è
forgiata) e da **4 classi di rarità** — comune, raffinata, pregiata, divina. Il bonus
è una % di attacco che cresce col regno (+6% per regno) e, di più, con la rarità
(+5% per classe). L'arma iniziale è comune/regno 1 = **+0%** (quindi nessun test
preesistente cambia).

**Auto-equip dai caduti.** I caduti importanti (e i patriarchi quasi sempre) lasciano
la loro arma. Quando fai `loot`:
- stesso tipo e più forte → **equipaggiata in automatico** ("Impugni …: è superiore alla tua …");
- stesso tipo ma uguale/peggiore → la lasci ("… non è all'altezza della tua …");
- tipo diverso dalla tua via → non puoi usarla ("… ma la tua via è la Spada: non puoi usarla");
- senza una via scelta → non puoi impugnarla.

Le armi non si accumulano nello zaino: o si equipaggiano o si lasciano (resta solo il
messaggio). Il bonus dell'arma equipaggiata moltiplica l'attacco in combattimento
(`combat.combat_power`), distinto dal Dao d'arma (che cresce con la comprensione).

**File toccati:** `engine/systems/weapons.py` (modello + `try_equip_drop`),
`engine/systems/loot.py` (drop dell'arma del caduto), `engine/cli/loop.py`
(messaggi in `cmd_loot`, display in `weapon`/`status`), `engine/simulation/combat.py`
(bonus in `combat_power`), `database/schema.sql` + `engine/db.py` (colonne
`weapon_tier`, `weapon_rarity`). Nuovo test: `tests/test_weapon_equip.py` (10 test).
Suite totale: **285 passati**, 1 rosso atteso (LLM).

---

## Aggiornamento 3 — Rework breakthrough, bugfix e bilanciamenti

### Breakthrough (ridisegnato come richiesto)
- L'**assorbimento (corruzione) ora ABBASSA la riuscita** del breakthrough (il Cielo ti
  percepisce come minaccia), invece di aumentarne la letalità: ho **rimosso il vecchio
  moltiplicatore di morte legato al residuo d'anima** — era quello che ti uccideva.
- Ogni **fallimento tempra il corpo** (cresce forza/vitalità/resistenza + body_level, lo
  senti in combattimento), **alza la riuscita** del tentativo successivo e **riduce il
  rischio di morte**. Più fallisci, più sfondare diventa inevitabile.
- **Garanzia anti-stallo**: dopo `BT_GUARANTEE` (8) fallimenti accumulati, il corpo
  sfonda comunque. Il contatore si azzera al successo.
- La morte da breakthrough resta possibile per un cultivatore "pulito" ad alto regno
  (così il bilanciamento regge), ma un forte assorbitore ora **macina fallimenti e
  diventa più forte** invece di morire.

### Bugfix
- **`attack all` + `loot`**: il conteggio uccisioni era falsato (le righe di bottino
  finivano in coda e rompevano il rilevamento), dando l'impressione che gli oggetti
  sparissero. Ora il conteggio è corretto e dopo `attack all` viene mostrato un riepilogo
  di **bottino a terra** e **resti da assorbire**. (Gli oggetti a terra non sparivano
  davvero: persistono per location.)
- **Guerra tra sette**: la scena del fronte elencava nemici/caduti **ovunque nella
  guerra**, mentre `attack`/`absorb` agiscono solo su chi è **nella tua location** →
  sembrava impossibile colpirli. Ora la scena mostra **solo chi è davvero presente**, e
  un `attack <nome>` a vuoto ti **indica dove si trova** il bersaglio.
- **Rating che calava** salendo i livelli: il `combat_power` del giocatore **ignorava i
  livelli di coltivazione** (Qi/Corpo/Anima/Dao). Ora vi attingono tutti e quattro:
  coltivare **alza sempre** il rating.

### Bilanciamenti assorbimento
- Gli umani danno **più Dao** (resa 0.18→0.30, con un **minimo legato al regno** del
  bersaglio) — il Dao non è più la voce più lenta.
- Il Dao assorbito **scala con il livello della tua setta** (tier 1 → 1-2; tier 3 → 3-4+).
- Lieve rimodulazione: meno dominanza di forza/vitalità, anima e Dao più rilevanti.

### `use all`
Nuovo comando per usare **tutti** gli oggetti consumabili dello zaino in sequenza.

Nuovi test: `tests/test_fixes.py` (6). Suite totale: **291 passati**, 1 rosso atteso (LLM).

---

## Aggiornamento 4 — Dao Spazio/Tempo/Destino → Heaven's Defiance → Tribolazioni

Nuovo modulo `engine/systems/dao_powers.py` + estensione di `engine/systems/tribulation.py`.

### I tre Dao profondi, differenziati per ruolo
- **Spazio = Dao distruttivo.** A comprensione crescente: perfora la difesa (fino ~95%),
  poi colpi critici "istantanei", poi **echi spaziali** (un attacco → +1/+2/+3 colpi).
  Integrato come passiva in `_attack_auto` (pierce + extra strikes + crit).
- **Tempo = Dao della coltivazione.** Accelera coltivazione e affinamento Dao
  (`time_cultivation_mult`, fino a ~×2.3) e in combattimento dà **schivata/iniziativa**
  (riduce i danni subiti). Integrato in `cmd_cultivate`, `cmd_comprehend`, `_attack_auto`.
- **Destino = Dao della fortuna.** Alza la riuscita del breakthrough e ne riduce la
  letalità (`fate_breakthrough`), e migliora la rarità dei bottini (`fate_loot_bonus`).
  Integrato in `cultivation.attempt_breakthrough` e in `loot`.

### Heaven's Defiance + Tribolazioni divine
- `heaven_defiance = comprensione(Spazio)+Tempo)+Destino)`: più sfidi le leggi
  dell'universo, più il Cielo ti vuole cancellare (`defiance_label`).
- Superata una soglia di defiance, **al breakthrough scatta una tribolazione divina** di
  potenza pari al regno + defiance. Comando **`tribulation`** per affrontarla quando incombe.
- **Affinità col Fulmine = domi il castigo:** ogni folgore assorbita dà benedizioni e
  **risveglia/poten­zia il Dao dello Spazio**; superare la prova **azzera la corruzione
  dell'Abisso** (`soul_residue → 0`). Chi non regge resta ustionato (ferite + arretramento),
  ma di norma **non muore** (coerente con la tua richiesta anti-morte-trappola).
- `dao` ora mostra i poteri profondi, la sfida al Cielo e se una tribolazione incombe.

Questo chiude anche il tuo "ho finito la via degli immortali ma nessun fulmine/potere":
ora coltivare i Dao profondi attira il castigo, e domarlo dà poteri e purifica l'Abisso.

Nuovi test: `tests/test_dao_powers.py` (8). Suite totale: **299 passati**, 1 rosso atteso (LLM).

### Roadmap residua (in ROADMAP.md): punti 3-8
Nomi di livello auto-generati + progressione infinita, mercato delle pietre, tornei
"giocati" + compagni che crescono, tecniche a 3+ Dao + nuovi elementi, invasioni/caccia
territoriale, razzie alle sette, generazione di zona per affinità di setta.

---

## Aggiornamento 5 — Mercato delle pietre + Tornei "giocati" + Compagni che crescono

### Mercato delle pietre spirituali (`engine/systems/market.py`)
Nelle **città** ora c'è un mercato: `market` mostra l'assortimento, `buy <n>` acquista con
le pietre spirituali. Gli oggetti (pillole, essenze di Dao, nuclei, manuali) riusano gli
effetti di `items.py` e finiscono nello zaino (`use`). **Assortimento, potenza e prezzo
crescono col livello della setta** e lo stock si rinnova ogni giorno. La scena di una città
te lo segnala.

### Tornei "giocati" (bugfix + arricchimento)
- **Bug trovato e risolto:** il torneo scattava dentro l'avanzamento del tempo, ma i comandi
  `cultivate`/`comprehend`/`sleep`/`breakthrough` **scartavano le osservazioni**, così non lo
  vedevi mai (vedevi solo il piazzamento con `class`). Ora i tornei vengono accodati in
  `pending_reports` e il loop principale li **mostra sempre**, comunque sia passato il tempo.
- Il torneo è ora un evento **ricco**: i tuoi incontri raccontati, qualche scontro fra rivali,
  **classifica finale con podio (medaglie)** e **premiazione** (pietre + fama). Vincere
  richiama ancora i rappresentanti delle sette superiori.

### Compagni di classe che crescono (talento)
- Ogni compagno ha ora un **talento** (più alto nelle sette di livello superiore).
- **Ogni giorno** i compagni coltivano in base al talento (`daily_cohort_growth`, chiamata dal
  day-banner): i più dotati ti incalzano in fretta, i mediocri lentamente. `class` mostra la
  loro coltivazione e il loro talento, così vedi i rivali avvicinarsi (o staccarti).

Nuove tabelle: `pending_reports`, `market_offers`, colonna `talent` su `sect_cohort`
(con migrazione difensiva). Nuovi test: `tests/test_market_tournaments.py` (7).
Suite totale: **306 passati**, 1 rosso atteso (LLM).

Roadmap residua (ROADMAP.md): livelli infiniti + nomi auto-generati, tecniche a 3+ Dao +
nuovi elementi, invasioni/caccia territoriale, razzie alle sette, generazione di zona per
affinità di setta, descrizioni di combattimento ancora più ricche, e la promozione di
categoria di discepolo vincendo i tornei.

---

## Aggiornamento 6 — Livelli infiniti + nomi auto-generati, tecniche a 3+ Dao + nuovi elementi

### Coltivazione infinita con nomi generati (Parte A)
- Tolto il tetto `MAX_TIER`: la via di coltivazione **sale all'infinito**. Oltre l'Immortale
  di Giada (regno 8) i regni si generano da soli con nomi ascendenti (Sovrano Celeste, Re
  degli Immortali, … e, esauriti, si cicla con un numerale romano: "Sovrano Celeste II", …).
- `cultivation.ensure_realm(tier)` crea pigramente il regno mancante; `_breakthrough_success`
  lo usa, così sfondare oltre l'8 funziona. Il vecchio stato "peak" non si verifica più.
  (`engine/generators/cultivation_gen.py`: `realm_name_for_tier`, `requirements_for`.)

### Tecniche Dao FUSE a 3+ Dao (Parte B)
- Prima la tecnica combinata si fermava a 2 Dao. Ora la tecnica **dominante è una FUSIONE**:
  ogni Dao che supera la soglia (comprensione ≥10) vi si **unisce**, aggiungendo nome ed
  effetto e rendendola più forte — 3, 4, … Dao senza limite. Gli altri Dao mantengono la
  loro tecnica singola per varietà. (`dao_techniques.py`: `_secondary_contribution` + fusione.)
- Esempio reale: Spada+Fuoco+Metallo+Acqua → un'unica tecnica con attacco, perforazione,
  colpi extra e riduzione danni sommati.

### Nuovi Dao elementali
- Aggiunti gli **elementi base** (fuoco, acqua, terra, vento, metallo, legno) e i **superiori**
  (luce, oscurità), oltre al Fulmine già presente. Sono Dao da combattimento (alimentano la
  potenza), hanno identità di tecnica propria, e sono **ottenibili** assorbendo NPC che li
  portano (i pool di archetipo ora li includono) o comprandone l'essenza al mercato.

Nuovi test: `tests/test_infinite_fusion.py` (8). Suite totale: **314 passati**, 1 rosso atteso (LLM).

Roadmap residua (ROADMAP.md): livelli di SETTA infiniti, invasioni/caccia territoriale,
razzie alle sette, generazione di zona per affinità di setta, promozione di categoria di
discepolo vincendo i tornei, e descrizioni di combattimento ancora più ricche.

---

## Aggiornamento 7 — Sette infinite, zone affini, promozioni, caccia e razzie

### Livelli di setta infiniti (#1)
`tier_name` è ora procedurale oltre la Setta Celeste (Setta Trascendente, Dominio
Primordiale, … con numerale quando si esauriscono). Gli inviti delle sette superiori non
hanno più tetto: si ascende sempre più in alto, con maestri scalati ai nuovi regni
(anche oltre l'8, grazie a `ensure_realm`).

### Generazione di zona per affinità (#4)
Le zone hanno un elemento affine (quello della setta che vi caccia, o uno stabile per
zona) e la maggior parte degli abitanti porta **quel Dao**: cacciando/assorbendo in una
zona ottieni soprattutto il suo elemento. (`zones._zone_element` + `dao_gen.bias_dominant`.)

### Promozione di categoria vincendo i tornei (#5)
Vincere un torneo ti fa **salire di categoria di discepolo** lungo una scala estesa
(Servitore → … → Discepolo del Nucleo → … → Giovane Patriarca). In cima sblocchi la
possibilità di guidare una RAZZIA. (`sects.promote_rank` + scala `RANK_LADDER`.)

### Caccia ai mostri premiata (#2, hook)
Uccidere creature (bestie/demoni/spiriti) ora dà **fama** e **ripulisce gradualmente
infamia e sospetto**: la caccia ai mostri riscatta il nome.

### Razzie alle sette — prima versione (#3)
Nuovo comando **`raid`**: alla sede di una setta rivale la assalti **da solo**, abbatti
i membri presenti e — se li sconfiggi tutti — ne **spezzi l'influenza**, razzii pietre e
**trafughi un manuale segreto** (finisce nello zaino, si impara con `use`). Lascia resti
da `loot`/`absorb`. Ti rende temuto e infame.

### Descrizioni di combattimento più ricche (#6)
Ampliati i repertori di verbi (colpi tuoi e del nemico) e aggiunte frasi-tecnica dedicate
agli 8 nuovi elementi (fuoco, acqua, terra, vento, metallo, legno, luce, oscurità).

Nuovi test: `tests/test_sect_expansion.py` (7). Suite totale: **321 passati**, 1 rosso atteso (LLM).

### Roadmap residua (il pezzo grosso rimasto)
Il **loop completo invasioni/caccia territoriale** con il "campione nemico che ti dà la
caccia se uccidi troppo" e l'infiltrazione nei territori delle specie resta da costruire
(è il sistema più grande). Le razzie potranno poi espandersi: conquista di territori →
più attacchi/invasioni subite.

---

## Aggiornamento 7 — Caccia territoriale + audit dei sistemi avanzati

### Correzione del mio assessment precedente (trasparenza)
Auditando il codice ho trovato che **diverse feature che avevo elencato come "mancanti"
erano già implementate e funzionanti** (verificate con smoke-test):
- **Livelli di setta infiniti** — `tier_name` genera nomi all'infinito ("Trono del Dao",
  "Setta Trascendente II", …) e gli inviti non hanno tetto.
- **Razzie alle sette (solo)** — `raid` alla sede di una setta rivale: ne abbatti i membri,
  ne spezzi l'influenza, razzii pietre e **rubi un manuale segreto**.
- **Generazione di zona per affinità di setta** — `populate_zone` fa portare al ~70% degli
  abitanti il Dao affine alla zona.
- **Promozione di categoria vincendo il torneo** — arrivare 1° fa salire di categoria di
  discepolo (`RANK_LADDER`); in cima ("Giovane Patriarca") sblocca le razzie.

### Caccia territoriale (NUOVO, punto 2)
- Uccidere creature selvagge (bestie/demoni/spiriti) ora dà **fama** e **abbassa sospetto e
  infamia**: diventi un flagello dei mostri, non un sospettato.
- Ma se ne **stermini troppe** (soglia per specie), un **CAMPIONE** della specie (Re Bestiale
  / Signore Demoniaco / Antico Spirito) si mette **sulle tue tracce** riusando il sistema dei
  cacciatori: ti insegue, ti raggiunge e ti affronta. Abbatterlo dà **gloria** (molta fama,
  crollo del sospetto); altrimenti puoi rifugiarti ('home') finché non si placa.

### Descrizioni di combattimento più ricche (punto 6)
- Le descrizioni dei colpi ora pescano da **più formulazioni** per fascia di danno (sfiori /
  incassa / barcolla / squarcia), con varietà ad ogni colpo. I verbi delle tecniche elementali
  (fuoco, acqua, terra, vento, metallo, legno, luce, oscurità) erano già presenti.

Nuovi test: `tests/test_territorial.py` (5). Suite totale: **326 passati**, 1 rosso atteso (LLM).

### Stato della roadmap
Dei 6 punti richiesti: **#1, #3, #4, #5 erano già fatti**; **#2 (caccia territoriale) aggiunto
ora**; **#6 (combattimenti più ricchi) migliorato**. Resta spazio per rifinire ancora la varietà
narrativa dei combattimenti e per dare più "vita" alle invasioni mondiali esistenti.

---

## Aggiornamento 8 — Rifinitura narrativa dei combattimenti

- **Colpi del nemico** ora pescano da più formulazioni per fascia di danno (schivi /
  graffia / accusi / vacilli), con varietà a ogni scambio.
- **Colpi di grazia** variati: niente più una sola frase fissa, ma finisher diversi per le
  uccisioni fulminee e per quelle "tirate" (mantenendo i marcatori usati dal motore: «★»,
  «ucciso», «(N round)»).
- **Colore ambientale** durante gli scontri prolungati: agli intervalli di stato compare a
  volte una riga d'atmosfera (terreno che si incrina, onde d'urto, pressione spirituale…).

Nuovi test in `tests/test_territorial.py` (varietà di colpi nemici, pool di colore).
Suite totale: **326 passati**, 1 rosso atteso (LLM).

> Resta come polish futuro dare più "vita" alle invasioni mondiali (più varietà di ondate,
> ricompense e reazioni del mondo), che oggi esistono ma sono essenziali.

---

## Aggiornamento 9 — Più vita alle invasioni mondiali

Il sistema `world_events.py` era statico (una sola ondata fissa, due tipi, e se la ignoravi
moriva gente e basta). Ora le invasioni sono VIVE:

- **Terzo tipo: Marea Spettrale** (spiriti), oltre a Marea di Bestie e Incursione Demoniaca.
- **Campione**: le invasioni forti (minaccia ≥4) sono guidate da un boss (Bestia Alfa /
  Generale Demoniaco / Spettro Ancestrale), più tosto e con nome proprio. Abbatterlo è il
  momento decisivo e dà ricompense extra.
- **Rinforzi**: se tardi a difendere, ogni ~8 tick l'ondata si **ingrossa** (fino a un tetto),
  con avviso. Ignorarla non è più gratis: peggiora.
- **Difensori locali (il mondo reagisce)**: gli abitanti combattono da soli e abbattono
  qualche invasore; se ripuliscono tutto **si salvano da soli** (gloria e bottino a loro!).
  Ma il **campione è troppo forte per loro**: le invasioni con boss richiedono il giocatore.
- **Ricompense scalate + bottino**: fama e pietre crescono con minaccia, numero di ondate e
  presenza del campione; respingere un'invasione con boss lascia un **Trofeo** (oggetto utile).
- **Descrizioni**: avvisi di comparsa, rinforzi e campione più ricchi; `events` mostra il
  campione in campo.

Nuove colonne `champion_id`, `reinforce_tick` su `world_events` (con migrazione difensiva).
Nuovi test: `tests/test_invasions.py` (6). Suite totale: **334 passati**, 1 rosso atteso (LLM).
