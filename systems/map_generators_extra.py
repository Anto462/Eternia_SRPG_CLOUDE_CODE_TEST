# systems/map_generators_extra.py
# -------------------------------------------------
# Generadores adicionales de mapas regulares.
# Importado por map_data.py para extender _GENERATORS.
# Todos los mapas siguen la convención de zona segura:
#   Aliados → SW  (x=2-4, y=14-16)
#   Enemigos → NE (x=19-21, y=2-4)
# -------------------------------------------------

from typing import List
import constants as C

GRILLA_ANCHO = C.GRILLA_ANCHO   # 25
GRILLA_ALTO  = C.GRILLA_ALTO    # 18

def _flat_e() -> List[List[int]]:
    return [[0] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]


# =================================================
# MAP 1 — Pantano Corrupto
# Grandes charcas de agua (3/6) con corredores sinuosos.
# Bosque (1) en las orillas; árboles muertos (9) en el barro.
# =================================================
def _gen_corrupted_swamp() -> List[List[int]]:
    g = _flat_e()

    # Pantanos norte — esquinas
    for y in range(6):
        for x in range(7):
            g[y][x] = 3
        for x in range(18, GRILLA_ANCHO):
            g[y][x] = 3
    for (y, x) in [(3, 3), (4, 3), (4, 4), (3, 20), (4, 20), (4, 21)]:
        g[y][x] = 6

    # Charcas centro-izquierda (rows 7-9)
    for x in range(3, 8):
        g[7][x] = 3; g[8][x] = 3
    g[7][5] = 6; g[8][5] = 6

    # Charcas centro-derecha (rows 7-9)
    for x in range(17, 22):
        g[7][x] = 3; g[8][x] = 3
    g[7][19] = 6; g[8][19] = 6

    # Gran charco central (rows 10-12, cols 9-15)
    for y in range(10, 13):
        for x in range(9, 16):
            g[y][x] = 3
    for (y, x) in [(10, 12), (11, 11), (11, 12), (11, 13)]:
        g[y][x] = 6
    # Abrir pasos E/O sobre el charco
    g[10][9] = 0; g[10][15] = 0
    g[12][9] = 0; g[12][15] = 0

    # Pantanos sur — esquinas (rows 14-17) — dejar cols 7-17 abiertos
    for y in range(14, 18):
        for x in range(1, 6):
            g[y][x] = 3
        for x in range(19, 24):
            g[y][x] = 3
    for (y, x) in [(15, 3), (15, 4), (16, 3), (15, 21), (15, 22), (16, 21)]:
        g[y][x] = 6

    # Orillas de bosque (1)
    for (y, x) in [(6, 7), (6, 8), (6, 16), (6, 17),
                    (0, 7), (1, 7), (0, 17), (1, 17),
                    (9, 2), (9, 22), (13, 7), (13, 17)]:
        if g[y][x] == 0:
            g[y][x] = 1

    # Árboles muertos (9) — atmósfera de barro
    for (y, x) in [(2, 8), (3, 8), (3, 16), (2, 16),
                    (6, 11), (6, 12), (9, 11), (9, 13),
                    (13, 11), (13, 13)]:
        if g[y][x] == 0:
            g[y][x] = 9

    return g


