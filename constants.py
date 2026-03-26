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

# UI Persona 5-style (combat menus — kept for legacy / P5 sections)
PERSONA_BLACK  = (8,   8,  14)
PERSONA_RED    = (210, 18,  18)
PERSONA_WHITE  = (245, 245, 250)
PERSONA_GOLD   = (255, 210,  40)
PERSONA_PANEL  = (12,  12,  22)
PERSONA_STRIP  = (180, 15,  15)
PERSONA_ALLY   = (30,  90, 200)
PERSONA_ENEMY  = (200, 25,  25)

# UI Persona 3 Reload-style palette
P3R_NAVY       = (6,   13,  26)   # fondo principal profundo
P3R_PANEL      = (10,  20,  40)   # paneles semitransparentes
P3R_BLUE_MID   = (20,  60, 120)   # azul medio para gradientes
P3R_TEAL       = (0,  200, 212)   # acento cian/teal principal
P3R_TEAL_DIM   = (0,  100, 120)   # teal apagado para bordes y separadores
P3R_DARK_TEAL  = (0,   40,  55)   # teal muy oscuro para fondos de separador
P3R_WHITE      = (220, 235, 255)  # texto (blanco frío)
P3R_GOLD       = (255, 210,  80)  # dorado para críticos / highlights
P3R_ALLY       = (40,  110, 230)  # azul eléctrico bando aliado
P3R_ENEMY      = (180,  40,  60)  # rojo oscuro bando enemigo
P3R_HP_HIGH    = (60,  220, 180)  # barra HP alta (verde-teal)
P3R_HP_MID     = (220, 180,  40)  # barra HP media (dorado)
P3R_HP_LOW     = (220,  60,  60)  # barra HP baja (rojo)
P3R_MP_BAR     = (60,  140, 255)  # barra MP (azul eléctrico)

# Sprites / Animación
TILE_ORIGINAL_SIZE = 16   # tamaño original de cada frame en el pack (16×16 mini world)
ANIM_SPEED_MAP     = 18   # ticks de juego por frame de animación en mapa (~3fps a 60fps)
ANIM_SPEED_FX      = 3    # ticks de juego por frame de animación FX (~20fps a 60fps)

# Terreno
# costo: puntos de movimiento que cuesta entrar
# esquive: bonus de esquive (%) que da al defensor que está en esta casilla
INFO_TERRENO = {
    0: {"color": (100, 220, 100), "costo": 1,   "esquive": 0},   # Hierba
    1: {"color": (30,  120,  30), "costo": 2,   "esquive": 20},  # Bosque
    2: {"color": (120, 120, 120), "costo": 999, "esquive": 0},   # Muro/Montaña (impassable)
    3: {"color": (50,  100, 200), "costo": 999, "esquive": 0},   # Agua (impassable)
    4: {"color": (165, 170,  90), "costo": 1,   "esquive": 0},   # Hierba Seca / Arena
    5: {"color": (100,  90,  75), "costo": 999, "esquive": 0},   # Rocas pequeñas (impassable)
    6: {"color": (20,   55, 165), "costo": 999, "esquive": 0},   # Agua Profunda (impassable)
    7: {"color": (218, 230, 242), "costo": 1,   "esquive": 0},   # Suelo Nevado
    8: {"color": (185, 212, 228), "costo": 2,   "esquive": 20},  # Árboles Invernales
    9: {"color": (75,   65,  48), "costo": 1,   "esquive": 8},   # Árboles Muertos
}
