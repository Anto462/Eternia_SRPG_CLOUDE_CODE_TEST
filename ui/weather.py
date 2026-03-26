# ui/weather.py
# -------------------------------------------------
# Sistema de clima puramente estético para los mapas.
# Usa un pool de partículas pre-asignado para cumplir
# la regla de "sin heap allocations en el Update loop".
#
# Tipos soportados:
#   None         — despejado
#   "rain"       — lluvia suave
#   "heavy_rain" — tormenta con viento
#   "snow"       — nieve suave
#   "blizzard"   — ventisca densa
#   "mist"       — niebla flotante
#   "lightning"  — tormenta eléctrica (lluvia + rayos)

import math
import random
import pygame

# ─── Parámetros por tipo de clima ─────────────────────────────────────────────
_WEATHER_CFG = {
    "rain": {
        "count":     120,
        "speed_y":   (8.0, 14.0),
        "speed_x":   (-1.0, 0.5),
        "length":    (6, 12),
        "width":     1,
        "color":     (180, 200, 230, 140),
        "wind_freq": 0.0,
        "overlay":   None,
        "lightning": False,
        "drift":     False,
    },
    "heavy_rain": {
        "count":     300,
        "speed_y":   (14.0, 22.0),
        "speed_x":   (-4.0, -1.5),
        "length":    (10, 18),
        "width":     1,
        "color":     (160, 185, 220, 160),
        "wind_freq": 0.3,
        "overlay":   (10, 15, 30, 35),
        "lightning": False,
        "drift":     False,
    },
    "snow": {
        "count":     80,
        "speed_y":   (1.5, 3.5),
        "speed_x":   (-0.5, 0.5),
        "length":    (2, 4),          # radio del copo (se dibuja como circle)
        "width":     2,
        "color":     (230, 240, 255, 180),
        "wind_freq": 0.15,
        "overlay":   (200, 215, 240, 8),
        "lightning": False,
        "drift":     True,
    },
    "blizzard": {
        "count":     220,
        "speed_y":   (4.0, 9.0),
        "speed_x":   (-8.0, -3.0),
        "length":    (2, 5),
        "width":     2,
        "color":     (215, 230, 255, 200),
        "wind_freq": 0.6,
        "overlay":   (180, 200, 230, 20),
        "lightning": False,
        "drift":     True,
    },
    "lightning": {
        "count":     180,
        "speed_y":   (12.0, 20.0),
        "speed_x":   (-3.0, -1.0),
        "length":    (8, 16),
        "width":     1,
        "color":     (150, 175, 215, 150),
        "wind_freq": 0.4,
        "overlay":   (5, 10, 20, 25),
        "lightning": True,
        "drift":     False,
    },
    "mist": {
        "count":     0,               # niebla no usa partículas puntuales
        "speed_y":   (0.0, 0.0),
        "speed_x":   (0.0, 0.0),
        "length":    (0, 0),
        "width":     1,
        "color":     (180, 200, 220, 0),
        "wind_freq": 0.0,
        "overlay":   None,
        "lightning": False,
        "drift":     False,
    },
}

_MAX_PARTICLES = 300


class _Particle:
    """Slot reutilizable en el pool — sin new durante el update loop."""
    __slots__ = ("x", "y", "vx", "vy", "length", "drift_phase", "active")

    def __init__(self):
        self.x = self.y = self.vx = self.vy = 0.0
        self.length = 6
        self.drift_phase = 0.0
        self.active = False


