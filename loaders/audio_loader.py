# loaders/audio_loader.py
# -------------------------------------------------
# AudioLoader: gestiona SFX con pygame.mixer.
# Waveform usada: Square (más retro/pixel).
# BGM: soporte listo para cuando se agreguen archivos .ogg en audio/bgm/.

import os
import pygame

_ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SFX_DIR = os.path.join(_ROOT, "assets", "audio", "sfx")
_BGM_DIR = os.path.join(_ROOT, "assets", "audio", "bgm")

# Waveform preferida para todos los SFX
_WAVE = "Square"

# Mapeo evento lógico → nombre de archivo real
# Formato: "JDSherbert - Pixel UI SFX Pack - {Tipo} {Num} ({Wave}).wav"
_SFX_MAP: dict = {
    # Cursor / navegación
    "cursor_move":   f"JDSherbert - Pixel UI SFX Pack - Cursor 1 ({_WAVE}).wav",
    "cursor_move2":  f"JDSherbert - Pixel UI SFX Pack - Cursor 2 ({_WAVE}).wav",
    "cursor_move3":  f"JDSherbert - Pixel UI SFX Pack - Cursor 3 ({_WAVE}).wav",
    # Confirmación / selección
    "menu_confirm":  f"JDSherbert - Pixel UI SFX Pack - Select 1 ({_WAVE}).wav",
    "menu_select":   f"JDSherbert - Pixel UI SFX Pack - Select 2 ({_WAVE}).wav",
    # Cancelar
    "menu_cancel":   f"JDSherbert - Pixel UI SFX Pack - Cancel 2 ({_WAVE}).wav",
    # Apertura / cierre de menú
    "menu_open":     f"JDSherbert - Pixel UI SFX Pack - Popup Open 1 ({_WAVE}).wav",
    "menu_close":    f"JDSherbert - Pixel UI SFX Pack - Popup Close 1 ({_WAVE}).wav",
    # Errores
    "error":         f"JDSherbert - Pixel UI SFX Pack - Error 1 ({_WAVE}).wav",
    "error2":        f"JDSherbert - Pixel UI SFX Pack - Error 2 ({_WAVE}).wav",

    # Alias semánticos para el juego
    "unit_select":   f"JDSherbert - Pixel UI SFX Pack - Select 1 ({_WAVE}).wav",
    "unit_move":     f"JDSherbert - Pixel UI SFX Pack - Cursor 2 ({_WAVE}).wav",
    "unit_wait":     f"JDSherbert - Pixel UI SFX Pack - Cursor 1 ({_WAVE}).wav",
    "attack":        f"JDSherbert - Pixel UI SFX Pack - Select 2 ({_WAVE}).wav",
    "no_mp":         f"JDSherbert - Pixel UI SFX Pack - Error 1 ({_WAVE}).wav",
    "no_move":       f"JDSherbert - Pixel UI SFX Pack - Error 2 ({_WAVE}).wav",
    "level_up":      f"JDSherbert - Pixel UI SFX Pack - Popup Open 1 ({_WAVE}).wav",
    "awakening":     f"JDSherbert - Pixel UI SFX Pack - Select 2 ({_WAVE}).wav",
    "conquer":       f"JDSherbert - Pixel UI SFX Pack - Popup Open 1 ({_WAVE}).wav",
    "turn_start":    f"JDSherbert - Pixel UI SFX Pack - Popup Open 1 ({_WAVE}).wav",
    "turn_end":      f"JDSherbert - Pixel UI SFX Pack - Popup Close 1 ({_WAVE}).wav",
}


class AudioLoader:
    """
    Carga y reproduce SFX con pygame.mixer.
    Instanciar una sola vez en main.py y pasar la referencia al GameState.
    """

    def __init__(self, sfx_volume: float = 0.55):
        self._ok   = False
        self._vol  = sfx_volume
        self._sounds: dict         = {}
        self._current_bgm: str     = ""

        if not pygame.get_init():
            return

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            self._ok = True
            self._preload_sfx()
            loaded = len(self._sounds)
            print(f"[AudioLoader] {loaded}/{len(_SFX_MAP)} SFX cargados.")
        except Exception as e:
            print(f"[AudioLoader] No se pudo inicializar mixer: {e}")

    def _preload_sfx(self):
        loaded_files: dict = {}   # path → Sound (evita cargar el mismo archivo dos veces)

        for key, filename in _SFX_MAP.items():
            path = os.path.join(_SFX_DIR, filename)
            if not os.path.exists(path):
                continue
            if path not in loaded_files:
                try:
                    snd = pygame.mixer.Sound(path)
                    snd.set_volume(self._vol)
                    loaded_files[path] = snd
                except Exception as e:
                    print(f"[AudioLoader] Error cargando '{filename}': {e}")
                    continue
            self._sounds[key] = loaded_files[path]

    # --------------------------------------------------
    # API pública
    # --------------------------------------------------

    def play(self, event: str):
        """Reproduce el SFX asociado al evento. Silencioso si no existe."""
        if not self._ok:
            return
        snd = self._sounds.get(event)
        if snd:
            snd.play()

    def set_sfx_volume(self, vol: float):
        self._vol = max(0.0, min(1.0, vol))
        for snd in self._sounds.values():
            snd.set_volume(self._vol)

    def play_bgm(self, filename: str, loops: int = -1, volume: float = 0.4):
        """
        Reproduce un archivo de música de fondo desde audio/bgm/.
        Si el archivo no existe, no hace nada (sin error).
        """
        if not self._ok:
            return
        if filename == self._current_bgm:
            return
        path = os.path.join(_BGM_DIR, filename)
        if not os.path.exists(path):
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(loops)
            self._current_bgm = filename
        except Exception as e:
            print(f"[AudioLoader] Error BGM '{filename}': {e}")

    def stop_bgm(self):
        if self._ok:
            pygame.mixer.music.stop()
            self._current_bgm = ""

    def loaded_events(self) -> list:
        """Retorna lista de eventos con SFX cargado (para debug)."""
        return sorted(self._sounds.keys())
