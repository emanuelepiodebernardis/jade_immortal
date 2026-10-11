
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
