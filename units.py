# units.py
# -------------------------------------------------
# Este módulo se encarga de:
# - Definir la clase Unidad (runtime: HP actual, mp actual, acted, etc.)
# - Tener un catálogo de unidades (data pura)
# - Tener un factory para construir una Unidad desde un ID
#
# OJO con el tema spawn:
# - El MAPA define dónde spawnea cada cosa (coords + unit_id)
# - units.py solo "construye" la unidad con sus stats/items/skills


import random

# Importamos tamaños/colores que usa dibujar() y agregar_texto
from constants import (
    TAMANO_TILE,
    BLANCO,
    NEGRO,
    GRIS_INACTIVO,
    VERDE_HP,
    ROJO_HP,
    AZUL_MP,
    AMARILLO_AWK,
    AZUL_EXP,
)

# Importamos factories de items/skills (IDs -> instancias)
from items import make_item, make_skill


# =================================================
# CATÁLOGO DE UNIDADES
# =================================================
# Aquí no va lógica, solo data.
# Si quieres agregar un personaje nuevo, lo agregas aquí y listo.

UNIT_CATALOG = {

    # ----------- ALIADOS -----------
    "HERO_ALLY": {
        "nombre": "Héroe",
        "mov": 5, "hp": 30, "mp": 20, "str": 8, "def": 5,
        "items": ["SWORD_IRON", "POTION"],
        "skills": ["FEROCIOUS_STRIKE"],
        "is_hero": True,
        "awakening_type": "basic"
    },

    "CLERIC_ALLY": {
        "nombre": "Clérigo",
        "mov": 4, "hp": 18, "mp": 30, "str": 5, "def": 2,
        "items": [],
        "skills": ["HEAL"],
        "is_hero": False,
        "awakening_type": None
    },

    # ----------- ENEMIGOS -----------
    "BANDIT_ENEMY": {
        "nombre": "Bandido",
        "mov": 5, "hp": 25, "mp": 10, "str": 7, "def": 3,
        "items": ["AXE_IRON"],
        "skills": [],
        "is_hero": False,
        "awakening_type": None
    },

    "ORC_ENEMY": {
        "nombre": "Orco",
        "mov": 4, "hp": 35, "mp": 10, "str": 9, "def": 4,
        "items": ["LANCE_IRON"],
        "skills": [],
        "is_hero": False,
        "awakening_type": None
    },

    "DUMMY_HP": {
        "nombre": "Saco HP",
        "mov": 0, "hp": 100, "mp": 10, "str": 0, "def": 0,
        "items": [],
        "skills": [],
        "is_hero": False,
        "awakening_type": None
    },
}


# =================================================
# AWAKENINGS (TIPOS)
# =================================================
# Esto te evita meter 20 ifs dentro de Unidad.
# En el futuro puedes meter más estilos de awakening aquí.

def apply_awakening(unit):
    """
    Aplica el awakening según unit.awakening_type.
    """
    t = unit.awakening_type
    if t == "basic":
        unit.fuerza += 5
        unit.defensa += 5
        unit.movimiento += 2
    # Aquí puedes meter otros:
    # elif t == "berserk": ...


def remove_awakening(unit):
    """
    Revierte el awakening según unit.awakening_type.
    """
    t = unit.awakening_type
    if t == "basic":
        unit.fuerza -= 5
        unit.defensa -= 5
        unit.movimiento -= 2


