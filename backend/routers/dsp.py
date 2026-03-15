"""Router FastAPI pour le controle DSP t.racks."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.dsp.tracks_hid import TracksDSPHID

router = APIRouter()
_dsp = TracksDSPHID()


class ConnexionDSP(BaseModel):
    host: str = "usb"
    port: int = 0


class GainCmd(BaseModel):
    canal: str
    db: float


class MuteCmd(BaseModel):
    canal: str
    mute: bool


class DelayCmd(BaseModel):
    canal: str
    delay_ms: float


class PEQCmd(BaseModel):
    canal: str
    bande: int
    frequence_hz: float
    gain_db: float
    q: float
    type: str = "peak"
    actif: bool = True


@router.get("/status")
def dsp_status():
    """Statut de la connexion DSP."""
    return {
        "connecte": _dsp.est_connecte(),
        "modele": _dsp.get_nom_modele() if _dsp.est_connecte() else None,
    }


@router.post("/connect")
def connecter_dsp(params: ConnexionDSP):
    """Connecte au DSP t.racks."""
    ok = _dsp.connecter(params.host, params.port)
    if not ok:
        raise HTTPException(503, f"Impossible de se connecter a {params.host}:{params.port}")
    return {
        "connecte": True,
        "modele": _dsp.get_nom_modele(),
        "canaux": _dsp.get_canaux(),
    }


@router.post("/disconnect")
def deconnecter_dsp():
    """Deconnecte du DSP."""
    _dsp.deconnecter()
    return {"connecte": False}


@router.get("/canaux")
def get_canaux():
    """Liste les canaux du DSP."""
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")
    return {
        "entrees": _dsp.get_canaux_entree(),
        "sorties": _dsp.get_canaux_sortie(),
    }


@router.get("/etat")
def get_etat():
    """Etat complet du DSP."""
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")
    return _dsp.get_etat()


@router.post("/gain")
def set_gain(cmd: GainCmd):
    """Regle le gain d'un canal."""
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")
    _dsp.set_gain(cmd.canal, cmd.db)
    return {"ok": True, "canal": cmd.canal, "db": cmd.db}


@router.post("/mute")
def set_mute(cmd: MuteCmd):
    """Mute/unmute un canal."""
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")
    _dsp.set_mute(cmd.canal, cmd.mute)
    return {"ok": True, "canal": cmd.canal, "mute": cmd.mute}


@router.post("/delay")
def set_delay(cmd: DelayCmd):
    """Regle le delay d'un canal."""
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")
    _dsp.set_delay(cmd.canal, cmd.delay_ms)
    return {"ok": True, "canal": cmd.canal, "delay_ms": cmd.delay_ms}


@router.post("/peq")
def set_peq(cmd: PEQCmd):
    """Regle une bande PEQ."""
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")
    from backend.models.filtre import FiltrePEQ, TypeFiltre
    filtre = FiltrePEQ(
        frequence_hz=cmd.frequence_hz,
        gain_db=cmd.gain_db,
        q=cmd.q,
        type=TypeFiltre(cmd.type),
        actif=cmd.actif,
    )
    _dsp.set_peq(cmd.canal, cmd.bande, filtre)
    return {"ok": True, "canal": cmd.canal, "bande": cmd.bande}


@router.get("/metres")
def get_metres():
    """Lecture des metres temps reel."""
    if not _dsp.est_connecte():
        raise HTTPException(503, "DSP non connecte")
    return _dsp.get_metres()
