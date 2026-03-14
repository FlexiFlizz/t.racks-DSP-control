"""Moteur de calage Mode Script (offline, algorithmes fixes).

Orchestrateur de la boucle de calage :
  Mesure → Analyse → Calcul delay/polarite/EQ → Application DSP
"""

import logging
from typing import Optional, List, Dict
from backend.models.mesure import Mesure
from backend.models.systeme import SystemeSon, Crossover
from backend.models.filtre import FiltrePEQ
from backend.dsp.base import BaseDSP
from backend.rew.client import ClientREW
from .analyseur_phase import (
    unwrap_phase, detecter_polarite, coherence_phase,
)
from .calculateur_delay import calculer_delay_optimal
from .calculateur_eq import generer_filtres_correctifs, formater_filtres

logger = logging.getLogger(__name__)


class ResultatCalage:
    """Resultat d'une etape de calage."""

    def __init__(self):
        self.delay_ms: Optional[float] = None
        self.appliquer_delay_sur: Optional[str] = None
        self.inverser_polarite: bool = False
        self.filtres_eq: List[FiltrePEQ] = []
        self.coherence_avant: float = 0.0
        self.coherence_apres: Optional[float] = None
        self.details: Dict = {}
        self.messages: List[str] = []

    def ajouter_message(self, msg: str):
        self.messages.append(msg)
        logger.info(msg)

    def __str__(self) -> str:
        lignes = ["=== Resultat du calage ==="]
        for msg in self.messages:
            lignes.append(f"  {msg}")
        if self.delay_ms is not None:
            lignes.append(f"  Delay : {self.delay_ms:.2f} ms sur {self.appliquer_delay_sur}")
        if self.inverser_polarite:
            lignes.append("  Polarite : INVERSER")
        if self.filtres_eq:
            lignes.append(f"  EQ : {len(self.filtres_eq)} filtres correctifs")
            lignes.append(formater_filtres(self.filtres_eq))
        lignes.append(f"  Coherence phase : {self.coherence_avant:.1%}")
        if self.coherence_apres is not None:
            lignes.append(f"  Coherence apres : {self.coherence_apres:.1%}")
        return "\n".join(lignes)


