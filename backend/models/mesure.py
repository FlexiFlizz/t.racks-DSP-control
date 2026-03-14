"""Modeles de donnees pour les mesures."""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class Mesure:
    """Une mesure acoustique (depuis REW ou import)."""
    nom: str
    index_rew: Optional[int] = None
    uuid_rew: Optional[str] = None

    # Donnees decodees (NumPy arrays)
    frequences: Optional[np.ndarray] = None
    magnitudes: Optional[np.ndarray] = None
    phases: Optional[np.ndarray] = None
    ir_echantillons: Optional[np.ndarray] = None
    ir_sample_rate: Optional[float] = None
    group_delay: Optional[np.ndarray] = None
    group_delay_freq: Optional[np.ndarray] = None

    # Metadata
    position: Optional[str] = None  # ex: "FOH", "Parterre gauche"
    sous_systeme: Optional[str] = None  # ex: "Sub", "Top", "Fill"
    notes: Optional[str] = None

    def a_freq_response(self) -> bool:
        """Verifie si les donnees freq/mag/phase sont presentes."""
        return (self.frequences is not None
                and self.magnitudes is not None
                and self.phases is not None)

    def a_ir(self) -> bool:
        """Verifie si la reponse impulsionnelle est presente."""
        return self.ir_echantillons is not None and self.ir_sample_rate is not None


@dataclass
class PositionMesure:
    """Position de mesure dans l'espace."""
    nom: str
    description: Optional[str] = None
    poids: float = 1.0  # ponderation pour l'optimisation multi-pos
    mesures: list = field(default_factory=list)  # liste de Mesure
