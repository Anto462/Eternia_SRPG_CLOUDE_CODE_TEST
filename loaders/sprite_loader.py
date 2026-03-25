# loaders/sprite_loader.py
# -------------------------------------------------
# Carga sprites desde assets/sprites/ con fallback automático.
#
# Dos tipos de carga:
#   SpriteSheetLoader : PNG único con múltiples frames en grilla (unidades, tiles, UI)
#   FxLoader          : Carpeta de frames separados (frame0000.png, frame0001.png, ...)
#
# Tamaños display canónicos:
#   Unidad en mapa   : 32×32 px  (original 16×16, escala ×2)
#   Tile terreno     : 32×32 px  (original 16×16, escala ×2)
#   Portrait HUD     : 48×48 px  (fallback generado)
#   Portrait diálogo : 96×96 px  (fallback generado)
#   Ícono UI         : 16×16 px
#   FX               : 48×48 px

import os
import glob
import pygame
from typing import Optional, List

_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPRITES = os.path.join(_ROOT, "assets", "sprites")

# Tamaños display canónicos
SIZE_UNIT_MAP       = (32, 32)
SIZE_UNIT_MAP_LARGE = (64, 64)   # Para unidades grandes (dragones, mamuts, etc.)
SIZE_UNIT_BATTLE    = (96, 96)
SIZE_PORTRAIT_HUD   = (48, 48)
SIZE_PORTRAIT_DLG   = (96, 96)
SIZE_TILE           = (32, 32)
SIZE_ICON           = (16, 16)
SIZE_FX             = (48, 48)

# Tamaño original de cada frame en el pack (16×16 mini world sprites)
FRAME_ORIGINAL       = 16
FRAME_ORIGINAL_LARGE = 32   # Sprites grandes: 32×32 px por frame

# IDs de sprites cuyos frames son 32×32 y deben mostrarse a 64×64 en el mapa.
# Se confirma por las dimensiones reales del PNG (128×256, 64×128, 96×128, 96×112).
LARGE_SPRITE_IDS: set = {
    "dragon", "black_dragon", "blue_dragon", "white_dragon", "yellow_dragon",
    "mammoth", "yeti", "minotaur",
}

# Cache global: evita recargar el mismo archivo cada frame
_cache: dict = {}


# =================================================
# MAPA EXPLÍCITO: sprite_id → ruta relativa a _SPRITES
# =================================================
# Las rutas usan os.path.join para compatibilidad multiplataforma.

