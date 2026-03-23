import sys, os
import pygame

print("CWD:", os.getcwd())
print("sys.path[0]:", sys.path[0])

import constants as C
print("constants ->", C.__file__)

import ui
import ui
print("ui ->", ui.__file__)
print("ui keys sample:", [k for k in dir(ui) if "UI" in k or "Render" in k or k in ("pygame","C")])

import inspect


import game_state
print("game_state ->", game_state.__file__)

import ai
print("ai ->", ai.__file__)

from ui import UIRenderer
from game_state import GameState
from ai import AIController


def main():
    pygame.init()
    screen = pygame.display.set_mode((C.ANCHO_PANTALLA, C.ALTO_PANTALLA))
    pygame.display.set_caption(C.TITULO)

    clock = pygame.time.Clock()

    fonts = {
        "std": pygame.font.SysFont("Arial", 20),
        "mini": pygame.font.SysFont("Arial", 16),
        "title": pygame.font.SysFont("Arial", 40, bold=True),
        "ui_title": pygame.font.SysFont("Arial", 22, bold=True),
    }

    ui_r = UIRenderer(fonts)
    state = GameState(modo_juego="PVP")
    ai_c = AIController(interval_frames=30)

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
