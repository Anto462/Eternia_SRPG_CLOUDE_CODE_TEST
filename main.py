# main.py — EterniaSrpg
# Punto de entrada limpio: solo inicialización + game loop.

import sys
import os
import pygame

# Asegurar que el directorio del proyecto está en sys.path
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import constants as C
from ui.renderer      import UIRenderer
from core.game_state  import GameState
from core.ai          import AIController
from loaders.audio_loader import AudioLoader


def main():
    pygame.init()
    pygame.display.set_caption(C.TITULO)
    screen = pygame.display.set_mode((C.ANCHO_PANTALLA, C.ALTO_PANTALLA))
    clock  = pygame.time.Clock()

    fonts = {
        "std":      pygame.font.SysFont("Arial", 20),
        "mini":     pygame.font.SysFont("Arial", 15),
        "title":    pygame.font.SysFont("Arial", 40, bold=True),
        "ui_title": pygame.font.SysFont("Arial", 22, bold=True),
    }

    audio = AudioLoader(sfx_volume=0.55)
    ui_r  = UIRenderer(fonts)
    state = GameState(modo_juego="PVP", audio=audio)
    ai_c  = AIController(interval_frames=25)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            else:
                state.handle_event(event)

        state.update(dt, ai_controller=ai_c)
        ui_r.render(screen, state.to_render_state())
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
