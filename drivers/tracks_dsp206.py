"""
Driver Python pour le processeur t.racks DSP 206 (Thomann/Musicrown).

Protocole reverse-engineere a partir du projet dsp-408-ui
(https://github.com/Aeternitaas/dsp-408-ui).

Le DSP 206 est un processeur 2 entrees / 6 sorties qui utilise le meme
protocole TCP que le DSP 408 (4 entrees / 8 sorties). La communication
se fait sur le port TCP 9761.

Format de trame :
    [0x10] [0x02] [DIR] [0x01] [LEN] [PAYLOAD...] [0x10] [0x03] [CHECKSUM]

    DIR      : 0x00 = hote vers appareil, 0x01 = appareil vers hote
    LEN      : nombre d'octets du payload (commande + donnees)
    CHECKSUM : XOR de tous les octets entre l'en-tete et le pied de trame,
               initialise a 1

Encodages principaux :
    Gain      : dB = (valeur_brute - 280) / 10.0
    Frequence PEQ : echelle log, 1000 pas
                    freq_hz = 19.70 * (20160 / 19.70) ^ (brut / 1000)
    Q PEQ     : echelle log, 256 pas
                    Q = 0.40 * (320.0) ^ (brut / 255)
    Gain PEQ/GEQ : dB = (valeur - 120) / 10.0
    Metres    : float16 IEEE 754 demi-precision, little-endian

Commandes principales :
    0x33 = PEQ paramétrique
    0x34 = Gain canal
    0x35 = Mute canal
    0x31 = Filtre passe-bas (LPF)
    0x32 = Filtre passe-haut (HPF)
    0x3a = Matrice de routage
    0x48 = GEQ graphique
    0x40 = Metres / keepalive

Adaptation DSP 206 (2-in / 6-out) :
    Entrees : In A (0x00), In B (0x01)
    Sorties : Out 1 (0x04) a Out 6 (0x09)
"""

import socket
import struct
import threading
import time
import math
import logging
from typing import Optional, List, Dict, Tuple, Callable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constantes du protocole
# ---------------------------------------------------------------------------

PORT_DEFAUT = 9761
TIMEOUT_CONNEXION = 5.0
TIMEOUT_REPONSE = 2.0
INTERVALLE_KEEPALIVE = 0.3  # 300 ms

# Octets de cadrage
HEADER = bytes([0x10, 0x02])
FOOTER = bytes([0x10, 0x03])

# Direction
DIR_HOTE_VERS_APPAREIL = 0x00
DIR_APPAREIL_VERS_HOTE = 0x01

# Codes de commande
CMD_HANDSHAKE = 0x10
CMD_DEVICE_INFO = 0x13
CMD_STATUS = 0x12
CMD_LOAD_PRESET = 0x20
CMD_STORE_SLOT = 0x21
CMD_CONFIG_CHUNK = 0x24
CMD_STORE_NAME = 0x26
CMD_GET_CONFIG = 0x27
CMD_GET_PRESET = 0x29
CMD_GET_ALL_PRESETS = 0x2C
CMD_LPF = 0x31
CMD_HPF = 0x32
CMD_PEQ = 0x33
CMD_COMPRESSOR = 0x30
CMD_GAIN = 0x34
CMD_MUTE = 0x35
CMD_PHASE_INVERT = 0x36
CMD_DELAY = 0x38
CMD_TEST_TONE = 0x39
CMD_MATRIX = 0x3A
CMD_LINK = 0x3B
CMD_CHANNEL_NAME = 0x3D
CMD_GATE = 0x3E
CMD_LIMITER = 0x3F
CMD_METERS = 0x40
CMD_GEQ = 0x48

# Canaux du DSP 206 (2 entrees, 6 sorties)
# Mapping verifie sur hardware reel (firmware V0104P)
# Le DSP 206 utilise des index sequentiels 0x00-0x07
# (different du DSP 408 qui utilise 0x00-0x03 + 0x04-0x0B)
CANAUX_ENTREE = {"In A": 0x00, "In B": 0x01}
CANAUX_SORTIE = {
    "Out 1": 0x02, "Out 2": 0x03, "Out 3": 0x04,
    "Out 4": 0x05, "Out 5": 0x06, "Out 6": 0x07,
}
TOUS_LES_CANAUX = {**CANAUX_ENTREE, **CANAUX_SORTIE}

# Index inverse (numero -> nom)
INDEX_VERS_NOM = {v: k for k, v in TOUS_LES_CANAUX.items()}

# Nombre de canaux pour les metres (2 entrees + 6 sorties = 8)
NB_CANAUX_METRES = 8

# Bits de routage matrice (entrees)
BITS_MATRICE_ENTREE = {"In A": 0x01, "In B": 0x02}

# Types de filtre PEQ
TYPES_PEQ = [
    "Peak", "Low Shelf", "High Shelf",
    "LP -6dB", "LP -12dB", "HP -6dB", "HP -12dB",
    "All Pass 1", "All Pass 2",
]

# Pentes de crossover HPF/LPF — verifie par capture Wireshark (2026-03-15)
# 0x00 = bypass (filtre desactive)
PENTES_CROSSOVER = {
    "bypass": 0x00,
    "BW -6": 0x01, "BL -6": 0x02,
    "BW -12": 0x03, "BL -12": 0x04, "LK -12": 0x05,
    "BW -18": 0x06, "BL -18": 0x07,
    "BW -24": 0x08, "BL -24": 0x09, "LK -24": 0x0A,
    "BW -30": 0x0B, "BL -30": 0x0C,
    "BW -36": 0x0D, "BL -36": 0x0E, "LK -36": 0x0F,
    "BW -42": 0x10, "BL -42": 0x11,
    "BW -48": 0x12, "BL -48": 0x13, "LK -48": 0x14,
}
# Index inverse pour decodage
PENTES_INDEX = {v: k for k, v in PENTES_CROSSOVER.items()}

# Parametres d'encodage frequence PEQ
# Le DSP 408 utilise 1000 pas : freq = 19.70 * (20160/19.70)^(brut/1000)
# Le DSP 206 (firmware V0104P) utilise 300 pas : freq = 20 * 1000^(brut/300)
# Verifie sur hardware reel le 2026-03-15
_FREQ_MIN = 19.70
_FREQ_MAX = 20160.0
_FREQ_RATIO = _FREQ_MAX / _FREQ_MIN
_FREQ_STEPS = 1000  # DSP 408
_FREQ_STEPS_206 = 300  # DSP 206

