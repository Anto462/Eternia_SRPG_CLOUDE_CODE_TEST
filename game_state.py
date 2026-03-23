# game_state.py
# -------------------------------------------------
# GameState = el cerebro del juego.
# main.py no debería tener lógica, solo:
# - pasar eventos a state.handle_event()
# - llamar state.update()
# - pedirle a ui.render(...) que dibuje state
#
# Este módulo mantiene el comportamiento de tu prototipo, pero ordenado.

import pygame

import constants as C

GRILLA_ANCHO = C.GRILLA_ANCHO
GRILLA_ALTO = C.GRILLA_ALTO
BLANCO = C.BLANCO
GRIS_INACTIVO = C.GRIS_INACTIVO
DORADO_COFRE = C.DORADO_COFRE
PURPURA_TRONO = C.PURPURA_TRONO
AZUL_MP = C.AZUL_MP
ROJO_HP = C.ROJO_HP


from map_data import pick_random_map
from items import make_item
from units import make_unit
from pathfinding import obtener_movimientos_validos
from combat import resolver_combate, obtener_enemigos_en_rango
from fx import FXManager
from dialogue_system import DialogueSystem


class GameState:
    def __init__(self, modo_juego="PVP"):
        # modo: "PVP" o "PVE"
        self.modo_juego = modo_juego

        # FX
        self.fx = FXManager()

        # Estado principal
        self.estado_juego = "MENU_PRINCIPAL"  # MENU_PRINCIPAL, MENU_CONTROLES, NEUTRAL, etc.

        # Turnos
        self.FASES = ["aliado", "enemigo"]
        self.idx_fase = 0

        # Cursor
        self.cursor_x = 5
        self.cursor_y = 5

        # Selección
        self.sel_unidad = None
        self.sel_skill = None
        self.casillas_mov = []
        self.pos_orig = (0, 0)

        # Transición
        self.timer_transicion = 0
        self.texto_transicion = ""
        self.color_transicion = BLANCO

        # Targets (para UI overlay)
        self.targets = []

        # Cargar primera partida “en memoria”
        self.map_def = None
        self.MAPA_DATA = None
        self.thrones = None
        self.ITEMS_SUELO = {}
        self.unidades = []

        self.dialogue = DialogueSystem()

        # Nota: no arrancamos la partida automáticamente en menú.
        # Cuando el usuario elija modo, pasamos a NEUTRAL y reiniciamos.

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    @property
    def fase_actual(self):
        return self.FASES[self.idx_fase]

    @property
    def unidades_vivas(self):
        return [u for u in self.unidades if u.esta_viva()]

    def clamp_cursor(self):
        self.cursor_x = max(0, min(self.cursor_x, GRILLA_ANCHO - 1))
        self.cursor_y = max(0, min(self.cursor_y, GRILLA_ALTO - 1))

    def es_turno_ia(self):
        return self.modo_juego == "PVE" and self.fase_actual == "enemigo"

    # -------------------------------------------------
    # Construcción / reinicio de partida
    # -------------------------------------------------
    def start_new_game(self):
        """
        Arranca partida nueva:
        - elige mapa random
        - crea items suelo
        - crea unidades según spawns
        """
        self.fx.clear()

        self.map_def = pick_random_map()
        self.MAPA_DATA = self.map_def.grid
        self.thrones = self.map_def.thrones

        # suelo
        self.ITEMS_SUELO = {pos: make_item(item_id) for pos, item_id in self.map_def.items_spawn.items()}

        # unidades
        self.unidades = []
        for sp in self.map_def.spawns:
            x, y = sp.pos
            self.unidades.append(make_unit(sp.unit_id, x, y, sp.bando, add_floating_text=self.fx.add_text))

        # reset turnos
        self.idx_fase = 0

        # reset selección
        self.sel_unidad = None
        self.sel_skill = None
        self.casillas_mov = []
        self.targets = []

        # cursor a un punto seguro
        self.cursor_x, self.cursor_y = 5, 5
        self.clamp_cursor()

        # estado de juego en neutral
        self.estado_juego = "NEUTRAL"

        # banner inicial
        self.timer_transicion = 60
        self.texto_transicion = f"TURNO {self.fase_actual.upper()}"
        self.color_transicion = AZUL_MP if self.fase_actual == "aliado" else ROJO_HP

        # Asegurar que solo el bando que juega se resetee
        for u in self.unidades:
            if u.bando == self.fase_actual:
                u.resetear_turno()

    # -------------------------------------------------
    # Cambio de turno
    # -------------------------------------------------
    def end_turn(self):
        """
        Finaliza turno manualmente (F):
        - cambia fase
        - resetea ha_actuado del bando nuevo
        - procesa awakening tick
        """
        self.idx_fase = (self.idx_fase + 1) % len(self.FASES)

        self.timer_transicion = 90
        self.texto_transicion = f"TURNO {self.fase_actual.upper()}"
        self.color_transicion = AZUL_MP if self.fase_actual == "aliado" else ROJO_HP

        for u in self.unidades:
            if u.bando == self.fase_actual:
                u.resetear_turno()
                u.procesar_turno_awakening()

        # limpiar selección
        self.sel_unidad = None
        self.sel_skill = None
        self.casillas_mov = []
        self.targets = []
        self.estado_juego = "NEUTRAL"

    # -------------------------------------------------
    # Reglas de victoria/derrota
    # -------------------------------------------------
    def check_end_conditions(self):
        if self.estado_juego in ["MENU_PRINCIPAL", "MENU_CONTROLES", "GAME_OVER", "VICTORIA"]:
            return

        vivos = self.unidades_vivas
        aliados = [u for u in vivos if u.bando == "aliado"]
        enemigos = [u for u in vivos if u.bando == "enemigo"]

        if not aliados:
            self.estado_juego = "GAME_OVER"
        elif not enemigos:
            self.estado_juego = "VICTORIA"

    # -------------------------------------------------
    # Entrada (eventos)
    # -------------------------------------------------
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        # Si hay transición, bloqueamos input como tu base
        if self.timer_transicion > 0:
            return

        k = event.key


        # --- DEBUG / TEST DIALOGUE ---
        if k == pygame.K_t:
            # si no hay sel_unidad, probamos con la unidad bajo cursor (más cómodo)
            u = self.sel_unidad
            if not u:
                u = next((x for x in self.unidades if x.esta_viva() and (x.x, x.y) == (self.cursor_x, self.cursor_y)), None)
                if u:
                    self.dialogue.trigger(u, "attack")
                    print("Dialogue triggered for:", getattr(u, "unit_id", None), u.nombre)
                else:
                    print("No unit to trigger dialogue")
                return
        # ------------------------
        # MENÚ PRINCIPAL
        # ------------------------
        if self.estado_juego == "MENU_PRINCIPAL":
            if k == pygame.K_1:
                self.modo_juego = "PVP"
                self.start_new_game()
            elif k == pygame.K_2:
                self.modo_juego = "PVE"
                self.start_new_game()
            elif k == pygame.K_3:
                self.estado_juego = "MENU_CONTROLES"
            return

        # ------------------------
        # MENÚ CONTROLES
        # ------------------------
        if self.estado_juego == "MENU_CONTROLES":
            if k == pygame.K_ESCAPE:
                self.estado_juego = "MENU_PRINCIPAL"
            return

        # ------------------------
        # FIN DE PARTIDA
        # ------------------------
        if self.estado_juego in ["GAME_OVER", "VICTORIA"]:
            if k == pygame.K_r:
                self.start_new_game()
            elif k == pygame.K_ESCAPE:
                self.estado_juego = "MENU_PRINCIPAL"
            return

        # ------------------------
        # JUEGO (si es turno IA, ignoramos input)
        # ------------------------
        if self.es_turno_ia():
            return

        # Escape handling (volver atrás)
        if k == pygame.K_ESCAPE:
            self._handle_escape()
            return

        # Finalizar turno (F)
        if k == pygame.K_f and self.estado_juego == "NEUTRAL":
            self.end_turn()
            return

        # Cursor movement (si no estamos en menús)
        if self.estado_juego not in ["MENU_ACCION", "MENU_INVENTARIO", "MENU_SKILLS"]:
            self._handle_cursor_move(k)

        # Confirm (Enter/Space)
        if k in [pygame.K_RETURN, pygame.K_SPACE]:
            self._handle_confirm()
            return

        # Menú acción
        if self.estado_juego == "MENU_ACCION":
            self._handle_action_menu(k)
            return

        # Menú skills
        if self.estado_juego == "MENU_SKILLS":
            self._handle_skills_menu(k)
            return

        # Menú inventario
        if self.estado_juego == "MENU_INVENTARIO":
            self._handle_inventory_menu(k)
            return


    # -------------------------------------------------
    # Escape states
    # -------------------------------------------------
    def _handle_escape(self):
        if self.estado_juego == "SELECCION_SKILL_TARGET":
            self.estado_juego = "MENU_SKILLS"
            self.targets = []
            return

        if self.estado_juego in ["MENU_SKILLS", "MENU_INVENTARIO", "SELECCION_OBJETIVO"]:
            self.estado_juego = "MENU_ACCION"
            self.targets = []
            return

        if self.estado_juego == "MENU_ACCION":
            # revertir movimiento si cancelas desde menú acción
            if self.sel_unidad:
                self.sel_unidad.x, self.sel_unidad.y = self.pos_orig
            self.sel_unidad = None
            self.sel_skill = None
            self.casillas_mov = []
            self.targets = []
            self.estado_juego = "NEUTRAL"
            return

        if self.estado_juego == "SELECCIONADO":
            self.sel_unidad = None
            self.casillas_mov = []
            self.targets = []
            self.estado_juego = "NEUTRAL"
            return

    # -------------------------------------------------
    # Cursor move
    # -------------------------------------------------
    def _handle_cursor_move(self, key):
        dx, dy = 0, 0
        if key == pygame.K_LEFT:
            dx = -1
        elif key == pygame.K_RIGHT:
            dx = 1
        elif key == pygame.K_UP:
            dy = -1
        elif key == pygame.K_DOWN:
            dy = 1

        self.cursor_x += dx
        self.cursor_y += dy
        self.clamp_cursor()

    # -------------------------------------------------
    # Confirm
    # -------------------------------------------------
    def _handle_confirm(self):
        cx, cy = self.cursor_x, self.cursor_y

        # NEUTRAL: seleccionar unidad del bando
        if self.estado_juego == "NEUTRAL":
            for u in self.unidades:
                if (u.x, u.y) == (cx, cy) and u.bando == self.fase_actual and not u.ha_actuado and u.esta_viva():
                    self.sel_unidad = u
                    self.pos_orig = (u.x, u.y)
                    self.estado_juego = "SELECCIONADO"

                    self.casillas_mov = obtener_movimientos_validos(u, self.MAPA_DATA, self.unidades)
                    self.casillas_mov.append((u.x, u.y))
                    return

        # SELECCIONADO: confirmar movimiento
        if self.estado_juego == "SELECCIONADO":
            if (cx, cy) in self.casillas_mov:
                # no permitir moverte encima de otra unidad
                if not any(u.x == cx and u.y == cy and u != self.sel_unidad and u.esta_viva() for u in self.unidades):
                    self.sel_unidad.x, self.sel_unidad.y = cx, cy

                    # pickup item si hay
                    if (cx, cy) in self.ITEMS_SUELO:
                        it = self.ITEMS_SUELO.pop((cx, cy))
                        self.sel_unidad.inventario.append(it)
                        self.fx.add_text(cx * 32, cy * 32, f"Gano: {it.nombre}", DORADO_COFRE)

                        # auto-equip si no tiene arma
                        if it.tipo == "arma" and not self.sel_unidad.arma_equipada:
                            self.sel_unidad.arma_equipada = it

                    self.estado_juego = "MENU_ACCION"
            return

        # SELECCION_OBJETIVO: atacar normal
        if self.estado_juego == "SELECCION_OBJETIVO":
            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades)
            t = next((e for e in objs if e.x == cx and e.y == cy), None)
            if t:
                self.dialogue.trigger(self.sel_unidad, "attack", target=t)
                resolver_combate(self.sel_unidad, t, add_floating_text=self.fx.add_text)
                self.sel_unidad.ha_actuado = True
                self.sel_unidad = None
                self.targets = []
                self.estado_juego = "NEUTRAL"
            return

        # SELECCION_SKILL_TARGET: usar skill
        if self.estado_juego == "SELECCION_SKILL_TARGET":
            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades, self.sel_skill)
            t = next((e for e in objs if e.x == cx and e.y == cy), None)
            if t:
                self.dialogue.trigger(self.sel_unidad, "skill", target=t, skill=self.sel_skill)
                ok = self.sel_unidad.usar_habilidad(self.sel_skill, t)
                if ok:
                    self.sel_unidad.ha_actuado = True
                    self.sel_unidad = None
                    self.sel_skill = None
                    self.targets = []
                    self.estado_juego = "NEUTRAL"
            return

    # -------------------------------------------------
    # Menú acción
    # -------------------------------------------------
    def _handle_action_menu(self, key):
        if not self.sel_unidad:
            self.estado_juego = "NEUTRAL"
            return

        # A: atacar
        if key == pygame.K_a:
            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades)
            if objs:
                self.targets = objs
                t = objs[0]
                self.cursor_x, self.cursor_y = t.x, t.y
                self.estado_juego = "SELECCION_OBJETIVO"
            else:
                self.fx.add_text(self.sel_unidad.x * 32, self.sel_unidad.y * 32, "Sin Objetivo", GRIS_INACTIVO)

        # H: skills
        elif key == pygame.K_h:
            self.estado_juego = "MENU_SKILLS"

        # I: inventario
        elif key == pygame.K_i:
            self.estado_juego = "MENU_INVENTARIO"

        # E: esperar
        elif key == pygame.K_e:
            self.sel_unidad.ha_actuado = True
            self.sel_unidad = None
            self.targets = []
            self.estado_juego = "NEUTRAL"

        # W: awakening
        elif key == pygame.K_w:
            self.sel_unidad.activar_awakening()

        # C: conquistar (solo héroe y en trono de su bando)
        elif key == pygame.K_c:
            if self.sel_unidad.es_heroe:
                throne = self.thrones.get(self.sel_unidad.bando)
                if throne and (self.sel_unidad.x, self.sel_unidad.y) == throne:
                    self.estado_juego = "VICTORIA"

    # -------------------------------------------------
    # Menú skills
    # -------------------------------------------------
    def _handle_skills_menu(self, key):
        if not self.sel_unidad:
            self.estado_juego = "NEUTRAL"
            return

        idx = key - 49  # '1' -> 0
        if 0 <= idx < len(self.sel_unidad.habilidades):
            sk = self.sel_unidad.habilidades[idx]

            if self.sel_unidad.mp_actual < sk.costo_mp:
                self.fx.add_text(self.sel_unidad.x * 32, self.sel_unidad.y * 32, "No MP", GRIS_INACTIVO)
                return

            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades, sk)
            if objs:
                self.sel_skill = sk
                self.targets = objs
                t = objs[0]
                self.cursor_x, self.cursor_y = t.x, t.y
                self.estado_juego = "SELECCION_SKILL_TARGET"
            else:
                self.fx.add_text(self.sel_unidad.x * 32, self.sel_unidad.y * 32, "Sin Objetivo", GRIS_INACTIVO)

    # -------------------------------------------------
    # Menú inventario
    # -------------------------------------------------
    def _handle_inventory_menu(self, key):
        if not self.sel_unidad:
            self.estado_juego = "NEUTRAL"
            return

        idx = key - 49
        if 0 <= idx < len(self.sel_unidad.inventario):
            it = self.sel_unidad.inventario[idx]

            # arma -> equipar
            if it.tipo == "arma":
                self.sel_unidad.equipar_item(idx)

            # consumible -> usar y termina turno
            else:
                ok = self.sel_unidad.usar_item(idx)
                if ok:
                    self.sel_unidad.ha_actuado = True
                    self.sel_unidad = None
                    self.targets = []
                    self.estado_juego = "NEUTRAL"

    # -------------------------------------------------
    # Update
    # -------------------------------------------------
    def update(self, dt, ai_controller=None):
        """
        dt: delta time (segundos). Por ahora solo lo dejamos por si luego animas cosas.
        ai_controller: IAController si estás en PVE.
        """
        # actualizar FX siempre
        self.fx.update()

        # transiciones
        if self.timer_transicion > 0:
            self.timer_transicion -= 1
            if self.timer_transicion < 0:
                self.timer_transicion = 0

        # chequeo fin de partida
        self.check_end_conditions()

        # si no estamos jugando, no hacemos lógica
        if self.estado_juego in ["MENU_PRINCIPAL", "MENU_CONTROLES", "GAME_OVER", "VICTORIA"]:
            return

        # IA (solo cuando toca)
        if self.es_turno_ia() and ai_controller and self.timer_transicion == 0:
            fin = ai_controller.ejecutar_turno(self.MAPA_DATA,self.unidades,self.ITEMS_SUELO,"enemigo",add_floating_text=self.fx.add_text)
            if fin:
                self.end_turn()
        
        self.dialogue.update(dt)

    # -------------------------------------------------
    # Helper para UI: construir el state dict que ui.render necesita
    # -------------------------------------------------
    def to_render_state(self):
        """
        Esto lo usas para pasarle al ui.render(screen, state).
        """
        return {
            "estado_juego": self.estado_juego,
            "modo_juego": self.modo_juego,
            "fase_actual": self.fase_actual,

            "mapa": self.MAPA_DATA,
            "map_def": self.map_def,
            "thrones": self.thrones,

            "items_suelo": self.ITEMS_SUELO,
            "unidades_vivas": self.unidades_vivas,

            "cursor": (self.cursor_x, self.cursor_y),
            "sel_unidad": self.sel_unidad,
            "casillas_mov": self.casillas_mov,
            "sel_skill": self.sel_skill,

            "timer_transicion": self.timer_transicion,
            "texto_transicion": self.texto_transicion,
            "color_transicion": self.color_transicion,

            "fx_manager": self.fx,
            "targets": self.targets,

            "battle_dialogue": self.dialogue.get_render_payload(),

        }
