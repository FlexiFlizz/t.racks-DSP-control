"""Router FastAPI pour les endpoints REW."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.rew.client import ClientREW

router = APIRouter()
_client = ClientREW()


class SelectMesure(BaseModel):
    index: int


class EQCommand(BaseModel):
    command: str


@router.get("/status")
def rew_status():
    """Statut de la connexion REW."""
    connecte = _client.est_connecte()
    return {"connecte": connecte, "url": _client.base_url}


@router.get("/mesures")
def lister_mesures():
    """Liste les mesures ouvertes dans REW."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    return _client.lister_mesures()


@router.get("/mesures/{id_mesure}")
def get_mesure(id_mesure: int):
    """Recupere les infos d'une mesure."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    data = _client.get_mesure(id_mesure)
    if data is None:
        raise HTTPException(404, f"Mesure {id_mesure} introuvable")
    return data


@router.get("/mesures/{id_mesure}/freq")
def get_freq_response(id_mesure: int, smoothing: str = "1/12", ppo: int = 96):
    """Recupere la reponse en frequence + phase."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    data = _client.get_reponse_frequentielle(id_mesure, smoothing=smoothing, ppo=ppo)
    if data is None:
        raise HTTPException(404, f"Mesure {id_mesure} introuvable")
    # Convertir numpy en listes pour JSON
    return {k: v.tolist() if hasattr(v, 'tolist') else v for k, v in data.items()}


@router.get("/mesures/{id_mesure}/ir")
def get_impulse_response(id_mesure: int):
    """Recupere la reponse impulsionnelle."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    data = _client.get_reponse_impulsionnelle(id_mesure)
    if data is None:
        raise HTTPException(404, f"Mesure {id_mesure} introuvable")
    return {k: v.tolist() if hasattr(v, 'tolist') else v for k, v in data.items()}


@router.get("/mesures/{id_mesure}/group-delay")
def get_group_delay(id_mesure: int, smoothing: str = "1/6"):
    """Recupere le group delay."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    data = _client.get_group_delay(id_mesure, smoothing=smoothing)
    if data is None:
        raise HTTPException(404, f"Mesure {id_mesure} introuvable")
    return {k: v.tolist() if hasattr(v, 'tolist') else v for k, v in data.items()}


@router.post("/select")
def select_mesure(params: SelectMesure):
    """Selectionne une mesure dans REW."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    _client.selectionner_mesure(params.index)
    return {"ok": True, "index": params.index}


@router.get("/mesures/{id_mesure}/eq-commands")
def get_eq_commands(id_mesure: int):
    """Liste les commandes EQ disponibles."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    return _client.get_commandes_eq(id_mesure)


@router.post("/mesures/{id_mesure}/eq-command")
def exec_eq_command(id_mesure: int, params: EQCommand):
    """Execute une commande EQ (Match Target, Optimise, etc.)."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    ok = _client.executer_commande_eq(id_mesure, params.command)
    return {"ok": ok, "command": params.command}


@router.get("/mesures/{id_mesure}/filters")
def get_filters(id_mesure: int):
    """Recupere les filtres EQ d'une mesure."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    return _client.get_filtres(id_mesure)


@router.get("/mesures/{id_mesure}/commands")
def get_commands(id_mesure: int):
    """Liste les commandes de traitement."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    return _client.get_commandes_mesure(id_mesure)


@router.post("/generator/start")
def generator_start():
    """Demarre le generateur de signal REW."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    data = _client._post("/generator/commands", json="Start")
    return {"ok": data is not None}


@router.post("/generator/stop")
def generator_stop():
    """Arrete le generateur de signal REW."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    data = _client._post("/generator/commands", json="Stop")
    return {"ok": data is not None}


@router.get("/audio")
def get_audio():
    """Recupere le statut audio REW."""
    if not _client.est_connecte():
        raise HTTPException(503, "REW non accessible")
    return _client.get_audio_status()
