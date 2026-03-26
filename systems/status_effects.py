# systems/status_effects.py
# -------------------------------------------------
# Sistema de efectos de estado.
# Cada efecto tiene: nombre, duración, efecto por turno.
#
# Efectos disponibles:
#   veneno    — -5% HP max por turno
#   quemado   — -3 DEF durante 2 turnos
#   aturdido  — no puede moverse durante 1 turno
#   bendecido — +10 resistencia durante 3 turnos
#   robo_str  — -2 STR al objetivo, +2 STR al atacante

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class StatusEffect:
    nombre:    str          # ID interno ("veneno", "quemado", etc.)
    etiqueta:  str          # Nombre visible en UI ("Veneno", "Quemado")
    color:     tuple        # Color del ícono en UI
    duracion:  int          # Turnos restantes (-1 = permanente hasta curar)
    # Modificadores temporales de stats mientras el efecto está activo
    def_mod:   int = 0
    str_mod:   int = 0
    spd_mod:   int = 0
    # Flag de incapacidad de movimiento
    inmoviliza: bool = False


# =================================================
# CATÁLOGO DE EFECTOS
# =================================================

EFFECT_DEFS = {
    "veneno": {
        "etiqueta": "Veneno",
        "color":    (120, 200, 50),
        "duracion": -1,     # permanente hasta curar con antídoto
        "def_mod":  0,
    },
    "quemado": {
        "etiqueta": "Quemado",
        "color":    (255, 100, 30),
        "duracion": 2,
        "def_mod":  -3,
    },
    "aturdido": {
        "etiqueta":    "Aturdido",
        "color":       (200, 200, 50),
        "duracion":    1,
        "inmoviliza":  True,
    },
    "bendecido": {
        "etiqueta": "Bendecido",
        "color":    (220, 220, 255),
        "duracion": 3,
        "def_mod":  3,
    },
    "robo_str": {
        "etiqueta": "Debilitado",
        "color":    (180, 50, 180),
        "duracion": 2,
        "str_mod":  -2,
    },
    "fortalecido": {
        "etiqueta": "Fortalecido",
        "color":    (255, 180, 50),
        "duracion": 3,
        "str_mod":  3,
    },
}


def make_effect(nombre: str, duracion_override: int | None = None) -> StatusEffect | None:
    """Construye un StatusEffect desde el catálogo. Retorna None si el ID no existe."""
    d = EFFECT_DEFS.get(nombre)
    if not d:
        print(f"[StatusEffects] ID desconocido: '{nombre}'")
        return None
    dur = duracion_override if duracion_override is not None else d["duracion"]
    return StatusEffect(
        nombre     = nombre,
        etiqueta   = d["etiqueta"],
        color      = d["color"],
        duracion   = dur,
        def_mod    = d.get("def_mod", 0),
        str_mod    = d.get("str_mod", 0),
        spd_mod    = d.get("spd_mod", 0),
        inmoviliza = d.get("inmoviliza", False),
    )


# =================================================
# LÓGICA DE PROCESAMIENTO
# =================================================

def apply_effect_to_unit(unit, effect_nombre: str, duracion: int | None = None):
    """
    Aplica un efecto de estado a una unidad.
    Si ya tiene el mismo efecto, renueva la duración.
    """
    if not hasattr(unit, "efectos"):
        unit.efectos = []

    # Renovar si ya existe
    for ef in unit.efectos:
        if ef.nombre == effect_nombre:
            if duracion is not None:
                ef.duracion = duracion
            elif EFFECT_DEFS.get(effect_nombre, {}).get("duracion", 1) > 0:
                ef.duracion = EFFECT_DEFS[effect_nombre]["duracion"]
            return

    ef = make_effect(effect_nombre, duracion)
    if ef:
        unit.efectos.append(ef)


def remove_effect(unit, effect_nombre: str):
    """Elimina un efecto por nombre."""
    if hasattr(unit, "efectos"):
        unit.efectos = [e for e in unit.efectos if e.nombre != effect_nombre]


def process_turn_effects(unit, add_fx=None):
    """
    Llamar al INICIO del turno de la unidad.
    - Aplica daño de veneno
    - Reduce duración de todos los efectos
    - Elimina efectos expirados
    """
    if not hasattr(unit, "efectos"):
        unit.efectos = []
        return

    expired = []
    for ef in unit.efectos:
        # Efecto de veneno: -5% HP max por turno
        if ef.nombre == "veneno":
            dmg = max(1, unit.max_hp // 20)  # 5% redondeado
            unit.hp_actual = max(1, unit.hp_actual - dmg)
            if add_fx:
                add_fx(unit.x * 32, unit.y * 32, f"Veneno -{dmg}", ef.color, 14, 1)

        # Reducir duración (si no es permanente)
        if ef.duracion > 0:
            ef.duracion -= 1
            if ef.duracion <= 0:
                expired.append(ef)

    for ef in expired:
        unit.efectos.remove(ef)
        if add_fx:
            add_fx(unit.x * 32, unit.y * 32, f"{ef.etiqueta} terminó", (200, 200, 200), 12, 1)


def get_stat_mods(unit) -> dict:
    """
    Retorna dict de modificadores de stats activos por efectos de estado.
    Ejemplo: {"def_mod": -3, "str_mod": 0, "spd_mod": 0}
    """
    mods = {"def_mod": 0, "str_mod": 0, "spd_mod": 0}
    if not hasattr(unit, "efectos"):
        return mods
    for ef in unit.efectos:
        mods["def_mod"] += ef.def_mod
        mods["str_mod"] += ef.str_mod
        mods["spd_mod"] += ef.spd_mod
    return mods


def is_stunned(unit) -> bool:
    """Retorna True si la unidad está aturdida (no puede moverse)."""
    if not hasattr(unit, "efectos"):
        return False
    return any(ef.inmoviliza for ef in unit.efectos)


def has_effect(unit, nombre: str) -> bool:
    if not hasattr(unit, "efectos"):
        return False
    return any(ef.nombre == nombre for ef in unit.efectos)
