# ai.py
# -------------------------------------------------
# IA enemiga mejorada:
# - Si puede atacar, ataca (prioriza kills)
# - Si no puede, se mueve usando pathfinding real
# - Luego intenta atacar otra vez (post-move)
#
# add_floating_text:
# - callback para FX de combate (lo pasamos a resolver_combate)

from pathfinding import obtener_movimientos_validos
from combat import resolver_combate, obtener_enemigos_en_rango


class AIController:
    def __init__(self, interval_frames=30):
        self.timer_accion = 0
        self.intervalo_accion = interval_frames

    def ejecutar_turno(self, mapa, lista_unidades, items_suelo, bando_activo, add_floating_text=None):
        # delay visual
        if self.timer_accion > 0:
            self.timer_accion -= 1
            return False

        ia_units = [
            u for u in lista_unidades
            if u.esta_viva() and u.bando == bando_activo and not u.ha_actuado
        ]

        if not ia_units:
            return True  # turno IA terminó

        unidad = ia_units[0]

        enemies = [u for u in lista_unidades if u.esta_viva() and u.bando != bando_activo]
        if not enemies:
            unidad.ha_actuado = True
            return False

        # 1) atacar si puede
        if self._try_attack_now(unidad, enemies, add_floating_text):
            unidad.ha_actuado = True
            self.timer_accion = self.intervalo_accion
            return False

        # 2) moverse hacia objetivo
        target = self._pick_main_target(unidad, enemies)
        self._move_towards_target(unidad, target, mapa, lista_unidades, items_suelo)

        # 3) atacar post-move
        if self._try_attack_now(unidad, enemies, add_floating_text):
            unidad.ha_actuado = True
            self.timer_accion = self.intervalo_accion
            return False

        unidad.ha_actuado = True
        self.timer_accion = self.intervalo_accion
        return False

    # -----------------------------------------
    # Ataque: prioriza kill confirm
    # -----------------------------------------
    def _try_attack_now(self, unidad, enemies, add_floating_text):
        targets = obtener_enemigos_en_rango(unidad, enemies)
        if not targets:
            return False

        best = None
        best_score = -10**9

        for t in targets:
            dmg = max(0, unidad.get_poder_ataque() - t.defensa)
            will_kill = (t.hp_actual - dmg) <= 0

            score = 0
            if will_kill:
                score += 10000
            score += (200 - t.hp_actual)

            if score > best_score:
                best_score = score
                best = t

        if best:
            resolver_combate(unidad, best, add_floating_text=add_floating_text)
            return True

        return False

    # -----------------------------------------
    # Target principal (para perseguir)
    # -----------------------------------------
    def _pick_main_target(self, unidad, enemies):
        best = None
        best_score = 10**9

        for e in enemies:
            dist = abs(e.x - unidad.x) + abs(e.y - unidad.y)
            score = dist * 100 + e.hp_actual  # cercano y low hp
            if score < best_score:
                best_score = score
                best = e

        return best

    # -----------------------------------------
    # Movimiento: usa movs válidos reales
    # -----------------------------------------
    def _move_towards_target(self, unidad, target, mapa, lista_unidades, items_suelo):
        if not target:
            return

        moves = obtener_movimientos_validos(unidad, mapa, lista_unidades)
        if not moves:
            return

        best_move = None
        best_score = 10**9

        for (mx, my) in moves:
            dist_after = abs(target.x - mx) + abs(target.y - my)

            # score base: acercarse
            score = dist_after * 10

            # bonus: si cae en item, le baja el score (o sea, lo prefiere)
            if (mx, my) in items_suelo:
                score -= 5

            if score < best_score:
                best_score = score
                best_move = (mx, my)

        if best_move:
            unidad.x, unidad.y = best_move

            # pickup item si cae encima
            if (unidad.x, unidad.y) in items_suelo:
                it = items_suelo.pop((unidad.x, unidad.y))
                unidad.inventario.append(it)

                # auto equip arma si no tiene
                if it.tipo == "arma" and not unidad.arma_equipada:
                    unidad.arma_equipada = it
