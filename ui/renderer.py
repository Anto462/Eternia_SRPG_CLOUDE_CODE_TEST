# ui/renderer.py
# -------------------------------------------------
# UIRenderer principal.
# Soporta sprites con fallback automático.
# Incluye: log de combate, battle preview, panel mejorado,
#          íconos de efectos de estado, minimapa.

import pygame
import constants as C
from loaders.sprite_loader import (
    get_tile_sprite, get_portrait_hud,
    get_unit_map_frames, get_ui_sprite,
)
from ui.battle_preview import draw_battle_preview


# =================================================
# HELPER: texto con salto de línea automático
# =================================================

def wrap_text(text, font, max_width):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


# =================================================
# CLASE PRINCIPAL
# =================================================

class UIRenderer:
    def __init__(self, fonts: dict):
        self.font_std      = fonts["std"]
        self.font_mini     = fonts["mini"]
        self.font_title    = fonts["title"]
        self.font_ui_title = fonts["ui_title"]

        self.sup_fx = pygame.Surface((C.ANCHO_PANTALLA, C.ALTO_PANTALLA), pygame.SRCALPHA)

        # Log de combate: últimas N líneas
        self._combat_log: list = []
        self._log_max = 6

        # Animación de unidades en mapa
        self._anim_tick: int = 0          # sube cada frame
        self._anim_speed: int = 18        # ticks por frame de animación (~3fps a 60fps)

        # Cache de cursor sprite
        self._cursor_spr = get_ui_sprite("BoxSelector", 0, 0, 16, 16, scale_to=(32, 32))

    # -------------------------
    # Log de combate
    # -------------------------
    def push_log(self, msg: str):
        self._combat_log.append(msg)
        if len(self._combat_log) > self._log_max:
            self._combat_log.pop(0)

    # -------------------------
    # Helpers UI
    # -------------------------
    def draw_box(self, surf, x, y, w, h, alpha=None):
        if alpha is not None:
            box = pygame.Surface((w, h), pygame.SRCALPHA)
            box.fill((*C.FONDO_UI, alpha))
            surf.blit(box, (x, y))
            pygame.draw.rect(surf, C.BORDE_UI, (x, y, w, h), 2)
        else:
            pygame.draw.rect(surf, C.FONDO_UI, (x, y, w, h))
            pygame.draw.rect(surf, C.BORDE_UI,  (x, y, w, h), 2)
            pygame.draw.line(surf, C.GRIS_OSCURO, (x+2, y+h-2), (x+w-2, y+h-2))
            pygame.draw.line(surf, C.GRIS_OSCURO, (x+w-2, y+2),  (x+w-2, y+h-2))

    def draw_turn_banner(self, surf, text, color, timer):
        if timer <= 0:
            return
        overlay = pygame.Surface((C.ANCHO_PANTALLA, 100))
        overlay.set_alpha(min(200, timer * 4))
        overlay.fill(C.NEGRO)
        surf.blit(overlay, (0, C.ALTO_PANTALLA // 2 - 50))
        txt = self.font_title.render(text, True, color)
        r   = txt.get_rect(center=(C.ANCHO_PANTALLA // 2, C.ALTO_PANTALLA // 2))
        surf.blit(txt, r)

    # -------------------------
    # Pantallas
    # -------------------------
    def draw_main_menu(self, surf):
        # Fondo con degradado vertical oscuro
        for y in range(C.ALTO_PANTALLA):
            t = y / C.ALTO_PANTALLA
            r = int(5  + 20 * t)
            g = int(5  + 10 * t)
            b = int(20 + 40 * t)
            pygame.draw.line(surf, (r, g, b), (0, y), (C.ANCHO_PANTALLA, y))

        # Línea decorativa superior e inferior
        pygame.draw.line(surf, C.AMARILLO_AWK, (60, 90),  (C.ANCHO_PANTALLA - 60, 90),  2)
        pygame.draw.line(surf, C.AMARILLO_AWK, (60, 185), (C.ANCHO_PANTALLA - 60, 185), 1)

        # Título
        cx = C.ANCHO_PANTALLA // 2
        title = self.font_title.render("ETERNIA  SRPG", True, C.AMARILLO_AWK)
        # Sombra
        shadow = self.font_title.render("ETERNIA  SRPG", True, (60, 40, 0))
        surf.blit(shadow, shadow.get_rect(center=(cx + 3, 133)))
        surf.blit(title,  title.get_rect(center=(cx, 130)))

        subtitle = self.font_std.render("— Victoria y Conquista —", True, C.BORDE_UI)
        surf.blit(subtitle, subtitle.get_rect(center=(cx, 165)))

        # Panel de opciones
        box_x, box_y, box_w, box_h = cx - 160, 210, 320, 190
        self.draw_box(surf, box_x, box_y, box_w, box_h, alpha=210)

        opciones = [
            ("[1]  Jugar PvP — Local",    C.BLANCO),
            ("[2]  Jugar PvE — vs IA",    C.BLANCO),
            ("[3]  Controles",            C.GRIS_INACTIVO),
        ]
        for i, (op, col) in enumerate(opciones):
            lbl = self.font_std.render(op, True, col)
            surf.blit(lbl, lbl.get_rect(center=(cx, 248 + i * 46)))

        # Línea separadora
        pygame.draw.line(surf, C.BORDE_UI, (box_x + 20, 390), (box_x + box_w - 20, 390), 1)

        # Versión / hint
        hint = self.font_mini.render("Mapas y unidades configurables en  data/", True, C.GRIS_INACTIVO)
        surf.blit(hint, hint.get_rect(center=(cx, C.ALTO_PANTALLA - 28)))

    def draw_controls_menu(self, surf):
        surf.fill(C.NEGRO)
        surf.blit(self.font_title.render("CONTROLES", True, C.BLANCO),
                  self.font_title.render("CONTROLES", True, C.BLANCO).get_rect(center=(C.ANCHO_PANTALLA//2, 60)))

        self.draw_box(surf, 80, 110, 640, 430)
        controles = [
            ("Flechas",          "Mover cursor"),
            ("ENTER / ESPACIO",  "Seleccionar / Confirmar"),
            ("ESCAPE",           "Cancelar / Volver"),
            ("F",                "Finalizar turno"),
            ("A",                "Atacar (en menú)"),
            ("H",                "Habilidad (en menú)"),
            ("I",                "Inventario (en menú)"),
            ("E",                "Esperar (en menú)"),
            ("W",                "Activar Awakening (si barra llena)"),
            ("C",                "Conquistar trono (solo Héroe)"),
            ("P",                "Pausa / Menú de pausa"),
        ]
        for i, (k, v) in enumerate(controles):
            surf.blit(self.font_std.render(k,  True, C.AMARILLO_AWK), (100, 130 + i * 36))
            surf.blit(self.font_std.render(v,  True, C.BLANCO),       (300, 130 + i * 36))

        surf.blit(self.font_mini.render("ESC — Volver", True, C.GRIS_INACTIVO), (100, C.ALTO_PANTALLA - 40))

    def draw_end_screen(self, surf, victory: bool, state=None):
        cx = C.ANCHO_PANTALLA // 2
        cy = C.ALTO_PANTALLA  // 2

        # Fondo con degradado
        base_r, base_g, base_b = (0, 60, 10) if victory else (60, 0, 0)
        for y in range(C.ALTO_PANTALLA):
            t = y / C.ALTO_PANTALLA
            pygame.draw.line(surf,
                             (int(base_r * (1 - t * 0.5)),
                              int(base_g * (1 - t * 0.5)),
                              int(base_b * (1 - t * 0.5))),
                             (0, y), (C.ANCHO_PANTALLA, y))

        txt   = "¡VICTORIA!" if victory else "GAME OVER"
        color = C.AMARILLO_AWK if victory else C.ROJO_HP

        # Sombra del título
        shadow = self.font_title.render(txt, True, (0, 0, 0))
        surf.blit(shadow, shadow.get_rect(center=(cx + 3, cy - 70 + 3)))
        title_s = self.font_title.render(txt, True, color)
        surf.blit(title_s, title_s.get_rect(center=(cx, cy - 70)))

        # Separador
        pygame.draw.line(surf, color, (cx - 140, cy - 35), (cx + 140, cy - 35), 2)

        # Info de mapa (si disponible)
        if state:
            map_num  = state.get("map_number", 0)
            tier     = state.get("difficulty_tier", "")
            map_def  = state.get("map_def")
            map_name = map_def.name if map_def else ""
            info_txt = f"Mapa {map_num + 1}  —  {map_name}  [{tier.upper()}]"
            info_s   = self.font_std.render(info_txt, True, (200, 200, 200))
            surf.blit(info_s, info_s.get_rect(center=(cx, cy - 10)))

        # Botones
        if victory:
            btn1 = self.font_std.render("[R]  Siguiente Mapa", True, C.AMARILLO_AWK)
        else:
            btn1 = self.font_std.render("[R]  Reintentar",     True, C.BLANCO)
        btn2 = self.font_std.render("[ESC]  Menú Principal",  True, C.GRIS_INACTIVO)
        surf.blit(btn1, btn1.get_rect(center=(cx, cy + 25)))
        surf.blit(btn2, btn2.get_rect(center=(cx, cy + 58)))

    def draw_pause_menu(self, surf):
        overlay = pygame.Surface((C.ANCHO_PANTALLA, C.ALTO_PANTALLA), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))

        self.draw_box(surf, 280, 180, 240, 200)
        surf.blit(self.font_ui_title.render("PAUSA", True, C.BLANCO), (340, 195))
        items = ["[ESC] Continuar", "[R]  Reiniciar", "[M]  Menú Principal"]
        for i, it in enumerate(items):
            surf.blit(self.font_std.render(it, True, C.BLANCO), (295, 230 + i * 40))

    # -------------------------
    # Mapa
    # -------------------------
    def draw_map(self, surf, grid):
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                # Intentar sprite de terreno
                tile_spr = get_tile_sprite(tile)
                if tile_spr:
                    surf.blit(tile_spr, (x * C.TAMANO_TILE, y * C.TAMANO_TILE))
                else:
                    color = C.INFO_TERRENO[tile]["color"]
                    pygame.draw.rect(surf, color,
                                     (x * C.TAMANO_TILE, y * C.TAMANO_TILE,
                                      C.TAMANO_TILE, C.TAMANO_TILE))

        # Grid lines
        for i in range(0, C.ANCHO_PANTALLA, C.TAMANO_TILE):
            pygame.draw.line(surf, (0, 0, 0, 25), (i, 0), (i, C.ALTO_PANTALLA))
        for j in range(0, C.ALTO_PANTALLA, C.TAMANO_TILE):
            pygame.draw.line(surf, (0, 0, 0, 25), (0, j), (C.ANCHO_PANTALLA, j))

    def draw_thrones(self, surf, thrones):
        if not thrones:
            return
        for bando, (tx, ty) in thrones.items():
            color = (80, 0, 180) if bando == "enemigo" else C.PURPURA_TRONO
            pygame.draw.rect(surf, color,
                             (tx * C.TAMANO_TILE, ty * C.TAMANO_TILE,
                              C.TAMANO_TILE, C.TAMANO_TILE))
            pygame.draw.rect(surf, C.BLANCO,
                             (tx * C.TAMANO_TILE, ty * C.TAMANO_TILE,
                              C.TAMANO_TILE, C.TAMANO_TILE), 1)
            crown = self.font_mini.render("♛", True, C.BLANCO)
            surf.blit(crown, (tx * C.TAMANO_TILE + 8, ty * C.TAMANO_TILE + 8))

    def draw_items(self, surf, items_suelo):
        for (ix, iy), item in items_suelo.items():
            px, py = ix * C.TAMANO_TILE, iy * C.TAMANO_TILE
            pygame.draw.rect(surf, C.DORADO_COFRE, (px + 8, py + 8, 16, 16))
            pygame.draw.rect(surf, (200, 150, 0),  (px + 8, py + 8, 16, 16), 1)
            # Letra inicial del ítem
            ltr = self.font_mini.render(item.nombre[0], True, C.NEGRO)
            surf.blit(ltr, (px + 12, py + 10))

    def draw_move_range(self, surf, casillas):
        self.sup_fx.fill((0, 0, 0, 0))
        for (rx, ry) in casillas:
            pygame.draw.rect(self.sup_fx, C.AZUL_RANGO,
                             (rx * C.TAMANO_TILE, ry * C.TAMANO_TILE,
                              C.TAMANO_TILE, C.TAMANO_TILE))
        surf.blit(self.sup_fx, (0, 0))

    def draw_attack_range_overlay(self, surf, casillas):
        """Muestra el rango de ataque desde todas las posiciones de movimiento."""
        self.sup_fx.fill((0, 0, 0, 0))
        for (rx, ry) in casillas:
            pygame.draw.rect(self.sup_fx, (255, 60, 60, 40),
                             (rx * C.TAMANO_TILE, ry * C.TAMANO_TILE,
                              C.TAMANO_TILE, C.TAMANO_TILE))
        surf.blit(self.sup_fx, (0, 0))

    def draw_target_overlay(self, surf, targets, is_heal=False, is_buff=False):
        self.sup_fx.fill((0, 0, 0, 0))
        if is_heal or is_buff:
            col = C.VERDE_RANGO_SKILL
        else:
            col = C.ROJO_ATAQUE
        for t in targets:
            pygame.draw.rect(self.sup_fx, col,
                             (t.x * C.TAMANO_TILE, t.y * C.TAMANO_TILE,
                              C.TAMANO_TILE, C.TAMANO_TILE))
        surf.blit(self.sup_fx, (0, 0))

    def draw_cursor(self, surf, cx, cy, selected_mode=False):
        tx = cx * C.TAMANO_TILE
        ty = cy * C.TAMANO_TILE
        # Intentar sprite BoxSelector; si no existe, usar rectángulo de color
        if self._cursor_spr:
            # Tinte rojo en modo selección, amarillo en modo normal
            spr = self._cursor_spr.copy()
            tint_color = C.ROJO_CURSOR if selected_mode else C.AMARILLO_CURSOR
            tint = pygame.Surface((C.TAMANO_TILE, C.TAMANO_TILE), pygame.SRCALPHA)
            tint.fill((*tint_color, 90))
            spr.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            surf.blit(spr, (tx, ty))
        else:
            color = C.ROJO_CURSOR if selected_mode else C.AMARILLO_CURSOR
            pygame.draw.rect(surf, color, (tx, ty, C.TAMANO_TILE, C.TAMANO_TILE), 3)

    # -------------------------
    # Panel de unidad mejorado
    # -------------------------
    def draw_unit_panel(self, surf, unidad):
        if not unidad:
            return

        pw, ph = 280, 145
        px, py = 10, C.ALTO_PANTALLA - ph - 10
        self.draw_box(surf, px, py, pw, ph)

        # Portrait 48×48
        portrait = get_portrait_hud(
            getattr(unidad, "sprite_id", unidad.nombre.lower()),
            unidad.bando,
            unidad.color_base,
            letter=unidad.nombre[0]
        )
        surf.blit(portrait, (px + 6, py + 6))

        tx = px + 62

        # Nombre + clase + nivel
        nombre_txt = f"{unidad.nombre}  Nv.{unidad.nivel}"
        surf.blit(self.font_ui_title.render(nombre_txt, True, C.BLANCO), (tx, py + 5))
        surf.blit(self.font_mini.render(getattr(unidad, "clase", ""), True, C.GRIS_INACTIVO), (tx, py + 25))

        # Barras HP / MP
        bw = pw - 70
        self._draw_bar(surf, tx, py + 42, bw, 8,
                       unidad.hp_actual, unidad.max_hp, C.VERDE_HP, C.ROJO_HP,
                       label=f"HP {unidad.hp_actual}/{unidad.max_hp}", font=self.font_mini)
        if unidad.max_mp > 0:
            self._draw_bar(surf, tx, py + 56, bw, 5,
                           unidad.mp_actual, unidad.max_mp, C.AZUL_MP, C.NEGRO,
                           label=f"MP {unidad.mp_actual}/{unidad.max_mp}", font=self.font_mini)

        # Stats en dos columnas
        col1, col2 = tx, tx + (pw - 70) // 2
        row1 = py + 72
        stats = [
            (f"STR {unidad.fuerza}",                     col1, row1),
            (f"DEF {unidad.defensa}",                    col2, row1),
            (f"SPD {getattr(unidad,'velocidad',5)}",      col1, row1 + 16),
            (f"SKL {getattr(unidad,'habilidad',4)}",      col2, row1 + 16),
            (f"LCK {getattr(unidad,'suerte',3)}",         col1, row1 + 32),
            (f"MOV {unidad.movimiento}",                  col2, row1 + 32),
        ]
        for label, sx, sy in stats:
            surf.blit(self.font_mini.render(label, True, C.BLANCO), (sx, sy))

        # Arma equipada
        arma_txt = f"Eq: {unidad.arma_equipada.nombre}" if unidad.arma_equipada else "Eq: Puños"
        surf.blit(self.font_mini.render(arma_txt, True, (200, 200, 200)), (px + 6, py + ph - 20))

        # Efectos de estado
        if hasattr(unidad, "efectos") and unidad.efectos:
            for i, ef in enumerate(unidad.efectos[:5]):
                ex = px + 6 + i * 22
                ey = py + ph - 38
                pygame.draw.circle(surf, ef.color, (ex + 8, ey + 8), 7)
                lbl = self.font_mini.render(ef.etiqueta[0], True, C.BLANCO)
                surf.blit(lbl, (ex + 4, ey + 2))

        # Awakening activo
        if getattr(unidad, "awakened", False):
            surf.blit(self.font_mini.render("★ AWAKENING ACTIVO", True, C.AMARILLO_AWK),
                      (px + 6, py + ph - 52))

    def _draw_bar(self, surf, x, y, w, h, val, max_val, fill_color, bg_color, label=None, font=None):
        pct = max(0.0, val / max_val) if max_val > 0 else 0
        pygame.draw.rect(surf, C.NEGRO,    (x, y, w, h))
        pygame.draw.rect(surf, bg_color,   (x, y, w, h))
        pygame.draw.rect(surf, fill_color, (x, y, int(w * pct), h))
        if label and font:
            surf.blit(font.render(label, True, C.BLANCO), (x + w + 3, y - 1))

    # -------------------------
    # Menús
    # -------------------------
    def draw_action_menu(self, surf, sel_unidad, thrones=None):
        if not sel_unidad:
            return

        px = sel_unidad.x * C.TAMANO_TILE + 40
        py = sel_unidad.y * C.TAMANO_TILE - 20
        if px > C.ANCHO_PANTALLA - 160:
            px = sel_unidad.x * C.TAMANO_TILE - 160
        if py < 0:
            py = 10

        can_conquer = False
        if thrones and sel_unidad.es_heroe:
            throne = thrones.get(sel_unidad.bando)
            if throne and (sel_unidad.x, sel_unidad.y) == throne:
                can_conquer = True

        can_wake = sel_unidad.es_heroe and getattr(sel_unidad, "awakening_meter", 0) >= 100

        opciones = ["[A] Atacar", "[H] Habilidad", "[I] Inventario", "[E] Esperar"]
        if can_wake:
            opciones.append("[W] Awakening!")
        if can_conquer:
            opciones.append("[C] Conquistar")

        alto = 20 + len(opciones) * 30
        self.draw_box(surf, px, py, 150, alto)
        for i, op in enumerate(opciones):
            color = C.AMARILLO_AWK if "Awakening" in op else \
                    C.PURPURA_TRONO if "Conquistar" in op else C.BLANCO
            surf.blit(self.font_std.render(op, True, color), (px + 8, py + 8 + int(i) * 30))

    def draw_inventory_menu(self, surf, sel_unidad):
        if not sel_unidad:
            return
        self.draw_box(surf, 180, 140, 440, 290)
        surf.blit(self.font_ui_title.render(f"Inventario — {sel_unidad.nombre}", True, C.BLANCO), (200, 152))

        for i, it in enumerate(sel_unidad.inventario):
            eq_mark = " (E)" if it == sel_unidad.arma_equipada else ""
            surf.blit(self.font_std.render(f"{i+1}. {it.nombre}{eq_mark}", True, C.BLANCO),
                      (200, 190 + i * 32))
            if it.tipo == "arma":
                detail = f"POD:{it.poder}  HIT:{it.precision_bonus:+}  CRT:{it.critico_bonus}"
            else:
                detail = f"Cura: {it.cura} HP"
                if getattr(it, "cura_estado", None):
                    detail += f" + Cura {it.cura_estado}"
            surf.blit(self.font_mini.render(detail, True, C.GRIS_INACTIVO), (370, 195 + i * 32))

        surf.blit(self.font_mini.render("ESC — Volver", True, C.GRIS_INACTIVO), (200, 410))

    def draw_skills_menu(self, surf, sel_unidad):
        if not sel_unidad:
            return
        self.draw_box(surf, 180, 140, 440, 220)
        surf.blit(self.font_ui_title.render("Habilidades", True, C.BLANCO), (200, 152))

        for i, sk in enumerate(sel_unidad.habilidades):
            tiene_mp = sel_unidad.mp_actual >= sk.costo_mp
            col      = C.BLANCO if tiene_mp else C.GRIS_INACTIVO
            surf.blit(self.font_std.render(f"{i+1}. {sk.nombre}  ({sk.costo_mp} MP)", True, col),
                      (200, 190 + i * 34))
            rango_txt = f"Rango {sk.rango[0]}-{sk.rango[1]}  |  {sk.tipo_efecto}"
            surf.blit(self.font_mini.render(rango_txt, True, C.GRIS_INACTIVO), (380, 195 + i * 34))

        surf.blit(self.font_mini.render("ESC — Volver", True, C.GRIS_INACTIVO), (200, 342))

    # -------------------------
    # Diálogo de batalla
    # -------------------------
    def draw_battle_dialogue(self, surf, payload: dict):
        if not payload or not payload.get("active"):
            return
        speaker = payload.get("speaker", "")
        text    = payload.get("text", "")
        if not text:
            return

        unit_id = payload.get("unit_id", "")
        bando   = "aliado" if "ALLY" in unit_id else "enemigo"

        margin = 20
        box_h  = 110
        bx, by = margin, C.ALTO_PANTALLA - box_h - margin
        bw     = C.ANCHO_PANTALLA - margin * 2

        self.draw_box(surf, bx, by, bw, box_h)

        # Portrait pequeño en el diálogo
        portrait = get_portrait_hud(
            unit_id.lower(), bando,
            letter=speaker[0] if speaker else "?"
        )
        surf.blit(portrait, (bx + 8, by + 8))

        # Nombre + texto
        surf.blit(self.font_ui_title.render(speaker, True, C.BLANCO), (bx + 64, by + 8))
        lines = wrap_text(text, self.font_std, bw - 80)[:3]
        for i, line in enumerate(lines):
            surf.blit(self.font_std.render(line, True, C.BLANCO), (bx + 64, by + 36 + i * 24))

    # -------------------------
    # Log de combate
    # -------------------------
    def draw_combat_log(self, surf, log_lines: list):
        if not log_lines:
            return
        lx = C.ANCHO_PANTALLA - 220
        ly = 10
        lw = 210
        lh = len(log_lines) * 18 + 10
        self.draw_box(surf, lx, ly, lw, lh, alpha=180)
        for i, line in enumerate(log_lines):
            surf.blit(self.font_mini.render(line, True, C.BLANCO), (lx + 5, ly + 4 + i * 18))

    # -------------------------
    # Mini-mapa
    # -------------------------
    def draw_minimap(self, surf, grid, unidades_vivas, thrones):
        mm_w, mm_h = 80, 50
        mm_x, mm_y = C.ANCHO_PANTALLA - mm_w - 10, C.ALTO_PANTALLA - mm_h - 10

        pygame.draw.rect(surf, C.NEGRO, (mm_x, mm_y, mm_w, mm_h))
        pygame.draw.rect(surf, C.BORDE_UI, (mm_x, mm_y, mm_w, mm_h), 1)

        rows, cols = len(grid), len(grid[0])
        pw = mm_w / cols
        ph = mm_h / rows

        # Terreno simplificado
        for y, row in enumerate(grid):
            for x, tile in enumerate(row):
                col = C.INFO_TERRENO[tile]["color"]
                pygame.draw.rect(surf, col,
                                 (mm_x + int(x * pw), mm_y + int(y * ph),
                                  max(1, int(pw)), max(1, int(ph))))

        # Unidades
        for u in unidades_vivas:
            col = (80, 120, 255) if u.bando == "aliado" else (255, 80, 80)
            ux  = mm_x + int(u.x * pw)
            uy  = mm_y + int(u.y * ph)
            pygame.draw.circle(surf, col, (ux, uy), max(2, int(min(pw, ph))))

    # -------------------------
    # Dibujo de unidades con sprites reales + fallback
    # -------------------------
    def draw_unit(self, surf: pygame.Surface, u):
        """
        Dibuja una unidad en el mapa usando sprite animado si existe,
        o la figura geométrica de fallback si no hay sprite cargado.
        Conserva barras HP/MP/Awakening y estado visual sobre el sprite.
        """
        px = u.x * C.TAMANO_TILE
        py = u.y * C.TAMANO_TILE

        # Obtener frames del sprite (lista de 1-4 Surfaces 32×32)
        frames = get_unit_map_frames(
            getattr(u, "sprite_id", ""),
            u.bando,
            getattr(u, "color_base", None),
        )

        # Seleccionar frame según tick de animación
        frame_idx = (self._anim_tick // self._anim_speed) % len(frames)
        sprite    = frames[frame_idx]

        # Unidad inactiva → semitransparente
        if u.ha_actuado:
            sprite = sprite.copy()
            sprite.set_alpha(110)

        # Halo dorado si está en awakening
        if getattr(u, "awakened", False):
            pygame.draw.rect(surf, C.AMARILLO_AWK, (px - 1, py - 1, 34, 34), 2)

        surf.blit(sprite, (px, py))

        # Nombre corto encima (solo en hover lo muestra el panel; aquí solo barra)
        bar_x = px + 1
        bar_w = C.TAMANO_TILE - 2

        # Barra HP
        pct_hp = max(0.0, u.hp_actual / u.max_hp) if u.max_hp > 0 else 0.0
        pygame.draw.rect(surf, C.NEGRO,    (bar_x, py - 5, bar_w, 4))
        pygame.draw.rect(surf, C.ROJO_HP,  (bar_x, py - 5, bar_w, 4))
        pygame.draw.rect(surf, C.VERDE_HP, (bar_x, py - 5, int(bar_w * pct_hp), 4))

        # Barra MP
        if u.max_mp > 0:
            pct_mp = max(0.0, u.mp_actual / u.max_mp)
            pygame.draw.rect(surf, C.NEGRO,   (bar_x, py - 1, bar_w, 2))
            pygame.draw.rect(surf, C.AZUL_MP, (bar_x, py - 1, int(bar_w * pct_mp), 2))

        # Barra Awakening (solo héroes)
        if u.es_heroe and getattr(u, "awakening_type", None):
            pct_awk = getattr(u, "awakening_meter", 0) / 100
            pygame.draw.rect(surf, C.NEGRO,       (bar_x, py + C.TAMANO_TILE, bar_w, 2))
            pygame.draw.rect(surf, C.AMARILLO_AWK,(bar_x, py + C.TAMANO_TILE, int(bar_w * pct_awk), 2))

        # Nivel (esquina superior derecha del tile)
        lvl = self.font_mini.render(str(u.nivel), True, C.BLANCO)
        surf.blit(lvl, (px + C.TAMANO_TILE - lvl.get_width() - 1, py + 1))

    # -------------------------
    # Render principal
    # -------------------------
    def render(self, surf, state: dict):
        estado = state.get("estado_juego", "MENU_PRINCIPAL")

        if estado == "MENU_PRINCIPAL":
            self.draw_main_menu(surf)
            return
        if estado == "MENU_CONTROLES":
            self.draw_controls_menu(surf)
            return
        if estado == "GAME_OVER":
            self.draw_end_screen(surf, victory=False, state=state)
            return
        if estado == "VICTORIA":
            self.draw_end_screen(surf, victory=True, state=state)
            return
        if estado == "PAUSA":
            self.render(surf, {**state, "estado_juego": "NEUTRAL"})
            self.draw_pause_menu(surf)
            return

        # ----- JUEGO -----
        surf.fill(C.NEGRO)

        grid           = state["mapa"]
        thrones        = state.get("thrones")
        items_suelo    = state.get("items_suelo", {})
        unidades_vivas = state.get("unidades_vivas", [])
        cursor_x, cursor_y = state.get("cursor", (0, 0))
        sel_unidad     = state.get("sel_unidad")
        casillas_mov   = state.get("casillas_mov", [])
        sel_skill      = state.get("sel_skill")
        targets        = state.get("targets", [])
        preview_data   = state.get("battle_preview")
        log_lines      = state.get("combat_log", [])

        # Mapa y extras
        self.draw_map(surf, grid)
        self.draw_thrones(surf, thrones)
        self.draw_items(surf, items_suelo)

        # Rango de movimiento
        if estado == "SELECCIONADO":
            self.draw_move_range(surf, casillas_mov)

        # Overlay de targets
        if "OBJETIVO" in estado or "TARGET" in estado:
            is_heal = bool(sel_skill and getattr(sel_skill, "tipo_efecto", "") == "curar")
            is_buff = bool(sel_skill and getattr(sel_skill, "tipo_efecto", "") == "buff")
            self.draw_target_overlay(surf, targets, is_heal=is_heal, is_buff=is_buff)

        # Unidades con sprites reales (o fallback geométrico)
        self._anim_tick = self._anim_tick + 1
        for u in unidades_vivas:
            self.draw_unit(surf, u)

        # Cursor
        self.draw_cursor(surf, cursor_x, cursor_y,
                         selected_mode=("SELECCION" in estado))

        # Panel de unidad bajo cursor
        u_hover = next((u for u in unidades_vivas
                        if u.x == cursor_x and u.y == cursor_y), None)
        if u_hover and estado not in ["MENU_ACCION", "MENU_INVENTARIO", "MENU_SKILLS", "PAUSA"]:
            self.draw_unit_panel(surf, u_hover)

        # Menús contextuales
        if estado == "MENU_ACCION":
            self.draw_action_menu(surf, sel_unidad, thrones=thrones)
        elif estado == "MENU_INVENTARIO":
            self.draw_inventory_menu(surf, sel_unidad)
        elif estado == "MENU_SKILLS":
            self.draw_skills_menu(surf, sel_unidad)

        # Battle Preview (forecast)
        if preview_data and estado == "SELECCION_OBJETIVO":
            draw_battle_preview(surf, preview_data,
                                {"std": self.font_std, "mini": self.font_mini,
                                 "ui_title": self.font_ui_title})

        # FX
        fx = state.get("fx_manager")
        if fx:
            fx.draw(surf)

        # Banner de turno
        self.draw_turn_banner(surf, state.get("texto_transicion", ""),
                              state.get("color_transicion", C.BLANCO),
                              state.get("timer_transicion", 0))

        # Diálogo de batalla
        self.draw_battle_dialogue(surf, state.get("battle_dialogue"))

        # Log de combate
        self.draw_combat_log(surf, log_lines)

        # Minimapa
        if grid:
            self.draw_minimap(surf, grid, unidades_vivas, thrones)

        # HUD superior izquierdo: turno, modo, mapa, dificultad
        fase      = state.get("fase_actual", "")
        modo      = state.get("modo_juego", "")
        map_num   = state.get("map_number", 0)
        tier      = state.get("difficulty_tier", "")
        map_def   = state.get("map_def")
        map_name  = map_def.name if map_def else ""

        color_fase = C.AZUL_MP if fase == "aliado" else C.ROJO_HP
        color_tier = {
            "easy":   (100, 220, 100),
            "medium": (220, 200, 60),
            "hard":   (220, 100, 40),
            "boss":   (200, 40,  200),
        }.get(tier, C.BLANCO)

        hud_lines = [
            (f"Turno: {fase.upper()}  [{modo}]", color_fase),
            (f"Mapa {map_num + 1}: {map_name}", C.BLANCO),
            (f"Dificultad: {tier.upper()}", color_tier),
        ]
        self.draw_box(surf, 4, 2, 210, 52, alpha=160)
        for i, (line, col) in enumerate(hud_lines):
            surf.blit(self.font_mini.render(line, True, col), (9, 5 + i * 17))
