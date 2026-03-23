# fx.py
# -------------------------------------------------
# FXManager: maneja efectos simples del juego.
# Por ahora solo textos flotantes, pero aquí puedes meter:
# - pequeños flashes
# - partículas
# - shake de cámara
# - etc.
#
# La idea es que el juego tenga UN objeto FX
# y el resto solo le diga: "agrega un texto aquí".

import pygame
from dataclasses import dataclass
from typing import List, Tuple

from constants import NEGRO


@dataclass
class FloatingText:
    x: float
    y: float
    text: str
    color: Tuple[int, int, int]
    size: int = 20
    speed_y: float = 1.0
    life: int = 60

    # Esto se calcula en runtime
    alpha: int = 255


class FXManager:
    def __init__(self):
        self.texts: List[FloatingText] = []

        # Cache básico de fuentes por tamaño para no crear fuentes cada frame
        self._font_cache = {}

    def _get_font(self, size: int):
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont("Arial", size, bold=True)
        return self._font_cache[size]

    # -------------------------------------------------
    # API simple para el resto del juego:
    # fx.add_text(x, y, "Hit!", color, size=12, speed_y=1)
    # -------------------------------------------------
    def add_text(self, x, y, text, color, size=20, speed_y=1):
        self.texts.append(
            FloatingText(
                x=float(x),
                y=float(y),
                text=str(text),
                color=color,
                size=size,
                speed_y=float(speed_y),
            )
        )

    def clear(self):
        # Útil para reiniciar partida
        self.texts.clear()

    def update(self):
        # Update de todos los textos flotantes
        for t in self.texts:
            t.y -= t.speed_y
            t.life -= 1

            # Fade out al final
            if t.life < 20:
                t.alpha = max(0, int((t.life / 20) * 255))

        # Limpieza
        self.texts = [t for t in self.texts if t.life > 0]

    def draw(self, surface: pygame.Surface):
        # Render de los textos flotantes
        for t in self.texts:
            font = self._get_font(t.size)

            text_surf = font.render(t.text, True, t.color)
            text_surf.set_alpha(t.alpha)

            # sombra para que se lea más (queda bien con tu estilo)
            shadow = font.render(t.text, True, NEGRO)
            shadow.set_alpha(t.alpha)

            surface.blit(shadow, (t.x + 1, t.y + 1))
            surface.blit(text_surf, (t.x, t.y))
