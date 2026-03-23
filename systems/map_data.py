# systems/map_data.py
# -------------------------------------------------
# Definición, generación y carga de mapas.
# Soporta:
#   - grid_generator: genera el mapa proceduralmente
#   - ally_spawns: aliados fijos por ID
#   - enemy_spawns: posiciones para enemigos aleatorios por dificultad
#   - ENEMY_POOLS: pool por tier de dificultad

import random
from dataclasses import dataclass
from typing import Dict, List, Tuple

import constants as C
from loaders.data_loader import load_maps

GRILLA_ANCHO = C.GRILLA_ANCHO   # 25
GRILLA_ALTO  = C.GRILLA_ALTO    # 18

Coord = Tuple[int, int]


# =================================================
# POOLS DE ENEMIGOS POR DIFICULTAD
# =================================================
# Se selecciona el tier según el número de mapa alcanzado.
# game_state llama a pick_enemies_for_difficulty(tier, positions).

ENEMY_POOLS: Dict[str, List[str]] = {
    "easy":   ["BANDIT_ENEMY", "GOBLIN_SPEAR", "GOBLIN_CLUB",    "SLIME"],
    "medium": ["ORC_ENEMY",    "MAGE_ENEMY",   "PIRATE_CAPTAIN", "GOBLIN_ARCHER", "SKELETON_SOLDIER"],
    "hard":   ["MINOTAUR",     "ORC_SHAMAN",   "PIRATE_GUNNER",  "NECROMANCER",   "DEMON_RED"],
    "boss":   ["DEMON_RED",    "MAMMOTH",       "NECROMANCER",    "MINOTAUR"],
}

def get_difficulty_tier(map_number: int) -> str:
    """Retorna el tier de dificultad según cuántos mapas completó el jugador."""
    if map_number <= 1:  return "easy"
    elif map_number <= 3: return "medium"
    elif map_number <= 5: return "hard"
    else:                 return "boss"

def pick_enemies_for_difficulty(tier: str, positions: List[Coord],
                                 map_number: int) -> List[Tuple[str, Coord]]:
    """
    Asigna un unit_id aleatorio del pool al tier indicado a cada posición.
    A mayor map_number, mayor probabilidad de mezclar con el tier superior.
    Retorna lista de (unit_id, pos).
    """
    pool = list(ENEMY_POOLS.get(tier, ENEMY_POOLS["easy"]))
    # Mezcla suave: conforme avanza el jugador, algunos enemigos son del tier superior
    tiers = list(ENEMY_POOLS.keys())
    tier_idx = tiers.index(tier)
    upper_pool = ENEMY_POOLS[tiers[min(tier_idx + 1, len(tiers) - 1)]]

    result = []
    for pos in positions:
        # Probabilidad de spawnar del tier superior según map_number
        upper_chance = min(40, (map_number - 1) * 8)
        if random.randint(1, 100) <= upper_chance:
            chosen = random.choice(upper_pool)
        else:
            chosen = random.choice(pool)
        result.append((chosen, pos))
    return result


# =================================================
# DATA CLASSES
# =================================================

@dataclass(frozen=True)
class SpawnDef:
    unit_id: str
    bando:   str
    pos:     Coord


@dataclass(frozen=True)
class MapDef:
    name:        str
    grid:        List[List[int]]
    thrones:     Dict[str, Coord]
    spawns:      List[SpawnDef]          # aliados fijos
    enemy_positions: List[Coord]         # posiciones para enemigos aleatorios
    items_spawn: Dict[Coord, str]
    rules:       Dict[str, object]


# =================================================
# VALIDACIÓN
# =================================================

def _validate_grid(grid, name):
    if len(grid) != GRILLA_ALTO:
        raise ValueError(f"[{name}] grid altura inválida. Esperado {GRILLA_ALTO}, recibido {len(grid)}")
    for i, row in enumerate(grid):
        if len(row) != GRILLA_ANCHO:
            raise ValueError(f"[{name}] fila {i} ancho inválido. Esperado {GRILLA_ANCHO}, recibido {len(row)}")


