
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

---

## Aggiornamento 10 — Fix dal playtest (loot, attack all, assorbimento, potenza Dao, zone, viaggi)

### Bug del loot dopo `attack all` (RISOLTO — causa trovata)
Durante `attack all`, l'avanzamento del tempo tra un'uccisione e l'altra faceva **vagare le
creature ancora vive** in location adiacenti: il loop continuava a colpirle e il loro
bottino/resti cadevano dove si erano spostate, non dove stavi tu. Ora: il bottino delle tue
uccisioni si deposita SEMPRE **dove sei tu**, e durante la sequenza i bersagli vengono
**richiamati sul posto** (così anche i resti per `absorb all` restano raccoglibili).

### `attack all` ora colpisce TUTTI + nuovi filtri
- `attack all` attacca **creature E umani** presenti (prima solo creature).
- `attack humans` → solo gli avversari umani; `attack creatures` → solo le creature.

### Assorbimento più ricco
- **Qi**: divorando un coltivatore ne assorbi il qi → avanza la tua coltivazione.
- **Più Dao, vari**: prima prendevi solo il Dao più alto (quasi sempre «spada»); ora assorbi
  un frammento dei **Dao principali** del bersaglio (fino a 3), quindi vari e in linea con chi
  divori. Chi ha più Dao ti arricchisce di più Dao.

### Potenza dei Dao (nuova formula, come da tua specifica)
La forza ora cresce molto col **numero** di Dao e (super-linearmente) col loro **livello**:
`2.5·media(L^1.3)·N^(0.4+0.6·log10 L)`. Tarata sui tuoi esempi: 2 Dao liv.10→~100, 3→~150;
1 Dao liv.100→~1000, 2→~3000, 3→~6000. Vale per giocatore e NPC ed è il contributo principale
all'attacco. (Conseguenza voluta: gli scontri pesano di più sull'attacco — i numeri di
combattimento andranno ritarati col tuo feedback.)

### Zone di caccia che si RIGENERANO
Bug: una zona si popolava **una volta sola** e mai più. Ora dopo averla ripulita si
**ripopola nel tempo** (cooldown ~1 giorno), così puoi tornare a cacciare e accumulare punti
setta.

### Tribolazione da ASSORBIMENTO + Colpi della Tribolazione
Divorare troppi cadaveri (oltre una soglia) ti fa crescere troppo in fretta: il Cielo ti
reputa una minaccia e scaglia una **tribolazione**. La domi in base al tuo **Dao del Fulmine**
(più è alto, più potere assorbi) e, sopravvivendo, sblocchi la **«Folgore della Tribolazione»**,
un colpo più potente del Fulmine base.

### Comandi di viaggio diretto
- `warzone` → ti porta al **fronte di guerra** attivo più vicino.
- `raidtarget` → ti porta alla **sede di una setta rivale**, pronta per il `raid`.

Nuovi test: `tests/test_playtest_fixes.py` (8). Suite totale: **342 passati**, 1 rosso atteso (LLM).

---

## Aggiornamento 11 — Invasioni guidate + conseguenze dell'espansione + nuovo README

### Invasioni guidate dal giocatore (Punto 1) — `engine/systems/sect_invasion.py`
Al **rango alto** di discepolo (Erede della Setta / Giovane Patriarca) sblocchi `invade`:
- **guidi la tua setta** contro la sede di una setta rivale, con **alleati** che combattono
  con te (più rango = più seguito);
- affronti TU i pezzi grossi (patriarca/anziano), gli alleati travolgono il resto;
- vincendo **CONQUISTI** la sede: l'influenza rivale crolla (a zero → setta *soggiogata*), la
  sede passa sotto il controllo della tua setta (`owner_faction_id`), razzii pietre, un
  **tesoro di guerra** e un **manuale** rubato, la tua setta si espande, +fama.
- Gate sul rango con messaggio chiaro se non sei abbastanza in alto.

### Espansione = ritorsione (Punto 2) — `world_events.py`
Più la tua setta conquista, più i nemici colpiscono i **tuoi** territori:
- le invasioni mondiali bersagliano con probabilità crescente le **tue roccaforti**
  (location controllate dalla tua setta + la tua sede), con avviso «⚔ RITORSIONE!»;
