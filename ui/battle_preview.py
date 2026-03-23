# ui/battle_preview.py
# -------------------------------------------------
# Battle Forecast / Preview de combate.
# Muestra antes de confirmar un ataque:
#   - Daño, Hit%, Crit% de ambos lados
#   - HP resultante estimado
#   - Triángulo de armas (icono de ventaja/desventaja)
#   - Si hay doble ataque
#   - Portrait de ambas unidades (con fallback)

import pygame
import constants as C
from loaders.sprite_loader import get_portrait_hud

# Dimensiones del panel
_W = 540
_H = 160
_X = (C.ANCHO_PANTALLA - _W) // 2
_Y = C.ALTO_PANTALLA - _H - 8


def draw_battle_preview(surf: pygame.Surface, preview: dict, fonts: dict):
    """
    preview: dict retornado por core.combat.calcular_preview()
    fonts:   {"std": Font, "mini": Font, "ui_title": Font}
    """
    if not preview:
        return

    font_t  = fonts.get("ui_title", fonts.get("std"))
    font_s  = fonts.get("std")
    font_m  = fonts.get("mini")

    # Fondo
    bg = pygame.Surface((_W, _H), pygame.SRCALPHA)
    bg.fill((10, 15, 30, 220))
    surf.blit(bg, (_X, _Y))

    # Borde
    pygame.draw.rect(surf, C.BORDE_UI, (_X, _Y, _W, _H), 2)

    # Línea divisoria central
    pygame.draw.line(surf, C.BORDE_UI, (_X + _W // 2, _Y + 5), (_X + _W // 2, _Y + _H - 5), 1)

    _draw_side(surf, preview, "atq", _X + 5,          _Y, font_t, font_s, font_m, lado="izq")
    _draw_side(surf, preview, "def", _X + _W // 2 + 5, _Y, font_t, font_s, font_m, lado="der")

    # Etiqueta VS centrada
    vs = font_t.render("VS", True, C.BORDE_UI)
    surf.blit(vs, (_X + _W // 2 - vs.get_width() // 2, _Y + _H // 2 - vs.get_height() // 2))


def _draw_side(surf, preview, prefix, ox, oy, font_t, font_s, font_m, lado):
    nombre   = preview[f"{prefix}_nombre"]
    hp       = preview[f"{prefix}_hp"]
    max_hp   = preview[f"{prefix}_max_hp"]
    dmg      = preview[f"{prefix}_dmg"]
    hit      = preview[f"{prefix}_hit"]
    crit     = preview[f"{prefix}_crit"]
    doble    = preview[f"{prefix}_doble"]
    tri      = preview[f"{prefix}_tri"]
    w_side   = _W // 2 - 10

    # Portrait 48×48
    unit_id  = nombre.lower().replace(" ", "_")
    bando    = "aliado" if prefix == "atq" else "enemigo"
    portrait = get_portrait_hud(unit_id, bando, letter=nombre[0])

    portrait_x = ox + 4
    portrait_y = oy + 8
    surf.blit(portrait, (portrait_x, portrait_y))

    tx = portrait_x + 52

    # Nombre + clase
    surf.blit(font_t.render(nombre, True, C.BLANCO), (tx, oy + 8))

    # HP bar
    hp_pct = max(0.0, hp / max_hp)
    bar_y  = oy + 34
    hp_col = C.VERDE_HP if hp_pct > 0.5 else (C.AMARILLO_AWK if hp_pct > 0.25 else C.ROJO_HP)
    bar_w  = w_side - 60

    pygame.draw.rect(surf, C.NEGRO,  (tx, bar_y, bar_w, 8))
    pygame.draw.rect(surf, C.ROJO_HP,(tx, bar_y, bar_w, 8))
    pygame.draw.rect(surf, hp_col,   (tx, bar_y, int(bar_w * hp_pct), 8))
    surf.blit(font_m.render(f"{hp}/{max_hp}", True, C.BLANCO), (tx, bar_y + 10))

    # Estadísticas de combate
    stats_y = oy + 60
    dmg_txt  = f"DMG: {dmg}" + (" ×2" if doble else "")
    hit_txt  = f"HIT: {hit}%"
    crit_txt = f"CRT: {crit}%"

    # Color según triángulo
    tri_color = C.BLANCO
    tri_label = ""
    if tri > 0:
        tri_color = C.VERDE_HP
        tri_label = " ▲"
    elif tri < 0:
        tri_color = C.ROJO_HP
        tri_label = " ▼"

    surf.blit(font_s.render(dmg_txt + tri_label, True, tri_color), (tx, stats_y))
    surf.blit(font_m.render(hit_txt,  True, C.BLANCO), (tx,      stats_y + 24))
    surf.blit(font_m.render(crit_txt, True, C.AMARILLO_AWK if crit > 0 else C.GRIS_INACTIVO),
              (tx + 70, stats_y + 24))

    # Si no puede contraatacar (solo lado defensor)
    if prefix == "def" and not preview.get("def_puede_contra"):
        cant = font_m.render("Sin contraataque", True, C.GRIS_INACTIVO)
        surf.blit(cant, (tx, stats_y + 44))
