-- JADE IMMORTAL — Schema completo (forward-compatible)
-- Creato interamente alla Fase 0 per evitare ALTER TABLE nelle fasi successive.
-- SQLite permette forward-reference nelle FK (verificate solo a runtime con PRAGMA foreign_keys=ON),
-- quindi l'ordine di creazione con riferimenti circolari (factions<->npcs) non è un problema.

PRAGMA foreign_keys = ON;

-- ============================================================
-- 6.1 GEOGRAFIA
-- ============================================================
CREATE TABLE IF NOT EXISTS worlds (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    current_year INTEGER DEFAULT 1,
    current_tick INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS regions (
    id INTEGER PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id),
    name TEXT NOT NULL,
    region_type TEXT,
    parent_region_id INTEGER REFERENCES regions(id),
    description TEXT
);

CREATE TABLE IF NOT EXISTS locations (
    id INTEGER PRIMARY KEY,
    region_id INTEGER REFERENCES regions(id),
    name TEXT NOT NULL,
    location_type TEXT,
    danger_level INTEGER DEFAULT 1,
    owner_faction_id INTEGER REFERENCES factions(id),
    description TEXT
);

-- AGGIUNTA (non presente nello spec): grafo di adiacenza tra location.
-- Necessaria dalla Fase 1 per il movimento N/S/E/W. Direzionale: una riga per direzione.
CREATE TABLE IF NOT EXISTS location_connections (
    id INTEGER PRIMARY KEY,
    from_location_id INTEGER NOT NULL REFERENCES locations(id),
    to_location_id   INTEGER NOT NULL REFERENCES locations(id),
    direction TEXT NOT NULL,          -- north, south, east, west (estendibile: up/down)
    travel_ticks INTEGER DEFAULT 1,
    UNIQUE(from_location_id, direction)
);

