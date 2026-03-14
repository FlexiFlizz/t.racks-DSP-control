"""Calcul du delay optimal pour l'alignement temporel.

Deux methodes :
1. Pic IR : trouve le pic de la reponse impulsionnelle
2. Pente de phase : calcule le delay depuis la trace de phase
"""

import numpy as np
from typing import Optional, Tuple
from .analyseur_phase import unwrap_phase, delay_depuis_phase


def delay_par_pic_ir(echantillons: np.ndarray, sample_rate: float,
                     start_time: float = 0.0) -> float:
    """Calcule le delay en trouvant le pic de la reponse impulsionnelle.

    Methode simple et robuste pour les mesures propres.

    Args:
        echantillons: reponse impulsionnelle.
        sample_rate: frequence d'echantillonnage en Hz.
        start_time: temps de depart en secondes.

    Returns:
        Delay en millisecondes depuis t=0.
    """
    pic_index = np.argmax(np.abs(echantillons))
    delay_s = start_time + pic_index / sample_rate
    return delay_s * 1000.0  # en ms


def delay_par_phase(frequences: np.ndarray, phases_deg: np.ndarray,
                    freq_min: float = 100.0, freq_max: float = 2000.0) -> float:
    """Calcule le delay depuis la pente de la trace de phase.

    Plus fiable que le pic IR pour le calage sub/top car la phase
    integre la reponse du filtre de crossover.

    Args:
        frequences: tableau de frequences en Hz.
        phases_deg: phase en degres (sera unwrappee).
        freq_min: borne inferieure de la bande d'analyse.
        freq_max: borne superieure de la bande d'analyse.

    Returns:
        Delay en millisecondes.
    """
    phases_uw = unwrap_phase(phases_deg)
    return delay_depuis_phase(frequences, phases_uw, freq_min, freq_max)


def delay_relatif(delay_a_ms: float, delay_b_ms: float) -> float:
    """Calcule le delay relatif entre deux sous-systemes.

    Un resultat positif signifie que B est en retard sur A.

    Args:
        delay_a_ms: delay absolu de A en ms.
        delay_b_ms: delay absolu de B en ms.

    Returns:
        Delay relatif en ms (positif = B en retard).
    """
    return delay_b_ms - delay_a_ms


def calculer_delay_optimal(
    freq_a: np.ndarray, phase_a: np.ndarray,
    freq_b: np.ndarray, phase_b: np.ndarray,
    freq_crossover: float,
    largeur_octaves: float = 1.0,
    ir_a: Optional[np.ndarray] = None,
    ir_b: Optional[np.ndarray] = None,
    sr: Optional[float] = None,
) -> dict:
    """Calcule le delay optimal pour aligner deux sous-systemes.

    Combine l'analyse de phase et l'IR pour un resultat robuste.

    Args:
        freq_a, phase_a: reponse du sous-systeme A.
        freq_b, phase_b: reponse du sous-systeme B.
        freq_crossover: frequence de crossover en Hz.
        largeur_octaves: largeur de la bande d'analyse autour du crossover.
        ir_a, ir_b: reponses impulsionnelles (optionnel).
        sr: sample rate des IR (requis si IR fourni).

    Returns:
        Dictionnaire avec les resultats :
        - delay_phase_ms : delay calcule par la phase
        - delay_ir_ms : delay calcule par l'IR (si dispo)
        - delay_recommande_ms : delay a appliquer
        - methode : methode utilisee
    """
    freq_min = freq_crossover / (2 ** (largeur_octaves / 2))
    freq_max = freq_crossover * (2 ** (largeur_octaves / 2))

    # Methode 1 : phase
    delay_a_phase = delay_par_phase(freq_a, phase_a, freq_min, freq_max)
    delay_b_phase = delay_par_phase(freq_b, phase_b, freq_min, freq_max)
    delay_phase = delay_relatif(delay_a_phase, delay_b_phase)

    resultat = {
        "delay_a_phase_ms": round(delay_a_phase, 3),
        "delay_b_phase_ms": round(delay_b_phase, 3),
        "delay_phase_ms": round(delay_phase, 3),
        "delay_ir_ms": None,
        "delay_recommande_ms": round(abs(delay_phase), 2),
        "appliquer_sur": "B" if delay_phase > 0 else "A",
        "methode": "phase",
    }

    # Methode 2 : IR (verification)
    if ir_a is not None and ir_b is not None and sr is not None:
        delay_a_ir = delay_par_pic_ir(ir_a, sr)
        delay_b_ir = delay_par_pic_ir(ir_b, sr)
        delay_ir = delay_relatif(delay_a_ir, delay_b_ir)
        resultat["delay_ir_ms"] = round(delay_ir, 3)

        # Si les deux methodes sont coherentes, c'est bon signe
        ecart = abs(delay_phase - delay_ir)
        if ecart < 1.0:
            resultat["methode"] = "phase+ir"
        else:
            # En cas de desaccord, privilegier la phase (CLAUDE.md)
            resultat["methode"] = "phase (IR diverge)"

    return resultat
