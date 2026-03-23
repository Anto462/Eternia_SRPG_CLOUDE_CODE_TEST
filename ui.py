# ui.py
import pygame
import constants as C
print("TOP OF ui.py reached")

def wrap_text(text, font, max_width):
    words = text.split(" ")
    lines = []
    cur = ""
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

print("ABOUT TO DEFINE UIRenderer")
class UIRenderer:
    def __init__(self, fonts: dict):
        self.font_std = fonts["std"]
        self.font_mini = fonts["mini"]
        self.font_title = fonts["title"]
        self.font_ui_title = fonts["ui_title"]

        self.sup_fx = pygame.Surface((C.ANCHO_PANTALLA, C.ALTO_PANTALLA), pygame.SRCALPHA)

    # -----------------------
    # Helpers UI
    # -----------------------
    def draw_box(self, surf, x, y, w, h):
        rect = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surf, C.FONDO_UI, rect)
        pygame.draw.rect(surf, C.BORDE_UI, rect, 2)

        pygame.draw.line(surf, C.GRIS_OSCURO, (x + 2, y + h - 2), (x + w - 2, y + h - 2))
        pygame.draw.line(surf, C.GRIS_OSCURO, (x + w - 2, y + 2), (x + w - 2, y + h - 2))

    def draw_turn_banner(self, surf, text, color, timer):
        if timer <= 0:
            return
        overlay = pygame.Surface((C.ANCHO_PANTALLA, 100))
        overlay.set_alpha(180)
        overlay.fill(C.NEGRO)
        surf.blit(overlay, (0, C.ALTO_PANTALLA // 2 - 50))

        txt_surf = self.font_title.render(text, True, color)
        rect_txt = txt_surf.get_rect(center=(C.ANCHO_PANTALLA // 2, C.ALTO_PANTALLA // 2))
        surf.blit(txt_surf, rect_txt)

    # -----------------------
    # Pantallas
    # -----------------------
    def draw_main_menu(self, surf):
        surf.fill(C.NEGRO)
        surf.blit(self.font_title.render("ETERNIA SRPG", True, C.BLANCO), (200, 100))

        self.draw_box(surf, 250, 200, 300, 200)
        surf.blit(self.font_std.render("1. Jugar PvP (Local)", True, C.BLANCO), (270, 220))
        surf.blit(self.font_std.render("2. Jugar PvE (Contra IA)", True, C.BLANCO), (270, 260))
        surf.blit(self.font_std.render("3. Controles", True, C.BLANCO), (270, 300))

    def draw_controls_menu(self, surf):
        surf.fill(C.NEGRO)
        surf.blit(self.font_title.render("CONTROLES", True, C.BLANCO), (300, 50))

        self.draw_box(surf, 100, 120, 600, 400)
        controles = [
            "Flechas: Mover Cursor",
            "ENTER/ESPACIO: Seleccionar / Confirmar",
            "ESCAPE: Cancelar / Volver",
            "F: Finalizar Turno Manualmente",
            "A: Atacar (en menú)",
            "I: Inventario (en menú)",
            "H: Habilidad (en menú)",
            "W: Activar Awakening (si barra llena)",
            "C: Conquistar (Solo Héroe en Trono)",
        ]
        for i, line in enumerate(controles):
            surf.blit(self.font_std.render(line, True, C.BLANCO), (120, 150 + i * 40))

    def draw_end_screen(self, surf, victory: bool):
        bg_color = (0, 50, 0) if victory else (50, 0, 0)
        surf.fill(bg_color)

        txt = "VICTORIA" if victory else "GAME OVER"
        color = C.AMARILLO_AWK if victory else C.ROJO_HP

        surf.blit(self.font_title.render(txt, True, color), (300, 200))
        surf.blit(self.font_std.render("Presiona [R] para Reiniciar", True, C.BLANCO), (280, 300))
        surf.blit(self.font_std.render("Presiona [ESC] para Menú", True, C.BLANCO), (280, 340))

    # -----------------------
    # Mapa / HUD
    # -----------------------
    def draw_map(self, surf, grid):
        for y in range(len(grid)):
            for x in range(len(grid[0])):
                tile = grid[y][x]
                pygame.draw.rect(
                    surf,
                    C.INFO_TERRENO[tile]["color"],
                    (x * C.TAMANO_TILE, y * C.TAMANO_TILE, C.TAMANO_TILE, C.TAMANO_TILE),
                )

        for i in range(0, C.ANCHO_PANTALLA, C.TAMANO_TILE):
            pygame.draw.line(surf, (0, 0, 0, 30), (i, 0), (i, C.ALTO_PANTALLA))
        for j in range(0, C.ALTO_PANTALLA, C.TAMANO_TILE):
            pygame.draw.line(surf, (0, 0, 0, 30), (0, j), (C.ANCHO_PANTALLA, j))

    def draw_thrones(self, surf, thrones: dict | None):
        if not thrones:
            return
        for _, (tx, ty) in thrones.items():
            pygame.draw.rect(surf, C.PURPURA_TRONO, (tx * C.TAMANO_TILE, ty * C.TAMANO_TILE, C.TAMANO_TILE, C.TAMANO_TILE))
            pygame.draw.rect(surf, C.BLANCO, (tx * C.TAMANO_TILE, ty * C.TAMANO_TILE, C.TAMANO_TILE, C.TAMANO_TILE), 1)

    def draw_items(self, surf, items_suelo: dict):
        for (ix, iy), _ in items_suelo.items():
            pygame.draw.rect(surf, C.DORADO_COFRE, (ix * C.TAMANO_TILE + 8, iy * C.TAMANO_TILE + 8, 16, 16))
            pygame.draw.rect(surf, (200, 150, 0), (ix * C.TAMANO_TILE + 8, iy * C.TAMANO_TILE + 8, 16, 16), 1)

    def draw_move_range(self, surf, casillas):
        for (rx, ry) in casillas:
            pygame.draw.rect(surf, C.AZUL_RANGO, (rx * C.TAMANO_TILE, ry * C.TAMANO_TILE, C.TAMANO_TILE, C.TAMANO_TILE), 2)

    def draw_target_overlay(self, surf, targets, is_heal=False):
        self.sup_fx.fill((0, 0, 0, 0))
        col = C.VERDE_RANGO_SKILL if is_heal else C.ROJO_ATAQUE
        for t in targets:
            pygame.draw.rect(self.sup_fx, col, (t.x * C.TAMANO_TILE, t.y * C.TAMANO_TILE, C.TAMANO_TILE, C.TAMANO_TILE))
        surf.blit(self.sup_fx, (0, 0))

    def draw_cursor(self, surf, cx, cy, selected_mode=False):
        pygame.draw.rect(
            surf,
            C.ROJO_CURSOR if selected_mode else C.AMARILLO_CURSOR,
            (cx * C.TAMANO_TILE, cy * C.TAMANO_TILE, C.TAMANO_TILE, C.TAMANO_TILE),
            3
        )

    def draw_unit_panel(self, surf, unidad):
        if not unidad:
            return

        x, y = 10, C.ALTO_PANTALLA - 120
        w, h = 250, 110
        self.draw_box(surf, x, y, w, h)

        surf.blit(self.font_ui_title.render(f"{unidad.nombre} (Nv.{unidad.nivel})", True, C.BLANCO), (x + 10, y + 5))

        col1_x = x + 10
        col2_x = x + 130

        surf.blit(self.font_mini.render(f"HP: {unidad.hp_actual}/{unidad.max_hp}", True, C.VERDE_HP), (col1_x, y + 35))
        surf.blit(self.font_mini.render(f"MP: {unidad.mp_actual}/{unidad.max_mp}", True, C.AZUL_MP), (col1_x, y + 55))

        arma_txt = unidad.arma_equipada.nombre if unidad.arma_equipada else "Puños"
        surf.blit(self.font_mini.render(f"Eq: {arma_txt}", True, (200, 200, 200)), (col1_x, y + 75))

        surf.blit(self.font_mini.render(f"Fuerza: {unidad.fuerza}", True, C.BLANCO), (col2_x, y + 35))
        surf.blit(self.font_mini.render(f"Defensa: {unidad.defensa}", True, C.BLANCO), (col2_x, y + 55))
        surf.blit(self.font_mini.render(f"Mov: {unidad.movimiento}", True, C.BLANCO), (col2_x, y + 75))

        if getattr(unidad, "awakened", False):
            surf.blit(self.font_mini.render("¡AWAKENING ACTIVO!", True, C.AMARILLO_AWK), (x + 10, y + 90))

    # -----------------------
    # Menús contextuales
    # -----------------------
    def draw_action_menu(self, surf, sel_unidad, thrones=None):
        if not sel_unidad:
            return

        px, py = sel_unidad.x * C.TAMANO_TILE + 40, sel_unidad.y * C.TAMANO_TILE - 20
        if px > C.ANCHO_PANTALLA - 150:
            px = sel_unidad.x * C.TAMANO_TILE - 150
        if py < 0:
            py = 10

        alto_menu = 140
        can_conquer = False
        if thrones and sel_unidad.es_heroe:
            throne = thrones.get(sel_unidad.bando)
            if throne and (sel_unidad.x, sel_unidad.y) == throne:
                can_conquer = True
                alto_menu += 30

        self.draw_box(surf, px, py, 140, alto_menu)
        surf.blit(self.font_std.render("[A]tacar", True, C.BLANCO), (px + 10, py + 10))
        surf.blit(self.font_std.render("[H]abilidad", True, C.BLANCO), (px + 10, py + 40))
        surf.blit(self.font_std.render("[I]nventario", True, C.BLANCO), (px + 10, py + 70))
        surf.blit(self.font_std.render("[E]sperar", True, C.BLANCO), (px + 10, py + 100))

        if sel_unidad.es_heroe and getattr(sel_unidad, "awakening_meter", 0) >= 100:
            surf.blit(self.font_mini.render("[W] WAKE!", True, C.AMARILLO_AWK), (px + 10, py + 120))

        if can_conquer:
            surf.blit(self.font_std.render("[C]onquistar", True, C.PURPURA_TRONO), (px + 10, py + 130))

    def draw_inventory_menu(self, surf, sel_unidad):
        if not sel_unidad:
            return
        self.draw_box(surf, 200, 150, 400, 300)
        surf.blit(self.font_ui_title.render(f"Inventario: {sel_unidad.nombre}", True, C.BLANCO), (220, 160))

        for i, it in enumerate(sel_unidad.inventario):
            st = "(E)" if it == sel_unidad.arma_equipada else ""
            surf.blit(self.font_std.render(f"{i+1}. {it.nombre} {st}", True, C.BLANCO), (220, 200 + i * 30))
            det = f"Poder: {it.poder}" if it.tipo == "arma" else f"Cura: {it.cura}"
            surf.blit(self.font_mini.render(det, True, C.GRIS_INACTIVO), (400, 205 + i * 30))

    def draw_skills_menu(self, surf, sel_unidad):
        if not sel_unidad:
            return
        self.draw_box(surf, 200, 150, 400, 200)
        surf.blit(self.font_ui_title.render("Habilidades", True, C.BLANCO), (220, 160))

        for i, sk in enumerate(sel_unidad.habilidades):
            col = C.BLANCO if sel_unidad.mp_actual >= sk.costo_mp else C.GRIS_INACTIVO
            surf.blit(self.font_std.render(f"{i+1}. {sk.nombre} ({sk.costo_mp} MP)", True, col), (220, 200 + i * 30))
    
    def draw_battle_quote(self, surf, unit, text):
        self.draw_box(surf, 50, 380, 700, 100)
        surf.blit(self.font_std.render(f"{unit.nombre}:", True, C.BLANCO), (70, 400))
        surf.blit(self.font_std.render(text, True, C.BLANCO), (70, 430))

    
    def draw_battle_dialogue(self, surf, payload: dict):
        if not payload or not payload.get("active"):
            return
        speaker = payload.get("speaker", "")
        text = payload.get("text", "")

        if not text:
            return  # si está vacío, ni lo dibujes

        # caja estilo FE: abajo, casi full width, con margen
        margin = 24
        box_h = 120
        x = margin
        y = C.ALTO_PANTALLA - box_h - margin
        w = C.ANCHO_PANTALLA - margin * 2
        h = box_h

        self.draw_box(surf, x, y, w, h)

        # nombre arriba-izq
        surf.blit(self.font_ui_title.render(speaker, True, C.BLANCO), (x + 16, y + 10))

        # texto (simple por ahora, 2-3 líneas)
        lines = wrap_text(text, self.font_std, w - 32)[:3]
        for i, line in enumerate(lines):
            surf.blit(self.font_std.render(line, True, C.BLANCO), (x + 16, y + 45 + i * 26))


    # -----------------------
    # Render principal
    # -----------------------
    def render(self, surf, state: dict):
        estado = state.get("estado_juego", "MENU_PRINCIPAL")

        if estado == "MENU_PRINCIPAL":
            self.draw_main_menu(surf)
            return
        if estado == "MENU_CONTROLES":
            self.draw_controls_menu(surf)
            return
        if estado == "GAME_OVER":
            self.draw_end_screen(surf, victory=False)
            return
        if estado == "VICTORIA":
            self.draw_end_screen(surf, victory=True)
            return

        # juego
        surf.fill(C.NEGRO)

        grid = state["mapa"]
        thrones = state.get("thrones")
        items_suelo = state.get("items_suelo", {})
        unidades_vivas = state.get("unidades_vivas", [])

        cursor_x, cursor_y = state.get("cursor", (0, 0))
        sel_unidad = state.get("sel_unidad")
        casillas_mov = state.get("casillas_mov", [])
        sel_skill = state.get("sel_skill")
        targets = state.get("targets", [])

        timer_transicion = state.get("timer_transicion", 0)
        texto_transicion = state.get("texto_transicion", "")
        color_transicion = state.get("color_transicion", C.BLANCO)

        # mapa + extras
        self.draw_map(surf, grid)
        self.draw_thrones(surf, thrones)
        self.draw_items(surf, items_suelo)
        
        # rango mov
        if estado == "SELECCIONADO":
            self.draw_move_range(surf, casillas_mov)

        # targets overlay
        if "OBJETIVO" in estado or "TARGET" in estado:
            is_heal = bool(sel_skill and getattr(sel_skill, "tipo_efecto", "") == "curar")
            self.draw_target_overlay(surf, targets, is_heal=is_heal)

        # unidades
        for u in unidades_vivas:
            u.dibujar(surf, self.font_mini)

        # cursor
        self.draw_cursor(surf, cursor_x, cursor_y, selected_mode=("SELECCION" in estado))

        # panel hover
        u_hover = next((u for u in unidades_vivas if u.x == cursor_x and u.y == cursor_y), None)
        if u_hover and estado not in ["MENU_ACCION", "MENU_INVENTARIO", "MENU_SKILLS"]:
            self.draw_unit_panel(surf, u_hover)

        # menus
        if estado == "MENU_ACCION":
            self.draw_action_menu(surf, sel_unidad, thrones=thrones)
        elif estado == "MENU_INVENTARIO":
            self.draw_inventory_menu(surf, sel_unidad)
        elif estado == "MENU_SKILLS":
            self.draw_skills_menu(surf, sel_unidad)

        # fx
        fx = state.get("fx_manager")
        if fx:
            fx.draw(surf)

        # banner turno
        self.draw_turn_banner(surf, texto_transicion, color_transicion, timer_transicion)

        #texto de dialogo
        payload = state.get("battle_dialogue")
        self.draw_battle_dialogue(surf, payload)


print("END ui.py reached")
print("UIRenderer in globals?:", "UIRenderer" in globals())
print("UI globals:", [k for k in globals().keys() if "UI" in k or "Render" in k])
