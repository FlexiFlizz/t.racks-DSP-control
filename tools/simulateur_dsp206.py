"""
Simulateur TCP du t.racks DSP 206 pour tests hors-ligne.

Emule le protocole binaire du DSP 206 sur le port TCP 9761.
Permet de tester l'app dsp-408-ui et le driver Python
sans avoir le processeur physique branche.

Usage :
    python simulateur_dsp206.py [--port 9761] [--verbose]

Le simulateur repond aux commandes du protocole t.racks :
    - Handshake (0x10)
    - Device info (0x13)
    - Status (0x12)
    - Gain (0x34)
    - Mute (0x35)
    - PEQ (0x33)
    - HPF (0x32)
    - LPF (0x31)
    - GEQ (0x48)
    - Matrice (0x3a)
    - Metres/Keepalive (0x40)
    - Presets (0x29, 0x2c)
    - Config chunks (0x27)
"""

import socket
import struct
import threading
import time
import math
import random
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("simulateur_dsp206")

# ---------------------------------------------------------------------------
# Constantes protocole
# ---------------------------------------------------------------------------
HEADER = bytes([0x10, 0x02])
FOOTER = bytes([0x10, 0x03])
DIR_REPONSE = 0x01  # appareil -> hote

CMD_HANDSHAKE = 0x10
CMD_STATUS = 0x12
CMD_DEVICE_INFO = 0x13
CMD_LOAD_PRESET = 0x20
CMD_CONFIG_CHUNK = 0x24
CMD_GET_CONFIG = 0x27
CMD_GET_PRESET = 0x29
CMD_GET_ALL_PRESETS = 0x2C
CMD_LPF = 0x31
CMD_HPF = 0x32
CMD_PEQ = 0x33
CMD_GAIN = 0x34
CMD_MUTE = 0x35
CMD_DELAY = 0x36
CMD_MATRIX = 0x3A
CMD_METERS = 0x40
CMD_GEQ = 0x48

# Canaux DSP 206 : 2 entrees + 6 sorties
NOMS_CANAUX = {
    0x00: "In A", 0x01: "In B",
    0x04: "Out 1", 0x05: "Out 2", 0x06: "Out 3",
    0x07: "Out 4", 0x08: "Out 5", 0x09: "Out 6",
}
NB_CANAUX = 8  # pour les metres


# ---------------------------------------------------------------------------
# Etat simule du DSP
# ---------------------------------------------------------------------------
class EtatDSP:
    """Stocke l'etat virtuel du DSP 206."""

    def __init__(self):
        self.gains = {}      # canal_idx -> valeur brute (280 = 0 dB)
        self.mutes = {}      # canal_idx -> bool
        self.peqs = {}       # (canal_idx, bande) -> {gain, freq, q, type, bypass}
        self.hpfs = {}       # canal_idx -> {freq, pente, actif}
        self.lpfs = {}       # canal_idx -> {freq, pente, actif}
        self.geqs = {}       # (canal_idx, bande) -> valeur brute
        self.matrice = {}    # sortie_idx -> bitmask entrees
        self.delays = {}     # canal_idx -> valeur brute
        self.preset_actif = 0
        self.nom_preset = "Default"
        self._init_defauts()

    def _init_defauts(self):
        """Initialise les valeurs par defaut (tout a 0 dB, non mute)."""
        for idx in NOMS_CANAUX:
            self.gains[idx] = 280    # 0 dB
            self.mutes[idx] = False
            self.delays[idx] = 0
            self.hpfs[idx] = {"freq": 0, "pente": 0, "actif": False}
            self.lpfs[idx] = {"freq": 1000, "pente": 0, "actif": False}

        # PEQ : 8 bandes entrees, 9 bandes sorties
        for idx in [0x00, 0x01]:
            for bande in range(8):
                self.peqs[(idx, bande)] = {
                    "gain": 120, "freq": 500, "q": 128, "type": 0, "bypass": False
                }
        for idx in [0x04, 0x05, 0x06, 0x07, 0x08, 0x09]:
            for bande in range(9):
                self.peqs[(idx, bande)] = {
                    "gain": 120, "freq": 500, "q": 128, "type": 0, "bypass": False
                }

        # GEQ : 31 bandes par entree
        for idx in [0x00, 0x01]:
            for bande in range(31):
                self.geqs[(idx, bande)] = 120  # 0 dB

        # Matrice : chaque sortie recoit In A par defaut
        for idx in [0x04, 0x05, 0x06, 0x07, 0x08, 0x09]:
            self.matrice[idx] = 0x01  # In A