# =================================================
# MAP 2 — Ruinas del Imperio
# Hierba seca (4) como base de piedra antigua.
# Muros (2) en formas de L y C forman edificios derruidos.
# Patios abiertos (0) entre ruinas; árboles muertos (9) que brotan.
# =================================================
def _gen_imperial_ruins() -> List[List[int]]:
    g = [[4] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]

    # Patios centrales abiertos — zonas de hierba verde
    for y in range(6, 12):
        for x in range(7, 18):
            g[y][x] = 0

    # Corredor NE abierto (zona enemiga)
    for y in range(0, 6):
        for x in range(18, GRILLA_ANCHO):
            g[y][x] = 0

    # Corredor SW abierto (zona aliada)
    for y in range(12, GRILLA_ALTO):
        for x in range(0, 7):
            g[y][x] = 0

    # Ruina A — norte centro (L abierta al sur)
    for x in range(4, 13):
        g[0][x] = 2; g[4][x] = 2
    for y in range(0, 5):
        g[y][4] = 2; g[y][12] = 2
    g[4][7] = 0; g[4][8] = 0; g[4][9] = 0  # entrada sur
    for y in range(1, 4):
        for x in range(5, 12):
            g[y][x] = 4  # interior patio desgastado

    # Ruina B — norte derecha (rectangulo con brecha norte)
    for x in range(15, 24):
        g[5][x] = 2; g[9][x] = 2
    for y in range(5, 10):
        g[y][15] = 2
    g[5][19] = 0; g[5][20] = 0  # brecha norte-salida
    for y in range(6, 9):
        for x in range(16, 24):
            g[y][x] = 4

    # Ruina C — centro-izquierda (fragmentos de muro)
    for y in range(6, 12):
        g[y][2] = 2; g[y][5] = 2
    for x in range(2, 6):
        g[6][x] = 2
    g[9][2] = 0; g[10][5] = 4  # puertas

    # Ruina D — sur izquierda (muro incompleto)
    for x in range(3, 9):
        g[13][x] = 2
    for y in range(13, 17):
        g[y][8] = 2
    g[13][5] = 0; g[13][6] = 0  # entrada norte

    # Ruina E — sur centro-derecha (arco)
    for x in range(15, 22):
        g[14][x] = 2
    for y in range(14, 18):
        g[y][15] = 2; g[y][21] = 2
    g[14][17] = 0; g[14][18] = 0  # paso

    # Rocas (5) como escombros junto a las ruinas
    for (y, x) in [(3, 3), (5, 11), (10, 6), (10, 16), (12, 9), (12, 14), (16, 4)]:
        if 0 <= y < GRILLA_ALTO and 0 <= x < GRILLA_ANCHO and g[y][x] in (0, 4):
            g[y][x] = 5

    # Árboles muertos (9) brotando entre las piedras
    for (y, x) in [(2, 7), (2, 10), (7, 13), (8, 3), (11, 17), (15, 10), (16, 17)]:
        if 0 <= y < GRILLA_ALTO and 0 <= x < GRILLA_ANCHO and g[y][x] in (0, 4):
            g[y][x] = 9

    return g