UNIT_SPRITE_PATHS = {
    # ---------- Aliados — Champions ----------
    "kael":   os.path.join("units", "allies", "Champions", "Kael",   "map", "Kael.png"),
    "lyra":   os.path.join("units", "allies", "Champions", "Lyra",   "map", "Lyra.png"),
    "ryn":    os.path.join("units", "allies", "Champions", "Ryn",    "map", "Ryn.png"),
    "theron": os.path.join("units", "allies", "Champions", "Theron", "map", "Katan.png"),
    "mira":   os.path.join("units", "allies", "Champions", "Mira",   "map", "Grum.png"),
    "zeph":   os.path.join("units", "allies", "Champions", "Zeph",   "map", "Okomo.png"),
    "aldric": os.path.join("units", "allies", "Champions", "Aldric", "map", "B\u00f6rg.png"),

    # ---------- Aliados — Soldados (variante Lime como default) ----------
    "swordsman": os.path.join("units", "allies", "Soldiers", "Melee",  "LimeMelee",  "SwordsmanLime.png"),
    "axeman":    os.path.join("units", "allies", "Soldiers", "Melee",  "CyanMelee",  "AxemanCyan.png"),
    "spearman":  os.path.join("units", "allies", "Soldiers", "Melee",  "RedMelee",   "SpearmanRed.png"),
    "assassin":  os.path.join("units", "allies", "Soldiers", "Melee",  "PurpleMelee","AssasinPurple.png"),
    "bowman":    os.path.join("units", "allies", "Soldiers", "Ranged", "CyanRanged", "BowmanCyan.png"),
    "mage_ally": os.path.join("units", "allies", "Soldiers", "Ranged", "LimeRanged", "MageLime.png"),
    "knight":    os.path.join("units", "allies", "Soldiers", "Mounted","CyanKnight.png"),

    # ---------- Enemigos — Orcos y Goblins ----------
    "bandit":         os.path.join("units", "enemies", "Orcs",    "ClubGoblin.png"),
    "goblin":         os.path.join("units", "enemies", "Orcs",    "ClubGoblin.png"),
    "goblin_club":    os.path.join("units", "enemies", "Orcs",    "ClubGoblin.png"),
    "goblin_spear":   os.path.join("units", "enemies", "Orcs",    "SpearGoblin.png"),
    "goblin_archer":  os.path.join("units", "enemies", "Orcs",    "ArcherGoblin.png"),
    "farmer_goblin":  os.path.join("units", "enemies", "Orcs",    "FarmerGoblin.png"),
    "kamikaze_goblin":os.path.join("units", "enemies", "Orcs",    "KamikazeGoblin.png"),
    "orc":            os.path.join("units", "enemies", "Orcs",    "Orc.png"),
    "orc_shaman":     os.path.join("units", "enemies", "Orcs",    "OrcShaman.png"),
    "orc_mage":       os.path.join("units", "enemies", "Orcs",    "OrcMage.png"),
    "minotaur":       os.path.join("units", "enemies", "Orcs",    "Minotaur.png"),

    # ---------- Enemigos — No Muertos ----------
    "dark_mage":  os.path.join("units", "enemies", "Undead",  "Necromancer.png"),
    "skeleton":   os.path.join("units", "enemies", "Undead",  "Skeleton-Soldier.png"),
    "necromancer":os.path.join("units", "enemies", "Undead",  "Necromancer.png"),

    # ---------- Enemigos — Demonios ----------
    "demon":          os.path.join("units", "enemies", "Demons",  "RedDemon.png"),
    "armoured_demon": os.path.join("units", "enemies", "Demons",  "ArmouredRedDemon.png"),
    "purple_demon":   os.path.join("units", "enemies", "Demons",  "PurpleDemon.png"),

    # ---------- Enemigos — Dragones ----------
    "dragon":       os.path.join("units", "enemies", "Dragons", "RedDragon.png"),
    "black_dragon": os.path.join("units", "enemies", "Dragons", "BlackDragon.png"),
    "blue_dragon":  os.path.join("units", "enemies", "Dragons", "BlueDragon.png"),
    "white_dragon": os.path.join("units", "enemies", "Dragons", "WhiteDragon.png"),
    "yellow_dragon":os.path.join("units", "enemies", "Dragons", "YellowDragon.png"),

    # ---------- Enemigos — Frostborn ----------
    "mammoth": os.path.join("units", "enemies", "Frostborn", "Mammoth.png"),
    "wendigo": os.path.join("units", "enemies", "Frostborn", "Wendigo.png"),
    "yeti":    os.path.join("units", "enemies", "Frostborn", "Yeti.png"),

    # ---------- Enemigos — Animales Gigantes ----------
    "giant_crab": os.path.join("units", "enemies", "GiantAnimals", "GiantCrab.png"),

    # ---------- Enemigos — Limos ----------
    "slime":       os.path.join("units", "enemies", "Slimes",  "Slime.png"),
    "slime_blue":  os.path.join("units", "enemies", "Slimes",  "SlimeBlue.png"),
    "mega_slime":  os.path.join("units", "enemies", "Slimes",  "MegaSlimeGreen.png"),
    "king_slime":  os.path.join("units", "enemies", "Slimes",  "KingSlimeGreen.png"),

    # ---------- Enemigos — Piratas ----------
    "pirate":         os.path.join("units", "enemies", "Pirates", "PirateGrunt.png"),
    "pirate_captain": os.path.join("units", "enemies", "Pirates", "PirateCaptain.png"),
    "pirate_gunner":  os.path.join("units", "enemies", "Pirates", "PirateGunner.png"),

    "dummy": None,  # sin sprite → fallback siempre
}

