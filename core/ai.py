# core/ai.py
# -------------------------------------------------
# IA enemiga.
# Usa el nuevo sistema de combate (hit rate, crits, triángulo).

from core.pathfinding import obtener_movimientos_validos
from core.combat import resolver_combate, obtener_enemigos_en_rango


class AIController:
    def __init__(self, interval_frames: int = 30):
        self.timer_accion    = 0
        self.intervalo_accion = interval_frames

    def ejecutar_turno(self, mapa, lista_unidades, items_suelo,
                       bando_activo, add_floating_text=None) -> bool:
        if self.timer_accion > 0:
            self.timer_accion -= 1
            return False

        ia_units = [
            u for u in lista_unidades
            if u.esta_viva() and u.bando == bando_activo and not u.ha_actuado
        ]
        if not ia_units:
            return True

        unidad  = ia_units[0]
        enemies = [u for u in lista_unidades if u.esta_viva() and u.bando != bando_activo]

        if not enemies:
            unidad.ha_actuado = True
            return False

        # 1) Intentar habilidad primero (solo si tiene MP y objetivo)
        if self._try_skill(unidad, lista_unidades, add_floating_text):
            unidad.ha_actuado = True
            self.timer_accion = self.intervalo_accion
            return False

        # 2) Atacar si puede
        if self._try_attack(unidad, enemies, mapa, add_floating_text):
            unidad.ha_actuado = True
            self.timer_accion = self.intervalo_accion
            return False

        # 3) Moverse hacia objetivo
        target = self._pick_target(unidad, enemies)
        self._move_towards(unidad, target, mapa, lista_unidades, items_suelo)

        # 4) Intentar atacar post-movimiento
        enemies = [u for u in lista_unidades if u.esta_viva() and u.bando != bando_activo]
        self._try_attack(unidad, enemies, mapa, add_floating_text)

        unidad.ha_actuado = True
        self.timer_accion = self.intervalo_accion
        return False

    # -----------------------------------------
    # Ataque normal: prioriza kills, luego low HP
    # -----------------------------------------
    def _try_attack(self, unidad, enemies, mapa, add_floating_text) -> bool:
        from core.combat import calcular_daño
        targets = obtener_enemigos_en_rango(unidad, enemies)
        if not targets:
            return False

        best, best_score = None, -10**9
        for t in targets:
            dmg       = calcular_daño(unidad, t)
            will_kill = (t.hp_actual - dmg) <= 0
            score     = 10000 if will_kill else 0
            score    += (200 - t.hp_actual)
            if score > best_score:
                best_score, best = score, t

        if best:
            resolver_combate(unidad, best, add_fx=add_floating_text)
            return True
        return False

    # -----------------------------------------
    # Habilidad: usa la primera que puede y tiene objetivo
    # -----------------------------------------
    def _try_skill(self, unidad, all_units, add_floating_text) -> bool:
        for sk in unidad.habilidades:
            if unidad.mp_actual < sk.costo_mp:
                continue
            targets = obtener_enemigos_en_rango(unidad, all_units, sk)
            if targets:
                unidad.usar_habilidad(sk, targets[0])
                return True
        return False

    # -----------------------------------------
    # Target a perseguir
    # -----------------------------------------
    def _pick_target(self, unidad, enemies):
        best, best_score = None, 10**9
        for e in enemies:
            dist  = abs(e.x - unidad.x) + abs(e.y - unidad.y)
            score = dist * 100 + e.hp_actual
            if score < best_score:
                best_score, best = score, e
        return best

    # -----------------------------------------
    # Movimiento + pickup de ítems
    # -----------------------------------------
    def _move_towards(self, unidad, target, mapa, lista_unidades, items_suelo):
        if not target:
            return

        moves = obtener_movimientos_validos(unidad, mapa, lista_unidades)
        if not moves:
            return

        best_move, best_score = None, 10**9
        for (mx, my) in moves:
            dist_after = abs(target.x - mx) + abs(target.y - my)
            score      = dist_after * 10
            if (mx, my) in items_suelo:
                score -= 5
            if score < best_score:
                best_score, best_move = score, (mx, my)

        if best_move:
            unidad.x, unidad.y = best_move

            if (unidad.x, unidad.y) in items_suelo:
                it = items_suelo.pop((unidad.x, unidad.y))
                unidad.inventario.append(it)
                if it.tipo == "arma" and not unidad.arma_equipada:
                    unidad.arma_equipada = it