# Trames singleton preformatees
TRAME_HANDSHAKE = bytes([0x10, 0x02, 0x00, 0x01, 0x01, 0x10, 0x10, 0x03, 0x11])
TRAME_DEVICE_INFO = bytes([0x10, 0x02, 0x00, 0x01, 0x01, 0x13, 0x10, 0x03, 0x12])
TRAME_ALL_PRESETS = bytes([0x10, 0x02, 0x00, 0x01, 0x01, 0x2C, 0x10, 0x03, 0x2D])
TRAME_KEEPALIVE = bytes([0x10, 0x02, 0x00, 0x01, 0x01, 0x40, 0x10, 0x03, 0x41])


# ---------------------------------------------------------------------------
# Fonctions utilitaires d'encodage / decodage
# ---------------------------------------------------------------------------

def calculer_checksum(data_bytes: bytes) -> int:
    """Calcule le checksum XOR du protocole t.racks.

    Le checksum est le XOR de tous les octets de donnees
    (entre l'en-tete 10 02 et le pied de trame 10 03),
    initialise a 1.

    Args:
        data_bytes: octets de donnees (DIR, 0x01, LEN, PAYLOAD).

    Returns:
        Octet de checksum (0x00 - 0xFF).
    """
    checksum = 1
    for b in data_bytes:
        checksum ^= b
    return checksum & 0xFF


def construire_trame(payload: bytes, type_byte: int = 0x02) -> bytes:
    """Construit une trame complete a partir d'un payload.

    La trame inclut l'en-tete, la direction (hote -> appareil),
    le byte type, la longueur, le payload, le pied de trame et le checksum.

    Le Processor Editor utilise type_byte=0x02 pour toutes les commandes.
    Le DSP accepte aussi 0x01 mais 0x02 est le format officiel
    (verifie par capture Wireshark du PE, 2026-03-15).

    Args:
        payload: octets de commande + donnees (sans direction ni longueur).
        type_byte: byte type (0x02 par defaut, format officiel PE).

    Returns:
        Trame complete prete a envoyer sur le socket TCP.
    """
    longueur = len(payload)
    data_bytes = bytes([DIR_HOTE_VERS_APPAREIL, type_byte, longueur]) + payload
    checksum = calculer_checksum(data_bytes)
    return HEADER + data_bytes + FOOTER + bytes([checksum])


def analyser_trame(data: bytes) -> Optional[dict]:
    """Analyse une trame recue et extrait les champs.

    Args:
        data: octets bruts recus du socket.

    Returns:
        Dictionnaire avec les cles 'direction', 'commande', 'payload',
        'checksum_ok', ou None si la trame est invalide.
    """
    if len(data) < 6 or data[0] != 0x10 or data[1] != 0x02:
        return None

    # Trouver le pied de trame (10 03)
    footer_idx = -1
    for i in range(2, len(data) - 1):
        if data[i] == 0x10 and data[i + 1] == 0x03:
            footer_idx = i
            break

    if footer_idx < 0:
        return None

    direction = data[2]
    longueur = data[4]
    commande = data[5] if len(data) > 5 else None
    payload = data[6:footer_idx] if footer_idx > 6 else b""

    # Verifier le checksum
    data_region = data[2:footer_idx]
    checksum_attendu = calculer_checksum(data_region)
    checksum_recu = data[-1] if len(data) > footer_idx + 2 else None
    checksum_ok = (checksum_recu == checksum_attendu) if checksum_recu is not None else False

    return {
        "direction": direction,
        "longueur": longueur,
        "commande": commande,
        "payload": payload,
        "checksum_ok": checksum_ok,
        "brut": data,
    }


# -- Encodage / decodage gain --

def gain_db_vers_brut(db: float) -> int:
    """Convertit un gain en dB vers la valeur brute du protocole.

    Le protocole utilise deux plages de resolution :
    - En dessous de -20 dB : resolution 0.5 dB (2 unites par dB)
      Formule : valeur = (dB + 60) * 2  ->  -60 dB = 0, -20 dB = 80
    - Au dessus de -20 dB : resolution 0.1 dB (10 unites par dB)
      Formule : valeur = 80 + (dB + 20) * 10  ->  -20 dB = 80, +12 dB = 400

    La formule inverse (decodage) est : dB = (valeur - 280) / 10.0
    qui donne une approximation lineaire valable pour la plage fine.

    Plage pratique : -60.0 dB (brut=0) a +12.0 dB (brut=400).

    Args:
        db: gain en dB (typiquement -60.0 a +12.0).

    Returns:
        Valeur brute entiere 16 bits (minimum 0).
    """
    if db < -20.0:
        return max(0, round((db + 60) * 2))
    else:
        return max(0, round(80 + (db + 20) * 10))


def gain_brut_vers_db(valeur: int) -> float:
    """Convertit une valeur brute de gain vers des dB.

    Args:
        valeur: valeur brute 16 bits du protocole.

    Returns:
        Gain en dB.
    """
    return (valeur - 280) / 10.0


def quantifier_gain(db: float) -> float:
    """Quantifie un gain a la resolution du protocole.

    Args:
        db: gain en dB.

    Returns:
        Gain quantifie au pas le plus proche.
    """
    if db < -20.0:
        return round(db * 2) / 2.0
    else:
        return round(db * 10) / 10.0


# -- Encodage / decodage frequence PEQ --

def freq_brut_vers_hz(brut: int, dsp206: bool = True) -> float:
    """Convertit une valeur brute de frequence PEQ en Hz.

    DSP 206 : freq = 20 * 1000^(brut/300)  (300 pas, verifie hardware)
    DSP 408 : freq = 19.70 * (20160/19.70)^(brut/1000)  (1000 pas)

    Args:
        brut: valeur brute.
        dsp206: True pour l'encodage DSP 206, False pour DSP 408.

    Returns:
        Frequence en Hz.
    """
    if dsp206:
        brut = max(0, min(_FREQ_STEPS_206, brut))
        return 20.0 * (1000.0 ** (brut / _FREQ_STEPS_206))
    else:
        brut = max(0, min(_FREQ_STEPS, brut))
        return _FREQ_MIN * (_FREQ_RATIO ** (brut / _FREQ_STEPS))


def freq_hz_vers_brut(hz: float, dsp206: bool = True) -> int:
    """Convertit une frequence en Hz vers la valeur brute PEQ.

    DSP 206 : brut = 300 * log10(hz/20) / 3  (verifie hardware)
    DSP 408 : brut = 1000 * log(hz/19.70) / log(20160/19.70)

    Args:
        hz: frequence en Hz.
        dsp206: True pour l'encodage DSP 206.

    Returns:
        Valeur brute entiere.
    """
    if dsp206:
        if hz <= 20.0:
            return 0
        if hz >= 20000.0:
            return _FREQ_STEPS_206
        return max(0, min(_FREQ_STEPS_206,
                          round(_FREQ_STEPS_206 * math.log10(hz / 20.0) / 3.0)))
    else:
        if hz <= _FREQ_MIN:
            return 0
        if hz >= _FREQ_MAX:
            return _FREQ_STEPS
        return max(0, min(_FREQ_STEPS,
                          round(math.log(hz / _FREQ_MIN) / math.log(_FREQ_RATIO) * _FREQ_STEPS)))