TILE_SPRITE_PATHS = {
    0: os.path.join("tiles", "Ground",  "Grass.png"),              # Hierba
    1: os.path.join("tiles", "Nature",  "Trees.png"),              # Bosque
    2: os.path.join("tiles", "Ground",  "Cliff.png"),              # Muro/Montaña
    3: os.path.join("tiles", "Ground",  "Shore.png"),              # Agua
    4: os.path.join("tiles", "Ground",  "DeadGrass.png"),          # Hierba seca/arena
    5: os.path.join("tiles", "Nature",  "Rocks.png"),              # Rocas pequeñas
    6: os.path.join("tiles", "Ground",  "Cliff-Water.png"),        # Agua profunda
    7: os.path.join("tiles", "Ground",  "Winter.png"),             # Suelo nevado
    8: os.path.join("tiles", "Nature",  "WinterTrees.png"),        # Árboles invernales
    9: os.path.join("tiles", "Nature",  "DeadTrees.png"),          # Árboles muertos
}

# FX: clave lógica → subcarpeta relativa a _SPRITES
FX_PATHS = {
    "attack":     os.path.join("fx", "Impacts",        "symmetrical_impact_001", "symmetrical_impact_001_small_yellow"),
    "heal":       os.path.join("fx", "Fantasy Spells", "spell_heal_001",          "spell_heal_001_small_red"),
    "critical":   os.path.join("fx", "Explosions",     "epic_explosion_001",      "epic_explosion_001_small_orange"),
    "skill":      os.path.join("fx", "Fantasy Spells", "spell_attack_up_001",     "spell_attack_up_001_small_red"),
    "death":      os.path.join("fx", "Fantasy Spells", "spell_death_001",         "spell_death_001_small_red"),
    "awakening":  os.path.join("fx", "Lightning",      "lightning_burst_001",     "lightning_burst_001_small_violet"),
    "poison":     os.path.join("fx", "Fantasy Spells", "spell_poison_001",        "spell_poison_001_small_green"),
    "level_up":   os.path.join("fx", "Magic Bursts",   "round_sparkle_burst_001","round_sparkle_burst_001_small_yellow"),
    "defense_up": os.path.join("fx", "Fantasy Spells", "spell_defense_up_001",   "spell_defense_up_001_small_blue"),
    "haste":      os.path.join("fx", "Fantasy Spells", "spell_haste_001",        "spell_haste_001_small_green"),
    "absorb":     os.path.join("fx", "Fantasy Spells", "spell_absorb_001",       "spell_absorb_001_small_violet"),
    "explosion":  os.path.join("fx", "Explosions",     "stylized_explosion_001", "stylized_explosion_001_small_yellow"),
    "lightning":  os.path.join("fx", "Lightning",      "lightning_strike_001",   "lightning_strike_001_small_violet"),
    "smoke":      os.path.join("fx", "Smoke Bursts",   "symmetrical_smoke_burst_001","symmetrical_smoke_burst_001_small_brown"),
}


# =================================================
# CLASE SpriteSheetLoader
# =================================================