# ---------------------------------------------------------------------------
# Fonctions protocole
# ---------------------------------------------------------------------------
def calculer_checksum(data: bytes) -> int:
    """Checksum XOR initialise a 1."""
    chk = 1
    for b in data:
        chk ^= b
    return chk & 0xFF


def construire_reponse(payload: bytes) -> bytes:
    """Construit une trame de reponse (appareil -> hote).

    Si le payload depasse 255 octets, le champ longueur est encode
    sur 2 octets (little-endian) pour rester compatible avec le
    protocole observe dans les captures reseau.
    """
    longueur = len(payload)
    if longueur <= 255:
        data = bytes([DIR_REPONSE, 0x01, longueur]) + payload
    else:
        # Longueur sur 2 octets LE pour les gros paquets
        data = bytes([DIR_REPONSE, 0x01, longueur & 0xFF, (longueur >> 8) & 0xFF]) + payload
    chk = calculer_checksum(data)
    return HEADER + data + FOOTER + bytes([chk])


def analyser_trame(data: bytes):
    """Extrait commande et payload d'une trame recue."""
    if len(data) < 6 or data[0] != 0x10 or data[1] != 0x02:
        return None, None

    # Trouver le footer 10 03
    footer_idx = -1
    for i in range(2, len(data) - 1):
        if data[i] == 0x10 and data[i + 1] == 0x03:
            footer_idx = i
            break
    if footer_idx < 0:
        return None, None

    commande = data[5] if len(data) > 5 else None
    payload = data[6:footer_idx] if footer_idx > 6 else b""
    return commande, payload


def float_vers_float16_bytes(val: float) -> bytes:
    """Encode un float en IEEE 754 float16 little-endian."""
    packed = struct.pack('<e', val)
    return packed


# ---------------------------------------------------------------------------
# Generateur de metres simules
# ---------------------------------------------------------------------------
def generer_metres() -> bytes:
    """Genere des donnees de metres simulees (niveaux aleatoires).

    Retourne 3 octets par canal : float16_lo, float16_hi, peak_byte.
    Simule des niveaux entre -60 et -6 dB avec du bruit.
    """
    donnees = bytearray()
    for i in range(NB_CANAUX):
        # Simuler un niveau en dB (-60 a -6) avec variation
        db = -30 + random.gauss(0, 8)
        db = max(-60, min(-3, db))
        # Convertir en lineaire
        lineaire = 10 ** (db / 20.0)
        # Encoder en float16
        f16 = float_vers_float16_bytes(lineaire)
        # Peak byte (0-255, proportionnel)
        peak = min(255, max(0, int((db + 60) / 60 * 255)))
        donnees.extend(f16)
        donnees.append(peak)
    return bytes(donnees)