- aumenta anche la **frequenza** degli attacchi con il numero di conquiste.

### Nuovo README
`README.md` riscritto da zero per GitHub: panoramica, avvio, elenco completo delle feature
(coltivazione infinita, Dao e fusione, Dao profondi + Heaven's Defiance, tribolazioni,
Abisso, sette/tornei/mercato, guerra/razzie/invasioni guidate, invasioni mondiali, caccia
territoriale), riferimento dei comandi, architettura, test e note di bilanciamento.

Nuovi test: `tests/test_invasion_lead.py` (3). Suite totale: **345 passati**, 1 rosso atteso (LLM).

---

## Aggiornamento 12 — Fix tribolazione del Cielo + Sfida di rango

### Tribolazione del Cielo: ora parte DA SOLA (bug di calibrazione risolto)
Prima la tribolazione legata alla **Sfida al Cielo** (`heaven_defiance`) veniva controllata
**solo** al breakthrough riuscito o digitando `tribulation` a mano: così potevi arrivare a
defiance altissima (es. 1139 «assoluta») senza che il castigo arrivasse mai. Ora il controllo
è agganciato allo **scorrere del tempo** (`world_tick`): superata una nuova soglia, la
tribolazione **scatta automaticamente** ed è sempre mostrata (coda report). Verificato:
defiance 1139 → folgore entro pochi tick.

### Nuova via di promozione: `challenge` (sfida di rango)
Oltre ai tornei, ora puoi salire di categoria **sfidando un anziano di rango superiore**:
`challenge` (alias `sfida`) lancia un duello **non letale** col tuo potere reale contro la
soglia attesa del rango successivo. Se sei sovra-allenato per il tuo rango **lo travolgi e ne
prendi il posto** (+fama); se sei acerbo, vieni respinto. Una sfida al giorno (cooldown).
Al rango massimo sblocchi l'invasione guidata (`invade`).

Nuovi test: `tests/test_tribulation_and_challenge.py` (5). Suite totale: **350 passati**, 1 rosso atteso (LLM).

---

## Aggiornamento 13 — Storia, scelte, legami e reincarnazione

Ispirato a *OOC: The Playable Anime* (scelte suggerite, statistiche visibili, finali
sbloccati da condizioni, memoria degli obiettivi, *Return by Death*) e ai giochi di
coltivazione (*Tale of Immortal*: incontri fortuiti, NPC con vite e rancori). Regola
mantenuta: **il motore decide, il DB è l'unica verità**; l'LLM resta opzionale.

### Rifiniture
- Interfaccia tutta in italiano (`Ti trovi a`, `Presenti`, `Uscite`, `Nome/Stato/Luogo`).
- Scelta del **nome** alla creazione del personaggio (default «Viandante»).
- **Riga di stato** dopo ogni comando (giorno/ora, regno, Qi, Spirito, ferite, pietre,
  compagno). `hud off` per nasconderla.
- **Aiuto per categorie** (`help`, `help legami`, `help tutto`): l'essenziale prima,
  il resto su richiesta. Testo in `engine/cli/help_text.py`.
- I **ricercati** e i tuoi legami sono segnalati in `look` (prima un ricercato sembrava
  un innocuo «mercante»).
