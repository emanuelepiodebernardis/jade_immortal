# Mappa del codice

Generata da `strumenti/mappa_codice.py`: per ogni modulo la prima riga della sua documentazione.
Rigenerala dopo un aggiornamento grande (`python strumenti/mappa_codice.py`).

Come è organizzato il gioco:
- `engine/core` — le entità e il tempo (tick, giocatore, personaggi, luoghi).
- `engine/simulation` — il mondo che vive da solo: coltivazione, combattimento, eventi.
- `engine/systems` — un modulo per sistema di gioco (setta, Dao, sangue, duello, grotte…). Ogni sistema
  tiene il suo stato in `state` (JSON) o in tabelle sue, ed espone `command`, `menu_build`, `daily` quando serve.
- `engine/cli` — i comandi testuali (`loop.dispatch` e `story_cmds.handle`).
- `engine/web` — la dashboard: `game.py` (dati), `server.py` (API), `static/` (pagina).
- `engine/narrative` — i testi variati e il modello linguistico opzionale.

## engine

| file | righe | cosa fa |
|---|---:|---|
| `db.py` | 190 | Connection manager per SQLite. |

## engine/cli

| file | righe | cosa fa |
|---|---:|---|
| `cmd_sect.py` | 460 | Comandi di SETTA del terminale (spostati da loop.py per tenerlo leggibile): elenco delle sette, |
| `help_text.py` | 403 | Testo d'aiuto, diviso per categorie. |
| `hud.py` | 56 | Riga di stato compatta (HUD) mostrata dopo ogni comando. |
| `intent.py` | 82 | Interprete di intenti in linguaggio naturale (Fase 9.1 — layer ibrido). |
| `lifecycle.py` | 197 | Inizio e fine di una vita: creazione del personaggio (origine + nome) e, alla morte, |
| `loop.py` | 2653 | Loop CLI (Fase 1 — World Static). |
| `story_cmds.py` | 741 | Comandi dei nuovi sistemi narrativi: scelte numerate, incontri, legami, obiettivi, |

## engine/core

| file | righe | cosa fa |
|---|---:|---|
| `entities.py` | 268 | Entità base e funzioni di accesso (repository). |
| `seed.py` | 78 | Seed minimale per la Fase 0. |
| `tick.py` | 72 | Sistema tick globale. |

## engine/generators

| file | righe | cosa fa |
|---|---:|---|
| `creature_gen.py` | 151 | Creature selvagge: bestie, demoni, spiriti. |
| `cultivation_gen.py` | 126 | Generazione coltivazione (Fase 7). |
| `dao_gen.py` | 139 | Generazione Dao (v1). |
| `faction_gen.py` | 137 | Generazione fazioni (Fase 4 — Step 6 della spec). |
| `npc_gen.py` | 149 | Generazione NPC (Fase 2 — NPC Identity). |
| `world_gen.py` | 311 | Generatore procedurale del mondo (Fase 1 — World Static). |

## engine/narrative

| file | righe | cosa fa |
|---|---:|---|
| `context.py` | 98 | NarrativeContext builder (Fase 9). |
| `llm.py` | 68 | Client LLM (Ollama) per il narrative engine (Fase 9). |
| `prompts.py` | 53 | Prompt per il narrative engine (Fase 9). |
| `renderer.py` | 105 | Renderer narrativo (Fase 9). |
| `varia.py` | 188 | VARIA — testo che non si ripete (senza LLM). |

## engine/simulation

| file | righe | cosa fa |
|---|---:|---|
| `combat.py` | 384 | Combat System (Fase 6). |
| `cultivation.py` | 371 | Cultivation system (Fase 7). |
| `event_generator.py` | 222 | Event generator (Fase 5). |
| `event_system.py` | 70 | Event system — registrazione eventi con invariante di tracciabilità (vincolo 26). |
| `faction_engine.py` | 178 | Faction engine (Fase 4) — drift autonomo delle fazioni. |
| `world_tick.py` | 224 | World Tick System (Fase 3). |

