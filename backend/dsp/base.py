"""Classe abstraite pour les processeurs DSP."""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from backend.models.filtre import FiltrePEQ, FiltreCrossover


class BaseDSP(ABC):
    """Interface commune pour tous les processeurs DSP.

    Chaque processeur (t.racks, XR18, CamillaDSP...) implemente
    cette interface. Le moteur de calage utilise uniquement cette
    abstraction.
    """

    @abstractmethod
    def connecter(self, host: str, port: int) -> bool:
        """Connecte au processeur."""
        ...

    @abstractmethod
    def deconnecter(self):
        """Deconnecte du processeur."""
        ...

    @abstractmethod
    def est_connecte(self) -> bool:
        """Verifie si la connexion est active."""
        ...

    @abstractmethod
    def get_nom_modele(self) -> str:
        """Retourne le nom du modele (ex: 'DSP 206')."""
        ...

    @abstractmethod
    def get_canaux(self) -> Dict[str, int]:
        """Retourne le mapping nom -> index de tous les canaux."""
        ...

    @abstractmethod
    def get_canaux_entree(self) -> Dict[str, int]:
        """Retourne les canaux d'entree."""
        ...

    @abstractmethod
    def get_canaux_sortie(self) -> Dict[str, int]:
        """Retourne les canaux de sortie."""
        ...

    # -- Gain --

    @abstractmethod
    def set_gain(self, canal: str, db: float):
        """Regle le gain d'un canal en dB."""
        ...

    @abstractmethod
    def get_gain(self, canal: str) -> float:
        """Lit le gain d'un canal en dB."""
        ...

    # -- Mute --

    @abstractmethod
    def set_mute(self, canal: str, mute: bool):
        """Mute/unmute un canal."""
        ...

    @abstractmethod
    def get_mute(self, canal: str) -> bool:
        """Lit l'etat mute d'un canal."""
        ...

    # -- Delay --

    @abstractmethod
    def set_delay(self, canal: str, delay_ms: float):
        """Regle le delay d'un canal en ms."""
        ...

    @abstractmethod
    def get_delay(self, canal: str) -> float:
        """Lit le delay d'un canal en ms."""
        ...

    # -- PEQ --

    @abstractmethod
    def set_peq(self, canal: str, bande: int, filtre: FiltrePEQ):
        """Regle une bande PEQ."""
        ...

    @abstractmethod
    def get_nb_bandes_peq(self, canal: str) -> int:
        """Retourne le nombre de bandes PEQ pour un canal."""
        ...

    # -- Crossover (HPF/LPF) --

    @abstractmethod
    def set_hpf(self, canal: str, filtre: FiltreCrossover):
        """Regle le filtre passe-haut."""
        ...

    @abstractmethod
    def set_lpf(self, canal: str, filtre: FiltreCrossover):
        """Regle le filtre passe-bas."""
        ...

    # -- Polarite --

    @abstractmethod
    def set_polarite(self, canal: str, inversee: bool):
        """Inverse la polarite d'un canal."""
        ...

    # -- Etat global --

    def get_etat(self) -> dict:
        """Retourne l'etat complet du DSP (gains, mutes, delays, EQ...)."""
        etat = {"modele": self.get_nom_modele(), "canaux": {}}
        for nom, idx in self.get_canaux().items():
            etat["canaux"][nom] = {
                "gain_db": self.get_gain(nom),
                "mute": self.get_mute(nom),
                "delay_ms": self.get_delay(nom),
            }
        return etat
