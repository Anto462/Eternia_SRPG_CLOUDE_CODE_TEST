# ui/fx.py
# -------------------------------------------------
# FXManager: textos flotantes + animaciones FX con sprites PNG.
#
# Dos tipos de efecto visual:
#   FloatingText  — texto que sube y se desvanece (fallback siempre disponible)
#   FxAnimation   — secuencia de frames PNG cargados por sprite_loader.get_fx_frames()
#
# Uso desde GameState / combat:
#   fx_mgr.add_text(px, py, "-12", BLANCO)
#   fx_mgr.add_animation(get_fx_frames("attack"), px, py)

import pygame
from dataclasses import dataclass, field
from typing import List, Tuple

from constants import NEGRO


# =================================================
# TEXTO FLOTANTE
# =================================================

@dataclass
class FloatingText:
    x:       float
    y:       float
    text:    str
    color:   Tuple[int, int, int]
    size:    int   = 20
    speed_y: float = 1.0
    life:    int   = 60
    alpha:   int   = 255


# =================================================
# ANIMACIÓN FX CON SPRITES
# =================================================

@dataclass
class FxAnimation:
    """
    Animación FX reproducida una sola vez (no loop).
    frames : lista de pygame.Surface cargados desde FxLoader.
    x, y   : posición en píxeles (centro de la animación).
    ticks  : ticks de juego por frame (a 60fps: 3 ticks ≈ 20fps de animación).
    """
    x:      float
    y:      float
    frames: List[pygame.Surface]
    cur:    int  = 0
    timer:  int  = 0
    ticks:  int  = 3
    done:   bool = False

    def update(self):
        if self.done or not self.frames:
            self.done = True
            return
        self.timer = self.timer + 1
        if self.timer >= self.ticks:
            self.timer = 0
            self.cur   = self.cur + 1
            if self.cur >= len(self.frames):
                self.done = True

    def draw(self, surf: pygame.Surface):
        if self.done or not self.frames:
            return
        frame   = self.frames[min(self.cur, len(self.frames) - 1)]
        fw, fh  = frame.get_size()
        surf.blit(frame, (self.x - fw // 2, self.y - fh // 2))


# =================================================
# FXMANAGER
# =================================================

class FXManager:
    """
    Gestiona todos los efectos visuales del juego en pantalla.
    - Textos flotantes: siempre disponibles como fallback.
    - Animaciones FX: cuando se cargan frames reales con sprite_loader.
    """

    def __init__(self):
        self.texts: List[FloatingText] = []
        self.anims: List[FxAnimation]  = []
        self._font_cache: dict         = {}

    # --------------------------------------------------
    # Texto flotante
    # --------------------------------------------------

    def add_text(self, x, y, text, color, size=20, speed_y=1.0):
        """Añade un texto flotante en posición de píxeles."""
        self.texts.append(FloatingText(
            x=float(x), y=float(y),
            text=str(text), color=color,
            size=int(size), speed_y=float(speed_y),
        ))

    # --------------------------------------------------
    # Animación FX
    # --------------------------------------------------

    def add_animation(self, frames: List[pygame.Surface], x: float, y: float,
                      ticks_per_frame: int = 3):
        """
        Añade una animación FX en posición de pantalla (píxeles).
        Si frames está vacío, no hace nada (el evento queda sin FX visual).
        """
        if not frames:
            return
        self.anims.append(FxAnimation(
            x=float(x), y=float(y),
            frames=frames,
            ticks=ticks_per_frame,
        ))

    # --------------------------------------------------
    # Control
    # --------------------------------------------------

    def clear(self):
        self.texts.clear()
        self.anims.clear()

    def update(self):
        # Textos flotantes
        for t in self.texts:
            t.y    = t.y - t.speed_y
            t.life = t.life - 1
            if t.life < 20:
                t.alpha = max(0, int((t.life / 20) * 255))
        self.texts = [t for t in self.texts if t.life > 0]

        # Animaciones FX
        for a in self.anims:
            a.update()
        self.anims = [a for a in self.anims if not a.done]

    # --------------------------------------------------
    # Render
    # --------------------------------------------------

    def draw(self, surface: pygame.Surface):
        # Primero animaciones (debajo de los textos)
        for a in self.anims:
            a.draw(surface)

        # Textos flotantes encima
        for t in self.texts:
            font   = self._get_font(t.size)
            surf   = font.render(t.text, True, t.color)
            shadow = font.render(t.text, True, NEGRO)
            surf.set_alpha(t.alpha)
            shadow.set_alpha(t.alpha)
            surface.blit(shadow, (t.x + 1, t.y + 1))
            surface.blit(surf,   (t.x,     t.y))

    def _get_font(self, size: int) -> pygame.font.Font:
        if size not in self._font_cache:
            self._font_cache[size] = pygame.font.SysFont("Arial", size, bold=True)
        return self._font_cache[size]
