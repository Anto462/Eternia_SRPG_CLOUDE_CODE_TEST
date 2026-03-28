# systems/shop_system.py
# -------------------------------------------------------
# Tienda Permanente — mejoras que persisten entre runs.
# Compras se guardan en data/shop_progress.json.
# La moneda se gana al terminar una run (victoria o derrota)
# en proporción al puntaje obtenido (1 moneda cada 100 pts).
# -------------------------------------------------------

from __future__ import annotations
import os, json
from dataclasses import dataclass, field
from typing import List, Set

_DATA      = os.path.join(os.path.dirname(__file__), "..", "data")
_SHOP_FILE = os.path.join(_DATA, "shop_progress.json")


@dataclass
class ShopItem:
    item_id:     str
    name:        str
    description: str
    price:       int
    # Bonificaciones acumulables (se suman con otros ítems comprados)
    hp:          int   = 0     # +HP máximo a todos los héroes
    mp:          int   = 0     # +MP máximo a todos los héroes
    strength:    int   = 0     # +Fuerza a todos los héroes
    defense:     int   = 0     # +Defensa a todos los héroes
    speed:       int   = 0     # +Velocidad a todos los héroes
    movement:    int   = 0     # +Movimiento a todos los héroes
    # Bonificaciones especiales (no acumulables — máximo del slot)
    start_level: int   = 0     # Nivel mínimo al inicio de run
    coin_bonus:  float = 0.0   # Fracción extra de monedas por run (ej. 0.25 = +25%)


# -------------------------------------------------------
# Catálogo — 15 mejoras permanentes
# Economía: 1 run media (~10.000 pts) → ~100 monedas.
#   Baratos (75-150): accesibles en 1-2 runs.
#   Medios (180-280): 2-3 runs.
#   Caros (300-500): 4-6 runs dedicadas.
# -------------------------------------------------------
SHOP_ITEMS: List[ShopItem] = [
    # ── Tier I: económicas ────────────────────────────────────────────────
    ShopItem(
        "IRON_BLOOD", "Sangre de Hierro",
        "+8 HP máximo a todos los héroes al iniciar run",
        price=75, hp=8
    ),
    ShopItem(
        "STONE_SKIN", "Piel de Piedra",
        "+2 DEF permanente a todos los héroes",
        price=90, defense=2
    ),
    ShopItem(
        "MANA_FONT", "Fuente de Maná",
        "+10 MP máximo a todos los héroes",
        price=100, mp=10
    ),
    ShopItem(
        "WAR_DRUMS", "Tambores de Guerra",
        "+3 STR permanente a todos los héroes",
        price=115, strength=3
    ),
    ShopItem(
        "COIN_MAGNET", "Imán de Monedas",
        "+25% de monedas al terminar cada run",
        price=140, coin_bonus=0.25
    ),
    # ── Tier II: moderadas ────────────────────────────────────────────────
    ShopItem(
        "SWIFT_BOOTS", "Botas Ágiles",
        "+1 SPD permanente — actuar antes en el turno",
        price=160, speed=1
    ),
    ShopItem(
        "SHADOW_STEP", "Paso de Sombra",
        "+1 MOV permanente — mayor alcance en el mapa",
        price=185, movement=1
    ),
    ShopItem(
        "CRYSTAL_HEART", "Corazón Cristalino",
        "+18 HP máximo a todos los héroes",
        price=200, hp=18
    ),
    ShopItem(
        "WARLORD_EDGE", "Filo del Caudillo",
        "+5 STR permanente — ataques notablemente más potentes",
        price=215, strength=5
    ),
    ShopItem(
        "IRON_FORTRESS", "Fortaleza de Hierro",
        "+4 DEF permanente — reduce daño recibido de forma visible",
        price=230, defense=4
    ),
    # ── Tier III: poderosas ───────────────────────────────────────────────
    ShopItem(
        "ARCANE_MIND", "Mente Arcana",
        "+15 MP y +2 STR a todos — mejora habilidades mágicas y físicas",
        price=260, mp=15, strength=2
    ),
    ShopItem(
        "VETERAN_MARK", "Marca Veterana",
        "Los héroes inician cada run desde nivel 2",
        price=300, start_level=2
    ),
    ShopItem(
        "DIAMOND_SKIN", "Piel de Diamante",
        "+6 DEF y +10 HP — máxima resistencia",
        price=350, defense=6, hp=10
    ),
    ShopItem(
        "TITAN_BLOOD", "Sangre de Titán",
        "+25 HP y +3 STR — transformación de base stat",
        price=400, hp=25, strength=3
    ),
    # ── Tier IV: élite ────────────────────────────────────────────────────
    ShopItem(
        "WARLORD_GLORY", "Gloria del Caudillo",
        "+3 STR, +3 DEF y +5 HP — el upgrade más completo",
        price=470, strength=3, defense=3, hp=5
    ),
]

