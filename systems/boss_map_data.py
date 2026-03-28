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
# GENERADORES ADICIONALES — JEFES
# =================================================

def _gen_boss_sunken_temple() -> List[List[int]]:
    """Templo Hundido: suelo inundado de agua profunda (6) con plataformas
    elevadas de hierba seca (4) y ruinas de muros (2).
    Caminos estrechos sobre el agua — cada paso importa."""
    g = [[6] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]   # base: agua profunda

    # Plataformas principales de piedra seca (4)
    # Plataforma norte — zona del jefe
    for y in range(0, 5):
        for x in range(8, 17):
            g[y][x] = 4

    # Plataforma central — campo de batalla
    for y in range(7, 11):
        for x in range(5, 20):
            g[y][x] = 4

    # Plataforma sur — zona aliada
    for y in range(13, 18):
        for x in range(8, 17):
            g[y][x] = 4

    # Puentes estrechos conectando plataformas (agua normal 3 a los lados)
    for y in range(5, 7):
        g[y][11] = 4; g[y][12] = 4; g[y][13] = 4   # puente norte-centro
        g[y][9]  = 3; g[y][10] = 3                  # agua lateral
        g[y][14] = 3; g[y][15] = 3
    for y in range(11, 13):
        g[y][11] = 4; g[y][12] = 4; g[y][13] = 4   # puente centro-sur
        g[y][9]  = 3; g[y][10] = 3
        g[y][14] = 3; g[y][15] = 3

    # Agua normal (3) rodeando plataformas (transición visual)
    for y in range(GRILLA_ALTO):
        for x in range(GRILLA_ANCHO):
            if g[y][x] == 6:
                # Convertir borde inmediato de plataforma a agua normal
                neighbors = [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]
                if any(0<=ny<GRILLA_ALTO and 0<=nx<GRILLA_ANCHO
                       and g[ny][nx] == 4 for ny,nx in neighbors):
                    g[y][x] = 3

    # Ruinas de muros (2) dentro de la plataforma norte (columnas del templo)
    for (row, col) in [(1, 9), (1, 15), (3, 9), (3, 15),
                        (2, 10), (2, 14)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 2

    # Rocas (5) en la plataforma central como cobertura táctica
    for (row, col) in [(8, 7), (8, 17), (9, 8), (9, 16),
                        (8, 11), (8, 13), (10, 10), (10, 14)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 5

    return g


def _gen_boss_cursed_graveyard() -> List[List[int]]:
    """Cementerio Maldito: hierba (0) con lápidas de roca (5),
    criptas de muro (2) y árboles muertos (9) por todo el mapa.
    Niebla densa — pocos chokepoints pero mucha cobertura de lápidas."""
    g = [[0] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]

    # Perímetro de muro — valla del cementerio
    for x in range(GRILLA_ANCHO):
        g[0][x] = 2; g[GRILLA_ALTO - 1][x] = 2
    for y in range(GRILLA_ALTO):
        g[y][0] = 2; g[y][GRILLA_ANCHO - 1] = 2

    # Cripta norte — sede del jefe (sala rectangular)
    for x in range(7, 18):
        g[1][x] = 2; g[5][x] = 2
    for y in range(1, 6):
        g[y][7] = 2; g[y][17] = 2
    g[5][11] = 0; g[5][12] = 0; g[5][13] = 0   # entrada
    for y in range(2, 5):
        for x in range(8, 17):
            g[y][x] = 4   # interior de cripta en hierba seca

    # Cripta pequeña SO (rows 9-12, cols 2-6)
    for x in range(2, 7):
        g[9][x] = 2; g[12][x] = 2
    for y in range(9, 13):
        g[y][2] = 2; g[y][6] = 2
    g[12][4] = 0; g[12][5] = 0

    # Cripta pequeña SE (rows 9-12, cols 18-22)
    for x in range(18, 23):
        g[9][x] = 2; g[12][x] = 2
    for y in range(9, 13):
        g[y][18] = 2; g[y][22] = 2
    g[12][20] = 0; g[12][21] = 0

    # Lápidas (5) — distribuidas por todo el campo
    tombstones = [
        (7, 3), (7, 5), (7, 10), (7, 14), (7, 19), (7, 21),
        (8, 7), (8, 12), (8, 17),
        (10, 9), (10, 15),
        (13, 4), (13, 8), (13, 12), (13, 16), (13, 20),
        (14, 6), (14, 10), (14, 14), (14, 18),
        (15, 3), (15, 8), (15, 16), (15, 21),
        (16, 5), (16, 11), (16, 13), (16, 19),
    ]
    for (row, col) in tombstones:
        if 0 < row < GRILLA_ALTO-1 and 0 < col < GRILLA_ANCHO-1:
            g[row][col] = 5

    # Árboles muertos (9) — atmósfera lúgubre
    dead_trees = [
        (6, 2), (6, 5), (6, 19), (6, 22),
        (8, 4), (8, 20),
        (11, 7), (11, 17),
        (13, 2), (13, 22),
        (15, 6), (15, 18),
        (16, 9), (16, 15),
    ]
    for (row, col) in dead_trees:
        if 0 < row < GRILLA_ALTO-1 and 0 < col < GRILLA_ANCHO-1 and g[row][col] == 0:
            g[row][col] = 9

    # Estanque maldito (agua 3) — reflejo oscuro en el centro
    for (row, col) in [(8, 11), (8, 12), (8, 13),
                        (9, 11), (9, 12), (9, 13)]:
        if g[row][col] == 0:
            g[row][col] = 3

    return g


def _gen_boss_sky_citadel() -> List[List[int]]:
    """Ciudadela del Cielo: fortaleza flotante.
    Vacíos de agua (3/6) como el cielo debajo; plataformas de
    hierba seca (4); puentes de hierba (0); torres de muro (2)."""
    g = [[6] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]   # base: vacío del cielo

    # Plataforma principal del castillo (norte)
    for y in range(0, 8):
        for x in range(4, 21):
            g[y][x] = 4

    # Patio interior del castillo norte
    for y in range(2, 7):
        for x in range(7, 18):
            g[y][x] = 0

    # Torres de las esquinas (muros 2)
    for (row, col) in [(0,4),(0,5),(1,4),(0,20),(0,19),(1,20),
                        (6,4),(7,4),(6,20),(7,20)]:
        g[row][col] = 2

    # Muro exterior de la ciudadela norte
    for x in range(4, 21):
        g[0][x] = 2
    for y in range(0, 8):
        g[y][4] = 2; g[y][20] = 2
    # Entrada
    g[7][11] = 4; g[7][12] = 4; g[7][13] = 4

    # Puente norte hacia la plataforma de aliados (sur)
    for y in range(8, 11):
        g[y][10] = 0; g[y][11] = 0
        g[y][12] = 0; g[y][13] = 0; g[y][14] = 0
        g[y][9]  = 3; g[y][15] = 3   # bordes del puente

    # Plataforma sur (aliados)
    for y in range(11, 18):
        for x in range(5, 20):
            g[y][x] = 4

    # Vacío parcial en plataforma sur (táctico)
    for x in range(8, 17):
        g[17][x] = 6   # borde sur al vacío
    for (row, col) in [(12, 6), (12, 22), (13, 7), (13, 21),
                        (14, 9), (14, 15), (15, 6), (15, 18)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 3

    # Rocas (5) en el patio como cobertura
    for (row, col) in [(3, 8), (3, 16), (4, 9), (4, 15),
                        (5, 10), (5, 14), (13, 9), (13, 15)]:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO and g[row][col] == 0:
            g[row][col] = 5

    return g


def _gen_boss_lava_cathedral() -> List[List[int]]:
    """Catedral de Lava: ríos de lava (3/6) en patrón de nave
    central + naves laterales; hierba seca (4) en los pasillos;
    columnas de muro (2) formando la estructura del templo."""
    g = [[4] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]   # base: piedra seca

    # Nave central de lava (cols 11-13 todo el alto)
    for y in range(GRILLA_ALTO):
        g[y][11] = 3; g[y][12] = 6; g[y][13] = 3

    # Naves laterales de lava (cols 5-6 y 18-19, rows 3-14)
    for y in range(3, 15):
        g[y][5]  = 3; g[y][6]  = 3
        g[y][18] = 3; g[y][19] = 3

    # Crucero transversal de lava (rows 7-8, todo el ancho)
    for x in range(GRILLA_ANCHO):
        if g[7][x] != 6:
            g[7][x] = 3
        if g[8][x] != 6:
            g[8][x] = 3
    # Profunda en intersecciones
    g[7][11] = 6; g[7][12] = 6; g[7][13] = 6
    g[8][11] = 6; g[8][12] = 6; g[8][13] = 6
    g[7][5]  = 6; g[7][6]  = 6; g[8][5]  = 6; g[8][6]  = 6
    g[7][18] = 6; g[7][19] = 6; g[8][18] = 6; g[8][19] = 6

    # Puentes sobre la lava (cruces navegables)
    # Puente norte sobre nave central (row 3)
    g[3][11] = 4; g[3][12] = 4; g[3][13] = 4
    # Puente sobre crucero (rows 7-8, cols 8-10 y 14-16)
    for y in [7, 8]:
        for x in [8, 9, 10, 14, 15, 16]:
            g[y][x] = 4
    # Puente sur nave central (row 12)
    g[12][11] = 4; g[12][12] = 4; g[12][13] = 4
    # Puente naves laterales (row 5 y row 11)
    for bridge_row in [5, 11]:
        g[bridge_row][5] = 4; g[bridge_row][6] = 4
        g[bridge_row][18] = 4; g[bridge_row][19] = 4

    # Columnas de la catedral (muros 2) — patrón simétrico
    columns = [
        (1, 7), (1, 17), (2, 8), (2, 16),
        (4, 4), (4, 20),
        (5, 8), (5, 16),
        (6, 4), (6, 20),
        (9, 4), (9, 20),
        (10, 8), (10, 16),
        (11, 4), (11, 20),
        (13, 8), (13, 16),
        (14, 4), (14, 20),
        (15, 7), (15, 17),
    ]
    for (row, col) in columns:
        if 0 <= row < GRILLA_ALTO and 0 <= col < GRILLA_ANCHO:
            g[row][col] = 2

    # Altar del jefe — zona norte sagrada (rows 0-2)
    for y in range(3):
        for x in range(7, 18):
            g[y][x] = 0   # piedra oscura (hierba 0 como contraste)
    g[0][12] = 5   # altar central

    return g


# =================================================
# REGISTRO DE GENERADORES
# =================================================

_BOSS_GENERATORS = {
    "boss_throne_hall":      _gen_boss_throne_hall,
    "boss_volcano_peak":     _gen_boss_volcano_peak,
    "boss_ice_citadel":      _gen_boss_ice_citadel,
    "boss_dark_fortress":    _gen_boss_dark_fortress,
    "boss_ancient_arena":    _gen_boss_ancient_arena,
    "boss_sunken_temple":    _gen_boss_sunken_temple,
    "boss_cursed_graveyard": _gen_boss_cursed_graveyard,
    "boss_sky_citadel":      _gen_boss_sky_citadel,
    "boss_lava_cathedral":   _gen_boss_lava_cathedral,
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