-- ============================================================
-- 6.2 FAZIONI
-- ============================================================
CREATE TABLE IF NOT EXISTS factions (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    leader_id INTEGER,
    home_location_id INTEGER REFERENCES locations(id),
    influence INTEGER DEFAULT 50,
    wealth INTEGER DEFAULT 50,
    description TEXT,
    goals TEXT,
    tier INTEGER DEFAULT 1,               -- livello della setta (1 Regionale .. 6 Celeste)
    element TEXT,                          -- Dao affine: chi vi appartiene lo comprende più in fretta
    hunt_zone_id INTEGER REFERENCES locations(id),  -- zona di caccia (mostri scalati al livello)
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS faction_relations (
    id INTEGER PRIMARY KEY,
    faction_a INTEGER REFERENCES factions(id),
    faction_b INTEGER REFERENCES factions(id),
    relation_score INTEGER DEFAULT 0,
    relation_type TEXT,
    reason TEXT,
    last_updated_tick INTEGER,
    UNIQUE(faction_a, faction_b)
);

-- ============================================================
-- 6.3 NPC
-- ============================================================
CREATE TABLE IF NOT EXISTS npcs (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    age INTEGER,
    realm_id INTEGER REFERENCES cultivation_realms(id),
    faction_id INTEGER REFERENCES factions(id),
    location_id INTEGER REFERENCES locations(id),
    status TEXT DEFAULT 'alive',
    description TEXT,
    -- AGGIUNTA (non nello spec): archetipo dell'NPC (anziano, mercante, eremita...).
    -- Guida la generazione dei traits (Fase 2) e le decisioni NPC (Fase 15).
    archetype TEXT,
    kind TEXT DEFAULT 'human',         -- human | beast | demon | spirit
    event_id INTEGER,                  -- se appartiene all'ondata di un evento mondiale
    hunting INTEGER DEFAULT 0,         -- 1 = dà attivamente la caccia al giocatore (Eretico)
    birth_tick INTEGER,
    death_tick INTEGER,
    -- AGGIUNTA (non nello spec): ultimo tick in cui l'NPC è stato simulato.
    -- Abilita la batch/catch-up simulation per gli NPC fuori dallo scope attivo
    -- (Active Simulation Scope). Default 0; usato dalla Fase 3 in poi.
    last_active_tick INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS npc_traits (
    npc_id INTEGER PRIMARY KEY REFERENCES npcs(id),
    ambition INTEGER DEFAULT 50,
    honor INTEGER DEFAULT 50,
    greed INTEGER DEFAULT 50,
    courage INTEGER DEFAULT 50,
    loyalty INTEGER DEFAULT 50,
    compassion INTEGER DEFAULT 50,
    pride INTEGER DEFAULT 50
);

CREATE TABLE IF NOT EXISTS npc_goals (
    id INTEGER PRIMARY KEY,
    npc_id INTEGER REFERENCES npcs(id),
    goal TEXT NOT NULL,
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'active',
    deadline_tick INTEGER
);

CREATE TABLE IF NOT EXISTS npc_relationships (
    id INTEGER PRIMARY KEY,
    source_npc INTEGER REFERENCES npcs(id),
    target_npc INTEGER REFERENCES npcs(id),
    score INTEGER DEFAULT 0,
    relationship_type TEXT,
    last_updated_tick INTEGER,
    UNIQUE(source_npc, target_npc)
);

-- AGGIUNTA (non nello spec): disposizione di un NPC verso il giocatore.
-- npc_relationships lega solo NPC<->NPC; il player non è un NPC.
CREATE TABLE IF NOT EXISTS npc_player_relations (
    id INTEGER PRIMARY KEY,
    npc_id INTEGER NOT NULL REFERENCES npcs(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    score INTEGER DEFAULT 0,                       -- -100..100
    relationship_type TEXT DEFAULT 'stranger',     -- stranger, acquaintance, friend, rival, enemy
    last_updated_tick INTEGER,
    UNIQUE(npc_id, player_id)
);

-- ============================================================
-- 6.4 GIOCATORE
-- ============================================================
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    realm_id INTEGER REFERENCES cultivation_realms(id),
    location_id INTEGER REFERENCES locations(id),
    faction_id INTEGER REFERENCES factions(id),
    status TEXT DEFAULT 'alive',
    created_tick INTEGER DEFAULT 0
);

-- ============================================================
-- 6.5 COLTIVAZIONE
-- ============================================================
CREATE TABLE IF NOT EXISTS cultivation_paths (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    compatible_with TEXT
);

CREATE TABLE IF NOT EXISTS cultivation_realms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    tier INTEGER NOT NULL,
    qi_requirement INTEGER,
    body_requirement INTEGER,
    soul_requirement INTEGER,
    dao_requirement INTEGER
);

CREATE TABLE IF NOT EXISTS cultivation_records (
    id INTEGER PRIMARY KEY,
    character_id INTEGER NOT NULL,
    character_type TEXT NOT NULL,
    realm_id INTEGER REFERENCES cultivation_realms(id),
    progress REAL DEFAULT 0.0,
    stage INTEGER DEFAULT 1,
    qi_level INTEGER DEFAULT 0,
    body_level INTEGER DEFAULT 0,
    soul_level INTEGER DEFAULT 0,
    dao_understanding INTEGER DEFAULT 0,
    breakthrough_tick INTEGER
);

-- ============================================================
-- 6.6 TECNICHE
-- ============================================================
CREATE TABLE IF NOT EXISTS techniques (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    element TEXT,
    intent TEXT,
    method TEXT,
    tier TEXT,
    description TEXT,
    is_procedural INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS npc_techniques (
    npc_id INTEGER REFERENCES npcs(id),
    technique_id INTEGER REFERENCES techniques(id),
    mastery INTEGER DEFAULT 1,
    PRIMARY KEY (npc_id, technique_id)
);

CREATE TABLE IF NOT EXISTS player_techniques (
    player_id INTEGER REFERENCES players(id),
    technique_id INTEGER REFERENCES techniques(id),
    mastery INTEGER DEFAULT 1,
    PRIMARY KEY (player_id, technique_id)
);

-- ============================================================
-- 6.7 OGGETTI
-- ============================================================
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    item_type TEXT,
    rarity TEXT,
    description TEXT,
    effects TEXT
);

CREATE TABLE IF NOT EXISTS inventories (
    id INTEGER PRIMARY KEY,
    owner_type TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    item_id INTEGER REFERENCES items(id),
    quantity INTEGER DEFAULT 1
);

-- ============================================================
-- 6.8 EVENTI E CONSEGUENZE
-- ============================================================
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    event_type TEXT,
    tick INTEGER NOT NULL,
    location_id INTEGER REFERENCES locations(id),
    status TEXT DEFAULT 'resolved',
    summary TEXT
);

CREATE TABLE IF NOT EXISTS event_participants (
    event_id INTEGER REFERENCES events(id),
    participant_type TEXT NOT NULL,
    participant_id INTEGER NOT NULL,
    role TEXT,
    PRIMARY KEY (event_id, participant_type, participant_id)
);

