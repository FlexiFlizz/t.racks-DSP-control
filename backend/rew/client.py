"""
Client Python pour l'API REST de REW (Room EQ Wizard).

Se connecte a REW sur localhost:4735 (port par defaut).
Les endpoints GET fonctionnent sans licence Pro.
Les endpoints POST (mesure automatique) necessitent REW Pro.

Usage :
    from backend.rew.client import ClientREW

    rew = ClientREW()
    if rew.est_connecte():
        mesures = rew.lister_mesures()
        freq = rew.get_reponse_frequentielle(0)
"""

import requests
import logging
from typing import Optional, List
from .decodeur import (
    decoder_reponse_frequentielle,
    decoder_reponse_impulsionnelle,
    decoder_group_delay,
)

logger = logging.getLogger(__name__)


class ClientREW:
    """Client pour l'API REST de REW."""

    def __init__(self, host: str = "localhost", port: int = 4735, timeout: float = 5.0):
        """Initialise le client REW.

        Args:
            host: adresse de REW (defaut: localhost).
            port: port de l'API REST (defaut: 4735).
            timeout: timeout des requetes HTTP en secondes.
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------
    # Connexion
    # ------------------------------------------------------------------

    def est_connecte(self) -> bool:
        """Verifie si REW est lance et l'API accessible."""
        try:
            # /application peut renvoyer 404 sur certaines versions,
            # on teste /application/commands qui marche toujours
            r = self._get("/application/commands")
            return r is not None
        except Exception:
            return False

    def get_statut(self) -> Optional[dict]:
        """Retourne le statut de l'application REW."""
        return self._get("/application")

    # ------------------------------------------------------------------
    # Mesures — lecture
    # ------------------------------------------------------------------

    def lister_mesures(self) -> List[dict]:
        """Liste toutes les mesures ouvertes dans REW.

        Returns:
            Liste de dictionnaires avec id, uuid, name, notes, etc.
        """
        data = self._get("/measurements")
        if data is None:
            return []
        # REW retourne un dict indexe par numero ("1": {...}, "2": {...})
        if isinstance(data, dict):
            if "measurements" in data:
                return data["measurements"]
            # Dict indexe par numero
            mesures = []
            for key in sorted(data.keys(), key=lambda k: int(k) if k.isdigit() else 0):
                entry = data[key]
                if isinstance(entry, dict):
                    entry["_index"] = key
                    # Normaliser le nom
                    if "title" in entry and "name" not in entry:
                        entry["name"] = entry["title"]
                    mesures.append(entry)
            return mesures
        if isinstance(data, list):
            return data
        return []

    def get_mesure(self, id_mesure) -> Optional[dict]:
        """Retourne le resume d'une mesure par index ou UUID.

        Note: REW indexe les mesures a partir de 1.
        Si on recoit un int, on ajoute 1 pour convertir de 0-based a 1-based.

        Args:
            id_mesure: index 0-based (int) ou UUID (str) de la mesure.
        """
        # Convertir index 0-based en 1-based pour REW
        rew_id = id_mesure + 1 if isinstance(id_mesure, int) else id_mesure
        data = self._get(f"/measurements/{rew_id}")
        if data and isinstance(data, dict) and "title" in data and "name" not in data:
            data["name"] = data["title"]
        return data

    def get_mesure_selectionnee(self) -> Optional[int]:
        """Retourne l'index de la mesure actuellement selectionnee."""
        data = self._get("/measurements/selected")
        if data is not None and "index" in data:
            return data["index"]
        return data

    def selectionner_mesure(self, index: int) -> bool:
        """Selectionne une mesure par index.

        Args:
            index: index de la mesure (0-based).
        """
        return self._post("/measurements/selected", json=index) is not None

    def nb_mesures(self) -> int:
        """Retourne le nombre de mesures ouvertes."""
        return len(self.lister_mesures())

    # ------------------------------------------------------------------
    # Donnees de mesure
    # ------------------------------------------------------------------

    def _rew_id(self, id_mesure) -> str:
        """Convertit un index 0-based en ID REW (1-based)."""
        if isinstance(id_mesure, int):
            return str(id_mesure + 1)
        return str(id_mesure)

    def get_reponse_frequentielle(
        self,
        id_mesure,
        smoothing: Optional[str] = None,
        ppo: Optional[int] = None,
    ) -> Optional[dict]:
        """Recupere la reponse en frequence (magnitude + phase).

        Args:
            id_mesure: index 0-based ou UUID de la mesure.
            smoothing: lissage (ex: "1/3", "1/6", "1/12", "1/24", "None").
            ppo: points par octave pour l'echantillonnage log (ex: 96).

        Returns:
            Dictionnaire avec 'frequences', 'magnitudes', 'phases' (NumPy arrays)
            ou None si erreur.
        """
        params = {}
        if smoothing is not None:
            params["smoothing"] = smoothing
        if ppo is not None:
            params["ppo"] = ppo

        rid = self._rew_id(id_mesure)
        data = self._get(f"/measurements/{rid}/frequency-response", params=params)
        if data is None:
            return None
        return decoder_reponse_frequentielle(data)

    def get_reponse_impulsionnelle(
        self,
        id_mesure,
        windowed: bool = False,
    ) -> Optional[dict]:
        """Recupere la reponse impulsionnelle.

        Args:
            id_mesure: index ou UUID de la mesure.
            windowed: appliquer le fenetrage IR.

        Returns:
            Dictionnaire avec 'echantillons' (NumPy), 'sample_rate', 'start_time'
            ou None si erreur.
        """
        params = {"windowed": str(windowed).lower()}
        rid = self._rew_id(id_mesure)
        data = self._get(f"/measurements/{rid}/impulse-response", params=params)
        if data is None:
            return None
        return decoder_reponse_impulsionnelle(data)

    def get_group_delay(
        self,
        id_mesure,
        smoothing: Optional[str] = None,
        ppo: Optional[int] = None,
    ) -> Optional[dict]:
        """Recupere le group delay.

        Args:
            id_mesure: index ou UUID de la mesure.
            smoothing: lissage.
            ppo: points par octave.

        Returns:
            Dictionnaire avec 'frequences' et 'group_delay' (en secondes, NumPy)
            ou None si erreur.
        """
        params = {}
        if smoothing is not None:
            params["smoothing"] = smoothing
        if ppo is not None:
            params["ppo"] = ppo

        rid = self._rew_id(id_mesure)
        data = self._get(f"/measurements/{rid}/group-delay", params=params)
        if data is None:
            return None
        return decoder_group_delay(data)

    # ------------------------------------------------------------------
    # EQ / Filtres
    # ------------------------------------------------------------------

    def get_filtres(self, id_mesure) -> Optional[list]:
        """Recupere les filtres EQ d'une mesure.

        Args:
            id_mesure: index ou UUID.

        Returns:
            Liste de dictionnaires FilterSetting.
        """
        data = self._get(f"/measurements/{self._rew_id(id_mesure)}/filters")
        if data is None:
            return None
        if isinstance(data, dict) and "filters" in data:
            return data["filters"]
        return data

    def get_egaliseur(self, id_mesure) -> Optional[dict]:
        """Recupere l'egaliseur associe a une mesure."""
        return self._get(f"/measurements/{self._rew_id(id_mesure)}/equaliser")

    def set_egaliseur(self, id_mesure, equaliser: str) -> bool:
        """Definit l'egaliseur pour une mesure.

        Args:
            id_mesure: index ou UUID.
            equaliser: nom de l'egaliseur (ex: "Generic").
        """
        return self._post(f"/measurements/{self._rew_id(id_mesure)}/equaliser", json=equaliser) is not None

    def get_egaliseurs_disponibles(self) -> List[str]:
        """Liste les egaliseurs disponibles dans REW."""
        data = self._get("/eq/equalisers")
        if data is None:
            return []
        if isinstance(data, list):
            return data
        return []

    # ------------------------------------------------------------------
    # Commandes EQ
    # ------------------------------------------------------------------

    def get_commandes_eq(self, id_mesure) -> List[str]:
        """Liste les commandes EQ disponibles pour une mesure."""
        data = self._get(f"/measurements/{self._rew_id(id_mesure)}/eq/commands")
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "commands" in data:
            return data["commands"]
        return []

    def executer_commande_eq(self, id_mesure, commande: str) -> bool:
        """Execute une commande EQ (Match Target, Optimise, etc.).

        Args:
            id_mesure: index ou UUID.
            commande: nom de la commande.
        """
        return self._post(f"/measurements/{self._rew_id(id_mesure)}/eq/command", json=commande) is not None

    # ------------------------------------------------------------------
    # Target / Courbe cible
    # ------------------------------------------------------------------

    def get_target_settings(self, id_mesure) -> Optional[dict]:
        """Recupere les reglages de la courbe cible."""
        return self._get(f"/measurements/{self._rew_id(id_mesure)}/target-settings")

    def set_target_settings(self, id_mesure, settings: dict) -> bool:
        """Definit les reglages de la courbe cible."""
        return self._post(f"/measurements/{self._rew_id(id_mesure)}/target-settings", json=settings) is not None

    def get_target_level(self, id_mesure) -> Optional[float]:
        """Recupere le niveau cible."""
        return self._get(f"/measurements/{self._rew_id(id_mesure)}/target-level")

    # ------------------------------------------------------------------
    # Alignment Tool (calage sub/top)
    # ------------------------------------------------------------------

    def get_alignment_mode(self) -> Optional[str]:
        """Recupere le mode d'alignement actuel."""
        return self._get("/alignment-tool/mode")

    def set_alignment_mode(self, mode: str) -> bool:
        """Definit le mode d'alignement (time, frequency, impulse)."""
        return self._post("/alignment-tool/mode", json=mode) is not None

    def set_alignment_frequency(self, freq_hz: float) -> bool:
        """Definit la frequence d'alignement (crossover)."""
        return self._post("/alignment-tool/frequency", json=freq_hz) is not None

    def set_alignment_mesures(self, index_a: int, index_b: int) -> bool:
        """Definit les deux mesures a aligner."""
        ok_a = self._post("/alignment-tool/index-a", json=index_a) is not None
        ok_b = self._post("/alignment-tool/index-b", json=index_b) is not None
        return ok_a and ok_b

    def set_alignment_delay(self, delay_a_ms: float = 0, delay_b_ms: float = 0) -> bool:
        """Definit les delays d'alignement en ms."""
        ok_a = self._post("/alignment-tool/delay-a", json=delay_a_ms) is not None
        ok_b = self._post("/alignment-tool/delay-b", json=delay_b_ms) is not None
        return ok_a and ok_b

    def set_alignment_invert(self, invert_a: bool = False, invert_b: bool = False) -> bool:
        """Inverse la polarite des mesures d'alignement."""
        ok_a = self._post("/alignment-tool/invert-a", json=invert_a) is not None
        ok_b = self._post("/alignment-tool/invert-b", json=invert_b) is not None
        return ok_a and ok_b

    def get_alignment_result(self) -> Optional[dict]:
        """Recupere le resultat de l'alignement (reponse sommee)."""
        return self._get("/alignment-tool/aligned-frequency-response")

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    def get_audio_status(self) -> Optional[dict]:
        """Recupere le statut audio (device, sample rate, etc.)."""
        return self._get("/audio")

    # ------------------------------------------------------------------
    # Mesure automatique (necessite REW Pro)
    # ------------------------------------------------------------------

    def get_sweep_config(self) -> Optional[dict]:
        """Recupere la configuration de sweep."""
        return self._get("/measure/sweep/configuration")

    def set_sweep_config(self, config: dict) -> bool:
        """Definit la configuration de sweep.

        Args:
            config: dict avec startFrequency, endFrequency, sweepLength, etc.
        """
        return self._post("/measure/sweep/configuration", json=config) is not None

    def lancer_mesure(self) -> bool:
        """Lance une mesure sweep (necessite REW Pro).

        Returns:
            True si la commande a ete acceptee, False sinon.
        """
        result = self._post("/measure/command", json="SPL")
        if result is None:
            logger.warning("Echec lancement mesure — licence REW Pro requise ?")
            return False
        return True

    # ------------------------------------------------------------------
    # Mode bloquant
    # ------------------------------------------------------------------

    def set_blocking(self, actif: bool = True) -> bool:
        """Active/desactive le mode bloquant.

        En mode bloquant, les reponses POST attendent la fin de l'operation.
        """
        return self._post("/application/blocking", json=actif) is not None

    # ------------------------------------------------------------------
    # IR Windows
    # ------------------------------------------------------------------

    def get_ir_windows(self, id_mesure) -> Optional[dict]:
        """Recupere les parametres de fenetrage IR."""
        return self._get(f"/measurements/{self._rew_id(id_mesure)}/ir-windows")

    def set_ir_windows(self, id_mesure, windows: dict) -> bool:
        """Definit les parametres de fenetrage IR."""
        return self._put(f"/measurements/{self._rew_id(id_mesure)}/ir-windows", json=windows) is not None

    # ------------------------------------------------------------------
    # Commandes de traitement
    # ------------------------------------------------------------------

    def get_commandes_mesure(self, id_mesure) -> List[str]:
        """Liste les commandes de traitement disponibles pour une mesure."""
        data = self._get(f"/measurements/{self._rew_id(id_mesure)}/commands")
        if data is None:
            return []
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "commands" in data:
            return data["commands"]
        return []

    def executer_commande_mesure(self, id_mesure, commande: str, params: Optional[dict] = None) -> bool:
        """Execute une commande de traitement sur une mesure."""
        payload = {"command": commande}
        if params:
            payload["parameters"] = params
        return self._post(f"/measurements/{self._rew_id(id_mesure)}/command", json=payload) is not None

    # ------------------------------------------------------------------
    # Helpers HTTP
    # ------------------------------------------------------------------

    def _get(self, endpoint: str, params: Optional[dict] = None) -> Optional[any]:
        """Requete GET."""
        try:
            r = self._session.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=self.timeout,
            )
            r.raise_for_status()
            return r.json()
        except requests.ConnectionError:
            logger.debug(f"REW non accessible sur {self.base_url}")
            return None
        except requests.Timeout:
            logger.warning(f"Timeout REW: {endpoint}")
            return None
        except requests.HTTPError as e:
            logger.warning(f"Erreur HTTP REW {endpoint}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Erreur REW {endpoint}: {e}")
            return None

    def _post(self, endpoint: str, json=None) -> Optional[any]:
        """Requete POST."""
        try:
            r = self._session.post(
                f"{self.base_url}{endpoint}",
                json=json,
                timeout=self.timeout,
            )
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                return {"status": "ok"}
        except requests.ConnectionError:
            logger.debug(f"REW non accessible sur {self.base_url}")
            return None
        except requests.Timeout:
            logger.warning(f"Timeout REW: {endpoint}")
            return None
        except requests.HTTPError as e:
            logger.warning(f"Erreur HTTP REW {endpoint}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Erreur REW {endpoint}: {e}")
            return None

    def _put(self, endpoint: str, json=None) -> Optional[any]:
        """Requete PUT."""
        try:
            r = self._session.put(
                f"{self.base_url}{endpoint}",
                json=json,
                timeout=self.timeout,
            )
            r.raise_for_status()
            try:
                return r.json()
            except ValueError:
                return {"status": "ok"}
        except Exception as e:
            logger.warning(f"Erreur REW PUT {endpoint}: {e}")
            return None

    def __repr__(self) -> str:
        connecte = self.est_connecte()
        return f"ClientREW({self.base_url}, connecte={connecte})"
