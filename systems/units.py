# systems/units.py
# -------------------------------------------------
# Clase Unidad (runtime) + catálogo desde JSON + factory.
# Nuevos stats: habilidad (skl), velocidad (spd), suerte (lck), magia (mag).
# El sprite se carga via sprite_loader con fallback automático.

import random

import constants as C
from systems.items import make_item, make_skill
from systems.status_effects import (
    apply_effect_to_unit, remove_effect, process_turn_effects,
    get_stat_mods, is_stunned, has_effect
)
from loaders.data_loader import load_units


# =================================================
# AWAKENINGS POR CLASE
# =================================================

_AWAKENING_APPLY = {
    "PALADIN": lambda u: _mod(u, str=+5, def_=+5, mov=+2),
    "CLERIC":  lambda u: None,   # El efecto del clérigo lo maneja el combate
    "ARCHER":  lambda u: _mod(u, spd=+4, skl=+6),
    "BERSERKER":lambda u:_mod(u, str=+8, def_=-3),
    "MAGE":    lambda u: _mod(u, mag=+6),
    "basic":   lambda u: _mod(u, str=+5, def_=+5, mov=+2),  # fallback legacy
}

_AWAKENING_REMOVE = {
    "PALADIN": lambda u: _mod(u, str=-5, def_=-5, mov=-2),
    "CLERIC":  lambda u: None,
    "ARCHER":  lambda u: _mod(u, spd=-4, skl=-6),
    "BERSERKER":lambda u:_mod(u, str=-8, def_=+3),
    "MAGE":    lambda u: _mod(u, mag=-6),
    "basic":   lambda u: _mod(u, str=-5, def_=-5, mov=-2),
}


def _mod(unit, str=0, def_=0, mov=0, spd=0, skl=0, mag=0):
    unit.fuerza   += str
    unit.defensa  += def_
    unit.movimiento += mov
    unit.velocidad  += spd
    unit.habilidad  += skl
    unit.magia      += mag


def apply_awakening(unit):
    t = unit.awakening_type
    fn = _AWAKENING_APPLY.get(t)
    if fn:
        fn(unit)


def remove_awakening(unit):
    t = unit.awakening_type
    fn = _AWAKENING_REMOVE.get(t)
    if fn:
        fn(unit)


# =================================================
# CLASE UNIDAD
# =================================================

