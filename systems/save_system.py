# systems/save_system.py
# -------------------------------------------------
# Guardado y carga de runs en progreso.
#
# Qué se serializa:
#   - Progresión: map_number, last_map_name, modo_juego
#   - Puntuación parcial: kills, maps_cleared, total
#   - Roguelike: héroe IDs, reliquias adquiridas
#   - Aliados: HP/MP actuales, nivel, exp, inventario
#
# Formato: JSON plano en data/save.json
# Auto-save al avanzar mapa; se borra al perder.

import json
import os

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SAVE_FILE = os.path.join(_ROOT, "data", "save.json")


# =================================================
# SERIALIZACIÓN DE UNIDADES
# =================================================

def _serialize_unit(u) -> dict:
    return {
        "unit_id":    getattr(u, "unit_id", u.nombre),
        "nombre":     u.nombre,
        "x": u.x, "y": u.y,
        "bando":      u.bando,
        "hp_actual":  u.hp_actual,
        "max_hp":     u.max_hp,
        "mp_actual":  u.mp_actual,
        "max_mp":     u.max_mp,
        "nivel":      u.nivel,
        "exp":        getattr(u, "exp", 0),
        "fuerza":     u.fuerza,
        "defensa":    u.defensa,
        "velocidad":  getattr(u, "velocidad", 5),
        "movimiento": u.movimiento,
        "inventario": [
            {"nombre": it.nombre, "item_id": getattr(it, "item_id", it.nombre)}
            for it in u.inventario
        ],
        "arma_equipada": (
            getattr(u.arma_equipada, "item_id", u.arma_equipada.nombre)
            if u.arma_equipada else None
        ),
    }


def _serialize_relic(r) -> dict:
    return {"relic_id": r.relic_id}


# =================================================
# API PÚBLICA
# =================================================

def has_save() -> bool:
    return os.path.exists(_SAVE_FILE)


def save_run(state) -> bool:
    """
    Serializa el GameState actual y lo escribe en save.json.
    Retorna True si tuvo éxito.
    `state` debe ser un GameState (no el dict de render).
    """
    try:
        aliados = [u for u in state.unidades_vivas if u.bando == "aliado"]
        data = {
            "map_number":    state.map_number,
            "last_map_name": state.last_map_name,
            "modo_juego":    state.modo_juego,
            "score": {
                "total":         state.score.total_score,
                "kills":         state.score.kills,
                "maps_cleared":  state.score.maps_cleared,
            },
            "rogue": {
                "selected_heroes": state.rogue.selected_heroes,
                "acquired_relics": [_serialize_relic(r) for r in state.rogue.acquired_relics],
                "score_multiplier": state.rogue.score_multiplier,
            },
            "aliados": [_serialize_unit(u) for u in aliados],
        }
        os.makedirs(os.path.dirname(_SAVE_FILE), exist_ok=True)
        with open(_SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[SaveSystem] Error guardando: {e}")
        return False


def load_save() -> dict:
    """Carga y retorna el dict del save, o {} si no existe/está corrupto."""
    if not has_save():
        return {}
    try:
        with open(_SAVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[SaveSystem] Error cargando save: {e}")
        return {}


def delete_save():
    """Borra el archivo de guardado (al perder una run)."""
    if os.path.exists(_SAVE_FILE):
        try:
            os.remove(_SAVE_FILE)
        except Exception as e:
            print(f"[SaveSystem] Error borrando save: {e}")