class _MistPatch:
    """Parche de niebla (5 usados por el tipo 'mist')."""
    __slots__ = ("x", "y", "radius", "alpha", "phase_x", "phase_y", "surf")

    def __init__(self, W: int, H: int):
        self.radius = random.randint(80, 160)
        self.x = float(random.randint(-self.radius, W + self.radius))
        self.y = float(random.randint(0, H))
        self.phase_x = random.uniform(0, math.tau)
        self.phase_y = random.uniform(0, math.tau)
        self.alpha = random.randint(18, 40)
        self.surf = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        # Gradiente radial: círculo sólido en el centro, fade en los bordes
        for r in range(self.radius, 0, -2):
            a = int(self.alpha * (1 - r / self.radius) ** 1.4)
            pygame.draw.circle(self.surf, (180, 200, 220, a),
                               (self.radius, self.radius), r)

    def update(self, t: float, W: int):
        # Deriva sinusoidal lenta — sin allocations
        self.x += math.sin(t * 0.18 + self.phase_x) * 0.4
        self.y += math.sin(t * 0.09 + self.phase_y) * 0.15
        if self.x > W + self.radius:
            self.x = float(-self.radius)

    def draw(self, surf: pygame.Surface):
        surf.blit(self.surf, (int(self.x) - self.radius, int(self.y) - self.radius),
                  special_flags=pygame.BLEND_RGBA_ADD)