# ---------------------------------------------------------------------------
# Generateur de config chunks
# ---------------------------------------------------------------------------
def generer_config_chunk(etat: EtatDSP, sub_index: int) -> bytes:
    """Genere un chunk de configuration pour la commande 0x27.

    Chaque sub_index (0x00-0x1C) correspond a un bloc de parametres.
    On simplifie en renvoyant des donnees coherentes pour les blocs principaux.
    """
    # Les chunks sont specifiques au modele, on renvoie des donnees
    # generiques mais valides pour que l'app ne plante pas
    if sub_index <= 0x01:
        # Chunks entrees (In A, In B) : gain + mute + PEQ 8 bandes + GEQ 31 bandes
        canal = sub_index  # 0x00 = In A, 0x01 = In B
        chunk = bytearray()
        # Gain (2 octets LE)
        g = etat.gains.get(canal, 280)
        chunk.extend([g & 0xFF, (g >> 8) & 0xFF])
        # Mute (1 octet)
        chunk.append(0x01 if etat.mutes.get(canal, False) else 0x00)
        # PEQ 8 bandes (7 octets par bande)
        for bande in range(8):
            peq = etat.peqs.get((canal, bande), {
                "gain": 120, "freq": 500, "q": 128, "type": 0, "bypass": False
            })
            chunk.append(peq["gain"] & 0xFF)
            chunk.append(0x00)
            chunk.extend([peq["freq"] & 0xFF, (peq["freq"] >> 8) & 0xFF])
            chunk.append(peq["q"] & 0xFF)
            chunk.append(peq["type"] & 0xFF)
            chunk.append(0x01 if peq["bypass"] else 0x00)
        # GEQ 31 bandes (1 octet par bande)
        for bande in range(31):
            chunk.append(etat.geqs.get((canal, bande), 120))
        return bytes(chunk)

    elif 0x04 <= sub_index <= 0x09:
        # Chunks sorties (Out 1-6) : gain + mute + PEQ 9 bandes + HPF + LPF + matrice
        canal = sub_index
        chunk = bytearray()
        # Gain
        g = etat.gains.get(canal, 280)
        chunk.extend([g & 0xFF, (g >> 8) & 0xFF])
        # Mute
        chunk.append(0x01 if etat.mutes.get(canal, False) else 0x00)
        # PEQ 9 bandes
        for bande in range(9):
            peq = etat.peqs.get((canal, bande), {
                "gain": 120, "freq": 500, "q": 128, "type": 0, "bypass": False
            })
            chunk.append(peq["gain"] & 0xFF)
            chunk.append(0x00)
            chunk.extend([peq["freq"] & 0xFF, (peq["freq"] >> 8) & 0xFF])
            chunk.append(peq["q"] & 0xFF)
            chunk.append(peq["type"] & 0xFF)
            chunk.append(0x01 if peq["bypass"] else 0x00)
        # HPF
        hpf = etat.hpfs.get(canal, {"freq": 0, "pente": 0, "actif": False})
        chunk.extend([hpf["freq"] & 0xFF, (hpf["freq"] >> 8) & 0xFF])
        chunk.append(hpf["pente"] & 0xFF)
        chunk.append(0x01 if hpf["actif"] else 0x00)
        # LPF
        lpf = etat.lpfs.get(canal, {"freq": 1000, "pente": 0, "actif": False})
        chunk.extend([lpf["freq"] & 0xFF, (lpf["freq"] >> 8) & 0xFF])
        chunk.append(lpf["pente"] & 0xFF)
        chunk.append(0x01 if lpf["actif"] else 0x00)
        # Matrice
        chunk.append(etat.matrice.get(canal, 0x01))
        # Delay
        d = etat.delays.get(canal, 0)
        chunk.extend([d & 0xFF, (d >> 8) & 0xFF])
        return bytes(chunk)

    # Sub-index inconnu : renvoyer un chunk vide
    return b"\x00" * 16