CREATE TABLE IF NOT EXISTS consequences (
    id INTEGER PRIMARY KEY,
    event_id INTEGER REFERENCES events(id),
    target_type TEXT,
    target_id INTEGER,
    consequence_type TEXT,
    visibility TEXT DEFAULT 'hidden',
    description TEXT,
    resolved INTEGER DEFAULT 0,
    resolve_tick INTEGER
);

-- ============================================================
-- 6.9 CONOSCENZA E VOCI
-- ============================================================
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY,
    owner_type TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    information TEXT NOT NULL,
    certainty INTEGER DEFAULT 100,
    source TEXT,
    acquired_tick INTEGER
);

CREATE TABLE IF NOT EXISTS rumors (
    id INTEGER PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    text TEXT NOT NULL,
    truthfulness INTEGER DEFAULT 100,
    spread_level INTEGER DEFAULT 1,
    origin_event_id INTEGER REFERENCES events(id),
    created_tick INTEGER
);

-- ============================================================
-- 6.10 CRONACHE E SIMULAZIONE
-- ============================================================
CREATE TABLE IF NOT EXISTS chronicles (
    id INTEGER PRIMARY KEY,
    period_start_tick INTEGER,
    period_end_tick INTEGER,
    title TEXT,
    summary TEXT,
    obsidian_path TEXT
);