class SpriteSheetLoader:
    """
    Carga un spritesheet PNG y corta frames individuales.
    frame_w, frame_h: tamaño original de cada frame (ej. 16×16).
    """

    def __init__(self, path: str, frame_w: int = FRAME_ORIGINAL, frame_h: int = FRAME_ORIGINAL):
        self.sheet   = pygame.image.load(path).convert_alpha()
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.sw, self.sh = self.sheet.get_size()

    def get_frame(self, col: int, row: int, scale_to: Optional[tuple] = None) -> pygame.Surface:
        """Recorta el frame en (col, row) y lo escala opcionalmente."""
        x = col * self.frame_w
        y = row * self.frame_h
        # Si la hoja es más pequeña, usamos la hoja completa
        if x + self.frame_w > self.sw or y + self.frame_h > self.sh:
            frame = self.sheet
        else:
            frame = self.sheet.subsurface(pygame.Rect(x, y, self.frame_w, self.frame_h))
        if scale_to:
            return pygame.transform.scale(frame, scale_to)
        return frame.copy()

    def get_animation(self, row: int, frame_count: int,
                      scale_to: Optional[tuple] = None) -> List[pygame.Surface]:
        """Retorna todos los frames de una fila como lista."""
        return [self.get_frame(col, row, scale_to) for col in range(frame_count)]

    def get_full_scaled(self, scale_to: tuple) -> pygame.Surface:
        """Escala toda la hoja (útil para tiles de frame único)."""
        return pygame.transform.scale(self.sheet, scale_to)

    def frames_in_row(self) -> int:
        return max(1, self.sw // self.frame_w)

    def rows_in_sheet(self) -> int:
        return max(1, self.sh // self.frame_h)


# =================================================
# CLASE FxLoader
# =================================================

class FxLoader:
    """
    Carga animaciones FX desde carpetas de frames separados.
    Formato esperado: frame0000.png, frame0001.png, ...
    """

    @staticmethod
    def load(folder_rel: str, scale_to: tuple = SIZE_FX) -> List[pygame.Surface]:
        """
        Carga todos los frames de la carpeta y los retorna ordenados.
        Usa glob para encontrar archivos frame*.png sin loop con contador.
        Retorna [] si la carpeta no existe o no tiene frames válidos.
        """
        full_dir = os.path.join(_SPRITES, folder_rel)
        if not os.path.isdir(full_dir):
            return []

        pattern = os.path.join(full_dir, "frame*.png")
        paths   = sorted(glob.glob(pattern))
        if not paths:
            return []

        frames: List[pygame.Surface] = []
        for path in paths:
            try:
                img = pygame.image.load(path).convert_alpha()
                frames.append(pygame.transform.scale(img, scale_to))
            except Exception as e:
                print(f"[FxLoader] Error cargando {os.path.basename(path)}: {e}")

        return frames


# =================================================
# HELPERS INTERNOS
# =================================================

def _cached(key: str, builder):
    if key not in _cache:
        _cache[key] = builder()
    return _cache[key]


def _load_sheet(rel_path: str,
               frame_w: int = FRAME_ORIGINAL,
               frame_h: int = FRAME_ORIGINAL) -> Optional[SpriteSheetLoader]:
    full = os.path.join(_SPRITES, rel_path)
    if not os.path.exists(full):
        return None
    try:
        return SpriteSheetLoader(full, frame_w, frame_h)
    except Exception as e:
        print(f"[SpriteLoader] Error cargando sheet '{rel_path}': {e}")
        return None


# =================================================
# FALLBACKS — figuras generadas por código
# =================================================
# Cada tipo de unidad tiene forma distinta para ser reconocible sin sprites.

_UNIT_FALLBACK_SHAPES = {
    # Aliados — Champions
    "kael":   {"shape": "diamond",     "color": (50,  80, 220)},
    "lyra":   {"shape": "cross",       "color": (220, 220,  80)},
    "ryn":    {"shape": "triangle_up", "color": (80,  200,  80)},
    "theron": {"shape": "triangle_up", "color": (80,  200,  80)},
    "mira":   {"shape": "diamond",     "color": (180,  80, 180)},
    "zeph":   {"shape": "cross",       "color": (60,  200, 200)},
    "aldric": {"shape": "diamond",     "color": (220, 140,  40)},
    # Aliados — Soldados
    "swordsman": {"shape": "triangle_up", "color": (60,  100, 200)},
    "axeman":    {"shape": "triangle_up", "color": (40,  160, 200)},
    "bowman":    {"shape": "triangle_up", "color": (40,  180, 100)},
    "knight":    {"shape": "diamond",     "color": (80,   80, 220)},
    # Enemigos — Orcos/Goblins
    "bandit":          {"shape": "triangle_down", "color": (200,  60,  60)},
    "goblin":          {"shape": "triangle_down", "color": (160, 100,  40)},
    "goblin_club":     {"shape": "triangle_down", "color": (180,  80,  20)},
    "goblin_spear":    {"shape": "triangle_down", "color": (160, 100,  40)},
    "goblin_archer":   {"shape": "triangle_down", "color": (140, 100,  30)},
    "farmer_goblin":   {"shape": "triangle_down", "color": (120, 130,  40)},
    "kamikaze_goblin": {"shape": "triangle_down", "color": (220,  80,  20)},
    "orc":             {"shape": "square",        "color": (160,  40,  40)},
    "orc_shaman":      {"shape": "diamond",       "color": (100,  30, 150)},
    "orc_mage":        {"shape": "diamond",       "color": (120,  40, 160)},
    "minotaur":        {"shape": "square",        "color": (140,  50,  20)},
    # Enemigos — No Muertos
    "dark_mage":  {"shape": "diamond", "color": (120,  20, 180)},
    "skeleton":   {"shape": "cross",   "color": (180, 180, 180)},
    "necromancer":{"shape": "diamond", "color": ( 80,   0, 120)},
    # Enemigos — Demonios
    "demon":          {"shape": "triangle_down", "color": (200,  20,  20)},
    "armoured_demon": {"shape": "square",        "color": (160,  10,  10)},
    "purple_demon":   {"shape": "triangle_down", "color": (140,  20, 160)},
    # Enemigos — Dragones
    "dragon":       {"shape": "square", "color": (180,  30,  30)},
    "black_dragon": {"shape": "square", "color": ( 30,  30,  30)},
    "blue_dragon":  {"shape": "square", "color": ( 30,  60, 200)},
    "white_dragon": {"shape": "diamond","color": (230, 230, 230)},
    "yellow_dragon":{"shape": "square", "color": (200, 180,  20)},
    # Enemigos — Frostborn
    "mammoth": {"shape": "square",  "color": (180, 200, 220)},
    "wendigo": {"shape": "diamond", "color": (140, 180, 220)},
    "yeti":    {"shape": "square",  "color": (200, 220, 240)},
    # Enemigos — Animales
    "giant_crab": {"shape": "square", "color": (200, 100,  40)},
    # Enemigos — Limos
    "slime":      {"shape": "circle", "color": ( 60, 200,  60)},
    "slime_blue": {"shape": "circle", "color": ( 60, 130, 220)},
    "mega_slime": {"shape": "circle", "color": ( 40, 180,  40)},
    "king_slime": {"shape": "square", "color": ( 20, 150,  20)},
    # Enemigos — Piratas
    "pirate":         {"shape": "triangle_down", "color": ( 30, 100, 160)},
    "pirate_captain": {"shape": "diamond",       "color": ( 20,  70, 140)},
    "pirate_gunner":  {"shape": "triangle_down", "color": ( 20,  80, 140)},
    "dummy":          {"shape": "circle",        "color": (120, 120, 120)},
}
_DEFAULT_ALLY  = {"shape": "triangle_up",   "color": (60,  100, 220)}
_DEFAULT_ENEMY = {"shape": "triangle_down", "color": (200,  60,  60)}


def _get_fallback_info(sprite_id: str, bando: str, color_override=None) -> dict:
    info = dict(_UNIT_FALLBACK_SHAPES.get(
        sprite_id,
        _DEFAULT_ALLY if bando == "aliado" else _DEFAULT_ENEMY
    ))
    if color_override:
        info["color"] = tuple(color_override)
    return info


def _fallback_unit_map(color: tuple, shape: str = "circle") -> pygame.Surface:
    surf = pygame.Surface(SIZE_UNIT_MAP, pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))
    cx, cy, r = 16, 16, 13
    dark = tuple(max(0, c - 60) for c in color)

    if shape == "diamond":
        pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, dark, pts, 2)
    elif shape == "cross":
        pygame.draw.rect(surf, color, (cx - 4, cy - r, 8, r * 2))
        pygame.draw.rect(surf, color, (cx - r, cy - 4, r * 2, 8))
        pygame.draw.rect(surf, dark,  (cx - 4, cy - r, 8, r * 2), 1)
        pygame.draw.rect(surf, dark,  (cx - r, cy - 4, r * 2, 8), 1)
    elif shape == "triangle_up":
        pts = [(cx, cy - r), (cx + r, cy + r - 2), (cx - r, cy + r - 2)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, dark, pts, 2)
    elif shape == "triangle_down":
        pts = [(cx, cy + r), (cx + r, cy - r + 2), (cx - r, cy - r + 2)]
        pygame.draw.polygon(surf, color, pts)
        pygame.draw.polygon(surf, dark, pts, 2)
    elif shape == "square":
        pygame.draw.rect(surf, color, (cx - r, cy - r, r * 2, r * 2))
        pygame.draw.rect(surf, dark,  (cx - r, cy - r, r * 2, r * 2), 2)
    else:  # circle
        pygame.draw.circle(surf, color, (cx, cy), r)
        pygame.draw.circle(surf, dark,  (cx, cy), r, 2)

    return surf


