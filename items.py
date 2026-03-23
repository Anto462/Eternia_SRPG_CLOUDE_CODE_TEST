# items.py
# -------------------------------------------------
# Este módulo se encarga de:
# - Definir las clases Item y Habilidad
# - Mantener un catálogo centralizado de ítems y habilidades
# - Proveer factories (make_item / make_skill)
#
# La idea es que el juego NUNCA cree ítems "a mano"
# sino siempre a partir de un ID del catálogo.
#
# Esto hace que:
# - Agregar nuevos ítems sea trivial
# - El balance se ajuste sin tocar lógica
# - Los mapas y personajes solo referencien IDs


# -------------------------
# CLASE ITEM
# -------------------------
class Item:
    def __init__(self, nombre, tipo, poder=0, rango=(1, 1), cura=0):
        """
        nombre: string visible ("Espada", "Poción G", etc.)
        tipo: "arma" | "consumible" | (futuro: "pasivo", "armadura")
        poder: daño extra si es arma
        rango: (min, max) para armas
        cura: HP que recupera si es consumible
        """
        self.nombre = nombre
        self.tipo = tipo
        self.poder = poder
        self.rango = rango
        self.cura = cura


# -------------------------
# CLASE HABILIDAD
# -------------------------
class Habilidad:
    def __init__(self, nombre, costo_mp, rango, poder, tipo_efecto):
        """
        nombre: string visible
        costo_mp: MP requerido
        rango: (min, max) distancia Manhattan
        poder: daño o curación base
        tipo_efecto: "daño" | "curar"
        """
        self.nombre = nombre
        self.costo_mp = costo_mp
        self.rango = rango
        self.poder = poder
        self.tipo_efecto = tipo_efecto


# =================================================
# CATÁLOGO DE ÍTEMS
# =================================================
# IMPORTANTE:
# - La KEY es el ID interno (lo usan mapas y personajes)
# - El contenido es solo data, no lógica
# - Si mañana quieres balancear algo, se hace aquí

ITEM_CATALOG = {

    # ---------- ARMAS ----------
    "SWORD_IRON": {
        "nombre": "Espada",
        "tipo": "arma",
        "poder": 5,
        "rango": (1, 1)
    },

    "AXE_IRON": {
        "nombre": "Hacha",
        "tipo": "arma",
        "poder": 7,
        "rango": (1, 1)
    },

    "LANCE_IRON": {
        "nombre": "Lanza",
        "tipo": "arma",
        "poder": 6,
        "rango": (1, 1)
    },

    "LANCE_SILVER": {
        "nombre": "Lanza Plata",
        "tipo": "arma",
        "poder": 10,
        "rango": (1, 1)
    },

    # ---------- CONSUMIBLES ----------
    "POTION": {
        "nombre": "Poción",
        "tipo": "consumible",
        "cura": 20
    },

    "POTION_G": {
        "nombre": "Poción G",
        "tipo": "consumible",
        "cura": 30
    },
}


# =================================================
# CATÁLOGO DE HABILIDADES
# =================================================
# Igual que los ítems:
# - Data pura
# - Fácil de extender
# - Cada habilidad tiene identidad clara

SKILL_CATALOG = {

    "FEROCIOUS_STRIKE": {
        "nombre": "Golpe Feroz",
        "costo_mp": 5,
        "rango": (1, 1),
        "poder": 8,
        "tipo": "daño"
    },

    "HEAL": {
        "nombre": "Sanar",
        "costo_mp": 8,
        "rango": (1, 2),
        "poder": 15,
        "tipo": "curar"
    },
}


# =================================================
# FACTORIES
# =================================================
# Estas funciones son CLAVE.
# Todo el juego debería crear ítems/habilidades usando esto,
# nunca instanciando Item() o Habilidad() directamente.

def make_item(item_id):
    """
    Crea una instancia de Item a partir del ID del catálogo.
    """
    if item_id not in ITEM_CATALOG:
        raise ValueError(f"Item ID inválido: {item_id}")

    d = ITEM_CATALOG[item_id]

    return Item(
        nombre=d["nombre"],
        tipo=d["tipo"],
        poder=d.get("poder", 0),
        rango=d.get("rango", (1, 1)),
        cura=d.get("cura", 0)
    )


def make_skill(skill_id):
    """
    Crea una instancia de Habilidad a partir del ID del catálogo.
    """
    if skill_id not in SKILL_CATALOG:
        raise ValueError(f"Skill ID inválido: {skill_id}")

    d = SKILL_CATALOG[skill_id]

    return Habilidad(
        nombre=d["nombre"],
        costo_mp=d["costo_mp"],
        rango=d["rango"],
        poder=d["poder"],
        tipo_efecto=d["tipo"]
    )