# =================================================
# CLASE UNIDAD
# =================================================
class Unidad:
    def __init__(
        self,
        x,
        y,
        nombre,
        bando,
        movimiento,
        max_hp,
        max_mp,
        fuerza,
        defensa,
        inventario=None,
        habilidades=None,
        es_heroe=False,
        awakening_type=None,
        add_floating_text=None,   # función callback: agregar_texto(...)
        unit_id=None
    ):
        # Pos
        self.x, self.y = x, y

        # Identidad
        self.nombre = nombre
        self.bando = bando

        # Stats
        self.movimiento = movimiento
        self.max_hp = max_hp
        self.hp_actual = max_hp

        self.max_mp = max(10, max_mp)
        self.mp_actual = self.max_mp

        self.fuerza = fuerza
        self.defensa = defensa

        # Progresión
        self.nivel = 1
        self.exp = 0

        # Growths (igual que tu prototipo)
        self.crecimientos = {"hp": 60, "fuerza": 50, "defensa": 30}

        # Inventario / arma
        self.inventario = inventario if inventario else []
        self.arma_equipada = None
        for it in self.inventario:
            if it.tipo == "arma":
                self.arma_equipada = it
                break

        # Skills
        self.habilidades = habilidades if habilidades else []

        # Turnos
        self.ha_actuado = False

        # Hero / Awakening
        self.es_heroe = es_heroe
        self.awakening_type = awakening_type
        self.awakening_meter = 0
        self.awakened = False
        self.awakening_timer = 0

        #ID
        self.unit_id = unit_id

        # Hook para textos flotantes (así no hacemos import circular con UI)
        self.add_floating_text = add_floating_text

        # Color por bando (igual que tu base)
        if bando == "aliado":
            self.color_base = (50, 50, 255)
        elif bando == "enemigo":
            self.color_base = (220, 50, 50)
        else:
            self.color_base = (255, 165, 0)
        

    # -------------------------
    # Helpers básicos
    # -------------------------
    def esta_viva(self):
        return self.hp_actual > 0

    def resetear_turno(self):
        self.ha_actuado = False

    def get_poder_ataque(self):
        return self.fuerza + (self.arma_equipada.poder if self.arma_equipada else 0)

    # -------------------------
    # Textos flotantes (si están conectados)
    # -------------------------
    def _fx(self, x, y, texto, color, tamaño=20, velocidad_y=1):
        if self.add_floating_text:
            self.add_floating_text(x, y, texto, color, tamaño, velocidad_y)

    # -------------------------
    # Awakening
    # -------------------------
    def ganar_awakening(self, cantidad):
        if self.es_heroe and not self.awakened and self.awakening_type:
            self.awakening_meter = min(100, self.awakening_meter + cantidad)
            if self.awakening_meter == 100:
                self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE, "MAX!", AMARILLO_AWK)

    def activar_awakening(self):
        if self.es_heroe and self.awakening_type and self.awakening_meter >= 100:
            self.awakened = True
            self.awakening_timer = 3
            self.awakening_meter = 0
            apply_awakening(self)
            self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE - 10, "AWAKENING!", AMARILLO_AWK, tamaño=24)

    def procesar_turno_awakening(self):
        if self.awakened:
            self.awakening_timer -= 1
            if self.awakening_timer <= 0:
                self.desactivar_awakening()

    def desactivar_awakening(self):
        if not self.awakened:
            return
        self.awakened = False
        remove_awakening(self)
        self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE, "FIN PODER", BLANCO)

    # -------------------------
    # Inventario
    # -------------------------
    def equipar_item(self, idx):
        item = self.inventario[idx]
        if item.tipo == "arma":
            self.arma_equipada = item
            return True
        return False

    def usar_item(self, idx):
        item = self.inventario[idx]
        if item.tipo == "consumible":
            recup = min(item.cura, self.max_hp - self.hp_actual)
            self.hp_actual += recup
            self.inventario.pop(idx)
            self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE, str(recup), VERDE_HP)
            return True
        return False

    # -------------------------
    # Habilidades (igual a tu lógica)
    # -------------------------
    def usar_habilidad(self, habilidad, objetivo):
        if self.mp_actual < habilidad.costo_mp:
            self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE, "NO MP", GRIS_INACTIVO)
            return False

        self.mp_actual -= habilidad.costo_mp

        if habilidad.tipo_efecto == "daño":
            daño = max(0, (self.fuerza + habilidad.poder) - objetivo.defensa)
            objetivo.hp_actual -= daño
            self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE - 20, habilidad.nombre, AZUL_MP)
            self._fx(objetivo.x * TAMANO_TILE, objetivo.y * TAMANO_TILE, str(daño), BLANCO)

            self.ganar_awakening(20)
            objetivo.ganar_awakening(10)

            if not objetivo.esta_viva():
                self.ganar_exp(50)
            else:
                self.ganar_exp(20)

        elif habilidad.tipo_efecto == "curar":
            cura = habilidad.poder + (self.fuerza // 2)
            curado_real = min(cura, objetivo.max_hp - objetivo.hp_actual)
            objetivo.hp_actual += curado_real
            self._fx(objetivo.x * TAMANO_TILE, objetivo.y * TAMANO_TILE, str(curado_real), VERDE_HP)
            self.ganar_exp(25)

        return True

    # -------------------------
    # EXP / Level up
    # -------------------------
    def ganar_exp(self, c):
        if self.bando == "enemigo":
            return
        self.exp += c
        self._fx(self.x * TAMANO_TILE + 16, self.y * TAMANO_TILE, f"+{c} XP", AZUL_EXP, tamaño=14)
        if self.exp >= 100:
            self.exp -= 100
            self.subir_nivel()

    def subir_nivel(self):
        self.nivel += 1
        self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE - 20, "LEVEL UP!", AMARILLO_AWK, tamaño=22)

        # full restore como tu base
        self.hp_actual = self.max_hp
        self.mp_actual = self.max_mp

        mejora = ""
        if random.randint(1, 100) <= self.crecimientos["hp"]:
            self.max_hp += 1
            mejora += "HP "
        if random.randint(1, 100) <= self.crecimientos["fuerza"]:
            self.fuerza += 1
            mejora += "STR "
        if random.randint(1, 100) <= self.crecimientos["defensa"]:
            self.defensa += 1
            mejora += "DEF "
        if mejora:
            self._fx(self.x * TAMANO_TILE, self.y * TAMANO_TILE - 40, mejora, BLANCO, tamaño=12)

    # -------------------------
    # Render (lo dejamos igualito, pero aquí o en ui.py luego)
    # -------------------------
    def dibujar(self, sup, font):
        # Nota: esto todavía usa pygame.draw, pero está bien por ahora.
        import pygame

        px, py = self.x * TAMANO_TILE + 16, self.y * TAMANO_TILE + 16
        color = (255, 255, 150) if self.awakened else self.color_base
        if self.ha_actuado:
            color = GRIS_INACTIVO

        pygame.draw.circle(sup, (0, 0, 0, 100), (px, py + 8), 10)
        pygame.draw.circle(sup, color, (px, py), 12)
        if self.awakened:
            pygame.draw.circle(sup, AMARILLO_AWK, (px, py), 16, 2)

        # HP bar
        pct_hp = max(0, self.hp_actual / self.max_hp)
        pygame.draw.rect(sup, NEGRO, (px - 13, py - 23, 26, 6))
        pygame.draw.rect(sup, ROJO_HP, (px - 12, py - 22, 24, 4))
        pygame.draw.rect(sup, VERDE_HP, (px - 12, py - 22, 24 * pct_hp, 4))

        # MP bar
        if self.max_mp > 0:
            pct_mp = max(0, self.mp_actual / self.max_mp)
            pygame.draw.rect(sup, NEGRO, (px - 13, py - 18, 26, 4))
            pygame.draw.rect(sup, AZUL_MP, (px - 12, py - 17, 24 * pct_mp, 2))

        # Awakening bar
        if self.es_heroe and self.awakening_type:
            pct_awk = self.awakening_meter / 100
            pygame.draw.rect(sup, NEGRO, (px - 13, py - 14, 26, 3))
            pygame.draw.rect(sup, AMARILLO_AWK, (px - 12, py - 13, 24 * pct_awk, 1))

        # Nivel + letra del arma
        sup.blit(font.render(str(self.nivel), True, BLANCO), (px + 6, py - 28))
        if self.arma_equipada:
            sup.blit(font.render(self.arma_equipada.nombre[0], True, (200, 200, 200)), (px - 10, py + 5))


# =================================================
# FACTORY: construir Unidad desde ID
# =================================================
def make_unit(unit_id, x, y, bando, add_floating_text=None):
    """
    Construye una Unidad usando UNIT_CATALOG.
    El mapa decide el "dónde" y "qué id".
    Esta función solo arma el objeto con items/skills/awakening.
    """
    if unit_id not in UNIT_CATALOG:
        raise ValueError(f"Unit ID inválido: {unit_id}")

    d = UNIT_CATALOG[unit_id]

    inv = [make_item(item_id) for item_id in d.get("items", [])]
    skills = [make_skill(skill_id) for skill_id in d.get("skills", [])]

    return Unidad(
        x=x,
        y=y,
        nombre=d["nombre"],
        bando=bando,
        movimiento=d["mov"],
        max_hp=d["hp"],
        max_mp=d["mp"],
        fuerza=d["str"],
        defensa=d["def"],
        inventario=inv,
        habilidades=skills,
        es_heroe=d.get("is_hero", False),
        awakening_type=d.get("awakening_type", None),
        add_floating_text=add_floating_text,
        unit_id=unit_id,
    )
