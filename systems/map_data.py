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
    "easy": [
        "BANDIT_ENEMY", "GOBLIN_SPEAR", "GOBLIN_CLUB", "FARMER_GOBLIN", "SLIME",
    ],
    "medium": [
        "ORC_ENEMY", "MAGE_ENEMY", "PIRATE_CAPTAIN", "GOBLIN_ARCHER",
        "SKELETON_SOLDIER", "KAMIKAZE_GOBLIN", "YETI",
    ],
    "hard": [
        "MINOTAUR", "ORC_SHAMAN", "PIRATE_GUNNER", "NECROMANCER", "DEMON_RED",
        "ARMOURED_DEMON", "PURPLE_DEMON", "WENDIGO",
        "BLUE_DRAGON", "YELLOW_DRAGON", "GIANT_CRAB",
    ],
    "boss": [
        "DEMON_RED", "MAMMOTH", "NECROMANCER", "MINOTAUR",
        "BLACK_DRAGON", "WHITE_DRAGON",
    ],
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
    weather:     "str | None" = None     # clima estético del mapa (ver ui/weather.py)
    is_boss:     bool          = False   # True → mapa de jefe


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
    """Dos paredes de bosque con brechas estratégicas.
    Árboles muertos (9) en bordes y rocas (5) como cobertura secundaria."""
    g = _flat()
    # Paredes de bosque (cols 7-9 y 15-17)
    for y in range(GRILLA_ALTO):
        for x in [7, 8, 9, 15, 16, 17]:
            g[y][x] = 1
    # Brechas en pared izquierda (filas 4-5 y 11-12)
    for y in range(4, 6):
        g[y][8] = 0; g[y][9] = 0
    for y in range(11, 13):
        g[y][7] = 0; g[y][8] = 0
    # Brecha en pared derecha (filas 8-9 — más difícil cruzar)
    for y in range(8, 10):
        g[y][15] = 0; g[y][16] = 0
    # Muros de roca bloqueando cruces del corredor central
    for x in range(10, 15):
        g[2][x] = 2
        g[15][x] = 2
    g[2][11] = 0; g[2][12] = 0    # paso superior
    g[15][12] = 0; g[15][13] = 0  # paso inferior
    # Bosque decorativo lateral (cobertura adicional)
    for row in [1, 3, 7, 10, 14, 16]:
        g[row][4] = 1; g[row][20] = 1
    # Árboles muertos (9) en los márgenes del mapa — atmósfera de bosque oscuro
    for row in [0, 2, 5, 9, 13, 17]:
        if row < GRILLA_ALTO:
            g[row][1] = 9; g[row][23] = 9
    # Rocas pequeñas (5) en el corredor como obstáculos tácticos secundarios
    for (row, col) in [(6, 11), (6, 13), (12, 11), (12, 13)]:
        g[row][col] = 5
    return g


def _gen_river_crossing() -> List[List[int]]:
    """Río vertical de 3 tiles de ancho (cols 11-13) con agua profunda en el centro.
    Cols 10 y 14 son hierba — transición libre desde las orillas.
    Tres puentes abren las cols de agua en filas 3, 9 y 14.
    Bosque en orillas (cols 7-8 y 15-16) con rocas como cobertura adicional."""
    g = _flat()
    # Río: solo cols 11-13 son agua — las orillas (cols 10 y 14) quedan libres
    for y in range(GRILLA_ALTO):
        g[y][11] = 3   # agua normal izquierda
        g[y][12] = 6   # agua profunda central (impassable diferenciada visualmente)
        g[y][13] = 3   # agua normal derecha
    # Tres puentes: abrir las 3 cols de agua completamente
    for bridge_y in [3, 8, 14]:
        g[bridge_y][11] = 0
        g[bridge_y][12] = 0
        g[bridge_y][13] = 0
    # Puente central más ancho (también col 10 y 14 se limpian de bosque)
    # (ya son hierba, no hace falta hacer nada extra)
    # Bosque en orillas como cobertura táctica
    for y in range(1, GRILLA_ALTO - 1):
        g[y][7]  = 1; g[y][8]  = 1
        g[y][16] = 1; g[y][17] = 1
    # Abrir bosque en filas de cruce para que no sea un callejón sin salida
    for y in [3, 8, 14]:
        g[y][7] = 0; g[y][8] = 0
        g[y][16] = 0; g[y][17] = 0
    # Rocas (5) en las orillas del río — cobertura táctica junto al agua
    for (row, col) in [(1, 9), (5, 10), (11, 9), (16, 10),
                       (2, 14), (7, 14), (12, 14), (15, 14)]:
        if 0 <= row < GRILLA_ALTO:
            g[row][col] = 5
    return g