def _validate_positions(m: MapDef):
    def ok(p):
        return 0 <= p[0] < GRILLA_ANCHO and 0 <= p[1] < GRILLA_ALTO
    for b, p in m.thrones.items():
        if not ok(p):
            raise ValueError(f"[{m.name}] Trono '{b}' fuera del mapa: {p}")
    for s in m.spawns:
        if not ok(s.pos):
            raise ValueError(f"[{m.name}] Spawn fuera del mapa: {s}")
    for p in m.items_spawn:
        if not ok(p):
            raise ValueError(f"[{m.name}] Item_spawn fuera del mapa: {p}")


# =================================================
# GENERADORES DE GRID
# =================================================

def _flat() -> List[List[int]]:
    return [[0] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]


def _gen_forest_pass() -> List[List[int]]:
    """Dos paredes de bosque verticales con brechas — chokepoint central."""
    g = _flat()
    # Pared izquierda (cols 7-9) y derecha (cols 15-17)
    for y in range(GRILLA_ALTO):
        for x in [7, 8, 9, 15, 16, 17]:
            g[y][x] = 1
    # Brechas en pared izquierda (filas 4-5 y 11-12)
    for y in range(4, 6):
        g[y][8] = 0; g[y][9] = 0
    for y in range(11, 13):
        g[y][7] = 0; g[y][8] = 0
    # Brechas en pared derecha (solo fila 8-9 — más difícil cruzar)
    for y in range(8, 10):
        g[y][15] = 0; g[y][16] = 0
    # Rocas que cortan pasos adicionales
    for x in range(10, 15):
        g[2][x] = 2
        g[15][x] = 2
    g[2][11] = 0; g[2][12] = 0   # paso superior
    g[15][12] = 0; g[15][13] = 0  # paso inferior
    # Bosque decorativo en lados
    for y in [1, 3, 7, 10, 14, 16]:
        g[y][4] = 1; g[y][20] = 1
    return g


def _gen_river_crossing() -> List[List[int]]:
    """Río vertical en el centro con 3 cruces estrechos."""
    g = _flat()
    # Río: cols 10-14, agua en su mayoría
    for y in range(GRILLA_ALTO):
        for x in range(10, 15):
            g[y][x] = 3
    # Tres cruces de un tile de ancho: filas 3, 9, 14
    for bridge_y in [3, 9, 14]:
        for x in range(10, 15):
            g[bridge_y][x] = 0
        # Solo uno de ancho real (col 12)
        for x in [10, 11, 13, 14]:
            g[bridge_y][x] = 3
    # Ampliar el cruce central a 2 tiles (col 11-12)
    g[9][11] = 0; g[9][12] = 0
    # Bosque en orillas
    for y in range(1, GRILLA_ALTO - 1):
        g[y][7] = 1; g[y][8] = 1
        g[y][16] = 1; g[y][17] = 1
    # Quitar bosque en filas de cruce para no bloquear
    for y in [3, 9, 14]:
        g[y][7] = 0; g[y][8] = 0
        g[y][16] = 0; g[y][17] = 0
    return g


def _gen_mountain_keep() -> List[List[int]]:
    """Cordillera horizontal con dos pasos — aliados en la parte baja."""
    g = _flat()
    # Cordillera: filas 7-10
    for y in range(7, 11):
        for x in range(GRILLA_ANCHO):
            g[y][x] = 2
    # Paso oeste (cols 4-5) y paso este (cols 18-19)
    for y in range(7, 11):
        g[y][4] = 0; g[y][5] = 0
        g[y][18] = 0; g[y][19] = 0
    # Muro de fortaleza enemiga en parte superior (filas 1-5, cols 16-23)
    for y in range(1, 6):
        g[y][16] = 2; g[y][23] = 2
    for x in range(16, 24):
        g[1][x] = 2; g[5][x] = 2
    # Entrada de la fortaleza
    g[5][19] = 0; g[5][20] = 0
    # Bosque en la parte inferior (zona aliada)
    for pos in [(6,13), (6,14), (10,13), (10,14), (3,11), (3,12)]:
        g[pos[0]][pos[1]] = 1
    # Pequeños bosques en parte superior
    for pos in [(2,8), (2,9), (3,8), (3,9)]:
        g[pos[0]][pos[1]] = 1
    return g


