# tools/validate_assets.py
# -------------------------------------------------
# Valida que todos los sprites necesarios existan
# y tengan el tamaño correcto.
# Uso: python tools/validate_assets.py

import os
import sys

# Asegurar que el root del proyecto está en sys.path
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)

from loaders.data_loader import load_units
from loaders.sprite_loader import (
    SIZE_UNIT_MAP, SIZE_UNIT_BATTLE, SIZE_PORTRAIT_HUD,
    SIZE_PORTRAIT_DLG, SIZE_TILE, SIZE_ICON, SIZE_FX,
    _SPRITES,
)

VERDE  = "\033[92m"
ROJO   = "\033[91m"
AMARILLO = "\033[93m"
RESET  = "\033[0m"


def check_file(rel_path: str, expected_size: tuple | None = None) -> bool:
    full = os.path.join(_SPRITES, rel_path)
    if not os.path.exists(full):
        print(f"  {ROJO}✗ FALTA:{RESET} {rel_path}")
        return False

    if expected_size:
        try:
            import pygame
            pygame.init()
            img = pygame.image.load(full)
            actual = img.get_size()
            if actual != expected_size:
                print(f"  {AMARILLO}⚠ TAMAÑO:{RESET} {rel_path}  "
                      f"(esperado {expected_size}, tiene {actual})")
                return False
        except Exception as e:
            print(f"  {AMARILLO}⚠ ERROR lectura:{RESET} {rel_path} — {e}")
            return False

    print(f"  {VERDE}✓{RESET} {rel_path}")
    return True


def validate():
    print("\n═══ ETERNIA SRPG — Validación de Assets ═══\n")

    catalog = load_units()
    if not catalog:
        print(f"{AMARILLO}No se encontraron datos JSON de unidades. Usando defaults.{RESET}")
        from systems.units import UNIT_CATALOG
        catalog = UNIT_CATALOG

    ok_total = 0
    fail_total = 0

    for uid, data in catalog.items():
        sprite_id = data.get("sprite", uid.lower())
        bando     = "aliado" if data.get("is_hero") or "ALLY" in uid else "enemigo"
        folder    = "allies" if bando == "aliado" else "enemies"

        print(f"[{uid}] — sprite: '{sprite_id}'")

        checks = [
            (os.path.join("units", folder, f"{sprite_id}_map.png"),      SIZE_UNIT_MAP,     "Mapa 32×32"),
            (os.path.join("units", folder, f"{sprite_id}_battle.png"),   SIZE_UNIT_BATTLE,  "Batalla 96×96"),
            (os.path.join("units", folder, f"{sprite_id}_portrait48.png"), SIZE_PORTRAIT_HUD, "Portrait HUD 48×48"),
            (os.path.join("units", folder, f"{sprite_id}_portrait96.png"), SIZE_PORTRAIT_DLG, "Portrait Diálogo 96×96"),
        ]

        for rel, size, label in checks:
            ok = check_file(rel, size)
            if ok:
                ok_total += 1
            else:
                fail_total += 1

        print()

    # Tiles
    print("[Terreno]")
    for tile_id in range(4):
        ok = check_file(os.path.join("tiles", f"tile_{tile_id}.png"), SIZE_TILE)
        ok_total += ok
        fail_total += (not ok)
    print()

    # Resumen
    total = ok_total + fail_total
    print(f"═══ Resumen: {ok_total}/{total} archivos OK ═══")
    if fail_total:
        print(f"{AMARILLO}Los sprites faltantes usarán fallbacks generados por código.{RESET}")
        print(f"{AMARILLO}Agrega los PNGs en assets/sprites/ para reemplazarlos.{RESET}")
    else:
        print(f"{VERDE}¡Todos los sprites están presentes!{RESET}")
    print()


if __name__ == "__main__":
    validate()
