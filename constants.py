# constants.py
# -----------------------------------------
# Config general
ANCHO_PANTALLA = 800
ALTO_PANTALLA = 600
TITULO = "ETERNIA: Victoria y Conquista"
TAMANO_TILE = 32

GRILLA_ANCHO = ANCHO_PANTALLA // TAMANO_TILE
GRILLA_ALTO = ALTO_PANTALLA // TAMANO_TILE

# Colores
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
GRIS_OSCURO = (30, 30, 30)

AZUL_RANGO = (0, 100, 255, 80)
ROJO_ATAQUE = (255, 0, 0, 80)
VERDE_RANGO_SKILL = (0, 255, 0, 80)

ROJO_CURSOR = (255, 50, 50)
AMARILLO_CURSOR = (255, 255, 50)

GRIS_INACTIVO = (100, 100, 100)

VERDE_HP = (50, 255, 50)
ROJO_HP = (200, 50, 50)
AZUL_MP = (80, 150, 255)

AMARILLO_AWK = (255, 215, 0)

FONDO_UI = (20, 25, 40)
BORDE_UI = (200, 200, 200)

AZUL_EXP = (100, 220, 255)
DORADO_COFRE = (255, 215, 0)

PURPURA_TRONO = (148, 0, 211)  # Trono

# Sprites / Animación
TILE_ORIGINAL_SIZE = 16   # tamaño original de cada frame en el pack (16×16 mini world)
ANIM_SPEED_MAP     = 18   # ticks de juego por frame de animación en mapa (~3fps a 60fps)
ANIM_SPEED_FX      = 3    # ticks de juego por frame de animación FX (~20fps a 60fps)

# Terreno
# costo: puntos de movimiento que cuesta entrar
# esquive: bonus de esquive (%) que da al defensor que está en esta casilla
INFO_TERRENO = {
    0: {"color": (100, 220, 100), "costo": 1,   "esquive": 0},   # Hierba
    1: {"color": (30, 120, 30),   "costo": 2,   "esquive": 20},  # Bosque
    2: {"color": (120, 120, 120), "costo": 999, "esquive": 0},   # Muro/Montaña (impassable)
    3: {"color": (50, 100, 200),  "costo": 999, "esquive": 0},   # Agua (impassable)
}
