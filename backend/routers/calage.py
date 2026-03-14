"""Router FastAPI pour le moteur de calage."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()


class CalageDeuxSources(BaseModel):
    index_mesure_a: int
    index_mesure_b: int
    freq_crossover: float
    canal_delay: str
    appliquer: bool = False
    smoothing: str = "1/12"


class CalageEQ(BaseModel):
    index_mesure: int
    canal_dsp: str
    cible_db: Optional[float] = None
    seuil_db: float = 3.0
    freq_min: float = 20.0
    freq_max: float = 20000.0
    appliquer: bool = False
    smoothing: str = "1/12"


@router.post("/delay")
def caler_delay(params: CalageDeuxSources):
    """Calcule et applique le delay entre deux sous-systemes."""
    from backend.rew.client import ClientREW
    from backend.dsp.tracks import TracksDSP
    from backend.core.moteur_script import MoteurScript

    rew = ClientREW()
    if not rew.est_connecte():
        raise HTTPException(503, "REW non accessible")

    # Pour le calage, on utilise le DSP global du router dsp
    from backend.routers.dsp import _dsp
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")

    moteur = MoteurScript(rew, _dsp)

    mesure_a = moteur.charger_mesure(params.index_mesure_a, params.smoothing)
    mesure_b = moteur.charger_mesure(params.index_mesure_b, params.smoothing)

    if mesure_a is None or mesure_b is None:
        raise HTTPException(404, "Mesure introuvable dans REW")

    resultat = moteur.caler_deux_sources(
        mesure_a, mesure_b,
        freq_crossover=params.freq_crossover,
        canal_delay=params.canal_delay,
        appliquer=params.appliquer,
    )

    return {
        "delay_ms": resultat.delay_ms,
        "appliquer_sur": resultat.appliquer_delay_sur,
        "inverser_polarite": resultat.inverser_polarite,
        "coherence_phase": resultat.coherence_avant,
        "messages": resultat.messages,
        "details": resultat.details,
    }


@router.post("/eq")
def caler_eq(params: CalageEQ):
    """Calcule et applique l'EQ correctif soustractif."""
    from backend.rew.client import ClientREW
    from backend.core.moteur_script import MoteurScript

    rew = ClientREW()
    if not rew.est_connecte():
        raise HTTPException(503, "REW non accessible")

    from backend.routers.dsp import _dsp
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")

    moteur = MoteurScript(rew, _dsp)

    mesure = moteur.charger_mesure(params.index_mesure, params.smoothing)
    if mesure is None:
        raise HTTPException(404, "Mesure introuvable dans REW")

    resultat = moteur.calculer_eq_correctif(
        mesure,
        canal_dsp=params.canal_dsp,
        cible_db=params.cible_db,
        seuil_db=params.seuil_db,
        freq_min=params.freq_min,
        freq_max=params.freq_max,
        appliquer=params.appliquer,
    )

    return {
        "filtres": [
            {
                "frequence_hz": f.frequence_hz,
                "gain_db": f.gain_db,
                "q": f.q,
                "type": f.type.value,
            }
            for f in resultat.filtres_eq
        ],
        "messages": resultat.messages,
    }
