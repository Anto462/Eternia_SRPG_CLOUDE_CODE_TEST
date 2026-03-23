# map_data.py
# -------------------------------------------------
# Aquí guardamos los mapas del juego como "plantillas".
# Un mapa trae TODO lo necesario para iniciar una partida:
# - grid (terreno)
# - thrones (trono aliado/enemigo)
# - spawns (posiciones iniciales de unidades)
# - items_spawn (items en el suelo al inicio)
# - rules (flags para mecánicas específicas del mapa)
#
# O sea: el mapa define el "dónde" y el "qué aparece".
# units.py / items.py se encargan de construir las instancias reales.

from dataclasses import dataclass
from typing import Dict, List, Tuple
import random

from constants import GRILLA_ANCHO, GRILLA_ALTO


Coord = Tuple[int, int]


@dataclass(frozen=True)
class SpawnDef:
    # unit_id es el ID del catálogo de units.py
    unit_id: str
    bando: str          # "aliado" | "enemigo" | "neutral"
    pos: Coord


@dataclass(frozen=True)
class MapDef:
    name: str
    grid: List[List[int]]
    thrones: Dict[str, Coord]              # {"aliado": (x,y), "enemigo": (x,y)}
    spawns: List[SpawnDef]
    items_spawn: Dict[Coord, str]          # {(x,y): "ITEM_ID"}
    rules: Dict[str, object]               # {"neutral_monsters": True, ...}


# -------------------------------------------------
# Helpers simples de validación
# (para que cuando metas mapas nuevos no te exploten en runtime raro)
# -------------------------------------------------
def _validate_grid(grid: List[List[int]], name: str):
    if len(grid) != GRILLA_ALTO:
        raise ValueError(f"[{name}] grid altura inválida. Esperado {GRILLA_ALTO}, vino {len(grid)}")

    for i, row in enumerate(grid):
        if len(row) != GRILLA_ANCHO:
            raise ValueError(f"[{name}] fila {i} ancho inválido. Esperado {GRILLA_ANCHO}, vino {len(row)}")


def _validate_positions(map_def: MapDef):
    def in_bounds(p: Coord):
        x, y = p
        return 0 <= x < GRILLA_ANCHO and 0 <= y < GRILLA_ALTO

    # thrones dentro del mapa
    for b, p in map_def.thrones.items():
        if not in_bounds(p):
            raise ValueError(f"[{map_def.name}] trono '{b}' fuera del mapa: {p}")

    # spawns dentro del mapa
    for s in map_def.spawns:
        if not in_bounds(s.pos):
            raise ValueError(f"[{map_def.name}] spawn fuera del mapa: {s}")

    # items dentro del mapa
    for p in map_def.items_spawn.keys():
        if not in_bounds(p):
            raise ValueError(f"[{map_def.name}] item_spawn fuera del mapa: {p}")


# =================================================
# MAPA 1: tu mapa base (ajustado a 18 filas)
# =================================================
# IMPORTANTE:
# Tu MAPA_DATA original tenía 19 filas.
# GRILLA_ALTO con 600/32 = 18.
# Entonces aquí lo dejo en 18 filas para que sea consistente.

GRID_GREENFIELD = [
    [2, 2, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 1, 1, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [2, 1, 0, 0, 0, 1, 1, 0, 0, 0, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 1, 1, 0, 0, 3, 3, 3, 3, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 2, 2, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 3, 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]

MAP_GREENFIELD = MapDef(
    name="Greenfield",
    grid=GRID_GREENFIELD,

    # tronos por bando
    # aquí puedes meter el trono enemigo cuando quieras
    thrones={
        "aliado": (2, 2),
        "enemigo": (22, 2),
    },

    # spawns iniciales (estos IDs vienen del UNIT_CATALOG)
    spawns=[
        SpawnDef("HERO_ALLY", "aliado", (5, 5)),
        SpawnDef("CLERIC_ALLY", "aliado", (6, 6)),
        SpawnDef("BANDIT_ENEMY", "enemigo", (10, 5)),
        SpawnDef("ORC_ENEMY", "enemigo", (12, 8)),
        SpawnDef("DUMMY_HP", "enemigo", (9, 9)),
    ],

    # items al suelo al inicio (IDs de ITEM_CATALOG)
    items_spawn={
        (8, 8): "LANCE_SILVER",
        (6, 8): "POTION_G",
    },

    # reglas extras del mapa
    rules={
        "neutral_monsters": False,
        "turn_limit": None,
    }
)


# =================================================
# MAPA 2: ejemplo simple (solo para demostrar que puedes meter otro)
# =================================================
# Este mapa es intencionalmente simple: campo plano + una pared
# Para que tengas un segundo mapa random sin complicarte.

GRID_ARENA = []
for y in range(GRILLA_ALTO):
    row = []
    for x in range(GRILLA_ANCHO):
        row.append(0)  # todo pasto
    GRID_ARENA.append(row)

# Metemos una pared en medio (tipo 2)
for x in range(6, 19):
    GRID_ARENA[8][x] = 2

MAP_ARENA = MapDef(
    name="Arena",
    grid=GRID_ARENA,
    thrones={
        "aliado": (1, 1),
        "enemigo": (23, 16),
    },
    spawns=[
        SpawnDef("HERO_ALLY", "aliado", (3, 3)),
        SpawnDef("CLERIC_ALLY", "aliado", (4, 3)),
        SpawnDef("BANDIT_ENEMY", "enemigo", (20, 12)),
        SpawnDef("ORC_ENEMY", "enemigo", (21, 12)),
    ],
    items_spawn={
        (12, 4): "POTION_G",
        (12, 12): "LANCE_SILVER",
    },
    rules={
        "neutral_monsters": False,
        "turn_limit": 30,
    }
)


# =================================================
# LISTA FINAL DE MAPAS
# =================================================
MAPS = [MAP_GREENFIELD, MAP_ARENA]

# Validación (para que si algo está mal, falle al iniciar, no en medio de la partida)
for m in MAPS:
    _validate_grid(m.grid, m.name)
    _validate_positions(m)


def pick_random_map():
    """
    Devuelve un MapDef random.
    """
    return random.choice(MAPS)