class WeatherSystem:
    """Sistema de clima estético con pool de partículas pre-asignado."""

    W = 800
    H = 600

    def __init__(self):
        # Pool fijo — se pre-asigna UNA sola vez
        self._pool: list[_Particle] = [_Particle() for _ in range(_MAX_PARTICLES)]
        self._active_count = 0

        self._weather_type: str | None = None
        self._cfg: dict = {}

        # Surface dedicada para compositar sobre el mapa
        self._surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)

        # Niebla
        self._mist_patches: list[_MistPatch] = []

        # Rayo
        self._lightning_timer  = 0.0
        self._lightning_next   = random.uniform(4.0, 9.0)   # segundos hasta próximo rayo
        self._lightning_flash  = 0.0   # segundos de destello activo (0 = inactivo)
        self._lightning_bolts: list[list[tuple]] = []        # polígonos del rayo actual

        # Viento sinusoidal
        self._wind_t = 0.0

        # Tiempo acumulado para drift
        self._t = 0.0

    # ─── API pública ──────────────────────────────────────────────────────────

    def set_weather(self, weather_type: str | None):
        """Cambia el tipo de clima; reinicia el pool."""
        if weather_type == self._weather_type:
            return
        self._weather_type = weather_type
        self._cfg = _WEATHER_CFG.get(weather_type or "", {})

        # Desactivar todas las partículas del pool
        for p in self._pool:
            p.active = False
        self._active_count = 0

        # Niebla: crear parches
        self._mist_patches = []
        if weather_type == "mist":
            for _ in range(6):
                self._mist_patches.append(_MistPatch(self.W, self.H))

        # Activar partículas según configuración
        count = self._cfg.get("count", 0)
        count = min(count, _MAX_PARTICLES)
        for i in range(count):
            self._spawn(self._pool[i], initial=True)
        self._active_count = count

    def update(self, dt: float):
        if not self._weather_type or not self._cfg:
            return

        self._t += dt
        self._wind_t += dt

        cfg = self._cfg

        # ── Partículas ────────────────────────────────────────────────────────
        wind_freq = cfg.get("wind_freq", 0.0)
        wind_x = math.sin(self._wind_t * 1.3) * wind_freq * 3.0 if wind_freq else 0.0

        for i in range(self._active_count):
            p = self._pool[i]
            if not p.active:
                self._spawn(p, initial=False)
                continue

            # Drift sinusoidal para nieve
            drift = math.sin(self._t * 1.2 + p.drift_phase) * 0.6 if cfg.get("drift") else 0.0

            p.x += (p.vx + wind_x + drift) * dt * 60
            p.y += p.vy * dt * 60

            # Reciclar partícula fuera de pantalla
            if p.y > self.H + 20 or p.x < -40 or p.x > self.W + 20:
                self._spawn(p, initial=False)

        # ── Niebla ────────────────────────────────────────────────────────────
        for patch in self._mist_patches:
            patch.update(self._t, self.W)

        # ── Rayos ─────────────────────────────────────────────────────────────
        if cfg.get("lightning"):
            self._lightning_flash = max(0.0, self._lightning_flash - dt)
            self._lightning_timer += dt
            if self._lightning_timer >= self._lightning_next:
                self._lightning_timer = 0.0
                self._lightning_next = random.uniform(4.0, 9.0)
                self._trigger_lightning()

    def draw(self, surf: pygame.Surface):
        if not self._weather_type:
            return

        self._surf.fill((0, 0, 0, 0))
        cfg = self._cfg

        # ── Overlay de ambiente ───────────────────────────────────────────────
        overlay_col = cfg.get("overlay")
        if overlay_col:
            self._surf.fill(overlay_col)

        # ── Flash de rayo ────────────────────────────────────────────────────
        if self._lightning_flash > 0:
            alpha = int(min(200, self._lightning_flash * 1800))
            flash_surf = pygame.Surface((self.W, self.H), pygame.SRCALPHA)
            flash_surf.fill((220, 230, 255, alpha))
            self._surf.blit(flash_surf, (0, 0))
            # Dibujar bolt
            for bolt in self._lightning_bolts:
                if len(bolt) >= 2:
                    pygame.draw.lines(self._surf, (240, 250, 255, 220), False, bolt, 2)

        # ── Niebla ────────────────────────────────────────────────────────────
        for patch in self._mist_patches:
            patch.draw(self._surf)

        # ── Partículas de lluvia / nieve ──────────────────────────────────────
        col = cfg.get("color", (255, 255, 255, 160))
        is_snow = cfg.get("drift", False)

        for i in range(self._active_count):
            p = self._pool[i]
            if not p.active:
                continue

            px, py = int(p.x), int(p.y)
            if is_snow:
                r = max(1, p.length // 2)
                pygame.draw.circle(self._surf, col, (px, py), r)
            else:
                # Línea de gota de lluvia
                end_x = px + int(p.vx * 0.12)
                end_y = py + p.length
                pygame.draw.line(self._surf, col, (px, py), (end_x, end_y),
                                 cfg.get("width", 1))

        surf.blit(self._surf, (0, 0))

    # ─── Helpers internos (no generan garbage) ────────────────────────────────

    def _spawn(self, p: _Particle, initial: bool):
        """Reinicia una partícula del pool en posición de spawn."""
        cfg = self._cfg
        vy_min, vy_max = cfg.get("speed_y", (5.0, 10.0))
        vx_min, vx_max = cfg.get("speed_x", (-1.0, 1.0))
        l_min, l_max   = cfg.get("length",  (4, 10))

        p.vx = random.uniform(vx_min, vx_max)
        p.vy = random.uniform(vy_min, vy_max)
        p.length = random.randint(l_min, l_max)
        p.drift_phase = random.uniform(0, math.tau)

        # Spawn fuera del borde superior (o distribución inicial aleatoria)
        p.x = float(random.randint(-20, self.W + 20))
        p.y = float(random.randint(-self.H, 0)) if not initial else float(random.randint(0, self.H))
        p.active = True

    def _trigger_lightning(self):
        """Genera un bolt ramificado y activa el flash."""
        self._lightning_flash = 0.12
        self._lightning_bolts = []

        # Rayo principal: zigzag desde arriba hasta 2/3 de la pantalla
        x = float(random.randint(self.W // 4, self.W * 3 // 4))
        y = 0.0
        target_y = float(random.randint(self.H // 2, self.H * 3 // 4))
        bolt: list[tuple] = [(int(x), int(y))]
        while y < target_y:
            x += random.uniform(-30, 30)
            y += random.uniform(18, 35)
            bolt.append((int(x), int(y)))
        self._lightning_bolts.append(bolt)

        # Rama secundaria ocasional
        if len(bolt) >= 3 and random.random() < 0.5:
            branch_start = random.randint(1, len(bolt) - 2)
            bx, by = float(bolt[branch_start][0]), float(bolt[branch_start][1])
            branch: list[tuple] = [(int(bx), int(by))]
            steps = random.randint(2, 4)
            for _ in range(steps):
                bx += random.uniform(-25, 25)
                by += random.uniform(15, 28)
                branch.append((int(bx), int(by)))
            self._lightning_bolts.append(branch)