## engine/systems

| file | righe | cosa fa |
|---|---:|---|
| `absorption.py` | 494 | Anomalia: Abisso Divoratore (v1). |
| `alignment.py` | 126 | VIE DELLE SETTE: ORTODOSSA, ETERODOSSA, DEMONIACA (正道 / 旁门 / 魔道). |
| `ancestral_sigils.py` | 212 | I SIGILLI ANCESTRALI (Aggiornamento 67) — le rune degli antichi, incastonate nel petto. |
| `archrival.py` | 183 | L'ARCINEMICO — il rivale che ti segue per tutta la vita (e oltre), senza mai essere l'ultimo. |
| `art.py` | 198 | LE IMMAGINI DEL GIOCO (Aggiornamento 68) — quale quadro mostrare per un oggetto, una mossa, una scena. |
| `ascension.py` | 367 | ASCENSIONE AI MONDI SUPERIORI (飞升) — infiniti strati di mondo, ognuno col suo TETTO. |
| `assembly.py` | 220 | GRANDE ASSEMBLEA DELL'ALLEANZA MARZIALE (武林大会). |
| `attention.py` | 188 | COSA CHIEDE ATTENZIONE (Aggiornamento 64) — i pallini rossi e «Cosa fare ora» della dashboard. |
| `attributes.py` | 241 | FINESTRA DI STATO — gli attributi del coltivatore (ispirata a «The Gamer»). |
| `auction.py` | 181 | CASA D'ASTE (拍卖会). |
| `auto_collect.py` | 108 | RACCOLTA AUTOMATICA — meno tasti: il bottino si raccoglie e le essenze si assorbono da sole. |
| `autopilot.py` | 757 | PILOTA AUTOMATICO — lo «stato etereo»: il personaggio vive da solo le parti monotone. |
| `beast_eggs.py` | 196 | UOVA E ALLEVAMENTO DI BESTIE. |
| `beast_team.py` | 262 | LA SQUADRA DI BESTIE (Aggiornamento 71) — alla Pokémon, nel mondo dei coltivatori. |
| `beasts.py` | 348 | BESTIE SPIRITUALI — domare, crescere, combattere insieme. |
| `blood_evolution.py` | 377 | L'EVOLUZIONE DEL SANGUE — ogni lignaggio può salire di rarità mutando nella bestia che ne è l'erede. |
| `blood_menu.py` | 331 | IL MENU DEL SANGUE — gestire i lignaggi in un posto solo ('sangue', pulsante 🩸 Sangue). |
| `bloodlines.py` | 775 | LIGNAGGI DI SANGUE (血脉) — il sangue delle bestie leggendarie che scorre in te. |
| `body_absorb.py` | 110 | I CORPI DEI NEMICI — anche gli altri nascono con un corpo leggendario, e chi li sconfigge lo prende. |
| `body_blood.py` | 139 | LA RISONANZA CORPO-SANGUE — il corpo leggendario e il lignaggio si riconoscono. |
| `body_powers.py` | 335 | I POTERI DEI CORPI LEGGENDARI — il corpo che si risveglia non diventa solo più forte: IMPARA. |
| `bonds.py` | 716 | LEGAMI — compagni di viaggio, maestro, rivali e NEMESI. |
| `bounties.py` | 161 | Taglie & criminali (avventure in città). |
| `breakthrough_fates.py` | 202 | DESTINI DELLO SFONDAMENTO (Aggiornamento 63) — a ogni nuovo regno, il Cielo ti offre tre strade. |
| `calibration.py` | 192 | LA TARATURA DEL GIOCO — tutte le manopole del ritmo e del pericolo, in un posto solo. |
| `captivity.py` | 127 | PRIGIONIA E FUGA — quando la forza non basta, serve l'astuzia. |
| `cave_abode.py` | 302 | GROTTA-DIMORA (洞府) — la tua casa tra le montagne. |
| `caves.py` | 373 | LE GROTTE (Aggiornamento 71) — un piccolo dungeon da percorrere stanza per stanza. |
| `celestial_elements.py` | 286 | ELEMENTI CELESTI (天地灵物) — l'essenza viva di ogni elemento, nata tra cielo e terra. |
| `character.py` | 264 | Fondamenta del Personaggio (prima passata). |
| `chronicle.py` | 91 | CRONACA — la storia della tua vita (e delle tue vite), da rileggere ed esportare. |
| `classes.py` | 198 | CLASSI DI PERSONAGGIO: ARTE + ELEMENTI. |
| `clones.py` | 322 | CLONI (分身) — dividi l'anima in più corpi. |
| `combat_narration.py` | 72 | Narrazione dei combattimenti. |
| `combat_states.py` | 351 | STATI DI COMBATTIMENTO — ciò che rende ogni scontro diverso. |
| `compact.py` | 71 | IL TESTO ESSENZIALE — alleggerisce il diario prima di mostrarlo (dashboard e pilota automatico). |
| `constitutions.py` | 487 | COSTITUZIONI SPECIALI (体质) — i corpi divini con cui pochi nascono. |
| `contests.py` | 139 | GARE DEI MAESTRI D'ARTE — Torneo degli Alchimisti, Concorso dei Forgiatori, e gli altri. |
| `cult_mods.py` | 123 | Moltiplicatori di coltivazione e comprensione raccolti da tutti i sistemi (un solo punto |
| `dantian.py` | 232 | IL DANTIAN (Aggiornamento 65) — le tecniche come pezzi da incastrare in uno spazio limitato. |
| `dao_heart.py` | 287 | CUORE DEL DAO (道心), DEVIAZIONE DEL QI (走火入魔) e TOSSINE DELLE PILLOLE (丹毒). |
| `dao_powers.py` | 172 | I tre Dao profondi, differenziati per RUOLO (impianto xianxia). |
| `dao_spirits.py` | 225 | SPIRITI DEL DAO — quando un Dao diventa profondo, prende forma e cammina accanto a te. |
| `dao_superiori.py` | 155 | DAO SUPERIORI — non si scelgono: si RISVEGLIANO. |
| `dao_techniques.py` | 246 | Tecniche generate dai Dao (la via del Guerriero Dao). |
| `dao_training.py` | 238 | Allenamento dei Dao. |
| `deep_dao.py` | 806 | I TRE DAO PROFONDI E LA SFIDA AL CIELO — arcani, risonanze, e la guerra con il Cielo. |
| `deification_tower.py` | 147 | LA TORRE DELLA DEIFICAZIONE (Aggiornamento 63) — piano dopo piano, settimana dopo settimana. |
| `destinies.py` | 202 | DESTINI ALLA NASCITA + TALENTO DEI RIVALI. |
| `dharma_body.py` | 179 | IL CORPO DEL DHARMA (Aggiornamento 67) — la proiezione gigante del tuo Dao. |
| `dialogues.py` | 278 | DIALOGHI E FAVORI — parlare davvero con chi ti è vicino. |
| `director.py` | 178 | IL REGISTA — regola il RITMO delle scene, perché il mondo non ti travolga di eventi simili. |
| `disciple_life.py` | 314 | LA VITA DEI DISCEPOLI (Aggiornamento 63) — carattere, compiti, lezioni e il demone del cuore. |
| `divine_sense.py` | 138 | SENSO DIVINO (神识) e CELARE IL PROPRIO LIVELLO (隐藏修为). |
| `dominion.py` | 1036 | DOMINIO — il Sigillo dell'Anima (魂印), le salme rianimate (炼尸) e le sette vassalle. |
| `duel.py` | 708 | DUELLO A TURNI — gli scontri importanti si giocano, non si leggono soltanto. |
| `duel_types.py` | 184 | TIPI E STATI NEL DUELLO (Aggiornamento 69) — il duello «alla Pokémon». |
| `echoes.py` | 130 | ECHI — le conseguenze che ritornano. |
| `elements.py` | 261 | CICLO DEI CINQUE ELEMENTI (五行), FUSIONI ELEMENTALI e FUSIONI LEGGENDARIE. |
| `elites.py` | 111 | ÉLITE E BOSS (Aggiornamento 70) — quando sei molto più forte del tuo regno, il mondo risponde. |
| `encounter_data.py` | 365 | Catalogo degli INCONTRI casuali (奇遇). Solo dati: il motore è in encounters.py. |
| `encounter_sagas.py` | 263 | SAGHE — incontri a più atti (2-3 scene concatenate con 'then'). |
| `encounters.py` | 665 | INCONTRI A SCELTA (奇遇) — mini-scene con 2–4 opzioni. |
| `eras.py` | 181 | LE ERE DEL MONDO e la CALAMITÀ che ritorna. |
| `face.py` | 134 | FACCIA E ONORE (面子) — le sfide pubbliche e le faide che crescono. |
| `family.py` | 247 | LA TUA FAMIGLIA — genitori, fratelli, il clan da proteggere (o da vendicare). |
| `fengshui.py` | 209 | FENG SHUI DELLA DIMORA e GIARDINO SPIRITUALE (Aggiornamento 65). |
| `feuds.py` | 488 | RANCORI E DEBITI (恩怨) — chi uccidi lascia qualcuno; chi risparmi, anche. |
| `formations.py` | 90 | FORMAZIONI PIAZZATE (阵法) — l'arte del Maestro delle Formazioni. |
| `frontier.py` | 479 | LA FRONTIERA — la mappa di ogni mondo si allarga man mano che sali. |
| `gear.py` | 385 | L'EQUIPAGGIAMENTO (Aggiornamento 69) — sei posti sul corpo, pezzi veri con regno, rarità, statistiche e set. |
| `gongfa.py` | 150 | METODI DI COLTIVAZIONE (功法) — come fai circolare il Qi. |
| `grand_tournament.py` | 143 | IL GRAN TORNEO DELL'ASCESA (Aggiornamento 65) — ogni novanta giorni, i prodigi di tutto il mondo. |
| `gu.py` | 158 | GU (蛊) — la via degli insetti spirituali, come Fang Yuan. |
| `guide.py` | 207 | L'INIZIO GUIDATO E IL CODEX (Aggiornamento 70). |
| `guild.py` | 162 | Gilde: zone di caccia, punti MERITO e TECNICHE segrete. |
| `heart_demon.py` | 127 | DEMONE INTERIORE (心魔) — la prova prima del breakthrough. |
| `heart_trials.py` | 45 | PROVE DEL CUORE (问心) — le illusioni che custodiscono le eredità. |
| `heaven_bonds.py` | 137 | I LEGAMI TI SEGUONO IN CIELO (Aggiornamento 63). |
| `heaven_trib.py` | 163 | TRIBOLAZIONE DEL FULMINE CELESTE (天劫) — a ogni nuovo regno, dal terzo in su. |
| `heirs.py` | 85 | GLI EREDI (Aggiornamento 65) — alla morte, la Via continua in chi hai cresciuto. |
| `history.py` | 54 | STORIA IN NUMERI — un'istantanea al giorno, per i grafici della dashboard. |
| `hunters.py` | 269 | Cacciatori dell'Eretico. |
| `idle_cultivation.py` | 87 | LA COLTIVAZIONE MENTRE SEI VIA (Aggiornamento 67) — il cuore idle del genere, in piccolo. |
| `income.py` | 176 | RENDITE — come si guadagna, in un pannello solo ('rendite', pulsante 💰 Rendite). |
| `inner_space.py` | 160 | LO SPAZIO INTERIORE — dalla bottiglietta di giada al MONDO INTERIORE. |
| `intrigue_data.py` | 1004 | LE TRAME — intrighi a più atti, scritti a mano, che il regista delle trame sceglie giorno per giorno. |
| `intrigue_data2.py` | 667 | ALTRE TRAME (Aggiornamento 58) — intrighi, tornei, corti, misteri e le loro conseguenze. |
| `intrigue_data3.py` | 496 | LE ANIME NEGLI OGGETTI (Aggiornamento 61) — i capitoli dei «vasi d'anima». |
| `intrigue_data4.py` | 290 | I COMPAGNI PERDUTI (Aggiornamento 67) — i capitoli della saga di chi è passato con te dal Varco. |
| `intrigue_data5.py` | 288 | NUOVE TRAME SCRITTE A MANO (Aggiornamento 71) — cattivi da ricordare, personaggi che ritornano. |
| `intrigue_variants.py` | 127 | VARIANTI DI TESTO DELLE TRAME (Aggiornamento 59). |
| `intrigues.py` | 879 | IL REGISTA DELLE TRAME — sceglie, giorno per giorno, il momento di storia più adatto. |
| `items.py` | 334 | Oggetti speciali — l'EREDITÀ materiale del mondo. |
| `karma.py` | 179 | Karma System (Fase 10). |
| `kingdoms.py` | 286 | REGNI E IMPERI — la politica dei mortali (e degli immortali che li governano). |
| `lifespan.py` | 82 | DURATA DELLA VITA (寿元). |
| `loot.py` | 237 | Bottino ed eredità — ciò che un caduto importante lascia sul campo. |
| `lost_companions.py` | 277 | I COMPAGNI PERDUTI (Aggiornamento 67) — chi è passato con te dal Varco del Cielo Spezzato. |
| `lost_legacy.py` | 202 | IL RETAGGIO SPEZZATO — ciò che ti è stato tolto, e che ti riprendi pezzo dopo pezzo. |
| `lower_world.py` | 240 | IL MONDO DI SOTTO TI PREGA (Aggiornamento 63). |
| `maintenance.py` | 38 | MANUTENZIONE — il salvataggio non deve crescere all'infinito. |
| `market.py` | 146 | Il MERCATO delle pietre spirituali. |
| `master_plot.py` | 522 | LA TRAMA MAESTRA — una storia sola, dal primo giorno a tutti i mondi, senza un nemico finale. |
| `memory.py` | 155 | Memory System (Fase 8). |
| `mentor_ring.py` | 421 | IL MAESTRO NELL'ANELLO — l'anima di un antico coltivatore che vive in un anello. |
| `menus.py` | 148 | MENU A SEZIONI — un posto solo per ogni parte del gioco, con le azioni già pronte. |
| `meridians.py` | 314 | I MERIDIANI (Aggiornamento 67) — aprirli uno a uno, poi temprarli senza fine. |
| `minigame.py` | 48 | I MINIGIOCHI DI MANO (Aggiornamento 71) — la forgia e il calderone non sono più solo un clic. |
| `mounts.py` | 85 | CAVALCATURE (Aggiornamento 63) — monti la tua bestia invece di farla combattere accanto a te. |
| `moves.py` | 154 | Mosse attive in combattimento. |
| `names.py` | 157 | I NOMI — mai più «Bai Cheng44» o «Landa Proibita di Drago62». |
| `npc_factory.py` | 148 | Creazione di NPC "di storia" (compagni, maestri, nemesi, personaggi degli incontri). |
| `npc_memory.py` | 227 | I PERSONAGGI RICORDANO (Aggiornamento 70) — senza bisogno del modello linguistico. |
| `npc_quests.py` | 300 | INCARICHI A CATENA — le richieste delle persone che incontri. |
| `oaths.py` | 232 | GIURAMENTI: FRATELLANZA GIURATA (结拜) e COMPAGNO DEL DAO (道侣). |
| `own_sect.py` | 402 | DISCEPOLI e la TUA SETTA. |
| `perception.py` | 175 | Percezione dell'avversario. |
| `place_actions.py` | 80 | COSA PUOI FARE QUI — le azioni del luogo come tessere (per la dashboard). |
| `power.py` | 106 | Potenza Effettiva Totale e CLASSI di combattimento. |
| `power_budget.py` | 183 | IL BILANCIO DELLA POTENZA — tante fonti, una forza sola. |
| `power_report.py` | 124 | IL RAPPORTO SULLA FORZA (Aggiornamento 70) — la scheda «⚖ Forza» della Via, più chiara. |
| `prodigies.py` | 183 | RIVALI CHE VIVONO DAVVERO — i PRODIGI della tua generazione, e le cronache del mondo. |
| `professions.py` | 539 | PROFESSIONI — Alchimia, Talismani, Forgia. |
| `progression.py` | 100 | Due vie di crescita. |
| `puppets.py` | 172 | MARIONETTE (傀儡) e TESORI MAGICI LEGATI AL SANGUE (本命法宝). |
| `pursuers.py` | 161 | Chi ti insegue cresce con te. |
| `qi.py` | 74 | Qi — l'energia per le MOSSE attive in combattimento. |
| `qol.py` | 250 | QUALITÀ DI VITA: salvataggi, mappa, colori, codex, tutorial. |
| `race_realms.py` | 636 | I REGNI DELLE RAZZE ANTICHE — campioni, sangue d'alto lignaggio, reliquie, e la scala che porta |
| `races.py` | 196 | LE RAZZE ANTICHE — popoli, non mostri. |
| `rankings.py` | 128 | CLASSIFICHE DEL CIELO (天榜) — chi è il più forte sotto il Cielo? |
| `rebirth.py` | 638 | MORTE → EPILOGO → REINCARNAZIONE nello stesso mondo. |
| `relations.py` | 107 | Relazioni NPC <-> giocatore (Fase 2, base). |
| `reports.py` | 31 | Coda di report differiti. |
| `reputation.py` | 239 | Reputazione — lo strato SOCIALE: come il mondo ti vede. |
| `rewards.py` | 164 | PREMI — un solo generatore per tornei, eredità, gratitudine, saghe. |
| `seasons.py` | 200 | LE STAGIONI E I GRANDI TRAGUARDI (Aggiornamento 70) — un obiettivo anche quando hai già tutto. |
| `seclusion.py` | 186 | RITIRO A PORTE CHIUSE (闭关), ILLUMINAZIONI e VITTORIE AL LIMITE. |
| `secret_masters.py` | 611 | MAESTRI SEGRETI — chi raggiunge certe vette in un'arte attira chi la padroneggia. |
| `secret_realms.py` | 217 | REAMI SEGRETI (秘境) — luoghi che si aprono per pochi giorni e poi si richiudono. |
| `sect_invasion.py` | 202 | INVASIONI GUIDATE (end-game). |
| `sect_life.py` | 355 | Vita di setta: il loop di competizione. |
| `sect_menu.py` | 606 | IL MENU DELLA SETTA e l'ASCESA alle sette superiori. |
| `sect_politics.py` | 253 | POLITICA INTERNA DELLA SETTA: anziani, bacheca delle missioni, intrighi. |
| `sect_war.py` | 271 | Guerre tra sette. |
| `sects.py` | 354 | Sette (strato "agenzia del giocatore"). |
| `shops.py` | 163 | TUTTO A UN CLIC — mercato, casa d'aste, ricette e bacheca come menu con pulsanti. |
| `soul_arcs.py` | 214 | GLI ARCHI DEI VASI D'ANIMA (Aggiornamento 61) — le storie che vivono dentro gli oggetti. |
| `soul_artifacts.py` | 590 | ALTRI VASI D'ANIMA (Aggiornamento 61) — oggetti con un'anima dentro, oltre all'anello. |
| `soul_roam.py` | 240 | IL VIAGGIO DELL'ANIMA e le DUE MEDITAZIONI (Aggiornamento 63). |
| `soul_temper.py` | 142 | TEMPRA DELLO SPIRITO (炼神) — la terza via di coltivazione, accanto al Qi e al Dao. |
| `soul_war.py` | 98 | BATTAGLIE DELL'ANIMA e la BANDIERA DELLE ANIME. |
| `spirit.py` | 85 | Spirito — l'energia per le TECNICHE DAO (la via del Guerriero Dao). |
| `spirit_roots.py` | 442 | RADICI SPIRITUALI (灵根) — punteggi per elemento, talenti, e combinazioni. |
| `state.py` | 76 | Piccolo accesso tipizzato alla tabella chiave/valore `game_state`. |
| `stone_qi.py` | 169 | COLTIVARE CON LE PIETRE SPIRITUALI (Aggiornamento 66) — dove finiscono le pietre di troppo. |
| `storyline.py` | 567 | STORIA PERSONALE per origine + OBIETTIVI. |
| `suggestions.py` | 351 | AZIONI SUGGERITE — dopo ogni comando, 2–4 opzioni numerate e sensate per la situazione. |
| `supreme_body.py` | 255 | IL CORPO SUPREMO — quando il corpo leggendario e il sangue più alto diventano una cosa sola. |
| `svolte.py` | 319 | SVOLTE — i salti di QUALITÀ della via, non solo numeri che salgono. |
| `system_daily.py` | 150 | MISSIONE QUOTIDIANA DEL SISTEMA e RANGO DEL CACCIATORE (ispirati a «Solo Leveling»). |
| `system_quest.py` | 225 | IL SISTEMA (系统) — solo per l'origine «Trasmigratore col Sistema». |
| `technique_forge.py` | 559 | LA FUCINA DELLE TECNICHE (功法融合) — fondere due o più tecniche in una tecnica nuova, tutta tua. |
| `tenacity.py` | 56 | LA VOLONTÀ DEL MORTALE — chi nasce senza talento sale con la fatica. |
| `train_all.py` | 119 | ALLENAMENTO D'INSIEME — `train` (o solo `t`): un'unica sessione in cui fai crescere tutto. |
| `training.py` | 79 | Economia dell'allenamento. |
| `travel.py` | 264 | METE — comandi diretti per raggiungere ciò che conta, senza perdersi sulla mappa. |
| `treasury.py` | 120 | TESORI — un solo pannello per tutto ciò che porti con te e fai crescere. |
| `tribulation.py` | 209 | Tribolazioni dell'Abisso: resistenza e doni del fulmine. |
| `unlocks.py` | 137 | LO SBLOCCO PROGRESSIVO (Aggiornamento 67) — la dashboard si apre poco a poco. |
| `via_menu.py` | 141 | LA TUA VIA (Aggiornamento 59) — un pannello solo per tutto ciò che fa crescere il personaggio. |
| `weapon_spirit.py` | 322 | L'ARMA VIVA: esperienza, tempra, risveglio e SPIRITO DELL'ARMA (器灵) senza tetto. |
| `weapons.py` | 178 | Arma principale — la via marziale del personaggio. |
| `world_arcs.py` | 172 | ARCHI DI METÀ PARTITA — storie del MONDO, non solo della tua origine. |
| `world_events.py` | 335 | Eventi mondiali — invasioni. |
| `world_menus.py` | 467 | I menu del mondo: ARTI, REGNI, EVENTI e l'indice di tutti i menu (vedi menus.py). |
| `zones.py` | 192 | Zone tematiche. |

## engine/web

| file | righe | cosa fa |
|---|---:|---|
| `game.py` | 1060 | Il ponte tra la dashboard e il motore. |
| `server.py` | 216 | Server HTTP della dashboard — solo libreria standard (nessuna dipendenza da installare). |