# -- Encodage / decodage Q PEQ --

def q_brut_vers_q(brut: int) -> float:
    """Convertit une valeur brute de Q en facteur de qualite.

    Echelle logarithmique sur 256 pas :
        Q = 0.40 * 320.0 ^ (brut / 255)

    Args:
        brut: valeur brute 0-255.

    Returns:
        Facteur de qualite Q.
    """
    if brut <= 0:
        return 0.40
    if brut >= 255:
        return 128.0
    return 0.40 * (320.0 ** (brut / 255.0))


def q_vers_brut(q: float) -> int:
    """Convertit un facteur de qualite Q en valeur brute.

    Args:
        q: facteur de qualite (0.40 - 128.0).

    Returns:
        Valeur brute entiere 0-255.
    """
    if q <= 0.40:
        return 0
    if q >= 128.0:
        return 255
    return max(0, min(255,
                      round(math.log(q / 0.40) / math.log(320.0) * 255.0)))


# -- Encodage / decodage gain PEQ / GEQ --

def peq_gain_db_vers_brut(db: float) -> int:
    """Convertit un gain PEQ/GEQ en dB vers la valeur brute.

    Encodage lineaire : valeur = dB * 10 + 120
    Plage : -12.0 dB a +12.0 dB -> 0 a 240

    Args:
        db: gain en dB (-12.0 a +12.0).

    Returns:
        Valeur brute entiere 0-240.
    """
    return max(0, min(240, round(db * 10 + 120)))


def peq_gain_brut_vers_db(valeur: int) -> float:
    """Convertit une valeur brute PEQ/GEQ en gain dB.

    Args:
        valeur: valeur brute 0-240.

    Returns:
        Gain en dB.
    """
    return (valeur - 120) / 10.0


# -- Decodage float16 (metres) --

def decoder_float16(low: int, high: int) -> float:
    """Decode un float16 IEEE 754 demi-precision (little-endian).

    Utilise pour lire les niveaux des metres renvoyes par le DSP.

    Args:
        low: octet de poids faible.
        high: octet de poids fort.

    Returns:
        Valeur flottante decodee.
    """
    valeur = low | (high << 8)
    signe = (valeur >> 15) & 1
    exposant = (valeur >> 10) & 0x1F
    mantisse = valeur & 0x3FF

    if exposant == 0:
        # Sous-normal
        resultat = (mantisse / 1024.0) * (1.0 / 16384.0)
    elif exposant == 31:
        # Infini / NaN
        resultat = float("inf") if mantisse == 0 else float("nan")
    else:
        resultat = (1.0 + mantisse / 1024.0) * (2.0 ** (exposant - 15))

    return -resultat if signe else resultat


# ---------------------------------------------------------------------------
# Validation des canaux
# ---------------------------------------------------------------------------

def _valider_canal(canal: str) -> int:
    """Valide un nom de canal et retourne son index protocole.

    Args:
        canal: nom du canal (ex: 'In A', 'Out 3').

    Returns:
        Index protocole du canal.

    Raises:
        ValueError: si le canal n'est pas valide pour le DSP 206.
    """
    if canal not in TOUS_LES_CANAUX:
        canaux_valides = ", ".join(sorted(TOUS_LES_CANAUX.keys()))
        raise ValueError(
            f"Canal invalide : '{canal}'. "
            f"Canaux valides pour le DSP 206 : {canaux_valides}"
        )
    return TOUS_LES_CANAUX[canal]


def _valider_canal_entree(canal: str) -> int:
    """Valide un canal d'entree.

    Args:
        canal: nom du canal d'entree.

    Returns:
        Index protocole.

    Raises:
        ValueError: si ce n'est pas un canal d'entree du DSP 206.
    """
    if canal not in CANAUX_ENTREE:
        raise ValueError(
            f"Canal d'entree invalide : '{canal}'. "
            f"Entrees du DSP 206 : In A, In B"
        )
    return CANAUX_ENTREE[canal]


def _valider_canal_sortie(canal: str) -> int:
    """Valide un canal de sortie.

    Args:
        canal: nom du canal de sortie.

    Returns:
        Index protocole.

    Raises:
        ValueError: si ce n'est pas un canal de sortie du DSP 206.
    """
    if canal not in CANAUX_SORTIE:
        sorties = ", ".join(sorted(CANAUX_SORTIE.keys()))
        raise ValueError(
            f"Canal de sortie invalide : '{canal}'. "
            f"Sorties du DSP 206 : {sorties}"
        )
    return CANAUX_SORTIE[canal]


# ---------------------------------------------------------------------------
# Construction de commandes
# ---------------------------------------------------------------------------

def cmd_gain(canal: str, db: float) -> bytes:
    """Construit la commande de reglage de gain d'un canal.

    Protocole : 10 02 00 01 04 34 [canal] [val_lo] [val_hi] 10 03 [chk]

    Args:
        canal: nom du canal (ex: 'Out 1').
        db: gain en dB.

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    db_q = quantifier_gain(db)
    valeur = gain_db_vers_brut(db_q)
    val_lo = valeur & 0xFF
    val_hi = (valeur >> 8) & 0xFF
    return construire_trame(bytes([CMD_GAIN, idx, val_lo, val_hi]))


def cmd_mute(canal: str, mute: bool) -> bytes:
    """Construit la commande mute/unmute d'un canal.

    Protocole : 10 02 00 01 03 35 [canal] [0x01|0x00] 10 03 [chk]

    Args:
        canal: nom du canal.
        mute: True pour couper, False pour reactiver.

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    return construire_trame(bytes([CMD_MUTE, idx, 0x01 if mute else 0x00]))