def _gen_fortress_siege() -> List[List[int]]:
    """Fortaleza enemiga en la esquina superior-derecha. Aliados asedian desde abajo."""
    g = _flat()
    # Fortaleza: muros exteriores (filas 0-7, cols 15-24)
    for x in range(15, 25):
        g[0][x] = 2; g[7][x] = 2
    for y in range(0, 8):
        g[y][15] = 2; g[y][24] = 2
    # Entrada de la fortaleza (fila 7, cols 19-20)
    g[7][19] = 0; g[7][20] = 0
    # Paredes interiores de la fortaleza
    for x in range(17, 23):
        g[3][x] = 2
    g[3][19] = 0; g[3][20] = 0
    # Bosque de aproximación para cobertura
    for pos in [(9,6),(9,7),(10,6),(11,5),(11,6),
                (9,11),(10,11),(10,12),(11,12),
                (8,16),(8,17)]:
        g[pos[0]][pos[1]] = 1
    # Pared lateral izquierda parcial
    for y in range(5, 12):
        g[y][10] = 2
    g[8][10] = 0; g[9][10] = 0  # brecha en la pared
    return g


def _gen_tundra_wastes() -> List[List[int]]:
    """Campo abierto con formaciones rocosas dispersas — táctica de maniobra."""
    g = _flat()
    # Bloques de roca 2×2 dispersos
    rock_anchors = [
        (3,5),(3,12),(4,19),(6,8),(6,16),
        (8,4),(8,13),(9,20),(10,7),(11,11),
        (12,3),(12,17),(13,9),(13,21),(14,5),(14,14)
    ]
    for rx, ry in rock_anchors:
        if 0 < rx < GRILLA_ANCHO-1 and 0 < ry < GRILLA_ALTO-1:
            g[ry][rx] = 2
            g[ry][rx+1] = 2
            g[ry+1][rx] = 2
    # Parches de bosque en lugar de algunos bloques
    forest_spots = [(2,7),(2,8),(5,14),(5,15),(7,18),(7,19),
                    (11,5),(11,6),(15,10),(15,11),(16,16),(16,17)]
    for fx, fy in forest_spots:
        if 0 <= fx < GRILLA_ANCHO and 0 <= fy < GRILLA_ALTO:
            g[fy][fx] = 1
    # Charcos de agua pequeños
    for wx, wy in [(10,9),(11,9),(10,10)]:
        g[wy][wx] = 3
    return g


_GENERATORS = {
    "forest_pass":    _gen_forest_pass,
    "river_crossing": _gen_river_crossing,
    "mountain_keep":  _gen_mountain_keep,
    "fortress_siege": _gen_fortress_siege,
    "tundra_wastes":  _gen_tundra_wastes,
    "flat_with_wall": lambda: _gen_flat_with_wall(8, 6, 18),
}


def _gen_flat_with_wall(wall_row=8, col_start=6, col_end=18) -> List[List[int]]:
    g = _flat()
    for x in range(col_start, col_end):
        g[wall_row][x] = 2
    return g


# =================================================
# MAPAS HARDCODEADOS (FALLBACK)
# =================================================

