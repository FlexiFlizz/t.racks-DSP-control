"""Calcul de filtres PEQ correctifs.

Regle fondamentale : EQ soustractif uniquement.
On coupe les pics, on ne booste PAS les creux.
"""

import numpy as np
from typing import List, Optional, Tuple
from backend.models.filtre import FiltrePEQ, TypeFiltre


def detecter_pics(frequences: np.ndarray, magnitudes_db: np.ndarray,
                  cible_db: np.ndarray, seuil_db: float = 3.0,
                  freq_min: float = 20.0, freq_max: float = 20000.0,
                  max_pics: int = 9) -> List[dict]:
    """Detecte les pics au-dessus de la courbe cible.

    Ne detecte PAS les creux (EQ soustractif uniquement).

    Args:
        frequences: tableau de frequences en Hz.
        magnitudes_db: magnitude mesuree en dB.
        cible_db: courbe cible en dB (meme taille que magnitudes).
        seuil_db: ecart minimum pour considerer un pic (defaut: 3 dB).
        freq_min: borne inferieure de la zone d'analyse.
        freq_max: borne superieure de la zone d'analyse.
        max_pics: nombre maximum de pics a retourner.

    Returns:
        Liste de dicts avec 'frequence_hz', 'exces_db', 'index'.
    """
    masque = (frequences >= freq_min) & (frequences <= freq_max)
    ecart = magnitudes_db - cible_db

    pics = []
    indices = np.where(masque)[0]

    # Trouver les maxima locaux de l'ecart positif
    for i in range(1, len(indices) - 1):
        idx = indices[i]
        if (ecart[idx] > seuil_db
                and ecart[idx] > ecart[idx - 1]
                and ecart[idx] > ecart[idx + 1]):
            pics.append({
                "frequence_hz": float(frequences[idx]),
                "exces_db": float(ecart[idx]),
                "index": int(idx),
            })

    # Trier par amplitude decroissante et limiter
    pics.sort(key=lambda p: p["exces_db"], reverse=True)
    return pics[:max_pics]


def estimer_q(frequences: np.ndarray, magnitudes_db: np.ndarray,
              index_pic: int) -> float:
    """Estime le facteur Q d'un pic a partir de sa largeur a -3 dB.

    Args:
        frequences: tableau de frequences.
        magnitudes_db: magnitude en dB.
        index_pic: index du pic dans le tableau.

    Returns:
        Facteur Q estime (typiquement 0.5 a 10).
    """
    niveau_pic = magnitudes_db[index_pic]
    niveau_3db = niveau_pic - 3.0
    freq_pic = frequences[index_pic]

    # Chercher les points a -3 dB de chaque cote
    freq_basse = freq_pic
    freq_haute = freq_pic

    # Cote gauche
    for i in range(index_pic - 1, 0, -1):
        if magnitudes_db[i] <= niveau_3db:
            # Interpolation lineaire
            ratio = (niveau_3db - magnitudes_db[i]) / (magnitudes_db[i + 1] - magnitudes_db[i])
            freq_basse = frequences[i] + ratio * (frequences[i + 1] - frequences[i])
            break

    # Cote droit
    for i in range(index_pic + 1, len(magnitudes_db)):
        if magnitudes_db[i] <= niveau_3db:
            ratio = (niveau_3db - magnitudes_db[i]) / (magnitudes_db[i - 1] - magnitudes_db[i])
            freq_haute = frequences[i] - ratio * (frequences[i] - frequences[i - 1])
            break

    bw = freq_haute - freq_basse
    if bw <= 0:
        return 2.0  # fallback

    return freq_pic / bw


def generer_filtres_correctifs(
    frequences: np.ndarray,
    magnitudes_db: np.ndarray,
    cible_db: Optional[np.ndarray] = None,
    seuil_db: float = 3.0,
    freq_min: float = 20.0,
    freq_max: float = 20000.0,
    max_filtres: int = 9,
) -> List[FiltrePEQ]:
    """Genere des filtres PEQ correctifs (soustractifs uniquement).

    Args:
        frequences: tableau de frequences en Hz.
        magnitudes_db: magnitude mesuree en dB.
        cible_db: courbe cible en dB (si None, utilise la moyenne).
        seuil_db: ecart minimum pour corriger.
        freq_min: borne inferieure.
        freq_max: borne superieure.
        max_filtres: nombre max de filtres.

    Returns:
        Liste de FiltrePEQ a appliquer.
    """
    if cible_db is None:
        # Cible = moyenne lissee de la reponse
        masque = (frequences >= freq_min) & (frequences <= freq_max)
        niveau_moyen = float(np.mean(magnitudes_db[masque]))
        cible_db = np.full_like(magnitudes_db, niveau_moyen)

    pics = detecter_pics(
        frequences, magnitudes_db, cible_db,
        seuil_db=seuil_db, freq_min=freq_min,
        freq_max=freq_max, max_pics=max_filtres,
    )

    filtres = []
    for pic in pics:
        q = estimer_q(frequences, magnitudes_db, pic["index"])
        # Gain negatif = soustractif (on coupe le pic)
        gain = -pic["exces_db"]

        filtres.append(FiltrePEQ(
            frequence_hz=pic["frequence_hz"],
            gain_db=round(gain, 1),
            q=round(q, 1),
            type=TypeFiltre.PEAK,
            actif=True,
        ))

    return filtres


def formater_filtres(filtres: List[FiltrePEQ]) -> str:
    """Formate une liste de filtres pour affichage texte.

    Args:
        filtres: liste de FiltrePEQ.

    Returns:
        Chaine formatee lisible.
    """
    if not filtres:
        return "Aucun filtre correctif necessaire."

    lignes = [f"{'Bande':>5} | {'Freq':>8} | {'Gain':>7} | {'Q':>5} | Type"]
    lignes.append("-" * 50)

    for i, f in enumerate(filtres):
        freq_str = f"{f.frequence_hz:.0f} Hz"
        gain_str = f"{f.gain_db:+.1f} dB"
        lignes.append(f"  {i:>3} | {freq_str:>8} | {gain_str:>7} | {f.q:>5.1f} | {f.type.value}")

    return "\n".join(lignes)
