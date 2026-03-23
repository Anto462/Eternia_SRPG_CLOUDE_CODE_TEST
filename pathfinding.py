# pathfinding.py
# -------------------------------------------------
# Aquí va todo lo relacionado a movimiento en grilla:
# - BFS con costo de terreno
# - Bloqueo por casillas ocupadas
#
# La idea es que esto NO toque pygame, ni UI.
# Solo devuelve listas de coordenadas válidas.

from collections import deque
import constants as C

GRILLA_ANCHO = C.GRILLA_ANCHO
GRILLA_ALTO = C.GRILLA_ALTO
INFO_TERRENO = C.INFO_TERRENO


def build_occupancy(unidades, include_dead=False):
    """
    Crea un dict de ocupación del tablero.
    - key: (x,y)
    - value: Unidad

    include_dead=False significa que ignoramos unidades muertas.
    """
    occ = {}
    for u in unidades:
        if not include_dead and not u.esta_viva():
            continue
        occ[(u.x, u.y)] = u
    return occ


def obtener_movimientos_validos(unidad, mapa, unidades):
    """
    BFS por costo de terreno.
    Reglas:
    - NO puedes pasar por encima de unidades (aliadas o enemigas o neutrales).
    - NO puedes terminar en una casilla ocupada (excepto tu casilla inicial).
    - Sí puedes "ver" tu casilla actual siempre.

    Retorna: lista de (x,y) donde la unidad puede moverse.
    """
    occ = build_occupancy(unidades)

    start = (unidad.x, unidad.y)
    cola = deque([(start[0], start[1], 0)])
    costo_min = {start: 0}
    resultado = []

    while cola:
        cx, cy, costo_acum = cola.popleft()

        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy

            # bounds
            if not (0 <= nx < GRILLA_ANCHO and 0 <= ny < GRILLA_ALTO):
                continue

            # costo del terreno (si es 999 prácticamente es pared)
            tipo_tile = mapa[ny][nx]
            costo_tile = INFO_TERRENO[tipo_tile]["costo"]
            nuevo_costo = costo_acum + costo_tile

            if nuevo_costo > unidad.movimiento:
                continue

            # bloqueo por ocupación:
            # - si la casilla está ocupada y NO es tu inicio, no puedes entrar ni pasar por ahí
            if (nx, ny) in occ and (nx, ny) != start:
                continue

            # relajación típica de BFS con pesos pequeños
            if (nx, ny) not in costo_min or nuevo_costo < costo_min[(nx, ny)]:
                costo_min[(nx, ny)] = nuevo_costo
                cola.append((nx, ny, nuevo_costo))

                # añadimos como destino válido (si no es start)
                if (nx, ny) != start:
                    resultado.append((nx, ny))

    return resultado
