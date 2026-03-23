# systems/score_system.py
# -------------------------------------------------
# ScoreTracker: acumula puntos durante una run.
#
# Fórmula:
#   kill      → +100 × multiplicador de dificultad
#   map clear → +500 × multiplicador de dificultad
#   HP bonus  → +(HP_total_aliados_al_limpiar × 3)
#   Racha     → cada 3 kills consecutivos sin perder aliados × 1.5
#
# Multiplicadores de dificultad:
#   easy   → 1.0
#   medium → 1.5
#   hard   → 2.0
#   boss   → 3.0

import json
import os
from dataclasses import dataclass, field
from typing import List

_ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCORES_FILE = os.path.join(_ROOT, "data", "scores.json")

_DIFF_MULT = {"easy": 1.0, "medium": 1.5, "hard": 2.0, "boss": 3.0}
_MAX_SCORES = 5


@dataclass
class ScoreEntry:
    total:      int
    kills:      int
    maps:       int
    tier:       str
    modo:       str


# =================================================
# TRACKER (por run)
# =================================================

class ScoreTracker:
    def __init__(self):
        self.reset()

    def reset(self):
        self.total_score:   int  = 0
        self.kills:         int  = 0
        self.maps_cleared:  int  = 0
        self._streak:       int  = 0   # kills consecutivos sin perder aliado
        self._current_tier: str  = "easy"
        self._breakdown:    list = []  # lista de strings para mostrar en pantalla

    def set_difficulty(self, tier: str):
        self._current_tier = tier

    # --------------------------------------------------
    # Eventos de juego
    # --------------------------------------------------

    def on_kill(self):
        """Llamar cuando un aliado mata a un enemigo."""
        mult  = _DIFF_MULT.get(self._current_tier, 1.0)
        self._streak += 1
        pts = int(100 * mult)
        if self._streak > 0 and self._streak % 3 == 0:
            # Bonus de racha cada 3 kills consecutivos
            pts = int(pts * 1.5)
            self._breakdown.append(f"¡RACHA x{self._streak}! +{pts}")
        self.kills      += 1
        self.total_score += pts

    def on_ally_lost(self):
        """Llamar cuando un aliado muere — rompe racha."""
        self._streak = 0

    def on_map_clear(self, allied_hp_total: int, tier: str):
        """Llamar al limpiar un mapa."""
        mult  = _DIFF_MULT.get(tier, 1.0)
        pts   = int(500 * mult)
        hp_bonus = allied_hp_total * 3
        self.maps_cleared  += 1
        self.total_score   += pts + hp_bonus
        self._breakdown.append(f"Mapa completado +{pts}  HP bonus +{hp_bonus}")
        self._streak = 0

    # --------------------------------------------------
    # Desglose para pantalla
    # --------------------------------------------------

    def get_summary(self) -> dict:
        return {
            "total":      self.total_score,
            "kills":      self.kills,
            "maps":       self.maps_cleared,
            "tier":       self._current_tier,
            "breakdown":  list(self._breakdown[-5:]),
        }

    # --------------------------------------------------
    # Persistencia
    # --------------------------------------------------

    def save_if_highscore(self, modo: str):
        """Guarda la puntuación si entra en el top-5."""
        scores = load_scores()
        entry = {"total": self.total_score, "kills": self.kills,
                 "maps": self.maps_cleared, "tier": self._current_tier, "modo": modo}
        scores.append(entry)
        scores.sort(key=lambda x: x["total"], reverse=True)
        scores = scores[:_MAX_SCORES]
        _write_scores(scores)
        return scores


# =================================================
# PERSISTENCIA
# =================================================

def load_scores() -> List[dict]:
    if not os.path.exists(_SCORES_FILE):
        return []
    try:
        with open(_SCORES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _write_scores(scores: list):
    os.makedirs(os.path.dirname(_SCORES_FILE), exist_ok=True)
    try:
        with open(_SCORES_FILE, "w", encoding="utf-8") as f:
            json.dump(scores, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ScoreSystem] Error guardando scores: {e}")
