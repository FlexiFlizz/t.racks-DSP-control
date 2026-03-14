"""Applique des corrections sur le DSP t.racks.

Usage :
    python -m backend.cli.appliquer gain "Out 1" -6.0
    python -m backend.cli.appliquer delay "Out 1" 2.5
    python -m backend.cli.appliquer mute "Out 1" on
    python -m backend.cli.appliquer peq "Out 1" 0 -3.0 250 2.0
    python -m backend.cli.appliquer eq-auto 0 "Out 1"  # EQ auto depuis mesure REW
"""

import sys
import argparse

sys.path.insert(0, ".")
from backend.dsp.tracks import TracksDSP
from backend.models.filtre import FiltrePEQ, TypeFiltre


def main():
    parser = argparse.ArgumentParser(description="Appliquer des corrections DSP")
    parser.add_argument("--host", default="192.168.3.100", help="IP du DSP")
    parser.add_argument("--port", type=int, default=9761, help="Port TCP")

    sub = parser.add_subparsers(dest="commande", required=True)

    # Gain
    p_gain = sub.add_parser("gain", help="Regler le gain")
    p_gain.add_argument("canal", help="Nom du canal (ex: 'Out 1')")
    p_gain.add_argument("db", type=float, help="Gain en dB")

    # Delay
    p_delay = sub.add_parser("delay", help="Regler le delay")
    p_delay.add_argument("canal", help="Nom du canal")
    p_delay.add_argument("ms", type=float, help="Delay en ms")

    # Mute
    p_mute = sub.add_parser("mute", help="Mute/unmute")
    p_mute.add_argument("canal", help="Nom du canal")
    p_mute.add_argument("etat", choices=["on", "off"], help="on=mute, off=unmute")

    # PEQ
    p_peq = sub.add_parser("peq", help="Regler une bande PEQ")
    p_peq.add_argument("canal", help="Nom du canal")
    p_peq.add_argument("bande", type=int, help="Index de bande (0-8)")
    p_peq.add_argument("gain_db", type=float, help="Gain en dB")
    p_peq.add_argument("freq_hz", type=float, help="Frequence en Hz")
    p_peq.add_argument("q", type=float, help="Facteur Q")

    # EQ auto depuis mesure REW
    p_eq = sub.add_parser("eq-auto", help="EQ automatique depuis mesure REW")
    p_eq.add_argument("index_mesure", type=int, help="Index mesure REW")
    p_eq.add_argument("canal", help="Canal DSP cible")
    p_eq.add_argument("--seuil", type=float, default=3.0, help="Seuil en dB")
    p_eq.add_argument("--dry-run", action="store_true", help="Calculer sans appliquer")

    args = parser.parse_args()

    # Connecter au DSP
    dsp = TracksDSP()
    print(f"Connexion a {args.host}:{args.port}...")
    if not dsp.connecter(args.host, args.port):
        print("ERREUR : impossible de se connecter au DSP")
        sys.exit(1)

    print(f"Connecte : {dsp.get_nom_modele()}")

    try:
        if args.commande == "gain":
            dsp.set_gain(args.canal, args.db)
            print(f"Gain {args.canal} = {args.db:+.1f} dB")

        elif args.commande == "delay":
            dsp.set_delay(args.canal, args.ms)
            print(f"Delay {args.canal} = {args.ms:.2f} ms")

        elif args.commande == "mute":
            mute = args.etat == "on"
            dsp.set_mute(args.canal, mute)
            print(f"{'Mute' if mute else 'Unmute'} {args.canal}")

        elif args.commande == "peq":
            filtre = FiltrePEQ(
                frequence_hz=args.freq_hz,
                gain_db=args.gain_db,
                q=args.q,
            )
            dsp.set_peq(args.canal, args.bande, filtre)
            print(f"PEQ {args.canal} bande {args.bande} : "
                  f"{args.gain_db:+.1f} dB @ {args.freq_hz:.0f} Hz Q={args.q:.1f}")

        elif args.commande == "eq-auto":
            from backend.rew.client import ClientREW
            from backend.core.moteur_script import MoteurScript

            rew = ClientREW()
            if not rew.est_connecte():
                print("ERREUR : REW non accessible")
                sys.exit(1)

            moteur = MoteurScript(rew, dsp)
            mesure = moteur.charger_mesure(args.index_mesure)
            if mesure is None:
                print("ERREUR : mesure introuvable")
                sys.exit(1)

            resultat = moteur.calculer_eq_correctif(
                mesure, args.canal,
                seuil_db=args.seuil,
                appliquer=not args.dry_run,
            )
            print(str(resultat))

    finally:
        dsp.deconnecter()
        print("Deconnecte.")


if __name__ == "__main__":
    main()
