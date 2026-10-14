
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

---

## Aggiornamento 17 — Lignaggi di sangue e pilota automatico

### Lignaggi di sangue (`engine/systems/bloodlines.py`, comando `sangue`)
- **Come si ottengono**: le bestie d'alto livello e quelle rare lasciano un'**Essenza di
  Sangue** (`use essenza`); le leggendarie e le ibride a volte anche un Nucleo Antico. Il
  **Divoratore** beve il sangue direttamente quando divora una bestia (×1,5). Per eredità:
  destino «Sangue di Drago» o «Corpo della Fenice», un sangue di famiglia per l'origine di
  clan, e alla reincarnazione un quarto del lignaggio più forte.
- **Concentrazione senza tetto**, a gradi: Tracce, Risvegliato, Concentrato, Puro, Ancestrale,
  Sacro, Primordiale, poi Sangue del Caos I, II, III…
- **Manifestazioni ibride**: a ogni grado una parte del corpo muta. Occhi (critici), artigli
  (attacco), squame/piume/guscio (danni ridotti), ali (schivata), corna/coda (perforazione;
  al Primordiale un colpo in più). Dal grado Puro si sblocca la **tecnica innata**, cioè lo
  stato del suo elemento. Ogni famiglia ha un **dono**: la Fenice rialza dalla morte, il Drago
  schiaccia, la Tartaruga indurisce, il Qilin acceca… Le stirpi longeve allungano la vita.
- **Trasformazione completa** (`trasformati`, dal grado Sacro): nello scontro successivo
  diventi la bestia sacra. Costa spirito e richiede qualche giorno di riposo.
- **Fusione** (`fondi_sangue <n> <m> [...]`): due o più lignaggi Puri diventano un sangue
  ibrido, per esempio «Drago-Fenice di Fuoco e Ghiaccio», con elementi e manifestazioni di
  entrambi. Si può fondere ancora, e il sangue nuovo delle specie fuse confluisce lì.
- **Sangue in rivolta**: lignaggi non fusi con elementi in conflitto possono ribellarsi
  (ferite, una crepa nel cuore). Fonderli o praticare l'arte del Domatore li calma.
- Nuova via di **maestri segreti: Sangue Antico**, infinita come le altre.

### Pilota automatico (`engine/systems/autopilot.py`, comando `auto`)
- `auto <giorni>` (al massimo 60) fa vivere i giorni al personaggio da solo, con i comandi
  veri del gioco. Alla fine mostra un **resoconto**: coltivazione, uccisioni, pietre, Dao,
  livelli dell'arte, età e momenti salienti.
- Si imposta prima di partire:
  - **attività** con pesi: coltiva, dao, caccia, raccolta, lavoro, insegna;
  - **bersagli**: nessuno, bestie, ricercati, deboli o tutti. Non attacca mai chi è più
    forte, e chi è alla pari solo con «tutti»;
  - **assorbi**, **loot**, **oggetti** (pillole ed essenze) e **sfonda** (breakthrough da solo);
  - **condotta** negli incontri casuali minori: virtuosa, prudente, opportunista o spietata;
  - **fermate** facoltative: reame, assemblea, asta, invasione.
- **Si ferma da solo** davanti a ciò che va giocato: capitoli della storia, maestri, scene
  importanti (nemesi, demone interiore, emissari…), tornei e sfide di setta imminenti,
  invasioni vicine, guerre, assalti alla tua setta, fratelli in pericolo, sfondamento pronto,
  ferite gravi, vecchiaia, morte. Ctrl+C lo interrompe salvando ciò che è stato fatto.

Nuovi test: `tests/test_bloodlines.py` (11) e `tests/test_autopilot.py` (6).
Suite totale: **451 passati**.

---

## Aggiornamento 18 — L'arma viva

L'arma ora cresce con il **tempo** e con l'**uso** (`engine/systems/weapon_spirit.py`, comando `arma`).
- **Esperienza** da molte fonti: vittorie (molta di più contro chi è più forte di te), sconfitte,
  sessioni sul Dao d'arma e ogni giorno passato con l'arma in pugno, anche in ritiro o in stato
  etereo. Più è lungo il **legame**, più cresce in fretta (fino al doppio dopo un anno insieme).
- **Tempra automatica**: l'arma sale da sola di rarità (comune → raffinata → pregiata →
  divina) e poi di regno, tenendo il passo con te ma senza mai superarti.
- **Risveglio per qualunque arma**: le divine si risvegliano in fretta, le comuni dopo una lunga
  strada insieme. Forgia e maestri segreti possono ancora risvegliarla subito.
- **Spirito senza tetto**, a gradi: Desto, Senziente, Maturo, Celeste, Primordiale, poi
  Spirito dell'Origine I, II…
  - da **Senziente** l'arma si dà un nome (`arma nome <nome>` per sceglierlo tu) e sprigiona
    la sua tecnica;
  - da **Matura** para un colpo mortale in ogni scontro;
  - da **Celeste** lo spirito prende forma e combatte al tuo fianco.
- Un'**arma viva non si abbandona**: un'arma più forte trovata sul campo non la sostituisce
  più in automatico. Cambiare arma azzera spirito e legame.
- `arma` mostra la qualità, il legame, la prossima tempra, lo spirito, i poteri e i nemici
  illustri abbattuti.

Nuovi test: `tests/test_weapon_growth.py` (5). Suite totale: **456 passati**.

---

## Aggiornamento 19 — Corpo, cuore e mondo vivo

- **Costituzioni speciali** (`constitutions.py`): undici corpi divini con doni e maledizioni.
  - Si nasce con uno raramente (più spesso i geni, sempre con il nuovo destino «Corpo Divino»).
  - Il corpo nasce sigillato e si risveglia a stadi senza fine: con i nuovi regni, le vittorie
    sull'orlo della morte, le illuminazioni.
  - Le Vene Yin uccidono a 20 anni se non trovi un Fuoco Yang. I Meridiani Spezzati
    dimezzano la coltivazione finché non si risvegliano, poi la raddoppiano.
- **Cuore del Dao** (0-100) e **deviazione del Qi** (`dao_heart.py`).
  - Sale con vittorie difficili, illuminazioni, giuramenti mantenuti e ritiri; scende con
    sconfitte, tradimenti, demoni interiori e sfondamenti troppo ravvicinati.
  - Sotto 30 meditare può farti deviare (ferite, esperienza persa, uno strato perduto).
    Sopra 80 arrivano più illuminazioni e sfondamenti più sicuri.
- **Tossine delle pillole**: ogni pillola di coltivazione lascia scorie che rallentano la
  coltivazione. Si smaltiscono col tempo, in ritiro, nelle tribolazioni o con la nuova
  Pillola di Purificazione. Gli alchimisti esperti ne assorbono meno.
- **Prodigi** (`prodigies.py`, `prodigi`): i rivali della tua generazione crescono da soli,
  trovano fortune (reami, sangue sacro, maestri, metodi) e ti superano se resti fermo. Le
  cronache raccontano nuovi geni, matrimoni tra sette e declini.
- **Uova e allevamento** (`beast_eggs.py`): le bestie rare lasciano uova da covare nella
  stalla della dimora (`use uovo`, `uova`). Con `alleva` il Domatore esperto ottiene uova ibride.
- **Incarichi a catena** (`npc_quests.py`: `richieste`, `incarico <n>`, `incarichi`, `consegna`):
  vendetta, scorta, recupero, guarigione e consegna, in catene di 3-5 passi con un grande dono finale.
- **Tribolazioni del fulmine celeste** (`heaven_trib.py`, `tribolazioni`): a ogni regno dal
  terzo in su, con più ondate e più forti ogni volta.
  - Dao del Fulmine sotto 30: le folgori ti feriscono.
  - Da 30: le folgori temprano il corpo e lo purificano.
  - Da 100: ne assorbi una parte crescente; cresce il fulmine (Dao, radice, affinità) e ne
    trattieni cariche da scatenare in battaglia. Tecniche speciali alla 1ª, 3ª, 6ª e 9ª.
- **Qualità di vita** (`qol.py`):
  - salvataggi in slot (`salva`, `carica`, `salvataggi`) più tre automatici ogni 5 giorni;
  - `mappa` della regione;
  - colori nel terminale (`colori`);
  - `codex` delle scoperte;
  - `tutorial` con i primi passi.

Nuovi test: `tests/test_body_world_qol.py` (11). Suite totale: **467 passati**.

---

## Aggiornamento 20 — I poteri dei protagonisti

Tutto si coltiva senza fine: ogni sistema ha livelli, gradi o cicli che continuano a salire.

- **Retaggio spezzato** (`lost_legacy.py`, comando `retaggio`; compare anche in `goals`).
  - All'inizio di ogni vita una parte del tuo talento ti è stata tolta: Osso Supremo
    strappato, Anima Primordiale frantumata, Vene Celesti sigillate, Pupilla Doppia
    strappata, Fortuna rubata, Memorie della vita precedente o Seme del Dao spezzato.
  - Salendo di regno, i custodi dei frammenti si fanno avanti. Ogni frammento ripreso ti
    restituisce potere (e, nel caso delle memorie, una tecnica).
  - Ripresi tutti e cinque, il retaggio rinasce più forte e comincia un nuovo ciclo, senza fine.
- **Maestro nell'anello** (`mentor_ring.py`, `anello`): l'anima di un antico maestro trovata
  in rovine o zone proibite.
  - Ti consiglia, migliora coltivazione e arti, e ti presta la sua forza in battaglia.
  - Lo nutri con i nuclei e si risveglia a livelli infiniti.
  - Al livello 6 il suo traditore viene a cercarlo: vendicarlo sblocca la sua eredità.
- **Spazio interiore** (`inner_space.py`, `spazio`): dalla bottiglietta di giada (campo con
  raccolto moltiplicato) al **Mondo Interiore** dal livello 5 (coltivazione più rapida ovunque).
  Si trova nei reami segreti e si risveglia da solo al quinto regno.
- **Cloni** (`clones.py`, `clone`): dal quarto regno, con una sola coltivazione condivisa.
  - Puoi dividere i compiti: uno lavora e si allena, un altro esplora e caccia, un altro
    combatte al tuo fianco.
  - I cloni crescono di livello senza fine. Se muori, un clone si sacrifica e la tua anima
    vi si trasferisce.
- **Elementi celesti** (`celestial_elements.py`, `elementi`): nove elementi, ciascuno con la
  sua classifica di essenze, che nascono nel mondo sorvegliate da un guardiano.
  - Assorbirli dà vantaggi propri dell'elemento e cresce senza fine (più ne assorbi, più
    salgono di grado).
  - Elementi diversi si armonizzano tra loro: due, cinque o tutti e nove.
- **Famiglia** (`family.py`, `famiglia`): genitori e fratelli nella città d'origine.
  - Visitarli calma il cuore del Dao; il clan cresce di livello con i tuoi regni e con i doni.
  - Va difeso quando lo minacciano; dal settimo regno puoi riportare in vita un familiare
    caduto, pagando con anni della tua vita.
- **Senso divino e livello nascosto** (`divine_sense.py`: `scruta`, `cela`): leggi chi hai
  davanti senza farti notare. Se nascondi la tua forza attiri i prepotenti, e umiliarli vale
  il doppio della fama.
- **Marionette e tesori legati al sangue** (`puppets.py`): marionette da combattimento (Forgia
  o Formazioni 3) e spade volanti, scudi, campane… nutriti col tuo sangue, a livelli infiniti.
- **Gu** (`gu.py`, `gu`): insetti spirituali da nutrire ogni giorno e da raffinare a gradi
  infiniti. Il rarissimo Gu della Primavera e dell'Autunno riavvolge il tempo alla morte.
- **Battaglie dell'anima e Bandiera delle Anime** (`soul_war.py`): anime antiche tentano di
  impossessarsi di chi divora i potenti; la bandiera raccoglie le anime degli uccisi.
- Il pilota automatico si ferma anche per gli elementi celesti, le minacce alla famiglia e i
  frammenti del retaggio.

Nuovi test: `tests/test_protagonist_features.py` (10). Suite totale: **477 passati**.

---

## Aggiornamento 21 — La trama maestra (che non finisce mai)

La storia ora ha una **spina dorsale in atti**, costruita a *storylet*: ogni capitolo si
apre quando le sue condizioni sono vere (regno, scelte fatte, mondi raggiunti), non a una
data fissa. Si legge con `trama`. **Non esiste un nemico finale**: sopra ogni verità ce
n'è un'altra, sopra ogni mondo un altro mondo.

- **Atto I — L'umiliazione**
  - L'annullamento del fidanzamento: subisci, rispondi o giuri il **duello dei tre anni**.
  - L'arcinemico.
  - La prima verità sulla **Mietitura**: qualcuno, in alto, «raccoglie» i talenti di
    ogni generazione.
- **Atto II — Il mondo è più grande**
  - Le corti dei regni.
  - Il segreto dei tuoi genitori.
  - Le razze antiche.
  - Il tradimento.
  - La prigionia.
- **Atto III — I Mietitori**: i Mietitori si mostrano, arriva la calamità dell'era, poi
  l'ascensione.
- **Atto IV e oltre — senza fine.** Per ogni mondo superiore:
  - il disprezzo dei nativi verso chi sale dal basso;
  - una nuova verità, che rivela un grado più alto dell'ordine della Mietitura (la
    gerarchia non ha cima);
  - il Signore di quel mondo;
  - una **Legge dell'Imperatore del Dao**, che aumenta la comprensione del Dao dell'8% per
    ogni legge.
- **Le scelte che il mondo ricorda** tornano nei capitoli successivi.
- **Arcinemico** (`archrival.py`, `arcinemico`), sul modello del «sistema Nemesi»:
  - ricorda le cicatrici che gli hai lasciato e le vittorie che ha avuto su di te;
  - cresce da solo e torna più forte;
  - se lo uccidi, dopo qualche settimana un erede (fratello, discepolo, figlio…) ne
    raccoglie il nome e la memoria, ogni generazione più forte.
- **Regni** (`kingdoms.py`: `regni`, `corte`, `sostieni`, `tributo`, `guerra_regni`, `trono`):
  - un regno per ogni regione, con successioni e guerre tra regni;
  - ranghi che salgono senza fine, da Suddito a Re dei Re N;
  - da Duca, se il popolo ti segue, puoi prendere il trono.
- **Razze antiche** (`races.py`: `razze`, `ambasciata`): draghi, demoni, spiriti, giganti e
  maree, con relazioni, onori a livelli infiniti, alleanze e incursioni.
