"""Driver t.racks unifie implementant l'interface BaseDSP.

Supporte les modeles DSP 206, 408, 306, 204 (meme protocole TCP).
"""

import sys
import os
import logging
from typing import Dict, Optional, List

# Ajouter le dossier racine au path pour importer le driver existant
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from drivers.tracks_dsp206 import (
    TracksDSP206,
    CANAUX_ENTREE, CANAUX_SORTIE, TOUS_LES_CANAUX,
    gain_brut_vers_db,
)
from backend.dsp.base import BaseDSP
from backend.models.filtre import FiltrePEQ, FiltreCrossover, TypeFiltre

logger = logging.getLogger(__name__)

# Topologies par modele
TOPOLOGIES = {
    "DSP 206": {
        "entrees": {"In A": 0x00, "In B": 0x01},
        "sorties": {"Out 1": 0x02, "Out 2": 0x03, "Out 3": 0x04,
                    "Out 4": 0x05, "Out 5": 0x06, "Out 6": 0x07},
        "peq_entree": 8,
        "peq_sortie": 9,
    },
    "DSP 408": {
        "entrees": {"In A": 0x00, "In B": 0x01, "In C": 0x02, "In D": 0x03},
        "sorties": {"Out 1": 0x04, "Out 2": 0x05, "Out 3": 0x06, "Out 4": 0x07,
                    "Out 5": 0x08, "Out 6": 0x09, "Out 7": 0x0A, "Out 8": 0x0B},
        "peq_entree": 8,
        "peq_sortie": 9,
    },
    "DSP 306": {
        "entrees": {"In A": 0x00, "In B": 0x01, "In C": 0x02},
        "sorties": {"Out 1": 0x04, "Out 2": 0x05, "Out 3": 0x06,
                    "Out 4": 0x07, "Out 5": 0x08, "Out 6": 0x09},
        "peq_entree": 8,
        "peq_sortie": 9,
    },
    "DSP 204": {
        "entrees": {"In A": 0x00, "In B": 0x01},
        "sorties": {"Out 1": 0x04, "Out 2": 0x05, "Out 3": 0x06, "Out 4": 0x07},
        "peq_entree": 8,
        "peq_sortie": 9,
    },
}


# Mapping TypeFiltre -> index protocole t.racks
TYPE_FILTRE_VERS_INDEX = {
    TypeFiltre.PEAK: 0,
    TypeFiltre.LOW_SHELF: 1,
    TypeFiltre.HIGH_SHELF: 2,
    TypeFiltre.ALL_PASS: 7,
}


class TracksDSP(BaseDSP):
    """Interface unifiee pour les processeurs t.racks.

    Encapsule le driver TracksDSP206 avec l'interface BaseDSP.
    Detecte automatiquement le modele a la connexion.
    """

    def __init__(self):
        self._driver: Optional[TracksDSP206] = None
        self._modele: str = "DSP 206"
        self._topo: dict = TOPOLOGIES["DSP 206"]
        # Etat cache (le protocole ne permet pas de relire facilement)
        self._gains: Dict[str, float] = {}
        self._mutes: Dict[str, bool] = {}
        self._delays: Dict[str, float] = {}

    def connecter(self, host: str, port: int = 9761) -> bool:
        self._driver = TracksDSP206(host, port)
        try:
            self._driver.connecter()
        except ConnectionError:
            return False

        # Detecter le modele depuis le nom de l'appareil
        nom = self._driver.nom_appareil.upper()
        for modele in TOPOLOGIES:
            if modele.replace(" ", "") in nom.replace(" ", "").replace("-", ""):
                self._modele = modele
                self._topo = TOPOLOGIES[modele]
                break

        logger.info("Modele detecte : %s", self._modele)

        # Initialiser le cache
        for canal in {**self._topo["entrees"], **self._topo["sorties"]}:
            self._gains[canal] = 0.0
            self._mutes[canal] = False
            self._delays[canal] = 0.0

        return True

    def deconnecter(self):
        if self._driver:
            self._driver.deconnecter()
            self._driver = None

    def est_connecte(self) -> bool:
        return self._driver is not None and self._driver.connecte

    def get_nom_modele(self) -> str:
        return self._modele

    def get_canaux(self) -> Dict[str, int]:
        return {**self._topo["entrees"], **self._topo["sorties"]}

    def get_canaux_entree(self) -> Dict[str, int]:
        return dict(self._topo["entrees"])

    def get_canaux_sortie(self) -> Dict[str, int]:
        return dict(self._topo["sorties"])

    # -- Gain --

    def set_gain(self, canal: str, db: float):
        self._driver.set_gain(canal, db)
        self._gains[canal] = db

    def get_gain(self, canal: str) -> float:
        return self._gains.get(canal, 0.0)

    # -- Mute --

    def set_mute(self, canal: str, mute: bool):
        self._driver.set_mute(canal, mute)
        self._mutes[canal] = mute

    def get_mute(self, canal: str) -> bool:
        return self._mutes.get(canal, False)

    # -- Delay --

    def set_delay(self, canal: str, delay_ms: float):
        self._driver.set_delay(canal, delay_ms)
        self._delays[canal] = delay_ms

    def get_delay(self, canal: str) -> float:
        return self._delays.get(canal, 0.0)

    # -- PEQ --

    def set_peq(self, canal: str, bande: int, filtre: FiltrePEQ):
        type_idx = TYPE_FILTRE_VERS_INDEX.get(filtre.type, 0)
        self._driver.set_peq(
            canal, bande,
            gain_db=filtre.gain_db,
            freq_hz=filtre.frequence_hz,
            q=filtre.q,
            type_filtre=type_idx,
            bypass=not filtre.actif,
        )

    def get_nb_bandes_peq(self, canal: str) -> int:
        if canal in self._topo["entrees"]:
            return self._topo["peq_entree"]
        return self._topo["peq_sortie"]

    # -- Crossover --

    def set_hpf(self, canal: str, filtre: FiltreCrossover):
        self._driver.set_hpf(canal, filtre.frequence_hz, filtre.actif)

    def set_lpf(self, canal: str, filtre: FiltreCrossover):
        self._driver.set_lpf(canal, filtre.frequence_hz, actif=filtre.actif)

    # -- Polarite --

    def set_polarite(self, canal: str, inversee: bool):
        # Le protocole t.racks n'a pas de commande de polarite directe.
        # On utilise un PEQ all-pass ou on passe par la config.
        logger.warning(
            "Polarite %s : pas de commande directe sur t.racks. "
            "Utiliser un filtre all-pass ou inverser dans la matrice.",
            canal,
        )

    # -- Metres --

    def get_metres(self) -> Dict[str, float]:
        if self._driver:
            return self._driver.get_meters()
        return {}
