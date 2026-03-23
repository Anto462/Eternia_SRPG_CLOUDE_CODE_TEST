# core/combat.py
# -------------------------------------------------
# Sistema de combate mejorado:
#   - Hit rate con precisión y esquive
#   - Críticos
#   - Triángulo de armas (espada/hacha/lanza)
#   - Doble ataque por velocidad
#   - Efectos de estado post-combate
#
# No dibuja nada. Solo lógica + callbacks FX.

import random
import constants as C


# =================================================
# TRIÁNGULO DE ARMAS
# =================================================
# Bonus al tener ventaja: +15 precisión, +1 daño
# Penalti al tener desventaja: -15 precisión, -1 daño

_WEAPON_TRIANGLE = {
    "espada": {"ventaja": "hacha",  "desventaja": "lanza"},
    "hacha":  {"ventaja": "lanza",  "desventaja": "espada"},
    "lanza":  {"ventaja": "espada", "desventaja": "hacha"},
    # magia y arco son neutros contra el triángulo físico
}


def weapon_triangle_bonus(atq_tipo: str | None, def_tipo: str | None) -> tuple[int, int]:
    """
    Retorna (bonus_precision, bonus_daño) para el atacante.
    Positivo = ventaja, negativo = desventaja.
    """
    if not atq_tipo or not def_tipo:
        return 0, 0
    tri = _WEAPON_TRIANGLE.get(atq_tipo)
    if not tri:
        return 0, 0
    if def_tipo == tri["ventaja"]:
        return 15, 1
    if def_tipo == tri["desventaja"]:
        return -15, -1
    return 0, 0


# =================================================
# CÁLCULO DE COMBATE
# =================================================

def calcular_hit_rate(atq, defen, terreno_esquive: int = 0) -> int:
    """
    Probabilidad de golpe (0-99).
    hit_rate = 70 + skl*2 + lck/2 + precision_arma
    esquive  = spd*2 + lck/4 + terreno
    """
    skl = getattr(atq, "habilidad", 4)
    lck_a = getattr(atq, "suerte", 3)
    prec_arma = getattr(atq.arma_equipada, "precision_bonus", 0) if atq.arma_equipada else 0

    spd_d = defen.get_velocidad_efectiva()
    lck_d = getattr(defen, "suerte", 3)

    hit_base = 70 + skl * 2 + lck_a // 2 + prec_arma
    esquive  = spd_d * 2 + lck_d // 4 + terreno_esquive

    # Triángulo de armas (afecta precisión)
    tri_prec, _ = weapon_triangle_bonus(atq.get_tipo_arma(), defen.get_tipo_arma())
    hit_base += tri_prec

    return max(10, min(99, hit_base - esquive))


