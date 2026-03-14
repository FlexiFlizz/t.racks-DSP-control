"""Modeles de donnees pour la definition du systeme son."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List
from .filtre import FiltreCrossover, TypePente, TypeFiltre


class TypeSousSysteme(str, Enum):
    SUB = "sub"
    TOP = "top"
    LOW_MID = "low_mid"
    HIGH = "high"
    FILL = "fill"
    DELAY = "delay"
    MONITOR = "monitor"


@dataclass
class SousSysteme:
    """Un sous-systeme (sub, top, fill, etc.)."""
    nom: str
    type: TypeSousSysteme
    canal_dsp: Optional[str] = None  # ex: "Out 1"
    hpf: Optional[FiltreCrossover] = None
    lpf: Optional[FiltreCrossover] = None


@dataclass
class Crossover:
    """Definition d'un point de crossover entre deux sous-systemes."""
    sous_systeme_bas: str  # nom du sous-systeme bas (ex: "Sub")
    sous_systeme_haut: str  # nom du sous-systeme haut (ex: "Top")
    frequence_hz: float  # frequence de crossover


@dataclass
class SystemeSon:
    """Definition complete du systeme son a caler."""
    nom: str
    sous_systemes: List[SousSysteme] = field(default_factory=list)
    crossovers: List[Crossover] = field(default_factory=list)
    ip_dsp: str = "192.168.3.100"
    port_dsp: int = 9761
    modele_dsp: str = "DSP 206"

    def get_sous_systeme(self, nom: str) -> Optional[SousSysteme]:
        for ss in self.sous_systemes:
            if ss.nom == nom:
                return ss
        return None