def cmd_peq(canal: str, bande: int, gain_db: float,
            freq_hz: float, q: float,
            type_filtre: int = 0, bypass: bool = False) -> bytes:
    """Construit la commande de reglage d'une bande PEQ.

    Protocole :
        10 02 00 01 0a 33 [ch] [band] [gain] [00]
        [freq_lo] [freq_hi] [Q] [type] [bypass] 10 03 [chk]

    Le DSP 206 a 8 bandes PEQ par entree et 9 par sortie.

    Args:
        canal: nom du canal.
        bande: index de bande (0-7 pour entrees, 0-8 pour sorties).
        gain_db: gain en dB (-12.0 a +12.0).
        freq_hz: frequence en Hz (19.70 a 20160.0).
        q: facteur de qualite (0.40 a 128.0).
        type_filtre: type de filtre (0=Peak, 1=Low Shelf, 2=High Shelf,
                     3=LP -6dB, 4=LP -12dB, 5=HP -6dB, 6=HP -12dB,
                     7=All Pass 1, 8=All Pass 2).
        bypass: True pour contourner cette bande.

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)

    # Valider le numero de bande
    max_bandes = 8 if canal in CANAUX_ENTREE else 9
    if not 0 <= bande < max_bandes:
        raise ValueError(
            f"Bande PEQ invalide : {bande}. "
            f"Plage valide pour {canal} : 0-{max_bandes - 1}"
        )

    gain_val = peq_gain_db_vers_brut(gain_db)
    freq_brut = freq_hz_vers_brut(freq_hz, dsp206=True)
    q_val = q_vers_brut(q)

    # Format DSP 206 (verifie sur hardware, 2026-03-15) :
    # Chaque parametre sur 2 octets LE (gain, freq, Q)
    # Pas de padding 0x00 entre gain et freq
    return construire_trame(bytes([
        CMD_PEQ, idx, bande,
        gain_val & 0xFF, (gain_val >> 8) & 0xFF,
        freq_brut & 0xFF, (freq_brut >> 8) & 0xFF,
        q_val & 0xFF, (q_val >> 8) & 0xFF,
    ]))


def cmd_hpf(canal: str, freq_hz: float, pente: str = "BW -24") -> bytes:
    """Construit la commande de filtre passe-haut (HPF).

    Verifie par capture Wireshark du PE (2026-03-15).
    Protocole : cmd ch freq_lo freq_hi slope

    Args:
        canal: nom du canal.
        freq_hz: frequence de coupure en Hz.
        pente: nom de la pente (ex: "BW -24", "LK -48", "bypass").

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    if pente == "bypass":
        slope = 0x00
    else:
        if pente not in PENTES_CROSSOVER:
            raise ValueError(f"Pente invalide : '{pente}'. Valides : {list(PENTES_CROSSOVER.keys())}")
        slope = PENTES_CROSSOVER[pente]
    freq_brut = freq_hz_vers_brut(freq_hz, dsp206=True)
    return construire_trame(bytes([
        CMD_HPF, idx, freq_brut & 0xFF, (freq_brut >> 8) & 0xFF, slope,
    ]))


