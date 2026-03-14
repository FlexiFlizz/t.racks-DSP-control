"""Modeles de donnees pour les filtres DSP."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TypeFiltre(str, Enum):
    PEAK = "peak"
    LOW_SHELF = "low_shelf"
    HIGH_SHELF = "high_shelf"
    HPF = "hpf"
    LPF = "lpf"
    ALL_PASS = "all_pass"
    NOTCH = "notch"


class TypePente(str, Enum):
    BW_6 = "BW -6"
    BW_12 = "BW -12"
    BW_18 = "BW -18"
    BW_24 = "BW -24"
    BW_36 = "BW -36"
    BW_48 = "BW -48"
    LR_12 = "LR -12"
    LR_24 = "LR -24"
    LR_36 = "LR -36"
    LR_48 = "LR -48"


@dataclass
class FiltrePEQ:
    """Filtre parametrique."""
    frequence_hz: float
    gain_db: float
    q: float
    type: TypeFiltre = TypeFiltre.PEAK
    actif: bool = True


@dataclass
class FiltreCrossover:
    """Filtre de crossover (HPF ou LPF)."""
    frequence_hz: float
    pente: TypePente
    type: TypeFiltre = TypeFiltre.HPF
    actif: bool = True


@dataclass
class FiltreAllPass:
    """Filtre all-pass pour correction de phase."""
    frequence_hz: float
    q: float
    ordre: int = 2  # 1 ou 2
    actif: bool = True
