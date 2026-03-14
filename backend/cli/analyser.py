"""Analyse complete d'une ou deux mesures pour le calage.

Usage :
    python -m backend.cli.analyser 0                    # analyse une mesure (EQ)
    python -m backend.cli.analyser 0 1 --crossover 120  # calage sub/top
"""

import sys
import argparse
import numpy as np

sys.path.insert(0, ".")
from backend.rew.client import ClientREW
from backend.core.analyseur_phase import (
    unwrap_phase, coherence_phase, detecter_polarite,
    group_delay_depuis_phase,
)
from backend.core.calculateur_delay import calculer_delay_optimal
from backend.core.calculateur_eq import generer_filtres_correctifs, formater_filtres


def charger_donnees(rew, index, smoothing="1/12"):
    """Charge freq+phase+IR depuis REW."""
    freq_data = rew.get_reponse_frequentielle(index, smoothing=smoothing)
    ir_data = rew.get_reponse_impulsionnelle(index)
    info = rew.get_mesure(index)
    nom = info.get("name", f"Mesure {index}") if info else f"Mesure {index}"
    return {
        "nom": nom,
        "freq": freq_data.get("frequences") if freq_data else None,
        "mag": freq_data.get("magnitudes") if freq_data else None,
        "phase": freq_data.get("phases") if freq_data else None,
        "ir": ir_data.get("echantillons") if ir_data else None,
        "sr": ir_data.get("sample_rate") if ir_data else None,
    }


def analyser_une_mesure(data, seuil_db=3.0):
    """Analyse une mesure et propose un EQ correctif."""
    print(f"\n=== Analyse EQ : {data['nom']} ===\n")

    if data["freq"] is None or data["mag"] is None:
        print("ERREUR : pas de donnees frequentielles")
        return

    freq = data["freq"]
    mag = data["mag"]

    # Stats
    masque = (freq >= 100) & (freq <= 10000)
    print(f"SPL moyen (100-10k) : {np.mean(mag[masque]):.1f} dB")
    print(f"SPL min/max : {np.min(mag[masque]):.1f} / {np.max(mag[masque]):.1f} dB")
    print(f"Variance : {np.std(mag[masque]):.1f} dB")

    # Filtres correctifs
    filtres = generer_filtres_correctifs(
        freq, mag, seuil_db=seuil_db, freq_min=60, freq_max=16000
    )

    print(f"\n--- Filtres correctifs (soustractifs) ---")
    print(formater_filtres(filtres))


def analyser_deux_mesures(data_a, data_b, freq_crossover, largeur=1.0):
    """Analyse de calage entre deux sous-systemes."""
    print(f"\n=== Calage : {data_a['nom']} / {data_b['nom']} ===")
    print(f"    Crossover : {freq_crossover:.0f} Hz\n")

    if data_a["phase"] is None or data_b["phase"] is None:
        print("ERREUR : pas de donnees de phase")
        return

    freq = data_a["freq"]
    phase_a = unwrap_phase(data_a["phase"])
    phase_b = unwrap_phase(data_b["phase"])

    # 1. Delay
    resultat = calculer_delay_optimal(
        freq, phase_a, freq, phase_b,
        freq_crossover, largeur,
        ir_a=data_a["ir"], ir_b=data_b["ir"],
        sr=data_a["sr"],
    )

    print(f"--- Delay ---")
    print(f"  {data_a['nom']} : {resultat['delay_a_phase_ms']:.3f} ms (phase)")
    print(f"  {data_b['nom']} : {resultat['delay_b_phase_ms']:.3f} ms (phase)")
    print(f"  Delay relatif : {resultat['delay_phase_ms']:.3f} ms")
    if resultat["delay_ir_ms"] is not None:
        print(f"  Delay par IR : {resultat['delay_ir_ms']:.3f} ms")
    print(f"  >> Appliquer {resultat['delay_recommande_ms']:.2f} ms sur {resultat['appliquer_sur']}")
    print(f"  Methode : {resultat['methode']}")

    # 2. Polarite
    inverser = detecter_polarite(freq, phase_a, phase_b, freq_crossover, largeur)
    print(f"\n--- Polarite ---")
    if inverser:
        print(f"  >> INVERSER la polarite recommande")
    else:
        print(f"  Polarite OK")

    # 3. Coherence
    freq_min = freq_crossover / (2 ** (largeur / 2))
    freq_max = freq_crossover * (2 ** (largeur / 2))
    coh = coherence_phase(freq, phase_a, phase_b, freq_min, freq_max)
    print(f"\n--- Coherence de phase ---")
    print(f"  Zone {freq_min:.0f}-{freq_max:.0f} Hz : {coh:.1%}")
    if coh > 0.8:
        print(f"  Bon alignement")
    elif coh > 0.6:
        print(f"  Alignement moyen — delay/polarite a verifier")
    else:
        print(f"  Mauvais alignement — corrections necessaires")

    # 4. Group delay
    if data_a["phase"] is not None:
        gd_freq, gd_a = group_delay_depuis_phase(freq, phase_a)
        _, gd_b = group_delay_depuis_phase(freq, phase_b)
        masque_gd = (gd_freq >= freq_min) & (gd_freq <= freq_max)
        if np.any(masque_gd):
            print(f"\n--- Group delay moyen dans la zone de crossover ---")
            print(f"  {data_a['nom']} : {np.mean(gd_a[masque_gd]):.2f} ms")
            print(f"  {data_b['nom']} : {np.mean(gd_b[masque_gd]):.2f} ms")


def main():
    parser = argparse.ArgumentParser(description="Analyser des mesures REW")
    parser.add_argument("index_a", type=int, help="Index mesure A")
    parser.add_argument("index_b", nargs="?", type=int, help="Index mesure B (calage)")
    parser.add_argument("--crossover", type=float, default=120,
                        help="Frequence de crossover en Hz (defaut: 120)")
    parser.add_argument("--seuil", type=float, default=3.0,
                        help="Seuil EQ en dB (defaut: 3)")
    parser.add_argument("--smoothing", default="1/12")
    parser.add_argument("--largeur", type=float, default=1.0,
                        help="Largeur d'analyse en octaves (defaut: 1)")
    args = parser.parse_args()

    rew = ClientREW()
    if not rew.est_connecte():
        print("ERREUR : REW non accessible sur " + rew.base_url)
        sys.exit(1)

    data_a = charger_donnees(rew, args.index_a, args.smoothing)

    if args.index_b is not None:
        data_b = charger_donnees(rew, args.index_b, args.smoothing)
        analyser_deux_mesures(data_a, data_b, args.crossover, args.largeur)
    else:
        analyser_une_mesure(data_a, args.seuil)


if __name__ == "__main__":
    main()
