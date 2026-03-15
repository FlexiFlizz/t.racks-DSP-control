"""Driver USB HID pour les processeurs t.racks DSP 206.

Utilise la connexion USB HID au lieu de TCP Ethernet.
Meme protocole, transport different.
"""

import hid
import time
import logging
from typing import Dict, Optional, List

from backend.dsp.base import BaseDSP
from backend.models.filtre import FiltrePEQ, FiltreCrossover, TypeFiltre
from drivers.tracks_dsp206 import (
    construire_trame, analyser_trame,
    cmd_gain, cmd_mute, cmd_peq, cmd_hpf, cmd_lpf, cmd_delay,
    cmd_phase_invert, cmd_compressor, cmd_gate, cmd_limiter,
    cmd_test_tone, cmd_link, cmd_channel_name, cmd_matrice,
    cmd_geq,
    gain_brut_vers_db, freq_hz_vers_brut, peq_gain_db_vers_brut, q_vers_brut,
    CANAUX_ENTREE, CANAUX_SORTIE, TOUS_LES_CANAUX,
    PENTES_CROSSOVER, TYPES_PEQ,
    CMD_METERS, TRAME_KEEPALIVE,
    HEADER, FOOTER,
)

logger = logging.getLogger(__name__)

VID = 0x0168
PID = 0x0821


class TracksDSPHID(BaseDSP):
    """Driver USB HID pour t.racks DSP 206."""

    def __init__(self):
        self._dev: Optional[hid.device] = None
        self._connecte = False
        self._gains: Dict[str, float] = {}
        self._mutes: Dict[str, bool] = {}
        self._delays: Dict[str, float] = {}

    def connecter(self, host: str = "", port: int = 0) -> bool:
        """Connecte au DSP via USB HID. host/port ignores."""
        try:
            self._dev = hid.device()
            self._dev.open(VID, PID)
            self._dev.set_nonblocking(0)
            self._connecte = True

            # Handshake
            self._send(bytes([0x10, 0x02, 0x00, 0x01, 0x01, 0x10, 0x10, 0x03, 0x11]))

            logger.info("DSP 206 connecte en USB HID")

            # Init cache
            for canal in TOUS_LES_CANAUX:
                self._gains[canal] = 0.0
                self._mutes[canal] = False
                self._delays[canal] = 0.0

            return True
        except Exception as e:
            logger.error("Erreur connexion USB HID: %s", e)
            self._connecte = False
            return False

    def deconnecter(self):
        if self._dev:
            try:
                self._dev.close()
            except:
                pass
            self._dev = None
        self._connecte = False

    def est_connecte(self) -> bool:
        return self._connecte

    def get_nom_modele(self) -> str:
        return "DSP 206 (USB)"

    def get_canaux(self) -> Dict[str, int]:
        return dict(TOUS_LES_CANAUX)

    def get_canaux_entree(self) -> Dict[str, int]:
        return dict(CANAUX_ENTREE)

    def get_canaux_sortie(self) -> Dict[str, int]:
        return dict(CANAUX_SORTIE)

    def _send(self, data: bytes) -> Optional[bytes]:
        """Envoie une trame HID et retourne la reponse."""
        if not self._dev:
            return None
        packet = (bytes([0x00]) + data).ljust(65, b'\x00')
        self._dev.write(packet)
        time.sleep(0.1)
        rep = self._dev.read(64)
        return bytes(rep) if rep else None

    # -- Gain --
    def set_gain(self, canal: str, db: float):
        self._send(cmd_gain(canal, db))
        self._gains[canal] = db

    def get_gain(self, canal: str) -> float:
        return self._gains.get(canal, 0.0)

    # -- Mute --
    def set_mute(self, canal: str, mute: bool):
        self._send(cmd_mute(canal, mute))
        self._mutes[canal] = mute

    def get_mute(self, canal: str) -> bool:
        return self._mutes.get(canal, False)

    # -- Delay --
    def set_delay(self, canal: str, delay_ms: float):
        self._send(cmd_delay(canal, delay_ms))
        self._delays[canal] = delay_ms

    def get_delay(self, canal: str) -> float:
        return self._delays.get(canal, 0.0)

    # -- PEQ --
    def set_peq(self, canal: str, bande: int, filtre: FiltrePEQ):
        type_idx = TYPES_PEQ.get(filtre.type.value if hasattr(filtre.type, 'value') else str(filtre.type), 0)
        self._send(cmd_peq(
            canal, bande,
            gain_db=filtre.gain_db,
            freq_hz=filtre.frequence_hz,
            q=filtre.q,
            type_filtre=type_idx,
            bypass=not filtre.actif,
        ))

    def get_nb_bandes_peq(self, canal: str) -> int:
        if canal in CANAUX_ENTREE:
            return 8
        return 9

    # -- Crossover --
    def set_hpf(self, canal: str, filtre: FiltreCrossover):
        pente = filtre.pente.value if hasattr(filtre.pente, 'value') else str(filtre.pente)
        if filtre.actif:
            self._send(cmd_hpf(canal, filtre.frequence_hz, pente))
        else:
            self._send(cmd_hpf(canal, filtre.frequence_hz, "bypass"))

    def set_lpf(self, canal: str, filtre: FiltreCrossover):
        pente = filtre.pente.value if hasattr(filtre.pente, 'value') else str(filtre.pente)
        if filtre.actif:
            self._send(cmd_lpf(canal, filtre.frequence_hz, pente))
        else:
            self._send(cmd_lpf(canal, filtre.frequence_hz, "bypass"))

    # -- Phase --
    def set_polarite(self, canal: str, inversee: bool):
        self._send(cmd_phase_invert(canal, inversee))

    # -- Metres --
    def get_metres(self) -> Dict[str, float]:
        rep = self._send(TRAME_KEEPALIVE)
        if rep:
            from drivers.tracks_dsp206 import decoder_metres
            return decoder_metres(rep)
        return {}
