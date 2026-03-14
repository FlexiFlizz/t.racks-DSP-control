"""Lit et affiche une mesure depuis REW.

Usage :
    python -m backend.cli.lire_mesure           # liste les mesures
    python -m backend.cli.lire_mesure 0          # affiche la mesure 0
    python -m backend.cli.lire_mesure 0 --phase  # affiche aussi la phase
    python -m backend.cli.lire_mesure 0 --ir     # affiche l'IR
"""

import sys
import argparse
import numpy as np

sys.path.insert(0, ".")
from backend.rew.client import ClientREW


def main():
    parser = argparse.ArgumentParser(description="Lire une mesure REW")
    parser.add_argument("index", nargs="?", type=int, help="Index de la mesure")
    parser.add_argument("--phase", action="store_true", help="Afficher la phase")
    parser.add_argument("--ir", action="store_true", help="Afficher l'IR")
    parser.add_argument("--smoothing", default="1/12", help="Lissage (defaut: 1/12)")
    parser.add_argument("--host", default="localhost", help="Host REW")
    parser.add_argument("--port", type=int, default=4735, help="Port REW")
    args = parser.parse_args()

    rew = ClientREW(args.host, args.port)

    if not rew.est_connecte():
        print("ERREUR : REW n'est pas accessible sur " + rew.base_url)
        print("Verifie que REW est lance et que l'API est activee.")
        sys.exit(1)

    # Si pas d'index, lister les mesures
    if args.index is None:
        mesures = rew.lister_mesures()
        if not mesures:
            print("Aucune mesure ouverte dans REW.")
            return

        print(f"\n{'Index':>5} | Nom")
        print("-" * 40)
        for i, m in enumerate(mesures):
            nom = m.get("name", m.get("title", f"Mesure {i}"))
            print(f"  {i:>3} | {nom}")
        print(f"\n{len(mesures)} mesure(s) au total.")
        return

    # Afficher une mesure
    info = rew.get_mesure(args.index)
    if info is None:
        print(f"ERREUR : mesure {args.index} introuvable")
        sys.exit(1)

    nom = info.get("name", f"Mesure {args.index}")
    print(f"\n=== {nom} ===\n")

    # Reponse frequentielle
    data = rew.get_reponse_frequentielle(args.index, smoothing=args.smoothing)
    if data and "frequences" in data:
        freq = data["frequences"]
        mag = data["magnitudes"]
        print(f"Reponse frequentielle : {len(freq)} points")
        print(f"  Plage : {freq[0]:.1f} Hz - {freq[-1]:.0f} Hz")
        print(f"  SPL min/max : {np.min(mag):.1f} / {np.max(mag):.1f} dB")
        print(f"  SPL moyen (100-10kHz) : ", end="")

        masque = (freq >= 100) & (freq <= 10000)
        if np.any(masque):
            print(f"{np.mean(mag[masque]):.1f} dB")
        else:
            print("N/A")

        # Afficher quelques points cles
        freqs_cles = [63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        print(f"\n  {'Freq':>8} | {'SPL':>7}")
        print("  " + "-" * 20)
        for fc in freqs_cles:
            idx = np.argmin(np.abs(freq - fc))
            if abs(freq[idx] - fc) < fc * 0.1:
                print(f"  {fc:>6} Hz | {mag[idx]:>6.1f} dB")

        if args.phase and "phases" in data:
            phases = data["phases"]
            print(f"\n  Phase :")
            print(f"  {'Freq':>8} | {'Phase':>8}")
            print("  " + "-" * 22)
            for fc in freqs_cles:
                idx = np.argmin(np.abs(freq - fc))
                if abs(freq[idx] - fc) < fc * 0.1:
                    print(f"  {fc:>6} Hz | {phases[idx]:>7.1f} deg")

    # IR
    if args.ir:
        ir_data = rew.get_reponse_impulsionnelle(args.index)
        if ir_data and "echantillons" in ir_data:
            ir = ir_data["echantillons"]
            sr = ir_data.get("sample_rate", 48000)
            pic = np.argmax(np.abs(ir))
            pic_ms = pic / sr * 1000
            print(f"\n  Reponse impulsionnelle :")
            print(f"    Echantillons : {len(ir)}")
            print(f"    Sample rate : {sr:.0f} Hz")
            print(f"    Pic @ {pic_ms:.2f} ms (index {pic})")
            print(f"    Amplitude pic : {ir[pic]:.4f}")


if __name__ == "__main__":
    main()