- **Ere del mondo e calamità** (`eras.py`: `era`, `calamita`):
  - un'era ogni 90 giorni: Rinascita del Qi (coltivazione ×1,25), Declino (×0,85), Mille
    Scuole (gare più frequenti) o Pace;
  - ogni quarta era torna la **calamità**, con un'ondata in più ogni volta;
  - gli alleati che hai conquistato (razze, regni, setta, famiglia, fratelli giurati,
    discepoli) combattono con te.
- **Gare dei maestri d'arte** (`contests.py`, `gara`): tre prove contro maestri rivali;
  ogni vittoria aggiunge una corona («Re delle Pillole (3ª corona)»…).
- **Prigionia e fuga** (`captivity.py`, `evadi`):
  - finché sei prigioniero non puoi viaggiare;
  - la fuga richiede tre passi: studiare le guardie, trovare un alleato (che poi viaggerà
    con te), evadere.
- **Prove del cuore** (`heart_trials.py`): illusioni del desiderio, della paura e del
  rimpianto, che custodiscono le eredità dei reami segreti e i momenti chiave della storia.
- **Pilota automatico**:
  - si ferma per aggressioni, cacciatori o nemesi appena arrivati, la calamità, le gare
    della tua arte e la cattura;
  - evita i luoghi dove c'è un nemico più forte di te.
- Nuova categoria d'aiuto: `help trama`. Le azioni suggerite propongono la fuga, le ondate
  della calamità e le gare.

Nuovi test: `tests/test_master_plot.py` (11). Suite totale: **488 passati**.

---

## Aggiornamento 22 — Allenamento d'insieme (`train` / `t`)

Un solo comando per far crescere tutto insieme, invece di alternare `cultivate`,
`comprehend <dao>` e `craft`.

- **`train`** (oppure `t`, `allena`): una sessione, lo stesso tempo di una meditazione.
  - **Qi**: rende il 70% di una meditazione dedicata, perché l'attenzione è divisa.
  - **Tutti i Dao che conosci** crescono un poco ciascuno. I comuni vanno più in fretta e
    i rari più piano: Dao d'arma ×1, elementali ×0,85, sistemici ×0,75, superiori ×0,5,
    profondi (Destino, Tempo, Spazio) ×0,35.
  - I progressi frazionari si accumulano da una sessione all'altra, quindi anche i Dao più
    lenti avanzano sempre.
  - **La tua arte** guadagna esperienza a ogni sessione.
  - Valgono tutti i bonus abituali: rendimento della giornata, setta affine, Dao del Tempo,
    ere, dimora, Leggi dell'Imperatore. Si nutre anche lo spirito dell'arma, se ti alleni
    nel suo Dao.
- Le meditazioni dedicate restano più efficaci per spingere una cosa sola.
- L'azione suggerita per coltivare ora propone `train`.
- **Il pilota automatico usa `train`.** C'è una nuova attività `allena` (peso 5 di default)
  che prende il posto di `coltiva` e `dao`: restano configurabili, ma sono spente di default.
  Anche quando un'attività non è possibile (niente prede, niente ricette), il pilota si
  allena invece di meditare soltanto.
  - Esempio: `auto imposta attivita allena=5 caccia=2 raccolta=1 lavoro=1 insegna=1`.

- **Il pilota evita l'arcinemico e le nemesi** quando sono più forti di te: si allontana
  anche se la relazione non li segna come ostili.
  - Ogni aggressione ferma il pilota una volta sola: ripartendo subito non si riferma per
    lo stesso scontro.

Nuovi test: `tests/test_train_all.py` (3), più un test in `tests/test_master_plot.py`.
Suite totale: **492 passati**.

---

## Aggiornamento 23 — Ritmo, bilanciamento, svolte, narrazione, tesori

Cinque lavori, nell'ordine in cui dipendono l'uno dall'altro.

### 1. Il regista: il ritmo degli eventi (`director.py`, comando `ritmo`)
Ispirato al «director» dei giochi a storylet: gli eventi non arrivano appena le loro
condizioni sono vere, ma quando c'è spazio per goderseli.
- **Scene portate dal mondo** (arcinemico, famiglia minacciata, emissari, elementi celesti…):
  - al massimo **4 a settimana**;
  - lo **stesso tipo** di scena non torna prima di **8 giorni**;
  - una scena che non trova posto entra in **coda** e arriva appena c'è spazio, le più
    vecchie prima. Dopo 25 giorni svanisce, perché il mondo è andato avanti.
- **Scene di reazione** (battaglie dell'anima, prove del cuore, sfide in piazza): anche
  quando nascono da un tuo comando, non si ripetono a breve distanza.
- **Passano sempre** le scene urgenti o decise da te: calamità, fuga, demone interiore,
  difesa della setta.
- **Capitoli della storia:** almeno **2 giorni** tra un capitolo e il successivo. Le trame
  (origine, trama maestra, archi del mondo, maestri segreti) si **alternano** invece di
  accavallarsi.
- Un maestro segreto che non hai seguito torna solo dopo 12 giorni, non più a ogni passo.
  Il demone interiore torna più di rado se l'hai appena affrontato al regno precedente.

### 2. Bilanciamento con dati veri
Uno script fa giocare il pilota automatico per **500 giorni** con ogni origine (due mondi
per origine) e misura quando si muore, quanto si sale, cosa ferma il pilota, quali scene
arrivano e quali sistemi dominano la potenza.

**Cosa abbiamo trovato**
- La potenza dei Dao veniva **sommata** all'attacco e cresceva senza misura: milioni di
  attacco contro poche centinaia di difesa. Gli scontri si chiudevano al primo colpo e il
  regno quasi non contava: un ragazzo al primo regno batteva patriarchi del quinto.
- Altre fonti si moltiplicavano tra loro senza limite: tecniche segrete (×11), crescita del
  corpo, soglie di tutti i Dao.
- Gli NPC non seguivano un ordine coerente per regno.
- Lo sfondamento diventava una lotteria della morte ai regni alti, fino al 70% di
  probabilità di morire per regno al dodicesimo.
- Il pilota automatico perdeva la configurazione a ogni reincarnazione.
- Cacciare bestie costava karma: il karma negativo rendeva ostili tutti quelli intorno,
  che poi ti tendevano agguati.

**Il nuovo modello di potenza** (`combat.py`)
- **Il regno è la scala principale:** ogni regno vale ×1,6 sul precedente, e la crescita
  è continua strato per strato.
  - Un genio con i Dao giusti batte chi sta un regno sopra.
  - Due regni sono quasi un muro.
- **I Dao amplificano.**
  - La potenza dei Dao (la tua formula di sempre, invariata) si confronta con il «vaso»
    del tuo regno e diventa un moltiplicatore **logaritmico**, senza tetto.
  - Colpisce l'attacco più della difesa e della vitalità.
- **Crescita personale compressa.** Corpo temprato, affinità, soglie dei Dao, tecniche,
  arma, linea dell'Abisso e doni della tribolazione si sommano in un rapporto sul profilo
  base, poi compresso in modo logaritmico: ×10 vale ×1,66, ×1000 vale ×3. Cresce sempre,
  ma non schiaccia più il regno.
- Gli scontri tra pari tornano a durare più scambi.

**Le altre correzioni**
- **Sfondamento**
  - La difficoltà e il rischio di morte crescono in modo logaritmico coi regni; il
    rischio per tentativo fallito non supera il 18%.
  - Il pilota tenta da solo solo se il rischio di morte è sotto il 10%; altrimenti ti
    avvisa (una volta per regno) e decidi tu.
- **Agguati**
  - Un nemico schiacciantemente più forte non ti uccide per strada.
  - Chi ti ha appena battuto ti lascia stare per 5 giorni.
  - Se vieni colto di sorpresa, spesso riesci a fuggire ferito invece di morire.
- **Nemici dei Braccati:** se la tua origine è «braccata», i nemici iniziali sono ora
  alla tua portata, non patriarchi del quarto regno.
- **Karma della caccia:** cacciare bestie e spiriti selvaggi non costa più karma, e
  abbattere un demone è un merito.
- **Arcinemico**
  - Nasce alla tua altezza; l'erede nasce un po' sopra di te.
  - Cresce *con* te: se lo stacchi troppo, ti rincorre; se ti ha staccato, aspetta.
    Prima cresceva da solo di dodici regni in 500 giorni.
- **Divoratore:** il Qi divorato va digerito, al massimo mezzo strato al giorno e mai oltre
  lo strato in cui sei. Prima il Divoratore saliva di un regno ogni due giorni (il
  diciassettesimo regno al giorno 100), poi moriva negli sfondamenti.
- **Pillole:** valgono meno a ogni regno, come la meditazione. Prima a regni alti valevano
  decine di sessioni.
- **Cuore del Dao:** un cuore ferito torna piano verso la calma (+1 al giorno, +3 se è in
  pericolo).
  - Prima un cuore a zero era una spirale senza uscita: deviazioni del Qi a ripetizione,
    e un personaggio fermo per trecento giorni.
  - Con il cuore incrinato, il pilota non medita e lascia che si calmi.
- **Radici spirituali:** l'effetto sulla coltivazione e sui Dao ora cresce in modo
  logaritmico.
  - L'affinamento a ogni regno ha un passo massimo, e il Divoratore strappa meno radici
    quanto più ne ha già.
  - Prima le radici si moltiplicavano a ogni regno: miliardi di punti e una coltivazione
    ×400 milioni, fino al regno 168 in 500 giorni.
- **Rete di sicurezza:** se tutti i moltiplicatori di coltivazione e di comprensione insieme
  superano ×3, oltre quella soglia crescono in modo logaritmico. Aumentano sempre, ma non
  esplodono.
- **Tribolazioni del Cielo** (Spazio, Tempo, Destino):
  - le folgori crescono in modo logaritmico;
  - le benedizioni sono riassunte;
  - prima un Divoratore arrivava a 5,7 milioni di folgori e un salvataggio di 2 GB.
- **Tribolazione del Fulmine** dei regni: la potenza delle folgori segue la scala dei
  regni, così resta una prova vera anche in alto.
- **Cacciatori:** quelli più deboli di te li affronta il pilota; si ferma solo per quelli
  pericolosi.
- **Rischio di sfondamento** configurabile: `auto imposta rischio <percento>`.
- **Pilota automatico**
  - Con ferite gravi si riposa invece di fermarsi di continuo.
  - La sua configurazione, il ritmo degli eventi e le preferenze d'interfaccia
    sopravvivono alla reincarnazione.

**Risultati dopo la taratura** (14 partite simulate da 500 giorni, due mondi per origine):
- **Morti:** da 0 a 4 per partita; il Divoratore, origine «braccata» e difficile, da 5
  a 8. Prima c'erano partite con 9 morti, alcune nel primo giorno.
- **Regni raggiunti senza morti tardive:** dal 5° al 10° al giorno 500. Prima c'erano il
  168° regno da una parte e personaggi fermi al 2° per trecento giorni dall'altra.
- **Scene importanti:** circa una ogni 5-6 giorni; il pilota si ferma circa una volta
  ogni 5 giorni.

### 3. Svolte: salti di qualità, non solo numeri (`svolte.py`, comando `svolte`)
- **Volo (2° regno):** `vola <luogo>` ti porta in un luogo già visitato senza camminare. Il
  tempo dipende dalla distanza e costa Qi. Dal **6° regno** è un *Passo nel Vuoto*
  istantaneo.
- **Incarnazione del Dao:** un Dao oltre la Legge (2000, poi a ogni raddoppio, senza
  fine) si incarna. All'inizio di ogni scontro il suo stato colpisce subito, più forte a
  ogni incarnazione.
- **Il tuo Dao:** con tre Dao alla Legge, `crea_dao <nome>` li fonde in un Dao **tuo**, mai
  percorso da nessuno, che poi coltivi come gli altri. Ogni altri tre Dao alla Legge, un
  nuovo Dao tuo.
- **Capolavori:** al livello 10, 20, 30… della tua arte, `capolavoro <nome>` crea un'opera
  unica. Ogni capolavoro rende la coltivazione più rapida del 5%, per sempre.
- **Il pannello `svolte`** mette insieme queste e quelle che c'erano già (domini dei Dao,
  cloni, Mondo Interiore, forma del sangue, eredità dell'anello, Leggi dell'Imperatore),
  raggiunte e prossime. Il mondo annuncia ogni svolta quando arriva.