# =================================================
# MAP 3 — Colinas de Piedra
# Dos cadenas de colinas rocosas (E y O) crean un valle central.
# Rocas (5) masivas en los flancos; bosque (1) en el valle;
# agua (3) en el fondo del barranco sur.
# =================================================
def _gen_stone_hills() -> List[List[int]]:
    g = _flat_e()

    # Cadena de colinas OESTE (cols 0-5, irregular)
    hill_west = [
        (0,0),(0,1),(0,2),(0,3),(0,4),
        (1,0),(1,1),(1,2),(1,3),
        (2,0),(2,1),(2,2),
        (3,0),(3,1),(3,2),(3,3),
        (4,0),(4,1),(4,2),(4,3),(4,4),
        (5,0),(5,1),(5,2),(5,3),
        (6,0),(6,1),(6,2),
        (7,0),(7,1),(7,2),(7,3),
        (8,0),(8,1),(8,2),(8,3),(8,4),
        (9,0),(9,1),(9,2),(9,3),
        (10,0),(10,1),(10,2),
        (11,0),(11,1),(11,2),(11,3),
        (12,0),(12,1),(12,2),(12,3),(12,4),
        (13,0),(13,1),(13,2),
        (14,0),(14,1),(14,2),(14,3),
        (15,0),(15,1),(15,2),(15,3),(15,4),
        (16,0),(16,1),(16,2),(16,3),
        (17,0),(17,1),(17,2),(17,3),(17,4),
    ]
    for (y, x) in hill_west:
        g[y][x] = 5

    # Cadena de colinas ESTE (cols 19-24, espejo aproximado)
    hill_east = [
        (0,20),(0,21),(0,22),(0,23),(0,24),
        (1,21),(1,22),(1,23),(1,24),
        (2,22),(2,23),(2,24),
        (3,21),(3,22),(3,23),(3,24),
        (4,20),(4,21),(4,22),(4,23),(4,24),
        (5,21),(5,22),(5,23),(5,24),
        (6,22),(6,23),(6,24),
        (7,21),(7,22),(7,23),(7,24),
        (8,20),(8,21),(8,22),(8,23),(8,24),
        (9,21),(9,22),(9,23),(9,24),
        (10,22),(10,23),(10,24),
        (11,21),(11,22),(11,23),(11,24),
        (12,20),(12,21),(12,22),(12,23),(12,24),
        (13,22),(13,23),(13,24),
        (14,21),(14,22),(14,23),(14,24),
        (15,20),(15,21),(15,22),(15,23),(15,24),
        (16,21),(16,22),(16,23),(16,24),
        (17,20),(17,21),(17,22),(17,23),(17,24),
    ]
    for (y, x) in hill_east:
        g[y][x] = 5

    # Bosque (1) flanqueando el valle central
    forest_pos = [
        (2,5),(3,5),(4,5),(5,4),(6,4),(7,4),(8,5),(9,4),(10,4),(11,4),(12,5),
        (2,19),(3,19),(4,19),(5,19),(6,19),(7,20),(8,19),(9,20),(10,20),(11,20),(12,19),
    ]
    for (y, x) in forest_pos:
        if g[y][x] == 0:
            g[y][x] = 1

    # Barranco húmedo sur (agua — fondo del desfiladero)
    for x in range(6, 19):
        g[16][x] = 3
    g[16][10] = 6; g[16][11] = 6; g[16][12] = 6; g[16][13] = 6

    # Rocas tácticas en el centro del valle
    tac_rocks = [(5,11),(5,13),(9,8),(9,16),(12,11),(12,13),(3,11),(3,13)]
    for (y, x) in tac_rocks:
        if g[y][x] == 0:
            g[y][x] = 5

    # Árboles muertos en bordes del barranco
    for (y, x) in [(15,6),(15,18),(14,7),(14,17),(17,5),(17,19)]:
        if g[y][x] == 0:
            g[y][x] = 9

    return g


# =================================================
# MAP 4 — Puerto Carmesí
# Costa en el sur (agua 3/6); muelles de hierba seca (4);
# edificios portuarios (muros 2); bosque (1) en tierra.
# Weather: rain
# =================================================
def _gen_crimson_port() -> List[List[int]]:
    g = _flat_e()

    # MAR / PUERTO — mitad sur (rows 11-17)
    for y in range(11, GRILLA_ALTO):
        for x in range(GRILLA_ANCHO):
            g[y][x] = 3
    # Agua profunda en el centro del puerto
    for y in range(13, 17):
        for x in range(8, 17):
            g[y][x] = 6

    # MUELLES (hierba seca 4) — piers de madera
    # Muelle principal (cols 10-14, rows 9-12)
    for y in range(9, 13):
        for x in range(10, 15):
            g[y][x] = 4
    # Muelle izquierdo (cols 3-6, rows 10-13)
    for y in range(10, 14):
        for x in range(3, 7):
            g[y][x] = 4
    # Muelle derecho (cols 18-21, rows 10-13)
    for y in range(10, 14):
        for x in range(18, 22):
            g[y][x] = 4

    # EDIFICIOS portuarios al norte (muros 2)
    # Almacén 1 (rows 1-4, cols 2-7)
    for x in range(2, 8):
        g[1][x] = 2; g[4][x] = 2
    for y in range(1, 5):
        g[y][2] = 2; g[y][7] = 2
    g[4][4] = 0; g[4][5] = 0  # entrada sur
    for y in range(2, 4):
        for x in range(3, 7):
            g[y][x] = 4  # interior

    # Almacén 2 (rows 1-4, cols 17-22)
    for x in range(17, 23):
        g[1][x] = 2; g[4][x] = 2
    for y in range(1, 5):
        g[y][17] = 2; g[y][22] = 2
    g[4][19] = 0; g[4][20] = 0
    for y in range(2, 4):
        for x in range(18, 22):
            g[y][x] = 4

    # Torre de vigilancia central (rows 1-3, cols 11-13)
    for x in range(11, 14):
        g[1][x] = 2; g[3][x] = 2
    g[1][11] = 2; g[1][13] = 2
    g[3][11] = 0; g[3][13] = 0
    g[2][12] = 4

    # Palizada costera (muros 2) separando tierra de muelles
    for x in range(0, 9):
        g[9][x] = 2
    for x in range(15, GRILLA_ANCHO):
        g[9][x] = 2
    g[9][0] = 0; g[9][8] = 0   # pasos laterales
    g[9][15] = 0; g[9][24] = 0

    # Bosque (1) costero al norte
    for (y, x) in [(5, 9), (6, 9), (5, 15), (6, 15),
                    (6, 3), (7, 3), (6, 21), (7, 21),
                    (7, 12), (8, 12)]:
        if g[y][x] == 0:
            g[y][x] = 1

    # Rocas (5) en la costa
    for (y, x) in [(10, 7), (10, 17), (11, 2), (11, 22), (12, 7), (12, 17)]:
        if g[y][x] in (3, 6):
            pass  # ya es agua
        elif g[y][x] == 0:
            g[y][x] = 5

    return g