# ---------------------------------------------------------------------------
# Traitement des commandes
# ---------------------------------------------------------------------------
def traiter_commande(cmd: int, payload: bytes, etat: EtatDSP, verbose: bool) -> list:
    """Traite une commande recue et retourne les trames de reponse."""
    reponses = []

    if cmd == CMD_HANDSHAKE:
        if verbose:
            log.info("  <- Handshake")
        # Repondre avec un handshake acknowledge
        reponses.append(construire_reponse(bytes([CMD_HANDSHAKE])))

    elif cmd == CMD_DEVICE_INFO:
        if verbose:
            log.info("  <- Device Info")
        # Repondre avec nom du modele
        info = b"DSP206-SIM\x00" + b"\x00" * 20
        reponses.append(construire_reponse(bytes([CMD_DEVICE_INFO]) + info))

    elif cmd == CMD_STATUS:
        if verbose:
            log.info("  <- Status (preset actif)")
        # Renvoyer le preset actif
        reponses.append(construire_reponse(bytes([CMD_STATUS, etat.preset_actif])))

    elif cmd == CMD_GET_ALL_PRESETS:
        if verbose:
            log.info("  <- Liste presets")
        # Envoyer les presets un par un pour eviter les paquets trop gros
        # D'abord le nombre de presets
        reponses.append(construire_reponse(bytes([CMD_GET_ALL_PRESETS, 0x10])))  # 16 presets

    elif cmd == CMD_GET_PRESET:
        if verbose:
            idx = payload[0] if payload else 0
            log.info(f"  <- Get Preset {idx}")
        idx = payload[0] if payload else 0
        nom = f"Preset {idx+1:02d}".encode("ascii").ljust(16, b"\x00")
        reponses.append(construire_reponse(bytes([CMD_GET_PRESET, idx]) + nom))

    elif cmd == CMD_LOAD_PRESET:
        if verbose:
            idx = payload[0] if payload else 0
            log.info(f"  <- Load Preset {idx}")
        if payload:
            etat.preset_actif = payload[0]

    elif cmd == CMD_GET_CONFIG:
        sub_idx = payload[0] if payload else 0
        if verbose:
            log.info(f"  <- Get Config chunk 0x{sub_idx:02X}")
        chunk = generer_config_chunk(etat, sub_idx)
        reponses.append(construire_reponse(
            bytes([CMD_CONFIG_CHUNK, sub_idx]) + chunk
        ))

    elif cmd == CMD_GAIN:
        if len(payload) >= 3:
            canal = payload[0]
            val = payload[1] | (payload[2] << 8)
            db = (val - 280) / 10.0
            etat.gains[canal] = val
            nom = NOMS_CANAUX.get(canal, f"0x{canal:02X}")
            if verbose:
                log.info(f"  <- Gain {nom} = {db:+.1f} dB (brut={val})")
        # Pas de reponse attendue pour les commandes de reglage

    elif cmd == CMD_MUTE:
        if len(payload) >= 2:
            canal = payload[0]
            mute = payload[1] == 0x01
            etat.mutes[canal] = mute
            nom = NOMS_CANAUX.get(canal, f"0x{canal:02X}")
            if verbose:
                log.info(f"  <- Mute {nom} = {'ON' if mute else 'OFF'}")

    elif cmd == CMD_PEQ:
        if len(payload) >= 8:
            canal = payload[0]
            bande = payload[1]
            gain = payload[2]
            freq = payload[4] | (payload[5] << 8)
            q = payload[6]
            type_f = payload[7]
            bypass = payload[8] == 0x01 if len(payload) > 8 else False
            etat.peqs[(canal, bande)] = {
                "gain": gain, "freq": freq, "q": q,
                "type": type_f, "bypass": bypass
            }
            nom = NOMS_CANAUX.get(canal, f"0x{canal:02X}")
            gain_db = (gain - 120) / 10.0
            if verbose:
                log.info(
                    f"  <- PEQ {nom} bande {bande}: "
                    f"gain={gain_db:+.1f}dB freq_brut={freq} Q_brut={q} "
                    f"type={type_f} bypass={bypass}"
                )

    elif cmd == CMD_HPF:
        if len(payload) >= 4:
            canal = payload[0]
            freq = payload[1] | (payload[2] << 8)
            pente = payload[3] if len(payload) > 3 else 0
            actif = payload[4] == 0x01 if len(payload) > 4 else True
            etat.hpfs[canal] = {"freq": freq, "pente": pente, "actif": actif}
            nom = NOMS_CANAUX.get(canal, f"0x{canal:02X}")
            if verbose:
                log.info(f"  <- HPF {nom}: freq_brut={freq} pente={pente} actif={actif}")

    elif cmd == CMD_LPF:
        if len(payload) >= 4:
            canal = payload[0]
            freq = payload[1] | (payload[2] << 8)
            pente = payload[3] if len(payload) > 3 else 0
            actif = payload[4] == 0x01 if len(payload) > 4 else True
            etat.lpfs[canal] = {"freq": freq, "pente": pente, "actif": actif}
            nom = NOMS_CANAUX.get(canal, f"0x{canal:02X}")
            if verbose:
                log.info(f"  <- LPF {nom}: freq_brut={freq} pente={pente} actif={actif}")

    elif cmd == CMD_GEQ:
        if len(payload) >= 3:
            canal = payload[0]
            bande = payload[1]
            val = payload[2]
            etat.geqs[(canal, bande)] = val
            nom = NOMS_CANAUX.get(canal, f"0x{canal:02X}")
            db = (val - 120) / 10.0
            if verbose:
                log.info(f"  <- GEQ {nom} bande {bande} = {db:+.1f} dB")

    elif cmd == CMD_MATRIX:
        if len(payload) >= 2:
            sortie = payload[0]
            bitmask = payload[1]
            etat.matrice[sortie] = bitmask
            nom = NOMS_CANAUX.get(sortie, f"0x{sortie:02X}")
            sources = []
            if bitmask & 0x01:
                sources.append("In A")
            if bitmask & 0x02:
                sources.append("In B")
            if verbose:
                log.info(f"  <- Matrice {nom} <- {', '.join(sources) or 'aucune'}")

    elif cmd == CMD_DELAY:
        if len(payload) >= 3:
            canal = payload[0]
            val = payload[1] | (payload[2] << 8)
            etat.delays[canal] = val
            nom = NOMS_CANAUX.get(canal, f"0x{canal:02X}")
            if verbose:
                log.info(f"  <- Delay {nom} = brut {val}")

    elif cmd == CMD_METERS:
        # Keepalive / demande de metres - repondre avec des niveaux
        metre_data = generer_metres()
        reponses.append(construire_reponse(bytes([CMD_METERS]) + metre_data))

    else:
        if verbose:
            log.info(f"  <- Commande inconnue 0x{cmd:02X} (payload: {payload.hex()})")
        # Repondre avec un echo generique pour ne pas bloquer l'app
        reponses.append(construire_reponse(bytes([cmd]) + payload))

    return reponses