def cmd_lpf(canal: str, freq_hz: float, pente: str = "BW -24") -> bytes:
    """Construit la commande de filtre passe-bas (LPF).

    Verifie par capture Wireshark du PE (2026-03-15).
    Protocole : cmd ch freq_lo freq_hi slope

    Args:
        canal: nom du canal.
        freq_hz: frequence de coupure en Hz.
        pente: nom de la pente (ex: "BW -24", "LK -48", "bypass").

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    if pente == "bypass":
        slope = 0x00
    else:
        if pente not in PENTES_CROSSOVER:
            raise ValueError(f"Pente invalide : '{pente}'. Valides : {list(PENTES_CROSSOVER.keys())}")
        slope = PENTES_CROSSOVER[pente]
    freq_brut = freq_hz_vers_brut(freq_hz, dsp206=True)
    return construire_trame(bytes([
        CMD_LPF, idx, freq_brut & 0xFF, (freq_brut >> 8) & 0xFF, slope,
    ]))


def cmd_matrice(sortie: str, masque_entrees: int) -> bytes:
    """Construit la commande de routage matrice.

    Protocole : 10 02 00 01 03 3a [sortie] [masque] 10 03 [chk]

    Le masque d'entrees est un champ de bits :
        0x01 = In A, 0x02 = In B

    Args:
        sortie: nom du canal de sortie (ex: 'Out 1').
        masque_entrees: masque binaire des entrees a router.

    Returns:
        Trame complete.
    """
    idx = _valider_canal_sortie(sortie)
    return construire_trame(bytes([CMD_MATRIX, idx, masque_entrees & 0xFF]))


def cmd_geq(canal: str, bande: int, db: float) -> bytes:
    """Construit la commande de reglage d'une bande GEQ (31 bandes).

    Protocole : 10 02 00 01 05 48 [ch] [bande] [valeur] [00] 10 03 [chk]

    Le GEQ est disponible uniquement sur les canaux d'entree.

    Args:
        canal: nom du canal d'entree ('In A' ou 'In B').
        bande: index de bande (0-30, 20 Hz a 20 kHz en tiers d'octave).
        db: gain en dB (-12.0 a +12.0).

    Returns:
        Trame complete.
    """
    idx = _valider_canal_entree(canal)
    if not 0 <= bande <= 30:
        raise ValueError(f"Bande GEQ invalide : {bande}. Plage : 0-30")
    valeur = peq_gain_db_vers_brut(db)
    return construire_trame(bytes([CMD_GEQ, idx, bande, valeur, 0x00]))


def cmd_delay(canal: str, delay_ms: float) -> bytes:
    """Construit la commande de reglage du delay d'un canal.

    Verifie sur hardware reel (DSP 206 firmware V0104P, 2026-03-15)
    via capture Wireshark du Processor Editor.

    Commande : 0x38
    Encodage : valeur_brute = delay_ms * 96 (base 96 kHz interne)
    Particularite : le byte type dans la trame est 0x02 (pas 0x01)

    Args:
        canal: nom du canal de sortie.
        delay_ms: delay en millisecondes (0.0 a 300.0 ms typiquement).

    Returns:
        Trame complete.

    Raises:
        ValueError: si le canal est invalide ou le delay hors plage.
    """
    idx = _valider_canal(canal)
    if delay_ms < 0 or delay_ms > 1000.0:
        raise ValueError(
            f"Delay hors plage : {delay_ms} ms. Plage typique : 0-300 ms"
        )
    valeur = round(delay_ms * 96)
    val_lo = valeur & 0xFF
    val_hi = (valeur >> 8) & 0xFF
    return construire_trame(bytes([CMD_DELAY, idx, val_lo, val_hi]))


def cmd_phase_invert(canal: str, inverser: bool) -> bytes:
    """Construit la commande d'inversion de phase.

    Verifie par capture Wireshark du PE (2026-03-15).
    Commande : 0x36

    Args:
        canal: nom du canal.
        inverser: True pour inverser la phase.

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    return construire_trame(bytes([CMD_PHASE_INVERT, idx, 0x01 if inverser else 0x00]))


def cmd_compressor(canal: str, ratio: int = 0, attack_ms: float = 100,
                   release_ms: float = 500, knee_db: int = 0,
                   threshold_db: float = 0.0) -> bytes:
    """Construit la commande du compresseur.

    Verifie et calibre par captures Wireshark du PE (2026-03-15).
    Commande : 0x30
    Layout : cmd ch ratio(2B) attack(2B) release(2B) knee(2B) threshold(2B)

    Encodages :
        ratio : index 0-15 (0=off/1:1, 1=1.2:1, ... 15=inf:1)
        attack : brut = ms - 1
        release : brut = ms - 1
        knee : brut = dB (direct)
        threshold : brut = dB * 2 + 180

    Args:
        canal: nom du canal de sortie.
        ratio: index de ratio (0=off, 1-15).
        attack_ms: temps d'attack en ms.
        release_ms: temps de release en ms.
        knee_db: knee en dB (0=hard).
        threshold_db: seuil en dB (-90 a +20).

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    atk = max(0, round(attack_ms - 1))
    rel = max(0, round(release_ms - 1))
    knee = max(0, round(knee_db))
    thresh = max(0, round(threshold_db * 2 + 180))
    return construire_trame(bytes([
        CMD_COMPRESSOR, idx,
        ratio & 0xFF, (ratio >> 8) & 0xFF,
        atk & 0xFF, (atk >> 8) & 0xFF,
        rel & 0xFF, (rel >> 8) & 0xFF,
        knee & 0xFF, (knee >> 8) & 0xFF,
        thresh & 0xFF, (thresh >> 8) & 0xFF,
    ]))


def cmd_gate(canal: str, attack_ms: float = 100, release_ms: float = 100,
             hold_ms: float = 100, threshold_db: float = -90.0) -> bytes:
    """Construit la commande du gate (entrees uniquement).

    Verifie et calibre par captures Wireshark du PE (2026-03-15).
    Commande : 0x3E
    Layout : cmd ch attack(2B) release(2B) hold(2B) threshold(2B)

    Encodages :
        attack : brut = ms - 1 (non-lineaire en dessous de 1ms)
        release : brut = ms - 1
        hold : brut = ms - 1
        threshold : brut = dB * 2 + 180

    Args:
        canal: nom du canal d'entree ('In A' ou 'In B').
        attack_ms: temps d'attack en ms.
        release_ms: temps de release en ms.
        hold_ms: temps de hold en ms.
        threshold_db: seuil en dB (-90 a 0).

    Returns:
        Trame complete.
    """
    idx = _valider_canal_entree(canal)
    atk = max(0, round(attack_ms - 1))
    rel = max(0, round(release_ms - 1))
    hold = max(0, round(hold_ms - 1))
    thresh = max(0, round(threshold_db * 2 + 180))
    return construire_trame(bytes([
        CMD_GATE, idx,
        atk & 0xFF, (atk >> 8) & 0xFF,
        rel & 0xFF, (rel >> 8) & 0xFF,
        hold & 0xFF, (hold >> 8) & 0xFF,
        thresh & 0xFF, (thresh >> 8) & 0xFF,
    ]))


def cmd_limiter(canal: str, attack_ms: float = 500, release_ms: float = 500,
                param3: int = 0, threshold_db: float = 20.0) -> bytes:
    """Construit la commande du limiteur.

    Verifie et calibre par captures Wireshark du PE (2026-03-15).
    Commande : 0x3F
    Layout : cmd ch attack(2B) release(2B) ??(2B) threshold(2B)

    Encodages :
        attack : brut = ms - 1
        release : brut = ms - 1
        threshold : brut = dB * 2 + 180

    Args:
        canal: nom du canal de sortie.
        attack_ms: temps d'attack en ms.
        release_ms: temps de release en ms.
        param3: parametre inconnu (toujours 0).
        threshold_db: seuil en dB (-90 a +20).

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    atk = max(0, round(attack_ms - 1))
    rel = max(0, round(release_ms - 1))
    thresh = max(0, round(threshold_db * 2 + 180))
    return construire_trame(bytes([
        CMD_LIMITER, idx,
        atk & 0xFF, (atk >> 8) & 0xFF,
        rel & 0xFF, (rel >> 8) & 0xFF,
        param3 & 0xFF, (param3 >> 8) & 0xFF,
        thresh & 0xFF, (thresh >> 8) & 0xFF,
    ]))


def cmd_test_tone(tone_type: int = 0, param: int = 0) -> bytes:
    """Construit la commande du generateur de test.

    Verifie par capture Wireshark du PE (2026-03-15).
    Commande : 0x39

    Types :
        0 = OFF
        1 = Pink noise
        2 = White noise
        3 = Sine (param = index de frequence)

    Args:
        tone_type: type de signal (0=off, 1=pink, 2=white, 3=sine).
        param: parametre additionnel (index freq pour sine).

    Returns:
        Trame complete.
    """
    return construire_trame(bytes([CMD_TEST_TONE, tone_type, param]))


def cmd_link(canal: str, mask: int) -> bytes:
    """Construit la commande de link entre canaux.

    Verifie par capture Wireshark du PE (2026-03-15).
    Commande : 0x3B

    Args:
        canal: nom du canal.
        mask: bitmask de link.

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    return construire_trame(bytes([CMD_LINK, idx, mask]))


def cmd_channel_name(canal: str, nom: str) -> bytes:
    """Construit la commande de renommage de canal.

    Verifie par capture Wireshark du PE (2026-03-15).
    Commande : 0x3D

    Args:
        canal: nom du canal.
        nom: nouveau nom (max 8 caracteres ASCII).

    Returns:
        Trame complete.
    """
    idx = _valider_canal(canal)
    nom_bytes = nom.encode("ascii", errors="replace")[:8].ljust(8, b"\x00")
    return construire_trame(bytes([CMD_CHANNEL_NAME, idx]) + nom_bytes)


# ---------------------------------------------------------------------------
# Decodage des reponses
# ---------------------------------------------------------------------------

def decoder_metres(data: bytes) -> Dict[str, float]:
    """Decode les niveaux de metres a partir d'une reponse keepalive.

    Le DSP renvoie les niveaux de tous les canaux en float16 IEEE 754.
    Chaque canal occupe 3 octets : [float16_lo] [float16_hi] [peak_byte].

    Pour le DSP 206, seuls les 8 premiers canaux sont utilises
    (2 entrees + 6 sorties).

    Args:
        data: trame brute recue du DSP (reponse a la commande 0x40).

    Returns:
        Dictionnaire {nom_canal: niveau_lineaire}.
        Les valeurs NaN (recalcul PEQ en cours) sont remplacees par 0.0.
    """
    niveaux = {}
    # Les donnees commencent a l'octet 6 (apres 10 02 01 00 XX 40)
    offset_debut = 6
    # Ordre des metres dans la reponse du DSP 206
    # Correspond au mapping sequentiel 0x00-0x07
    canaux_ordre = ["In A", "In B",
                    "Out 1", "Out 2", "Out 3", "Out 4", "Out 5", "Out 6"]

    for i, nom in enumerate(canaux_ordre):
        offset = offset_debut + i * 3
        if offset + 2 <= len(data):
            niveau = decoder_float16(data[offset], data[offset + 1])
            niveaux[nom] = niveau if math.isfinite(niveau) else 0.0
        else:
            niveaux[nom] = 0.0

    return niveaux


# ---------------------------------------------------------------------------
# Classe principale du driver
# ---------------------------------------------------------------------------

class TracksDSP206:
    """Driver de controle pour le processeur t.racks DSP 206.

    Gere la connexion TCP, le keepalive, l'envoi de commandes
    et la reception des reponses.

    Exemple d'utilisation :
        dsp = TracksDSP206("192.168.1.100")
        dsp.connecter()
        dsp.set_gain("Out 1", -6.0)
        dsp.set_mute("Out 2", True)
        dsp.set_peq("Out 1", bande=0, gain_db=-3.0,
                     freq_hz=250.0, q=2.0)
        metres = dsp.get_meters()
        dsp.deconnecter()

    Attributes:
        hote: adresse IP du DSP.
        port: port TCP (defaut 9761).
        connecte: True si la connexion est active.
    """

    def __init__(self, hote: str, port: int = PORT_DEFAUT,
                 timeout: float = TIMEOUT_CONNEXION):
        """Initialise le driver.

        Args:
            hote: adresse IP du processeur DSP 206.
            port: port TCP (defaut : 9761).
            timeout: timeout de connexion en secondes.
        """
        self.hote = hote
        self.port = port
        self.timeout = timeout

        self._socket: Optional[socket.socket] = None
        self._connecte = False
        self._lock = threading.Lock()

        # Thread de keepalive
        self._keepalive_actif = False
        self._thread_keepalive: Optional[threading.Thread] = None
        self._intervalle_keepalive = INTERVALLE_KEEPALIVE

        # Callback pour les metres
        self._callback_metres: Optional[Callable[[Dict[str, float]], None]] = None

        # Derniers niveaux de metres recus
        self.derniers_metres: Dict[str, float] = {}

        # Informations appareil
        self.nom_appareil: str = ""

    @property
    def connecte(self) -> bool:
        """Indique si la connexion TCP est active."""
        return self._connecte

    # -- Connexion / deconnexion --

    def connecter(self) -> bool:
        """Etablit la connexion TCP et envoie le handshake.

        Envoie la commande de handshake puis demarre le thread
        de keepalive pour maintenir la connexion active.

        Returns:
            True si la connexion est etablie avec succes.

        Raises:
            ConnectionError: si la connexion echoue.
        """
        if self._connecte:
            logger.warning("Deja connecte a %s:%d", self.hote, self.port)
            return True

        try:
            logger.info("Connexion a %s:%d ...", self.hote, self.port)
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.hote, self.port))
            self._connecte = True

            # Envoyer le handshake
            self._envoyer_brut(TRAME_HANDSHAKE)
            reponse = self._recevoir()
            if reponse:
                logger.info("Handshake OK")
            else:
                logger.warning("Pas de reponse au handshake")

            # Demander les infos appareil
            self._envoyer_brut(TRAME_DEVICE_INFO)
            reponse = self._recevoir()
            if reponse:
                trame = analyser_trame(reponse)
                if trame and trame["commande"] == CMD_DEVICE_INFO:
                    self.nom_appareil = trame["payload"].decode(
                        "latin-1", errors="replace"
                    ).strip().rstrip("\x00")
                    logger.info("Appareil detecte : %s", self.nom_appareil)

            # Demarrer le keepalive
            self._demarrer_keepalive()

            logger.info("Connecte a %s (%s)", self.hote, self.nom_appareil)
            return True

        except (socket.error, OSError) as e:
            self._connecte = False
            if self._socket:
                try:
                    self._socket.close()
                except OSError:
                    pass
                self._socket = None
            raise ConnectionError(
                f"Impossible de se connecter a {self.hote}:{self.port} : {e}"
            ) from e

    def deconnecter(self):
        """Ferme proprement la connexion TCP et arrete le keepalive."""
        self._arreter_keepalive()

        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except OSError:
                    pass
                self._socket = None
            self._connecte = False

        logger.info("Deconnecte de %s", self.hote)

    # -- Envoi / reception bas niveau --

    def _envoyer_brut(self, data: bytes):
        """Envoie des octets bruts sur le socket.

        Args:
            data: octets a envoyer.

        Raises:
            ConnectionError: si le socket n'est pas connecte.
        """
        with self._lock:
            if not self._socket or not self._connecte:
                raise ConnectionError("Non connecte")
            try:
                self._socket.sendall(data)
                logger.debug("Tx: %s", data.hex(" "))
            except (socket.error, OSError) as e:
                self._connecte = False
                raise ConnectionError(f"Erreur d'envoi : {e}") from e

    def _recevoir(self, timeout: float = TIMEOUT_REPONSE) -> Optional[bytes]:
        """Recoit des donnees du socket avec timeout.

        Args:
            timeout: duree maximale d'attente en secondes.

        Returns:
            Octets recus, ou None en cas de timeout.
        """
        with self._lock:
            if not self._socket or not self._connecte:
                return None
            try:
                self._socket.settimeout(timeout)
                data = self._socket.recv(4096)
                if data:
                    logger.debug("Rx: %s", data.hex(" "))
                return data if data else None
            except socket.timeout:
                return None
            except (socket.error, OSError) as e:
                logger.error("Erreur de reception : %s", e)
                self._connecte = False
                return None

    def _envoyer_commande(self, trame: bytes,
                          attendre_reponse: bool = True) -> Optional[bytes]:
        """Envoie une commande et attend optionnellement la reponse.

        Args:
            trame: trame complete a envoyer.
            attendre_reponse: si True, attend et retourne la reponse.

        Returns:
            Reponse brute ou None.
        """
        self._envoyer_brut(trame)
        if attendre_reponse:
            return self._recevoir()
        return None

    # -- Keepalive --

    def _demarrer_keepalive(self):
        """Demarre le thread de keepalive periodique.

        Envoie la commande metres (0x40) a intervalle regulier
        pour maintenir la connexion et recuperer les niveaux.
        """
        self._keepalive_actif = True
        self._thread_keepalive = threading.Thread(
            target=self._boucle_keepalive,
            daemon=True,
            name="dsp206-keepalive",
        )
        self._thread_keepalive.start()

    def _arreter_keepalive(self):
        """Arrete le thread de keepalive."""
        self._keepalive_actif = False
        if self._thread_keepalive and self._thread_keepalive.is_alive():
            self._thread_keepalive.join(timeout=2.0)
        self._thread_keepalive = None

    def _boucle_keepalive(self):
        """Boucle du thread keepalive.

        Envoie periodiquement la commande metres et decode la reponse.
        """
        while self._keepalive_actif and self._connecte:
            try:
                reponse = self._envoyer_commande(TRAME_KEEPALIVE)
                if reponse:
                    trame = analyser_trame(reponse)
                    if trame and trame["commande"] == CMD_METERS:
                        self.derniers_metres = decoder_metres(reponse)
                        if self._callback_metres:
                            self._callback_metres(self.derniers_metres)
            except ConnectionError:
                logger.error("Perte de connexion pendant le keepalive")
                self._connecte = False
                break
            except Exception as e:
                logger.debug("Erreur keepalive : %s", e)

            time.sleep(self._intervalle_keepalive)

    def on_metres(self, callback: Optional[Callable[[Dict[str, float]], None]]):
        """Enregistre un callback appele a chaque reception de metres.

        Args:
            callback: fonction recevant un dict {canal: niveau_lineaire},
                      ou None pour desactiver.
        """
        self._callback_metres = callback

    # -- Methodes de haut niveau --

    def set_gain(self, canal: str, db: float):
        """Regle le gain d'un canal.

        Args:
            canal: nom du canal (ex: 'In A', 'Out 3').
            db: gain en dB (typiquement -72.0 a +12.0).
        """
        logger.info("Set gain %s = %.1f dB", canal, db)
        self._envoyer_commande(cmd_gain(canal, db), attendre_reponse=False)

    def set_mute(self, canal: str, mute: bool):
        """Active ou desactive le mute d'un canal.

        Args:
            canal: nom du canal.
            mute: True pour couper, False pour reactiver.
        """
        etat = "MUTE" if mute else "UNMUTE"
        logger.info("Set %s %s", canal, etat)
        self._envoyer_commande(cmd_mute(canal, mute), attendre_reponse=False)

    def set_peq(self, canal: str, bande: int, gain_db: float,
                freq_hz: float, q: float,
                type_filtre: int = 0, bypass: bool = False):
        """Configure une bande d'egalisation parametrique (PEQ).

        Privilegier l'EQ soustractif : couper les pics plutot que
        booster les creux.

        Args:
            canal: nom du canal.
            bande: index de bande (0-7 entrees, 0-8 sorties).
            gain_db: gain en dB (-12.0 a +12.0).
            freq_hz: frequence centrale en Hz (19.70 a 20160.0).
            q: facteur de qualite (0.40 a 128.0).
            type_filtre: type (0=Peak, 1=LowShelf, 2=HighShelf,
                         3-4=LP, 5-6=HP, 7-8=AllPass).
            bypass: True pour contourner cette bande.
        """
        logger.info(
            "Set PEQ %s bande %d : %.1f dB @ %.0f Hz Q=%.1f type=%d%s",
            canal, bande, gain_db, freq_hz, q, type_filtre,
            " [BYPASS]" if bypass else "",
        )
        self._envoyer_commande(
            cmd_peq(canal, bande, gain_db, freq_hz, q, type_filtre, bypass),
            attendre_reponse=False,
        )

    def set_hpf(self, canal: str, freq_hz: float, actif: bool = True):
        """Configure le filtre passe-haut (HPF).

        Args:
            canal: nom du canal.
            freq_hz: frequence de coupure en Hz.
            actif: True pour activer.
        """
        logger.info("Set HPF %s = %.0f Hz (%s)", canal, freq_hz,
                     "ON" if actif else "OFF")
        self._envoyer_commande(
            cmd_hpf(canal, freq_hz, actif),
            attendre_reponse=False,
        )

    def set_lpf(self, canal: str, freq_hz: float, pente: int = 0,
                actif: bool = True):
        """Configure le filtre passe-bas (LPF).

        Args:
            canal: nom du canal.
            freq_hz: frequence de coupure en Hz.
            pente: index de pente (0-19).
            actif: True pour activer.
        """
        logger.info("Set LPF %s = %.0f Hz pente=%d (%s)", canal, freq_hz,
                     pente, "ON" if actif else "OFF")
        self._envoyer_commande(
            cmd_lpf(canal, freq_hz, pente, actif),
            attendre_reponse=False,
        )

    def set_matrice(self, sortie: str, entrees: List[str]):
        """Configure le routage matrice pour une sortie.

        Args:
            sortie: canal de sortie (ex: 'Out 1').
            entrees: liste des entrees a router (ex: ['In A', 'In B']).
        """
        masque = 0
        for entree in entrees:
            if entree not in BITS_MATRICE_ENTREE:
                raise ValueError(f"Entree invalide pour la matrice : '{entree}'")
            masque |= BITS_MATRICE_ENTREE[entree]

        logger.info("Set matrice %s <- %s (masque=0x%02X)",
                     sortie, ", ".join(entrees) if entrees else "aucune", masque)
        self._envoyer_commande(
            cmd_matrice(sortie, masque),
            attendre_reponse=False,
        )

    def set_geq(self, canal: str, bande: int, db: float):
        """Regle une bande du GEQ 31 bandes (entrees seulement).

        Args:
            canal: canal d'entree ('In A' ou 'In B').
            bande: index de bande (0-30).
            db: gain en dB (-12.0 a +12.0).
        """
        logger.info("Set GEQ %s bande %d = %.1f dB", canal, bande, db)
        self._envoyer_commande(
            cmd_geq(canal, bande, db),
            attendre_reponse=False,
        )

    def set_delay(self, canal: str, delay_ms: float):
        """Regle le delay d'un canal.

        ATTENTION : commande non verifiee, basee sur une analyse
        partielle du protocole. A tester avec precaution.

        Args:
            canal: nom du canal.
            delay_ms: delay en millisecondes.
        """
        logger.warning(
            "Set delay %s = %.1f ms (commande non verifiee !)",
            canal, delay_ms,
        )
        self._envoyer_commande(
            cmd_delay(canal, delay_ms),
            attendre_reponse=False,
        )

    def get_meters(self) -> Dict[str, float]:
        """Interroge les metres du DSP et retourne les niveaux actuels.

        Envoie une commande metres (0x40) et decode la reponse.
        Le keepalive met aussi a jour self.derniers_metres en continu.

        Returns:
            Dictionnaire {nom_canal: niveau_lineaire}.
        """
        try:
            reponse = self._envoyer_commande(TRAME_KEEPALIVE)
            if reponse:
                trame = analyser_trame(reponse)
                if trame and trame["commande"] == CMD_METERS:
                    self.derniers_metres = decoder_metres(reponse)
                    return self.derniers_metres
        except ConnectionError:
            logger.error("Erreur lors de la lecture des metres")

        return self.derniers_metres

    # -- Gestion de contexte (with) --

    def __enter__(self):
        """Permet l'utilisation avec 'with'."""
        self.connecter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Deconnexion automatique a la sortie du bloc 'with'."""
        self.deconnecter()
        return False

    def __repr__(self):
        etat = "connecte" if self._connecte else "deconnecte"
        nom = f" ({self.nom_appareil})" if self.nom_appareil else ""
        return f"<TracksDSP206 {self.hote}:{self.port} [{etat}]{nom}>"


# ---------------------------------------------------------------------------
# Demo / test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Driver t.racks DSP 206 - test de connexion et commandes",
    )
    parser.add_argument(
        "ip",
        nargs="?",
        default="192.168.1.100",
        help="Adresse IP du DSP 206 (defaut: 192.168.1.100)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=PORT_DEFAUT,
        help=f"Port TCP (defaut: {PORT_DEFAUT})",
    )
    parser.add_argument(
        "--test-hors-ligne",
        action="store_true",
        help="Executer les tests d'encodage sans connexion reseau",
    )
    args = parser.parse_args()

    # -- Tests d'encodage (toujours executes) --
    print("=" * 60)
    print("  Tests d'encodage du protocole t.racks DSP")
    print("=" * 60)

    # Test checksum
    print("\n--- Checksum ---")
    # Handshake : data = [0x00, 0x01, 0x01, 0x10], checksum attendu = 0x11
    data_hs = bytes([0x00, 0x01, 0x01, 0x10])
    chk = calculer_checksum(data_hs)
    print(f"  Handshake checksum : 0x{chk:02X} (attendu: 0x11) "
          f"{'OK' if chk == 0x11 else 'ERREUR'}")

    # Test gain
    print("\n--- Gain ---")
    for db in [-60.0, -40.0, -20.0, -6.0, 0.0, 6.0, 12.0]:
        brut = gain_db_vers_brut(db)
        retour = gain_brut_vers_db(brut)
        print(f"  {db:+6.1f} dB -> brut={brut:4d} -> retour={retour:+6.1f} dB")

    # Test frequence PEQ
    print("\n--- Frequence PEQ ---")
    for hz in [20.0, 100.0, 250.0, 1000.0, 4000.0, 10000.0, 20000.0]:
        brut = freq_hz_vers_brut(hz)
        retour = freq_brut_vers_hz(brut)
        print(f"  {hz:8.0f} Hz -> brut={brut:4d} -> retour={retour:8.1f} Hz")

    # Test Q PEQ
    print("\n--- Q PEQ ---")
    for q in [0.40, 0.71, 1.0, 2.0, 4.0, 10.0, 35.0, 128.0]:
        brut = q_vers_brut(q)
        retour = q_brut_vers_q(brut)
        print(f"  Q={q:6.2f} -> brut={brut:3d} -> retour={retour:6.2f}")

    # Test gain PEQ/GEQ
    print("\n--- Gain PEQ/GEQ ---")
    for db in [-12.0, -6.0, 0.0, 3.0, 12.0]:
        brut = peq_gain_db_vers_brut(db)
        retour = peq_gain_brut_vers_db(brut)
        print(f"  {db:+6.1f} dB -> brut={brut:3d} -> retour={retour:+6.1f} dB")

    # Test construction de trames
    print("\n--- Construction de trames ---")
    trame_gain = cmd_gain("Out 1", -6.0)
    print(f"  Gain Out 1 = -6.0 dB : {trame_gain.hex(' ')}")

    trame_mute = cmd_mute("In A", True)
    print(f"  Mute In A ON         : {trame_mute.hex(' ')}")

    trame_peq = cmd_peq("Out 1", 0, -3.0, 250.0, 2.0)
    print(f"  PEQ Out1 b0 -3dB 250Hz Q2 : {trame_peq.hex(' ')}")

    trame_hpf = cmd_hpf("Out 1", 80.0)
    print(f"  HPF Out 1 = 80 Hz    : {trame_hpf.hex(' ')}")

    trame_lpf = cmd_lpf("Out 1", 1200.0, pente=8)
    print(f"  LPF Out 1 = 1200 Hz  : {trame_lpf.hex(' ')}")

    trame_matrice = cmd_matrice("Out 1", 0x03)  # In A + In B
    print(f"  Matrice Out1 <- A+B  : {trame_matrice.hex(' ')}")

    # Test analyse de trame
    print("\n--- Analyse de trame ---")
    # Analyser la trame keepalive preformatee
    resultat = analyser_trame(TRAME_KEEPALIVE)
    print(f"  Keepalive : {resultat}")

    # Verifier le handshake preformate
    resultat_hs = analyser_trame(TRAME_HANDSHAKE)
    print(f"  Handshake : commande=0x{resultat_hs['commande']:02X}, "
          f"checksum_ok={resultat_hs['checksum_ok']}")

    print("\n" + "=" * 60)

    if args.test_hors_ligne:
        print("\nTests hors ligne termines avec succes.")
        sys.exit(0)

    # -- Test de connexion reelle --
    print(f"\nTentative de connexion a {args.ip}:{args.port} ...")
    print("(Ctrl+C pour annuler)\n")

    try:
        with TracksDSP206(args.ip, args.port) as dsp:
            print(f"Connecte : {dsp}")
            print(f"Appareil : {dsp.nom_appareil}")

            # Lire les metres
            print("\nLecture des metres...")
            metres = dsp.get_meters()
            for canal, niveau in metres.items():
                if niveau > 0.001:
                    db_approx = 20 * math.log10(niveau) if niveau > 0 else -120
                    print(f"  {canal}: {niveau:.4f} ({db_approx:.1f} dBFS)")
                else:
                    print(f"  {canal}: silence")

            # Attendre un moment pour observer le keepalive
            print("\nKeepalive actif (3 secondes)...")
            time.sleep(3)

            # Relire les metres
            metres = dsp.get_meters()
            print("\nMetres apres 3s :")
            for canal, niveau in metres.items():
                if niveau > 0.001:
                    db_approx = 20 * math.log10(niveau) if niveau > 0 else -120
                    print(f"  {canal}: {niveau:.4f} ({db_approx:.1f} dBFS)")
                else:
                    print(f"  {canal}: silence")

    except ConnectionError as e:
        print(f"Erreur de connexion : {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur.")
        sys.exit(0)

    print("\nTest termine.")
