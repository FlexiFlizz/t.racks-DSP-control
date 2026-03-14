"""Analyse de phase pour le calage systeme.

Fonctions pour extraire, unwrapper et analyser les traces de phase
a partir des mesures REW. La phase est la reference pour le calage
sub/top (pas l'IR seule).
"""

import numpy as np
from typing import Tuple, Optional


def unwrap_phase(phases_deg: np.ndarray) -> np.ndarray:
    """Dewrappe la phase (supprime les sauts de 360 degres).

    Args:
        phases_deg: phase en degres (peut contenir des wraps).

    Returns:
        Phase unwrappee en degres.
    """
    return np.degrees(np.unwrap(np.radians(phases_deg)))


def pente_phase(frequences: np.ndarray, phases_deg: np.ndarray,
                freq_min: float, freq_max: float) -> float:
    """Calcule la pente de la phase dans une bande de frequences.

    La pente de phase est directement proportionnelle au delay :
        delay_s = -dphi/df / 360

    Args:
        frequences: tableau de frequences en Hz.
        phases_deg: phase unwrappee en degres.
        freq_min: borne inferieure de la bande (Hz).
        freq_max: borne superieure de la bande (Hz).

    Returns:
        Pente en degres/Hz.
    """
    masque = (frequences >= freq_min) & (frequences <= freq_max)
    if np.sum(masque) < 2:
        return 0.0

    freq_band = frequences[masque]
    phase_band = phases_deg[masque]

    # Regression lineaire
    coeffs = np.polyfit(freq_band, phase_band, 1)
    return coeffs[0]  # pente en deg/Hz


def delay_depuis_phase(frequences: np.ndarray, phases_deg: np.ndarray,
                       freq_min: float, freq_max: float) -> float:
    """Calcule le delay en ms a partir de la pente de phase.

    delay_ms = -pente / 360 * 1000

    Args:
        frequences: tableau de frequences en Hz.
        phases_deg: phase unwrappee en degres.
        freq_min: borne inferieure (Hz).
        freq_max: borne superieure (Hz).

    Returns:
        Delay en millisecondes.
    """
    pente = pente_phase(frequences, phases_deg, freq_min, freq_max)
    return -pente / 360.0 * 1000.0


def offset_phase_moyen(frequences: np.ndarray, phases_a: np.ndarray,
                       phases_b: np.ndarray, freq_min: float,
                       freq_max: float) -> float:
    """Calcule l'offset de phase moyen entre deux mesures dans une bande.

    Args:
        frequences: tableau de frequences commun.
        phases_a: phase de la mesure A (degres, unwrappee).
        phases_b: phase de la mesure B (degres, unwrappee).
        freq_min: borne inferieure (Hz).
        freq_max: borne superieure (Hz).

    Returns:
        Offset moyen en degres (A - B).
    """
    masque = (frequences >= freq_min) & (frequences <= freq_max)
    if np.sum(masque) < 1:
        return 0.0

    diff = phases_a[masque] - phases_b[masque]
    return float(np.mean(diff))


def detecter_polarite(frequences: np.ndarray, phases_a: np.ndarray,
                      phases_b: np.ndarray, freq_crossover: float,
                      largeur_octaves: float = 1.0) -> bool:
    """Detecte si la polarite doit etre inversee pour l'alignement.

    Si le dephasage moyen dans la zone de crossover est proche de 180
    degres, la polarite doit etre inversee.

    Args:
        frequences: tableau de frequences commun.
        phases_a: phase du sous-systeme A (degres, unwrappee).
        phases_b: phase du sous-systeme B (degres, unwrappee).
        freq_crossover: frequence de crossover en Hz.
        largeur_octaves: largeur de la bande d'analyse en octaves.

    Returns:
        True si la polarite doit etre inversee.
    """
    freq_min = freq_crossover / (2 ** (largeur_octaves / 2))
    freq_max = freq_crossover * (2 ** (largeur_octaves / 2))

    offset = offset_phase_moyen(frequences, phases_a, phases_b, freq_min, freq_max)

    # Normaliser entre -180 et +180
    offset_norm = ((offset + 180) % 360) - 180

    return abs(offset_norm) > 120  # > 120 deg = probablement inverse


def coherence_phase(frequences: np.ndarray, phases_a: np.ndarray,
                    phases_b: np.ndarray, freq_min: float,
                    freq_max: float) -> float:
    """Evalue la coherence de phase entre deux mesures.

    Retourne un score de 0 (oppose) a 1 (parfaitement aligne).
    Utilise le cosinus de la difference de phase.

    Args:
        frequences: tableau de frequences commun.
        phases_a: phase A en degres.
        phases_b: phase B en degres.
        freq_min: borne inferieure.
        freq_max: borne superieure.

    Returns:
        Score de coherence (0.0 a 1.0).
    """
    masque = (frequences >= freq_min) & (frequences <= freq_max)
    if np.sum(masque) < 1:
        return 0.0

    diff_rad = np.radians(phases_a[masque] - phases_b[masque])
    return float((np.mean(np.cos(diff_rad)) + 1) / 2)


def group_delay_depuis_phase(frequences: np.ndarray,
                             phases_deg: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Calcule le group delay a partir de la phase.

    group_delay = -1/(2*pi) * dphi/df

    Args:
        frequences: tableau de frequences en Hz.
        phases_deg: phase unwrappee en degres.

    Returns:
        Tuple (frequences_centre, group_delay_ms).
    """
    dphi = np.diff(np.radians(phases_deg))
    df = np.diff(frequences)

    # Eviter division par zero
    valide = df > 0
    freq_centre = (frequences[:-1] + frequences[1:]) / 2

    gd = np.zeros_like(dphi)
    gd[valide] = -dphi[valide] / (2 * np.pi * df[valide])

    return freq_centre, gd * 1000  # en ms
