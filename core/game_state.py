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
                                    pick_enemies_for_difficulty, get_difficulty_tier,
                                    MAPS)
from systems.boss_map_data import pick_boss_map
from systems.items         import make_item, make_skill
from systems.units         import make_unit
from systems.dialogue_system import DialogueSystem
from core.pathfinding      import obtener_movimientos_validos, get_terrain_esquive
from core.combat           import (resolver_combate, obtener_enemigos_en_rango,
                                   calcular_preview)
from ui.fx                 import FXManager
from loaders.sprite_loader import get_fx_frames
from systems.score_system  import ScoreTracker, load_scores
from systems.rogue_system  import (RogueRunState, pick_relic_choices,
                                   get_hero_pool, MIN_HEROES, MAX_HEROES,
                                   ALL_RELICS)
from systems.save_system   import save_run, load_save, delete_save, has_save


GRILLA_ANCHO = C.GRILLA_ANCHO
GRILLA_ALTO  = C.GRILLA_ALTO

MAX_MAPS = 10   # Duración total de una run roguelike

# IDs de todos los jefes disponibles en el pool
_ALL_BOSS_IDS = [
    "GOBLIN_OVERLORD", "IRON_MAMMOTH", "SHADOW_MAGE", "DRAGON_EMPEROR",
    "BONE_EMPEROR", "ORC_WARLORD", "FROST_QUEEN", "INFERNAL_DEMON",
    "SEA_COLOSSUS", "VOID_HERALD",
]


def _is_boss_slot(map_number: int) -> bool:
    """Devuelve True si map_number corresponde a un mapa de jefe (índices 2, 5, 8)."""
    return map_number % 3 == 2