- Il traduttore in linguaggio naturale ora conosce **tutti** i comandi (li ricava
  dall'aiuto; prima ne conosceva circa 25 su 60).
- I test forzano l'LLM spento (`tests/conftest.py`): niente più test «rosso atteso».

### Azioni suggerite (`engine/systems/suggestions.py`)
Dopo ogni comando 2–4 azioni numerate e sensate per la situazione (minacce, bottino,
breakthrough pronto, taglie alla tua portata, setta, persone, ritmo della giornata,
esplorazione *alla tua portata*). Scrivi il numero per eseguirla. Non suggerisce scontri
con chi è più forte di te né zone troppo pericolose. `suggest off` per nasconderle.

### Incontri a scelta (`engine/systems/encounters.py` + `encounter_data.py`)
18 mini-scene (il vecchio morente, il Frutto Spirituale, la caverna sigillata, il patto
demoniaco, il Giovane Maestro, la bisca, la tempesta viola…), con prove sulle tue qualità
reali (Corpo, Anima, Qi, Talento, Istinto, Fortuna, Karma, Potenza). Prima di scegliere
vedi quanto è probabile riuscire (*sicura / favorevole / incerta / rischiosa /
disperata*) e, per gli scontri, quanto ti sembra forte l'avversario. Capitano viaggiando;
se te ne vai, l'occasione svanisce.

### Legami (`engine/systems/bonds.py`)
- Nuovi comandi: `talk`, `gift <nome> <pietre>`, `spar`, `recruit`, `dismiss`,
  `disciple`, `bonds`.
- **Compagno di viaggio**: ti segue, combatte al tuo fianco, cresce ogni giorno; se la
  tua fama si fa oscura e lui è onorevole, se ne va.
- **Maestro**: +25% alla coltivazione e, parlandogli, insegnamenti sul tuo Dao.
- **Rivali e NEMESI**: chi ti sfugge umiliato, o chi giura vendetta per un amico che hai
  ucciso, si ritira ad allenarsi e **torna più forte** a cercarti. Quando ti trova si
  apre una scena: combattere, placarlo a parole o fuggire. Ucciderla chiude il conto.
- `attack all` non colpisce mai compagno e maestro.

### Storia personale e obiettivi (`engine/systems/storyline.py`)
Ogni origine ha un arco in 4 capitoli (*Il villaggio di cenere*, *Il peso del nome*,
*L'invidia del Cielo*, *Due anime*, *L'eredità contesa*, *La fame dell'Abisso*) che si
apre da solo al momento giusto (giorni vissuti, regno, un nemico abbattuto). Il comando
`goals` mostra capitolo in corso e traguardi vicini. Titoli: `titles`.

### Morte → epilogo → reincarnazione (`engine/systems/rebirth.py`, `engine/cli/lifecycle.py`)
La morte non chiude più la partita. Ricevi un **epilogo** scelto dalle tue statistiche
(11 destini, dall'«Immortale di Giada» a «Una Foglia nel Vento»), nel luogo della morte
sorge la tua **tomba** (metà delle pietre + una reliquia con la tua tecnica, si reclama
con `loot`), e puoi **rinascere nello stesso mondo** con una nuova origine e un
frammento ereditato (un Dao, la memoria del regno, o radici temprate). `lives` elenca le
vite passate. Con l'LLM attivo l'epitaffio può essere narrato, sempre sui soli fatti.

Nuovi test: `tests/test_story_systems.py` (26). Suite totale: **377 passati**.

---

## Aggiornamento 14 — Elementi, stati, fusioni, Dao superiori, destini, bestie, arti, maestri segreti e durata della vita

Ispirato a *Tale of Immortal* (destini, campi, emorragie), *Amazing Cultivation Simulator* e
*Yi Xian* (Cinque Elementi, professioni), ai Duo Boon di *Hades* e ai topoi wuxia/xianxia
(maestri nascosti, tombe delle spade, arti demoniache dal prezzo terribile, l'alchimista
nell'anello).

### 0. Scontri più lunghi
La vitalità usata nello scontro si moltiplica (fino a ×16) quando gli avversari si
equivalgono, e torna normale quando il divario è enorme (`combat.duel_scale`): tra pari
3-6 round, i massacri restano immediati.

### 1-4. Ciclo dei Cinque Elementi, stati, fusioni leggendarie, domini
- `engine/systems/elements.py`: generazione Legno→Fuoco→Terra→Metallo→Acqua; **catene di
  2, 3, 4 e 5 elementi** con nome (es. «Vulcano Vivente», «Ciclo Perfetto dei Cinque
  Elementi») e bonus crescenti; distruzione contro il Dao dominante del nemico (+25%);
  conflitti interni senza l'elemento-ponte; **22 fusioni leggendarie** a 2-3 Dao (anche
  superiori); **Dominio** a comprensione 500.
- `engine/systems/combat_states.py`: ustione, gelo, emorragia (cumuli), stordimento,
  accecamento, pressione, terrore, confusione, rigenerazione, scudo, velocità, drenaggio…
  Valgono anche per i nemici. `dao` e `techniques` mostrano catene, fusioni attive e quelle a portata.

### Dao superiori (`engine/systems/dao_superiori.py`)
11 nuovi Dao che si **risvegliano** con imprese: Karma (|karma| ≥ 300), Massacro (60 vite),
Vita e Morte (3 vittorie sull'orlo della morte), Reincarnazione (terza vita), Yin-Yang
(Luce e Oscurità ≥ 50), Caos (tutti i 5 elementi ≥ 25), Sangue, Illusione, Stelle,
Vuoto, Creazione. Ognuno ha stato, nomi delle tecniche e fusioni proprie.

### 5. Destini alla nascita e talento dei rivali (`engine/systems/destinies.py`)
Alla creazione: origine + **destino** (mano di 6 con rarità, 2 rimescolate; i leggendari
dalla seconda vita) + **talento dei rivali** (facile/normale/difficile/leggendario).
Il Portatore dell'Abisso ha ora **sempre** il talento più alto.

### 6. Demone interiore (`engine/systems/heart_demon.py`)
Prima del breakthrough (una volta per regno) il passato prende forma: affrontarlo,
accettarlo o rimandare. Perdere genera una nemesi: il Demone del Cuore.

### 7. Bestie spirituali (`engine/systems/beasts.py`)
`tame`, `beast`, `feed`, `release`. Talenti (comune → divina), elementi, avvistamenti di
bestie **rare** (dal regno 3), **leggendarie** (Fenice, Drago, dal 5) e **ibride**
(Drago-Fenice, Qilin del Tuono, Fenice di Ghiaccio… dal 6).

### 8. Professioni (`engine/systems/professions.py`)
Alchimia, Talismani, Forgia: `profession`, `gather`, `recipes`, `craft`. Materiali da
raccolta e caccia; livelli 1-10; pillole (anche di longevità), talismani da battaglia,
armi riforgiate.

### 9. Spirito dell'arma (`engine/systems/weapon_spirit.py`)
Un'arma pregiata si risveglia dopo 25 vittorie (o alla forgia): elemento, livelli, stato.

### 10. Durata della vita (`engine/systems/lifespan.py`)
80 anni di base (senza malattie); ogni breakthrough di regno la **raddoppia**; destini e
elisir la modificano; si può morire di vecchiaia (epilogo dedicato).

### 11. Maestri segreti (`engine/systems/secret_masters.py`)
27 maestri in 11 vie (Spada, Demoniaca, Alchimia, Talismani, Forgia, Fulmine, Corpo,
Anima, Giustizia, Bestie, Abisso), a livelli: il successivo appare solo dopo aver appreso
dal precedente e superato una soglia più alta (es. Spada 50 → 250 → 1000; vite tolte
10 → 100 → 1000). Insegnano tecniche con stati propri; alcune hanno un prezzo (karma,
infamia, anni di vita). `masters` mostra i progressi.

Nuovi test: `tests/test_elements_states.py` (12), `tests/test_progression_systems.py` (18).
Suite totale: **407 passati**.

---

## Aggiornamento 15 — Maestri segreti infiniti

I maestri segreti ora sono **infiniti**, come i regni. Dopo i 27 maestri scritti a mano,
ogni via (Spada, Demoniaca, Alchimia, Talismani, Forgia, Fulmine, Corpo, Anima, Giustizia,
Bestie, Abisso) genera maestri sempre più antichi — «Il Santo della Spada, Immortale di
Giada», «… Sovrano Celeste», «… Re degli Immortali» e oltre — che ti accompagnano fino alle
vette più alte:
- ognuno richiede una soglia più alta nella sua arte (Dao ×1,5, vite tolte ×1,6, livelli di
  professione +3, fama ×1,6, …) **e** un regno di coltivazione più alto;
- insegna una tecnica più potente (+10% di potenza a livello) con uno stato più frequente e
  più forte; le vie con un prezzo (demoniaca) chiedono un prezzo che cresce;
- le professioni non hanno più un livello massimo.

`masters` mostra per ogni via quanti maestri hai incontrato e chi sarà il prossimo.
Nuovi test (3). Suite totale: **410 passati**.

---

## Aggiornamento 16 — Il mondo del coltivatore: reami segreti, dimore, sette proprie, radici spirituali, mondi superiori

Tutto ciò che mancava rispetto ai temi classici del genere, in tre fasce.

### Fascia 1 — la vita del coltivatore
- **Reami segreti** (`secret_realms.py`): ogni ~12 giorni se ne apre uno in un luogo
  selvaggio per 3 giorni. `realm`, `enter`, `delve`: piani con guardiani, scrigni sigillati,
  discepoli rivali, pozze di Qi; in fondo la **Sala dell'Eredità** (tecnica, frammento di
  Dao o anni di vita). Scalato al tuo regno.
- **Ritiro a porte chiuse** (`seclusion.py`): `ritiro <giorni> [dao]` in montagna, rovine,
  sede o dimora; giorni di coltivazione senza fatica, gli anni passano davvero, a volte
  qualcuno ti disturba. **Illuminazioni improvvise** (balzi nel Dao) e **vittorie contro
  chi è più forte** (fama, titoli, illuminazione).
- **Classifiche del Cielo** (`rankings.py`): `classifica [giovani|sette]`, con premi e
  titoli quando sali oltre le soglie (in classifiche abbastanza affollate).
- **Grotta-dimora** (`cave_abode.py`): `dimora reclama/potenzia/raccogli/torna`; ali con
  livelli infiniti: campo di erbe, raccolta del Qi, stanza del ritiro, alchimia, formazione
  difensiva, stalla delle bestie.
- **Discepoli e setta propria** (`own_sect.py`): `accogli`, `insegna`, `discepoli`;
  dal regno 4 `fonda <nome>`: tributi, reclutamento, aspiranti attratti dalla fama, assalti
  delle altre sette da respingere (`setta difendi`).

### Fascia 2 — società, talento e mondo
- **Vie delle sette** (`alignment.py`): ortodosse, eterodosse, demoniache, con regole
  d'ingresso, premi per le uccisioni e l'emissario demoniaco per chi ha molta infamia.
- **Grande Assemblea dell'Alleanza Marziale** (`assembly.py`): torneo a 8 ogni ~45 giorni,
  incontri non letali con tre stili; il vincitore è **Capo dell'Alleanza Marziale**.
- **Fratellanza giurata e compagno del Dao** (`oaths.py`): `giura`, `chiama`, `proponi`;
  combattono con te, il fratello in pericolo va salvato (o il giuramento si spezza),
  doppia coltivazione col compagno del Dao, lutto e Spergiuro.
- **Radici spirituali** (`spirit_roots.py`, `radici`): 9 elementi con punteggio senza tetto
  e gradi infiniti; ogni radice forte genera un talento; **tutte le 511 combinazioni** hanno
  un effetto (generazione, distruzione con elemento-ponte, coppie speciali, armonia di N
  radici, Corpo dei Cinque Elementi, Radice del Caos). Il **Divoratore** si nutre delle
  radici delle vittime e migliora all'infinito.
- **Metodi di coltivazione** (`gongfa.py`), **casa d'aste** (`auction.py`) con offerte
  contro limiti nascosti, **archi del mondo** di metà partita (`world_arcs.py`).

### Fascia 3 — oltre
- **Ascensione ai mondi superiori** (`ascension.py`): dal regno 9 (poi 12, 15…) apri la
  Porta Celeste verso un nuovo continente generato; strati di mondo infiniti.
- **Politica di setta** (`sect_politics.py`): anziani e loro favore, bacheca delle
  missioni, protettori e false accuse. **Faccia e onore** (`face.py`): sfide pubbliche e
  faide di clan che crescono senza fine.
- **Formazioni e Domatore di Bestie** (`formations.py`, `classes.py`): due nuove arti;
  `sintonia <elementi>` lega l'arte agli elementi delle radici e crea la tua **classe**
  (es. Maestro delle Formazioni della Fiamma); formazioni piazzabili (raccolta, difesa,
  uccisione, teletrasporto); stato **veleno**; nuove vie di maestri segreti.
- **Origine «Trasmigratore col Sistema»** (`system_quest.py`): missioni quotidiane, punti
  e negozio del Sistema (`sistema`), e un arco d'origine in 4 capitoli.

Aiuto (`help mondo`, `help dimora`, …), azioni suggerite e obiettivi aggiornati.
Nuovi test: `tests/test_world_features.py`, `tests/test_world_features2.py`.
Suite totale: **434 passati**.