CREATE TABLE IF NOT EXISTS simulation_ticks (
    id INTEGER PRIMARY KEY,
    world_id INTEGER REFERENCES worlds(id),
    tick_number INTEGER NOT NULL,
    timestamp TEXT,
    events_processed INTEGER DEFAULT 0,
    npcs_acted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pending_actions (
    id INTEGER PRIMARY KEY,
    actor_type TEXT NOT NULL,
    actor_id INTEGER NOT NULL,
    action_type TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    scheduled_tick INTEGER NOT NULL,
    priority INTEGER DEFAULT 5,
    context TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS save_games (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT,
    world_tick INTEGER,
    snapshot_path TEXT
);

-- ============================================================
-- 6.11 KARMA
-- ============================================================
CREATE TABLE IF NOT EXISTS karma_records (
    id INTEGER PRIMARY KEY,
    character_type TEXT NOT NULL,
    character_id INTEGER NOT NULL,
    karma_score INTEGER DEFAULT 0,
    positive_sources TEXT,
    negative_sources TEXT,
    last_updated_tick INTEGER,
    UNIQUE(character_type, character_id)
);

-- ============================================================
-- 6.12 RISORSE
-- ============================================================
CREATE TABLE IF NOT EXISTS resource_nodes (
    id INTEGER PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    resource_type TEXT NOT NULL,
    resource_name TEXT NOT NULL,
    quality INTEGER DEFAULT 1,
    quantity INTEGER DEFAULT 100,
    regeneration_rate INTEGER DEFAULT 1,
    controller_faction_id INTEGER REFERENCES factions(id),
    last_harvested_tick INTEGER
);

CREATE TABLE IF NOT EXISTS resources (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    resource_type TEXT,
    grade INTEGER DEFAULT 1,
    description TEXT
);

CREATE TABLE IF NOT EXISTS resource_stockpiles (
    id INTEGER PRIMARY KEY,
    owner_type TEXT NOT NULL,
    owner_id INTEGER NOT NULL,
    resource_id INTEGER REFERENCES resources(id),
    quantity INTEGER DEFAULT 0
);

-- ============================================================
-- 6.13 PERCEZIONE
-- ============================================================
CREATE TABLE IF NOT EXISTS perception_stats (
    id INTEGER PRIMARY KEY,
    character_type TEXT NOT NULL,
    character_id INTEGER NOT NULL,
    sight_range INTEGER DEFAULT 1,
    spiritual_sense_range INTEGER DEFAULT 0,
    investigation INTEGER DEFAULT 10,
    intuition INTEGER DEFAULT 10,
    disguise_penetration INTEGER DEFAULT 0
);

-- ============================================================
-- 6.14 TRIBOLAZIONI
-- ============================================================
CREATE TABLE IF NOT EXISTS tribulations (
    id INTEGER PRIMARY KEY,
    character_type TEXT NOT NULL,
    character_id INTEGER NOT NULL,
    tribulation_type TEXT NOT NULL,
    trigger_event TEXT,
    intensity INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending',
    scheduled_tick INTEGER,
    resolved_tick INTEGER,
    outcome TEXT
);

-- AGGIUNTA (non nello spec): ferite attive da combattimento (Fase 6).
-- Riducono la potenza di combattimento finché non guariscono (heal_tick).
CREATE TABLE IF NOT EXISTS injuries (
    id INTEGER PRIMARY KEY,
    character_type TEXT NOT NULL,    -- 'npc' | 'player'
    character_id INTEGER NOT NULL,
    severity INTEGER NOT NULL,       -- 1..10
    description TEXT,
    inflicted_tick INTEGER,
    healed INTEGER DEFAULT 0,
    heal_tick INTEGER
);

-- AGGIUNTA (Fondamenta del Personaggio): profilo del giocatore.
-- Le affinità sono NUMERI INTERNI (mai mostrati grezzi: il display è qualitativo).
CREATE TABLE IF NOT EXISTS character_profiles (
    id INTEGER PRIMARY KEY,
    character_type TEXT NOT NULL,        -- 'player' (npc in futuro)
    character_id INTEGER NOT NULL,
    origin TEXT NOT NULL,
    age INTEGER,
    aff_cultivation INTEGER DEFAULT 50,
    aff_body INTEGER DEFAULT 50,
    aff_qi INTEGER DEFAULT 50,
    aff_soul INTEGER DEFAULT 50,
    aff_combat INTEGER DEFAULT 50,
    anomaly TEXT,                        -- es. 'abisso_divoratore' (categoria a sé)
    soul_residue INTEGER DEFAULT 0,      -- accumulo da assorbimenti = CORRUZIONE dell'Abisso
    grow_strength INTEGER DEFAULT 0,     -- crescita fisica da assorbimento (bestie)
    grow_vitality INTEGER DEFAULT 0,
    grow_resistance INTEGER DEFAULT 0,
    grow_aura INTEGER DEFAULT 0,         -- aggressività/aura (demoni)
    grow_soul INTEGER DEFAULT 0,         -- anima (spiriti)
    abs_beast INTEGER DEFAULT 0,         -- conteggi per "linea evolutiva"
    abs_demon INTEGER DEFAULT 0,
    abs_spirit INTEGER DEFAULT 0,
    abs_human INTEGER DEFAULT 0,
    fame INTEGER DEFAULT 0,               -- reputazione sociale: gloria pubblica
    infamy INTEGER DEFAULT 0,             -- disonore pubblico
    suspicion INTEGER DEFAULT 0,          -- sospetto sull'Abisso
    disguised INTEGER DEFAULT 0,          -- 1 = maschera indossata (in incognito)
    weapon TEXT,                          -- arma principale scelta in setta (sblocca il Dao d'arma)
    qi_current INTEGER DEFAULT -1,        -- Qi attuale per le mosse (-1 = non inizializzato => pieno)
    dao_sessions INTEGER DEFAULT 0,       -- quante volte hai allenato i Dao (via del Dao)
    cult_sessions INTEGER DEFAULT 0,      -- quante volte hai coltivato (via dell'Universo)
    flags TEXT,                          -- JSON: trade-off dell'origine
    created_tick INTEGER DEFAULT 0,
    UNIQUE(character_type, character_id)
);

-- Dao: classificati su 3 livelli (narrative/systemic/deep). Riferimento.
CREATE TABLE IF NOT EXISTS daos (
    id INTEGER PRIMARY KEY,
    dao_key TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    level TEXT NOT NULL,                 -- narrative | systemic | deep
    description TEXT
);

-- Rapporto personaggio<->Dao: affinità (talento latente, NASCOSTO) e comprensione reale.
CREATE TABLE IF NOT EXISTS character_daos (
    id INTEGER PRIMARY KEY,
    character_type TEXT NOT NULL,
    character_id INTEGER NOT NULL,
    dao_key TEXT NOT NULL,
    affinity INTEGER DEFAULT 50,         -- quanto facilmente lo impari (nascosto)
    comprehension INTEGER DEFAULT 0,     -- padronanza reale 0..100
    practiced INTEGER DEFAULT 0,
    UNIQUE(character_type, character_id, dao_key)
);

-- ============================================================
-- INDICI (query frequenti: chi è in questa location?)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_npcs_location   ON npcs(location_id);
CREATE INDEX IF NOT EXISTS idx_npcs_faction    ON npcs(faction_id);
CREATE INDEX IF NOT EXISTS idx_events_tick     ON events(tick);
CREATE INDEX IF NOT EXISTS idx_conn_from       ON location_connections(from_location_id);
CREATE INDEX IF NOT EXISTS idx_injuries_char    ON injuries(character_type, character_id, healed);
CREATE INDEX IF NOT EXISTS idx_ep_participant   ON event_participants(participant_type, participant_id);
CREATE INDEX IF NOT EXISTS idx_character_daos    ON character_daos(character_type, character_id);

-- ============================================================
-- SETTE, RISORSE, ATTIVITÀ GIORNALIERA (strato "agenzia del giocatore")
-- ============================================================
CREATE TABLE IF NOT EXISTS sect_memberships (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    faction_id INTEGER NOT NULL REFERENCES factions(id),
    rank TEXT NOT NULL,
    rank_level INTEGER DEFAULT 1,
    grade TEXT,                          -- "radici spirituali" emerse dal test
    class_tier INTEGER DEFAULT 1,        -- regno della classe attuale
    class_rank INTEGER,                  -- piazzamento nell'ultima sfida/torneo
    merit INTEGER DEFAULT 0,             -- punti merito accumulati per QUESTA setta
    joined_tick INTEGER DEFAULT 0,
    UNIQUE(player_id)
);

-- Tecniche segrete apprese (spendendo merito). Restano tue per sempre.
CREATE TABLE IF NOT EXISTS learned_techniques (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    faction_id INTEGER,                  -- setta da cui l'hai appresa
    tech_key TEXT NOT NULL,              -- "faction_id:rank"
    name TEXT NOT NULL,
    magnitude REAL DEFAULT 0,            -- bonus % alla potenza
    learned_tick INTEGER DEFAULT 0,
    UNIQUE(player_id, tech_key)
);

-- Inviti delle sette superiori (i "7 rappresentanti" dopo un torneo vinto).
-- Sono dati leggeri: la fazione reale nasce solo quando il giocatore accetta.
CREATE TABLE IF NOT EXISTS sect_invitations (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    slot INTEGER NOT NULL,               -- 1..7 (numero scelto dal giocatore)
    name TEXT NOT NULL,
    tier INTEGER NOT NULL,
    element TEXT,
    hint TEXT,
    created_tick INTEGER DEFAULT 0,
    resolved INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS player_resources (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    resource TEXT NOT NULL,
    amount INTEGER DEFAULT 0,
    UNIQUE(player_id, resource)
);

CREATE TABLE IF NOT EXISTS daily_activity (
    id INTEGER PRIMARY KEY,
    character_type TEXT NOT NULL,
    character_id INTEGER NOT NULL,
    day INTEGER NOT NULL,
    cultivation_sessions INTEGER DEFAULT 0,
    UNIQUE(character_type, character_id, day)
);

-- compagni di classe (rivali) del giocatore nella setta
CREATE TABLE IF NOT EXISTS sect_cohort (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    npc_id INTEGER NOT NULL REFERENCES npcs(id),
    faction_id INTEGER NOT NULL,
    class_tier INTEGER NOT NULL,
    UNIQUE(player_id, npc_id)
);

-- eventi di setta programmati nel tempo (sfide, tornei)
CREATE TABLE IF NOT EXISTS sect_events (
    id INTEGER PRIMARY KEY,
    player_id INTEGER NOT NULL,
    faction_id INTEGER NOT NULL,
    kind TEXT NOT NULL,                  -- 'ranking_challenge' | 'monthly_tournament'
    fire_tick INTEGER NOT NULL,
    resolved INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_sect_events ON sect_events(player_id, resolved, fire_tick);

-- ricercati: criminali con una taglia (missioni di caccia)
CREATE TABLE IF NOT EXISTS game_state (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Eventi mondiali: invasioni (maree di bestie / incursioni demoniache) che colpiscono
-- un luogo. Il giocatore può difenderlo o ignorarlo (conseguenze alla scadenza).
CREATE TABLE IF NOT EXISTS world_events (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL,                  -- beast_tide | demon_incursion
    location_id INTEGER REFERENCES locations(id),
    threat INTEGER DEFAULT 1,            -- tier della minaccia
    status TEXT DEFAULT 'active',        -- active | repelled | lost
    started_tick INTEGER DEFAULT 0,
    deadline_tick INTEGER DEFAULT 0,
    wave_total INTEGER DEFAULT 0,
    wave_remaining INTEGER DEFAULT 0
);


CREATE TABLE IF NOT EXISTS outlaws (
    id INTEGER PRIMARY KEY,
    npc_id INTEGER NOT NULL REFERENCES npcs(id),
    crime TEXT NOT NULL,
    reward INTEGER DEFAULT 50,
    faction_id INTEGER,                  -- chi ha emesso la taglia (può essere NULL)
    notoriety INTEGER DEFAULT 1,
    resolved INTEGER DEFAULT 0,
    UNIQUE(npc_id)
);