def _fallback_portrait_hud(color: tuple, letter: str = "?") -> pygame.Surface:
    surf = pygame.Surface(SIZE_PORTRAIT_HUD, pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (2, 2, 44, 44), border_radius=8)
    pygame.draw.rect(surf, (255, 255, 255, 80), (2, 2, 44, 44), 2, border_radius=8)
    try:
        font = pygame.font.SysFont("Arial", 22, bold=True)
        txt  = font.render(letter.upper(), True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=(24, 24)))
    except Exception:
        pass
    return surf


def _fallback_portrait_dlg(color: tuple, letter: str = "?") -> pygame.Surface:
    surf = pygame.Surface(SIZE_PORTRAIT_DLG, pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (3, 3, 90, 90), border_radius=12)
    pygame.draw.rect(surf, (255, 255, 255, 80), (3, 3, 90, 90), 2, border_radius=12)
    try:
        font = pygame.font.SysFont("Arial", 44, bold=True)
        txt  = font.render(letter.upper(), True, (255, 255, 255))
        surf.blit(txt, txt.get_rect(center=(48, 48)))
    except Exception:
        pass
    return surf


def _fallback_icon(color: tuple) -> pygame.Surface:
    surf = pygame.Surface(SIZE_ICON, pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, 16, 16), border_radius=3)
    pygame.draw.rect(surf, (255, 255, 255), (0, 0, 16, 16), 1, border_radius=3)
    return surf