class Unidad:
    def __init__(
        self, x, y, nombre, bando,
        movimiento, max_hp, max_mp,
        fuerza, defensa, mag=0, velocidad=5, habilidad=4, suerte=3,
        inventario=None, habilidades=None,
        skill_progression=None,
        es_heroe=False, awakening_type=None,
        add_floating_text=None, unit_id=None,
        sprite_id=None, color_base=None,
        crecimientos=None, clase="Unidad",
    ):
        self.x, self.y = x, y
        self.nombre    = nombre
        self.bando     = bando
        self.clase     = clase
        self.unit_id   = unit_id
        self.sprite_id = sprite_id or (unit_id or "").lower()

        # Stats base
        self.movimiento = movimiento
        self.max_hp     = max_hp
        self.hp_actual  = max_hp
        self.max_mp     = max(0, max_mp)
        self.mp_actual  = self.max_mp
        self.fuerza     = fuerza
        self.defensa    = defensa
        self.magia      = mag
        self.velocidad  = velocidad
        self.habilidad  = habilidad
        self.suerte     = suerte

        # Progresión
        self.nivel = 1
        self.exp   = 0
        self.crecimientos = crecimientos or {
            "hp": 60, "fuerza": 50, "defensa": 30,
            "spd": 40, "skl": 35, "lck": 30,
        }
        # Ganancias acumuladas por level-up (sin incluir bonos de reliquias).
        # Permite restaurar correctamente el nivel al cambiar de mapa.
        self._level_gains: dict = {
            "max_hp": 0, "fuerza": 0, "defensa": 0,
            "velocidad": 0, "habilidad": 0, "suerte": 0,
        }

        # Inventario
        self.inventario    = inventario or []
        self.arma_equipada = None
        for it in self.inventario:
            if it.tipo == "arma":
                self.arma_equipada = it
                break

        self.habilidades = habilidades or []
        # dict: nivel (int) → skill_id (str) — habilidades aprendidas por subida de nivel
        self._skill_progression: dict = {
            int(k): v for k, v in (skill_progression or {}).items()
        }

        # Estado de turno
        self.ha_actuado = False

        # Awakening
        self.es_heroe        = es_heroe
        self.awakening_type  = awakening_type
        self.awakening_meter = 0
        self.awakened        = False
        self.awakening_timer = 0

        # Efectos de estado
        self.efectos = []

        # Vínculos (Bond System) — unit_id → nivel (1-3)
        self.vinculos: dict = {}

        # FX callback
        self.add_floating_text = add_floating_text

        # Color para fallback y barras
        if color_base:
            self.color_base = color_base
        elif bando == "aliado":
            self.color_base = (50, 80, 220)
        elif bando == "enemigo":
            self.color_base = (200, 60, 60)
        else:
            self.color_base = (255, 165, 0)

    # -------------------------
    # Helpers básicos
    # -------------------------
    def esta_viva(self):
        return self.hp_actual > 0

    def resetear_turno(self):
        self.ha_actuado = False

    def puede_moverse(self):
        return not is_stunned(self)

    def get_poder_ataque(self):
        """Fuerza + poder del arma equipada."""
        return self.fuerza + (self.arma_equipada.poder if self.arma_equipada else 0)

    def get_defensa_efectiva(self):
        """Defensa base + modificadores de efectos de estado."""
        mods = get_stat_mods(self)
        return max(0, self.defensa + mods["def_mod"])

    def get_velocidad_efectiva(self):
        mods = get_stat_mods(self)
        return max(0, self.velocidad + mods["spd_mod"])

    def get_tipo_arma(self):
        """Retorna tipo_arma del arma equipada o None."""
        if self.arma_equipada:
            return getattr(self.arma_equipada, "tipo_arma", None)
        return None

    # -------------------------
    # FX helper
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
                self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE, "MAX!", C.AMARILLO_AWK)

    def activar_awakening(self):
        if self.es_heroe and self.awakening_type and self.awakening_meter >= 100:
            self.awakened        = True
            self.awakening_timer = 3
            self.awakening_meter = 0
            apply_awakening(self)
            self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE - 10, "AWAKENING!", C.AMARILLO_AWK, tamaño=24)

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
        self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE, "Fin Poder", C.BLANCO)

    # -------------------------
    # Efectos de estado
    # -------------------------
    def procesar_efectos_turno(self):
        process_turn_effects(self, add_fx=self.add_floating_text)

    def aplicar_efecto(self, nombre: str):
        apply_effect_to_unit(self, nombre)

    def remover_efecto(self, nombre: str):
        remove_effect(self, nombre)

    def tiene_efecto(self, nombre: str) -> bool:
        return has_effect(self, nombre)

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
            # Curación de HP
            recup = min(item.cura, self.max_hp - self.hp_actual)
            self.hp_actual += recup
            if recup > 0:
                self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE, f"+{recup}", C.VERDE_HP)

            # Curación de estado
            if getattr(item, "cura_estado", None):
                self.remover_efecto(item.cura_estado)
                self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE - 16,
                         f"¡{item.cura_estado.capitalize()} curado!", C.BLANCO, 14)

            self.inventario.pop(idx)
            return True
        return False

    # -------------------------
    # Habilidades
    # -------------------------
    def usar_habilidad(self, habilidad, objetivo):
        if self.mp_actual < habilidad.costo_mp:
            self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE, "NO MP", C.GRIS_INACTIVO)
            return False

        self.mp_actual -= habilidad.costo_mp
        import random as _rnd

        if habilidad.tipo_efecto == "daño":
            atk_stat = max(self.fuerza, self.magia)  # usa el mayor
            daño = max(0, (atk_stat + habilidad.poder) - objetivo.get_defensa_efectiva())
            objetivo.hp_actual -= daño
            self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE - 20, habilidad.nombre, C.AZUL_MP)
            self._fx(objetivo.x * C.TAMANO_TILE, objetivo.y * C.TAMANO_TILE, str(daño), C.BLANCO)

            # Aplicar efecto de estado con probabilidad
            if habilidad.efecto_estado and _rnd.randint(1, 100) <= habilidad.efecto_prob:
                objetivo.aplicar_efecto(habilidad.efecto_estado)
                self._fx(objetivo.x * C.TAMANO_TILE, objetivo.y * C.TAMANO_TILE - 16,
                         habilidad.efecto_estado.capitalize(), (150, 255, 100), 13)

            self.ganar_awakening(20)
            objetivo.ganar_awakening(10)

            if not objetivo.esta_viva():
                self.ganar_exp(50)
            else:
                self.ganar_exp(20)

        elif habilidad.tipo_efecto == "curar":
            cura = habilidad.poder + (self.magia // 2) + (self.fuerza // 4)
            curado_real = min(cura, objetivo.max_hp - objetivo.hp_actual)
            objetivo.hp_actual += curado_real
            self._fx(objetivo.x * C.TAMANO_TILE, objetivo.y * C.TAMANO_TILE, f"+{curado_real}", C.VERDE_HP)
            self.ganar_exp(25)

        elif habilidad.tipo_efecto == "buff":
            if habilidad.efecto_estado:
                objetivo.aplicar_efecto(habilidad.efecto_estado)
                self._fx(objetivo.x * C.TAMANO_TILE, objetivo.y * C.TAMANO_TILE,
                         habilidad.efecto_estado.capitalize(), (200, 200, 255), 14)
            self.ganar_exp(15)

        return True

    # -------------------------
    # EXP / Level up
    # -------------------------
    def ganar_exp(self, c):
        if self.bando == "enemigo":
            return
        self.exp += c
        self._fx(self.x * C.TAMANO_TILE + 16, self.y * C.TAMANO_TILE, f"+{c} XP", C.AZUL_EXP, tamaño=14)
        while self.exp >= 100:
            self.exp -= 100
            self.subir_nivel()

    def apply_skill_progression(self, max_nivel: int):
        """Otorga todas las habilidades de progresión hasta max_nivel.
        Es idempotente: no duplica habilidades ya presentes.
        Llamar tras restaurar nivel desde snapshot o al subir nivel."""
        ids_actuales = {getattr(h, "id", None) for h in self.habilidades}
        for nivel_req in sorted(self._skill_progression.keys()):
            if nivel_req > max_nivel:
                break
            skill_id = self._skill_progression[nivel_req]
            if skill_id not in ids_actuales:
                nueva = make_skill(skill_id)
                if nueva:
                    self.habilidades.append(nueva)
                    ids_actuales.add(skill_id)
                    self._fx(
                        self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE - 36,
                        f"+ {nueva.nombre}", C.AMARILLO_AWK, tamaño=14,
                    )

    def subir_nivel(self):
        self.nivel += 1
        self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE - 20, "LEVEL UP!", C.AMARILLO_AWK, tamaño=22)
        self.hp_actual = self.max_hp
        self.mp_actual = self.max_mp

        mejoras = []
        c = self.crecimientos
        if random.randint(1, 100) <= c.get("hp", 60):
            self.max_hp += 1; self._level_gains["max_hp"] += 1; mejoras.append("HP")
        if random.randint(1, 100) <= c.get("fuerza", 50):
            self.fuerza += 1; self._level_gains["fuerza"] += 1; mejoras.append("STR")
        if random.randint(1, 100) <= c.get("defensa", 30):
            self.defensa += 1; self._level_gains["defensa"] += 1; mejoras.append("DEF")
        if random.randint(1, 100) <= c.get("spd", 40):
            self.velocidad += 1; self._level_gains["velocidad"] += 1; mejoras.append("SPD")
        if random.randint(1, 100) <= c.get("skl", 35):
            self.habilidad += 1; self._level_gains["habilidad"] += 1; mejoras.append("SKL")
        if random.randint(1, 100) <= c.get("lck", 30):
            self.suerte += 1; self._level_gains["suerte"] += 1; mejoras.append("LCK")
        if mejoras:
            self._fx(self.x * C.TAMANO_TILE, self.y * C.TAMANO_TILE - 40,
                     " ".join(mejoras), C.BLANCO, tamaño=12)

        # Desbloquear habilidades de progresión para el nuevo nivel
        self.apply_skill_progression(self.nivel)

    # -------------------------
    # Render (sprite o fallback)
    # -------------------------
    def dibujar(self, surf, font):
        import pygame
        from loaders.sprite_loader import get_unit_map_sprite

        px = self.x * C.TAMANO_TILE
        py = self.y * C.TAMANO_TILE

        # Obtener sprite (con fallback automático)
        sprite = get_unit_map_sprite(self.sprite_id, self.bando, self.color_base)

        # Si está inactivo, oscurecer el sprite
        if self.ha_actuado:
            sombra = sprite.copy()
            sombra.fill((80, 80, 80, 180), special_flags=pygame.BLEND_RGBA_MULT)
            surf.blit(sombra, (px, py))
        else:
            surf.blit(sprite, (px, py))

        # Halo dorado si está en Awakening
        if self.awakened:
            pygame.draw.rect(surf, C.AMARILLO_AWK, (px, py, C.TAMANO_TILE, C.TAMANO_TILE), 2)

        cx = px + C.TAMANO_TILE // 2
        cy = py + C.TAMANO_TILE // 2

        # HP bar (debajo del sprite)
        bar_y = py + C.TAMANO_TILE - 5
        pct_hp = max(0.0, self.hp_actual / self.max_hp)
        hp_color = C.VERDE_HP if pct_hp > 0.5 else (C.AMARILLO_AWK if pct_hp > 0.25 else C.ROJO_HP)
        pygame.draw.rect(surf, C.NEGRO,  (px, bar_y, C.TAMANO_TILE, 4))
        pygame.draw.rect(surf, C.ROJO_HP,(px+1, bar_y+1, C.TAMANO_TILE-2, 2))
        pygame.draw.rect(surf, hp_color, (px+1, bar_y+1, int((C.TAMANO_TILE-2) * pct_hp), 2))

        # MP bar
        if self.max_mp > 0:
            pct_mp = max(0.0, self.mp_actual / self.max_mp)
            pygame.draw.rect(surf, C.NEGRO,  (px, bar_y - 4, C.TAMANO_TILE, 3))
            pygame.draw.rect(surf, C.AZUL_MP,(px+1, bar_y - 3, int((C.TAMANO_TILE-2) * pct_mp), 1))

        # Awakening bar (héroe)
        if self.es_heroe and self.awakening_type:
            pct_awk = self.awakening_meter / 100
            pygame.draw.rect(surf, C.NEGRO,     (px, py + 1, C.TAMANO_TILE, 3))
            pygame.draw.rect(surf, C.AMARILLO_AWK, (px+1, py+2, int((C.TAMANO_TILE-2) * pct_awk), 1))

        # Ícono de nivel (pequeño, esquina superior derecha)
        lv_txt = font.render(str(self.nivel), True, C.BLANCO)
        surf.blit(lv_txt, (px + C.TAMANO_TILE - lv_txt.get_width() - 1, py + 1))

        # Íconos de efectos de estado (puntos de color)
        for i, ef in enumerate(self.efectos[:4]):
            ex = px + 2 + i * 7
            ey = py + C.TAMANO_TILE - 12
            pygame.draw.circle(surf, ef.color, (ex, ey), 3)


