"""
Decodeur de donnees REW API.

REW encode les tableaux de floats en Base64 big-endian 32-bit.
Ce module decode ces donnees en tableaux NumPy.
"""

import base64
import struct
import numpy as np
from typing import Optional


def decoder_base64_float32(data_b64: str) -> np.ndarray:
    """Decode une chaine Base64 contenant des float32 big-endian.

    C'est le format utilise par REW pour les reponses en frequence,
    les reponses impulsionnelles, le group delay, etc.

    Args:
        data_b64: chaine Base64 encodee par REW.

    Returns:
        Tableau NumPy de float64.
    """
    raw = base64.b64decode(data_b64)
    # Big-endian float32 = '>f'
    count = len(raw) // 4
    values = struct.unpack(f'>{count}f', raw)
    return np.array(values, dtype=np.float64)


def decoder_reponse_frequentielle(data: dict) -> dict:
    """Decode la reponse de GET /measurements/:id/frequency-response.

    REW v5.40 retourne :
    - magnitude : Base64 float32 (dB)
    - phase : Base64 float32 (degres)
    - startFreq : frequence de depart (Hz)
    - ppo : points par octave

    Les frequences sont reconstruites a partir de startFreq et ppo.

    Args:
        data: dictionnaire JSON de la reponse REW.

    Returns:
        Dictionnaire avec 'frequences', 'magnitudes', 'phases' (NumPy arrays).
    """
    resultat = {}

    # Decoder magnitude (cle 'magnitude' ou 'magnitudes')
    mag_key = "magnitude" if "magnitude" in data else "magnitudes"
    if mag_key in data:
        resultat["magnitudes"] = decoder_base64_float32(data[mag_key])

    # Decoder phase (cle 'phase' ou 'phases')
    phase_key = "phase" if "phase" in data else "phases"
    if phase_key in data:
        resultat["phases"] = decoder_base64_float32(data[phase_key])

    # Decoder ou reconstruire les frequences
    if "frequencies" in data:
        resultat["frequences"] = decoder_base64_float32(data["frequencies"])
    elif "startFreq" in data and "ppo" in data and "magnitudes" in resultat:
        # Reconstruire les frequences depuis startFreq et ppo
        start_freq = data["startFreq"]
        ppo = data["ppo"]
        n_points = len(resultat["magnitudes"])
        freqs = np.array([
            start_freq * (2.0 ** (i / ppo)) for i in range(n_points)
        ])
        resultat["frequences"] = freqs

    return resultat


def decoder_reponse_impulsionnelle(data: dict) -> dict:
    """Decode la reponse de GET /measurements/:id/impulse-response.

    REW v5.40 retourne :
    - data : Base64 float32 (echantillons IR)
    - sampleRate : frequence d'echantillonnage
    - startTime : temps de depart en secondes

    Args:
        data: dictionnaire JSON de la reponse REW.

    Returns:
        Dictionnaire avec 'echantillons' (NumPy), 'sample_rate', 'start_time'.
    """
    resultat = {}

    # Cle 'data' ou 'samples'
    ir_key = "data" if "data" in data else "samples"
    if ir_key in data:
        resultat["echantillons"] = decoder_base64_float32(data[ir_key])
    if "sampleRate" in data:
        resultat["sample_rate"] = data["sampleRate"]
    if "startTime" in data:
        resultat["start_time"] = data["startTime"]

    return resultat


def decoder_group_delay(data: dict) -> dict:
    """Decode la reponse de GET /measurements/:id/group-delay.

    REW v5.40 retourne :
    - magnitude : Base64 float32 (group delay en secondes)
    - startFreq, ppo : pour reconstruire les frequences

    Args:
        data: dictionnaire JSON de la reponse REW.

    Returns:
        Dictionnaire avec 'frequences' et 'group_delay' (en secondes).
    """
    resultat = {}

    # Decoder le group delay (cle 'magnitude' ou 'groupDelay')
    gd_key = "magnitude" if "magnitude" in data else "groupDelay"
    if gd_key in data:
        resultat["group_delay"] = decoder_base64_float32(data[gd_key])

    # Frequences
    if "frequencies" in data:
        resultat["frequences"] = decoder_base64_float32(data["frequencies"])
    elif "startFreq" in data and "ppo" in data and "group_delay" in resultat:
        start_freq = data["startFreq"]
        ppo = data["ppo"]
        n_points = len(resultat["group_delay"])
        resultat["frequences"] = np.array([
            start_freq * (2.0 ** (i / ppo)) for i in range(n_points)
        ])

    return resultat