# ---------------------------------------------------------------------------
# Gestion client TCP
# ---------------------------------------------------------------------------
def extraire_trames(buffer: bytes):
    """Extrait les trames completes d'un buffer de donnees brutes.

    Retourne une liste de trames et le reste du buffer non consomme.
    """
    trames = []
    pos = 0

    while pos < len(buffer) - 1:
        # Chercher le header 10 02
        if buffer[pos] != 0x10 or buffer[pos + 1] != 0x02:
            pos += 1
            continue

        # Chercher le footer 10 03 apres le header
        footer_pos = -1
        for i in range(pos + 4, len(buffer) - 1):
            if buffer[i] == 0x10 and buffer[i + 1] == 0x03:
                footer_pos = i
                break

        if footer_pos < 0:
            # Trame incomplete, garder le reste dans le buffer
            break

        # La trame inclut header + data + footer + 1 octet checksum
        fin = footer_pos + 3  # footer (2) + checksum (1)
        if fin > len(buffer):
            break

        trames.append(buffer[pos:fin])
        pos = fin

    return trames, buffer[pos:]


def gerer_client(conn: socket.socket, addr, etat: EtatDSP, verbose: bool):
    """Gere une connexion client."""
    log.info(f"Client connecte : {addr[0]}:{addr[1]}")
    conn.settimeout(1.0)
    buffer = b""

    try:
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data

                trames, buffer = extraire_trames(buffer)

                for trame in trames:
                    cmd, payload = analyser_trame(trame)
                    if cmd is not None:
                        if verbose and cmd != CMD_METERS:
                            log.info(f"  Trame recue: {trame.hex(' ')}")

                        reponses = traiter_commande(cmd, payload, etat, verbose)

                        for rep in reponses:
                            conn.sendall(rep)
                            if verbose and cmd != CMD_METERS:
                                log.info(f"  Trame envoyee: {rep.hex(' ')}")

            except socket.timeout:
                continue
            except ConnectionResetError:
                break

    except Exception as e:
        log.error(f"Erreur client {addr}: {e}")
    finally:
        conn.close()
        log.info(f"Client deconnecte : {addr[0]}:{addr[1]}")


# ---------------------------------------------------------------------------
# Serveur principal
# ---------------------------------------------------------------------------
def demarrer_serveur(port: int = 9761, verbose: bool = False):
    """Demarre le simulateur TCP du DSP 206."""
    etat = EtatDSP()

    serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serveur.bind(("0.0.0.0", port))
    serveur.listen(2)

    log.info("=" * 55)
    log.info("  SIMULATEUR t.racks DSP 206")
    log.info(f"  Ecoute sur 0.0.0.0:{port}")
    log.info(f"  Connecter l'app dsp-408-ui sur 127.0.0.1:{port}")
    log.info(f"  Mode verbose : {'OUI' if verbose else 'NON'}")
    log.info("=" * 55)

    try:
        while True:
            conn, addr = serveur.accept()
            thread = threading.Thread(
                target=gerer_client,
                args=(conn, addr, etat, verbose),
                daemon=True,
            )
            thread.start()
    except KeyboardInterrupt:
        log.info("\nArret du simulateur.")
    finally:
        serveur.close()


# ---------------------------------------------------------------------------
# Point d'entree
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Simulateur TCP du t.racks DSP 206"
    )
    parser.add_argument(
        "--port", type=int, default=9761,
        help="Port TCP d'ecoute (defaut: 9761)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Afficher le detail des trames"
    )
    args = parser.parse_args()

    demarrer_serveur(port=args.port, verbose=args.verbose)
