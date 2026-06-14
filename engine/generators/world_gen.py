"""
Generatore procedurale del mondo (Fase 1 — World Static).

Deterministico: stesso seed -> stesso mondo (filosofia di tracciabilità).
Genera: 1 mondo, 1 continente, N territori, cluster di location connesse su
griglia (N/S/E/W coerenti e reciproci), danger level per profondità, NPC statici.

NON genera ancora: fazioni, coltivazione, eventi (fasi successive).
Segue in forma ridotta l'ordine della spec sez. 25.

Coerenza del grafo: le location di un territorio nascono su una griglia 2D
(scaffold solo in memoria, non persistito). Le adiacenze di griglia danno
direzioni geometricamente coerenti e automaticamente reciproche. I territori
sono poi collegati da "rotte" (bridge) usando direzioni libere su entrambi i capi.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from engine.db import is_initialized, transaction, PROJECT_ROOT

# ---- direzioni ----
# delta (dx, dy) -> nome direzione. north = y+1.
_DELTA_TO_DIR = {(0, 1): "north", (0, -1): "south", (1, 0): "east", (-1, 0): "west"}
_OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}

# ---- pool nomi luoghi (deterministici via rng) ----
_PLACE_WORDS = ["Giada", "Pietra", "Nube", "Drago", "Loto", "Cenere", "Ferro",
                "Bruma", "Vento", "Gelo", "Aurora", "Sangue", "Luna", "Pino"]

# tipi di location e modificatore di pericolo
_LOC_TYPE_DANGER = {"city": 0, "mountain": 1, "ruin": 2, "forbidden_zone": 3}
_LOC_TYPE_PREFIX = {
    "city": ["Villaggio di", "Borgo", "Città di"],
    "mountain": ["Monte", "Picco"],
    "ruin": ["Rovine di", "Tempio Caduto di"],
    "forbidden_zone": ["Landa Proibita di", "Abisso di"],
}


@dataclass
class WorldGenConfig:
    seed: int | None = 42
    world_name: str = "Jade Realm"
    continent_name: str = "Mondo Mortale"
    territories: int = 3
    locations_per_territory_min: int = 4
    locations_per_territory_max: int = 7
    factions: int = 4
    static_npc_count: int = 8

    @classmethod
    def load(cls, path: Path | str | None = None) -> "WorldGenConfig":
        path = Path(path) if path else PROJECT_ROOT / "config" / "world_config.yaml"
        if not path.exists():
            return cls()
        try:
            import yaml
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            return cls()
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in data.items() if k in known})


# ============================================================
# Carving del cluster su griglia
# ============================================================

def _carve_cluster(rng: random.Random, n: int) -> set[tuple[int, int]]:
    """Cresce in modo connesso n celle a partire da (0,0)."""
    cells: set[tuple[int, int]] = {(0, 0)}
    guard = 0
    while len(cells) < n and guard < n * 50:
        guard += 1
        cx, cy = rng.choice(list(cells))
        dirs = list(_DELTA_TO_DIR.keys())
        rng.shuffle(dirs)
        for dx, dy in dirs:
            nc = (cx + dx, cy + dy)
            if nc not in cells:
                cells.add(nc)
                break
    return cells


def _edges_for_cluster(cells: set[tuple[int, int]]) -> list[tuple[tuple, str, tuple]]:
    """Tutte le adiacenze di griglia come archi (from_cell, direction, to_cell)."""
    edges = []
    for (x, y) in cells:
        for (dx, dy), direction in _DELTA_TO_DIR.items():
            nc = (x + dx, y + dy)
            if nc in cells:
                edges.append(((x, y), direction, nc))
    return edges


# ============================================================
# Generazione
# ============================================================

def generate(conn: sqlite3.Connection, cfg: WorldGenConfig | None = None) -> None:
    cfg = cfg or WorldGenConfig.load()
    rng = random.Random(cfg.seed)
    used_place_names: set[str] = set()

    # Step 1 — Mondo
    conn.execute(
        "INSERT INTO worlds (id, name, description, current_year, current_tick) "
        "VALUES (1, ?, 'Un mondo di coltivatori.', 1, 0);",
        (cfg.world_name,),
    )

    # Step 2 — Continente
    cur = conn.execute(
        "INSERT INTO regions (world_id, name, region_type) VALUES (1, ?, 'continent');",
        (cfg.continent_name,),
    )
    continent_id = cur.lastrowid

    # tiene, per ogni territorio, i location_id e il loro grado libero di direzioni
    territory_locs: list[list[int]] = []
    free_dirs: dict[int, set[str]] = {}     # location_id -> direzioni ancora libere
    start_location_id: int | None = None

    # Step 3-4 — Territori e location
    for t_idx in range(cfg.territories):
        t_name = f"Territorio {_unique_place(rng, used_place_names)}"
        cur = conn.execute(
            "INSERT INTO regions (world_id, name, region_type, parent_region_id) "
            "VALUES (1, ?, 'territory', ?);",
            (t_name, continent_id),
        )
        region_id = cur.lastrowid

        n = rng.randint(cfg.locations_per_territory_min, cfg.locations_per_territory_max)
        cells = _carve_cluster(rng, n)
        cell_to_id: dict[tuple[int, int], int] = {}

        # crea le location
        for cell in sorted(cells):
            is_start = (start_location_id is None and cell == (0, 0) and t_idx == 0)
            if is_start:
                ltype = "city"
            else:
                ltype = rng.choices(
                    ["city", "mountain", "ruin", "forbidden_zone"],
                    weights=[5, 3, 2, 1],
                )[0]
            name = _location_name(rng, ltype, used_place_names)
            danger = 1 if is_start else _danger_for(t_idx, ltype, rng)
            desc = _location_desc(ltype)
            cur = conn.execute(
                "INSERT INTO locations (region_id, name, location_type, danger_level, description) "
                "VALUES (?, ?, ?, ?, ?);",
                (region_id, name, ltype, danger, desc),
            )
            loc_id = cur.lastrowid
            cell_to_id[cell] = loc_id
            free_dirs[loc_id] = {"north", "south", "east", "west"}
            if is_start:
                start_location_id = loc_id

        # connessioni interne (griglia: reciproche automaticamente)
        for from_cell, direction, to_cell in _edges_for_cluster(cells):
            a, b = cell_to_id[from_cell], cell_to_id[to_cell]
            conn.execute(
                "INSERT OR IGNORE INTO location_connections "
                "(from_location_id, to_location_id, direction) VALUES (?, ?, ?);",
                (a, b, direction),
            )
            free_dirs[a].discard(direction)

        territory_locs.append(list(cell_to_id.values()))

    # Step 4b — Bridge tra territori consecutivi (mondo unico grafo connesso)
    for i in range(len(territory_locs) - 1):
        _bridge_territories(conn, rng, territory_locs[i], territory_locs[i + 1], free_dirs)

    # fallback: garantisce start
    if start_location_id is None:
        start_location_id = territory_locs[0][0]
        conn.execute(
            "UPDATE locations SET location_type='city', danger_level=1 WHERE id=?;",
            (start_location_id,),
        )

    all_locs = [l for terr in territory_locs for l in terr]

    # Step 6 — Fazioni (sede, territorio, leader, relazioni)
    from engine.generators import faction_gen
    faction_gen.generate_factions(conn, rng, cfg.factions, all_locs)

    # Step 7 (ridotto) — NPC statici con archetipo + traits + membership (vedi npc_gen)
    from engine.generators import npc_gen
    npc_gen.generate_static_npcs(conn, rng, cfg.static_npc_count, all_locs)

    # Step 10 — Player
    conn.execute(
        "INSERT INTO players (id, name, location_id, status, created_tick) "
        "VALUES (1, 'Wanderer', ?, 'alive', 0);",
        (start_location_id,),
    )

    # Coltivazione (Fase 7): regni di riferimento + assegnazione a player e NPC
    from engine.generators import cultivation_gen
    cultivation_gen.seed_realms(conn)
    cultivation_gen.assign_cultivation(conn, rng)

    # Dao (v1): riferimento + Dao primario degli NPC (per l'assorbimento)
    from engine.generators import dao_gen
    dao_gen.seed_daos(conn)
    dao_gen.assign_npc_daos(conn, rng)

    # Ricercati: criminali con una taglia (avventure in città)
    from engine.systems import bounties
    bounties.seed_outlaws(conn, rng, n=5)

    # Creature selvagge (bestie/demoni/spiriti) nelle zone pericolose:
    # popolano il mondo da cacciare e assorbire (Abisso Divoratore).
    from engine.generators import creature_gen
    creature_gen.seed_creatures(conn, rng)
    # ogni setta ha una zona di caccia con mostri scalati al suo livello
    creature_gen.assign_hunt_zones(conn, rng)

    # ZONE TEMATICHE: alcune zone pericolose acquistano un'identità (Guerrieri Dao,
    # Maestri dell'Anima, Cultivatori del Corpo, ...) con abitanti di classi diverse
    # ma di forza equivalente.
    from engine.systems import zones
    zones.assign_zone_themes(conn, rng)


def _bridge_territories(conn, rng, locs_a, locs_b, free_dirs) -> None:
    """Collega due territori con una rotta, usando direzioni libere su entrambi i capi."""
    cand_a = [l for l in locs_a if free_dirs[l]]
    cand_b = [l for l in locs_b if free_dirs[l]]
    rng.shuffle(cand_a)
    rng.shuffle(cand_b)
    for a in cand_a:
        for b in cand_b:
            for d in list(free_dirs[a]):
                if _OPPOSITE[d] in free_dirs[b]:
                    conn.execute(
                        "INSERT OR IGNORE INTO location_connections "
                        "(from_location_id, to_location_id, direction) VALUES (?, ?, ?);",
                        (a, b, d),
                    )
                    conn.execute(
                        "INSERT OR IGNORE INTO location_connections "
                        "(from_location_id, to_location_id, direction) VALUES (?, ?, ?);",
                        (b, a, _OPPOSITE[d]),
                    )
                    free_dirs[a].discard(d)
                    free_dirs[b].discard(_OPPOSITE[d])
                    return



# ============================================================
# Helper nomi / pericolo
# ============================================================

def _unique_place(rng, used: set[str]) -> str:
    for _ in range(100):
        w = rng.choice(_PLACE_WORDS)
        if w not in used:
            used.add(w)
            return w
    # esauriti: aggiungi suffisso
    w = rng.choice(_PLACE_WORDS) + str(rng.randint(2, 99))
    used.add(w)
    return w


def _location_name(rng, ltype: str, used: set[str]) -> str:
    prefix = rng.choice(_LOC_TYPE_PREFIX[ltype])
    place = _unique_place(rng, used)
    return f"{prefix} {place}"


def _location_desc(ltype: str) -> str:
    return {
        "city": "Un insediamento di coltivatori e mortali.",
        "mountain": "Vette spazzate dal vento, ricche di qi.",
        "ruin": "Resti di un'epoca dimenticata.",
        "forbidden_zone": "Un luogo che i saggi evitano.",
    }[ltype]


def _danger_for(t_idx: int, ltype: str, rng) -> int:
    base = 1 + t_idx                      # territori più lontani = più pericolosi
    d = base + _LOC_TYPE_DANGER[ltype] + rng.randint(0, 1)
    return max(1, min(10, d))




# ============================================================
# Bootstrap
# ============================================================

def generate_if_empty(cfg: WorldGenConfig | None = None) -> bool:
    """Genera il mondo solo se il DB è vuoto. Ritorna True se ha generato."""
    if is_initialized():
        return False
    with transaction() as conn:
        generate(conn, cfg)
    return True
