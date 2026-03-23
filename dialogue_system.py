# dialogue_system.py
# -------------------------------------------------
# Quotes estilo FE (minimal)
# - trigger(unit, event, target=None, skill=None)
# - update(dt)
# - get_render_payload()

import random

class DialogueSystem:
    def __init__(self):
        self.active = False
        self.timer = 0.0
        self.speaker = ""
        self.text = ""

        # Quotes por unit_id y evento
        self.QUOTES = {
            "HERO_ALLY": {
                "attack": ["¡Por Eternia!", "No te me escapas.", "Vamos con todo."],
                "skill":  ["¡Ahora!", "Tiempo de rematar."],
            },
            "CLERIC_ALLY": {
                "attack": ["No quería hacer esto…", "Perdóname."],
                "skill":  ["Resiste…", "Te curo, rápido."],
            },
            "BANDIT_ENEMY": {
                "attack": ["Dame todo lo que tengas.", "¡Te partí!"],
            },
        }

    def trigger(self, unit, event, target=None, skill=None):
        if not unit:
            print("No unit to trigger dialogue")
            return

        # unit_id opcional (si lo tienes en Unidad)
        unit_id = getattr(unit, "unit_id", None)

        # fallback: si no existe unit_id, usa nombre como llave (o pon "HERO_ALLY")
        key = unit_id or getattr(unit, "nombre", "UNKNOWN")

        # intenta sacar lista de quotes
        pool = self.QUOTES.get(key, {}).get(event, [])
        if not pool:
            # si no hay quote definido, no lo mostramos (evita cajas vacías)
            self.active = False
            return

        # speaker (nombre ingame)
        self.speaker = unit.nombre

        # texto base random
        base = random.choice(pool)

        # opcional: añade info del target (sin hacerlo obligatorio)
        if target:
            base = f"{base}"

        # opcional: skills
        if skill:
            base = f"{base} [{skill.nombre}]"

        self.text = base
        self.active = True
        self.timer = 2.5  # segundos en pantalla

        print(f"Dialogue triggered for: {key} {unit.nombre}")

    def update(self, dt):
        if not self.active:
            return
        self.timer -= dt
        if self.timer <= 0:
            self.active = False
            self.timer = 0

    def get_render_payload(self):
        return {
            "active": self.active,
            "speaker": self.speaker,
            "text": self.text,
        }
