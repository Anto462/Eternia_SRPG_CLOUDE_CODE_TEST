# core/pathfinding.py
# -------------------------------------------------
# BFS con costo de terreno + esquive de terreno.
# No toca pygame ni UI.

from collections import deque
import constants as C

GRILLA_ANCHO = C.GRILLA_ANCHO
GRILLA_ALTO  = C.GRILLA_ALTO
INFO_TERRENO = C.INFO_TERRENO


def build_occupancy(unidades, include_dead: bool = False) -> dict:
    occ = {}
    for u in unidades:
        if not include_dead and not u.esta_viva():
            continue
        occ[(u.x, u.y)] = u
    return occ


def obtener_movimientos_validos(unidad, mapa, unidades) -> list:
    """
    BFS por costo de terreno.
    Respeta: bloqueo por unidades, terreno infranqueable, stunned (sin mov).
    """
    from systems.status_effects import is_stunned
    if is_stunned(unidad):
        return []

    occ   = build_occupancy(unidades)
    start = (unidad.x, unidad.y)

    cola      = deque([(start[0], start[1], 0)])
    costo_min = {start: 0}
    resultado = []

    while cola:
        cx, cy, costo_acum = cola.popleft()

        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = cx + dx, cy + dy

            if not (0 <= nx < GRILLA_ANCHO and 0 <= ny < GRILLA_ALTO):
                continue

            tipo_tile  = mapa[ny][nx]
            costo_tile = INFO_TERRENO[tipo_tile]["costo"]
            nuevo_costo = costo_acum + costo_tile

            if nuevo_costo > unidad.movimiento:
                continue

            if (nx, ny) in occ and (nx, ny) != start:
                continue

            if (nx, ny) not in costo_min or nuevo_costo < costo_min[(nx, ny)]:
                costo_min[(nx, ny)] = nuevo_costo
                cola.append((nx, ny, nuevo_costo))
                if (nx, ny) != start:
                    resultado.append((nx, ny))

    return resultado


def get_terrain_esquive(mapa, x: int, y: int) -> int:
    """
    Retorna el bonus de esquive del terreno en (x,y).
    0 = hierba, 20 = bosque, 30 = montaña, etc.
    """
    if 0 <= y < len(mapa) and 0 <= x < len(mapa[0]):
        tipo = mapa[y][x]
        return INFO_TERRENO.get(tipo, {}).get("esquive", 0)
    return 0
