# systems/items.py
# -------------------------------------------------
# Clase Item y Habilidad + catálogos + factories.
# El catálogo se carga desde JSON (data/items/).
# Si el JSON no existe, usa defaults hardcodeados.

from loaders.data_loader import load_items, load_skills


# =================================================
# CLASES
# =================================================

class Item:
    def __init__(self, nombre, tipo, tipo_arma=None, poder=0,
                 rango=(1, 1), cura=0, precision_bonus=0,
                 critico_bonus=0, cura_estado=None, icono=None):
        self.nombre         = nombre
        self.tipo           = tipo          # "arma" | "consumible"
        self.tipo_arma      = tipo_arma     # "espada" | "hacha" | "lanza" | "arco" | "magia" | None
        self.poder          = poder
        self.rango          = tuple(rango) if isinstance(rango, list) else rango
        self.cura           = cura
        self.precision_bonus = precision_bonus
        self.critico_bonus  = critico_bonus
        self.cura_estado    = cura_estado   # cura este estado si es consumible
        self.icono          = icono or nombre.lower().replace(" ", "_")

    def __repr__(self):
        return f"<Item {self.nombre} [{self.tipo}]>"


class Habilidad:
    def __init__(self, nombre, costo_mp, rango, poder, tipo_efecto,
                 efecto_estado=None, efecto_prob=0, icono=None):
        self.nombre        = nombre
        self.costo_mp      = costo_mp
        self.rango         = tuple(rango) if isinstance(rango, list) else rango
        self.poder         = poder
        self.tipo_efecto   = tipo_efecto    # "daño" | "curar" | "buff"
        self.efecto_estado = efecto_estado  # nombre del estado que puede aplicar
        self.efecto_prob   = efecto_prob    # % de probabilidad de aplicar estado
        self.icono         = icono or nombre.lower().replace(" ", "_")

    def __repr__(self):
        return f"<Habilidad {self.nombre} [{self.tipo_efecto}]>"


# =================================================
# CATÁLOGOS (default hardcoded)
# =================================================

_DEFAULT_ITEMS = {
    "SWORD_IRON":  {"nombre": "Espada",       "tipo": "arma",       "tipo_arma": "espada", "poder": 5,  "rango": [1,1], "precision_bonus": 0,   "critico_bonus": 0},
    "SWORD_STEEL": {"nombre": "Espada Acero",  "tipo": "arma",       "tipo_arma": "espada", "poder": 8,  "rango": [1,1], "precision_bonus": -5,  "critico_bonus": 0},
    "AXE_IRON":    {"nombre": "Hacha",         "tipo": "arma",       "tipo_arma": "hacha",  "poder": 8,  "rango": [1,1], "precision_bonus": -10, "critico_bonus": 5},
    "LANCE_IRON":  {"nombre": "Lanza",         "tipo": "arma",       "tipo_arma": "lanza",  "poder": 6,  "rango": [1,1], "precision_bonus": 5,   "critico_bonus": 0},
    "LANCE_SILVER":{"nombre": "Lanza Plata",   "tipo": "arma",       "tipo_arma": "lanza",  "poder": 10, "rango": [1,1], "precision_bonus": 5,   "critico_bonus": 5},
    "BOW_IRON":    {"nombre": "Arco",          "tipo": "arma",       "tipo_arma": "arco",   "poder": 6,  "rango": [2,3], "precision_bonus": 5,   "critico_bonus": 0},
    "STAFF_DARK":  {"nombre": "Bastón Oscuro", "tipo": "arma",       "tipo_arma": "magia",  "poder": 7,  "rango": [1,2], "precision_bonus": 5,   "critico_bonus": 0},
    "POTION":      {"nombre": "Poción",        "tipo": "consumible", "tipo_arma": None,     "poder": 0,  "rango": [0,0], "cura": 20},
    "POTION_G":    {"nombre": "Poción Grande", "tipo": "consumible", "tipo_arma": None,     "poder": 0,  "rango": [0,0], "cura": 35},
    "ANTIDOTE":    {"nombre": "Antídoto",      "tipo": "consumible", "tipo_arma": None,     "poder": 0,  "rango": [0,0], "cura": 5, "cura_estado": "veneno"},
}

_DEFAULT_SKILLS = {
    "FEROCIOUS_STRIKE": {"nombre": "Golpe Feroz",     "costo_mp": 5,  "rango": [1,1], "poder": 9,  "tipo": "daño"},
    "HEAL":             {"nombre": "Sanar",            "costo_mp": 8,  "rango": [1,2], "poder": 15, "tipo": "curar"},
    "DARK_BOLT":        {"nombre": "Rayo Oscuro",      "costo_mp": 10, "rango": [1,3], "poder": 10, "tipo": "daño",  "efecto_estado": "veneno", "efecto_prob": 30},
    "PIERCING_SHOT":    {"nombre": "Disparo Certero",  "costo_mp": 6,  "rango": [2,4], "poder": 8,  "tipo": "daño"},
    "RALLY":            {"nombre": "Inspirar",         "costo_mp": 12, "rango": [1,2], "poder": 0,  "tipo": "buff",  "efecto_estado": "bendecido"},
}


def _build_catalog() -> tuple[dict, dict]:
    """
    Construye los catálogos fusionando defaults + JSON.
    El JSON tiene prioridad (permite override sin tocar código).
    """
    item_cat = {**_DEFAULT_ITEMS}
    skill_cat = {**_DEFAULT_SKILLS}

    json_items = load_items()
    if json_items:
        item_cat.update(json_items)

    json_skills = load_skills()
    if json_skills:
        skill_cat.update(json_skills)

    return item_cat, skill_cat


ITEM_CATALOG, SKILL_CATALOG = _build_catalog()


# =================================================
# FACTORIES
# =================================================

def make_item(item_id: str) -> Item:
    if item_id not in ITEM_CATALOG:
        raise ValueError(f"[items] Item ID inválido: '{item_id}'. Disponibles: {list(ITEM_CATALOG.keys())}")
    d = ITEM_CATALOG[item_id]
    return Item(
        nombre          = d["nombre"],
        tipo            = d["tipo"],
        tipo_arma       = d.get("tipo_arma"),
        poder           = d.get("poder", 0),
        rango           = d.get("rango", [1, 1]),
        cura            = d.get("cura", 0),
        precision_bonus = d.get("precision_bonus", 0),
        critico_bonus   = d.get("critico_bonus", 0),
        cura_estado     = d.get("cura_estado"),
        icono           = d.get("icono"),
    )


def make_skill(skill_id: str) -> Habilidad:
    if skill_id not in SKILL_CATALOG:
        raise ValueError(f"[items] Skill ID inválido: '{skill_id}'. Disponibles: {list(SKILL_CATALOG.keys())}")
    d = SKILL_CATALOG[skill_id]
    return Habilidad(
        nombre        = d["nombre"],
        costo_mp      = d["costo_mp"],
        rango         = d["rango"],
        poder         = d["poder"],
        tipo_efecto   = d.get("tipo", d.get("tipo_efecto", "daño")),
        efecto_estado = d.get("efecto_estado"),
        efecto_prob   = d.get("efecto_prob", 0),
        icono         = d.get("icono"),
    )