class GameState:
    def __init__(self, modo_juego="PVP", audio=None):
        self.modo_juego = modo_juego
        self.audio      = audio       # AudioLoader (opcional)

        self.fx       = FXManager()
        self.dialogue = DialogueSystem()

        # Progresión de mapas
        self.map_number    = 0        # sube 1 por cada victoria
        self.last_map_name = ""       # evita repetir el mismo mapa

        # Puntuación
        self.score = ScoreTracker()

        # Roguelike
        self.rogue            = RogueRunState()
        self.hero_pool        = get_hero_pool()
        self._hero_cursor     = 0           # índice en hero_pool
        self._selected_heroes: list = []    # HeroOption elegidos
        self.relic_choices: list    = []    # 3 reliquias a mostrar
        self._relic_cursor    = 0
        self._show_acquired_relics: bool = False  # toggle panel de items adquiridos

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
    # ===================================================
    # Sistema de guardado
    # ===================================================
    def continue_saved_run(self):
        """Restaura una run guardada desde data/save.json."""
        data = load_save()
        if not data:
            self._open_hero_selection()
            return

        self.map_number    = data.get("map_number", 0)
        self.last_map_name = data.get("last_map_name", "")
        self.modo_juego    = data.get("modo_juego", self.modo_juego)

        # Restaurar puntuación
        sc = data.get("score", {})
        self.score.total_score   = sc.get("total", 0)
        self.score.kills         = sc.get("kills", 0)
        self.score.maps_cleared  = sc.get("maps_cleared", 0)

        # Restaurar roguelike
        rogue_data = data.get("rogue", {})
        self.rogue.selected_heroes  = rogue_data.get("selected_heroes", [])
        self.rogue.score_multiplier = rogue_data.get("score_multiplier", 1.0)
        relic_ids = [r["relic_id"] for r in rogue_data.get("acquired_relics", [])]
        self.rogue.acquired_relics  = [r for r in ALL_RELICS if r.relic_id in relic_ids]

        # Cargar el mapa actual
        mapa = next((m for m in MAPS if m.name == self.last_map_name), None)
        if mapa is None:
            mapa = pick_random_map()
        self._load_map(mapa)

        # Restaurar HP/MP de aliados según save
        saved_allies = {u["unit_id"]: u for u in data.get("aliados", [])}
        for u in self.unidades:
            if u.bando == "aliado":
                uid = getattr(u, "unit_id", u.nombre)
                if uid in saved_allies:
                    s = saved_allies[uid]
                    u.hp_actual  = min(s.get("hp_actual", u.hp_actual), u.max_hp)
                    u.mp_actual  = min(s.get("mp_actual", u.mp_actual), u.max_mp)
                    u.nivel      = s.get("nivel", u.nivel)

    # ===================================================
    # Roguelike — selección de grupo
    # ===================================================
    def _open_hero_selection(self):
        self.rogue           = RogueRunState()
        self._hero_cursor    = 0
        self._selected_heroes = []
        self.estado_juego    = "MENU_SELECCION_GRUPO"
        if self.audio:
            self.audio.play("menu_open")

    def _handle_hero_selection(self, key):
        pool = self.hero_pool
        if key == pygame.K_LEFT:
            self._hero_cursor = (self._hero_cursor - 1) % len(pool)
            if self.audio: self.audio.play("cursor_move")
        elif key == pygame.K_RIGHT:
            self._hero_cursor = (self._hero_cursor + 1) % len(pool)
            if self.audio: self.audio.play("cursor_move")
        elif key in [pygame.K_RETURN, pygame.K_SPACE]:
            hero = pool[self._hero_cursor]
            if hero not in self._selected_heroes:
                if len(self._selected_heroes) < MAX_HEROES:
                    self._selected_heroes.append(hero)
                    if self.audio: self.audio.play("menu_confirm")
            else:
                self._selected_heroes.remove(hero)
                if self.audio: self.audio.play("menu_cancel")
        elif key == pygame.K_f and len(self._selected_heroes) >= MIN_HEROES:
            # Confirmar grupo y empezar
            self.rogue.selected_heroes = [h.unit_id for h in self._selected_heroes]
            self.start_new_game()
        elif key == pygame.K_ESCAPE:
            self.estado_juego = "MENU_PRINCIPAL"
            if self.audio: self.audio.play("menu_cancel")

    # ===================================================
    # Roguelike — selección de reliquia
    # ===================================================
    def _open_relic_selection(self):
        self.relic_choices  = pick_relic_choices(self.rogue.acquired_relics)
        self._relic_cursor  = 0
        self._show_acquired_relics = False
        self.estado_juego   = "MENU_MEJORAS"
        if self.audio:
            self.audio.play("menu_open")

    def _handle_relic_selection(self, key):
        if not self.relic_choices:
            self._do_advance()
            return
        # TAB o Q alternan el panel de items adquiridos
        if key in [pygame.K_TAB, pygame.K_q]:
            self._show_acquired_relics = not self._show_acquired_relics
            if self.audio: self.audio.play("cursor_move")
            return
        if key == pygame.K_LEFT:
            self._relic_cursor = (self._relic_cursor - 1) % len(self.relic_choices)
            if self.audio: self.audio.play("cursor_move")
        elif key == pygame.K_RIGHT:
            self._relic_cursor = (self._relic_cursor + 1) % len(self.relic_choices)
            if self.audio: self.audio.play("cursor_move")
        elif key in [pygame.K_RETURN, pygame.K_SPACE]:
            relic = self.relic_choices[self._relic_cursor]
            self.rogue.add_relic(relic)
            self._log(f"Reliquia: {relic.nombre}")
            if self.audio: self.audio.play("level_up")
            self._do_advance()  # _load_map aplica las reliquias a las nuevas unidades

    # ===================================================
    # Inicio de partida
    # ===================================================
    def start_new_game(self):
        """Reinicia desde cero (mapa 1, dificultad fácil)."""
        self.map_number    = 0
        self.last_map_name = ""
        self.score.reset()
        self._load_map(pick_random_map())

    def _do_advance(self):
        """Carga el siguiente mapa efectivamente (llamado tras elegir reliquia o directo)."""
        self.map_number += 1
        if _is_boss_slot(self.map_number):
            next_map = pick_boss_map(self.rogue.used_boss_map_names)
            if next_map:
                self.rogue.used_boss_map_names.append(next_map.name)
            else:
                next_map = pick_next_map(self.map_number, self.last_map_name)
        else:
            next_map = pick_next_map(self.map_number, self.last_map_name)
        self._load_map(next_map)

    def _save_hero_snapshots(self):
        """Guarda stats actuales de los aliados vivos para persistirlos al siguiente mapa."""
        self.rogue.hero_snapshots = {}
        self.rogue.snapshot_relic_count = len(self.rogue.acquired_relics)
        for u in self.unidades_vivas:
            if u.bando != "aliado":
                continue
            uid = getattr(u, "unit_id", u.nombre)
            # Serializar inventario como lista de item_ids del catálogo.
            # Se excluyen ítems sin ID (no deberían existir en condiciones normales).
            inv_ids = [
                it.item_id for it in u.inventario
                if getattr(it, "item_id", "")
            ]
            equipped_id = getattr(getattr(u, "arma_equipada", None), "item_id", None)
            self.rogue.hero_snapshots[uid] = {
                "nivel":           u.nivel,
                "exp":             u.exp,
                "hp_actual":       u.hp_actual,
                "max_hp":          u.max_hp,
                "mp_actual":       u.mp_actual,
                "max_mp":          u.max_mp,
                "level_gains":     dict(getattr(u, "_level_gains", {})),
                "inventario":      inv_ids,
                "arma_equipada_id": equipped_id,
            }

    def advance_to_next_map(self):
        """Registra puntos, guarda snapshots de héroes y abre menú de mejoras (o VICTORIA final)."""
        hp_total = sum(u.hp_actual for u in self.unidades_vivas if u.bando == "aliado")
        tier     = get_difficulty_tier(self.map_number)
        self.score.on_map_clear(hp_total, tier)
        self.score.save_if_highscore(self.modo_juego)
        self._save_hero_snapshots()   # persistir niveles antes de descartar las unidades
        # Mapa 9 (índice) = décimo mapa → run completa → victoria total
        if self.map_number >= MAX_MAPS - 1:
            delete_save()
            self.estado_juego = "VICTORIA"
            if self.audio:
                self.audio.play_bgm("victory.mp3")
            return
        self._open_relic_selection()

    def _pick_next_boss(self) -> str:
        """Elige un boss ID del pool que no haya sido usado en esta run."""
        available = [b for b in _ALL_BOSS_IDS if b not in self.rogue.used_boss_ids]
        if not available:
            available = list(_ALL_BOSS_IDS)   # todos usados — reiniciar pool
        import random as _rnd
        chosen = _rnd.choice(available)
        self.rogue.used_boss_ids.append(chosen)
        return chosen

    @staticmethod
    def _scale_boss_for_map(unit, map_number: int):
        """Escala stats del jefe según el slot de jefe (0, 1 o 2) en la run.
        Slot 0 (mapa 2): stats base del JSON — primer jefe accesible.
        Slot 1 (mapa 5): escala moderada — jefe de mitad de run.
        Slot 2 (mapa 8): escala alta — jefe final de run.
        """
        boss_slot = max(0, min(2, (map_number - 2) // 3))

        # Multiplicadores por slot: (hp, str, def, mp)
        SLOT_MULTS = [
            (1.00, 1.00, 1.00, 1.00),   # Slot 0: sin escala (mapa 2)
            (1.35, 1.20, 1.15, 1.25),   # Slot 1: +35% HP, +20% STR (mapa 5)
            (1.80, 1.50, 1.40, 1.60),   # Slot 2: +80% HP, +50% STR (mapa 8)
        ]
        hp_m, str_m, def_m, mp_m = SLOT_MULTS[boss_slot]

        unit.max_hp    = max(1, round(unit.max_hp  * hp_m))
        unit.hp_actual = unit.max_hp
        unit.fuerza    = max(1, round(unit.fuerza  * str_m))
        unit.defensa   = max(0, round(unit.defensa * def_m))
        if unit.max_mp and mp_m > 1.0:
            unit.max_mp    = max(0, round(unit.max_mp * mp_m))
            unit.mp_actual = unit.max_mp

        # SPD: +1 en slot 1, +2 en slot 2
        if boss_slot >= 1:
            unit.velocidad = max(1, getattr(unit, "velocidad", 5) + boss_slot)

        # Nivel visual acorde al slot
        unit.nivel = max(unit.nivel, [3, 8, 14][boss_slot])

    @staticmethod
    def _scale_enemy_for_map(unit, map_number: int):
        """Escala stats y habilidades del enemigo según el número de mapa (empieza en 0).
        Stats: HP +12%/mapa, STR +8%/mapa, DEF +6%/mapa. SPD +1 cada 2 mapas desde mapa 4.
        Skills: mapa 2 → skill básico si no tiene ninguno;
                mapa 4 → skill ofensivo según tipo (físico/mágico);
                mapa 6 → skill avanzado adicional.
        """
        n = max(0, map_number)
        if n == 0:
            return

        # ── Stats ──────────────────────────────────────────────────────────
        hp_mult  = 1.0 + 0.12 * n
        str_mult = 1.0 + 0.08 * n
        def_mult = 1.0 + 0.06 * n

        unit.max_hp    = max(1, round(unit.max_hp  * hp_mult))
        unit.hp_actual = unit.max_hp
        unit.fuerza    = max(1, round(unit.fuerza  * str_mult))
        unit.defensa   = max(0, round(unit.defensa * def_mult))

        if n >= 4:
            spd_bonus  = (n - 2) // 2
            unit.velocidad = max(1, getattr(unit, "velocidad", 5) + spd_bonus)

        # Nivel visual coherente con el progreso
        unit.nivel = max(unit.nivel, 1 + n)

        # ── Habilidades ────────────────────────────────────────────────────
        # Determinar tipo dominante del enemigo
        is_magic = getattr(unit, "magia", 0) >= getattr(unit, "fuerza", 1)
        existing_ids = {getattr(h, "id", None) for h in getattr(unit, "habilidades", [])}

        def _grant(skill_id: str):
            """Añade una skill al enemigo si no la tiene ya."""
            if skill_id not in existing_ids:
                sk = make_skill(skill_id)
                if sk:
                    unit.habilidades.append(sk)
                    existing_ids.add(skill_id)

        # Mapa 2+: si no tiene ninguna habilidad, darle la básica según tipo
        if n >= 2 and not existing_ids - {None}:
            _grant("DARK_BOLT" if is_magic else "FEROCIOUS_STRIKE")

        # Mapa 4+: habilidad ofensiva con efecto de estado
        if n >= 4:
            if is_magic:
                _grant("THUNDER_BOLT")   # magia + aturdido
            else:
                _grant("VENOM_STRIKE")   # físico + veneno

        # Mapa 6+: habilidad avanzada (drenar / tajo doble)
        if n >= 6:
            if is_magic:
                _grant("DRAIN_FORCE")    # drenar fuerza
            else:
                _grant("DOUBLE_CUT")     # máximo daño físico

        # Mapa 8+: todos los enemigos añaden habilidad de fuego/sombra
        if n >= 8:
            _grant("FIRE_BLAST" if is_magic else "SHADOW_BLADE")

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

        # Determinar aliados: PVE roguelike usa el grupo seleccionado
        ally_positions = [sp.pos for sp in map_def.spawns if sp.bando == "aliado"]

        if self.modo_juego == "PVE" and self.rogue.selected_heroes:
            # Mapear cada héroe elegido a una posición de spawn
            self.unidades = []
            for i, unit_id in enumerate(self.rogue.selected_heroes):
                if i < len(ally_positions):
                    pos = ally_positions[i]
                else:
                    # Más héroes que posiciones: colocar adyacente al último
                    base = ally_positions[-1] if ally_positions else (3, 3)
                    pos  = (base[0] + (i - len(ally_positions) + 1), base[1])
                self.unidades.append(
                    make_unit(unit_id, pos[0], pos[1], "aliado",
                              add_floating_text=self.fx.add_text)
                )
        else:
            # PVP u otros modos: aliados fijos del JSON del mapa
            self.unidades = [
                make_unit(sp.unit_id, sp.pos[0], sp.pos[1], sp.bando,
                          add_floating_text=self.fx.add_text)
                for sp in map_def.spawns
            ]

        # Restaurar niveles/stats o aplicar reliquias según corresponda
        new_relics = self.rogue.acquired_relics[self.rogue.snapshot_relic_count:]
        for u in self.unidades:
            if u.bando != "aliado":
                continue
            uid = getattr(u, "unit_id", u.nombre)
            snap = self.rogue.hero_snapshots.get(uid)
            if snap:
                # Héroe vivo del mapa anterior: restaurar stats y aplicar solo reliquias nuevas
                gains = snap.get("level_gains", {})
                u.nivel     = snap["nivel"]
                u.exp       = snap["exp"]
                u.max_hp    = snap["max_hp"]
                u.max_mp    = snap["max_mp"]
                u.hp_actual = snap["hp_actual"]
                u.mp_actual = snap["mp_actual"]
                # Restaurar ganancias de level-up en stats que NO están en max_hp/max_mp
                u.fuerza    = u.fuerza    + gains.get("fuerza",    0)
                u.defensa   = u.defensa   + gains.get("defensa",   0)
                u.velocidad = u.velocidad + gains.get("velocidad", 0)
                u.habilidad = u.habilidad + gains.get("habilidad", 0)
                u.suerte    = u.suerte    + gains.get("suerte",    0)
                # Restaurar _level_gains para que futuros level-ups sigan acumulando
                if hasattr(u, "_level_gains"):
                    u._level_gains = dict(gains)
                # Solo aplicar las reliquias adquiridas DESPUÉS de la última snapshot
                for r in new_relics:
                    self.rogue.apply_relic_to_unit_single(r, u)
                # Restaurar habilidades de progresión (silencioso — sin floating text)
                if hasattr(u, "apply_skill_progression"):
                    u.apply_skill_progression(u.nivel)
                # Restaurar inventario acumulado durante la run
                saved_inv = snap.get("inventario", [])
                if saved_inv:
                    u.inventario = []
                    u.arma_equipada = None
                    for iid in saved_inv:
                        try:
                            u.inventario.append(make_item(iid))
                        except ValueError:
                            pass  # ítem obsoleto — ignorar silenciosamente
                    # Reequipar el arma guardada, o la primera arma disponible
                    equipped_id = snap.get("arma_equipada_id")
                    for it in u.inventario:
                        if it.tipo == "arma":
                            if u.arma_equipada is None:
                                u.arma_equipada = it   # fallback: primera arma
                            if it.item_id == equipped_id:
                                u.arma_equipada = it
                                break
            else:
                # Héroe nuevo (murió el mapa anterior) o primera partida: aplicar todas las reliquias
                for r in self.rogue.acquired_relics:
                    self.rogue.apply_relic_to_unit_single(r, u)

        is_boss_map = getattr(map_def, "is_boss", False)
        tier = get_difficulty_tier(self.map_number)

        if is_boss_map:
            # Mapa de jefe: un único jefe escalado en cada posición de enemigo
            boss_id = self._pick_next_boss()
            for pos in map_def.enemy_positions:
                boss = make_unit(boss_id, pos[0], pos[1], "enemigo",
                                 add_floating_text=self.fx.add_text)
                boss.is_boss = True
                self._scale_boss_for_map(boss, self.map_number)
                self.unidades.append(boss)
        else:
            # Mapa normal: enemigos aleatorios según dificultad
            enemy_assignments = pick_enemies_for_difficulty(
                tier, list(map_def.enemy_positions), self.map_number)
            for unit_id, pos in enemy_assignments:
                enemy = make_unit(unit_id, pos[0], pos[1], "enemigo",
                                  add_floating_text=self.fx.add_text)
                self._scale_enemy_for_map(enemy, self.map_number)
                self.unidades.append(enemy)

        self.idx_fase   = 0
        self.sel_unidad = None
        self.sel_skill  = None
        self.casillas_mov = []
        self.targets      = []

        self.cursor_x, self.cursor_y = 5, 5
        self.clamp_cursor()

        self.estado_juego = "NEUTRAL"

        if is_boss_map:
            self.timer_transicion = 150
            self.texto_transicion = "¡JEFE APARECE!"
            self.color_transicion = (200, 30, 30)
        else:
            self.timer_transicion = 90
            self.texto_transicion = f"TURNO {self.fase_actual.upper()}"
            self.color_transicion = C.AZUL_MP if self.fase_actual == "aliado" else C.ROJO_HP

        for u in self.unidades:
            if u.bando == self.fase_actual:
                u.resetear_turno()

        if self.audio:
            if is_boss_map:
                self.audio.play_bgm("Boss.mp3")
            else:
                self.audio.play_bgm("exploration.mp3")

        self.score.set_difficulty(tier)
        save_run(self)          # auto-save al cargar cada mapa

        tier_label = "JEFE" if is_boss_map else tier.upper()
        self._log(f"--- {map_def.name} [Mapa {self.map_number+1}] [{tier_label}] ---")

    # ===================================================
    # Cambio de turno
    # ===================================================
    def end_turn(self):
        self.idx_fase = (self.idx_fase + 1) % len(self.FASES)

        if self.audio:
            self.audio.play("turn_start")

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
        if self.estado_juego in ["MENU_PRINCIPAL","MENU_CONTROLES","GAME_OVER","VICTORIA","PAUSA",
                                  "MENU_SELECCION_GRUPO","MENU_MEJORAS","MENU_PUNTAJES"]:
            return
        vivos    = self.unidades_vivas
        aliados  = [u for u in vivos if u.bando == "aliado"]
        enemigos = [u for u in vivos if u.bando == "enemigo"]
        if not aliados:
            self.estado_juego = "GAME_OVER"
            self.score.save_if_highscore(self.modo_juego)
            delete_save()           # run perdida → borra el guardado
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
                self._open_hero_selection()
            elif k == pygame.K_2:
                self.modo_juego = "PVE"
                self._open_hero_selection()
            elif k == pygame.K_3:
                self.estado_juego = "MENU_CONTROLES"
            elif k == pygame.K_4 and has_save():
                self.continue_saved_run()
            elif k == pygame.K_5:
                self.estado_juego = "MENU_PUNTAJES"
            return

        # --- PANTALLA DE PUNTAJES ---
        if self.estado_juego == "MENU_PUNTAJES":
            if k == pygame.K_ESCAPE:
                self.estado_juego = "MENU_PRINCIPAL"
            return

        # --- SELECCIÓN DE GRUPO ---
        if self.estado_juego == "MENU_SELECCION_GRUPO":
            self._handle_hero_selection(k)
            return

        # --- MEJORAS ENTRE MAPAS ---
        if self.estado_juego == "MENU_MEJORAS":
            self._handle_relic_selection(k)
            return

        # --- MENÚ CONTROLES ---
        if self.estado_juego == "MENU_CONTROLES":
            if k == pygame.K_ESCAPE:
                self.estado_juego = "MENU_PRINCIPAL"
            return

        # --- FIN DE PARTIDA ---
        if self.estado_juego == "VICTORIA":
            if k == pygame.K_r:
                self.advance_to_next_map()   # → abre MENU_MEJORAS → _do_advance
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
        if self.audio:
            self.audio.play("menu_cancel")

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
                    if self.audio:
                        self.audio.play("unit_select")
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
                    if self.audio:
                        self.audio.play("unit_move")

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

                if self.audio:
                    self.audio.play("attack")
                # VFX impacto en el defensor
                tx_px = t.x * C.TAMANO_TILE + C.TAMANO_TILE // 2
                ty_px = t.y * C.TAMANO_TILE + C.TAMANO_TILE // 2
                self.fx.add_animation(get_fx_frames("attack"), tx_px, ty_px)

                result = resolver_combate(self.sel_unidad, t,
                                          add_fx=self.fx.add_text,
                                          terreno_esquive_def=esq_def,
                                          terreno_esquive_atq=esq_atq)
                self._process_combat_result(self.sel_unidad, t, result)

                # VFX muerte
                if result.get("mato_def"):
                    self.fx.add_animation(get_fx_frames("death"), tx_px, ty_px)
                if result.get("mato_atq"):
                    ax_px = self.sel_unidad.x * C.TAMANO_TILE + C.TAMANO_TILE // 2
                    ay_px = self.sel_unidad.y * C.TAMANO_TILE + C.TAMANO_TILE // 2
                    self.fx.add_animation(get_fx_frames("death"), ax_px, ay_px)

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
            if atq.bando == "aliado":
                self.score.on_kill()
        if result.get("mato_atq"):
            self._log(f"{atq.nombre} fue derrotado en el contraataque.")
            if atq.bando == "aliado":
                self.score.on_ally_lost()

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
                if self.audio:
                    self.audio.play("menu_open")
            else:
                self.fx.add_text(self.sel_unidad.x * 32, self.sel_unidad.y * 32,
                                  "Sin objetivo", C.GRIS_INACTIVO)
                if self.audio:
                    self.audio.play("error")

        elif key == pygame.K_h:  # Habilidad
            self.estado_juego = "MENU_SKILLS"
            if self.audio:
                self.audio.play("menu_open")

        elif key == pygame.K_i:  # Inventario
            self.estado_juego = "MENU_INVENTARIO"
            if self.audio:
                self.audio.play("menu_open")

        elif key == pygame.K_e:  # Esperar
            self.sel_unidad.ha_actuado = True
            self._log(f"{self.sel_unidad.nombre} esperó.")
            if self.audio:
                self.audio.play("unit_wait")
            self.sel_unidad   = None
            self.targets      = []
            self.estado_juego = "NEUTRAL"

        elif key == pygame.K_w:  # Awakening
            self.sel_unidad.activar_awakening()
            if self.sel_unidad.awakened:
                self.dialogue.trigger(self.sel_unidad, "awakening")
                self._log(f"{self.sel_unidad.nombre} activó Awakening.")
                if self.audio:
                    self.audio.play("awakening")
                awk_px = self.sel_unidad.x * C.TAMANO_TILE + C.TAMANO_TILE // 2
                awk_py = self.sel_unidad.y * C.TAMANO_TILE + C.TAMANO_TILE // 2
                self.fx.add_animation(get_fx_frames("awakening"), awk_px, awk_py)

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

        if self.estado_juego in ["MENU_PRINCIPAL","MENU_CONTROLES","GAME_OVER","VICTORIA","PAUSA",
                                  "MENU_SELECCION_GRUPO","MENU_MEJORAS"]:
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
            "weather":         getattr(self.map_def, "weather", None),
            "is_boss_map":     getattr(self.map_def, "is_boss", False),

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

            "score_summary":   self.score.get_summary(),
            "top_scores":      load_scores(),
            "has_save":        has_save(),

            # Roguelike
            "rogue_heroes":    self.hero_pool,
            "rogue_selected":  list(self._selected_heroes),
            "rogue_cursor":    self._hero_cursor,
            "relic_choices":   list(self.relic_choices),
            "relic_cursor":    self._relic_cursor,
            "rogue_relics":    list(self.rogue.acquired_relics),
            "show_acquired_relics": self._show_acquired_relics,
        }