def _gen_mountain_keep() -> List[List[int]]:
    """Cordillera con zona nevada al norte y fortaleza enemiga.
    Nieve (7) y árboles invernales (8) en la cima; hierba seca (4) dentro de la fortaleza;
    rocas (5) naturales en los bordes de la cordillera."""
    g = _flat()
    # Zona nevada en las 3 filas superiores
    for y in range(3):
        for x in range(GRILLA_ANCHO):
            g[y][x] = 7   # suelo nevado
    # Árboles invernales (8) dispersos en zona nevada
    for (row, col) in [(0, 4), (0, 5), (1, 8), (1, 9),
                       (0, 14), (0, 15), (1, 19), (1, 20)]:
        g[row][col] = 8
    # Cordillera: filas 7-10 (muros impassable)
    for y in range(7, 11):
        for x in range(GRILLA_ANCHO):
            g[y][x] = 2
    # Rocas (5) en los bordes de la cordillera — aspecto más orgánico
    for (row, col) in [(7, 0), (7, 1), (10, 23), (10, 24),
                       (8, 2), (9, 22), (7, 13), (10, 12)]:
        if 0 <= col < GRILLA_ANCHO:
            g[row][col] = 5
    # Pasos: oeste (cols 4-5) y este (cols 18-19)
    for y in range(7, 11):
        g[y][4] = 0; g[y][5] = 0
        g[y][18] = 0; g[y][19] = 0
    # Muro de fortaleza enemiga (filas 1-5, cols 16-23)
    for y in range(1, 6):
        g[y][16] = 2; g[y][23] = 2
    for x in range(16, 24):
        g[1][x] = 2; g[5][x] = 2
    # Interior de fortaleza en hierba seca (4) — patio interior desgastado
    for y in range(2, 5):
        for x in range(17, 23):
            g[y][x] = 4
    # Entrada de la fortaleza
    g[5][19] = 0; g[5][20] = 0
    # Bosque en la zona aliada inferior (filas 11-16)
    for (row, col) in [(11, 2), (11, 3), (12, 5), (12, 6),
                       (13, 13), (13, 14), (14, 3), (15, 11), (16, 12)]:
        if 0 <= row < GRILLA_ALTO:
            g[row][col] = 1
    # Bosque en zona enemiga al aire libre (árboles invernales en la nieve)
    for (row, col) in [(2, 8), (2, 9)]:
        g[row][col] = 8   # sobre suelo nevado → árboles invernales
    for (row, col) in [(3, 8), (3, 9)]:
        g[row][col] = 1   # ya es hierba normal → bosque estándar
    return g