# =================================================
# CATÁLOGO Y FACTORY
# =================================================

_DEFAULT_UNIT_CATALOG = {
    "HERO_ALLY":    {"nombre":"Kael",    "clase":"Paladin",  "mov":5, "hp":32,"mp":20,"str":9,"def":5,"mag":2,"spd":7,"skl":6,"lck":5, "items":["SWORD_IRON","POTION"],  "skills":["FEROCIOUS_STRIKE"],"is_hero":True, "awakening_type":"PALADIN",  "sprite":"kael",      "color_fallback":[50,80,220]},
    "CLERIC_ALLY":  {"nombre":"Lyra",    "clase":"Cleriga",  "mov":4, "hp":20,"mp":35,"str":4,"def":2,"mag":8,"spd":5,"skl":4,"lck":7, "items":[],                       "skills":["HEAL"],            "is_hero":False,"awakening_type":"CLERIC",   "sprite":"lyra",      "color_fallback":[220,220,80]},
    "ARCHER_ALLY":  {"nombre":"Ryn",     "clase":"Arquero",  "mov":5, "hp":22,"mp":15,"str":7,"def":3,"mag":1,"spd":9,"skl":8,"lck":6, "items":["BOW_IRON"],             "skills":["PIERCING_SHOT"],   "is_hero":False,"awakening_type":"ARCHER",   "sprite":"ryn",       "color_fallback":[80,200,80]},
    "BANDIT_ENEMY": {"nombre":"Bandido", "clase":"Bandido",  "mov":5, "hp":26,"mp":10,"str":8,"def":3,"mag":0,"spd":6,"skl":4,"lck":2, "items":["AXE_IRON"],             "skills":[],                  "is_hero":False,"awakening_type":None,       "sprite":"bandit",    "color_fallback":[200,60,60]},
    "ORC_ENEMY":    {"nombre":"Orco",    "clase":"Orco",     "mov":4, "hp":38,"mp":10,"str":10,"def":5,"mag":0,"spd":4,"skl":3,"lck":1,"items":["LANCE_IRON"],            "skills":[],                  "is_hero":False,"awakening_type":None,       "sprite":"orc",       "color_fallback":[160,40,40]},
    "MAGE_ENEMY":   {"nombre":"Mago Oscuro","clase":"Mago",  "mov":4, "hp":20,"mp":40,"str":3,"def":2,"mag":9,"spd":6,"skl":7,"lck":4, "items":["STAFF_DARK"],           "skills":["DARK_BOLT"],       "is_hero":False,"awakening_type":None,       "sprite":"dark_mage", "color_fallback":[120,20,180]},
    "DUMMY_HP":     {"nombre":"Saco HP", "clase":"Objeto",   "mov":0, "hp":100,"mp":0,"str":0,"def":0,"mag":0,"spd":0,"skl":0,"lck":0, "items":[],                       "skills":[],                  "is_hero":False,"awakening_type":None,       "sprite":"dummy",     "color_fallback":[120,120,120]},
}


