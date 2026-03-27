# systems/boss_map_data.py
# -------------------------------------------------
# Generadores de grid, carga y selección de mapas de jefe.
# Separado de map_data.py para cumplir el límite de 500 líneas por módulo.

import random
from typing import List
from systems.map_data import (MapDef, SpawnDef,
                               GRILLA_ANCHO, GRILLA_ALTO,
                               _validate_grid, _validate_positions)
from loaders.data_loader import load_boss_maps


# =================================================
# GENERADORES DE GRID — MAPAS DE JEFE
# =================================================

def _flat_boss() -> List[List[int]]:
    return [[0] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]


def _gen_boss_throne_hall() -> List[List[int]]:
    """Sala del Trono Oscuro: pasillos convergentes hacia el centro.
    Zona del trono en hierba seca (4) al norte; pilares de roca (5);
    árboles muertos (9) decorativos; muros (2) creando chokepoints."""
    g = _flat_boss()
    # Muro perimetral
    for x in range(GRILLA_ANCHO):
        g[0][x] = 2; g[GRILLA_ALTO - 1][x] = 2
    for y in range(GRILLA_ALTO):
        g[y][0] = 2; g[y][GRILLA_ANCHO - 1] = 2
    # Sala del trono norte — hierba seca (4)
    for y in range(1, 8):
        for x in range(8, 17):
            g[y][x] = 4
    # Muros laterales creando pasillo doble
    for y in range(1, 12):
        g[y][7] = 2; g[y][17] = 2
    # Puertas hacia la sala
    g[7][7] = 0; g[8][7] = 0
    g[7][17] = 0; g[8][17] = 0
    # Pilares dentro de la sala del trono
    for (row, col) in [(2, 9), (2, 15), (5, 9), (5, 15)]:
        g[row][col] = 5
    # Muros fragmentados en zona media para cobertura
    for x in range(3, 7):
        g[12][x] = 2
    for x in range(18, 22):
        g[12][x] = 2
    g[12][5] = 0; g[12][19] = 0   # pasos laterales
    # Árboles muertos decorativos (atmósfera)
    for (row, col) in [(9, 3), (10, 4), (9, 20), (10, 21),
                       (15, 3), (15, 21), (13, 11), (13, 13)]:
        if 0 < row < GRILLA_ALTO - 1 and 0 < col < GRILLA_ANCHO - 1:
            g[row][col] = 9
    return g


