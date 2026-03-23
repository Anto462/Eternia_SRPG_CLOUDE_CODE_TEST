# loaders/data_loader.py
# -------------------------------------------------
# Carga catálogos desde archivos JSON en data/.
# Si un archivo JSON no existe, retorna un catálogo vacío
# y el sistema cae en los defaults del código.
#
# Esto permite:
# - Agregar personajes editando solo el JSON (sin tocar Python)
# - El juego funciona sin JSONs (usa defaults hardcodeados en systems/)

import json
import os

# Directorio raíz del proyecto (un nivel arriba de /loaders)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA = os.path.join(_ROOT, "data")


def _load_json(path: str) -> dict:
    """Carga un archivo JSON. Retorna {} si no existe."""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[DataLoader] Error cargando {path}: {e}")
        return {}


def load_allies() -> dict:
    """Carga catálogo de aliados desde data/units/allies.json."""
    return _load_json(os.path.join(_DATA, "units", "allies.json"))


def load_enemies() -> dict:
    """Carga catálogo de enemigos desde data/units/enemies.json."""
    return _load_json(os.path.join(_DATA, "units", "enemies.json"))


def load_units() -> dict:
    """Carga aliados + enemigos en un único catálogo."""
    catalog = {}
    catalog.update(load_allies())
    catalog.update(load_enemies())
    return catalog


def load_items() -> dict:
    """Carga catálogo de ítems desde data/items/items.json."""
    return _load_json(os.path.join(_DATA, "items", "items.json"))


def load_skills() -> dict:
    """Carga catálogo de habilidades desde data/items/skills.json."""
    return _load_json(os.path.join(_DATA, "items", "skills.json"))


def load_quotes() -> dict:
    """Carga frases de diálogo desde data/dialogue/quotes.json."""
    return _load_json(os.path.join(_DATA, "dialogue", "quotes.json"))


def load_maps() -> list:
    """
    Carga todos los archivos .json en data/maps/.
    Retorna lista de dicts (uno por mapa).
    """
    maps_dir = os.path.join(_DATA, "maps")
    if not os.path.exists(maps_dir):
        return []

    maps = []
    for filename in sorted(os.listdir(maps_dir)):
        if filename.endswith(".json"):
            path = os.path.join(maps_dir, filename)
            data = _load_json(path)
            if data:
                maps.append(data)
    return maps