# =================================================
# MAP 5 — Templo del Crepúsculo
# Planta simétrica de templo: hierba seca (4) como piedra;
# muros (2) formando columnatas y muros; agua (3) en los estanques
# rituales; árboles muertos (9) en el camino de entrada.
# =================================================
def _gen_dusk_temple() -> List[List[int]]:
    g = [[4] * GRILLA_ANCHO for _ in range(GRILLA_ALTO)]

    # Naos — patio central del templo
    for y in range(3, 10):
        for x in range(8, 17):
            g[y][x] = 0

    # Patio abierto sur (zona aliada)
    for y in range(12, GRILLA_ALTO):
        for x in range(5, 20):
            g[y][x] = 0

    # Patio abierto norte (zona enemiga)
    for y in range(0, 3):
        for x in range(5, 20):
            g[y][x] = 0

    # Columnata Norte (fila 3)
    for x in range(8, 17, 2):
        g[3][x] = 2
    # Columnata Sur del templo (fila 9)
    for x in range(8, 17, 2):
        g[9][x] = 2
    # Muros laterales del templo (cols 7 y 17, rows 3-9)
    for y in range(3, 10):
        g[y][7] = 2; g[y][17] = 2
    # Puertas en el muro lateral
    g[6][7] = 0; g[6][17] = 0

    # Muros exteriores norte (rows 0-2, cols 4 y 20)
    for y in range(3):
        g[y][4] = 2; g[y][20] = 2

    # Muros exteriores sur (rows 10-11, cols 4 y 20)
    for y in range(10, 12):
        g[y][4] = 2; g[y][20] = 2
    for x in range(4, 21):
        g[10][x] = 2
    # Entrada al patio sur
    g[10][10] = 0; g[10][11] = 0; g[10][12] = 0; g[10][13] = 0; g[10][14] = 0

    # Estanques rituales dentro del templo
    g[5][10] = 3; g[5][11] = 3; g[6][10] = 3; g[6][11] = 3
    g[5][13] = 3; g[5][14] = 3; g[6][13] = 3; g[6][14] = 3

    # Altar central (roca 5)
    g[4][12] = 5; g[5][12] = 5; g[6][12] = 5; g[7][12] = 5
    g[4][12] = 4  # recovecos del altar en seco

    # Árbol muerto en la avenida de entrada (cols 12, rows 11-17)
    for y in range(11, 16):
        if g[y][11] == 0:
            g[y][11] = 9
        if g[y][13] == 0:
            g[y][13] = 9

    # Columnas exteriores decorativas
    for (y, x) in [(1, 6), (1, 7), (1, 17), (1, 18),
                    (2, 4), (2, 20)]:
        if g[y][x] == 0:
            g[y][x] = 5

    return g


