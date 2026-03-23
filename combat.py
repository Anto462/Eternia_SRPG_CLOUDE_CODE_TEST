# combat.py
# -------------------------------------------------
# Todo lo relacionado a:
# - calcular objetivos en rango
# - resolver combate básico (tu versión actual)
#
# Importante:
# - No dibujamos nada aquí
# - Solo llamamos a add_floating_text si viene como callback
# - Mantiene el comportamiento de tu prototipo

import constants as C

TAMANO_TILE = C.TAMANO_TILE
BLANCO = C.BLANCO
ROJO_ATAQUE = C.ROJO_ATAQUE


def obtener_enemigos_en_rango(atq, unidades, usar_skill=None):
    """
    Obtiene objetivos válidos según:
    - Si es ataque normal: solo enemigos
    - Si es skill:
        - tipo 'daño': enemigos
        - tipo 'curar': aliados (mismo bando)

    El rango se interpreta en distancia Manhattan (como FE clásico).
    """
    objetivos = []

    if usar_skill:
        rango = usar_skill.rango
    else:
        rango = atq.arma_equipada.rango if atq.arma_equipada else (1, 1)

    for u in unidades:
        if not u.esta_viva():
            continue
        if u is atq:
            continue

        dist = abs(atq.x - u.x) + abs(atq.y - u.y)
        if not (rango[0] <= dist <= rango[1]):
            continue

        es_enemigo = (u.bando != atq.bando)

        if usar_skill:
            if (usar_skill.tipo_efecto == "daño" and es_enemigo) or \
               (usar_skill.tipo_efecto == "curar" and not es_enemigo):
                objetivos.append(u)
        else:
            if es_enemigo:
                objetivos.append(u)

    return objetivos


def resolver_combate(atq, defen, add_floating_text=None):
    """
    Combate básico tipo prototipo:
    - Atacante golpea
    - Si defensor sobrevive y tiene rango para contraataque -> contraataca

    add_floating_text: función callback (x, y, texto, color, tamaño=..., velocidad_y=...)
    """
    def fx(x, y, texto, color, tamaño=20, velocidad_y=2):
        if add_floating_text:
            add_floating_text(x, y, texto, color, tamaño, velocidad_y)

    # --- Golpe del atacante ---
    daño = max(0, atq.get_poder_ataque() - defen.defensa)
    defen.hp_actual -= daño

    # FX (igual que tu base)
    fx(defen.x * TAMANO_TILE, defen.y * TAMANO_TILE, str(daño), BLANCO, velocidad_y=2)
    fx(atq.x * TAMANO_TILE, atq.y * TAMANO_TILE, "Hit!", ROJO_ATAQUE, tamaño=12, velocidad_y=1)

    # Awakening + EXP (igual lógica)
    atq.ganar_awakening(15)
    defen.ganar_awakening(10)

    if not defen.esta_viva():
        atq.ganar_exp(50)
        return  # muerto, no hay contra
    else:
        atq.ganar_exp(15)

    # --- Contraataque si tiene rango ---
    rng = defen.arma_equipada.rango if defen.arma_equipada else (1, 1)
    dist = abs(atq.x - defen.x) + abs(atq.y - defen.y)

    if rng[0] <= dist <= rng[1]:
        daño_contra = max(0, defen.get_poder_ataque() - atq.defensa)
        atq.hp_actual -= daño_contra

        fx(atq.x * TAMANO_TILE, atq.y * TAMANO_TILE, str(daño_contra), BLANCO, velocidad_y=2)

        defen.ganar_exp(10)
        defen.ganar_awakening(15)

