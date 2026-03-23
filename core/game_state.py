# core/game_state.py
# -------------------------------------------------
# Cerebro del juego. Orquesta todos los sistemas.
# Nuevas funcionalidades:
#   - Battle Preview antes de confirmar ataque
#   - Log de combate con historial
#   - Sistema de efectos de estado integrado
#   - Menú de pausa
#   - Efectos de terreno en combate

import pygame
import constants as C

from systems.map_data      import (pick_random_map, pick_next_map,
                                    pick_enemies_for_difficulty, get_difficulty_tier)
from systems.items         import make_item
from systems.units         import make_unit
from systems.dialogue_system import DialogueSystem
from core.pathfinding      import obtener_movimientos_validos, get_terrain_esquive
from core.combat           import (resolver_combate, obtener_enemigos_en_rango,
                                   calcular_preview)
from ui.fx                 import FXManager


GRILLA_ANCHO = C.GRILLA_ANCHO
GRILLA_ALTO  = C.GRILLA_ALTO


class GameState:
    def __init__(self, modo_juego="PVP", audio=None):
        self.modo_juego = modo_juego
        self.audio      = audio       # AudioLoader (opcional)

        self.fx       = FXManager()
        self.dialogue = DialogueSystem()

        # Progresión de mapas
        self.map_number    = 0        # sube 1 por cada victoria
        self.last_map_name = ""       # evita repetir el mismo mapa

        self.estado_juego = "MENU_PRINCIPAL"
        if self.audio:
            self.audio.play_bgm("menu.mp3")

        self.FASES   = ["aliado", "enemigo"]
        self.idx_fase = 0

        self.cursor_x = 5
        self.cursor_y = 5

        self.sel_unidad   = None
        self.sel_skill    = None
        self.casillas_mov = []
        self.pos_orig     = (0, 0)
        self.targets      = []

        self.timer_transicion  = 0
        self.texto_transicion  = ""
        self.color_transicion  = C.BLANCO

        # Preview de combate (battle forecast)
        self.battle_preview = None

        # Log de combate
        self._combat_log: list = []

        # Datos de mapa
        self.map_def    = None
        self.MAPA_DATA  = None
        self.thrones    = None
        self.ITEMS_SUELO = {}
        self.unidades   = []

    # ===================================================
    # Propiedades
    # ===================================================
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

    def _log(self, msg: str):
        """Agrega línea al log de combate."""
        self._combat_log.append(f"> {msg}")
        if len(self._combat_log) > 8:
            self._combat_log.pop(0)

    # ===================================================
    # Inicio de partida
    # ===================================================
    def start_new_game(self):
        """Reinicia desde cero (mapa 1, dificultad fácil)."""
        self.map_number    = 0
        self.last_map_name = ""
        self._load_map(pick_random_map())

    def advance_to_next_map(self):
        """Progresa al siguiente mapa con dificultad creciente."""
        self.map_number   += 1
        next_map           = pick_next_map(self.map_number, self.last_map_name)
        self._load_map(next_map)

    def _load_map(self, map_def):
        self.fx.clear()
        self._combat_log.clear()
        self.battle_preview = None

        self.map_def        = map_def
        self.last_map_name  = map_def.name
        self.MAPA_DATA      = map_def.grid
        self.thrones        = map_def.thrones

        self.ITEMS_SUELO = {
            pos: make_item(item_id)
            for pos, item_id in map_def.items_spawn.items()
        }

        # Aliados fijos
        self.unidades = [
            make_unit(sp.unit_id, sp.pos[0], sp.pos[1], sp.bando,
                      add_floating_text=self.fx.add_text)
            for sp in map_def.spawns
        ]

        # Enemigos aleatorios según dificultad
        tier = get_difficulty_tier(self.map_number)
        enemy_assignments = pick_enemies_for_difficulty(
            tier, list(map_def.enemy_positions), self.map_number)
        for unit_id, pos in enemy_assignments:
            self.unidades.append(
                make_unit(unit_id, pos[0], pos[1], "enemigo",
                          add_floating_text=self.fx.add_text)
            )

        self.idx_fase   = 0
        self.sel_unidad = None
        self.sel_skill  = None
        self.casillas_mov = []
        self.targets      = []

        self.cursor_x, self.cursor_y = 5, 5
        self.clamp_cursor()

        self.estado_juego = "NEUTRAL"

        self.timer_transicion = 90
        self.texto_transicion = f"TURNO {self.fase_actual.upper()}"
        self.color_transicion = C.AZUL_MP if self.fase_actual == "aliado" else C.ROJO_HP

        for u in self.unidades:
            if u.bando == self.fase_actual:
                u.resetear_turno()

        if self.audio:
            self.audio.play_bgm("exploration.mp3")

        tier_label = tier.upper()
        self._log(f"--- {map_def.name} [Mapa {self.map_number+1}] [{tier_label}] ---")

    # ===================================================
    # Cambio de turno
    # ===================================================
    def end_turn(self):
        self.idx_fase = (self.idx_fase + 1) % len(self.FASES)

        self.timer_transicion = 90
        self.texto_transicion = f"TURNO {self.fase_actual.upper()}"
        self.color_transicion = C.AZUL_MP if self.fase_actual == "aliado" else C.ROJO_HP

        for u in self.unidades:
            if u.bando == self.fase_actual:
                u.resetear_turno()
                u.procesar_turno_awakening()
                u.procesar_efectos_turno()

        self.sel_unidad = None
        self.sel_skill  = None
        self.casillas_mov = []
        self.targets      = []
        self.battle_preview = None
        self.estado_juego = "NEUTRAL"

    # ===================================================
    # Condiciones de victoria
    # ===================================================
    def check_end_conditions(self):
        if self.estado_juego in ["MENU_PRINCIPAL","MENU_CONTROLES","GAME_OVER","VICTORIA","PAUSA"]:
            return
        vivos    = self.unidades_vivas
        aliados  = [u for u in vivos if u.bando == "aliado"]
        enemigos = [u for u in vivos if u.bando == "enemigo"]
        if not aliados:
            self.estado_juego = "GAME_OVER"
            if self.audio:
                self.audio.play_bgm("game_over.mp3")
        elif not enemigos:
            self.estado_juego = "VICTORIA"
            if self.audio:
                self.audio.play_bgm("victory.mp3")

    # ===================================================
    # Eventos
    # ===================================================
    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if self.timer_transicion > 0:
            return

        k = event.key

        # --- MENÚ PRINCIPAL ---
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

        # --- MENÚ CONTROLES ---
        if self.estado_juego == "MENU_CONTROLES":
            if k == pygame.K_ESCAPE:
                self.estado_juego = "MENU_PRINCIPAL"
            return

        # --- FIN DE PARTIDA ---
        if self.estado_juego == "VICTORIA":
            if k == pygame.K_r:
                self.advance_to_next_map()
            elif k == pygame.K_ESCAPE:
                self.estado_juego = "MENU_PRINCIPAL"
                if self.audio:
                    self.audio.play_bgm("menu.mp3")
            return
        if self.estado_juego == "GAME_OVER":
            if k == pygame.K_r:
                self.start_new_game()
            elif k == pygame.K_ESCAPE:
                self.estado_juego = "MENU_PRINCIPAL"
                if self.audio:
                    self.audio.play_bgm("menu.mp3")
            return

        # --- PAUSA ---
        if self.estado_juego == "PAUSA":
            if k in [pygame.K_ESCAPE, pygame.K_p]:
                self.estado_juego = "NEUTRAL"
                if self.audio:
                    self.audio.play_bgm("exploration.mp3")
            elif k == pygame.K_r:
                self.start_new_game()
            elif k == pygame.K_m:
                self.estado_juego = "MENU_PRINCIPAL"
                if self.audio:
                    self.audio.play_bgm("menu.mp3")
            return

        # --- TURNO IA ---
        if self.es_turno_ia():
            return

        # Pausa con P
        if k == pygame.K_p:
            self.estado_juego = "PAUSA"
            return

        # Escape
        if k == pygame.K_ESCAPE:
            self._handle_escape()
            return

        # Finalizar turno
        if k == pygame.K_f and self.estado_juego == "NEUTRAL":
            self.end_turn()
            return

        # Movimiento de cursor (fuera de menús)
        if self.estado_juego not in ["MENU_ACCION","MENU_INVENTARIO","MENU_SKILLS"]:
            self._handle_cursor_move(k)

        # Confirmar
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

    # ===================================================
    # Escape
    # ===================================================
    def _handle_escape(self):
        if self.estado_juego == "SELECCION_SKILL_TARGET":
            self.estado_juego   = "MENU_SKILLS"
            self.targets        = []
            self.battle_preview = None
            return

        if self.estado_juego in ["MENU_SKILLS","MENU_INVENTARIO","SELECCION_OBJETIVO"]:
            self.estado_juego   = "MENU_ACCION"
            self.targets        = []
            self.battle_preview = None
            return

        if self.estado_juego == "MENU_ACCION":
            if self.sel_unidad:
                self.sel_unidad.x, self.sel_unidad.y = self.pos_orig
            self.sel_unidad     = None
            self.sel_skill      = None
            self.casillas_mov   = []
            self.targets        = []
            self.battle_preview = None
            self.estado_juego   = "NEUTRAL"
            return

        if self.estado_juego == "SELECCIONADO":
            self.sel_unidad   = None
            self.casillas_mov = []
            self.targets      = []
            self.estado_juego = "NEUTRAL"
            return

    # ===================================================
    # Cursor
    # ===================================================
    def _handle_cursor_move(self, key):
        dx, dy = 0, 0
        if key == pygame.K_LEFT:   dx = -1
        elif key == pygame.K_RIGHT: dx =  1
        elif key == pygame.K_UP:    dy = -1
        elif key == pygame.K_DOWN:  dy =  1

        self.cursor_x += dx
        self.cursor_y += dy
        self.clamp_cursor()

        # Actualizar battle preview si está en selección de objetivo
        if self.estado_juego == "SELECCION_OBJETIVO" and self.sel_unidad:
            self._update_battle_preview()

    def _update_battle_preview(self):
        cx, cy = self.cursor_x, self.cursor_y
        t = next((e for e in self.targets if e.x == cx and e.y == cy), None)
        if t:
            esq_def = get_terrain_esquive(self.MAPA_DATA, t.x, t.y)
            esq_atq = get_terrain_esquive(self.MAPA_DATA, self.sel_unidad.x, self.sel_unidad.y)
            self.battle_preview = calcular_preview(
                self.sel_unidad, t, esq_def, esq_atq)
        else:
            self.battle_preview = None

    # ===================================================
    # Confirmar
    # ===================================================
    def _handle_confirm(self):
        cx, cy = self.cursor_x, self.cursor_y

        # NEUTRAL → seleccionar unidad
        if self.estado_juego == "NEUTRAL":
            for u in self.unidades:
                if (u.x, u.y) == (cx, cy) and u.bando == self.fase_actual \
                        and not u.ha_actuado and u.esta_viva():
                    self.sel_unidad   = u
                    self.pos_orig     = (u.x, u.y)
                    self.casillas_mov = obtener_movimientos_validos(u, self.MAPA_DATA, self.unidades)
                    self.casillas_mov.append((u.x, u.y))
                    self.estado_juego = "SELECCIONADO"
                    return

        # SELECCIONADO → confirmar movimiento
        if self.estado_juego == "SELECCIONADO":
            if (cx, cy) in self.casillas_mov:
                bloqueado = any(
                    u.x == cx and u.y == cy and u != self.sel_unidad and u.esta_viva()
                    for u in self.unidades
                )
                if not bloqueado:
                    self.sel_unidad.x, self.sel_unidad.y = cx, cy

                    # Pickup ítem
                    if (cx, cy) in self.ITEMS_SUELO:
                        it = self.ITEMS_SUELO.pop((cx, cy))
                        self.sel_unidad.inventario.append(it)
                        self.fx.add_text(cx * 32, cy * 32, f"¡{it.nombre}!", C.DORADO_COFRE)
                        if it.tipo == "arma" and not self.sel_unidad.arma_equipada:
                            self.sel_unidad.arma_equipada = it

                    self.estado_juego = "MENU_ACCION"
            return

        # SELECCION_OBJETIVO → atacar
        if self.estado_juego == "SELECCION_OBJETIVO":
            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades)
            t    = next((e for e in objs if e.x == cx and e.y == cy), None)
            if t:
                self.dialogue.trigger(self.sel_unidad, "attack", target=t)
                esq_def = get_terrain_esquive(self.MAPA_DATA, t.x, t.y)
                esq_atq = get_terrain_esquive(self.MAPA_DATA, self.sel_unidad.x, self.sel_unidad.y)

                result = resolver_combate(self.sel_unidad, t,
                                          add_fx=self.fx.add_text,
                                          terreno_esquive_def=esq_def,
                                          terreno_esquive_atq=esq_atq)
                self._process_combat_result(self.sel_unidad, t, result)
                self.sel_unidad.ha_actuado = True
                self.sel_unidad   = None
                self.targets      = []
                self.battle_preview = None
                self.estado_juego = "NEUTRAL"
            return

        # SELECCION_SKILL_TARGET → usar habilidad
        if self.estado_juego == "SELECCION_SKILL_TARGET":
            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades, self.sel_skill)
            t    = next((e for e in objs if e.x == cx and e.y == cy), None)
            if t:
                event = "skill"
                if self.sel_skill.tipo_efecto == "curar":
                    event = "heal"
                self.dialogue.trigger(self.sel_unidad, event, skill=self.sel_skill)
                ok = self.sel_unidad.usar_habilidad(self.sel_skill, t)
                if ok:
                    self._log(f"{self.sel_unidad.nombre} usó {self.sel_skill.nombre}")
                    self.sel_unidad.ha_actuado = True
                    self.sel_unidad   = None
                    self.sel_skill    = None
                    self.targets      = []
                    self.battle_preview = None
                    self.estado_juego = "NEUTRAL"
            return

    def _process_combat_result(self, atq, defen, result: dict):
        """Procesa y logea el resultado del combate."""
        self._log(f"{atq.nombre} atacó a {defen.nombre}")
        if result.get("mato_def"):
            self._log(f"{defen.nombre} fue derrotado.")
            self.dialogue.trigger(atq, "kill")
        if result.get("mato_atq"):
            self._log(f"{atq.nombre} fue derrotado en el contraataque.")

    # ===================================================
    # Menú acción
    # ===================================================
    def _handle_action_menu(self, key):
        if not self.sel_unidad:
            self.estado_juego = "NEUTRAL"
            return

        if key == pygame.K_a:  # Atacar
            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades)
            if objs:
                self.targets = objs
                t = objs[0]
                self.cursor_x, self.cursor_y = t.x, t.y
                self.estado_juego = "SELECCION_OBJETIVO"
                self._update_battle_preview()
            else:
                self.fx.add_text(self.sel_unidad.x * 32, self.sel_unidad.y * 32,
                                  "Sin objetivo", C.GRIS_INACTIVO)

        elif key == pygame.K_h:  # Habilidad
            self.estado_juego = "MENU_SKILLS"

        elif key == pygame.K_i:  # Inventario
            self.estado_juego = "MENU_INVENTARIO"

        elif key == pygame.K_e:  # Esperar
            self.sel_unidad.ha_actuado = True
            self._log(f"{self.sel_unidad.nombre} esperó.")
            self.sel_unidad   = None
            self.targets      = []
            self.estado_juego = "NEUTRAL"

        elif key == pygame.K_w:  # Awakening
            self.sel_unidad.activar_awakening()
            if self.sel_unidad.awakened:
                self.dialogue.trigger(self.sel_unidad, "awakening")
                self._log(f"{self.sel_unidad.nombre} activó Awakening.")

        elif key == pygame.K_c:  # Conquistar
            if self.sel_unidad.es_heroe:
                throne = self.thrones.get(self.sel_unidad.bando)
                if throne and (self.sel_unidad.x, self.sel_unidad.y) == throne:
                    self.estado_juego = "VICTORIA"

    # ===================================================
    # Menú skills
    # ===================================================
    def _handle_skills_menu(self, key):
        if not self.sel_unidad:
            self.estado_juego = "NEUTRAL"
            return

        idx = key - 49  # '1' → 0
        if 0 <= idx < len(self.sel_unidad.habilidades):
            sk = self.sel_unidad.habilidades[idx]
            if self.sel_unidad.mp_actual < sk.costo_mp:
                self.fx.add_text(self.sel_unidad.x * 32, self.sel_unidad.y * 32,
                                  "No MP", C.GRIS_INACTIVO)
                return

            objs = obtener_enemigos_en_rango(self.sel_unidad, self.unidades, sk)
            if objs:
                self.sel_skill = sk
                self.targets   = objs
                self.cursor_x, self.cursor_y = objs[0].x, objs[0].y
                self.estado_juego = "SELECCION_SKILL_TARGET"
            else:
                self.fx.add_text(self.sel_unidad.x * 32, self.sel_unidad.y * 32,
                                  "Sin objetivo", C.GRIS_INACTIVO)

    # ===================================================
    # Menú inventario
    # ===================================================
    def _handle_inventory_menu(self, key):
        if not self.sel_unidad:
            self.estado_juego = "NEUTRAL"
            return

        idx = key - 49
        if 0 <= idx < len(self.sel_unidad.inventario):
            it = self.sel_unidad.inventario[idx]
            if it.tipo == "arma":
                self.sel_unidad.equipar_item(idx)
                self._log(f"{self.sel_unidad.nombre} equipó {it.nombre}.")
            else:
                ok = self.sel_unidad.usar_item(idx)
                if ok:
                    self._log(f"{self.sel_unidad.nombre} usó {it.nombre}.")
                    self.sel_unidad.ha_actuado = True
                    self.sel_unidad   = None
                    self.targets      = []
                    self.estado_juego = "NEUTRAL"

    # ===================================================
    # Update
    # ===================================================
    def update(self, dt, ai_controller=None):
        self.fx.update()

        if self.timer_transicion > 0:
            self.timer_transicion = max(0, self.timer_transicion - 1)

        self.check_end_conditions()

        if self.estado_juego in ["MENU_PRINCIPAL","MENU_CONTROLES","GAME_OVER","VICTORIA","PAUSA"]:
            return

        if self.es_turno_ia() and ai_controller and self.timer_transicion == 0:
            fin = ai_controller.ejecutar_turno(
                self.MAPA_DATA, self.unidades, self.ITEMS_SUELO,
                "enemigo", add_floating_text=self.fx.add_text
            )
            if fin:
                self.end_turn()

        self.dialogue.update(dt)

    # ===================================================
    # Estado para el renderer
    # ===================================================
    def to_render_state(self) -> dict:
        return {
            "estado_juego":    self.estado_juego,
            "modo_juego":      self.modo_juego,
            "fase_actual":     self.fase_actual,
            "map_number":      self.map_number,
            "difficulty_tier": get_difficulty_tier(self.map_number),

            "mapa":            self.MAPA_DATA,
            "map_def":         self.map_def,
            "thrones":         self.thrones,

            "items_suelo":     self.ITEMS_SUELO,
            "unidades_vivas":  self.unidades_vivas,

            "cursor":          (self.cursor_x, self.cursor_y),
            "sel_unidad":      self.sel_unidad,
            "casillas_mov":    self.casillas_mov,
            "sel_skill":       self.sel_skill,
            "targets":         self.targets,

            "timer_transicion": self.timer_transicion,
            "texto_transicion": self.texto_transicion,
            "color_transicion": self.color_transicion,

            "fx_manager":      self.fx,
            "battle_preview":  self.battle_preview,
            "combat_log":      self._combat_log[-6:],
            "battle_dialogue": self.dialogue.get_render_payload(),
        }