class MoteurScript:
    """Moteur de calage algorithmique (Mode Script).

    Utilise des algorithmes fixes et deterministes pour calculer
    les corrections de delay, polarite et EQ.
    """

    def __init__(self, rew: ClientREW, dsp: BaseDSP):
        """Initialise le moteur.

        Args:
            rew: client REW connecte.
            dsp: driver DSP connecte.
        """
        self.rew = rew
        self.dsp = dsp

    def charger_mesure(self, index_rew: int,
                       smoothing: str = "1/12") -> Optional[Mesure]:
        """Charge une mesure depuis REW.

        Args:
            index_rew: index de la mesure dans REW.
            smoothing: lissage a appliquer.

        Returns:
            Objet Mesure avec les donnees, ou None si erreur.
        """
        # Info mesure
        info = self.rew.get_mesure(index_rew)
        if info is None:
            logger.error("Mesure %d introuvable dans REW", index_rew)
            return None

        nom = info.get("name", f"Mesure {index_rew}")
        mesure = Mesure(nom=nom, index_rew=index_rew)

        # Reponse frequentielle + phase
        freq_data = self.rew.get_reponse_frequentielle(index_rew, smoothing=smoothing)
        if freq_data:
            mesure.frequences = freq_data.get("frequences")
            mesure.magnitudes = freq_data.get("magnitudes")
            mesure.phases = freq_data.get("phases")

        # Reponse impulsionnelle
        ir_data = self.rew.get_reponse_impulsionnelle(index_rew)
        if ir_data:
            mesure.ir_echantillons = ir_data.get("echantillons")
            mesure.ir_sample_rate = ir_data.get("sample_rate")

        # Group delay
        gd_data = self.rew.get_group_delay(index_rew, smoothing=smoothing)
        if gd_data:
            mesure.group_delay = gd_data.get("group_delay")
            mesure.group_delay_freq = gd_data.get("frequences")

        logger.info("Mesure chargee : %s", nom)
        return mesure

    def caler_deux_sources(
        self,
        mesure_a: Mesure,
        mesure_b: Mesure,
        freq_crossover: float,
        canal_delay: str,
        appliquer: bool = False,
    ) -> ResultatCalage:
        """Cale deux sous-systemes (ex: sub + top).

        Sequence : delay → polarite → verification coherence.

        Args:
            mesure_a: mesure du sous-systeme A (ex: sub).
            mesure_b: mesure du sous-systeme B (ex: top).
            freq_crossover: frequence de crossover en Hz.
            canal_delay: canal DSP sur lequel appliquer le delay.
            appliquer: si True, applique les corrections sur le DSP.

        Returns:
            ResultatCalage avec les corrections calculees.
        """
        resultat = ResultatCalage()

        if not mesure_a.a_freq_response() or not mesure_b.a_freq_response():
            resultat.ajouter_message("ERREUR : donnees de phase manquantes")
            return resultat

        # Unwrap les phases
        phase_a = unwrap_phase(mesure_a.phases)
        phase_b = unwrap_phase(mesure_b.phases)
        freq = mesure_a.frequences

        resultat.ajouter_message(
            f"Calage {mesure_a.nom} / {mesure_b.nom} @ {freq_crossover:.0f} Hz"
        )

        # 1. Calculer le delay
        delay_result = calculer_delay_optimal(
            freq, phase_a, freq, phase_b,
            freq_crossover,
            ir_a=mesure_a.ir_echantillons,
            ir_b=mesure_b.ir_echantillons,
            sr=mesure_a.ir_sample_rate,
        )

        resultat.delay_ms = delay_result["delay_recommande_ms"]
        resultat.appliquer_delay_sur = delay_result["appliquer_sur"]
        resultat.details["delay"] = delay_result

        resultat.ajouter_message(
            f"Delay calcule : {resultat.delay_ms:.2f} ms "
            f"(methode: {delay_result['methode']})"
        )

        # 2. Detecter la polarite
        inverser = detecter_polarite(freq, phase_a, phase_b, freq_crossover)
        resultat.inverser_polarite = inverser

        if inverser:
            resultat.ajouter_message("Polarite : INVERSER recommande")
        else:
            resultat.ajouter_message("Polarite : OK")

        # 3. Coherence de phase
        freq_min = freq_crossover / 2
        freq_max = freq_crossover * 2
        coh = coherence_phase(freq, phase_a, phase_b, freq_min, freq_max)
        resultat.coherence_avant = coh
        resultat.ajouter_message(f"Coherence de phase : {coh:.1%}")

        # 4. Appliquer si demande
        if appliquer and resultat.delay_ms > 0:
            resultat.ajouter_message(
                f"Application delay {resultat.delay_ms:.2f} ms sur {canal_delay}"
            )
            self.dsp.set_delay(canal_delay, resultat.delay_ms)

        return resultat

    def calculer_eq_correctif(
        self,
        mesure: Mesure,
        canal_dsp: str,
        cible_db: Optional[float] = None,
        seuil_db: float = 3.0,
        freq_min: float = 20.0,
        freq_max: float = 20000.0,
        appliquer: bool = False,
    ) -> ResultatCalage:
        """Calcule et applique l'EQ correctif soustractif.

        Args:
            mesure: mesure a corriger.
            canal_dsp: canal DSP cible.
            cible_db: niveau cible en dB (si None, utilise la moyenne).
            seuil_db: seuil de detection des pics.
            freq_min: borne inferieure.
            freq_max: borne superieure.
            appliquer: si True, applique sur le DSP.

        Returns:
            ResultatCalage avec les filtres.
        """
        resultat = ResultatCalage()

        if not mesure.a_freq_response():
            resultat.ajouter_message("ERREUR : donnees frequentielles manquantes")
            return resultat

        resultat.ajouter_message(f"EQ correctif pour {mesure.nom} -> {canal_dsp}")

        # Generer les filtres
        import numpy as np
        cible = None
        if cible_db is not None:
            cible = np.full_like(mesure.magnitudes, cible_db)

        max_bandes = self.dsp.get_nb_bandes_peq(canal_dsp)
        filtres = generer_filtres_correctifs(
            mesure.frequences, mesure.magnitudes,
            cible_db=cible,
            seuil_db=seuil_db,
            freq_min=freq_min,
            freq_max=freq_max,
            max_filtres=max_bandes,
        )

        resultat.filtres_eq = filtres
        resultat.ajouter_message(f"{len(filtres)} pics detectes au-dessus du seuil")

        for i, f in enumerate(filtres):
            resultat.ajouter_message(
                f"  Bande {i}: {f.gain_db:+.1f} dB @ {f.frequence_hz:.0f} Hz Q={f.q:.1f}"
            )

        # Appliquer si demande
        if appliquer and filtres:
            resultat.ajouter_message(f"Application sur {canal_dsp}...")
            for i, filtre in enumerate(filtres):
                self.dsp.set_peq(canal_dsp, i, filtre)
            resultat.ajouter_message("EQ applique.")

        return resultat
