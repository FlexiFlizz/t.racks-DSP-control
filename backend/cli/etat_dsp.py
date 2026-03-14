"""Affiche l'etat actuel du DSP t.racks.

Usage :
    python -m backend.cli.etat_dsp                    # etat complet
    python -m backend.cli.etat_dsp --host 127.0.0.1   # simulateur
"""

import sys
import argparse

sys.path.insert(0, ".")
from backend.dsp.tracks import TracksDSP


def main():
    parser = argparse.ArgumentParser(description="Etat du DSP t.racks")
    parser.add_argument("--host", default="192.168.3.100", help="IP du DSP")
    parser.add_argument("--port", type=int, default=9761, help="Port TCP")
    args = parser.parse_args()

    dsp = TracksDSP()
    print(f"Connexion a {args.host}:{args.port}...")

    if not dsp.connecter(args.host, args.port):
        print("ERREUR : impossible de se connecter")
        sys.exit(1)

    print(f"Modele : {dsp.get_nom_modele()}")
    print(f"Entrees : {', '.join(dsp.get_canaux_entree().keys())}")
    print(f"Sorties : {', '.join(dsp.get_canaux_sortie().keys())}")

    # Metres
    metres = dsp.get_metres()
    if metres:
        import math
        print(f"\n--- Metres ---")
        for canal, niveau in metres.items():
            if niveau > 0.001:
                db = 20 * math.log10(niveau) if niveau > 0 else -120
                print(f"  {canal:>6} : {db:>6.1f} dBFS")
            else:
                print(f"  {canal:>6} : silence")

    # Etat cache
    etat = dsp.get_etat()
    print(f"\n--- Etat ---")
    for nom, infos in etat.get("canaux", {}).items():
        gain = infos.get("gain_db", 0)
        mute = infos.get("mute", False)
        delay = infos.get("delay_ms", 0)
        mute_str = " [MUTE]" if mute else ""
        delay_str = f" delay={delay:.1f}ms" if delay > 0 else ""
        print(f"  {nom:>6} : {gain:+.1f} dB{delay_str}{mute_str}")

    dsp.deconnecter()


if __name__ == "__main__":
    main()