def _gen_fortress_siege() -> List[List[int]]:
    """Fortaleza enemiga en esquina superior-derecha. Aliados asedian desde el sur.
    Patio interior en hierba seca (4); árboles muertos (9) cerca del campo de batalla;
    rocas (5) como cobertura extra en la aproximación."""
    g = _flat()
    # Muros exteriores de la fortaleza (filas 0-7, cols 15-24)
    for x in range(15, 25):
        if x < GRILLA_ANCHO:
            g[0][x] = 2; g[7][x] = 2
    for y in range(0, 8):
        g[y][15] = 2
        if 24 < GRILLA_ANCHO:
            g[y][24] = 2
    # Entrada de la fortaleza (fila 7, cols 19-20)
    g[7][19] = 0; g[7][20] = 0
    # Paredes interiores
    for x in range(17, 23):
        g[3][x] = 2
    g[3][19] = 0; g[3][20] = 0
    # Patio interior en hierba seca (4) — desgastado por el uso militar
    for y in range(1, 3):
        for x in range(16, 24):
            if x < GRILLA_ANCHO:
                g[y][x] = 4
    for y in range(4, 7):
        for x in range(16, 24):
            if x < GRILLA_ANCHO:
                g[y][x] = 4
    # Bosque de aproximación — mezcla de árboles vivos (1) y muertos (9)
    for (row, col) in [(9, 6), (9, 7), (10, 6), (11, 5), (11, 6),
                       (9, 11), (10, 11), (10, 12), (11, 12)]:
        g[row][col] = 1
    # Árboles muertos (9) — quemados por la batalla, dan atmósfera de asedio
    for (row, col) in [(8, 5), (10, 8), (12, 10), (9, 13), (11, 14)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 9
    # Pared lateral izquierda con brecha para flanqueo
    for y in range(5, 12):
        g[y][10] = 2
    g[8][10] = 0; g[9][10] = 0
    # Rocas (5) como cobertura táctica en la aproximación central
    for (row, col) in [(13, 7), (14, 8), (13, 18), (14, 19)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 5
    return g


def _gen_tundra_wastes() -> List[List[int]]:
    """Yermo helado con suelo nevado base (7), árboles invernales (8),
    formaciones de rocas (5) y ruinas aisladas (2). Táctica de maniobra amplia."""
    # Base: suelo nevado (7) — todo el mapa cubierto de nieve
    g = [[7] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]
    # Formaciones rocosas dispersas (5) en lugar de muros — más orgánico
    # (col, row) — ry=row, rx=col
    rock_anchors = [
        (5, 3), (12, 3), (19, 4), (8, 6), (16, 6),
        (4, 8), (13, 8), (20, 9), (7, 10), (11, 11),
        (3, 12), (17, 12), (9, 13), (21, 13),
    ]
    for col, row in rock_anchors:
        if 0 < col < GRILLA_ANCHO - 1 and 0 < row < GRILLA_ALTO - 1:
            g[row][col]     = 5
            g[row][col + 1] = 5
            g[row + 1][col] = 5
    # Árboles invernales (8) en grupos — esquinas y centro
    winter_tree_spots = [
        # Esquinas del mapa
        (1, 1), (2, 1), (1, 2), (2, 2),
        (22, 1), (23, 1), (22, 2), (23, 2),
        (1, 15), (2, 15), (1, 16), (2, 16),
        (22, 15), (23, 15), (22, 16), (23, 16),
        # Grupos en zonas centrales
        (6, 7), (7, 7), (6, 8),
        (17, 8), (18, 8), (17, 9),
        (11, 10), (12, 10), (11, 11),
    ]
    for col, row in winter_tree_spots:
        if 0 <= col < GRILLA_ANCHO and 0 <= row < GRILLA_ALTO:
            g[row][col] = 8
    # Charcos helados (3) — pequeños estanques congelados
    for col, row in [(10, 4), (11, 4), (10, 5), (13, 13), (14, 13)]:
        if 0 <= col < GRILLA_ANCHO and 0 <= row < GRILLA_ALTO:
            g[row][col] = 3
    # Ruinas de muros (2) — restos de una fortaleza destruida
    for col, row in [(6, 3), (7, 3), (16, 14), (17, 14)]:
        if 0 <= col < GRILLA_ANCHO and 0 <= row < GRILLA_ALTO:
            g[row][col] = 2
    return g


_GENERATORS = {
    "forest_pass":    _gen_forest_pass,
    "river_crossing": _gen_river_crossing,
    "mountain_keep":  _gen_mountain_keep,
    "fortress_siege": _gen_fortress_siege,
    "tundra_wastes":  _gen_tundra_wastes,
    "flat_with_wall": lambda: _gen_flat_with_wall(8, 6, 18),
}

# Registrar generadores adicionales (ver map_generators_extra.py)
from systems.map_generators_extra import EXTRA_GENERATORS as _EXTRA
_GENERATORS.update(_EXTRA)


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
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,5,5,0,0,0,0,0,0,1,1,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,1,1,0,0,0,0,5,5,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,5,5,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0],
    [0,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0,0,0,0,1,1,0,0,0,0],
    [0,0,0,0,1,1,0,0,0,0,0,3,3,3,0,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,3,3,3,3,3,0,0,0,0,0,0,0,0,0,0],
    [0,0,0,0,0,0,0,0,0,0,0,3,3,3,0,0,0,0,0,0,0,0,0,0,0],
]

_MAP_GREENFIELD = MapDef(
    name="Greenfield",
    grid=_GRID_GREENFIELD,
    thrones={"aliado": (2, 2), "enemigo": (22, 2)},
    spawns=[
        SpawnDef("HERO_ALLY",   "aliado",  (5, 5)),
        SpawnDef("CLERIC_ALLY", "aliado",  (4, 7)),
    ],
    enemy_positions=[(17, 5), (19, 9), (16, 12)],
    items_spawn={(7, 7): "LANCE_SILVER", (6, 8): "POTION_G", (13, 11): "ANTIDOTE"},
    rules={"neutral_monsters": False, "turn_limit": None},
)

_GRID_ARENA = [
    [2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2],
    [2,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,2],
    [2,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,5,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0,0,0,4,2],
    [2,4,0,0,5,5,0,0,0,0,0,0,0,0,0,0,0,0,5,5,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,5,0,0,0,0,5,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,0,5,0,0,5,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,0,0,5,5,0,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,0,5,0,0,5,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,5,0,0,0,0,5,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,0,0,5,5,0,0,0,0,0,0,0,0,0,0,0,0,5,5,0,0,0,4,2],
    [2,4,0,0,0,5,0,0,0,0,0,0,0,0,0,0,0,0,0,5,0,0,0,4,2],
    [2,4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,4,2],
    [2,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,2],
    [2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2],
]

_MAP_ARENA = MapDef(
    name="Arena",
    grid=_GRID_ARENA,
    thrones={"aliado": (1, 1), "enemigo": (23, 16)},
    spawns=[
        SpawnDef("HERO_ALLY",   "aliado",  (3, 3)),
        SpawnDef("CLERIC_ALLY", "aliado",  (3, 5)),
    ],
    enemy_positions=[(21, 12), (20, 14), (21, 9)],
    items_spawn={(12, 6): "POTION_G", (12, 12): "LANCE_SILVER"},
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
                      items_spawn=items_spawn, rules=rules,
                      weather=d.get("weather", None),
                      is_boss=bool(d.get("is_boss", False)))
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
