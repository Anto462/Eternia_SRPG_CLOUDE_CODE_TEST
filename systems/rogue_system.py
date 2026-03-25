# systems/rogue_system.py
# -------------------------------------------------
# Sistema Roguelike para EterniaSrpg.
#
# Flujo:
#   MENU_PRINCIPAL
#     → MENU_SELECCION_GRUPO  (elegir 2-3 héroes del pool)
#     → MAPA (combate normal)
#     → VICTORIA → MENU_MEJORAS  (elegir 1 de 3 reliquias)
#     → SIGUIENTE MAPA  ...  hasta derrota
#
# Reliquias: bonus pasivos acumulables por run.
# Se aplican a todos los aliados al elegirlas.

import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# =================================================
# POOL DE HÉROES SELECCIONABLES
# =================================================

@dataclass
class HeroOption:
    unit_id:     str
    nombre:      str
    clase:       str
    descripcion: str
    color:       tuple   # color representativo para la UI


HERO_POOL: List[HeroOption] = [
    HeroOption("HERO_ALLY",   "Kael",   "Paladín",   "Héroe equilibrado. Alto HP y DEF.",          (80, 120, 220)),
    HeroOption("CLERIC_ALLY", "Lyra",   "Clérigo",   "Soporte y curación. Magia defensiva.",        (200, 180, 60)),
    HeroOption("ARCHER_ALLY", "Ryn",    "Arquero",   "Alto alcance y velocidad. Frágil.",           (80, 200, 80)),
    HeroOption("THERON_ALLY", "Theron", "Arquero",   "Precisión extrema. Más FUE y SKL que Ryn.",  (80, 200, 80)),
    HeroOption("MIRA_ALLY",   "Mira",   "Asesina",   "Velocidad extrema. Baja DEF.",                (180, 80, 180)),
    HeroOption("ZEPH_ALLY",   "Zeph",   "Mago",      "Gran poder mágico. Sin contraataque físico.", (60, 200, 200)),
    HeroOption("ALDRIC_ALLY", "Aldric", "Caballero", "Montado. Alto movimiento y fuerza.",          (220, 140, 40)),
]

MIN_HEROES = 2
MAX_HEROES = 3


# =================================================
# RELIQUIAS
# =================================================

@dataclass
class Relic:
    relic_id:    str
    nombre:      str
    descripcion: str
    color:       tuple
    # Modificadores que se aplican a cada aliado
    hp_bonus:    int   = 0
    mp_bonus:    int   = 0
    str_bonus:   int   = 0
    def_bonus:   int   = 0
    spd_bonus:   int   = 0
    mov_bonus:   int   = 0
    # Efectos especiales (flags para game_state)
    revive_once: bool  = False   # Revive con 1HP una vez por mapa
    crit_boost:  int   = 0      # +X% crit global
    score_mult:  float = 1.0    # Multiplicador de puntuación


ALL_RELICS: List[Relic] = [
    Relic("corazon_piedra", "Corazón de Piedra",
          "+15 HP máx. a todos los aliados.",
          (150, 80, 80), hp_bonus=15),

    Relic("sigilo_elfico", "Sigilo Élfico",
          "+2 VEL a todos los aliados.",
          (80, 200, 120), spd_bonus=2),

    Relic("filo_caos", "Filo del Caos",
          "+4 FUE pero -1 DEF a todos los aliados.",
          (220, 60, 60), str_bonus=4, def_bonus=-1),

    Relic("phylactery", "Phylactery",
          "Al caer en combate, revive con 1HP (una vez por mapa).",
          (120, 60, 180), revive_once=True),

    Relic("botas_mercurio", "Botas de Mercurio",
          "+1 movimiento a todos los aliados.",
          (60, 180, 220), mov_bonus=1),

    Relic("orbe_magia", "Orbe de Magia",
          "+10 MP máx. a todos los aliados.",
          (80, 100, 220), mp_bonus=10),

    Relic("ojo_critico", "Ojo Crítico",
          "+10% probabilidad de crítico global.",
          (220, 200, 40), crit_boost=10),

    Relic("caliz_guerra", "Cáliz de Guerra",
          "+2 FUE y +2 DEF a todos los aliados.",
          (200, 140, 40), str_bonus=2, def_bonus=2),

    Relic("escudo_ancestral", "Escudo Ancestral",
          "+5 DEF y +5 HP máx. a todos los aliados.",
          (100, 140, 220), def_bonus=5, hp_bonus=5),

    Relic("talisman_suerte", "Talismán de la Suerte",
          "×1.5 multiplicador de puntuación esta run.",
          (240, 200, 60), score_mult=1.5),
]