# =================================================
# MAP 6 — Desfiladero del Trueno
# Cañón estrecho: muros (2) en norte y sur de la cuadrícula
# crean un corredor forzado E-O; rocas (5) como cascotes dentro;
# árboles muertos (9) en las bocas del cañón.
# Weather: lightning
# =================================================
def _gen_thunder_pass() -> List[List[int]]:
    g = _flat_e()

    # Paredes del cañón NORTE (rows 0-4)
    for y in range(5):
        for x in range(GRILLA_ANCHO):
            g[y][x] = 2
    # Abrir bocas norte y pasos dentro del cañón
    for x in range(0, GRILLA_ANCHO):
        g[0][x] = 2
    # Pasos en la pared norte-interna (fila 4)
    for x in [3, 4, 9, 10, 14, 15, 19, 20]:
        g[4][x] = 0

    # Paredes del cañón SUR (rows 13-17)
    for y in range(13, GRILLA_ALTO):
        for x in range(GRILLA_ANCHO):
            g[y][x] = 2
    # Pasos en la pared sur-interna (fila 13)
    for x in [3, 4, 9, 10, 14, 15, 19, 20]:
        g[13][x] = 0

    # Corredor del cañón (rows 5-12) — hierba libre
    # Cascotes internos (rocas 5) — chokepoints tácticos
    cascade_rocks = [
        (5, 2), (5, 3), (5, 22), (5, 23),
        (6, 6), (6, 7), (6, 17), (6, 18),
        (7, 11), (7, 13),
        (8, 6), (8, 7), (8, 17), (8, 18),
        (9, 2), (9, 3), (9, 22), (9, 23),
        (10, 9), (10, 15),
        (11, 11), (11, 13),
        (12, 2), (12, 3), (12, 22), (12, 23),
    ]
    for (y, x) in cascade_rocks:
        if 0 <= y < GRILLA_ALTO and 0 <= x < GRILLA_ANCHO:
            g[y][x] = 5

    # Bosque (1) en los flancos del corredor — cobertura media
    forest_sides = [
        (5, 5), (6, 4), (7, 4), (8, 4), (9, 5), (10, 4), (11, 4), (12, 4),
        (5, 19), (6, 20), (7, 20), (8, 20), (9, 19), (10, 20), (11, 20), (12, 20),
    ]
    for (y, x) in forest_sides:
        if g[y][x] == 0:
            g[y][x] = 1

    # Árboles muertos (9) en bocas del cañón (atmósfera tormenta)
    for (y, x) in [(5, 0), (5, 1), (5, 24), (5, 23),
                    (12, 0), (12, 1), (12, 24), (12, 23),
                    (7, 12), (8, 12)]:
        if 0 <= y < GRILLA_ALTO and 0 <= x < GRILLA_ANCHO and g[y][x] == 0:
            g[y][x] = 9

    # Abrir filas 1-3 en zona aliada y enemiga (salida del cañón)
    # Zona aliada (SW): cols 0-5, rows 1-4 — mantener como walls del cañón
    # pero abrir un camino de acceso
    for y in range(1, 4):
        g[y][0] = 0; g[y][1] = 0  # salida oeste
    for y in range(1, 4):
        g[y][23] = 0; g[y][24] = 0  # salida este

    # Zona de zona segura aliada/enemiga: abrir rows 5-12 en cols 0-4 y 20-24
    # (ya son hierba salvo las rocas)

    return g


# =================================================
# REGISTRO
# =================================================
EXTRA_GENERATORS = {
    "corrupted_swamp":  _gen_corrupted_swamp,
    "imperial_ruins":   _gen_imperial_ruins,
    "stone_hills":      _gen_stone_hills,
    "crimson_port":     _gen_crimson_port,
    "dusk_temple":      _gen_dusk_temple,
    "thunder_pass":     _gen_thunder_pass,
}