### 4. Narrazione meno a schede (`engine/narrative/varia.py`)
- Una piccola **grammatica generativa** alla Tracery, con memoria anti-ripetizione.
- Il testo cambia col **mondo**:
  - ora del giorno, stagioni (l'anno ha quattro stagioni);
  - un tempo atmosferico coerente per ogni giorno (sereno, pioggia, nebbia, vento,
    temporale, diverso per stagione);
  - tipo di luogo.
- Si applica alle frasi più frequenti:
  - l'alba di ogni giorno, la meditazione, l'allenamento d'insieme;
  - l'esito delle prove negli incontri, l'atmosfera che apre ogni incontro casuale;
  - una riga di ambiente in `look`.

### 5. Accorpare e svelare man mano
- **`tesori`:** un solo pannello per arma viva, maestro nell'anello, spazio interiore, Gu,
  marionette, tesori legati al sangue, bandiera, elementi celesti e cloni.
  - **`tesori cura`** fa la cura quotidiana in un colpo: raccoglie e risemina lo spazio
    interiore, nutre l'anello coi nuclei che hai e avvisa se i Gu hanno fame.
  - `tesori <nome>` mostra il dettaglio. I vecchi comandi restano validi.
- **Aiuto progressivo:** `help` mostra le categorie che hai già toccato. Le altre restano
  in fondo («Ancora da scoprire»), con il modo per svelarle. `help tutto` mostra sempre
  tutto.

### 6. Il protagonista è un uomo: fidanzata e compagna del Dao sono donne
- Gli NPC hanno ora un **genere** (`npcs.gender`). Nei salvataggi vecchi viene dedotto in modo
  stabile, e le donne hanno nomi femminili.
- **La fidanzata** dell'Atto I è una donna: «la tua promessa sposa fin dall'infanzia, ora
  discepola prediletta…».
- **La compagna del Dao** (`proponi`) è sempre una donna. A un uomo puoi giurare
  fratellanza (`giura`).
- Testi al femminile ovunque si parla della compagna: combattimento, lutto, doppia
  coltivazione, aiuto.
- **Famiglia:** madre e sorella sono donne, con nomi femminili.
- **Eredi dell'arcinemico:** «la sorella gemella» e «la compagna del Dao» ereditano il nome
  del rivale come donne.

### 7. Mete e comandi diretti (`travel.py`)
Muoversi sulla mappa passo per passo non è comodo. Ora ogni cosa importante si raggiunge con
un comando.
- **`mete`** elenca, numerato, tutto ciò che sta accadendo: reame segreto, Grande Assemblea,
  gara della tua arte, asta, invasione, elemento celeste, famiglia minacciata, casa, sede
  della setta. Per ognuno indica il luogo, la distanza e il comando per partecipare.
- **`vai <n | meta | luogo>`** ti porta direttamente lì: `vai 1`, `vai assemblea`, oppure il
  nome di un luogo qualsiasi.
  - Il viaggio costa tempo in proporzione alla distanza, e il mondo intanto continua a
    vivere.
  - Dal 2° regno voli (costa Qi, metà del tempo); dal 6° il Passo nel Vuoto è quasi
    istantaneo.
- **`iscriviti <n | meta>`** ti porta lì **e** partecipi subito: ti iscrivi all'Assemblea o
  alla gara, entri nel reame, difendi dall'invasione o la famiglia. Se all'arrivo succede
  qualcosa, si ferma e te lo lascia risolvere. `iscriviti` senza argomento resta
  l'iscrizione a una setta.
- Le **azioni suggerite** propongono da sole «Raggiungi: Grande Assemblea →
  `iscriviti assemblea`» quando un evento importante è lontano.

Nuovi test: `test_director.py` (5), `test_svolte.py` (5), `test_consolidation.py` (3),
`test_balance.py` (6), `test_romance_gender.py` (3), `test_travel.py` (3).
Suite totale: **517 passati**.

---

## Aggiornamento 24 — La dashboard nel browser

`python dashboard.py` apre il gioco nel browser, su `http://127.0.0.1:8765`. È la **stessa
partita** del terminale: ogni azione passa dallo stesso `dispatch`, e dopo ogni comando
gira lo stesso ciclo del loop testuale (alba, report, morte, capitoli, suggerimenti).

**Architettura** (`engine/web/`)
- `game.py` è il ponte col motore: turni, istantanea dello stato in JSON, pannelli, mappa,
  Dao, pilota automatico un giorno alla volta, creazione, morte e rinascita.
  - Un lucchetto rende sicuro il server multi-thread.
  - I pannelli vengono letti dentro una transazione annullata, quindi guardarli non fa
    mai passare il tempo né cambia nulla.
- `server.py` usa solo la libreria standard: nessuna dipendenza. Ascolta solo su
  127.0.0.1. Il pilota automatico arriva dal vivo con i Server-Sent Events.
- `static/` contiene una sola pagina in HTML, CSS e JavaScript semplice, senza build.

**Fase 1 — Console web**
- Barra di stato fissa: regno ed esperienza, Qi, spirito, cuore del Dao, ferite, pietre,
  fama, giorno e ora, stagione, meteo, era, età.
- Registro colorato per tipo di evento: pericoli, morte, svolte, successi.
- **Scelte degli incontri come pulsanti**, con la probabilità di riuscita e la forza
  dell'avversario.
- **Azioni suggerite come pulsanti**; i tasti 1-9 le eseguono quando la casella è vuota.
- Casella di comando sempre presente, con la cronologia (frecce su e giù).
- Creazione del personaggio e rinascita in finestre guidate: origine, destino, rivali,
  nome, frammento ereditato.

**Fase 2 — Pannelli**
- **Luogo:** uscite cliccabili e presenti con «parla» e «attacca».
- **Mete:** tutto ciò che accade, con «Vai» e «Partecipa».
- **Personaggio:** barre dei Dao con la soglia successiva, poi stato, potenza, corpo,
  radici, sangue.
- **Tesori:** con «Cura tutti i tesori».
- **Storia:** trama, obiettivi, arcinemico, retaggio, svolte, legami.
- **Mondo:** era, regni, razze, classifiche, setta, ritmo.

**Fase 3 — Mappa e pilota dal vivo**
- **Mappa** dei luoghi intorno a te: icone per tipo, i luoghi visitati in evidenza, le
  mete bordate di giallo. Clic su un luogo per andarci.
- **Pilota automatico dal vivo:** il resoconto arriva giorno per giorno, con
  «Interrompi».
- Le impostazioni del pilota (bersagli, condotta, sfondamento e rischio, assorbire,
  bottino, oggetti) sono moduli, non comandi.

**Fase 4 — Rifiniture**
- Tema chiaro e scuro automatico.
- Stile sobrio e leggibile, che si adatta a schermi più stretti.
- Salvataggi e caricamenti dal pannello Aiuto.
- Tipi MIME espliciti, così funziona anche su Windows.

Nuovi test: `tests/test_dashboard.py` (5) — suite totale **523 passati**: turni, pannelli che non cambiano il mondo,
mappa, Dao, pilota, morte e rinascita, server HTTP di fine in fine. La pagina è verificata
anche in un browser vero (Chromium), senza errori in console.

---

## Aggiornamento 25 — Il prezzo della morte, storie che ritornano, duelli e 8 azioni rapide

**Il prezzo della morte** (`rebirth.py`)
- Alla morte porti con te fino a **2 frammenti** di eredità, non più uno solo.
- **Memoria del regno**: la vita dopo ricorda fin dove eri arrivato. Sotto quel regno coltivi
  ×2,5 e gli sfondamenti hanno +20%: risalire è più rapido, superarlo resta difficile.
- **Senza Ritorno** (`senza_ritorno si|no`, o la casella alla creazione): la morte è
  definitiva. Il mondo viene archiviato in `database/saves/` e ne nasce uno nuovo.
- **Reincarnati ora** (`reincarnati`, o il pulsante nella scheda *Partita*): chiudi tu questa
  vita e rinasci con i benefici di ciò che hai accumulato.
  - Il **merito** conta regno, Dao, titoli, giorni vissuti e fama.
  - Diventa pietre spirituali e **Samsara**: un moltiplicatore permanente di coltivazione,
    logaritmico e quindi infinito.
  - Puoi scegliere tutti i frammenti. Ti aspetta un epilogo apposito.
- **Ricomincia da zero** (`ricomincia`): un mondo nuovo e nessuna eredità. Il mondo vecchio
  viene archiviato, non cancellato.

**Storie che ritornano**
- **Cronaca** (`cronaca [tutte|esporta]`): la storia di questa vita e di quelle passate, con
  titoli, svolte, sfondamenti, lutti e duelli. Si può esportare in un file `.md`.
- **Echi** (`echoes.py`): ciò che hai fatto torna a cercarti. Chi hai risparmiato può
  tornare grato o rabbioso, chi hai aiutato ricambia, chi hai offeso torna a chiedere il conto.
- **Varianti delle scene**: gli incontri cambiano se ti ripeti, se sei famoso o temuto, se
  domini chi hai davanti. Ci sono scelte nuove come *Fai valere il tuo nome*.

**Dialoghi e favori** (`dialogues.py`)
- `parla` con le persone a te vicine (compagni, maestro, fidanzata, compagna del Dao) apre un
  dialogo vero. A volte ti chiedono un **favore**: `favori` per vederli, `favore <nome>` per
  esaudirne uno.
- Esaudire i favori fa crescere l'**intimità**. Da 2 in su, chi ti è caro **accorre in tuo
  aiuto** nei combattimenti difficili.

**Duelli a turni** (`duello <nome>`)
- Gli scontri importanti si giocano a turni: Colpisci, le tue tecniche (con costo e ricarica),
  Difendi, Concentrati, Fuggi.
- Il nemico a volte carica un colpo pesante e lo vedi un turno prima: difendersi al momento
  giusto lo para quasi del tutto.
- Alla fine decidi tu se **finirlo** o **risparmiarlo**, e il mondo se lo ricorda.
- L'arcinemico e i legami ostili offrono il duello direttamente tra le scelte.

**Dashboard**
- Nuove schede:
  - **Obiettivi**: primari (storia, trama, svolte, sfondamento), secondari (incarichi, favori,
    nemesi, taglie, bestie rare) e missioni (bacheca della setta, Sistema), ognuno con il suo
    pulsante.
  - **Alleati e nemici**: per ognuno la potenza, il confronto con la tua, il regno, dove si
    trova, il rapporto e i pulsanti Vai, Parla, Duello e Attacca.
- Pannelli strutturati:
  - *Tesori*, con i colori di rarità e il pulsante Usa;
  - *Storia*, con la cronaca;
  - *Mondo*, con le tabelle di classifica, regni e razze;
  - *Partita*, con i salvataggi, la nota sul salvataggio automatico ogni 5 giorni,
    *Reincarnati ora* con l'anteprima del merito e *Ricomincia da zero*.
- Duelli con le barre della vita.
- `python dashboard.py --rete` per giocare dal telefono sulla rete di casa.

**8 azioni rapide** (`suggestions.py`)
- Dopo ogni comando ci sono fino a **8** azioni numerate: tasti 1-8 nella dashboard, `1`…`8`
  nel terminale.
- In testa c'è ciò che è urgente o a tempo: prigionia, calamità, nemesi, invasioni, eventi
  da raggiungere, sfondamento, bottino, incarichi, favori da esaudire.
- Poi vengono le azioni che **accorpano** tanti comandi in uno:
  - `train` per Qi, Dao e arte insieme;
  - `tesori cura` per tutti i tesori, quando c'è qualcosa da raccogliere;
  - `mete` per gli eventi del mondo;
  - `auto 1` e `auto 7` per il pilota automatico;
  - `sleep` per Qi, Spirito e ferite;
  - le due uscite migliori.
- Il pilota automatico è sempre a portata di tasto. Con ferite gravi il riposo sale in cima.

**Manutenzione** (`maintenance.py`)
- Ogni 10 giorni il database si alleggerisce: eventi altrui vecchi, conseguenze risolte,
  tick di simulazione, report già mostrati e voci vecchie. La tua storia resta intatta.
- Un nuovo test di regressione del bilanciamento controlla 30 giorni di gioco con valori
  limitati.

Nuovi test: `test_duel.py` (3), `test_stories.py` (5) e aggiunte in `test_dashboard.py`,
`test_balance.py` e `test_story_systems.py`. Suite totale: **538 passati**.

---

## Aggiornamento 26 — I menu: setta, arti, coltivazione, eventi, regni, famiglia

**Menu a sezioni** (`menus.py`)
- Ogni parte del gioco ha il suo menu, diviso in sezioni. In ogni sezione trovi qualche riga di
  stato, a volte una barra di avanzamento, e le azioni già pronte.
- Nel terminale le azioni sono numerate e basta scrivere il numero. Nella dashboard sono
  pulsanti; quelle non ancora possibili sono spente e dicono perché.
- `menu` mostra l'indice di tutti i menu.
- Nella dashboard la colonna di sinistra ha i pulsanti *Setta, Arti, Coltivazione, Eventi,
  Regni, Famiglia*: aprono il menu nel pannello di destra. Lo stesso succede se scrivi il nome
  del menu nella casella dei comandi.

**La setta e l'ascesa** (`setta`, `sect_menu.py`)
- **Ascesa nella storia.** Ogni setta ha una soglia, e la superi in uno di tre modi:
  - sei troppo forte per lei;
  - hai guadagnato abbastanza merito da quando ci sei entrato;
  - vinci il torneo mensile.
- A quel punto arrivano gli emissari di tre sette superiori, con una scena scritta che cambia
  in base a come ci sei arrivato. Puoi:
  - **accettare** una delle tre;
  - **rimandare**: le offerte restano nel menu;
  - **restare per lealtà**: ricevi merito, pietre, il favore degli anziani e un rango in più.
    La soglia si alza e le offerte successive vengono da sette ancora più grandi.
- Le soglie si misurano sul livello effettivo della setta: chi entra da mortale in una grande
  setta parte comunque dal basso.
- Il menu della setta raccoglie:
  - l'**ascesa**, con la barra di avanzamento e le offerte aperte;
  - **classe, tornei e sfide**: la prossima sfida, i compagni, la sfida di rango;
  - le **tecniche segrete** e il **metodo** della setta;
  - il **tesoro del merito**: pillole del progresso, pietre, materiali, nuclei, essenze del Dao,
    la stanza di coltivazione (×1,5 nella sede per 3 giorni);
  - il **rango**: promozione col merito, in alternativa alla sfida;
  - lo **stipendio** del mese;
  - la **bacheca delle missioni** e gli **anziani** da servire;
  - **guerre, razzie, invasioni** e la zona di caccia, con i comandi per raggiungerle.
- Se non sei in una setta, il menu mostra le sette vicine con *Vai* e il test d'ingresso.
  La setta che hai fondato tu resta in `setta mia`.

**Le arti: una, alcune, tutte o nessuna** (`arti`)
- Ora puoi praticare più arti insieme. `train` le fa crescere tutte: ognuna un po' più piano,
  se sono tante. Il pilota automatico crea con le ricette di tutte quelle in pratica.
- `arti nessuna` mette le arti a riposo e l'allenamento si concentra su Qi e Dao.
- Cambiare l'arte principale non fa più perdere esperienza: le altre restano tue.
- `craft <arte> <n>` crea con un'arte qualsiasi e `ricette <arte>` ne mostra le ricette.
- I vecchi salvataggi con una sola arte vengono convertiti da soli.

**Gli altri menu**
- **Coltivazione**: allenamento e ritiri, sfondamento e tribolazioni, i tuoi Dao, il metodo,
  le radici e la grotta-dimora con i potenziamenti.
- **Eventi**: tutto ciò a cui puoi partecipare adesso, con *Partecipa* o *Raggiungilo*. Ci sono
  anche gli scontri dell'Assemblea, le offerte all'asta, il reame segreto, la calamità e la
  guerra tra sette, più il calendario di ciò che verrà.
- **Regni**: la corte in cui sei, con tributi, principi da sostenere, guerra e trono; tutti i
  regni con *Vai*; le razze antiche, con doni e campioni da sfidare.
- **Famiglia**: il clan (visita, difesa, doni), i legami (parla, favori, duello con rivali e
  nemesi) e i discepoli.
- Le 8 azioni rapide segnalano quando gli emissari ti aspettano e quando puoi salire di rango o
  ritirare lo stipendio.
- `vai #<luogo>` porta in un luogo preciso: lo usano i menu.

Nuovi test: `test_menus.py` (8). Suite totale: **546 passati**.

---

## Aggiornamento 27 — Il menu della dimora e «potenzia al massimo»

- **Menu della dimora** (`dimora`, e il pulsante *⌂ Dimora* nella dashboard). Contiene:
  - la produzione da raccogliere;
  - per ogni ala il livello, cosa fa ora e cosa farà al livello successivo, con i pulsanti
    *+1 livello* e *Al massimo possibile*.
- **Potenzia al massimo** (`dimora potenzia max`): spende le pietre che hai per portare la
  dimora al livello più alto che puoi permetterti adesso, in una sola sessione di lavoro.
  - Ogni volta sceglie il potenziamento più economico, così le ali crescono in equilibrio.
  - Prima di confermare, il menu mostra quanti livelli farebbe e quanto costerebbe.
  - `dimora potenzia <ala> max` fa lo stesso su un'ala sola.
- Quando sei a casa e puoi permetterti un potenziamento, compare tra le 8 azioni rapide.
- Nel menu Coltivazione la dimora ha un collegamento al suo menu e il potenziamento massimo.

Nuovi test in `test_menus.py`. Suite totale: **547 passati**.

---

## Aggiornamento 28 — Le essenze si assorbono tutte insieme

- `use essenze` (o `use essenza`) assorbe con un solo comando **tutte** le essenze dello zaino,
  sia quelle di sangue sia quelle del Dao. Lo stesso vale per `use pillole`, `use nuclei` e
  `use manuali`.
- `use tutte <oggetto>` usa tutte le copie di un oggetto. Se usi per nome un'essenza di cui
  hai più copie, le assorbe tutte.
- Ora `use` riconosce anche gli oggetti con il nome di più parole (prima venivano scambiati
  per una mossa).
- Dashboard: nella scheda Tesori le essenze hanno il pulsante *Assorbi tutte*, gli altri oggetti
  con più copie hanno *Tutte*, e in fondo c'è *Assorbi tutte le essenze*.
- Anche l'azione rapida assorbe tutte le essenze in una volta.

Suite totale: **548 passati**.

---

## Correzione — Ascesa alle sette altissime

- Accettare l'offerta di una setta oltre l'ottavo livello dava l'errore
  `ValueError: empty range in randrange`. La zona di caccia aveva ancora un tetto all'ottavo
  regno e chiedeva mostri "tra il livello 11 e il livello 8".
  - Ora le zone di caccia non hanno più un tetto: i mostri crescono con la setta.
  - Se serve un regno oltre quelli esistenti, viene creato.
  - L'estrazione dei livelli non può più ricevere un intervallo vuoto.
- Nuovo test di regressione: sei ascese di fila fino a una setta oltre il livello 10.

---

## Aggiornamento 29 — Il tetto dei mondi, rancori e debiti, nomi nuovi

**Ogni mondo ha il suo tetto** (`ascension.py`)
- Il **Mondo Mortale** regge nove regni: nessuno, lì, può andare oltre il nono. Né tu, né gli
  NPC, né le bestie, né i maestri delle sette: anche chi nasce e chi cresce si ferma al tetto.
- Alla **Grande Perfezione** del nono regno lo sfondamento non c'è più: resta l'**ascensione**
  (`ascendi_mondo`, che prima ti dice cosa lascerai e poi chiede `conferma`).
  - Attraversando la Porta diventi subito il primo regno del mondo superiore: *Immortale di Giada*.
  - Non porti nulla del mondo inferiore: oggetti, pillole e materiali si dissolvono, le pietre
    valgono un decimo. Restano tuoi arma, tecniche, Dao, bestia e legami.
  - Anche salire da una porta già aperta (`up`) lascia indietro gli oggetti, con un avviso prima.
- Ogni mondo superiore regge tre regni in più (12, 15, 18…).
- Anche le sette hanno un tetto: in ogni mondo si sale fino alla setta più grande che quel mondo
  regga, poi l'ascesa successiva è quella al mondo superiore.
- Il pilota automatico non tenta più sfondamenti impossibili e si ferma una volta per dirti che
  puoi ascendere.

**Nomi nuovi** — i livelli restano gli stessi, cambiano solo i nomi (anche nei salvataggi)
- **Regni del Mondo Mortale**: Condensazione del Qi, Fondazione, Nucleo d'Oro, Anima Nascente,
  Trasformazione dello Spirito, Raffinamento del Vuoto, Unione del Corpo, Grande Veicolo,
  Superamento della Tribolazione.
- **Oltre** (tre per mondo):
  - Mondo degli Immortali: Immortale di Giada, Immortale Celeste, Immortale Mistico;
  - Cielo d'Oro: Immortale d'Oro, dell'Unità Suprema, della Grande Rete;
  - Mondo dei Santi: Mezzo Santo, Santo, Santo Supremo;
  - Reame del Dao: Re del Dao, Imperatore del Dao, Antenato del Dao;
  - Mare del Caos: Caos Primordiale, Origine Senza Origine, Oltre il Principio;
  - poi i nomi ricominciano con un numerale, senza fine.
- **Fasi di ogni regno**: strati 1-3 *iniziale*, 4-6 *intermedia*, 7-9 *avanzata*, 10 *picco*.
  Con l'esperienza piena, *Grande Perfezione*.
- **Maestria nei Dao**: oltre a *legislatore* ci sono *sovrano*, *origine* e *antenato*. Ogni Dao
  ha le sue tecniche di Sovranità, di Origine e di Antenato.

**Rancori e debiti** (`faide`, `feuds.py`) — ogni vittima lascia qualcuno
- Chi uccidi può avere chi giura vendetta: padre o madre (più forti), fratelli, figli (più
  deboli, ma tornano anni dopo e sono i più temibili), il maestro, un fratello giurato, un
  allievo. Se era un anziano o un patriarca, anche la sua setta.
  - Quanti e quanto accaniti dipende da chi era la vittima. Un ricercato non lascia quasi rancori
    (la sua famiglia se ne vergogna); chi muore in guerra lascia rancori più tiepidi.
  - Se agivi mascherato e senza testimoni, non sanno chi cercare. Ci mettono molto di più, e a
    volte non lo scoprono mai.
- Il vendicatore si allena, poi ti trova, con una scena scritta per ogni legame. Puoi:
  - **duellare**: se lo uccidi, la faida passa alla generazione successiva, fino alla terza
    (titolo: *Colui che Spezzò una Stirpe*);
  - **risarcire** la famiglia con le pietre: non funziona se il rancore è troppo profondo;
  - **raccontare la verità**: funziona soprattutto se la vittima era un ricercato;
  - **andartene**: il rancore cresce.
  Se lo sconfiggi e lo risparmi, a volte depone la spada per sempre.
- **Risparmiare per scelta** (duello o `spare`) crea un **debito di vita**. Chi ha onore lo
  ripaga: con un dono (pietre e una pillola), con un segreto, oppure diventa un alleato che
  accorre al tuo fianco nelle battaglie difficili. La sua setta ti guarda con favore.
- Il **Libro dei Rancori e dei Debiti** (`faide`, pulsante *🩸 Faide* nella dashboard) mostra
  ogni faida (rancore, generazione, dove si trova, chi è più forte) con duello, risarcimento e
  verità a portata di tasto. Mostra anche i debiti di vita e i conti chiusi.

**Difetti corretti e ritocchi**
- **Fascia alta**: invasioni, guerre tra sette, cacciatori, ricercati, zone e bestie non sono più
  fermi all'ottavo regno, e i regni mancanti si creano quando servono. La simulazione è arrivata
  al regno 10 senza errori.
- **Avvisi raccolti**: "5 giovani geni ti hanno superato: …" in una riga sola. Chi va e viene
  diventa "Arrivano / Se ne vanno / Di passaggio" invece di una riga per ogni passo.
- **Duelli più rapidi**: 5-8 scambi tra pari, 10-12 con arcinemico, nemesi o rivali.
- **Scheda del luogo** nella dashboard: prima nemici e legami (bordo rosso o verde), poi i
  ricercati e le figure di rango; il resto in "+ altri".
- I cacciatori della vita precedente non inseguono più chi è appena rinato.

Nuovi test: `test_worlds.py` (3), `test_feuds.py` (4). Suite totale: **556 passati**.

---

## Aggiornamento 30 — Eventi più ricchi, grafici, la rete, il Libro e il pilota che sbriga le faccende

**Eventi più lunghi e ricchi**
- **Saghe a più atti** (`encounter_sagas.py`): sei storie in 2-3 scene, ognuna con le sue scelte.
  - *La sposa rapita*: la segui fino all'accampamento dei rapitori, poi la liberi, tratti o duelli.
  - *La Fossa delle Mille Ossa*: un torneo clandestino, con il campione da battere o da
    risparmiare.
  - *La tomba del Patriarca Senza Nome*: rune, un guardiano di giada, e tre eredità tra cui
    scegliere.
  - *Il Giovane Signore*: un affronto in locanda, e poi l'anziano del suo clan che viene a
    decidere se odiarti o rispettarti.
  - *Il villaggio che non si sveglia*: un coltivatore demoniaco che beve la vita dei dormienti.
  - *La carovana delle erbe*: una scorta e un'imboscata.
- Nelle scene uccidere o risparmiare ha le stesse conseguenze dei combattimenti: vendicatori
  oppure debiti di vita.
- **Premi generati** (`rewards.py`): pillole, essenze del Dao, manuali, nuclei e tesori antichi
  con nomi propri. Scalano col piazzamento, con il tuo regno e con l'importanza dell'evento.
- **Torneo mensile della setta**: un'apertura raccontata, poi pietre, merito e premi dal tesoro
  della setta per i primi tre. La prima vittoria dà il titolo *Campione di …*.
- **Grande Assemblea**: ogni incontro presenta l'avversario (regno e forza a confronto) e la folla,
  e a ogni turno vinto ricevi un premio. Il campione riceve il Sigillo dell'Alleanza: un tesoro e
  un manuale.

**Grafica e simboli** (`viz.js`) — tutto in SVG, senza immagini da internet
- **Legenda** dei simboli e dei colori di rarità (scheda *Partita*). Ogni simbolo ha sempre lo
  stesso significato: ⚔ combattimento, ☯ coltivazione, ☸ Dao, ♥ legami, 🩸 faide, 🤝 debiti di
  vita, ⛩ setta, 👑 regni, ✦ storia, ⚠ pericolo, ✧ guadagni, 💰 pietre.
- **Registro filtrabile**: Tutto, Combattimento, Coltivazione, Legami, Setta, Mondo.
- **Grafici** (scheda *Personaggio*):
  - la coltivazione nel tempo, con gli sfondamenti segnati;
  - la potenza di combattimento, in scala logaritmica;
  - la comprensione dei Dao;
  - il radar del tuo profilo (attacco, difesa, vitalità, spirito, Qi, Dao).
  Ogni alba si registra un'istantanea (`history.py`).
- **La rete delle relazioni** (scheda *Alleati e nemici*): famiglia, legami, debiti di vita,
  nemici e faide intorno a te. I caduti da cui nasce ogni faida sono collegati al loro
  vendicatore con un tratteggio di sangue. Il cerchio pieno vuol dire qui, quello tenue lontano;
  la grandezza dice la forza. Cliccando un nome compaiono Vai, Parla o Duello.
  Vendicatori e debitori compaiono anche tra le schede di alleati e nemici.
- **Il Libro** (nuova scheda): una pagina per ogni tesoro ottenuto, bestia (la tua, quelle rare,
  quelle affrontate), sangue, reliquia (gli elementi celesti), nemico principale e maestro, con
  tutti i dati. Ogni pagina ha un **sigillo generato** dal nome (forma, carattere cinese e
  colore della rarità).
  - Cartella **`immagini/`**: un'immagine con lo stesso nome sostituisce il sigillo.
    Istruzioni in `immagini/LEGGIMI.txt`.

**Il pilota automatico**
- Al termine compare una **scheda di riepilogo**: coltivazione prima e dopo, potenza (×), Dao,
  pietre, fama, karma, vite tolte, nuove faide e debiti, oggetti, titoli.
- **Faccende** (attive di default): ritira lo stipendio, consegna le missioni di setta,
  raccoglie la produzione della dimora.
- Si possono attivare anche:
  - **Potenzia la dimora** al massimo quando è a casa;
  - **Setta**: si iscrive e accetta l'ascesa più alta.
  Sono tre caselle in *Impostazioni*, oppure `auto imposta routine|potenzia|setta si/no`.

**Ritocchi**
- Le faide aperte sono al massimo 8 insieme.
- I vendicatori hanno sempre un nome unico.
- Il rancore ha una barra rossa.

Nuovi test: `test_sagas.py` (2), nuove verifiche in `test_dashboard.py`. Suite totale: **559 passati**.

---

## Aggiornamento 31 — Duelli tattici e riordino del codice

**Lo stile dell'avversario.** Ogni duellante ha uno stile, letto dai suoi tratti:
- **Impetuoso**: carica spesso e colpisce forte, ma si scopre.
- **Prudente**: si difende e incassa meno.
- **Subdolo**: finta. Dove sembra caricare, a volte non c'è nulla: chi si difende per niente perde il tempo.
- **Equilibrato**: nessun eccesso.

Lo stile si annuncia all'inizio del duello e resta visibile nel pannello della dashboard.

**Vantaggio elementale.** Si confronta il Dao più profondo dei due:
- **ciclo dei cinque elementi**: metallo > legno > terra > acqua > fuoco > metallo;
- **luce e oscurità**: ciascuna vince sull'altra;
- **fulmine**: vince sull'acqua.

Chi ha il vantaggio infligge **+25%** di danni, chi è in svantaggio **−15%**. Il duello lo dice all'inizio («Il tuo fuoco divora il suo metallo…»).

**Pillole in duello.** Sotto il 70% di vita compare la scelta «Ingoi …»: una pillola qualsiasi cura il 25%, una *Curativa* il 50%. Costa il turno.

**Riordino del codice.** I comandi di setta del terminale sono stati spostati da `loop.py` (2950 → 2530 righe) in `engine/cli/cmd_sect.py`. Comprendono:
- sette, iscrizione, inviti, tecniche e sfide di rango;
- razzie, invasioni, guerre e ritorno alla sede.

`loop.py` li reimporta, quindi nulla cambia per chi li usa.

Nuovi test in `test_duel.py` (2). Suite totale: **561 passati**.

---

## Aggiornamento 32 — Lo spirito, il Sigillo dell'Anima, le salme e le sette vassalle

**Tempra dello Spirito (炼神).** È una terza via di coltivazione, accanto al Qi e al Dao.
- Si allena con `tempra`, una seduta dedicata. Anche `train` la allena, con una quota minore.
- I gradi non hanno fine: Anima Mortale, Scintilla, Fiamma, Lago, Mare della Coscienza, Senso Divino Compiuto, Anima di Giada, Anima d'Oro Immortale, Anima Sovrana, Anima Eterna, e oltre l'Anima del N° Cielo.
- Ogni grado fa crescere:
  - il **punteggio di spirito**;
  - la riserva di Spirito per le tecniche Dao;
  - il senso divino.
- Esistono anche gli *incensi dell'anima*, tra i premi.

**Sigillo dell'Anima (魂印)** — `sigilla <nome>`.
- Si usa su chi hai sconfitto senza ucciderlo, entro un giorno. Funziona anche alla fine di un duello vinto, con la scelta «gli marchi l'anima».
- Va bene su persone, bestie e spiriti.
- Regola: il tuo spirito deve essere più forte del suo. Senza combattere serve un'anima almeno 2,5 volte più forte.
- La probabilità cresce con il distacco. Scende per patriarchi, gente d'onore e orgogliosi; sale per bestie e spiriti.
- Se fallisci:
  - l'anima ti respinge;
  - i più fieri possono bruciare la propria anima pur di non servirti;
  - altri ti giurano odio.
- Il servo ti consegna **tutti i suoi beni** e riceve un compito:
  - **scorta**: ti segue e combatte con te;
  - **lavoro**: porta pietre;
  - **guardia**: veglia sulla dimora;
  - **reggente**: un patriarca governa la sua setta per te.
- Il sigillo si **incrina** se l'anima del servo cresce fino a sfidare la tua. Si può rinsaldare; altrimenti il servo si ribella e diventa una nemesi.
- La famiglia può giurare di spezzare il sigillo. È una faida: nella scena puoi liberarlo davanti ai suoi occhi per chiuderla.
- Liberare un servo può lasciarti un debito di vita, oppure un nemico.

**Sette vassalle.** Marchiare un patriarca rende la sua setta tua vassalla. Una vassalla:
- apre il suo tesoro (pietre e tesori, una volta sola);
- ti versa un **tributo** ogni giorno (`dominio riscuoti`, o il pilota automatico);
- ti insegna le sue **tecniche segrete**, pagate in pietre;
- **combatte per te**:
  - rinforzi nelle guerre tra sette e nelle invasioni;
  - una scelta in più nelle guerre dei regni;
  - assalti agli ordini (`dominio attacca <setta>`, ogni 3 giorni).

Una setta piegata fino in fondo si arrende e diventa vassalla anche lei, ma con poca lealtà. Il vassallaggio finisce se il patriarca muore o se si sceglie un nuovo patriarca senza il tuo sigillo.

**Arte del Ritorno della Salma (炼尸)** — `rianima <nome>`.
- Si impara dal *Canone del Ritorno della Salma*, che si trova:
  - nelle eredità demoniache;
  - di rado, tra i premi più alti;
  - negli archivi delle sette vassalle demoniache.
- Riporta in piedi un caduto morto da non più di due giorni, come servo senza volontà: non si ribella, non cresce, combatte.
- È un'arte proibita: costa karma e infamia davanti ai testimoni, e la famiglia giura di dare pace alla salma.
- Un patriarca rianimato entro un giorno e senza testimoni torna sul **trono come burattino**, finché gli anziani non se ne accorgono.

**Dashboard.**
- Nuovo menu **⛓ Dominio**.
- Nella rete delle relazioni compaiono i servi e le sette vassalle.
- La legenda ha nuovi simboli.
- Il grado dell'anima compare nella barra dello Spirito.

**Altre modifiche.**
- Non puoi più attaccare per sbaglio un tuo servo: l'attacco cerca un altro bersaglio con lo stesso nome.
- Ascendendo, servi e vassalle restano nel mondo inferiore. Rinascendo, tornano liberi.
- Corretto «giura» al plurale: quando sono in più, ora giurano.

Nuovi file: `engine/systems/soul_temper.py`, `engine/systems/dominion.py`. Nuovi test: `test_dominion.py` (7). Suite totale: **568 passati**.

---

## Aggiornamento 33 — I regni delle razze: campioni, sangue d'alto lignaggio, reliquie e il trono

Le cinque razze antiche (Draghi, Demoni Celesti, Spiriti dei Boschi, Giganti, Popolo delle Maree) ora hanno un regno vero e proprio. Si apre con `razze` o con il pulsante **🐉 Razze**.

**Campioni.** Nelle terre di ogni razza veglia un campione. Quando lo batti, ne sorge uno di rango più alto:
- **Draghi:** Guardiano della Rupe, Campione delle Scaglie, Generale del Tuono, Principe dei Draghi, **Re Drago**.
- **Demoni Celesti:** Sentinella dell'Abisso, Campione delle Fiamme Nere, Generale Demone, Principe Demone, **Imperatore Demone**.
- **Spiriti dei Boschi:** fino al **Custode dell'Albero Madre**.
- **Giganti:** fino al **Re dei Giganti**.
- **Popolo delle Maree:** fino alla **Regina delle Maree**.
- Oltre il sovrano si risvegliano gli **Antenati**, senza fine.

Lo sfidi con `razza <razza> sfida`, in duello a turni. Quando l'hai battuto, cosa fai di lui conta:
- **Uccidere**: lascia **sangue d'alto lignaggio** (Drago Celeste, Demone Celeste, Gigante Antico, Leviatano). Gli Spiriti lasciano un'**essenza d'anima**, che tempra lo spirito e risveglia la linfa silvana. Spesso cade anche una **reliquia**. I Demoni approvano; le altre razze se lo ricordano.
- **Risparmiare**: il campione si inchina e ti dona metà del suo sangue, con molto onore.
- **Sigillare**: diventa tuo servo e la razza si offende. Marchiare il sovrano ti dà il trono con il terrore.

Le creature potenti uccise nelle terre delle razze lasciano almeno una **traccia** di sangue o di spirito.

**Nuovi lignaggi:** Demone, Spirito Silvano, Gigante e Leviatano. Ognuno ha le sue cinque manifestazioni e un dono in battaglia: terrore, rigenerazione, scudo, gelo.

**Reliquie dei regni** (Scaglia del Re Drago, Corona d'Ossidiana, Seme dell'Albero Madre, Martello del Primo Gigante, Perla della Regina delle Maree…).
- Dove si trovano:
  - sui campioni;
  - esplorando le loro terre;
  - raramente tra i premi più alti.
- Cosa puoi farne:
  - **assorbirle** con `use`, per un balzo enorme del sangue o dell'anima;
  - **offrirle** con `razza <razza> offri`, per onore e per salire di grado.

**La scala** (`razza <razza> ascendi`, una cerimonia per ogni grado):

| Grado | Requisiti |
|---|---|
| Discepolo | rapporto ≥10, e sangue Risvegliato o onore 50 |
| Campione | 2° campione battuto, e sangue Concentrato o onore 200 |
| Anziano | 3° campione battuto, sangue Puro, 1 reliquia offerta |
| Principe | 4° campione battuto, sangue Ancestrale, 2 reliquie offerte |
| **Sovrano** (via della forza) | il sovrano battuto, sangue Ancestrale, 2 reliquie offerte |
| **Eletto** (via della pace) | sangue Sacro, 3 reliquie offerte, rapporto ≥80 |

Il **sangue** di cui parla la tabella è il grado del tuo lignaggio affine a quella razza.

Cosa dà ogni grado:
- una tecnica della razza (Ruggito del Drago, Fiamma Nera dell'Abisso…);
- un dono di sangue;
- un titolo.

Benefici dai gradi più alti:
- dall'**Anziano**: doni di sangue periodici;
- dal **Principe**: i loro guerrieri accorrono negli scontri difficili;
- da **Sovrano/Eletto**: tributo quotidiano, e la razza marcia nelle tue guerre (rinforzi nelle guerre di setta, nelle invasioni e nelle guerre dei regni).

Il vecchio `ambasciata <razza> prova` ora porta al duello con il campione.

Nuovo file: `engine/systems/race_realms.py`. Nuovi test: `test_race_realms.py` (5). Suite totale: **573 passati**.

---

## Aggiornamento 34 — La fucina delle tecniche

Un solo pannello per tutte le tecniche: si apre con `tecniche` o con il pulsante **⚒ Tecniche**. Fondere due tecniche in una nuova richiede un clic.

**Il pannello mostra:**
- **tutte le tue tecniche** con i loro effetti: moltiplicatore, perforazione, colpi in più, letalità, difesa e costo in Qi o spirito. Ci sono la mossa dell'arma, le tecniche segrete di sette, razze e manuali, le tecniche dei Dao, i colpi speciali e le tecniche create da te. Ognuna mostra anche i Dao da cui nasce;
- **le fusioni proposte**: le 6 combinazioni migliori, anche a tre tecniche, con il nome della tecnica che nascerà, la potenza prevista e la probabilità di riuscita. Un pulsante per ciascuna;
- **le tecniche create**, con una barra del livello e i pulsanti *Allenala* e *Dimenticala*.

**Come si fonde.** Conta il legame tra i Dao delle tecniche:
- **Risonanza** (stesso Dao): più potenza.
- **Generazione** (Legno→Fuoco→Terra→Metallo→Acqua→Legno): più potenza e più riuscita.
- **Intento** (arma + elemento).
- **Conflitto** (Fuoco contro Acqua, Luce contro Ombra): molto più difficile, ma se riesce nasce un'**Armonia degli Opposti**.

La riuscita cresce con la tempra dello spirito e con la comprensione dei Dao coinvolti. Fallire costa spirito e a volte una ferita, ma lascia un'**intuizione**: ogni tentativo fallito alza la riuscita del successivo.

**Le tecniche create:**
- combattono subito: si scelgono da sole in combattimento e compaiono nei duelli;
- **crescono** usandole o allenandole, con livelli senza tetto;
- si possono **rinominare**;
- si possono **fondere di nuovo** (generazioni senza fine). Le tecniche create usate come ingredienti confluiscono nella nuova, e ogni generazione aggiunge un po' meno potenza.

I posti per le tecniche create crescono con la tempra dello spirito e con il regno.

Comandi: `tecniche`, `tecniche fondi <n> <m> [<k>]`, `tecniche fondi migliore`, `tecniche allena <n>`, `tecniche rinomina <n> <nome>`, `tecniche dimentica <n>`. Il vecchio elenco delle tecniche della setta resta con `techniques`.

Nuovo file: `engine/systems/technique_forge.py`. Nuovi test: `test_technique_forge.py` (4). Suite totale: **577 passati**.

---

## Aggiornamento 35 — Tecniche: solo la più forte di ogni categoria (il pannello non si blocca più)

**Il problema.** Con un personaggio avanzato le tecniche apprese erano diventate più di 500. Erano soprattutto manuali delle eredità con lo stesso nome: «Arte Suprema della Spada» c'era 210 volte. Ognuna diventava una mossa, e per proporre le fusioni la fucina provava milioni di combinazioni. Il pannello non si apriva e teneva bloccato il gioco.

**Le soluzioni.**
- **I doppioni con lo stesso nome sono una tecnica sola.** Nel pannello compare per esempio «Arte Suprema della Spada (×210)». La potenza complessiva del personaggio resta identica: nessun salvataggio perde forza.
- **Di ogni categoria si carica solo la più forte.** La categoria è il Dao della tecnica, oppure la sua combinazione di 2, 3, 4 o più Dao. Le tecniche superate restano tue ma non si caricano più, né nel pannello né in combattimento. Il pannello dice quante sono. Le tecniche create nella fucina restano tutte.
- **Come mossa, una tecnica molto padroneggiata cresce in modo graduale.** Il moltiplicatore cresce piano oltre una certa soglia, invece di sommarsi all'infinito.
- **La fucina è più veloce:**
  - legge i dati una volta sola;
  - prova le coppie tra le 24 tecniche più forti e le terne tra le 10 più forti;
  - nell'elenco mostra le 25 più forti (`tecniche tutte` per vederle tutte).
- **Le tecniche delle eredità senza setta** prendono il Dao dal nome («…della Spada» → spada), così entrano nelle categorie e nelle fusioni.

Con il salvataggio di prova il pannello passa da bloccato a 0,01 secondi: 42 tecniche attive su 560. Anche i combattimenti sono più veloci, perché scelgono tra molte meno mosse.

Nuovo test in `test_technique_forge.py`. Suite totale: **578 passati**.

---

## Aggiornamento 36 — Il menu del sangue

Si apre con il pulsante **🩸 Sangue** o con `sangue`. Tutti i lignaggi si gestiscono in un posto solo:
- **le essenze nello zaino**: «Assorbi tutte le essenze» con un clic. Il menu conta anche le reliquie e avvisa dei **conflitti** tra lignaggi con elementi opposti, che rischiano il sangue in rivolta;
- **la trasformazione**: un pulsante per ogni lignaggio Sacro («Diventa Drago…»), con l'attesa del riposo del sangue;
- **le fusioni proposte**: prima quelle che risolvono un conflitto, poi i tre lignaggi più forti, poi le coppie migliori. Per ognuna mostra in anteprima il nome del lignaggio che nascerà, il grado e la concentrazione;
- **ogni lignaggio** (i 12 più forti):
  - una barra verso il grado successivo;
  - elementi, dono, manifestazioni, tecnica innata e trasformazione;
  - la **razza affine** (Draghi, Demoni, Spiriti, Giganti, Maree), con il collegamento al suo regno.
- **raffinazione** (`sangue raffina <n> in <m>`, o il pulsante «Versalo nel #1»): un lignaggio debole si scioglie in uno forte. Il forte ne assorbe il 70%, o il 50% se i due non hanno famiglia o elemento in comune. Serve a togliere doppioni e conflitti senza perdere tutto.

L'elenco testuale di prima resta con `sangue info`, anche nel pannello Personaggio.

Nuovo file: `engine/systems/blood_menu.py`. Nuovo test. Suite totale: **579 passati**.

---

## Aggiornamento 37 — La rarità del sangue: il più pregiato domina

**Rarità dei lignaggi.** Ogni lignaggio ha una rarità, che compare nel menu del sangue:

| Rarità | Lignaggi |
|---|---|
| · selvaggio | sangue di bestia senza famiglia |
| ★ comune | Cinghiale, Lupo, Orso, Aquila, Serpente |
| ★★ raro | Tigre, Peng, Tartaruga |
| ★★★ leggendario | Drago, Fenice, Qilin, e i sangui delle razze: Demone, Spirito Silvano, Gigante, Leviatano |
| ✦✦✦✦ divino | due o più famiglie leggendarie fuse insieme |

**Il sangue più raro è più forte.** In battaglia ogni lignaggio pesa secondo la sua rarità: ×0,8 selvaggio, ×0,85 comune, ×1 raro, ×1,25 leggendario, ×1,5 divino.

**Nelle fusioni domina il sangue più pregiato:**
- le famiglie più rare diventano la **forma principale**: danno il nome, le manifestazioni e la trasformazione;
- le altre restano come **tratti minori**: compaiono nel menu, mantengono metà del loro dono e contano per le razze affini;
- se ci sono più famiglie alla pari al livello più alto, il nome le **combina**, ma al massimo due («Drago-Fenice»; con tre o più: «Drago-Fenice dai 3 Sangui»);
- nel nome entrano al massimo **due elementi**: niente più «di Carne Ferrea e Terra e Metallo»;
- se il lignaggio che nasce ha lo stesso nome di uno che hai già, i due confluiscono in uno solo.

Esempio: Cinghiale + Drago + Lupo → **Sangue di Drago di Tuono e Ghiaccio** (leggendario), con Cinghiale e Lupo come tratti minori.

Nuovo test. Suite totale: **580 passati**.

---

## Aggiornamento 38 — Ogni mondo è un piano a sé · il sacrificio del sangue

**Salire di mondo vale per tutto, anche per le sette.**
- Con `ascendi_mondo conferma`, o con `up` attraverso una porta già aperta, il tuo posto nella setta del mondo inferiore **resta lì**: nel nuovo mondo non sei più membro di niente e gli inviti pendenti decadono. Cerchi una setta del nuovo mondo con `sette`.
- **Ogni mondo superiore ha le sue sette**: quattro, dalla più piccola alla più alta che quel mondo regga. Ognuna ha patriarca, anziani, discepoli e zona di caccia. La mappa del nuovo mondo è più grande (12 luoghi).
- **Gli abitanti sono di quel mondo e in linea con la tua forza**:
  - tutti nascono tra il primo regno sopra il mondo inferiore e il tetto del mondo;
  - chi era rimasto indietro (anche nei salvataggi vecchi) viene riportato al livello del suo mondo;
  - ogni 5 giorni chi è morto viene rimpiazzato.
- **Sette, classifiche, guerre e assalti** riguardano solo il mondo in cui ti trovi:
  - l'elenco delle sette, il menu della setta per chi non è iscritto e la classifica delle sette;
  - le guerre tra sette (solo tra sette dello stesso mondo) e i bersagli delle vassalle;
  - le sette superiori che ti invitano nascono nel mondo in cui sei.

**Sacrificare il sangue meno nobile** (menu 🩸 Sangue):
- `sangue sacrifica <n> a <m>`, o il pulsante «Sacrificalo al #…»: un lignaggio meno raro viene divorato da uno più nobile. Il nobile ne prende il 60% e diventa più **puro**: più grande la differenza di rarità, più purezza.
- **La purezza** rafforza il lignaggio in battaglia: +10% per ogni 100% di purezza.
- `sangue sacrifica tutti`, o il pulsante in cima al menu: tutti i sangui meno nobili vanno insieme al lignaggio più nobile, che è quello più raro, anche se meno concentrato.
- Un sangue più nobile non si sacrifica a uno inferiore. Tra pari resta la raffinazione (70% o 50%).

Nuovi test in `test_worlds.py` e `test_technique_forge.py`. Suite totale: **582 passati**.

---

## Aggiornamento 39 — Rendite, spirito più generoso, raccolta e assorbimento automatici

**Rendite** (pulsante **💰 Rendite**, o `rendite`). Le cose costano sempre di più, quindi le entrate ora crescono con te:
- **Bottega delle arti**: ogni arte dal livello 3 vende ciò che produci, ogni giorno. Più alto il livello e il regno, più rende. Le arti che pratichi rendono intere, le altre a metà.
- **Setta**:
  - lo stipendio del rango (ogni 30 giorni) è molto più alto e cresce con rango e livello della setta;
  - da **Erede della Setta** in su attingi ogni giorno a una **quota del tesoro della setta**.
- **Razze**: dall'Anziano in su una rendita quotidiana; da **Sovrano o Eletto** il tesoro della razza.
- **Regni**: lo stipendio di corte e la rendita del trono crescono con il tuo regno.
- **Servi** al lavoro: rendono di più.
- Il pannello mostra quanto rende ogni fonte al giorno e al mese. «Riscuoti tutto» prende in un colpo stipendio, tesoro della tua setta e tributi delle vassalle; lo fa anche il pilota automatico. Ogni 7 giorni arriva un riepilogo della settimana.

**Lo spirito cresce di più e costa di meno:**
- la tempra rende +50%, e l'allenamento d'insieme ne dà di più (quota da 0,4 a 0,6);
- la riserva di spirito cresce di più con il regno (+20 a regno invece di +10) e con la tempra (+20 a grado invece di +12);
- costa meno:
  - sigillo dell'anima: 20% della riserva (prima 30%);
  - rinsaldare un sigillo: 12% (prima 20%);
  - rianimare una salma: 25% (prima 40%);
  - fondere tecniche: 20% (prima 35%);
  - allenare una tecnica creata: 10% (prima 20%).

**Meno tasti: raccolta e assorbimento automatici** (accesi di base):
- **raccolta automatica**: quando abbatti qualcuno, la sua eredità finisce subito nello zaino, senza `loot`;
- **assorbimento automatico**: essenze di sangue e del Dao, nuclei, manuali e incensi dell'anima si usano appena li ottieni, anche dopo aver risparmiato un campione, e all'alba per ciò che arriva da altre vie. Le pillole restano tue, da usare quando vuoi;
- il riepilogo è di una riga («🩸 Assorbi 2 essenze.»), più i passaggi di grado e le cose nuove imparate;
- `raccogli`, o il pulsante «✋ Raccogli tutto», raccoglie e assorbe tutto in un colpo;
- `autoraccolta on|off` e `autoassorbi on|off` accendono e spengono le due funzioni (pulsanti anche nello zaino).

Nuovi file: `engine/systems/income.py`, `engine/systems/auto_collect.py`. Nuovi test. Suite totale: **584 passati**.

---

## Aggiornamento 40 — La gerarchia del sangue, le bestie di ogni mondo, mai un mondo più debole

**Nove ranghi di sangue**, ispirati ai romanzi di coltivazione e al Classico dei Monti e dei Mari:

| Rango | Lignaggi | Peso in battaglia |
|---|---|---|
| · Sangue Selvatico | | ×0,8 |
| ★ Mortale | Cinghiale, Lupo, Orso, Aquila, Serpente | ×0,85 |
| ★★ Spirituale | Tigre, Volpe, Gru | ×1 |
| ★★★ Reale | Pixiu, Suanni, Peng, Tartaruga | ×1,15 |
| ★★★★ Imperiale | Qilin, Bai Ze, Volpe a Nove Code, Kun | ×1,3 |
| ✦ Divino | Drago, Fenice, i sangui delle razze | ×1,5 |
| ✦✦ dei Quattro Simboli | Drago Azzurro, Tigre Bianca, Uccello Vermiglio, Tartaruga Nera | ×1,75 |
| ✦✦✦ Ancestrale | Taotie, Qiongqi, Taowu, Kunpeng, Drago della Torcia, Xiangliu | ×2,0 |
| ✦✦✦✦ del Caos | Hundun | ×2,4 |

- Ogni nuova famiglia ha le sue cinque manifestazioni e il suo dono in battaglia.
- Due famiglie del rango più alto fuse insieme salgono di un rango, senza fine: oltre il Caos c'è il «Sangue Oltre il Caos».
- Il nome riconosce la famiglia più specifica: «Tigre Bianca» non è una tigre qualunque. I lignaggi già posseduti si aggiornano da soli; per esempio la Tartaruga Nera diventa dei Quattro Simboli.
- Il Drago Azzurro ora è uno dei Quattro Simboli. Il drago dei destini e dei doni dei Draghi diventa «Drago delle Nubi».

**Il sacrificio si divide in parti uguali:**
- `sangue sacrifica <n>`, o il pulsante su ogni lignaggio: un sangue già assorbito viene offerto ai lignaggi del rango più alto. Se sono più d'uno, il 60% si divide **in parti uguali** tra loro, con la purezza.
- `sangue sacrifica tutti`: tutti i meno nobili, tranne i sangui delle razze, che servono ai loro regni.
- **Purificazione automatica** (`sangue purifica`, spenta di base): il sangue meno nobile che assorbi va subito ai lignaggi più nobili invece di diventare un lignaggio a sé.

**Le bestie rare di ogni mondo:**
- **Mondo Mortale**: bestie spirituali, reali, imperiali, divine e i Quattro Simboli.
- **Mondo Spirituale**: dalle divine alle **Bestie Ancestrali**.
- **Dal terzo mondo**: i Quattro Simboli, le Ancestrali e il **Caos**.
- Oltre ancora, le stesse bestie «del N° Cielo».

Le bestie più alte hanno regno più alto, sono più difficili da domare, hanno talento migliore e lasciano più sangue. Le uova di bestie fino ai Quattro Simboli esistono; incrociando, un ibrido non supera mai il proprio sangue.

**Ogni mondo ha i suoi regni delle razze:**
- campioni, reliquie e gradi ripartono da zero;
- se porti già il sangue di una razza, lì sei subito **Discepolo**, non di più;
- le terre delle razze sono nel nuovo mondo, i campioni sono più forti, e le tecniche e i titoli della razza portano il nome del mondo.

**Mai un mondo più debole:**
- l'ascensione salta direttamente al primo mondo il cui tetto supera il tuo regno (succedeva con i salvataggi oltre il vecchio tetto);
- `up` non attraversa più una porta verso un mondo che non regge la tua coltivazione.

Nuovi test. Suite totale: **586 passati**.

---

## Aggiornamento 41 — Nomi brevi anche per i sangui fusi già esistenti

Ora anche i lignaggi fusi **prima** della regola «domina il più nobile» si sistemano da soli all'apertura:
- **forma principale**: solo le famiglie del rango più alto; tutte le altre diventano tratti minori;
- **nome**: al massimo due famiglie e due elementi. Per esempio «Cinghiale-Serpente-Tartaruga-Tigre-Aquila-Lupo-Orso-Drago-Demone-Leviatano-Spirito Silvano-Gigante di Carne Ferrea e Terra e …» diventa **«Drago-Demone dai 5 Sangui di Tuono e Tenebra»**;
- gli elementi del nome sono quelli della forma principale: il Drago dà il Tuono, il Demone la Tenebra, la Fenice il Fuoco… Se il lignaggio ne ha altri suoi, valgono quelli: un drago di fuoco con una fenice di ghiaccio diventa «di Fuoco e Ghiaccio»;
- **trasformazione**: il pulsante dice «Diventa Drago-Demone dai 5 Sangui», non più l'elenco di tutte le famiglie;
- **menu**: i doni sono senza doppioni e solo quelli della forma principale. Gli elementi mostrano prima quelli principali (al massimo 4, poi «+N»), e i tratti minori hanno una riga a parte.

Concentrazione, rango e potenza del lignaggio non cambiano: cambia solo il nome. Nuovo test. Suite totale: **587 passati**.

---

## Aggiornamento 42 — La dashboard si riavvia da sola quando il gioco viene aggiornato

**Il problema.** Una dashboard già aperta continuava a usare il codice vecchio finché non veniva chiusa e riaperta. Per questo, dopo un aggiornamento, si vedevano i pulsanti nuovi ma i menu dicevano «menu sconosciuto», oppure il sangue mostrava ancora i nomi lunghi.

**La soluzione.** Ogni 2 secondi la dashboard controlla se i file del gioco sono cambiati. Se sì, si riavvia da sola con il codice nuovo nella stessa finestra e sulla stessa porta, senza aprire un'altra scheda del browser. La partita è salvata, non si perde nulla. Basta ricaricare la pagina (F5) per vedere anche le novità grafiche.

`python dashboard.py --no-reload` disattiva il riavvio automatico.

**Nota:** serve chiudere e riaprire la dashboard **un'ultima volta** a mano, perché quella aperta ora non contiene ancora questa funzione.

---

## Aggiornamento 43 — Corpi leggendari: storie, doni, stadi; nascere con un corpo leggendario a caso

**Ventidue corpi, ognuno con la sua storia.** Agli undici di prima si aggiungono undici corpi presi dalle grandi storie del genere: **Corpo Santo dell'Era Desolata**, **Osso Supremo**, **Doppie Pupille**, **Embrione del Dao Innato**, **Corpo dei Nove Yang**, **Corpo Santo della Luna Grande** e **del Sole Grande**, **Corpo di Asura**, **Corpo Immortale**, **Corpo del Nirvana della Fenice** e **Anima Innata Celeste**. Ogni corpo, nuovo o vecchio, ha:
- una **leggenda** (da dove viene, chi lo ha portato prima di te, perché il Cielo lo teme);
- l'elenco chiaro dei suoi **doni**: coltivazione, Dao affini, breakthrough, cuore del Dao, durata della vita, riserva di spirito, tempra dell'anima, colpi in combattimento;
- il **prezzo** quando c'è. Il Corpo Santo dell'Era Desolata coltiva più lentamente finché è sigillato. L'Anima Innata Celeste ha un corpo fragile.

**Stadi con un nome.** Il risveglio passa per *Sigillato → Primo Risveglio → Secondo Risveglio → Piccola Perfezione → Grande Perfezione → Corpo Compiuto*. A ogni stadio i doni crescono e si guadagnano anni di vita.

**Doni nuovi:**
- **anni di vita** in più;
- **riserva di spirito** più ampia;
- **tempra dell'anima** più rapida;
- **salvataggi dalla morte**: il Corpo Immortale e la Fenice del Nirvana sopravvivono a un colpo mortale.

**Nascere con un corpo leggendario.** Quando crei il personaggio o rinasci (dalla dashboard o dal terminale) puoi «affidarti al Cielo»: nasci con un corpo leggendario estratto a caso. È facoltativo, e senza la spunta tutto resta come prima.

**Comando** `costituzione` (o `corpo_leggendario`, `fisico`): la scheda completa del tuo corpo, con storia, stadio e doni attivi.

Nuovi test. Suite totale: **590 passati**.

---

## Aggiornamento 44 — Inseguitori al tuo passo, Dao profondi e guerra con il Cielo, Spiriti del Dao, finestra di stato, dashboard nuova

**Chi ti insegue cresce con te.** Se la tua potenza è 200, chi ti dà la caccia non può averne 10 000. Ogni inseguitore ha una fascia di forza rispetto alla tua e ci torna alla nascita, ogni giorno e prima di ogni scontro:

| Inseguitore | Fascia (volte la tua forza) |
|---|---|
| Cacciatori di taglie | 0,8–1,2 |
| Campioni delle specie e Messaggeri del Cielo | 0,95–1,35 |
| Nemesi | 0,9–1,3 |
| Arcinemico | 0,85–1,25 |
| Vendicatori «alla pari» (fratelli, sorelle, figli, fratelli giurati, allievi) | 0,75–1,15 |

Se cresci, crescono anche loro. Le faide degli anziani (padre, madre, maestro, la setta) restano un'altra storia: possono essere molto più forti di te e non vengono mai indeboliti. Se però li superi di molto, si allenano per non restare indietro.

**I tre Dao profondi e la Sfida al Cielo** (menu `profondi`):
- **12 arcani**, cioè poteri che si sbloccano con la comprensione:
  - Spazio: Passo nel Vuoto, Taglio del Vuoto, Prigione Spaziale, Piccolo Mondo;
  - Tempo: Occhio del Domani, Camera del Tempo, Rallentare il Tempo, Riavvolgere;
  - Destino: Leggere il Fato, Riannodare il Filo, Benedizione del Fato, Recidere il Fato.
- **Risonanze** tra due Dao profondi a «maestro»: Dominio Spazio-Tempo, Fiume del Destino, Causalità. Con tutti e tre a «gran maestro» si attiva la **Trinità delle Leggi**.
- La **guerra con il Cielo** procede a capitoli: Presagi → Occhio del Cielo → Messaggeri → **Giudizio**. Il Giudizio offre tre risposte: sottometterti, sfidare la Volontà del Cielo o ingannarlo col Destino. Torna più alto a ogni raddoppio della sfida, senza fine.
- Ogni vittoria sulla Volontà del Cielo dà un **Sigillo della Sfida**, che aumenta la forza e porta titoli.
- I poteri passivi del Tempo crescono anche oltre l'ultima soglia.

**Spiriti del Dao** (menu `spiriti`). Ogni Dao arrivato a «maestro» prende forma: Salamandra di Fiamma, Ondina, Silfide, Drago del Tuono, Spirito della Spada, Tessitrice del Fato… In tutto sono 31 forme, più una generica per gli altri Dao.
- Gli stadi sono Scintilla → Spirito → Incarnazione → Forma del Dharma → Signore → Primordiale → Antenato, e poi continuano senza fine.
- Combattono con te. Quanti ne scendono in battaglia dipende dalla tempra dell'anima.
- Allenano il loro Dao ogni giorno; con `spiriti allena` vi allenate tutti insieme.

**Finestra di stato** (ispirata a *The Gamer*):
- livello, PV, ATT, DIF, Qi, spirito e sei attributi: FOR, VIT, AGI, INT, SAG, FRT;
- punti attributo a ogni strato e a ogni regno, con effetti logaritmici e senza tetto;
- `osserva <nome>` legge la finestra di stato degli altri.

**Missione quotidiana del Sistema** e **rango del cacciatore** (ispirati a *Solo Leveling*):
- ogni giorno tre obiettivi: Dao, caccia, tempra;
- la ricompensa è un punto attributo più le pietre; ogni 7 giorni di fila arrivano 2 punti e un titolo;
- saltarla azzera la serie;
- rango da E a S, poi SS, SSS, Livello Nazionale, Monarca.

**Dashboard rifatta:**
- **7 schede** invece di 10: Mete (con missione quotidiana, obiettivi e missioni), Eroe, Mappa, Legami, Tesori (zaino e Libro), Storia (cronaca, trama, mondo) e Partita. Ognuna ha sottoschede.
- La scheda **Eroe** contiene:
  - la finestra di stato in stile «finestra di sistema»;
  - il grafico di tutti i Dao (scala logaritmica, colori per tipo);
  - radar e barre del **talento** e delle **radici spirituali**, con le combinazioni attive;
  - gli anelli dei Dao profondi, il corpo leggendario, la tempra, il cuore del Dao, i lignaggi, gli Spiriti del Dao e i grafici di crescita.
- **Mappa nuova**: zoom con la rotella, trascinamento, pericolo a colori e chi ti dà la caccia (⚔), sedi delle sette (⛩), persone presenti e mete in corso (★). Ci sono filtri per ogni livello di informazione.
- Pulsante **⤢** per allargare il pannello di destra (e la mappa), e pulsante **◐** per il tema automatico, chiaro o scuro.
- **Ogni comando citato nel testo diventa un pulsante.** Vale per il registro, i menu, le scene e le schede, per esempio ▶ join o ▶ mask on. Se il comando ha un segnaposto (`vola <luogo>`) viene scritto nella riga di comando da completare.
- Ogni obiettivo mostra la sua azione.
- **Notifiche di sistema**: titoli, sfondamenti, spiriti, Giudizi e pericoli compaiono in finestrelle a comparsa.
- **Grafica rinnovata**: tema «giada e inchiostro» con titoli in serif, ombre e angoli morbidi, barra in alto fissa e traslucida, schede a pillola, menu raggruppati (La Via, Potere, Mondo) e tema scuro curato. Il focus è visibile da tastiera e le animazioni si spengono se il sistema chiede movimento ridotto.
- La dashboard ora funziona anche **sul telefono**.

Nuovi comandi: `profondi`, `arcano`, `cielo sottometti|sfida|inganna`, `spiriti`, `attributi`, `finestra`, `osserva`, `quotidiana`. Nuovi test. Suite totale: **598 passati**.

---

## Aggiornamento 45 — Tutto a un tocco: il luogo mostra cosa puoi fare, mercato, asta, ricette e bacheca cliccabili

La dashboard ora sfrutta la libertà che il terminale non dava: non devi ricordare i comandi, scegli a schermo.

**Cosa puoi fare qui.** Sotto il nome del luogo compaiono le tessere delle azioni possibili, solo quelle che hanno senso lì:
- sfondamento e tribolazione quando ti aspettano;
- gli eventi in corso proprio qui;
- allenamento, tempra, allenamento con gli Spiriti del Dao e la missione quotidiana;
- il mercato, la casa d'aste, la sede di una setta (con il test d'ingresso), la tua dimora (con il ritiro) e i materiali da raccogliere;
- la caccia alle creature presenti;
- chi ti dà la caccia e i ricercati presenti, da affrontare in duello;
- chi ha bisogno di te, e il sonno.

**Menu nuovi con i pulsanti:**

| Menu | Cosa ci trovi |
|---|---|
| 🏪 **Mercato** | Gli oggetti in vendita divisi per tipo: li tocchi e li compri (i grigi dicono quante pietre mancano). Se non c'è un mercato, c'è il pulsante per andare alla città più vicina. |
| ⚖ **Casa d'aste** | Ogni lotto con le offerte pronte (rilancio minimo e rilanci più alti). Se l'asta è lontana, il pulsante per andarci. |
| 📜 **Ricette** | Le ricette di tutte le arti che conosci: crea con un tocco, e ognuna dice se manca il livello o un materiale. C'è anche la barra dell'esperienza dell'arte. |
| 📋 **Bacheca** | Le missioni della setta (accetta e consegna), le tecniche segrete (impara col merito), gli inviti delle sette superiori, chi ha bisogno di te in questo luogo, gli incarichi in corso e le taglie (con il pulsante per andare dal ricercato). |

Scrivere `market`, `asta`, `recipes`, `missioni`, `inviti` nella dashboard apre direttamente il menu con i pulsanti. Ogni persona presente ha anche il pulsante **osserva**.

Corretto: comprare un oggetto visto solo nel menu del mercato a volte diceva «quel numero non è in vendita».

Nuovi test. Suite totale: **600 passati**.

---

## Aggiornamento 46 — Ogni pulsante una volta sola; allenamento e simili solo in alto a sinistra

- **Niente doppioni a schermo.** Se la stessa azione compare in più punti (menu a sinistra, tessere del luogo, pannello di destra, azioni suggerite), resta visibile solo la prima. La precedenza va ai pulsanti fissi in alto a sinistra, poi ai menu, poi alle tessere del luogo, poi al pannello e infine alle azioni suggerite. Le azioni suggerite si rinumerano, e i tasti 1-8 seguono i numeri visibili. Il testo del registro non viene toccato.
- **Allenati, Tempra, Spiriti, Dormi, Sfonda, Tribolazione, Raccogli e Cura tesori stanno solo in alto a sinistra:**
  - **Sfonda** si illumina quando sei al colmo del regno;
  - **Tribolazione** compare solo quando ti aspetta;
  - **Spiriti** compare solo se hai degli Spiriti del Dao;
  - **Raccogli** mostra quanti oggetti ci sono a terra;
  - **Dormi** si evidenzia quando ti manca il Qi.
- Le **tessere del luogo** mostrano solo ciò che è proprio di quel posto: eventi, mercato, asta, setta, dimora, materiali, caccia, chi ti insegue, ricercati, chi ha bisogno di te.
- I **punti attributo** compaiono come numero accanto al menu Attributi, non più come secondo pulsante.
- Gli eventi «qui, ora» nel pannello Mete non ripetono il pulsante della tessera.

---

## Aggiornamento 47 — La frontiera: la mappa di ogni mondo si allarga col livello; sistemi doppi accorpati

**La mappa cresce con te.** Ogni mondo comincia dal suo cuore abitato. A ogni soglia di coltivazione si apre un nuovo **anello di terre** attorno a quelle che già conosci:
- **nemici più forti**: bestie, demoni, spiriti e coltivatori del regno di quell'anello;
- **bottini più rari**: chi cade negli anelli lontani lascia oggetti di qualità più alta (+1 classe ogni due anelli);
- **più risorse**: raccogliere rende il 35% in più per ogni anello;
- **incontri misteriosi** (❖): tombe antiche, sorgenti spirituali, eremiti, rovine di sette perdute, alberi dai frutti spirituali, frammenti di reami, antichi campi di battaglia.
  - Ognuno si apre una volta sola.
  - **Esplorarli fino in fondo** rende di più ma può svegliare un guardiano. **Con prudenza** prendi solo ciò che è sicuro.
  - I premi vanno da esperienza di coltivazione, anni di vita, comprensione dei Dao e pietre fino ai punti attributo e ai Dao profondi.

Gli anelli di un mondo sono almeno 6. Nel Mondo Mortale sono 9, uno per regno; nei mondi superiori, che hanno 3 regni, uno ogni mezzo regno. Al tetto del mondo la mappa è **completa**.

**Ogni mondo ha la sua mappa.** La mappa mostra solo il mondo in cui sei. Quando ascendi, il mondo di prima scompare e ne comincia uno nuovo, piccolo, che si allarga con le stesse regole, senza fine.

**Mappa:**
- coordinate fisse, senza più luoghi sovrapposti;
- crescita ad anelli concentrici;
- gli anelli lontani sono più scuri;
- ❖ segna i misteri;
- in alto la barra della frontiera, con il regno e lo strato a cui si apre l'anello successivo.

Comandi: `frontiera`, `mistero esplora|prudente`. I luoghi nuovi hanno nomi composti senza ripetizioni (Monte Sacro del Drago, Necropoli delle Perle, Torre Proibita dell'Aurora…). I salvataggi esistenti ricevono subito gli anelli che spettano al loro livello.

**Sistemi doppi accorpati:**
- **Una sola missione del giorno.** Per il Trasmigratore, completare la Missione Quotidiana dà anche i punti del Sistema e i suoi titoli. Il negozio del Sistema resta.
- Le vecchie «Incarnazioni del Dao» (un Dao oltre 2000) diventano il **Primo Colpo dello Spirito del Dao**: è il tuo Spirito a colpire per primo.
- Il menu **Dominio** ha una sezione **Il tuo esercito** con tutto ciò che combatte per te: servi, salme, marionette, Spiriti del Dao e bandiera delle anime.
- Le **tecniche segrete di setta** stanno solo nel menu Tecniche, accanto alla fucina.

Nuovi test. Suite totale: **602 passati**.

---

## Aggiornamento 48 — Viaggio a tappe

Toccare un luogo lontano sulla mappa non ti teletrasporta più: **viaggi tappa per tappa** lungo la strada più breve, e il tempo passa.

**Lungo la via:**
- ✿ **raccogli** erbe e minerali (di più negli anelli lontani);
- ✦ incontri **viandanti** che ti lasciano qualche pietra;
- ❖ se passi accanto a un **incontro misterioso**, ti fermi lì;
- ⚠ può tenderti un **agguato** una creatura del luogo. Il viaggio si ferma e scegli se combattere, combattere a turni o aggirarla e ripartire (quel giorno la stessa tappa non ti riprende).

Gli imprevisti capitano più spesso nei luoghi pericolosi e negli anelli lontani. **In volo** capitano la metà delle volte, e col **passo nel vuoto** (dal 6° regno) non capita nulla: arrivi e basta.

**Sulla mappa:**
- passando sopra un luogo si illumina la strada che percorreresti;
- il clic avvia il viaggio;
- la vista non si sposta più a ogni azione, solo quando ti muovi.

---

## Aggiornamento 49 — Il combattimento visivo: l'arena del duello

Il duello a turni nella dashboard ora è un'**arena**:
- **ritratti e barre**: tu e l'avversario, con la vita in grande, Qi e spirito, il regno, quanto è forte rispetto a te e il suo stile (impetuoso, prudente, subdolo, equilibrato);
- **avvisi chiari**: se ha l'elemento a favore o a sfavore, se è **concentrato**, e ⚠ quando sta **caricando un colpo pesante** (lampeggia);
- **carte delle azioni**: Colpisci, **tutte le tue tecniche** (fino a 8, non più solo 3), Difendi, Concentrati, Pillola, Fuggi.
  - Ogni tecnica mostra il costo in Qi o spirito e gli effetti (×danno, colpi in più, perforazione, danno subito ridotto).
  - Quelle non usabili dicono perché («si ricarica tra 2 turni», «serve 54 spirito»).
  - Difendi si illumina quando arriva il colpo pesante.
  - I tasti 1-9 giocano le carte;
- **numeri di danno** che saltano fuori dai ritratti (più grandi sui critici);
- **gli alleati scendono in campo**: Spiriti del Dao, bestia, spirito dell'arma, servi, cloni e marionette ora combattono anche nei duelli e colpiscono a ogni turno;
- **registro dello scambio**: le ultime righe del turno.

Quando l'avversario crolla, l'arena resta visibile con le tre scelte: finirlo, risparmiarlo o marchiarne l'anima.

Il registro principale non ripete più le scelte numerate delle scene, che hanno già i loro pulsanti.

---

## Aggiornamento 50 — Ritratti, paesaggi, suoni

- **Ritratti generati.** Ogni personaggio ha un volto disegnato dal suo nome, sempre lo stesso: capelli, acconciatura (crocchia, chiome lunghe, corona di giada), barba, veste, carnagione e aura. Compaiono nell'arena del duello, nelle schede di Alleati e nemici e accanto ai presenti nel luogo. Se metti un disegno tuo nella cartella `immagini/` con il nome del personaggio, prende il posto del ritratto generato.
- **Paesaggi a inchiostro.** Il riquadro del luogo ha uno sfondo discreto che cambia col tipo di luogo: profili di monti, tetti della città, colonne delle rovine, nebbie rosse delle zone proibite. È diverso per ogni luogo e funziona nel tema chiaro e in quello scuro.
- **Suoni discreti**, sintetizzati, senza file:
  - un accordo per i titoli e i risvegli;
  - una nota grave per i pericoli;
  - il colpo e il critico nei duelli.
  
  Il pulsante 🔊 in alto a destra li spegne e la scelta viene ricordata.

---

## Aggiornamento 51 — Le immagini vere: dipinti classici al posto dei disegni generati

La cartella `immagini/` ora ha delle **sottocartelle per ogni parte del gioco**, e la dashboard le usa ovunque:

| Cartella | Dove compare |
|---|---|
| `luoghi/` (`city`, `mountain`, `ruin`, `forbidden_zone`) | sfondo del riquadro del luogo e dell'arena del duello |
| `mondi/` (`0`, `1`, `2`, `3`…) | sfondo della mappa di ogni mondo |
| `ritratti/` (nome del personaggio, oppure il tipo: `patriarca`, `anziano`, `eremita`, `discepolo`, `guardia`, `mercante`, `vagabondo`, `cacciatore`, `f`, `f_anziana`, `eroe`) | ritratti nell'arena, nelle schede di Alleati e nemici e accanto ai presenti |
| `bestie/` (`drago`, `fenice`, `tigre`, `tartaruga`, `qilin`, `gru`, `volpe`, `serpente`, `kun`) e `creature/` (`beast`, `demon`, `spirit`) | ritratti delle creature |
| `momenti/` (`tribolazione`, `duello`) | riservata ai momenti speciali |

L'ordine di precedenza è: prima un'immagine col nome esatto, poi quella del tipo, infine il disegno generato.

**Per riempirle in un colpo**, dal tuo PC (serve internet):

    python strumenti/scarica_immagini.py

Lo script cerca su **Wikimedia Commons** i grandi dipinti cinesi classici, uno per ogni posto:
- i paesaggi Song di Fan Kuan, Guo Xi e Li Cheng;
- il «Lungo il fiume durante la festa di Qingming»;
- «Mille li di fiumi e montagne» di Wang Ximeng;
- l'immortale a inchiostro spruzzato di Liang Kai;
- i Nove Draghi di Chen Rong;
- le gru di Huizong;
- la Ninfa del fiume Luo;
- Zhong Kui…

Le salva a 1024 pixel e annota titolo, autore e licenza in `immagini/CREDITI.txt`. `--elenco` mostra cosa cercherebbe senza scaricare; `--tutto` riscarica tutto. Le ricerche sono in cima allo script e si possono cambiare, e qualsiasi immagine si può sostituire con una tua dello stesso nome.

Nuovi test. Suite totale: **607 passati**.

## Aggiornamento 52 — Ribilanciamento (simulazioni da 400 giorni)

Quattro partite automatiche da 400 giorni, una per origine, prima e dopo le modifiche: le morti
scendono da 8–9 a circa 6 per partita.

- **Inseguitori** più bassi rispetto alla tua forza (cacciatori 0,7–1,05×, campioni 0,8–1,1×,
  nemesi e arcinemici 0,85–1,2×). I padri, i patriarchi e gli anziani delle faide restano come
  sono.
- **Campioni delle specie** ogni 10 bestie uccise della stessa specie, non più ogni 6.
- **Faide dopo la rinascita**: chi ti dava la caccia perde le tue tracce e torna a cercarti dopo
  90 giorni.
- **Copie della stessa tecnica**: non si sommano più una per una. Conta la copia più forte, più
  un piccolo bonus che cresce col logaritmo del numero di copie. Nel salvataggio di prova il
  fattore tecniche passa da 43,7 a 12.

## Aggiornamento 53 — Evoluzione del sangue, risonanza col corpo, testo essenziale

- **Evoluzione del sangue** (`engine/systems/blood_evolution.py`): ogni famiglia ha una o più
  evoluzioni verso un rango più alto, alcune con un ramo per elemento.
  - Le catene: serpente ▸ Jiao ▸ Drago ▸ Drago Azzurro ▸ Drago della Torcia ▸ Hundun; Kun ▸
    Kunpeng; gru ▸ Fenice ▸ Uccello Vermiglio; lupo ▸ Tiangou ▸ Taotie.
  - Tre famiglie nuove si ottengono solo evolvendo: **Jiao**, **Tiangou** e **Drago Giallo**.
  - Servono un grado del lignaggio e un regno, entrambi crescenti col rango d'arrivo. Poi si
    passano tre giorni nel bozzolo con una probabilità di riuscita. La probabilità sale col
    grado in più, con la purezza, con un'essenza della bestia d'arrivo (che fa da guida), con
    il Domatore e col corpo affine.
  - Se l'evoluzione fallisce, il sangue perde il 20%, ti ferisce e si può ritentare dopo 7
    giorni.
  - La forma di prima resta come tratto minore, e ogni evoluzione dà +8% di forza al lignaggio.
  - In cima c'è l'Hundun; poi il sangue **ascende oltre il Caos** senza fine.
  - Nei lignaggi fusi si propongono solo le evoluzioni che alzano davvero il rango.
  - Le evoluzioni passano alla vita successiva insieme al sangue ereditato.
  - Si usano dal menu `sangue` o con `sangue evolvi <n> [forma]`; quando un lignaggio diventa
    pronto, lo annuncia.
- **Risonanza corpo-sangue** (`engine/systems/body_blood.py`): ogni corpo leggendario ha
  famiglie ed elementi affini.
  - Con un lignaggio affine il sangue si concentra fino a +50%, combatte fino a +20%, il dono
    del corpo scatta più spesso e le evoluzioni riescono il 15% in più.
  - La risonanza cresce con gli stadi di risveglio del corpo.
  - Quando il sangue evolve nella bestia del tuo corpo, il corpo si risveglia di uno stadio.
  - La risonanza compare nel menu del sangue, nel pannello del corpo e nella scheda Eroe.
- **Poteri dei corpi leggendari** (`engine/systems/body_powers.py`): ogni corpo ha una sua via di
  sei poteri.
  - Stadio 1: la tecnica del corpo.
  - Stadi 2 e 3: due doni passivi.
  - Stadio 4: il potere maggiore e la seconda tecnica.
  - Stadio 5 (Corpo Compiuto): il potere supremo.
  - Oltre: ogni 3 stadi la tecnica sale di grado, senza fine.
  - Alcuni esempi: il Corpo Santo apre il Mare dell'Amaro e la Ruota della Vita; l'Osso Supremo
    ha le Arti Preziose del Suanni e del Kunpeng; l'Asura ottiene Tre Teste e Sei Braccia; il
    Nirvana della Fenice rinasce dal fuoco.
  - I poteri passivi entrano in ogni scontro, le tecniche si sommano alle altre. Nei salvataggi
    vecchi i poteri già raggiunti si sbloccano al primo comando.
- **Corpo Supremo** (`engine/systems/supreme_body.py`, `corpo supremo`): sta sopra i corpi
  leggendari e i lignaggi.
  - Si sblocca con il corpo al Corpo Compiuto e un lignaggio di rango Ancestrale o più alto al
    grado Primordiale.
  - La fusione dura 7 giorni. Il corpo che nasce dipende da corpo e sangue: Primo Dio, Sovrano
    dei Draghi Ancestrali, Fenice dell'Eterno Nirvana, Mille Mondi, Re dei Demoni Celesti,
    Montagna Primordiale, Abisso del Nord, Spada che Precede il Cielo, oppure il Corpo Supremo
    del Cielo e della Terra.
  - Doni: coltivazione +40%, attacco +20%, danni subiti −12%, un colpo e una resurrezione in più,
    sangue e doni del corpo +30%, la tecnica suprema.
  - Cresce di livello senza fine con i risvegli del corpo e i gradi del sangue: +10% di tutto a
    livello e una nuova tecnica suprema ogni 5 livelli.
- **Corpi dei nemici** (`engine/systems/body_absorb.py`):
  - Alcuni coltivatori forti, dal 3° regno in su, portano un corpo leggendario. Sono più
    probabili tra patriarchi, anziani e geni, combattono il 20% più forte e il nome del corpo
    compare tra i presenti.
  - Sconfitti, lasciano un'Essenza del Corpo. Se non hai un corpo, la sua essenza te lo dà.
    Se è lo stesso corpo che hai, si risveglia di uno stadio.
  - Se è un corpo diverso, si tenta la fusione: la riuscita va dal 60% al 95% secondo i tuoi
    stadi. Riuscita, aggiunge i doni dell'altro corpo a metà forza (senza maledizione), la sua
    tecnica e le sue affinità di sangue. Il nome diventa «Corpo A ⟡ Corpo B» e non c'è limite
    ai corpi fusi.
  - Anche i corpi fusi contano per il Corpo Supremo.
- **Testo essenziale**:
  - Il diario della dashboard passa da un filtro (`engine/systems/compact.py`) che non riscrive
    nulla e sceglie soltanto cosa mostrare:
    - le righe ripetute compaiono una volta sola;
    - gli elenchi lunghi mostrano i primi 5 elementi più «e altri N»;
    - cinque o più righe dello stesso tipo si riducono alle prime tre più «e altre N simili»;
    - spariscono i suggerimenti da terminale.
  - La frontiera che si allarga di più anelli insieme dà una riga sola, non nove.
  - L'allenamento mostra al massimo 4 Dao.
  - Nei menu restano aperte le prime 6 voci e le altre si raccolgono sotto «Altre N voci».
    Ogni voce mostra al massimo 3 righe, con il resto in «altri dettagli». I pulsanti non
    disponibili diventano piccoli, con il motivo nel tooltip.
- **Velocità a partita avanzata**: sette indici nuovi (cultivation_records, consequences, npcs per
  stato/luogo, evento e caccia, character_profiles). Sul salvataggio reale tre notti di sonno
  passano da 1,45 s a 0,61 s; le query più lente (fino a 270 ms) ora restano sotto i 10 ms.
- **Correzioni**:
  - Le ricompense «un Dao a caso» creavano un finto Dao chiamato «random». Ora scelgono uno dei
    tuoi Dao, e il finto Dao dei vecchi salvataggi confluisce in quello più praticato.
  - Il guadagno di spirito si mostra senza decimali.
  - Un test dipendeva dall'ordine delle righe nel database.

## Aggiornamento 54 — Il regista delle trame

Il gioco ora tiene una raccolta di trame a più atti, scritte a mano (`engine/systems/intrigue_data.py`).
Ogni giorno un regista (`engine/systems/intrigues.py`) sceglie il momento di storia più adatto. Non
genera testo nuovo: dà un punteggio ai candidati e prende il migliore, in una passata sola.

- **I candidati** sono l'atto successivo di ogni trama aperta e l'inizio delle trame nuove adatte al
  tuo regno. Il punteggio sale se l'atto è maturo o aspetta da giorni, se tocca i tuoi legami o la
  tua setta e se chi è in scena ti è vicino. Scende se hai appena vissuto una trama dello stesso tipo.
- **Il ritmo**: un solo momento di trama al giorno, e solo se non c'è un'altra scena aperta. Al
  massimo due trame aperte, una nuova ogni 6 giorni al più, la stessa non prima di 60 giorni. Una
  trama lasciata a metà per 30 giorni si chiude da sola.
- **Il cast** viene dal mondo vivo: i tuoi legami e compagni di setta, i potenti delle altre sette,
  oppure personaggi creati per la trama. Chi deve combattere ti raggiunge.
- **Indizi e rami**: le prove riuscite danno indizi e le scelte aprono rami. L'atto finale cambia
  con quello che sai. Con due indizi puoi smascherare il mandante; senza, la verità resta
  nell'ombra. Alcune scelte compaiono solo se hai preso un certo ramo, per esempio perdere apposta
  il torneo dopo aver accettato il denaro.
- **Sette trame** ispirate alle grandi saghe di coltivazione:
  - *La mano nell'ombra*: un delitto per far scoppiare una guerra tra sette.
  - *Il Torneo delle Cento Sette*: corruzione, lame avvelenate, un genio che nasconde la sua forza
    e una finale contro chi ha comprato i giudici.
  - *Il debito dell'Oltretomba*: un falsario dei registri della vita e della morte.
  - *L'eredità del Dio-Demone*: una mappa incisa nell'osso, le tre prove e un tradimento nella
    tomba.
  - *La maledizione della vita passata*.
  - *Il traditore della setta*, con la possibilità del doppio gioco.
  - *L'Isola della Spada Nascosta*, che appare ogni sessant'anni.
- **Dove si vede**: le trame aperte e concluse compaiono in testa al menu Eventi e con il comando
  `trame`. Ogni finale entra nella cronaca, e il titolo «Tessitore di Trame» arriva dopo cinque
  trame concluse.
- **Come aggiungerne**: una trama nuova è un dizionario (cast, atti, scelte, esiti); il formato è
  spiegato in testa a `intrigue_data.py`. I nomi delle sette prendono l'articolo giusto («del
  Palazzo…», «della Setta…»).
- I corpi leggendari degli NPC ora sono deterministici per mondo, e nei test che confrontano le
  forze vengono neutralizzati.