def calcular_crit_rate(atq) -> int:
    """
    Probabilidad de crítico (0-50).
    crit = skl/2 + lck/4 + critico_arma
    """
    skl = getattr(atq, "habilidad", 4)
    lck = getattr(atq, "suerte", 3)
    crit_arma = getattr(atq.arma_equipada, "critico_bonus", 0) if atq.arma_equipada else 0
    return max(0, min(50, skl // 2 + lck // 4 + crit_arma))


def calcular_daño(atq, defen) -> int:
    """
    Daño base = (fuerza + poder_arma) - defensa_efectiva_defensor.
    Aplica triángulo de armas.
    """
    poder_base = atq.get_poder_ataque()
    def_ef     = defen.get_defensa_efectiva()
    _, tri_dmg = weapon_triangle_bonus(atq.get_tipo_arma(), defen.get_tipo_arma())
    return max(0, poder_base - def_ef + tri_dmg)


def puede_contraatacar(atq, defen) -> bool:
    """Defensor puede contraatacar si tiene arma con rango que alcanza al atacante."""
    if not defen.arma_equipada:
        return False
    dist = abs(atq.x - defen.x) + abs(atq.y - defen.y)
    r = defen.arma_equipada.rango
    return r[0] <= dist <= r[1]


def tiene_doble_ataque(atq, defen) -> bool:
    """Atacante golpea dos veces si su velocidad supera al defensor en ≥ 4."""
    return atq.get_velocidad_efectiva() >= defen.get_velocidad_efectiva() + 4


# =================================================
# EJECUCIÓN DE UN GOLPE
# =================================================

def _execute_hit(atq, defen, add_fx, terreno_esquive: int = 0) -> bool:
    """
    Ejecuta un único golpe. Retorna True si el defensor muere.
    """
    hit_rate  = calcular_hit_rate(atq, defen, terreno_esquive)
    crit_rate = calcular_crit_rate(atq)
    dmg_base  = calcular_daño(atq, defen)

    roll = random.randint(1, 100)
    if roll > hit_rate:
        # Fallo
        if add_fx:
            add_fx(defen.x * C.TAMANO_TILE, defen.y * C.TAMANO_TILE,
                   "Fallo", C.GRIS_INACTIVO, 16, 1.5)
        return False

    roll_crit = random.randint(1, 100)
    es_critico = roll_crit <= crit_rate

    if es_critico:
        dmg = dmg_base * 3
    else:
        dmg = dmg_base

    defen.hp_actual -= dmg

    if add_fx:
        color = C.AMARILLO_AWK if es_critico else C.BLANCO
        size  = 26          if es_critico else 20
        add_fx(defen.x * C.TAMANO_TILE, defen.y * C.TAMANO_TILE,
               str(dmg), color, size, 2.0)
        if es_critico:
            add_fx(defen.x * C.TAMANO_TILE, defen.y * C.TAMANO_TILE - 20,
                   "¡CRÍTICO!", C.AMARILLO_AWK, 18, 1.5)

    return not defen.esta_viva()


# =================================================
# COMBATE COMPLETO
# =================================================

def resolver_combate(atq, defen, add_fx=None, terreno_esquive_def: int = 0,
                     terreno_esquive_atq: int = 0) -> dict:
    """
    Secuencia completa de combate (estilo Fire Emblem):
    1. Ataque del atacante
    2. Contraataque (si defensor sobrevive y tiene rango)
    3. Segundo golpe del atacante (si tiene doble ataque)
    4. Segundo golpe del defensor (si tiene doble ataque y sobrevivió)

    Retorna dict con resultado: {mato_def, mato_atq, exp_ganada}
    """
    result = {"mato_def": False, "mato_atq": False, "exp_ganada": 0}

    doble_atq = tiene_doble_ataque(atq, defen)
    doble_def = tiene_doble_ataque(defen, atq)

    # --- Ataque 1 del atacante ---
    atq.ganar_awakening(15)
    defen.ganar_awakening(10)

    mato = _execute_hit(atq, defen, add_fx, terreno_esquive_def)
    if mato:
        result["mato_def"] = True
        result["exp_ganada"] = 50
        atq.ganar_exp(50)
        return result
    atq.ganar_exp(15)

    # --- Contraataque del defensor ---
    if puede_contraatacar(atq, defen):
        defen.ganar_awakening(15)
        mato_atq = _execute_hit(defen, atq, add_fx, terreno_esquive_atq)
        defen.ganar_exp(10)
        if mato_atq:
            result["mato_atq"] = True
            return result

    if not defen.esta_viva():
        return result

    # --- Segundo golpe del atacante (doble ataque) ---
    if doble_atq and atq.esta_viva():
        mato = _execute_hit(atq, defen, add_fx, terreno_esquive_def)
        if mato:
            result["mato_def"] = True
            atq.ganar_exp(20)
            return result

    # --- Segundo golpe del defensor ---
    if doble_def and defen.esta_viva() and atq.esta_viva() and puede_contraatacar(atq, defen):
        mato_atq = _execute_hit(defen, atq, add_fx, terreno_esquive_atq)
        if mato_atq:
            result["mato_atq"] = True
            return result

    return result


# =================================================
# OBTENER OBJETIVOS EN RANGO
# =================================================

def obtener_enemigos_en_rango(atq, unidades, usar_skill=None):
    """
    Devuelve lista de objetivos válidos según arma o habilidad.
    """
    objetivos = []

    if usar_skill:
        rango = usar_skill.rango
    else:
        rango = atq.arma_equipada.rango if atq.arma_equipada else (1, 1)

    for u in unidades:
        if not u.esta_viva() or u is atq:
            continue

        dist = abs(atq.x - u.x) + abs(atq.y - u.y)
        if not (rango[0] <= dist <= rango[1]):
            continue

        es_enemigo = (u.bando != atq.bando)

        if usar_skill:
            efecto = getattr(usar_skill, "tipo_efecto", "daño")
            if efecto == "buff":
                # buff: aliados y uno mismo
                if not es_enemigo:
                    objetivos.append(u)
            elif efecto == "curar":
                if not es_enemigo:
                    objetivos.append(u)
            else:
                if es_enemigo:
                    objetivos.append(u)
        else:
            if es_enemigo:
                objetivos.append(u)

    return objetivos


# =================================================
# PREVIEW (para Battle Forecast)
# =================================================

def calcular_preview(atq, defen, terreno_esquive_def: int = 0,
                     terreno_esquive_atq: int = 0) -> dict:
    """
    Calcula estadísticas del combate SIN ejecutarlo.
    Usado por ui/battle_preview.py.
    """
    hit_a  = calcular_hit_rate(atq, defen, terreno_esquive_def)
    crit_a = calcular_crit_rate(atq)
    dmg_a  = calcular_daño(atq, defen)

    puede_contra = puede_contraatacar(atq, defen)
    hit_d  = calcular_hit_rate(defen, atq, terreno_esquive_atq) if puede_contra else 0
    crit_d = calcular_crit_rate(defen) if puede_contra else 0
    dmg_d  = calcular_daño(defen, atq) if puede_contra else 0

    doble_a = tiene_doble_ataque(atq, defen)
    doble_d = tiene_doble_ataque(defen, atq) and puede_contra

    tri_a, _ = weapon_triangle_bonus(atq.get_tipo_arma(), defen.get_tipo_arma())
    tri_d, _ = weapon_triangle_bonus(defen.get_tipo_arma(), atq.get_tipo_arma())

    return {
        # Atacante
        "atq_nombre":  atq.nombre,
        "atq_hp":      atq.hp_actual,
        "atq_max_hp":  atq.max_hp,
        "atq_dmg":     dmg_a,
        "atq_hit":     hit_a,
        "atq_crit":    crit_a,
        "atq_doble":   doble_a,
        "atq_tri":     tri_a,        # positivo=ventaja, negativo=desventaja
        # Defensor
        "def_nombre":  defen.nombre,
        "def_hp":      defen.hp_actual,
        "def_max_hp":  defen.max_hp,
        "def_dmg":     dmg_d,
        "def_hit":     hit_d,
        "def_crit":    crit_d,
        "def_doble":   doble_d,
        "def_tri":     tri_d,
        "def_puede_contra": puede_contra,
    }
