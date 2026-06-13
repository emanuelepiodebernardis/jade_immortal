# Jade Immortal

Simulatore narrativo testuale (Wuxia/Xianxia). Uso personale, offline.

## Stato fasi
- **Fase 0 — Foundation** ✅
- **Fase 1 — World Static** ✅ (mondo procedurale, movimento, NPC statici)
- **Fase 2 — NPC Identity** ✅ (archetipi, traits correlati, rapporti NPC-player)
- **Fase 3 — World Tick System** ✅ (NPC autonomi, active scope P1, event log tracciabile)
- **Fase 4 — Factions** ✅ (fazioni, territori, leader, drift autonomo: espansione/conflitto)
- **Fase 5 — Events System** ✅ (incontri, scontri, morte differita, resolver, cronache)
- **Fase 6 — Combat System** ✅ (combat a round non lineare, ferite, morte, NPC vs player)
- **Fase 7 — Cultivation Core** ✅ (8 regni, progresso, breakthrough con fallimento/morte)
- **Fase 8 — Memory System** ✅ (memoria stratificata derivata dal log eventi)
- **Fase 9 — Narrative Engine** ✅ (LLM Ollama + fallback, scena leggibile, sink puro)
- **Fase 9.1 — Linguaggio naturale** ✅ (LLM come traduttore di intenti; ibrido)
- **Fondamenta del Personaggio** ✅ (origini, affinità nascoste, creazione personaggio)
- **Abisso Divoratore v1** ✅ (Dao + affinità latenti, anomalia di assorbimento, preset)
- **Fase 10 — Karma** ✅ (peso morale nascosto: uccisioni/assorbimenti, breakthrough, sventura)
- **Sette & Allenamento** ✅ (test d'ingresso sul talento, iscrizione, risorse, economia giornaliera)
- **Sotto-livelli** ✅ (10 strati per regno: progressione graduale, breakthrough come evento di regno)
- **Competizione di setta** ✅ (compagni di classe, sfida programmata, tornei mensili, promozione)
- **Allenamento Dao** ✅ (comprensione allenabile, i Dao da combattimento danno potenza, risveglio via assorbimento)
- **Avventure in città** ✅ (ricercati da cacciare, taglie/missioni, karma che premia la giustizia)

## Avvio
```bash
cd jade_immortal
python main.py
```
Al primo avvio crea `database/world.db` e **genera** il mondo (procedurale,
deterministico dal seed in `config/world_config.yaml`).
Per rigenerare: cancella `database/world.db`.

## Test
```bash
python -m pytest -q     # 11 test
```

## Comandi CLI
`move <n/s/e/w>`, `wait`, `cultivate`, `dao`, `comprehend`, `breakthrough`, `look [dir]`, `examine <nome>`, `greet <nome>`, `attack <nome>`, `narrate`, `chronicle`, `profilo`, `absorb`, `sects`, `join`, `class`, `leave`, `bounties`, `map`, `factions`, `faction <nome>`, `log [n]`, `memories`, `where`, `status`, `help`, `quit`

## Cosa c'è
- Schema SQLite **completo** (tutta la spec + `location_connections` + `npcs.last_active_tick`)
- Connection manager (FK on, Row factory, transazioni), tick system + log
- **Generatore procedurale** (`engine/generators/world_gen.py`): mondo → continente →
  territori → location su griglia (grafo N/S/E/W connesso e reciproco garantito),
  danger per profondità, NPC statici. Deterministico via seed.
- Loop CLI esteso

## Principi vincolanti
Vedi `docs/ARCHITECTURE_PRINCIPLES.md`:
- **P1** Active Simulation Scope (convenzione per Fase 3, colonna già pronta)
- **P2** Factual Lock = narrative layer come *sink puro* (Fase 9)

## Gap colmati vs spec
- `location_connections`: grafo di adiacenza (assente nello spec, serve al movimento)
- `npcs.last_active_tick`: abilita la batch simulation futura
- `npcs.archetype`: archetipo che guida i traits (e l'AI futura)
- `npc_player_relations`: disposizione NPC verso il giocatore

## Config
- `config/world_config.yaml`: seed, n. territori, location per territorio, n. NPC
- `config/settings.yaml`: modello LLM (non ancora usato)

## Cosa c'è in Fase 2
- `engine/generators/npc_gen.py`: ogni NPC ha un **archetipo** (anziano, mercante,
  eremita, discepolo, guardia, vagabondo) con **traits correlati** (l'anziano è
  onorevole e poco ambizioso, il mercante avido, ecc.). Descrizione e tag generati
  dai traits, senza LLM.
- `engine/systems/relations.py`: rapporto NPC↔player (stranger→acquaintance→friend
  / rival→enemy), aggiornato da `greet`.

## Cosa c'è in Fase 3
- `engine/simulation/world_tick.py`: il mondo evolve da solo. A ogni tick gli NPC
  nello **scope attivo** (location del player + adiacenti, principio P1) restano
  fermi o si spostano. Gli NPC fuori scope sono dormienti (`last_active_tick` fermo).
- `engine/simulation/event_system.py`: `log_event` impone il **vincolo 26** a livello
  di codice — un evento NON può esistere senza ≥1 partecipante e ≥1 conseguenza.
  Verificato: zero eventi orfani; ogni evento è interrogabile via SQL (chi/cosa/quando/visibilità).
- `wait` fa avanzare il tempo e mostra cosa accade intorno a te.
- Determinismo: stesso seed + stesso rng → stessa evoluzione (riproducibile).

## Cosa c'è in Fase 4
- `engine/generators/faction_gen.py`: fazioni con sede, territorio iniziale, un
  **leader** (NPC archetipo 'patriarca') e relazioni iniziali (alleate/tese/neutrali).
  Gli NPC nei territori controllati diventano **membri** in base all'archetipo.
- `engine/simulation/faction_engine.py`: **drift autonomo**. Ogni ~24 tick ogni
  fazione tenta un'azione di confine: espansione (su territorio libero) o conflitto
  (su territorio altrui, prob. legata alla relazione — le alleanze evitano lo scontro).
  Influenza e controllo territoriale cambiano da soli. Tutto tracciabile (vincolo 26).
- CLI: `factions`, `faction <nome>`; il controllo è mostrato nelle location.

## Cosa c'è in Fase 5
- `engine/simulation/event_generator.py`:
  - **incontri** tra NPC co-locati: la relazione migliora/peggiora per tratti +
    enmity ereditata dalle fazioni (principio 8: le guerre nascono da relazioni deteriorate);
  - **scontri** (fight): un incontro molto ostile degenera; risoluzione semplice
    (precursore della Fase 6);
  - **morte (rara)** via **conseguenza differita**: lo scontro programma un
    `death_check` a un tick futuro; `resolve_due_consequences` lo applica quando matura,
    con bassa probabilità di morte. Se muore un leader → **successione** automatica.
- Tassi regolabili via costanti in cima al modulo (tuning fine = Fase 16).
- `relations.py`: relazioni NPC↔NPC. CLI: `log [n]` = cronache pubbliche.

## Cosa c'è in Fase 6
- `engine/simulation/combat.py`: combattimento **a round, non lineare** (no somma
  pesata): danno con varianza (caos controllato) + **colpi critici** a soglia che
  ribaltano gli scontri. La potenza conta ma non è assoluta — gli imprevisti accadono.
- **Ferite** persistenti (`injuries`) che riducono la potenza e guariscono nel tempo;
  ferite gravi possono rivelarsi fatali (riusa il `death_check` differito della Fase 5).
- Funziona NPC vs NPC e **NPC vs giocatore**: il comando `attack <nome>` ti fa
  combattere, e puoi morire. Un NPC molto ostile può attaccarti da solo.
- Hook `_realm_factor` pronto per la Fase 7 (la coltivazione moltiplicherà la potenza).
- Valori base riequilibrati una volta; il tuning fine resta Fase 16.

## Cosa c'è in Fase 7
- 8 regni (tier 1–8), da Condensazione del Qi fino a **Immortale di Giada**.
- `engine/simulation/cultivation.py`: `cultivate` accumula progresso; al colmo
  si tenta un **breakthrough** che può riuscire, fallire (contraccolpo) o causare
  **deviazione del qi e morte** (più rischioso ai regni alti). Progresso NON garantito.
- Gli NPC coltivano da soli nello scope attivo e talvolta sfondano (o muoiono):
  la gerarchia di potere del mondo evolve.
- La coltivazione alimenta il combat (`_realm_factor`): salire di regno ti rende più forte.
- CLI: `cultivate`, `dao`, `comprehend`, `breakthrough`; regno mostrato in `status` ed `examine`.

## Cosa c'è in Fase 8
- `engine/systems/memory.py`: la memoria è **derivata dal log eventi**, non un
  archivio duplicato (niente doppia verità / desync — coerente coi principi).
  - `short_term`: ricordi entro una finestra di tick;
  - `historical`: ricordi vecchi ma significativi (banalità filtrata in SQL);
  - `active_memory`: selezione limitata e ordinata (recency × importanza) — pronta
    contro il context drift, è ciò che la Fase 9 darà all'LLM;
  - `world_historical`: cronaca significativa del mondo.
- CLI: `memories` mostra ciò che il tuo personaggio ricorda.

## Cosa c'è in Fase 9 — VERTICAL SLICE COMPLETO
- `engine/narrative/context.py`: NarrativeContext = SOLO fatti osservabili
  (Factual Lock), limitato (memoria attiva, NPC presenti, eventi locali recenti).
- `engine/narrative/prompts.py`: system prompt xianxia che VIETA all'LLM di
  inventare eventi/emozioni/cause — è renderizzatore, non interprete.
- `engine/narrative/llm.py`: client Ollama (solo stdlib). **Graceful**: se
  disabilitato o Ollama non raggiungibile, ritorna None.
- `engine/narrative/renderer.py`: usa l'LLM se disponibile, altrimenti un
  **fallback deterministico** che intesse i fatti in prosa. Il narrative layer è
  un **SINK PURO** (P2): non scrive MAI nella simulazione (verificato da test).
  Controllo entità (Factual Lock leggero) sui nomi inventati.
- CLI: `narrate` (scena come prosa), `chronicle` (cronaca del mondo).

### Linguaggio naturale (ibrido)
Con Ollama attivo (`llm.enabled: true`) puoi scrivere in italiano naturale: se la
frase non è un comando noto, l'LLM la traduce in un comando permesso (es.
"esamina il vecchio" -> `examine Han`). L'LLM NON decide l'esito: traduce soltanto;
il motore deterministico esegue. La riga `(interpreto: ...)` mostra il comando scelto.
Senza Ollama restano i comandi fissi. Modulo: `engine/cli/intent.py`.

### Abilitare la narrativa LLM
1. Installa Ollama e scarica un modello (es. `ollama pull qwen3:8b`).
2. In `config/settings.yaml` metti `llm.enabled: true` (e il modello che preferisci).
3. Senza Ollama il gioco resta giocabile col fallback testuale.

## Fondamenta del Personaggio (prima passata)
- All'avvio scegli un'**origine** (Mortale, Clan, Genio, Reincarnato, Erede): ognuna
  con pregi E fardelli — nessuna build dominante.
- **Affinità nascoste** (`character_profiles`): numeri interni che alimentano
  coltivazione, breakthrough e combattimento, ma mostrati SOLO come etichette
  qualitative ("affinità prodigiosa"). Modulo: `engine/systems/character.py`.
- Trade-off reali: Genio = tribolazioni più dure; Erede = braccato; Clan = rivali.
- CLI: `profilo` (origine, età, affinità qualitative).
- Prossimo strato personaggio: Tecniche, e l'espansione dei Dao profondi.

## Abisso Divoratore (v1) — la prima Anomalia
- **Dao** classificati su 3 livelli (narrative/systemic/deep) in `daos`; ogni
  personaggio ha affinità (latente, nascosta) e comprensione per Dao (`character_daos`).
- Origine **"Portatore dell'Abisso Divoratore"**: pratica Corpo/Anima/Fulmine,
  **affinità latenti** verso Destino/Tempo/Spazio (potenziale, non potere), anima
  alta come contenitore, e il fardello "braccato".
- **Assorbimento** (`engine/systems/absorption.py`): `absorb <nome>` sui resti di
  un caduto. Mai garantito — esito randomico (frammento di comprensione *o* trauma);
  rendimento decrescente per dislivello; decadimento del cadavere nel tempo; l'anima
  fa da contenitore; ogni assorbimento accumula **residuo** che destabilizza i
  breakthrough e, all'estremo, frantuma l'anima. Rubi eredità, non potenza.
- **Preset**: in `config/settings.yaml` `character.default_origin: divoratore` salta
  la scelta a ogni avvio.
- Slottato (non implementato): cadaveri leggendari/jackpot, personalità multiple,
  Dao profondi con effetti meccanici, tecniche.

## Fase 10 — Karma (peso morale invisibile)
- `karma_records`: ogni personaggio (anche NPC) ha un karma NASCOSTO. Mostrato solo
  qualitativamente nel `profilo` ("un debito karmico sottile ti segue"). Modulo:
  `engine/systems/karma.py`.
- **Generato dalle azioni**: uccidere = karma negativo (peggio uccidere i deboli; meno
  per legittima difesa); risparmiare un avversario = piccolo karma positivo; assorbire =
  negativo + **eredita parte del karma della vittima** (i debiti dei caduti diventano tuoi).
- **Effetti emergenti**: karma negativo rende i breakthrough più letali (tribolazione
  karmica, fino a +80%); karma molto negativo (< -60) attira **sventura** — un NPC presente
  può voltarti contro (evento `karmic_pressure`). Vale anche per gli NPC.

## Sette & Allenamento (agenzia del giocatore — parte 1)
- **Sette in cui iscriversi**: ogni fazione con una sede è una setta. `sects` le
  elenca; alla sede usi `join` per il **test d'ingresso**, che misura il tuo
  talento riusando le **affinità nascoste** del profilo e assegna un **grado di
  radici spirituali** -> rango (Servitore / Esterno / Interno / Nucleo) + **pietre
  spirituali**. Affiliazione registrata; rango e risorse in `status`. Modulo:
  `engine/systems/sects.py`.
- **Economia dell'allenamento**: ora esiste il **giorno** (120 tick). La
  coltivazione ha **rendimento decrescente**: ~4 sessioni utili al giorno (pieno ->
  buono -> calante), poi sei sfinito e conviene riposare/fare altro. Allenarsi
  presso la sede della propria setta dà +30%. Modulo: `engine/systems/training.py`.
  Niente più scalata dei regni a spam infinito.
- Prossimo (parte 2): città viva — parlare con NPC, dicerie, mercato, bacheca incarichi.

## Sotto-livelli (10 strati per regno)
- Ogni regno è diviso in **10 strati**. `cultivate` riempie l'esperienza dello
  strato corrente; quando si colma avanzi automaticamente di strato (1→2→…→10),
  l'esperienza riparte e le **statistiche salgono** (Strato 4 > Strato 3).
- Solo allo **Strato 10 colmo** puoi tentare il `breakthrough`: evento di REGNO,
  rischioso (può fallire → retrocedi di strato, o uccidere). Salire di regno ora è
  una conquista, non uno spam. Il combattimento scala col **livello effettivo**
  = (tier-1)·10 + strato.
- Gli NPC nascono a strati casuali (varietà di forza). Salvataggi vecchi: la colonna
  `stage` viene aggiunta in automatico.

## Competizione di setta (agenzia del giocatore — parte 2)
- Iscrivendoti ricevi **2-3 compagni di classe** (rivali reali, esaminabili) e ti
  viene **annunciato** il calendario. Modulo: `engine/systems/sect_life.py`.
- **Sfida di Classifica** programmata a 10 giorni dall'iscrizione: fissa la
  graduatoria iniziale della tua classe. Poi **Torneo Mensile** ricorrente.
- I tornei sono sparring NON letali: il piazzamento dipende da regno+strato+affinità
  (con varianza). Premi in pietre spirituali per posizione. Devi allenarti per salire.
- **Promozione di classe**: al breakthrough di regno entri nella classe successiva
  (nuovi compagni, nuovo calendario).
- `class` mostra compagni, posizione e prossimo evento; il countdown è anche in
  `status`. Gli eventi compaiono nelle osservazioni e alimentano `narrate`/`chronicle`.
- Scheduler generico di eventi nel tempo (`sect_events`): base per futuri eventi a tempo.

## Allenamento dei Dao (lo strato Dao diventa vivo)
- `dao` elenca i Dao che pratichi e la comprensione (qualitativa); `comprehend <nome>`
  li affina. Modulo: `engine/systems/dao_training.py`.
- **Affinità** (talento nascosto) accelera l'apprendimento; **tetto comprensione = 100**.
- **I Dao da combattimento** (Corpo/Fulmine/Spada) aumentano la potenza fino a **+20%**
  complessivo — allenarli ti rende più forte, ma regno e strato restano dominanti
  (nessuna build dominante). Gli altri Dao (Destino/Tempo/Spazio) si affinano ma i
  loro effetti meccanici restano per una fase futura.
- **Economia condivisa**: allenare un Dao e coltivare il regno pescano dalle stesse
  ~4 sessioni utili al giorno: ogni giorno scegli come spenderle. Più Dao insegui,
  più lento ognuno (attenzione divisa).
- **Vantaggio dell'assorbitore**: assorbendo guadagni comprensione in fretta e puoi
  **risvegliare** Dao di cui hai solo affinità latente (es. Destino) — poi allenabili.
  Paghi in karma e residuo: rubi eredità, non potenza.

## Avventure in città (cose da fare + bivio morale)
- **Ricercati**: al world gen alcuni NPC sono criminali con una **taglia** (depredano,
  tormentano, praticano arti demoniache). Portano karma negativo. `bounties` li elenca
  (crimine, luogo, ricompensa); `examine` segnala "⚠ RICERCATO". Modulo:
  `engine/systems/bounties.py`.
- **Caccia**: sconfiggi un ricercato con `attack` → **taglia riscossa** (pietre spirituali).
- **Twist karmico**: GIUSTIZIARE un criminale è un atto giusto → **karma positivo** (non il
  malus delle uccisioni normali). Uccidere un innocente resta negativo.
- **Bivio dell'assorbitore**: puoi **divorare** il criminale per potere (comprensione Dao,
  perfino risvegliare Dao profondi) MA erediti i suoi debiti karmici → l'anima si macchia.
  Esecutore giusto, oppure predatore di potere.
- I ricercati ogni tanto seminano il terrore (eventi `crime`), e la lista si ripopola da sola.

## Stato: simulation core + narrativa + creazione personaggio = slice giocabile.
Rimangono (opzionali): karma (10), percezione (11), risorse (12), tribolazioni (13),
Obsidian (14), AI loop avanzato (15), polish/tuning (16); più Dao/Anomalie/Tecniche.
