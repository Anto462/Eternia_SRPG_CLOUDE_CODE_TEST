# ui/renderer.py
# -------------------------------------------------
# UIRenderer principal.
# Soporta sprites con fallback automático.
# Incluye: log de combate, battle preview, panel mejorado,
#          íconos de efectos de estado, minimapa.

import math
import pygame
import constants as C
from loaders.sprite_loader import (
    get_tile_sprite, get_portrait_hud,
    get_unit_map_frames, get_ui_sprite, is_large_sprite,
)
from ui.battle_preview import draw_battle_preview
from ui.weather import WeatherSystem
from systems.rogue_system import MIN_HEROES, MAX_HEROES


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

        # Animaciones de UI en combate
        self._ui_anim_start: dict = {}
        self._ui_anim_duration = 160
        self._prev_banner_text: str = ""
        self._prev_action_unit_id: "int | None" = None

        # Sistema de clima estético
        self._weather = WeatherSystem()
        self._current_weather: "str | None" = None

        # Typewriter para banner P3R
        self._banner_chars_shown: int = 0
        self._banner_char_timer:  int = 0

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

    def _draw_panel(self, surf, x, y, w, h, alpha=210, accent=None):
        """Panel estilo Fire Emblem: fondo oscuro + borde doble + línea de acento."""
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((10, 14, 32, alpha))
        surf.blit(bg, (x, y))
        outer = accent or (140, 160, 200)
        pygame.draw.rect(surf, outer,       (x,     y,     w,     h    ), 2)
        pygame.draw.rect(surf, (40, 55, 90),(x + 3, y + 3, w - 6, h - 6), 1)
        if accent:
            pygame.draw.line(surf, accent, (x + 5, y + 2), (x + w - 5, y + 2), 1)

    def _draw_gradient_bg(self, surf, r1, g1, b1, r2, g2, b2):
        """Degradado vertical de dos colores."""
        H = C.ALTO_PANTALLA
        for y in range(H):
            t = y / H
            pygame.draw.line(surf,
                (int(r1 + (r2-r1)*t), int(g1 + (g2-g1)*t), int(b1 + (b2-b1)*t)),
                (0, y), (C.ANCHO_PANTALLA, y))

    def _draw_diagonal_accent(self, surf, color, alpha=55):
        """Franja diagonal estilo Persona en la esquina superior derecha."""
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        dsurf = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.polygon(dsurf, (*color, alpha),
                            [(W - 280, 0), (W, 0), (W, H // 2), (W - 480, H // 2)])
        surf.blit(dsurf, (0, 0))

    def _draw_title_bar(self, surf, text, y, font=None, color=None):
        """Barra de título estilo Persona: fondo negro diagonal + texto con sombra."""
        W = C.ANCHO_PANTALLA
        cx = W // 2
        font  = font  or self.font_title
        color = color or C.AMARILLO_AWK
        # Backing shape
        bar = pygame.Surface((W, 48), pygame.SRCALPHA)
        pygame.draw.polygon(bar, (0, 0, 0, 190),
                            [(20, 4), (W - 10, 4), (W - 40, 44), (0, 44)])
        surf.blit(bar, (0, y - 24))
        # Shadow + text
        sh = font.render(text, True, (30, 10, 10))
        tx = font.render(text, True, color)
        surf.blit(sh, sh.get_rect(center=(cx + 3, y + 3)))
        surf.blit(tx, tx.get_rect(center=(cx, y)))

    # -------------------------
    # Helpers de animación
    # -------------------------
    def _anim_t(self, key: str) -> float:
        """Retorna t en [0,1] para el slide-in del widget 'key'.
        Si el widget no fue llamado por más de 500ms (estaba cerrado),
        reinicia automáticamente la animación al reabrir."""
        now = pygame.time.get_ticks()
        last_key = key + "_last"
        last_call = self._ui_anim_start.get(last_key, 0)
        # Si estuvo inactivo más de 500ms → fue cerrado, reiniciar
        if last_call > 0 and now - last_call > 500:
            self._ui_anim_start.pop(key, None)
        self._ui_anim_start[last_key] = now

        if key not in self._ui_anim_start:
            self._ui_anim_start[key] = now
        elapsed = now - self._ui_anim_start[key]
        t = min(1.0, elapsed / self._ui_anim_duration)
        # Ease out cubic
        return 1 - (1 - t) ** 3

    def _anim_reset(self, key: str):
        """Reinicia la animación de un widget."""
        self._ui_anim_start.pop(key, None)

    def _text_outline(self, surf, font, text, color, pos, outline_col=(0, 0, 0), thickness=2):
        """Renderiza texto con contorno — estilo Persona."""
        cx, cy = pos
        for dx in range(-thickness, thickness + 1):
            for dy in range(-thickness, thickness + 1):
                if dx == 0 and dy == 0:
                    continue
                s = font.render(text, True, outline_col)
                r = s.get_rect(center=(cx + dx, cy + dy))
                surf.blit(s, r)
        s = font.render(text, True, color)
        surf.blit(s, s.get_rect(center=(cx, cy)))

    # ─── Helpers P3R ──────────────────────────────────────────────────────────

    def _draw_hex_pattern(self, surf, alpha=18):
        """Patrón de hexágonos tenues al fondo — sello visual de P3R."""
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        pat = pygame.Surface((W, H), pygame.SRCALPHA)
        size = 28          # radio del hexágono
        dx   = size * 2
        dy   = int(size * 1.73)
        for row in range(-1, H // dy + 2):
            for col in range(-1, W // dx + 2):
                cx = col * dx + (size if row % 2 else 0)
                cy = row * dy
                pts = [
                    (cx + size * math.cos(math.radians(60 * k - 30)),
                     cy + size * math.sin(math.radians(60 * k - 30)))
                    for k in range(6)
                ]
                pygame.draw.polygon(pat, (0, 200, 212, alpha), pts, 1)
        surf.blit(pat, (0, 0))

    def _draw_p3r_panel(self, surf, x, y, w, h, alpha=235, accent=None):
        """Panel P3R: fondo navy, borde teal fino, franja lateral teal."""
        acc = accent or C.P3R_TEAL
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((*C.P3R_PANEL, alpha))
        surf.blit(bg, (x, y))
        # Franja lateral izquierda teal
        pygame.draw.rect(surf, acc, (x, y, 4, h))
        # Borde exterior
        pygame.draw.rect(surf, acc, (x, y, w, h), 1)
        # Línea interna teal tenue
        pygame.draw.rect(surf, C.P3R_DARK_TEAL, (x + 5, y + 1, w - 6, h - 2), 1)

    def _draw_p3r_title_bar(self, surf, text, y, font=None, color=None):
        """Barra de título P3R: fondo navy con borde teal + texto teal."""
        W  = C.ANCHO_PANTALLA
        cx = W // 2
        fnt   = font  or self.font_title
        color = color or C.P3R_TEAL
        bar = pygame.Surface((W, 52), pygame.SRCALPHA)
        bar.fill((*C.P3R_NAVY, 200))
        surf.blit(bar, (0, y - 26))
        # Líneas teal arriba y abajo
        pygame.draw.line(surf, C.P3R_TEAL,    (40, y - 26), (W - 40, y - 26), 1)
        pygame.draw.line(surf, C.P3R_TEAL,    (40, y + 26), (W - 40, y + 26), 1)
        pygame.draw.line(surf, C.P3R_TEAL_DIM,(40, y - 24), (W - 40, y - 24), 1)
        # Sombra + texto
        sh = fnt.render(text, True, C.P3R_DARK_TEAL)
        tx = fnt.render(text, True, color)
        surf.blit(sh, sh.get_rect(center=(cx + 2, y + 2)))
        surf.blit(tx, tx.get_rect(center=(cx, y)))

    def _draw_arc_gauge(self, surf, cx, cy, radius, pct, color, bg_color,
                        thickness=6, start_angle=-210, arc_span=240):
        """Barra de HP/MP en forma de arco — estilo P3R.
        pct en [0,1]. El arco va en sentido horario desde start_angle."""
        # Fondo del arco (gris oscuro)
        rect = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        end_rad   = math.radians(-start_angle)
        start_rad = math.radians(-(start_angle + arc_span))
        pygame.draw.arc(surf, bg_color, rect, start_rad, end_rad, thickness)
        # Relleno activo
        if pct > 0.01:
            fill_span = arc_span * pct
            fill_end  = math.radians(-(start_angle))
            fill_start= math.radians(-(start_angle + fill_span))
            pygame.draw.arc(surf, color, rect, fill_start, fill_end, thickness)
        # Punto de inicio y final
        pygame.draw.circle(surf, color,    (cx, cy + radius - thickness // 2), thickness // 2)

    def _draw_p3r_gradient_bg(self, surf):
        """Fondo degradado P3R: navy oscuro con pulso de brillo suave."""
        t   = (pygame.time.get_ticks() % 4000) / 4000.0
        pulse = int(math.sin(t * math.pi * 2) * 4)
        r1, g1, b1 = C.P3R_NAVY
        r2, g2, b2 = C.P3R_BLUE_MID
        H = C.ALTO_PANTALLA
        for y in range(H):
            lp = y / H
            pygame.draw.line(surf,
                (int(r1 + (r2-r1)*lp) + pulse,
                 int(g1 + (g2-g1)*lp) + pulse,
                 int(b1 + (b2-b1)*lp) + pulse),
                (0, y), (C.ANCHO_PANTALLA, y))

    def draw_turn_banner(self, surf, text, color, timer):
        """Banner de turno P3R: panel navy con borde teal + barrido lateral + typewriter."""
        if timer <= 0:
            self._anim_reset("banner")
            self._prev_banner_text = ""
            self._banner_chars_shown = 0
            self._banner_char_timer  = 0
            return

        if text != self._prev_banner_text:
            self._anim_reset("banner")
            self._prev_banner_text   = text
            self._banner_chars_shown = 0
            self._banner_char_timer  = 0

        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cy   = H // 2
        t    = self._anim_t("banner")
        alpha = min(255, timer * 6)

        # Color de acento según bando
        is_enemy = "ENEMIGO" in text.upper() or color == C.ROJO_HP
        acc = C.P3R_ENEMY if is_enemy else C.P3R_ALLY

        # Panel principal navy que barre desde la izquierda
        banner_h = 68
        banner_y = cy - banner_h // 2
        offset_x = int((1 - t) * (-W - 40))

        panel = pygame.Surface((W + 40, banner_h), pygame.SRCALPHA)
        panel.fill((*C.P3R_NAVY, min(alpha, 230)))
        surf.blit(panel, (offset_x, banner_y))

        # Franja de acento de color (izquierda)
        strip_w = 10
        pygame.draw.rect(surf, (*acc, min(alpha, 255)),
                         (offset_x, banner_y, strip_w, banner_h))

        # Borde teal arriba y abajo
        pygame.draw.line(surf, (*C.P3R_TEAL, min(alpha, 200)),
                         (offset_x, banner_y), (W, banner_y), 2)
        pygame.draw.line(surf, (*C.P3R_TEAL, min(alpha, 200)),
                         (offset_x, banner_y + banner_h - 1),
                         (W, banner_y + banner_h - 1), 2)
        # Línea teal_dim secundaria
        pygame.draw.line(surf, (*C.P3R_TEAL_DIM, min(alpha, 140)),
                         (offset_x, banner_y + 2), (W, banner_y + 2), 1)

        # Typewriter: mostrar texto carácter a carácter
        self._banner_char_timer += 1
        if self._banner_char_timer >= 2:        # 1 char cada 2 frames
            self._banner_char_timer = 0
            self._banner_chars_shown = min(len(text), self._banner_chars_shown + 1)
        visible_text = text[:self._banner_chars_shown]

        txt_x = W // 2 + offset_x // 4   # sigue suavemente al panel
        self._text_outline(surf, self.font_title, visible_text,
                           C.P3R_WHITE, (txt_x, cy),
                           outline_col=C.P3R_NAVY, thickness=2)

        # Subtítulo
        phase_str = "FASE ALIADA" if not is_enemy else "FASE ENEMIGA"
        sub = self.font_mini.render(phase_str, True, C.P3R_TEAL)
        surf.blit(sub, sub.get_rect(center=(txt_x, cy + 26)))

    # -------------------------
    # Pantallas
    # -------------------------
    def draw_main_menu(self, surf, state=None):
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx = W // 2

        # Fondo navy P3R con pulso suave
        self._draw_p3r_gradient_bg(surf)
        # Patrón de hexágonos tenues
        self._draw_hex_pattern(surf, alpha=16)

        # Círculo decorativo grande en esquina superior derecha (motivo P3R)
        t_glow = (pygame.time.get_ticks() % 3000) / 3000.0
        glow_r = int(110 + math.sin(t_glow * math.pi * 2) * 8)
        glow_surf = pygame.Surface((300, 300), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*C.P3R_TEAL_DIM, 18), (150, 150), glow_r)
        pygame.draw.circle(glow_surf, (*C.P3R_TEAL, 8),      (150, 150), glow_r, 2)
        surf.blit(glow_surf, (W - 200, -60))

        # Líneas horizontales teal decorativas
        pygame.draw.line(surf, C.P3R_TEAL,    (40, 82),  (W - 40, 82),  2)
        pygame.draw.line(surf, C.P3R_TEAL_DIM,(40, 84),  (W - 40, 84),  1)
        pygame.draw.line(surf, C.P3R_TEAL_DIM,(40, 176), (W - 40, 176), 1)
        pygame.draw.line(surf, C.P3R_TEAL,    (40, 178), (W - 40, 178), 2)

        # Título P3R
        self._draw_p3r_title_bar(surf, "ETERNIA  SRPG", 130)
        sub = self.font_std.render("— Victoria y Conquista —", True, C.P3R_TEAL_DIM)
        surf.blit(sub, sub.get_rect(center=(cx, 163)))

        # Panel de opciones P3R
        has_sv = state.get("has_save", False) if state else False
        coins    = state.get("shop_coins", 0) if state else 0
        opciones = [
            ("[1]  Nueva PvP — Local",                   C.P3R_WHITE),
            ("[2]  Nueva PvE — vs IA",                   C.P3R_WHITE),
            ("[3]  Controles",                            (130, 150, 175)),
            ("[5]  Puntajes",                             C.P3R_TEAL_DIM),
            (f"[6]  Tienda Permanente   ({coins:,} ✦)", C.P3R_GOLD),
        ]
        if has_sv:
            opciones.insert(0, ("[4]  Continuar run guardada", C.P3R_GOLD))

        n_opts = len(opciones)
        box_w  = 350
        box_h  = 28 + n_opts * 44 + 18
        box_x  = cx - box_w // 2
        box_y  = 194
        self._draw_p3r_panel(surf, box_x, box_y, box_w, box_h, alpha=225)

        for i, (op, col) in enumerate(opciones):
            oy = box_y + 28 + i * 44
            # Fila resaltada para "Continuar"
            if has_sv and i == 0:
                hl = pygame.Surface((box_w - 8, 36), pygame.SRCALPHA)
                hl.fill((*C.P3R_TEAL, 20))
                surf.blit(hl, (box_x + 4, oy - 8))
            # Cursor teal pulsante en primera opción
            if i == 0 and not has_sv:
                pulse = abs(pygame.time.get_ticks() % 1000 - 500) / 500.0
                cur_alpha = int(60 + pulse * 40)
                cur_s = pygame.Surface((box_w - 8, 34), pygame.SRCALPHA)
                cur_s.fill((*C.P3R_TEAL, cur_alpha))
                surf.blit(cur_s, (box_x + 4, oy - 7))
            lbl = self.font_std.render(op, True, col)
            surf.blit(lbl, lbl.get_rect(center=(cx, oy)))
            if i < n_opts - 1:
                pygame.draw.line(surf, C.P3R_DARK_TEAL,
                                 (box_x + 20, oy + 18), (box_x + box_w - 20, oy + 18), 1)

        # Mejor puntaje bajo el panel
        top = state.get("top_scores", []) if state else []
        if top:
            e      = top[0]
            best_y = box_y + box_h + 10
            self._draw_p3r_panel(surf, box_x, best_y, box_w, 34, alpha=180)
            bs = self.font_mini.render(
                f"① MEJOR  {e.get('total', 0):,}  pts   ×{e.get('maps', 0)} mapas   [{e.get('tier','?')[:3].upper()}]",
                True, C.P3R_TEAL)
            surf.blit(bs, bs.get_rect(center=(cx, best_y + 17)))

        hint = self.font_mini.render("Mapas y unidades configurables en  data/", True, (50, 70, 90))
        surf.blit(hint, hint.get_rect(center=(cx, H - 22)))

    def draw_all_scores(self, surf, top_scores: list):
        """Pantalla dedicada de puntajes — estilo Persona con tabla completa."""
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx = W // 2

        self._draw_gradient_bg(surf, 4, 6, 18, 10, 14, 35)
        self._draw_diagonal_accent(surf, (120, 100, 10), alpha=35)

        self._draw_title_bar(surf, "RANKING DE PUNTAJES", 42)
        pygame.draw.line(surf, C.AMARILLO_AWK, (50, 64), (W - 50, 64), 1)

        if not top_scores:
            msg = self.font_std.render("Aún no hay puntajes registrados.", True, (130, 140, 155))
            surf.blit(msg, msg.get_rect(center=(cx, H // 2)))
        else:
            medals      = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
            medal_cols  = [
                C.PERSONA_GOLD,
                (200, 210, 215),
                (200, 145, 70),
                (180, 185, 195),
                (170, 175, 185),
            ]
            # Cabecera de tabla
            header_y = 82
            pw, ph   = W - 120, len(top_scores) * 38 + 52
            self._draw_panel(surf, 60, header_y, pw, ph, alpha=215, accent=C.AMARILLO_AWK)

            # Títulos de columnas
            cols_x = [80, 130, 300, 430, 530]
            hdrs   = ["#", "Puntos", "Mapas", "Dif.", "Modo"]
            for hx, ht in zip(cols_x, hdrs):
                hs = self.font_mini.render(ht, True, (140, 150, 170))
                surf.blit(hs, (hx, header_y + 8))
            pygame.draw.line(surf, (60, 70, 100),
                             (76, header_y + 26), (60 + pw - 6, header_y + 26), 1)

            for i, entry in enumerate(top_scores):
                ry    = header_y + 32 + i * 38
                col   = medal_cols[i] if i < len(medal_cols) else (165, 170, 180)
                medal = medals[i] if i < len(medals) else f"#{i+1}"

                # Fondo de fila alternado
                if i % 2 == 0:
                    row_bg = pygame.Surface((pw - 8, 34), pygame.SRCALPHA)
                    row_bg.fill((255, 255, 255, 6))
                    surf.blit(row_bg, (64, ry + 2))

                total = entry.get("total", 0)
                maps  = entry.get("maps",  0)
                tier  = entry.get("tier",  "?")[:4].upper()
                modo  = entry.get("modo",  "PVE")[:3].upper()

                surf.blit(self.font_std.render(medal,          True, col),           (cols_x[0], ry + 6))
                surf.blit(self.font_std.render(f"{total:,}",   True, col),           (cols_x[1], ry + 6))
                surf.blit(self.font_mini.render(f"× {maps}",   True, (160, 170, 180)), (cols_x[2], ry + 8))
                surf.blit(self.font_mini.render(f"[{tier}]",   True, (140, 150, 165)), (cols_x[3], ry + 8))
                surf.blit(self.font_mini.render(modo,          True, (130, 140, 155)), (cols_x[4], ry + 8))

                if i < len(top_scores) - 1:
                    pygame.draw.line(surf, (35, 45, 68),
                                     (76, ry + 36), (60 + pw - 6, ry + 36), 1)

        hint = self.font_mini.render("ESC — Volver al menú", True, (80, 90, 110))
        surf.blit(hint, hint.get_rect(center=(cx, H - 20)))

    def draw_controls_menu(self, surf):
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx = W // 2
        self._draw_gradient_bg(surf, 4, 6, 18, 10, 14, 35)
        self._draw_diagonal_accent(surf, (20, 60, 120), alpha=40)

        self._draw_title_bar(surf, "CONTROLES", 42)
        pygame.draw.line(surf, C.AMARILLO_AWK, (50, 64), (W - 50, 64), 1)

        controles = [
            ("Flechas",         "Mover cursor"),
            ("ENTER / ESPACIO", "Seleccionar / Confirmar"),
            ("ESCAPE",          "Cancelar / Volver"),
            ("F",               "Finalizar turno"),
            ("A",               "Atacar (en menú acción)"),
            ("H",               "Habilidad (en menú acción)"),
            ("I",               "Inventario (en menú acción)"),
            ("E",               "Esperar (en menú acción)"),
            ("W",               "Activar Awakening (barra llena)"),
            ("C",               "Conquistar trono (solo Héroe)"),
            ("P",               "Pausa"),
        ]
        pw, ph = W - 100, len(controles) * 38 + 20
        self._draw_panel(surf, 50, 76, pw, ph, alpha=210, accent=(80, 100, 150))

        for i, (k, v) in enumerate(controles):
            ry = 88 + i * 38
            # Fila alternada sutil
            if i % 2 == 0:
                row_bg = pygame.Surface((pw - 8, 32), pygame.SRCALPHA)
                row_bg.fill((255, 255, 255, 8))
                surf.blit(row_bg, (54, ry - 4))
            surf.blit(self.font_std.render(k, True, C.AMARILLO_AWK), (68, ry))
            surf.blit(self.font_std.render(v, True, C.BLANCO),        (280, ry))
            pygame.draw.line(surf, (35, 50, 80),
                             (58, ry + 30), (50 + pw - 8, ry + 30), 1)

        hint = self.font_mini.render("ESC — Volver al menú", True, (80, 90, 110))
        surf.blit(hint, hint.get_rect(center=(cx, H - 20)))

    def draw_end_screen(self, surf, victory: bool, state=None):
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx, cy = W // 2, H // 2

        # Fondo: victoria=verde azulado oscuro, derrota=rojo-negro
        if victory:
            self._draw_gradient_bg(surf, 0, 30, 18, 5, 55, 30)
            accent_col  = C.AMARILLO_AWK
            title_txt   = "¡VICTORIA!"
            diag_color  = (20, 100, 40)
        else:
            self._draw_gradient_bg(surf, 50, 0, 0, 18, 4, 4)
            accent_col  = C.ROJO_HP
            title_txt   = "GAME OVER"
            diag_color  = (120, 10, 10)
        self._draw_diagonal_accent(surf, diag_color, alpha=60)

        # Líneas horizontales de acento
        pygame.draw.line(surf, accent_col, (50, cy - 100), (W - 50, cy - 100), 2)
        pygame.draw.line(surf, (60, 70, 80), (50, cy - 98), (W - 50, cy - 98), 1)

        # Título con backing shape
        self._draw_title_bar(surf, title_txt, cy - 70,
                             font=self.font_title, color=accent_col)

        # Línea divisoria inferior al título
        pygame.draw.line(surf, accent_col,  (cx - 160, cy - 38), (cx + 160, cy - 38), 2)
        pygame.draw.line(surf, (60, 70, 80),(cx - 160, cy - 36), (cx + 160, cy - 36), 1)

        # Info de mapa
        if state:
            map_num  = state.get("map_number", 0)
            tier     = state.get("difficulty_tier", "")
            map_def  = state.get("map_def")
            map_name = map_def.name if map_def else ""
            info_txt = f"Mapa {map_num + 1}  —  {map_name}  [{tier.upper()}]"
            inf = self.font_std.render(info_txt, True, (195, 205, 215))
            surf.blit(inf, inf.get_rect(center=(cx, cy - 16)))

            # Panel de puntuación estilo FE
            sc = state.get("score_summary", {})
            if sc:
                pw, ph = 340, 110
                self._draw_panel(surf, cx - pw//2, cy - 2, pw, ph,
                                 alpha=215, accent=accent_col)
                # Puntuación total destacada
                total_s = self.font_ui_title.render(
                    f"PUNTUACIÓN:  {sc.get('total', 0):,}", True, accent_col)
                surf.blit(total_s, total_s.get_rect(center=(cx, cy + 18)))
                # Stats secundarios
                stats_txt = (f"Kills: {sc.get('kills', 0)}     "
                             f"Mapas: {sc.get('maps', 0)}     "
                             f"Dif: {sc.get('tier','?').upper()}")
                st = self.font_mini.render(stats_txt, True, (190, 195, 210))
                surf.blit(st, st.get_rect(center=(cx, cy + 40)))
                # Separador
                pygame.draw.line(surf, (50, 65, 95),
                                 (cx - pw//2 + 16, cy + 54),
                                 (cx + pw//2 - 16, cy + 54), 1)
                # Último evento de breakdown
                breakdown = sc.get("breakdown", [])
                if breakdown:
                    bd = self.font_mini.render(breakdown[-1], True, C.VERDE_HP)
                    surf.blit(bd, bd.get_rect(center=(cx, cy + 68)))
                    if len(breakdown) > 1:
                        bd2 = self.font_mini.render(breakdown[-2], True, (160, 200, 160))
                        surf.blit(bd2, bd2.get_rect(center=(cx, cy + 84)))

        # Panel de botones
        btn_y = cy + 125
        self._draw_panel(surf, cx - 170, btn_y, 340, 62, alpha=195, accent=(70, 85, 115))
        if victory:
            b1 = self.font_std.render("[R]  Siguiente Mapa", True, C.AMARILLO_AWK)
        else:
            b1 = self.font_std.render("[R]  Reintentar",     True, C.BLANCO)
        b2 = self.font_std.render("[ESC]  Menú Principal",   True, (140, 150, 170))
        surf.blit(b1, b1.get_rect(center=(cx, btn_y + 18)))
        # Separador entre botones
        pygame.draw.line(surf, (50, 65, 95),
                         (cx - 150, btn_y + 32), (cx + 150, btn_y + 32), 1)
        surf.blit(b2, b2.get_rect(center=(cx, btn_y + 46)))

    def draw_pause_menu(self, surf):
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx = W // 2
        # Overlay semitransparente
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        surf.blit(ov, (0, 0))

        # Panel central con estilo FE
        pw, ph = 280, 210
        px, py = cx - pw // 2, H // 2 - ph // 2
        self._draw_panel(surf, px, py, pw, ph, alpha=235, accent=C.AMARILLO_AWK)

        # Título del panel
        self._draw_title_bar(surf, "PAUSA", py + 22,
                             font=self.font_ui_title, color=C.AMARILLO_AWK)
        pygame.draw.line(surf, (60, 80, 120),
                         (px + 16, py + 38), (px + pw - 16, py + 38), 1)

        items = [
            ("[ESC]  Continuar",       C.BLANCO),
            ("[R]    Reiniciar mapa",   (200, 200, 200)),
            ("[M]    Menú Principal",   (160, 165, 180)),
        ]
        for i, (it, col) in enumerate(items):
            iy = py + 56 + i * 46
            # Fondo sutil en hover (primera opción = acción principal)
            if i == 0:
                hl = pygame.Surface((pw - 16, 34), pygame.SRCALPHA)
                hl.fill((255, 215, 0, 18))
                surf.blit(hl, (px + 8, iy - 8))
            surf.blit(self.font_std.render(it, True, col),
                      self.font_std.render(it, True, col).get_rect(center=(cx, iy)))
            if i < len(items) - 1:
                pygame.draw.line(surf, (35, 50, 80),
                                 (px + 20, iy + 22), (px + pw - 20, iy + 22), 1)

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
    # Panel de unidad — estilo Persona
    # -------------------------
    def draw_unit_panel(self, surf, unidad):
        """Panel P3R: navy profundo, acento teal/rojo por bando,
        arco de HP, stats compactos, efectos como hexágonos."""
        if not unidad:
            return

        pw, ph = 296, 150
        px, py = 8, C.ALTO_PANTALLA - ph - 8

        acc = C.P3R_ALLY if unidad.bando == "aliado" else C.P3R_ENEMY

        # Fondo navy
        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((*C.P3R_PANEL, 248))
        surf.blit(bg, (px, py))

        # Franja lateral de bando
        pygame.draw.rect(surf, acc, (px, py, 5, ph))
        # Borde exterior teal/rojo
        pygame.draw.rect(surf, acc, (px, py, pw, ph), 1)
        # Línea interna teal_dim
        pygame.draw.line(surf, C.P3R_TEAL_DIM, (px + 5, py + 1), (px + pw - 1, py + 1), 1)

        # ── Portrait con marco circular ──────────────────────────────────────
        portrait = get_portrait_hud(
            getattr(unidad, "sprite_id", unidad.nombre.lower()),
            unidad.bando,
            unidad.color_base,
            letter=unidad.nombre[0]
        )
        port_cx, port_cy = px + 30, py + 32
        # Clip circular del portrait
        port_mask = pygame.Surface((44, 44), pygame.SRCALPHA)
        pygame.draw.circle(port_mask, (255, 255, 255, 255), (22, 22), 22)
        port_clipped = portrait.copy()
        port_clipped.blit(port_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(port_clipped, (port_cx - 22, port_cy - 22))
        # Marco circular del bando
        pygame.draw.circle(surf, acc,           (port_cx, port_cy), 23, 2)
        pygame.draw.circle(surf, C.P3R_TEAL_DIM,(port_cx, port_cy), 25, 1)

        tx = px + 62

        # Nombre + nivel
        ns  = self.font_ui_title.render(unidad.nombre, True, C.P3R_WHITE)
        nls = self.font_mini.render(f"Nv.{unidad.nivel}", True, C.P3R_TEAL)
        surf.blit(ns,  (tx, py + 5))
        surf.blit(nls, (px + pw - nls.get_width() - 8, py + 7))
        # Clase en teal apagado
        surf.blit(self.font_mini.render(
            getattr(unidad, "clase", "").upper(), True, C.P3R_TEAL_DIM),
            (tx, py + 22))

        bar_w = pw - tx + px - 10
        bar_x = tx

        # ── HP con gradiente de color ────────────────────────────────────────
        hp_pct = max(0.0, unidad.hp_actual / unidad.max_hp) if unidad.max_hp > 0 else 0
        if hp_pct > 0.5:
            hp_col = C.P3R_HP_HIGH
        elif hp_pct > 0.25:
            hp_col = C.P3R_HP_MID
        else:
            hp_col = C.P3R_HP_LOW

        hp_lbl = self.font_mini.render(f"HP  {unidad.hp_actual}/{unidad.max_hp}", True, hp_col)
        surf.blit(hp_lbl, (bar_x, py + 38))
        self._draw_bar(surf, bar_x, py + 52, bar_w, 7,
                       unidad.hp_actual, unidad.max_hp, hp_col, (15, 5, 5))

        # ── MP ───────────────────────────────────────────────────────────────
        if unidad.max_mp > 0:
            mp_lbl = self.font_mini.render(
                f"MP  {unidad.mp_actual}/{unidad.max_mp}", True, C.P3R_MP_BAR)
            surf.blit(mp_lbl, (bar_x, py + 62))
            self._draw_bar(surf, bar_x, py + 76, bar_w, 5,
                           unidad.mp_actual, unidad.max_mp, C.P3R_MP_BAR, (5, 5, 20))

        # ── Awakening ────────────────────────────────────────────────────────
        bar_offset_y = py + 84 if unidad.max_mp > 0 else py + 64
        if unidad.es_heroe and getattr(unidad, "awakening_type", None):
            pct_awk = getattr(unidad, "awakening_meter", 0) / 100
            awk_col = C.P3R_GOLD if pct_awk >= 1.0 else C.P3R_TEAL_DIM
            surf.blit(self.font_mini.render("AWK", True, awk_col), (bar_x, bar_offset_y))
            self._draw_bar(surf, bar_x + 30, bar_offset_y + 3, bar_w - 30, 4,
                           int(pct_awk * 100), 100, awk_col, (10, 8, 0))
            bar_offset_y += 14

        # ── Separador ────────────────────────────────────────────────────────
        pygame.draw.line(surf, C.P3R_DARK_TEAL,
                         (px + 8, bar_offset_y + 4), (px + pw - 8, bar_offset_y + 4), 1)

        # ── Stats compactos ──────────────────────────────────────────────────
        stats_y = bar_offset_y + 8
        stat_col = (160, 185, 210)
        for row_i, (s1, s2) in enumerate([
            (f"STR {unidad.fuerza}",                f"DEF {unidad.defensa}"),
            (f"SPD {getattr(unidad,'velocidad',5)}", f"MOV {unidad.movimiento}"),
        ]):
            sy = stats_y + row_i * 14
            if sy + 12 < py + ph:
                surf.blit(self.font_mini.render(s1, True, stat_col), (tx, sy))
                surf.blit(self.font_mini.render(s2, True, stat_col), (tx + bar_w // 2, sy))

        # ── Arma equipada ────────────────────────────────────────────────────
        arma_txt = f"⚔ {unidad.arma_equipada.nombre}" if unidad.arma_equipada else "⚔ Puños"
        surf.blit(self.font_mini.render(arma_txt, True, (130, 155, 175)), (px + 9, py + ph - 18))

        # ── Efectos de estado como hexágonos ─────────────────────────────────
        if hasattr(unidad, "efectos") and unidad.efectos:
            for i, ef in enumerate(unidad.efectos[:5]):
                ex = px + pw - 16 - i * 22
                ey = py + ph - 16
                # Hexágono pequeño
                pts = [(ex + 8*math.cos(math.radians(60*k - 30)),
                        ey + 8*math.sin(math.radians(60*k - 30))) for k in range(6)]
                pygame.draw.polygon(surf, ef.color, pts)
                pygame.draw.polygon(surf, C.P3R_WHITE, pts, 1)
                surf.blit(self.font_mini.render(ef.etiqueta[0], True, C.P3R_WHITE),
                          self.font_mini.render(ef.etiqueta[0], True, C.P3R_WHITE)
                          .get_rect(center=(ex, ey)))

        # ── Awakening activo — banner pulsante ───────────────────────────────
        if getattr(unidad, "awakened", False):
            pulse = abs(pygame.time.get_ticks() % 800 - 400) / 400
            aw_a  = int(140 + pulse * 90)
            aw_bg = pygame.Surface((pw - 10, 14), pygame.SRCALPHA)
            aw_bg.fill((*C.P3R_TEAL, aw_a // 6))
            surf.blit(aw_bg, (px + 5, py + ph - 32))
            aw_s = self.font_mini.render("★ AWAKENING ACTIVO ★", True, C.P3R_TEAL)
            surf.blit(aw_s, aw_s.get_rect(center=(px + pw // 2, py + ph - 25)))

    def _draw_bar(self, surf, x, y, w, h, val, max_val, fill_color, bg_color, label=None, font=None):
        """Barra de recurso con segmentos Persona-style (tick marks cada 25%)."""
        pct = max(0.0, val / max_val) if max_val > 0 else 0
        fill_w = int(w * pct)

        # Fondo
        pygame.draw.rect(surf, (12, 12, 20), (x, y, w, h))
        # Relleno principal
        pygame.draw.rect(surf, fill_color, (x, y, fill_w, h))

        # Pulso en HP crítico (≤20%)
        if fill_color == C.VERDE_HP and pct <= 0.20 and pct > 0:
            pulse = abs(pygame.time.get_ticks() % 600 - 300) / 300  # 0–1–0
            pulsed = pygame.Surface((fill_w, h), pygame.SRCALPHA)
            pulsed.fill((255, 255, 255, int(pulse * 80)))
            surf.blit(pulsed, (x, y))

        # Tick marks cada 25% (estilo Persona)
        for seg in [1, 2, 3]:
            tx = x + int(w * seg / 4)
            pygame.draw.line(surf, (10, 10, 18), (tx, y), (tx, y + h), 1)

        # Borde sutil
        pygame.draw.rect(surf, (40, 40, 60), (x, y, w, h), 1)

        if label and font:
            surf.blit(font.render(label, True, C.BLANCO), (x + w + 3, y - 1))

    # -------------------------
    # Menús
    # -------------------------
    def draw_action_menu(self, surf, sel_unidad, thrones=None):
        """Menú de acción P3R: panel navy con franja teal lateral,
        bullet hexagonal como cursor, highlight teal en fila activa."""
        if not sel_unidad:
            self._anim_reset("action_menu")
            self._prev_action_unit_id = None
            return

        # Reiniciar animación cuando cambia la unidad seleccionada
        cur_uid = id(sel_unidad)
        if self._prev_action_unit_id != cur_uid:
            self._anim_reset("action_menu")
            self._prev_action_unit_id = cur_uid

        t = self._anim_t("action_menu")

        can_conquer = False
        if thrones and sel_unidad.es_heroe:
            throne = thrones.get(sel_unidad.bando)
            if throne and (sel_unidad.x, sel_unidad.y) == throne:
                can_conquer = True

        can_wake = sel_unidad.es_heroe and getattr(sel_unidad, "awakening_meter", 0) >= 100

        # Opciones con tecla, label, color especial
        opciones = [
            ("A", "Atacar",      C.P3R_WHITE),
            ("H", "Habilidad",   C.P3R_WHITE),
            ("I", "Inventario",  C.P3R_WHITE),
            ("E", "Esperar",     C.P3R_TEAL_DIM),
        ]
        if can_wake:
            opciones.append(("W", "Awakening!", C.P3R_GOLD))
        if can_conquer:
            opciones.append(("C", "Conquistar", C.PURPURA_TRONO))

        item_h  = 34
        menu_w  = 162
        menu_h  = len(opciones) * item_h + 10
        strip_w = 20   # franja lateral teal

        # Posición — pegado a la unidad pero con margen
        raw_x = sel_unidad.x * C.TAMANO_TILE + 38
        raw_y = sel_unidad.y * C.TAMANO_TILE - menu_h // 2
        if raw_x + menu_w > C.ANCHO_PANTALLA - 4:
            raw_x = sel_unidad.x * C.TAMANO_TILE - menu_w - 6
        raw_y = max(4, min(raw_y, C.ALTO_PANTALLA - menu_h - 4))

        # Slide desde la izquierda o derecha según lado
        slide_dir = 1 if raw_x > C.ANCHO_PANTALLA // 2 else -1
        px = int(raw_x + slide_dir * menu_w * (1 - t))
        py = raw_y

        # Fondo principal navy
        bg = pygame.Surface((menu_w, menu_h), pygame.SRCALPHA)
        bg.fill((*C.P3R_PANEL, 245))
        surf.blit(bg, (px, py))

        # Franja lateral teal
        pygame.draw.rect(surf, C.P3R_TEAL, (px, py, strip_w, menu_h))
        # Borde exterior teal fino
        pygame.draw.rect(surf, C.P3R_TEAL, (px, py, menu_w, menu_h), 1)
        # Línea interna teal_dim en la parte superior
        pygame.draw.line(surf, C.P3R_TEAL_DIM,
                         (px + strip_w, py + 1), (px + menu_w - 1, py + 1), 1)

        # Filas de opciones
        for i, (key, label, col) in enumerate(opciones):
            ry = py + 5 + i * item_h

            # Highlight teal suave en primera opción
            if i == 0:
                hl = pygame.Surface((menu_w - strip_w - 2, item_h - 2), pygame.SRCALPHA)
                hl.fill((*C.P3R_TEAL, 28))
                surf.blit(hl, (px + strip_w + 1, ry + 1))

            # Bullet hexagonal pequeño en la franja teal (cursor)
            hx_cx = px + strip_w // 2
            hx_cy = ry + item_h // 2
            hex_pts = [(hx_cx + 7*math.cos(math.radians(60*k - 30)),
                        hx_cy + 7*math.sin(math.radians(60*k - 30))) for k in range(6)]
            if i == 0:
                pygame.draw.polygon(surf, C.P3R_NAVY, hex_pts)
                pygame.draw.polygon(surf, C.P3R_WHITE, hex_pts, 1)
            # Tecla dentro del hexágono
            ks = self.font_mini.render(key, True, C.P3R_WHITE)
            surf.blit(ks, ks.get_rect(center=(hx_cx, hx_cy)))

            # Label
            ls = self.font_std.render(label, True, col)
            surf.blit(ls, (px + strip_w + 8, ry + (item_h - ls.get_height()) // 2))

            # Separador entre ítems
            if i < len(opciones) - 1:
                pygame.draw.line(surf, C.P3R_DARK_TEAL,
                                 (px + strip_w + 4, ry + item_h - 1),
                                 (px + menu_w - 4,  ry + item_h - 1), 1)

    def _draw_persona_panel(self, surf, x, y, w, h, title, accent=None):
        """Panel base estilo Persona: fondo negro, franja lateral, título con backing."""
        acc = accent or C.PERSONA_RED
        # Fondo
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((*C.PERSONA_PANEL, 248))
        surf.blit(bg, (x, y))
        # Franja izquierda de color
        pygame.draw.rect(surf, acc, (x, y, 5, h))
        # Borde
        pygame.draw.rect(surf, acc, (x, y, w, h), 1)
        # Barra de título
        tbar = pygame.Surface((w - 6, 26), pygame.SRCALPHA)
        tbar.fill((*acc, 200))
        surf.blit(tbar, (x + 5, y))
        # Línea dorada bajo el título
        pygame.draw.line(surf, C.PERSONA_GOLD, (x + 5, y + 26), (x + w - 1, y + 26), 1)
        # Texto del título
        ts = self.font_ui_title.render(title, True, C.PERSONA_WHITE)
        surf.blit(ts, (x + 12, y + 4))

    def draw_inventory_menu(self, surf, sel_unidad):
        """Inventario estilo Persona: panel negro con franja roja, ítem equipado en dorado."""
        if not sel_unidad:
            self._anim_reset("inv_menu")
            return

        t = self._anim_t("inv_menu")
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        pw, ph = 460, min(310, 60 + len(sel_unidad.inventario) * 46 + 20)
        px = W // 2 - pw // 2
        # Slide desde abajo
        py = int(H // 2 - ph // 2 + (H - H // 2 + ph) * (1 - t))

        self._draw_persona_panel(surf, px, py, pw, ph,
                                 f"INVENTARIO  —  {sel_unidad.nombre.upper()}")

        for i, it in enumerate(sel_unidad.inventario):
            ry = py + 34 + i * 44
            is_eq = (it == sel_unidad.arma_equipada)

            # Fondo de fila (dorado si equipado, alterno sutil si no)
            row_bg = pygame.Surface((pw - 8, 38), pygame.SRCALPHA)
            if is_eq:
                row_bg.fill((*C.PERSONA_GOLD, 25))
            elif i % 2 == 0:
                row_bg.fill((255, 255, 255, 6))
            surf.blit(row_bg, (px + 4, ry + 3))

            # Número + nombre
            eq_col = C.PERSONA_GOLD if is_eq else C.PERSONA_WHITE
            name_str = f"{i+1}.  {it.nombre}"
            if is_eq:
                name_str += "  ★"
            surf.blit(self.font_std.render(name_str, True, eq_col), (px + 14, ry + 4))

            # Detalle técnico a la derecha
            if it.tipo == "arma":
                detail = f"POD {it.poder}  HIT {it.precision_bonus:+}  CRT {it.critico_bonus}"
            else:
                detail = f"Cura {it.cura} HP"
                if getattr(it, "cura_estado", None):
                    detail += f"  +{it.cura_estado}"
            ds = self.font_mini.render(detail, True, (130, 145, 165))
            surf.blit(ds, (px + pw - ds.get_width() - 14, ry + 6))

            # Separador
            if i < len(sel_unidad.inventario) - 1:
                pygame.draw.line(surf, (35, 35, 55),
                                 (px + 10, ry + 41), (px + pw - 10, ry + 41), 1)

        hint = self.font_mini.render("ESC  Volver", True, (80, 90, 110))
        surf.blit(hint, (px + pw - hint.get_width() - 10, py + ph - 18))

    def draw_skills_menu(self, surf, sel_unidad):
        """Habilidades P3R: tarjetas navy con franja teal, badge MP circular, descripción de efecto."""
        if not sel_unidad:
            self._anim_reset("skill_menu")
            return

        t = self._anim_t("skill_menu")
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        pw, ph = 460, min(330, 64 + len(sel_unidad.habilidades) * 52 + 24)
        px = W // 2 - pw // 2
        # Slide desde abajo
        py = int(H // 2 - ph // 2 + (H - H // 2 + ph) * (1 - t))

        # Panel base P3R
        self._draw_p3r_panel(surf, px, py, pw, ph, alpha=248, accent=C.P3R_TEAL)
        # Barra de título
        tbar = pygame.Surface((pw - 5, 28), pygame.SRCALPHA)
        tbar.fill((*C.P3R_TEAL, 55))
        surf.blit(tbar, (px + 5, py))
        pygame.draw.line(surf, C.P3R_TEAL, (px + 5, py + 28), (px + pw - 1, py + 28), 1)
        ts = self.font_ui_title.render("HABILIDADES", True, C.P3R_WHITE)
        surf.blit(ts, (px + 14, py + 5))

        for i, sk in enumerate(sel_unidad.habilidades):
            ry = py + 36 + i * 52
            tiene_mp = sel_unidad.mp_actual >= sk.costo_mp

            # Tarjeta de habilidad: fondo alternado sutil
            card = pygame.Surface((pw - 10, 46), pygame.SRCALPHA)
            card.fill((*C.P3R_BLUE_MID, 18) if i % 2 == 0 else (0, 0, 0, 0))
            surf.blit(card, (px + 5, ry))
            # Borde izquierdo de tarjeta en teal si tiene MP
            if tiene_mp:
                pygame.draw.rect(surf, C.P3R_TEAL_DIM, (px + 5, ry, 2, 46))

            # Nombre de habilidad
            col = C.P3R_WHITE if tiene_mp else (70, 80, 100)
            surf.blit(self.font_std.render(sk.nombre, True, col), (px + 14, ry + 4))

            # Línea de descripción de efecto
            efecto_txt = sk.tipo_efecto.upper()
            if hasattr(sk, "efecto") and sk.efecto:
                efecto_txt += f"  +{sk.efecto}"
            rango_txt = f"Rango {sk.rango[0]}–{sk.rango[1]}  ·  {efecto_txt}"
            surf.blit(self.font_mini.render(rango_txt, True, C.P3R_TEAL_DIM if tiene_mp else (50, 60, 80)),
                      (px + 16, ry + 26))

            # Badge MP circular a la derecha
            mp_col   = C.P3R_MP_BAR if tiene_mp else (40, 50, 75)
            mp_str   = f"{sk.costo_mp}MP"
            badge_r  = 18
            badge_cx = px + pw - badge_r - 14
            badge_cy = ry + 23
            badge_bg = pygame.Surface((badge_r*2, badge_r*2), pygame.SRCALPHA)
            pygame.draw.circle(badge_bg, (*mp_col, 180 if tiene_mp else 70), (badge_r, badge_r), badge_r)
            pygame.draw.circle(badge_bg, (*C.P3R_TEAL, 100 if tiene_mp else 30), (badge_r, badge_r), badge_r, 1)
            surf.blit(badge_bg, (badge_cx - badge_r, badge_cy - badge_r))
            ms = self.font_mini.render(mp_str, True, C.P3R_WHITE)
            surf.blit(ms, ms.get_rect(center=(badge_cx, badge_cy)))

            # Separador teal
            if i < len(sel_unidad.habilidades) - 1:
                pygame.draw.line(surf, C.P3R_DARK_TEAL,
                                 (px + 12, ry + 50), (px + pw - 12, ry + 50), 1)

        # Barra inferior: MP actual + hint
        bar_y = py + ph - 22
        mp_pct = sel_unidad.mp_actual / sel_unidad.max_mp if sel_unidad.max_mp > 0 else 0
        mp_txt = f"MP  {sel_unidad.mp_actual} / {sel_unidad.max_mp}"
        surf.blit(self.font_mini.render(mp_txt, True, C.P3R_MP_BAR), (px + 14, bar_y))
        self._draw_bar(surf, px + 14 + 90, bar_y + 3, 100, 4,
                       sel_unidad.mp_actual, sel_unidad.max_mp, C.P3R_MP_BAR, (5, 5, 20))
        hint = self.font_mini.render("ESC  Volver", True, C.P3R_TEAL_DIM)
        surf.blit(hint, (px + pw - hint.get_width() - 10, bar_y))

    # -------------------------
    # Diálogo de batalla — estilo Persona
    # -------------------------
    def draw_battle_dialogue(self, surf, payload: dict):
        """Diálogo de batalla P3R: panel navy con franja teal, portrait circular, typewriter cursor."""
        if not payload or not payload.get("active"):
            self._anim_reset("dialogue")
            return

        speaker = payload.get("speaker", "")
        text    = payload.get("text", "")
        if not text:
            return

        unit_id = payload.get("unit_id", "")
        bando   = "aliado" if "ALLY" in unit_id else "enemigo"
        acc     = C.P3R_ALLY if bando == "aliado" else C.P3R_ENEMY

        t = self._anim_t("dialogue")

        W, H   = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        box_h  = 110
        margin = 14
        bw     = W - margin * 2
        # Slide desde abajo
        by = int((H - box_h - margin) + (box_h + margin) * (1 - t))
        bx = margin

        # Fondo navy P3R
        panel = pygame.Surface((bw, box_h), pygame.SRCALPHA)
        panel.fill((*C.P3R_PANEL, 248))
        surf.blit(panel, (bx, by))

        # Franja lateral teal
        pygame.draw.rect(surf, C.P3R_TEAL, (bx, by, 6, box_h))

        # Borde superior teal + línea secundaria
        pygame.draw.line(surf, C.P3R_TEAL,    (bx, by),     (bx + bw, by),     2)
        pygame.draw.line(surf, C.P3R_TEAL_DIM,(bx, by + 2), (bx + bw, by + 2), 1)
        # Borde inferior
        pygame.draw.line(surf, C.P3R_DARK_TEAL,(bx, by + box_h - 1), (bx + bw, by + box_h - 1), 1)

        # Portrait circular
        portrait = get_portrait_hud(
            unit_id.lower(), bando,
            letter=speaker[0] if speaker else "?"
        )
        port_cx = bx + 38
        port_cy = by + box_h // 2
        port_r  = 28
        # Clip circular
        port_mask = pygame.Surface((port_r*2, port_r*2), pygame.SRCALPHA)
        pygame.draw.circle(port_mask, (255, 255, 255, 255), (port_r, port_r), port_r)
        port_clipped = portrait.copy()
        port_clipped.blit(port_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(port_clipped, (port_cx - port_r, port_cy - port_r))
        # Marco circular de bando
        pygame.draw.circle(surf, acc,            (port_cx, port_cy), port_r + 2, 2)
        pygame.draw.circle(surf, C.P3R_TEAL_DIM, (port_cx, port_cy), port_r + 4, 1)

        # Nombre: placa teal a la derecha del portrait
        name_x = bx + port_r * 2 + 20
        name_bg = pygame.Surface((170, 22), pygame.SRCALPHA)
        name_bg.fill((*acc, 55))
        surf.blit(name_bg, (name_x, by + 6))
        pygame.draw.line(surf, acc, (name_x, by + 28), (name_x + 170, by + 28), 1)
        ns = self.font_ui_title.render(speaker, True, C.P3R_WHITE)
        surf.blit(ns, (name_x + 6, by + 6))

        # Texto del diálogo
        text_x = name_x + 2
        text_y = by + 34
        lines  = wrap_text(text, self.font_std, bw - name_x + bx - 20)[:3]
        for i, line in enumerate(lines):
            surf.blit(self.font_std.render(line, True, C.P3R_WHITE),
                      (text_x, text_y + i * 24))

        # Cursor parpadeante teal
        tick_on = (pygame.time.get_ticks() // 420) % 2 == 0
        if tick_on:
            cont = self.font_mini.render("▼", True, C.P3R_TEAL)
            surf.blit(cont, (bx + bw - 22, by + box_h - 18))

    # -------------------------
    # Log de combate — estilo Persona
    # -------------------------
    def draw_combat_log(self, surf, log_lines: list):
        """Log de combate P3R: panel navy lateral derecho, franja teal, entradas con color semántico."""
        if not log_lines:
            return

        lw = 222
        lh = len(log_lines) * 19 + 16
        lx = C.ANCHO_PANTALLA - lw - 6
        ly = 6

        # Fondo navy
        bg = pygame.Surface((lw, lh), pygame.SRCALPHA)
        bg.fill((*C.P3R_PANEL, 215))
        surf.blit(bg, (lx, ly))
        # Borde teal
        pygame.draw.rect(surf, C.P3R_TEAL, (lx, ly, lw, lh), 1)
        # Franja superior teal (línea de cabecera)
        pygame.draw.line(surf, C.P3R_TEAL,    (lx, ly),     (lx + lw, ly),     2)
        pygame.draw.line(surf, C.P3R_TEAL_DIM,(lx, ly + 2), (lx + lw, ly + 2), 1)
        # Franja izquierda teal
        pygame.draw.rect(surf, C.P3R_TEAL, (lx, ly, 3, lh))

        for i, line in enumerate(log_lines):
            # Color semántico por contenido
            if any(k in line for k in ("crítico", "CRIT", "★")):
                col = C.P3R_GOLD
            elif any(k in line for k in ("derrota", "muere", "eliminado", "KO")):
                col = C.P3R_ENEMY
            elif any(k in line for k in ("cura", "HP+", "restaura")):
                col = C.P3R_HP_HIGH
            elif any(k in line for k in ("MP", "habilidad", "skill")):
                col = C.P3R_MP_BAR
            elif any(k in line for k in ("esquiva", "falla", "miss")):
                col = C.P3R_TEAL_DIM
            else:
                # Entradas más recientes más brillantes
                alpha = int(160 + (i / max(len(log_lines) - 1, 1)) * 75)
                col = (alpha, alpha + 10, alpha + 20)

            # Flash teal en la entrada más reciente
            if i == len(log_lines) - 1:
                flash = pygame.Surface((lw - 5, 17), pygame.SRCALPHA)
                flash.fill((*C.P3R_TEAL, 18))
                surf.blit(flash, (lx + 4, ly + 6 + i * 19 - 1))

            surf.blit(self.font_mini.render(line, True, col),
                      (lx + 7, ly + 7 + i * 19))

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

        # Jefe → usar siempre el frame 0 (idle estable) escalado a 2× (64×64).
        # Usar frames[0] evita que la animación cambie a un sprite vecino en la hoja.
        if getattr(u, "is_boss", False) and frames[0].get_width() <= C.TAMANO_TILE:
            sprite = pygame.transform.scale(frames[0], (C.TAMANO_TILE * 2, C.TAMANO_TILE * 2))

        # Unidad inactiva → semitransparente
        if u.ha_actuado:
            sprite = sprite.copy()
            sprite.set_alpha(110)

        # Detectar sprite grande (64×64) — dragones, mamuts, etc.
        sw, sh = sprite.get_width(), sprite.get_height()
        is_large = sw > C.TAMANO_TILE or sh > C.TAMANO_TILE
        # Centrar horizontalmente y anclar la base del sprite al borde inferior del tile
        draw_x = px - (sw - C.TAMANO_TILE) // 2
        draw_y = py - (sh - C.TAMANO_TILE)

        # Halo dorado si está en awakening (ajustado al tamaño real del sprite)
        if getattr(u, "awakened", False):
            pygame.draw.rect(surf, C.AMARILLO_AWK, (draw_x - 1, draw_y - 1, sw + 2, sh + 2), 2)

        surf.blit(sprite, (draw_x, draw_y))

        # Barras encima del sprite (HP/MP sobre la cabeza)
        bar_x = px + 1
        bar_w = C.TAMANO_TILE - 2
        bar_top = draw_y - 5  # 5px sobre el borde superior del sprite

        # Barra HP
        pct_hp = max(0.0, u.hp_actual / u.max_hp) if u.max_hp > 0 else 0.0
        pygame.draw.rect(surf, C.NEGRO,    (bar_x, bar_top, bar_w, 4))
        pygame.draw.rect(surf, C.ROJO_HP,  (bar_x, bar_top, bar_w, 4))
        pygame.draw.rect(surf, C.VERDE_HP, (bar_x, bar_top, int(bar_w * pct_hp), 4))

        # Barra MP
        if u.max_mp > 0:
            pct_mp = max(0.0, u.mp_actual / u.max_mp)
            pygame.draw.rect(surf, C.NEGRO,   (bar_x, bar_top + 4, bar_w, 2))
            pygame.draw.rect(surf, C.AZUL_MP, (bar_x, bar_top + 4, int(bar_w * pct_mp), 2))

        # Barra Awakening (solo héroes) — bajo el tile
        if u.es_heroe and getattr(u, "awakening_type", None):
            pct_awk = getattr(u, "awakening_meter", 0) / 100
            awk_y = py + C.TAMANO_TILE
            pygame.draw.rect(surf, C.NEGRO,       (bar_x, awk_y, bar_w, 2))
            pygame.draw.rect(surf, C.AMARILLO_AWK,(bar_x, awk_y, int(bar_w * pct_awk), 2))

        # Nivel (esquina superior derecha del tile)
        lvl = self.font_mini.render(str(u.nivel), True, C.BLANCO)
        surf.blit(lvl, (px + C.TAMANO_TILE - lvl.get_width() - 1, py + 1))

    # -------------------------
    # Roguelike: selección de héroes
    # -------------------------
    def draw_hero_selection(self, surf, state: dict):
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx = W // 2

        # Fondo P3R navy con hexágonos
        self._draw_p3r_gradient_bg(surf)
        self._draw_hex_pattern(surf, alpha=14)

        # Título P3R
        self._draw_p3r_title_bar(surf, "ELIGE TU GRUPO", 38)

        # Líneas teal decorativas
        pygame.draw.line(surf, C.P3R_TEAL,    (40, 58), (W - 40, 58), 2)
        pygame.draw.line(surf, C.P3R_TEAL_DIM,(40, 60), (W - 40, 60), 1)

        heroes   = state.get("rogue_heroes", [])
        selected = state.get("rogue_selected", [])
        cursor   = state.get("rogue_cursor", 0)

        # Grid: máximo 4 columnas, 2 filas si hay más de 4 héroes
        card_w, card_h = 160, 146
        spacing_x, spacing_y = 10, 10
        cols = 4
        row_y0 = 70

        for i, hero in enumerate(heroes):
            row = i // cols
            col_in_row = i % cols
            heroes_this_row = min(cols, len(heroes) - row * cols)
            row_w = heroes_this_row * (card_w + spacing_x) - spacing_x
            row_x0 = (W - row_w) // 2

            hx = row_x0 + col_in_row * (card_w + spacing_x)
            hy = row_y0 + row * (card_h + spacing_y)

            is_sel    = hero in selected
            is_cursor = (i == cursor)

            # Fondo de la carta P3R
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            if is_sel:
                card_surf.fill((*C.P3R_BLUE_MID, 90))
            elif is_cursor:
                card_surf.fill((*C.P3R_PANEL, 220))
            else:
                card_surf.fill((*C.P3R_NAVY, 160))
            surf.blit(card_surf, (hx, hy))

            # Borde exterior teal (seleccionado = dorado)
            bw   = 2 if is_sel or is_cursor else 1
            bcol = C.P3R_GOLD if is_sel else C.P3R_TEAL if is_cursor else C.P3R_DARK_TEAL
            pygame.draw.rect(surf, bcol, (hx, hy, card_w, card_h), bw)
            # Línea interna teal_dim
            if is_cursor or is_sel:
                pygame.draw.rect(surf, C.P3R_DARK_TEAL,
                                 (hx + bw + 1, hy + bw + 1,
                                  card_w - (bw + 1)*2, card_h - (bw + 1)*2), 1)

            # Franja superior teal (o color de clase si seleccionado)
            top_col = hero.color if is_sel else C.P3R_TEAL if is_cursor else C.P3R_DARK_TEAL
            pygame.draw.rect(surf, top_col, (hx + bw, hy + bw, card_w - bw*2, 4))

            # Círculo del héroe — con halo teal si cursor
            circ_cx = hx + card_w // 2
            circ_cy = hy + 40
            if is_cursor:
                glow = pygame.Surface((60, 60), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*C.P3R_TEAL, 30), (30, 30), 30)
                surf.blit(glow, (circ_cx - 30, circ_cy - 30))
            pygame.draw.circle(surf, C.P3R_NAVY,     (circ_cx, circ_cy), 25)
            pygame.draw.circle(surf, hero.color,      (circ_cx, circ_cy), 22)
            ring_col = C.P3R_TEAL if is_cursor else (C.P3R_GOLD if is_sel else C.P3R_TEAL_DIM)
            pygame.draw.circle(surf, ring_col,        (circ_cx, circ_cy), 23, 2)
            ltr = self.font_ui_title.render(hero.nombre[0], True, C.P3R_WHITE)
            surf.blit(ltr, ltr.get_rect(center=(circ_cx, circ_cy)))

            # Nombre
            ncol = C.P3R_GOLD if is_sel else C.P3R_WHITE
            ns = self.font_ui_title.render(hero.nombre, True, ncol)
            surf.blit(ns, ns.get_rect(center=(hx + card_w // 2, hy + 72)))

            # Clase
            cs = self.font_mini.render(hero.clase.upper(), True, C.P3R_TEAL_DIM)
            surf.blit(cs, cs.get_rect(center=(hx + card_w // 2, hy + 87)))

            # Separador teal
            pygame.draw.line(surf, C.P3R_DARK_TEAL,
                             (hx + 12, hy + 96), (hx + card_w - 12, hy + 96), 1)

            # Descripción con wrap
            for j, ln in enumerate(wrap_text(hero.descripcion, self.font_mini, card_w - 16)[:3]):
                ds = self.font_mini.render(ln, True, (140, 165, 195))
                surf.blit(ds, ds.get_rect(center=(hx + card_w // 2, hy + 108 + j * 13)))

            # Check de seleccionado — círculo teal
            if is_sel:
                chk_bg = pygame.Surface((20, 20), pygame.SRCALPHA)
                pygame.draw.circle(chk_bg, (*C.P3R_TEAL, 220), (10, 10), 10)
                surf.blit(chk_bg, (hx + card_w - 24, hy + 5))
                ck = self.font_ui_title.render("✓", True, C.P3R_WHITE)
                surf.blit(ck, ck.get_rect(center=(hx + card_w - 14, hy + 15)))

        # --- Barra de instrucciones P3R ---
        rows_used = (len(heroes) + cols - 1) // cols
        inst_y = row_y0 + rows_used * (card_h + spacing_y) + 6
        n = len(selected)
        inst_col = C.P3R_TEAL if n >= MIN_HEROES else (100, 110, 130)

        self._draw_p3r_panel(surf, 40, inst_y, W - 80, 54, alpha=210)
        sel_txt   = f"ESPACIO — Seleccionar / Deseleccionar    {n} / {MAX_HEROES} elegidos"
        start_txt = "[F]  Comenzar aventura" if n >= MIN_HEROES else f"Selecciona al menos {MIN_HEROES} héroes"
        st = self.font_std.render(sel_txt,   True, C.P3R_WHITE)
        ft = self.font_std.render(start_txt, True, inst_col)
        surf.blit(st, st.get_rect(center=(cx, inst_y + 16)))
        surf.blit(ft, ft.get_rect(center=(cx, inst_y + 38)))

        # --- Reliquias activas (si las hay) ---
        relics = state.get("rogue_relics", [])
        if relics:
            rel_y = inst_y + 62
            self._draw_p3r_panel(surf, cx - 200, rel_y, 400, 22 + len(relics) * 18,
                                 alpha=180, accent=C.P3R_TEAL)
            rt = self.font_mini.render("▸ Reliquias activas:", True, C.P3R_TEAL)
            surf.blit(rt, (cx - 190, rel_y + 5))
            for i, r in enumerate(relics):
                rs = self.font_mini.render(f"  • {r.nombre}", True, C.P3R_WHITE)
                surf.blit(rs, (cx - 190, rel_y + 20 + i * 18))

    # -------------------------
    # Roguelike: selección de reliquias
    # -------------------------
    def draw_relic_selection(self, surf, state: dict):
        W, H = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx = W // 2

        # Fondo P3R navy con hexágonos
        self._draw_p3r_gradient_bg(surf)
        self._draw_hex_pattern(surf, alpha=14)

        # Título P3R
        self._draw_p3r_title_bar(surf, "ELIGE UNA MEJORA", 38)
        pygame.draw.line(surf, C.P3R_TEAL,    (40, 58), (W - 40, 58), 2)
        pygame.draw.line(surf, C.P3R_TEAL_DIM,(40, 60), (W - 40, 60), 1)

        choices       = state.get("relic_choices", [])
        cursor        = state.get("relic_cursor", 0)
        acquired      = state.get("rogue_relics", [])
        show_acquired = state.get("show_acquired_relics", False)

        # Cartas de reliquias — centradas
        card_w, card_h = 205, 212
        spacing = 24
        total_w = len(choices) * (card_w + spacing) - spacing
        start_x = cx - total_w // 2
        card_y  = 78

        for i, relic in enumerate(choices):
            rx = start_x + i * (card_w + spacing)
            ry = card_y
            is_cursor = (i == cursor)

            # Fondo carta navy
            card_bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_bg.fill((*C.P3R_PANEL, 235) if is_cursor else (*C.P3R_NAVY, 190))
            surf.blit(card_bg, (rx, ry))

            # Borde teal (cursor = oro)
            bcol = C.P3R_GOLD if is_cursor else C.P3R_TEAL_DIM
            bw   = 2 if is_cursor else 1
            pygame.draw.rect(surf, bcol, (rx, ry, card_w, card_h), bw)
            if is_cursor:
                pygame.draw.rect(surf, C.P3R_DARK_TEAL,
                                 (rx + 3, ry + 3, card_w - 6, card_h - 6), 1)

            # Franja superior teal (o color de reliquia si cursor)
            top_col = relic.color if is_cursor else C.P3R_TEAL_DIM
            pygame.draw.rect(surf, top_col, (rx + bw, ry + bw, card_w - bw*2, 5))

            # Círculo icono con halo teal pulsante si cursor
            icon_cx = rx + card_w // 2
            icon_cy = ry + 50
            if is_cursor:
                pulse = abs(pygame.time.get_ticks() % 1600 - 800) / 800.0
                halo_r = int(34 + pulse * 4)
                halo = pygame.Surface((halo_r*2, halo_r*2), pygame.SRCALPHA)
                pygame.draw.circle(halo, (*C.P3R_TEAL, int(30 + pulse * 20)),
                                   (halo_r, halo_r), halo_r)
                surf.blit(halo, (icon_cx - halo_r, icon_cy - halo_r))
            pygame.draw.circle(surf, C.P3R_NAVY,     (icon_cx, icon_cy), 30)
            pygame.draw.circle(surf, relic.color,     (icon_cx, icon_cy), 26)
            ring_col = C.P3R_TEAL if is_cursor else C.P3R_TEAL_DIM
            pygame.draw.circle(surf, ring_col,        (icon_cx, icon_cy), 27, 2)
            ltr = self.font_title.render(relic.nombre[0], True, C.P3R_WHITE)
            surf.blit(ltr, ltr.get_rect(center=(icon_cx, icon_cy)))

            # Nombre
            ncol = C.P3R_GOLD if is_cursor else C.P3R_WHITE
            ns = self.font_ui_title.render(relic.nombre, True, ncol)
            surf.blit(ns, ns.get_rect(center=(rx + card_w // 2, ry + 92)))

            # Separador teal
            pygame.draw.line(surf, C.P3R_DARK_TEAL,
                             (rx + 16, ry + 104), (rx + card_w - 16, ry + 104), 1)

            # Descripción
            for j, ln in enumerate(wrap_text(relic.descripcion, self.font_mini, card_w - 20)[:4]):
                ds = self.font_mini.render(ln, True, C.P3R_TEAL_DIM if is_cursor else (155, 170, 200))
                surf.blit(ds, ds.get_rect(center=(rx + card_w // 2, ry + 118 + j * 18)))

            # Flecha cursor teal
            if is_cursor:
                arr = self.font_ui_title.render("▼", True, C.P3R_TEAL)
                surf.blit(arr, arr.get_rect(center=(rx + card_w // 2, ry + card_h + 14)))

        # Botón "Items adquiridos"
        btn_y = card_y + card_h + 28
        if acquired:
            btn_w, btn_h = 240, 32
            btn_x = cx - btn_w // 2
            btn_bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            btn_col = C.P3R_TEAL if show_acquired else C.P3R_TEAL_DIM
            btn_bg.fill((*btn_col, 40))
            surf.blit(btn_bg, (btn_x, btn_y))
            pygame.draw.rect(surf, btn_col, (btn_x, btn_y, btn_w, btn_h), 1)
            arrow = "▲" if show_acquired else "▼"
            btn_lbl = self.font_std.render(
                f"{arrow}  Items adquiridos ({len(acquired)})  {arrow}",
                True, btn_col)
            surf.blit(btn_lbl, btn_lbl.get_rect(center=(cx, btn_y + btn_h // 2)))

            # Panel desplegable
            if show_acquired:
                t = self._anim_t("acquired_panel")
                panel_w = 440
                panel_h = 26 + len(acquired) * 26 + 10
                panel_x = cx - panel_w // 2
                panel_y = int(btn_y + btn_h + 4 + panel_h * (1 - t))
                panel_clip_y = btn_y + btn_h + 4

                clip_rect = surf.get_clip()
                surf.set_clip(pygame.Rect(0, panel_clip_y, W, H - panel_clip_y))

                self._draw_p3r_panel(surf, panel_x, panel_y, panel_w, panel_h,
                                     alpha=240, accent=C.P3R_TEAL)
                tbar2 = pygame.Surface((panel_w - 5, 24), pygame.SRCALPHA)
                tbar2.fill((*C.P3R_TEAL, 40))
                surf.blit(tbar2, (panel_x + 5, panel_y))
                ts2 = self.font_ui_title.render("ITEMS ADQUIRIDOS", True, C.P3R_WHITE)
                surf.blit(ts2, (panel_x + 12, panel_y + 3))

                for i, r in enumerate(acquired):
                    ry2 = panel_y + 28 + i * 26
                    pygame.draw.circle(surf, r.color,      (panel_x + 20, ry2 + 9), 6)
                    pygame.draw.circle(surf, C.P3R_TEAL_DIM,(panel_x + 20, ry2 + 9), 7, 1)
                    surf.blit(self.font_std.render(r.nombre, True, C.P3R_WHITE),
                              (panel_x + 34, ry2 + 1))
                    desc_s = self.font_mini.render(r.descripcion, True, C.P3R_TEAL_DIM)
                    surf.blit(desc_s, (panel_x + panel_w - desc_s.get_width() - 10, ry2 + 5))

                surf.set_clip(clip_rect)
            else:
                self._anim_reset("acquired_panel")

        # Barra de instrucciones inferior P3R
        inst_txt = "◄ ► Mover     ENTER Confirmar"
        if acquired:
            inst_txt += "     [TAB] Items adquiridos"
        self._draw_p3r_panel(surf, 40, H - 46, W - 80, 32, alpha=200, accent=C.P3R_TEAL)
        inst = self.font_std.render(inst_txt, True, C.P3R_TEAL_DIM)
        surf.blit(inst, inst.get_rect(center=(cx, H - 30)))

    # -------------------------
    # Tienda permanente
    # -------------------------
    def draw_shop_menu(self, surf, state: dict):
        """Tienda de mejoras permanentes — estilo P3R con lista scrollable."""
        W, H   = C.ANCHO_PANTALLA, C.ALTO_PANTALLA
        cx     = W // 2

        self._draw_p3r_gradient_bg(surf)
        self._draw_hex_pattern(surf, alpha=14)

        # ── Cabecera ──────────────────────────────────────────────────────
        self._draw_p3r_title_bar(surf, "TIENDA PERMANENTE", 52)
        pygame.draw.line(surf, C.P3R_TEAL,     (40, 74), (W - 40, 74), 2)
        pygame.draw.line(surf, C.P3R_TEAL_DIM, (40, 76), (W - 40, 76), 1)

        coins      = state.get("shop_coins", 0)
        items      = state.get("shop_items", [])
        purchased  = state.get("shop_purchased", set())
        cursor     = state.get("shop_cursor", 0)
        bonuses    = state.get("shop_bonuses", {})

        # Monedas disponibles — esquina superior derecha
        coin_lbl = self.font_ui_title.render(f"Monedas:  {coins:,}", True, C.P3R_GOLD)
        surf.blit(coin_lbl, (W - coin_lbl.get_width() - 30, 16))

        # ── Panel de lista de ítems ───────────────────────────────────────
        list_x, list_y = 20, 90
        list_w, list_h = W - 300, H - 110
        self._draw_p3r_panel(surf, list_x, list_y, list_w, list_h, alpha=220)

        VISIBLE  = 10
        scroll   = max(0, cursor - VISIBLE + 1)
        row_h    = (list_h - 20) // VISIBLE

        for i_vis in range(VISIBLE):
            idx = scroll + i_vis
            if idx >= len(items):
                break
            item   = items[idx]
            ry     = list_y + 10 + i_vis * row_h
            bought = item.item_id in purchased
            active = idx == cursor

            # Fondo de fila
            row_col = (
                (*C.P3R_TEAL, 45)      if active and not bought else
                (*C.P3R_TEAL_DIM, 18) if active else
                (30, 30, 50, 30)
            )
            row_surf = pygame.Surface((list_w - 10, row_h - 2), pygame.SRCALPHA)
            row_surf.fill(row_col)
            surf.blit(row_surf, (list_x + 5, ry))

            # Indicador comprado
            if bought:
                chk = self.font_mini.render("[OK]", True, C.P3R_TEAL)
                surf.blit(chk, (list_x + 10, ry + row_h // 2 - 5))
                name_col = C.P3R_TEAL_DIM
            else:
                can_buy = coins >= item.price
                name_col = C.P3R_WHITE if can_buy else (100, 100, 130)

            # Nombre + precio
            name_s  = self.font_std.render(item.name, True, name_col)
            price_s = self.font_mini.render(
                "COMPRADO" if bought else f"{item.price}  monedas",
                True, C.P3R_TEAL if bought else (C.P3R_GOLD if (not bought and coins >= item.price) else (120, 100, 80))
            )
            surf.blit(name_s,  (list_x + 40, ry + 4))
            surf.blit(price_s, (list_x + 40, ry + 22))

            # Separador
            if i_vis < VISIBLE - 1:
                pygame.draw.line(surf, C.P3R_DARK_TEAL,
                                 (list_x + 20, ry + row_h - 1),
                                 (list_x + list_w - 20, ry + row_h - 1), 1)

        # ── Panel de detalle del ítem seleccionado ────────────────────────
        det_x, det_y = W - 270, 90
        det_w, det_h = 255, H - 110
        self._draw_p3r_panel(surf, det_x, det_y, det_w, det_h, alpha=230, accent=C.P3R_TEAL)

        # Barra de título del panel
        tbar = pygame.Surface((det_w - 5, 24), pygame.SRCALPHA)
        tbar.fill((*C.P3R_TEAL, 50))
        surf.blit(tbar, (det_x + 5, det_y))
        det_title = self.font_ui_title.render("DETALLE", True, C.P3R_WHITE)
        surf.blit(det_title, (det_x + 14, det_y + 3))

        if 0 <= cursor < len(items):
            sel   = items[cursor]
            bought = sel.item_id in purchased
            dy    = det_y + 34

            # Nombre
            name_big = self.font_std.render(sel.name, True,
                                            C.P3R_TEAL if bought else C.P3R_WHITE)
            surf.blit(name_big, (det_x + 12, dy)); dy += 26

            # Estado
            status_s = self.font_mini.render(
                "COMPRADO" if bought else f"Precio:  {sel.price} monedas",
                True, C.P3R_TEAL if bought else C.P3R_GOLD)
            surf.blit(status_s, (det_x + 12, dy)); dy += 22
            pygame.draw.line(surf, C.P3R_DARK_TEAL, (det_x + 10, dy), (det_x + det_w - 10, dy), 1)
            dy += 8

            # Descripción (word-wrap manual)
            desc = sel.description
            words, line, max_w = desc.split(), "", det_w - 24
            for w in words:
                test = (line + " " + w).strip()
                if self.font_mini.size(test)[0] > max_w:
                    s = self.font_mini.render(line, True, (160, 170, 200))
                    surf.blit(s, (det_x + 12, dy)); dy += 16
                    line = w
                else:
                    line = test
            if line:
                s = self.font_mini.render(line, True, (160, 170, 200))
                surf.blit(s, (det_x + 12, dy)); dy += 22
            pygame.draw.line(surf, C.P3R_DARK_TEAL, (det_x + 10, dy), (det_x + det_w - 10, dy), 1)
            dy += 8

            # Bonificaciones del ítem
            stat_title = self.font_mini.render("BONIFICACIONES:", True, C.P3R_TEAL_DIM)
            surf.blit(stat_title, (det_x + 12, dy)); dy += 16
            stats = []
            if sel.hp:        stats.append(f"+{sel.hp} HP")
            if sel.mp:        stats.append(f"+{sel.mp} MP")
            if sel.strength:  stats.append(f"+{sel.strength} STR")
            if sel.defense:   stats.append(f"+{sel.defense} DEF")
            if sel.speed:     stats.append(f"+{sel.speed} SPD")
            if sel.movement:  stats.append(f"+{sel.movement} MOV")
            if sel.start_level: stats.append(f"Nivel inicial {sel.start_level}")
            if sel.coin_bonus:  stats.append(f"+{int(sel.coin_bonus*100)}% monedas")
            for st in stats:
                st_s = self.font_mini.render(f"  {st}", True, C.P3R_WHITE)
                surf.blit(st_s, (det_x + 12, dy)); dy += 15

        # ── Bonificaciones activas totales ────────────────────────────────
        dy_bot = det_y + det_h - 100
        pygame.draw.line(surf, C.P3R_DARK_TEAL,
                         (det_x + 10, dy_bot), (det_x + det_w - 10, dy_bot), 1)
        tot_lbl = self.font_mini.render("TOTAL ACTIVO:", True, C.P3R_TEAL_DIM)
        surf.blit(tot_lbl, (det_x + 12, dy_bot + 6))
        dy_bot += 22
        active_stats = []
        if bonuses.get("hp"):        active_stats.append(f"+{bonuses['hp']} HP")
        if bonuses.get("mp"):        active_stats.append(f"+{bonuses['mp']} MP")
        if bonuses.get("strength"):  active_stats.append(f"+{bonuses['strength']} STR")
        if bonuses.get("defense"):   active_stats.append(f"+{bonuses['defense']} DEF")
        if bonuses.get("speed"):     active_stats.append(f"+{bonuses['speed']} SPD")
        if bonuses.get("movement"):  active_stats.append(f"+{bonuses['movement']} MOV")
        if bonuses.get("coin_bonus"): active_stats.append(f"+{int(bonuses['coin_bonus']*100)}% coins")
        if bonuses.get("start_level"): active_stats.append(f"Nivel {bonuses['start_level']} inicial")
        for st in active_stats:
            s = self.font_mini.render(f"  {st}", True, C.P3R_TEAL)
            surf.blit(s, (det_x + 12, dy_bot)); dy_bot += 14

        # ── Footer instrucciones ──────────────────────────────────────────
        inst = self.font_mini.render(
            "↑↓ Navegar    ENTER Comprar    ESC Volver", True, (70, 90, 110))
        surf.blit(inst, inst.get_rect(center=(cx, H - 18)))

    # -------------------------
    # Render principal
    # -------------------------
    def render(self, surf, state: dict):
        estado = state.get("estado_juego", "MENU_PRINCIPAL")

        if estado == "MENU_PRINCIPAL":
            self.draw_main_menu(surf, state)
            return
        if estado == "MENU_PUNTAJES":
            self.draw_all_scores(surf, state.get("top_scores", []))
            return
        if estado == "MENU_TIENDA":
            self.draw_shop_menu(surf, state)
            return
        if estado == "MENU_CONTROLES":
            self.draw_controls_menu(surf)
            return
        if estado == "MENU_SELECCION_GRUPO":
            self.draw_hero_selection(surf, state)
            return
        if estado == "MENU_MEJORAS":
            self.draw_relic_selection(surf, state)
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

        # Clima: sincronizar tipo cuando cambia el mapa
        weather = state.get("weather")
        if weather != self._current_weather:
            self._current_weather = weather
            self._weather.set_weather(weather)

        # Mapa y extras
        self.draw_map(surf, grid)
        self.draw_thrones(surf, thrones)
        self.draw_items(surf, items_suelo)

        # Efectos de clima (sobre el mapa, bajo las unidades)
        dt = state.get("dt", 0.016)
        self._weather.update(dt)
        self._weather.draw(surf)

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
        fase     = state.get("fase_actual", "")
        modo     = state.get("modo_juego", "")
        map_num  = state.get("map_number", 0)
        tier     = state.get("difficulty_tier", "")
        map_def  = state.get("map_def")
        map_name = map_def.name if map_def else ""

        color_fase = C.AZUL_MP if fase == "aliado" else C.ROJO_HP
        color_tier = {
            "easy":   (100, 220, 100),
            "medium": (220, 200, 60),
            "hard":   (220, 100, 40),
            "boss":   (200, 40,  200),
        }.get(tier, C.BLANCO)

        # Panel HUD con estilo FE: borde izquierdo coloreado según fase
        self._draw_panel(surf, 4, 3, 218, 56, alpha=210, accent=(50, 65, 100))
        pygame.draw.rect(surf, color_fase, (4, 3, 4, 56))  # franja lateral de fase
        surf.blit(self.font_mini.render(f"{fase.upper()}  [{modo}]", True, color_fase),   (13, 7))
        surf.blit(self.font_mini.render(f"Mapa {map_num + 1}: {map_name}", True, C.BLANCO), (13, 24))
        surf.blit(self.font_mini.render(tier.upper(), True, color_tier), (13, 41))
        # Dot de color dificultad
        pygame.draw.circle(surf, color_tier, (9, 45), 3)

        # Badge de jefe: pulsante en rojo vivo (esquina superior derecha)
        if state.get("is_boss_map"):
            W = C.ANCHO_PANTALLA
            pulse = abs((self._anim_tick % 60) - 30) / 30.0   # 0.0..1.0
            badge_r = int(180 + 75 * pulse)
            badge_color = (badge_r, 20, 20)
            badge_w, badge_h = 110, 28
            bx = W - badge_w - 6
            by = 6
            self._draw_panel(surf, bx, by, badge_w, badge_h, alpha=220,
                             accent=badge_color)
            pygame.draw.rect(surf, badge_color, (bx, by, 4, badge_h))
            label = self.font_std.render("! JEFE !", True, (255, 80, 80))
            surf.blit(label, (bx + (badge_w - label.get_width()) // 2,
                               by + (badge_h - label.get_height()) // 2))