def _build_unit_catalog() -> dict:
    catalog = {**_DEFAULT_UNIT_CATALOG}
    json_cat = load_units()
    if json_cat:
        catalog.update(json_cat)
    return catalog


UNIT_CATALOG = _build_unit_catalog()


def make_unit(unit_id: str, x: int, y: int, bando: str,
              add_floating_text=None) -> "Unidad":
    if unit_id not in UNIT_CATALOG:
        raise ValueError(f"[units] Unit ID inválido: '{unit_id}'. Disponibles: {list(UNIT_CATALOG.keys())}")

    d = UNIT_CATALOG[unit_id]
    inv    = [make_item(i)  for i in d.get("items",  [])]
    skills = [make_skill(s) for s in d.get("skills", [])]
    skill_prog = d.get("skill_progression", {})

    crec_raw = d.get("crecimientos", {})
    crec = {
        "hp":      crec_raw.get("hp",  60),
        "fuerza":  crec_raw.get("str", crec_raw.get("fuerza", 50)),
        "defensa": crec_raw.get("def", crec_raw.get("defensa", 30)),
        "spd":     crec_raw.get("spd", 40),
        "skl":     crec_raw.get("skl", 35),
        "lck":     crec_raw.get("lck", 30),
    }

    return Unidad(
        x=x, y=y,
        nombre       = d["nombre"],
        bando        = bando,
        clase        = d.get("clase", "Unidad"),
        movimiento   = d["mov"],
        max_hp       = d["hp"],
        max_mp       = d.get("mp", 0),
        fuerza       = d.get("str", d.get("fuerza", 5)),
        defensa      = d.get("def", d.get("defensa", 2)),
        mag          = d.get("mag", 0),
        velocidad    = d.get("spd", 5),
        habilidad    = d.get("skl", 4),
        suerte       = d.get("lck", 3),
        inventario         = inv,
        habilidades        = skills,
        skill_progression  = skill_prog,
        es_heroe           = d.get("is_hero", False),
        awakening_type = d.get("awakening_type"),
        add_floating_text = add_floating_text,
        unit_id      = unit_id,
        sprite_id    = d.get("sprite", unit_id.lower()),
        color_base   = tuple(d["color_fallback"]) if d.get("color_fallback") else None,
        crecimientos = crec,
    )