# =================================================
# ESTADO DE LA RUN ROGUELIKE
# =================================================

@dataclass
class RogueRunState:
    selected_heroes: List[str]          = field(default_factory=list)  # unit_ids
    acquired_relics: List[Relic]        = field(default_factory=list)
    score_multiplier: float             = 1.0
    # Snapshot de stats de cada héroe vivo al terminar un mapa.
    # key = unit_id, value = dict con stats + nivel + exp + _level_gains.
    # Al crear nuevas unidades en _load_map se restauran estos valores y
    # solo se aplican las reliquias adquiridas DESDE la última snapshot.
    hero_snapshots: Dict[str, dict]     = field(default_factory=dict)
    # Cuántas reliquias había cuando se guardó la última snapshot.
    # Permite aplicar solo las reliquias nuevas al restaurar.
    snapshot_relic_count: int           = 0

    def add_relic(self, relic: Relic):
        self.acquired_relics.append(relic)
        self.score_multiplier *= relic.score_mult

    def apply_relic_to_unit_single(self, relic: "Relic", unit):
        """Aplica el bonus de una sola reliquia a una unidad aliada."""
        r = relic
        if r.hp_bonus:
            unit.max_hp    = max(1, unit.max_hp + r.hp_bonus)
            unit.hp_actual = min(unit.hp_actual + r.hp_bonus, unit.max_hp)
        if r.mp_bonus:
            unit.max_mp    = max(0, unit.max_mp + r.mp_bonus)
            unit.mp_actual = min(unit.mp_actual + r.mp_bonus, unit.max_mp)
        if r.str_bonus:
            unit.fuerza    = max(1, unit.fuerza  + r.str_bonus)
        if r.def_bonus:
            unit.defensa   = max(0, unit.defensa  + r.def_bonus)
        if r.spd_bonus:
            v = getattr(unit, "velocidad", 5)
            unit.velocidad = max(1, v + r.spd_bonus)
        if r.mov_bonus:
            unit.movimiento = max(1, unit.movimiento + r.mov_bonus)
        if r.crit_boost:
            current = getattr(unit, "crit_bonus_global", 0)
            unit.crit_bonus_global = current + r.crit_boost

    def apply_relics_to_unit(self, unit):
        """Aplica todos los bonus de reliquias a una unidad aliada."""
        for r in self.acquired_relics:
            if r.hp_bonus:
                unit.max_hp    = max(1, unit.max_hp + r.hp_bonus)
                unit.hp_actual = min(unit.hp_actual + r.hp_bonus, unit.max_hp)
            if r.mp_bonus:
                unit.max_mp    = max(0, unit.max_mp + r.mp_bonus)
                unit.mp_actual = min(unit.mp_actual + r.mp_bonus, unit.max_mp)
            if r.str_bonus:
                unit.fuerza   = max(1, unit.fuerza  + r.str_bonus)
            if r.def_bonus:
                unit.defensa  = max(0, unit.defensa  + r.def_bonus)
            if r.spd_bonus:
                v = getattr(unit, "velocidad", 5)
                unit.velocidad = max(1, v + r.spd_bonus)
            if r.mov_bonus:
                unit.movimiento = max(1, unit.movimiento + r.mov_bonus)
            if r.crit_boost:
                current = getattr(unit, "crit_bonus_global", 0)
                unit.crit_bonus_global = current + r.crit_boost


# =================================================
# SELECCIÓN DE MEJORAS
# =================================================

def pick_relic_choices(acquired: List[Relic], count: int = 3) -> List[Relic]:
    """Devuelve `count` reliquias aleatorias distintas (sin repetir adquiridas)."""
    acquired_ids = {r.relic_id for r in acquired}
    pool = [r for r in ALL_RELICS if r.relic_id not in acquired_ids]
    if not pool:
        pool = list(ALL_RELICS)  # si ya tiene todo, permite repetir
    random.shuffle(pool)
    return pool[:min(count, len(pool))]


# =================================================
# SELECCIÓN DE HEROES UI HELPERS
# =================================================

def get_hero_pool() -> List[HeroOption]:
    return list(HERO_POOL)
