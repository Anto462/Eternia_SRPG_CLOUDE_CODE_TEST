# systems/dialogue_system.py
# -------------------------------------------------
# Sistema de diálogo de batalla estilo Fire Emblem.
# Carga frases desde data/dialogue/quotes.json.
# Fallback a frases hardcodeadas si el JSON no existe.

import random
from loaders.data_loader import load_quotes


# =================================================
# FRASES POR DEFECTO
# =================================================

_DEFAULT_QUOTES = {
    "HERO_ALLY": {
        "attack":    ["¡Por Eternia!", "No te me escapas.", "¡Vamos con todo!"],
        "skill":     ["¡Ahora!", "Tiempo de rematar."],
        "crit":      ["¡AHORA!", "¡Sin piedad!"],
        "kill":      ["Se acabó.", "Caíste."],
        "death":     ["No… todavía no…"],
        "heal":      ["Gracias."],
        "awakening": ["¡AWAKENING!", "¡Siento el poder!"],
    },
    "CLERIC_ALLY": {
        "attack":    ["No quería hacer esto…", "Perdóname."],
        "skill":     ["Resiste…", "Te curo, rápido."],
        "crit":      ["¡No me queda otra!"],
        "kill":      ["Que descansen en paz."],
        "death":     ["Que… los dioses me perdonen…"],
        "heal":      ["Aguanta.", "Ya estás mejor."],
        "awakening": ["¡Gracia Divina!"],
    },
    "BANDIT_ENEMY": {
        "attack":    ["Dame todo lo que tengas.", "¡Te partí!"],
        "kill":      ["¡Ja!"],
        "death":     ["¡Malditos…!"],
    },
    "ORC_ENEMY": {
        "attack":    ["¡APLASTO!", "¡ORCO FUERTE!"],
        "kill":      ["¡ORCO GANA!"],
        "death":     ["¡Orco… caer…!"],
    },
    "MAGE_ENEMY": {
        "attack":    ["El oscuro poder te consume.", "Resistir es inútil."],
        "skill":     ["¡Rayo Oscuro!"],
        "kill":      ["Polvo serás."],
        "death":     ["Esto… no es posible…"],
    },
}


class DialogueSystem:
    def __init__(self):
        self.active  = False
        self.timer   = 0.0
        self.speaker = ""
        self.text    = ""
        self.unit_id = None

        # Construir catálogo: default + JSON
        self.quotes = {**_DEFAULT_QUOTES}
        json_q = load_quotes()
        if json_q:
            # Merge: agrega eventos nuevos y extiende listas existentes
            for uid, events in json_q.items():
                if uid not in self.quotes:
                    self.quotes[uid] = {}
                for event, lines in events.items():
                    existing = self.quotes[uid].get(event, [])
                    # Dedup
                    merged = list(dict.fromkeys(existing + lines))
                    self.quotes[uid][event] = merged

    def trigger(self, unit, event: str, target=None, skill=None, duration: float = 2.5):
        """
        Dispara una línea de diálogo.
        unit: Unidad que habla
        event: "attack" | "skill" | "crit" | "kill" | "death" | "heal" | "awakening"
        """
        if not unit:
            return

        uid = getattr(unit, "unit_id", None) or getattr(unit, "nombre", "UNKNOWN")
        pool = self.quotes.get(uid, {}).get(event, [])

        if not pool:
            self.active = False
            return

        base = random.choice(pool)
        if skill:
            base = f"{base} [{skill.nombre}]"

        self.speaker = unit.nombre
        self.text    = base
        self.unit_id = uid
        self.active  = True
        self.timer   = duration

    def update(self, dt: float):
        if not self.active:
            return
        self.timer -= dt
        if self.timer <= 0:
            self.active = False
            self.timer  = 0

    def get_render_payload(self) -> dict:
        return {
            "active":  self.active,
            "speaker": self.speaker,
            "text":    self.text,
            "unit_id": self.unit_id,
        }