_GRID_GREENFIELD = [
    [2,2,2,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [2,1,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [2,1,0,0,0,1,1,0,0,0,3,3,3,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,0,0,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,3,3,2,2,3,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,1,0,0,0,0,0,0,3,2,2,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
]

_MAP_GREENFIELD = MapDef(
    name="Greenfield",
    grid=_GRID_GREENFIELD,
    thrones={"aliado": (2, 2), "enemigo": (22, 2)},
    spawns=[
        SpawnDef("HERO_ALLY",   "aliado",  (5, 5)),
        SpawnDef("CLERIC_ALLY", "aliado",  (6, 6)),
    ],
    enemy_positions=[(10, 5), (12, 8), (9, 9)],
    items_spawn={(8, 8): "LANCE_SILVER", (6, 8): "POTION_G"},
    rules={"neutral_monsters": False, "turn_limit": None},
)

_MAP_ARENA = MapDef(
    name="Arena",
    grid=_gen_flat_with_wall(8, 6, 18),
    thrones={"aliado": (1, 1), "enemigo": (23, 16)},
    spawns=[
        SpawnDef("HERO_ALLY",   "aliado",  (3, 3)),
        SpawnDef("CLERIC_ALLY", "aliado",  (4, 3)),
    ],
    enemy_positions=[(20, 12), (21, 12), (18, 10)],
    items_spawn={(12, 4): "POTION_G", (12, 12): "LANCE_SILVER"},
    rules={"neutral_monsters": False, "turn_limit": 30},
)

_HARDCODED_MAPS = [_MAP_GREENFIELD, _MAP_ARENA]


# =================================================
# CARGA DESDE JSON
# =================================================

def _json_to_mapdef(d: dict) -> "MapDef | None":
    try:
        name = d.get("name", "Desconocido")

        # Grid
        if "grid" in d:
            grid = d["grid"]
        elif d.get("grid_generator") in _GENERATORS:
            grid = _GENERATORS[d["grid_generator"]]()
        elif d.get("grid_generator") == "flat_with_wall":
            wr = d.get("wall_row", 8)
            wc = d.get("wall_cols", [6, 18])
            grid = _gen_flat_with_wall(wr, wc[0], wc[1])
        else:
            print(f"[MapData] Mapa '{name}' sin grid definido, omitido.")
            return None

        # Thrones
        thrones = {k: tuple(v) for k, v in d.get("thrones", {}).items()}

        # Ally spawns fijos
        spawns = []
        for sp in d.get("ally_spawns", d.get("spawns", [])):
            # Compatibilidad: si tiene bando==aliado o no especifica bando
            bando = sp.get("bando", "aliado")
            if bando == "aliado":
                spawns.append(SpawnDef(sp["unit_id"], bando, tuple(sp["pos"])))

        # Enemy spawn positions (sin unit_id aún — se asigna en game_state)
        enemy_positions = []
        for esp in d.get("enemy_spawns", []):
            enemy_positions.append(tuple(esp["pos"]))

        # Items spawn
        items_spawn = {}
        for it in d.get("items_spawn", []):
            items_spawn[tuple(it["pos"])] = it["item_id"]

        rules = d.get("rules", {})

        mdef = MapDef(name=name, grid=grid, thrones=thrones,
                      spawns=spawns, enemy_positions=enemy_positions,
                      items_spawn=items_spawn, rules=rules)
        _validate_grid(grid, name)
        _validate_positions(mdef)
        return mdef

    except Exception as e:
        print(f"[MapData] Error cargando mapa '{d.get('name','?')}': {e}")
        return None


def _load_all_maps() -> list:
    json_maps = load_maps()
    result = []

    if json_maps:
        for d in json_maps:
            m = _json_to_mapdef(d)
            if m:
                result.append(m)

    if not result:
        result = list(_HARDCODED_MAPS)

    for m in _HARDCODED_MAPS:
        try:
            _validate_grid(m.grid, m.name)
            _validate_positions(m)
        except Exception as e:
            print(f"[MapData] Hardcoded map error: {e}")

    return result


MAPS: List[MapDef] = _load_all_maps()


# =================================================
# API PÚBLICA
# =================================================

def pick_random_map() -> MapDef:
    return random.choice(MAPS)


def pick_next_map(map_number: int, last_map_name: str = "") -> MapDef:
    """
    Elige el siguiente mapa distinto al último jugado.
    Siempre hay progresión — nunca repite el mapa inmediatamente.
    """
    candidates = [m for m in MAPS if m.name != last_map_name]
    if not candidates:
        candidates = MAPS
    return random.choice(candidates)