# Mapa de acceso rápido por ID
_ITEM_MAP: dict[str, ShopItem] = {it.item_id: it for it in SHOP_ITEMS}


# -------------------------------------------------------
# Clase principal
# -------------------------------------------------------
class PermanentShop:
    """Gestiona monedas y compras permanentes del jugador."""

    def __init__(self):
        self.coins:     int       = 0
        self.purchased: Set[str] = set()
        self._load()

    # ── Persistencia ──────────────────────────────────────────────────────
    def _load(self):
        if not os.path.exists(_SHOP_FILE):
            return
        try:
            with open(_SHOP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.coins     = int(data.get("coins", 0))
            self.purchased = set(data.get("purchased", []))
        except Exception:
            pass   # archivo corrupto → comenzar desde cero

    def save(self):
        os.makedirs(_DATA, exist_ok=True)
        with open(_SHOP_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {"coins": self.coins, "purchased": sorted(self.purchased)},
                f, indent=2, ensure_ascii=False
            )

    # ── Economía ──────────────────────────────────────────────────────────
    def award_coins(self, score: int) -> int:
        """Convierte puntaje de run en monedas y las acredita.
        Base: 1 moneda cada 100 puntos.
        COIN_MAGNET aplica multiplicador si está comprado.
        Retorna la cantidad de monedas ganadas.
        """
        base       = max(1, score // 100)
        multiplier = 1.0 + self.get_bonuses()["coin_bonus"]
        earned     = max(1, round(base * multiplier))
        self.coins += earned
        self.save()
        return earned

    def buy(self, item_id: str) -> bool:
        """Intenta comprar el ítem. Retorna True si la compra fue exitosa."""
        item = _ITEM_MAP.get(item_id)
        if not item or item_id in self.purchased or self.coins < item.price:
            return False
        self.coins     -= item.price
        self.purchased.add(item_id)
        self.save()
        return True

    # ── Bonificaciones ────────────────────────────────────────────────────
    def get_bonuses(self) -> dict:
        """Agrega todos los bonos de los ítems comprados en un solo dict."""
        b = {"hp": 0, "mp": 0, "strength": 0, "defense": 0,
             "speed": 0, "movement": 0, "start_level": 0, "coin_bonus": 0.0}
        for iid in self.purchased:
            item = _ITEM_MAP.get(iid)
            if not item:
                continue
            b["hp"]          += item.hp
            b["mp"]          += item.mp
            b["strength"]    += item.strength
            b["defense"]     += item.defense
            b["speed"]       += item.speed
            b["movement"]    += item.movement
            b["coin_bonus"]  += item.coin_bonus
            if item.start_level > b["start_level"]:
                b["start_level"] = item.start_level
        return b

    def apply_to_unit(self, unit) -> None:
        """Aplica los bonos permanentes a una unidad aliada recién creada."""
        b = self.get_bonuses()
        if b["hp"]:
            unit.max_hp    += b["hp"]
            unit.hp_actual  = unit.max_hp
        if b["mp"]:
            unit.max_mp    += b["mp"]
            unit.mp_actual  = unit.max_mp
        if b["strength"]:
            unit.fuerza    += b["strength"]
        if b["defense"]:
            unit.defensa   = max(0, unit.defensa + b["defense"])
        if b["speed"]:
            unit.velocidad  = max(1, unit.velocidad + b["speed"])
        if b["movement"]:
            unit.movimiento = max(1, unit.movimiento + b["movement"])
        if b["start_level"] and unit.nivel < b["start_level"]:
            unit.nivel = b["start_level"]