# =================================================
# API PÚBLICA — Unidades
# =================================================

def get_unit_map_frames(sprite_id: str, bando: str = "aliado",
                        color_override=None) -> List[pygame.Surface]:
    """
    Retorna lista de Surfaces para la animación idle en el mapa.
    - Sprites normales  → frames 16×16, display 32×32.
    - Sprites grandes   → frames 32×32, display 64×64 (dragones, mamuts, etc.)
    La lista tiene entre 1 y 4 frames para animación cíclica.
    """
    key = f"unit_frames_{bando}_{sprite_id}"

    def build():
        rel = UNIT_SPRITE_PATHS.get(sprite_id)
        if rel:
            is_large   = sprite_id in LARGE_SPRITE_IDS
            fw = fh    = FRAME_ORIGINAL_LARGE if is_large else FRAME_ORIGINAL
            display    = SIZE_UNIT_MAP_LARGE  if is_large else SIZE_UNIT_MAP
            sheet = _load_sheet(rel, fw, fh)
            if sheet:
                n = min(sheet.frames_in_row(), 4)
                frames = sheet.get_animation(row=0, frame_count=n, scale_to=display)
                if frames:
                    return frames

        info = _get_fallback_info(sprite_id, bando, color_override)
        # Fallback para sprites grandes: generar en tamaño 64×64
        if sprite_id in LARGE_SPRITE_IDS:
            s = pygame.Surface(SIZE_UNIT_MAP_LARGE, pygame.SRCALPHA)
            small = _fallback_unit_map(info["color"], info["shape"])
            s.blit(pygame.transform.scale(small, SIZE_UNIT_MAP_LARGE), (0, 0))
            return [s]
        return [_fallback_unit_map(info["color"], info["shape"])]

    return _cached(key, build)