def _gen_boss_volcano_peak() -> List[List[int]]:
    """Pico Volcánico: ríos de lava (agua 3) cruzando el mapa,
    formaciones de roca (5) y terreno seco (4) en zonas seguras."""
    g = [[4] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]   # base: hierba seca
    # Río de lava diagonal izquierda (col 5-6, shift por fila)
    for y in range(GRILLA_ALTO):
        col = 5 + y // 3
        if 0 <= col < GRILLA_ANCHO:
            g[y][col] = 3
        if 0 <= col + 1 < GRILLA_ANCHO:
            g[y][col + 1] = 3
    # Río de lava diagonal derecha (col 18-17)
    for y in range(GRILLA_ALTO):
        col = 18 - y // 3
        if 0 <= col < GRILLA_ANCHO:
            g[y][col] = 3
        if 0 <= col - 1 < GRILLA_ANCHO:
            g[y][col - 1] = 3
    # Puentes seguros sobre los ríos (fila 4 y fila 12)
    for bridge_y in [4, 12]:
        for x in range(GRILLA_ANCHO):
            if g[bridge_y][x] == 3:
                g[bridge_y][x] = 4
    # Muros de roca volcánica dispersos
    for (row, col) in [(2, 3), (2, 4), (3, 21), (3, 22),
                       (7, 2), (7, 22), (9, 12), (9, 13),
                       (13, 4), (13, 20), (15, 11), (15, 13)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 5
    # Zona segura norte (hierba 0) para el boss
    for y in range(0, 4):
        for x in range(10, 15):
            if g[y][x] == 4:
                g[y][x] = 0
    return g


def _gen_boss_ice_citadel() -> List[List[int]]:
    """Ciudadela de Hielo: fortaleza nevada con muros de hielo (2),
    suelo nevado (7) y árboles invernales (8) flanqueando los accesos."""
    g = [[7] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]   # base: suelo nevado
    # Muros exteriores de la ciudadela (sector norte)
    for x in range(6, 19):
        g[0][x] = 2; g[6][x] = 2
    for y in range(0, 7):
        g[y][6] = 2; g[y][18] = 2
    # Interior de la ciudadela abierto
    for y in range(1, 6):
        for x in range(7, 18):
            g[y][x] = 4
    # Entrada sur de la ciudadela
    g[6][11] = 0; g[6][12] = 0; g[6][13] = 0
    # Muro intermedio con pasos
    for x in range(4, 21):
        g[10][x] = 2
    g[10][10] = 0; g[10][14] = 0
    # Árboles invernales flanqueando caminos
    for (row, col) in [(8, 3), (9, 3), (8, 21), (9, 21),
                       (7, 5), (7, 19), (12, 5), (12, 19),
                       (13, 8), (13, 16), (15, 11), (15, 13)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 8
    # Charcos helados (3) zona central inferior
    for (row, col) in [(14, 10), (14, 11), (14, 13), (14, 14),
                       (16, 9), (16, 15)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 3
    return g


def _gen_boss_dark_fortress() -> List[List[int]]:
    """Fortaleza Oscura: laberinto de muros con pasillos angostos.
    Hierba (0) en zonas controladas; rocas (5) tapizando el exterior."""
    g = _flat_boss()
    # Muros perimetrales norte/sur
    for x in range(GRILLA_ANCHO):
        g[0][x] = 2; g[GRILLA_ALTO - 1][x] = 2
    for y in range(GRILLA_ALTO):
        g[y][0] = 2; g[y][GRILLA_ANCHO - 1] = 2
    # Zona del jefe: fortaleza interior norte
    for x in range(5, 20):
        g[1][x] = 2; g[7][x] = 2
    for y in range(1, 8):
        g[y][5] = 2; g[y][19] = 2
    g[7][11] = 0; g[7][12] = 0; g[7][13] = 0   # entrada principal
    g[4][5] = 0                                  # puerta lateral izquierda
    g[4][19] = 0                                 # puerta lateral derecha
    # Patio interior
    for y in range(2, 7):
        for x in range(6, 19):
            g[y][x] = 4
    # Pared media — divide el campo
    for x in range(3, 22):
        g[11][x] = 2
    g[11][8] = 0; g[11][12] = 0; g[11][16] = 0  # tres pasos
    # Muros laterales zona sur
    for y in range(11, 17):
        if y not in [13, 15]:
            g[y][3] = 2; g[y][21] = 2
    # Rocas decorativas y cobertura táctica
    for (row, col) in [(9, 2), (9, 22), (13, 6), (13, 18),
                       (15, 8), (15, 16), (16, 10), (16, 14)]:
        if 0 < row < GRILLA_ALTO - 1 and 0 < col < GRILLA_ANCHO - 1:
            g[row][col] = 5
    # Árboles muertos decorativos
    for (row, col) in [(8, 2), (8, 22), (10, 4), (10, 20), (14, 11), (14, 13)]:
        if 0 < row < GRILLA_ALTO - 1 and 0 < col < GRILLA_ANCHO - 1:
            g[row][col] = 9
    return g


def _gen_boss_ancient_arena() -> List[List[int]]:
    """Arena Ancestral: campo abierto con pilares de roca (5) simétricos.
    Sin obstáculos impassables grandes — todo es maniobra y posicionamiento."""
    g = _flat_boss()
    # Borde decorativo de hierba seca (4)
    for x in range(GRILLA_ANCHO):
        g[0][x] = 4; g[GRILLA_ALTO - 1][x] = 4
    for y in range(GRILLA_ALTO):
        g[y][0] = 4; g[y][GRILLA_ANCHO - 1] = 4
    # Pilares de roca simétricos (disposición en X)
    pilares = [
        (3, 4), (3, 20), (3, 12),
        (6, 7), (6, 17),
        (9, 5), (9, 12), (9, 19),
        (12, 7), (12, 17),
        (14, 4), (14, 20),
    ]
    for (row, col) in pilares:
        if 0 < row < GRILLA_ALTO - 1 and 0 < col < GRILLA_ANCHO - 1:
            g[row][col] = 5
    # Bosque ligero en los flancos (cobertura lateral)
    for (row, col) in [(2, 2), (4, 2), (7, 2), (10, 2), (13, 2), (16, 2),
                       (2, 22), (4, 22), (7, 22), (10, 22), (13, 22), (16, 22)]:
        if 0 < row < GRILLA_ALTO - 1:
            g[row][col] = 1
    return g


# =================================================
# REGISTRO DE GENERADORES
# =================================================

_BOSS_GENERATORS = {
    "boss_throne_hall":   _gen_boss_throne_hall,
    "boss_volcano_peak":  _gen_boss_volcano_peak,
    "boss_ice_citadel":   _gen_boss_ice_citadel,
    "boss_dark_fortress": _gen_boss_dark_fortress,
    "boss_ancient_arena": _gen_boss_ancient_arena,
}


# =================================================
# CARGA DESDE JSON
# =================================================

def _json_to_boss_mapdef(d: dict) -> "MapDef | None":
    try:
        name = d.get("name", "Jefe Desconocido")

        gen_key = d.get("grid_generator", "")
        if gen_key in _BOSS_GENERATORS:
            grid = _BOSS_GENERATORS[gen_key]()
        elif "grid" in d:
            grid = d["grid"]
        else:
            print(f"[BossMapData] Mapa '{name}' sin grid, omitido.")
            return None

        thrones = {k: tuple(v) for k, v in d.get("thrones", {}).items()}

        spawns = []
        for sp in d.get("ally_spawns", []):
            spawns.append(SpawnDef(sp["unit_id"], "aliado", tuple(sp["pos"])))

        # Mapas de jefe: enemy_positions son posiciones del boss (1-2)
        enemy_positions = [tuple(esp["pos"]) for esp in d.get("enemy_spawns", [])]

        items_spawn = {tuple(it["pos"]): it["item_id"]
                       for it in d.get("items_spawn", [])}

        rules = d.get("rules", {})

        mdef = MapDef(
            name=name, grid=grid, thrones=thrones,
            spawns=spawns, enemy_positions=enemy_positions,
            items_spawn=items_spawn, rules=rules,
            weather=d.get("weather", None),
            is_boss=True,
        )
        _validate_grid(grid, name)
        _validate_positions(mdef)
        return mdef

    except Exception as e:
        print(f"[BossMapData] Error cargando '{d.get('name','?')}': {e}")
        return None


def _load_boss_maps() -> List[MapDef]:
    raw = load_boss_maps()
    result = []
    for d in raw:
        m = _json_to_boss_mapdef(d)
        if m:
            result.append(m)
    if not result:
        print("[BossMapData] ¡Sin mapas de jefe! Usando arena como fallback.")
    return result


BOSS_MAPS: List[MapDef] = _load_boss_maps()


# =================================================
# API PÚBLICA
# =================================================

def pick_boss_map(used_names: List[str]) -> "MapDef | None":
    """Elige un mapa de jefe que no haya sido usado en esta run.
    Si ya se usaron todos, recicla (el pool tiene 5, la run necesita 3)."""
    if not BOSS_MAPS:
        return None
    candidates = [m for m in BOSS_MAPS if m.name not in used_names]
    if not candidates:
        candidates = BOSS_MAPS   # todos usados — reiniciar pool
    return random.choice(candidates)
