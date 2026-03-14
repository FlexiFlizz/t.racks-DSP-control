"""Compare deux mesures (avant/apres correction).

Usage :
    python -m backend.cli.comparer 0 1              # comparer mesure 0 et 1
    python -m backend.cli.comparer 0 1 --freq 60 16000  # limiter la plage
"""

import sys
import argparse
import numpy as np

sys.path.insert(0, ".")
from backend.rew.client import ClientREW


def main():
    parser = argparse.ArgumentParser(description="Comparer deux mesures REW")
    parser.add_argument("avant", type=int, help="Index mesure avant")
    parser.add_argument("apres", type=int, help="Index mesure apres")
    parser.add_argument("--freq", nargs=2, type=float, default=[20, 20000],
                        help="Plage de frequences (defaut: 20 20000)")
    parser.add_argument("--smoothing", default="1/12")
    args = parser.parse_args()

    rew = ClientREW()
    if not rew.est_connecte():
        print("ERREUR : REW non accessible")
        sys.exit(1)

    # Charger les deux mesures
    data_avant = rew.get_reponse_frequentielle(args.avant, smoothing=args.smoothing)
    data_apres = rew.get_reponse_frequentielle(args.apres, smoothing=args.smoothing)

    if data_avant is None or data_apres is None:
        print("ERREUR : mesure introuvable")
        sys.exit(1)

    info_avant = rew.get_mesure(args.avant)
    info_apres = rew.get_mesure(args.apres)
    nom_avant = info_avant.get("name", f"Mesure {args.avant}") if info_avant else f"Mesure {args.avant}"
    nom_apres = info_apres.get("name", f"Mesure {args.apres}") if info_apres else f"Mesure {args.apres}"

    freq = data_avant["frequences"]
    mag_avant = data_avant["magnitudes"]
    mag_apres = data_apres["magnitudes"]

    masque = (freq >= args.freq[0]) & (freq <= args.freq[1])

    print(f"\n=== Comparaison : {nom_avant} vs {nom_apres} ===")
    print(f"    Plage : {args.freq[0]:.0f} - {args.freq[1]:.0f} Hz\n")

    # Stats globales
    moy_avant = np.mean(mag_avant[masque])
    moy_apres = np.mean(mag_apres[masque])
    std_avant = np.std(mag_avant[masque])
    std_apres = np.std(mag_apres[masque])

    print(f"{'':>12} | {'Avant':>10} | {'Apres':>10} | {'Delta':>10}")
    print("-" * 50)
    print(f"  {'SPL moyen':>10} | {moy_avant:>9.1f} dB | {moy_apres:>9.1f} dB | {moy_apres - moy_avant:>+9.1f} dB")
    print(f"  {'Variance':>10} | {std_avant:>9.1f} dB | {std_apres:>9.1f} dB | {std_apres - std_avant:>+9.1f} dB")
    print(f"  {'SPL max':>10} | {np.max(mag_avant[masque]):>9.1f} dB | {np.max(mag_apres[masque]):>9.1f} dB |")
    print(f"  {'SPL min':>10} | {np.min(mag_avant[masque]):>9.1f} dB | {np.min(mag_apres[masque]):>9.1f} dB |")

    # Amelioration ?
    if std_apres < std_avant:
        amelioration = (1 - std_apres / std_avant) * 100
        print(f"\n  Amelioration de la regularite : {amelioration:.0f}%")
    else:
        degradation = (std_apres / std_avant - 1) * 100
        print(f"\n  ATTENTION : variance augmentee de {degradation:.0f}%")

    # Comparaison par bande d'octave
    print(f"\n--- Comparaison par bande ---")
    print(f"  {'Freq':>8} | {'Avant':>7} | {'Apres':>7} | {'Delta':>7}")
    print("  " + "-" * 40)

    bandes = [31.5, 63, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
    for fc in bandes:
        if fc < args.freq[0] or fc > args.freq[1]:
            continue
        f_lo = fc / 1.414
        f_hi = fc * 1.414
        m = (freq >= f_lo) & (freq <= f_hi)
        if np.any(m):
            av = np.mean(mag_avant[m])
            ap = np.mean(mag_apres[m])
            delta = ap - av
            indicateur = "+" if delta > 1 else ("-" if delta < -1 else "=")
            print(f"  {fc:>6.0f} Hz | {av:>6.1f} | {ap:>6.1f} | {delta:>+6.1f} {indicateur}")


if __name__ == "__main__":
    main()