def is_large_sprite(sprite_id: str) -> bool:
    """Retorna True si el sprite es de tamaño grande (64×64 en el mapa)."""
    return sprite_id in LARGE_SPRITE_IDS


def get_unit_map_sprite(sprite_id: str, bando: str = "aliado",
                        color_override=None) -> pygame.Surface:
    """Retorna el primer frame (para código que no necesita animación)."""
    return get_unit_map_frames(sprite_id, bando, color_override)[0]


def get_portrait_hud(sprite_id: str, bando: str = "aliado",
                     color_override=None, letter: str = "?") -> pygame.Surface:
    """Retorna Surface 48×48 para el panel de info del HUD."""
    key = f"portrait48_{bando}_{sprite_id}_{letter}"

    def build():
        info = _get_fallback_info(sprite_id, bando, color_override)
        return _fallback_portrait_hud(info["color"], letter)

    return _cached(key, build)


def get_portrait_dialogue(sprite_id: str, bando: str = "aliado",
                          color_override=None, letter: str = "?") -> pygame.Surface:
    """Retorna Surface 96×96 para el cuadro de diálogo."""
    key = f"portrait96_{bando}_{sprite_id}_{letter}"

    def build():
        info = _get_fallback_info(sprite_id, bando, color_override)
        return _fallback_portrait_dlg(info["color"], letter)

    return _cached(key, build)


# =================================================
# API PÚBLICA — Tiles
# =================================================

def get_tile_sprite(tile_id: int) -> Optional[pygame.Surface]:
    """
    Retorna Surface 32×32 para un tipo de terreno.
    Toma el primer frame (0, 0) del spritesheet como tile base.
    Retorna None si no existe (renderer usa color sólido como fallback).
    """
    key = f"tile_{tile_id}"

    def build():
        rel = TILE_SPRITE_PATHS.get(tile_id)
        if not rel:
            return None
        sheet = _load_sheet(rel)
        if not sheet:
            return None
        return sheet.get_frame(0, 0, scale_to=SIZE_TILE)

    return _cached(key, build)


# =================================================
# API PÚBLICA — FX
# =================================================

def get_fx_frames(fx_key: str, scale_to: tuple = SIZE_FX) -> List[pygame.Surface]:
    """
    Retorna lista de Surfaces para una animación FX.
    Retorna [] si no existe (FXManager usa texto flotante como fallback).
    """
    cache_key = f"fx_{fx_key}_{scale_to[0]}x{scale_to[1]}"

    def build():
        folder = FX_PATHS.get(fx_key)
        if not folder:
            return []
        return FxLoader.load(folder, scale_to)

    return _cached(cache_key, build)


# =================================================
# API PÚBLICA — UI
# =================================================

def get_ui_sprite(name: str, cell_x: int = 0, cell_y: int = 0,
                  frame_w: int = 16, frame_h: int = 16,
                  scale_to: Optional[tuple] = None) -> Optional[pygame.Surface]:
    """
    Extrae un frame del spritesheet de UI.
    name: nombre del archivo sin extensión (ej. 'BoxSelector').
    cell_x, cell_y: posición en la grilla del spritesheet.
    """
    key = f"ui_{name}_{cell_x}_{cell_y}_{scale_to}"

    def build():
        rel  = os.path.join("ui", f"{name}.png")
        full = os.path.join(_SPRITES, rel)
        if not os.path.exists(full):
            return None
        try:
            loader = SpriteSheetLoader(full, frame_w, frame_h)
            return loader.get_frame(cell_x, cell_y, scale_to)
        except Exception as e:
            print(f"[SpriteLoader] Error UI sprite '{name}': {e}")
            return None

    return _cached(key, build)


def get_icon(icon_id: str, color: tuple = (200, 200, 200)) -> pygame.Surface:
    """Retorna Surface 16×16 para íconos de inventario/habilidades."""
    key = f"icon_{icon_id}"
    return _cached(key, lambda: _fallback_icon(color))


def clear_cache():
    """Limpia el cache completo (útil al reiniciar partida)."""
    _cache.clear()
