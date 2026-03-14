"""Router FastAPI pour la gestion du systeme son."""

import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

SYSTEME_FILE = "systeme.json"


class Enceinte(BaseModel):
    id: str
    nom: str
    type: str  # sub, top, fill, delay, monitor, low_mid, high
    canal_dsp: str  # ex: "Out 1"
    hpf_hz: Optional[float] = None
    lpf_hz: Optional[float] = None


class Paire(BaseModel):
    id: str
    enceinte_bas: str  # id de l'enceinte basse (sub)
    enceinte_haut: str  # id de l'enceinte haute (top)
    crossover_hz: float
    # Index des mesures REW associees
    mesure_bas: Optional[int] = None
    mesure_haut: Optional[int] = None
    # Resultats
    delay_ms: Optional[float] = None
    inverser_polarite: Optional[bool] = None
    coherence: Optional[float] = None
    filtres_eq: Optional[list] = None


class Systeme(BaseModel):
    nom: str = "Mon systeme"
    ip_dsp: str = "127.0.0.1"
    port_dsp: int = 9761
    enceintes: List[Enceinte] = []
    paires: List[Paire] = []


def _load() -> Systeme:
    if os.path.exists(SYSTEME_FILE):
        with open(SYSTEME_FILE, "r", encoding="utf-8") as f:
            return Systeme(**json.load(f))
    return Systeme()


def _save(s: Systeme):
    with open(SYSTEME_FILE, "w", encoding="utf-8") as f:
        json.dump(s.model_dump(), f, indent=2, ensure_ascii=False)


# -- Systeme --

@router.get("")
def get_systeme():
    return _load()


@router.put("")
def update_systeme(s: Systeme):
    _save(s)
    return s


# -- Enceintes --

@router.get("/enceintes")
def get_enceintes():
    return _load().enceintes


@router.post("/enceintes")
def add_enceinte(e: Enceinte):
    s = _load()
    # Verifier id unique
    if any(x.id == e.id for x in s.enceintes):
        raise HTTPException(400, f"Enceinte '{e.id}' existe deja")
    s.enceintes.append(e)
    _save(s)
    return e


@router.put("/enceintes/{eid}")
def update_enceinte(eid: str, e: Enceinte):
    s = _load()
    for i, x in enumerate(s.enceintes):
        if x.id == eid:
            s.enceintes[i] = e
            _save(s)
            return e
    raise HTTPException(404, f"Enceinte '{eid}' introuvable")


@router.delete("/enceintes/{eid}")
def delete_enceinte(eid: str):
    s = _load()
    s.enceintes = [x for x in s.enceintes if x.id != eid]
    # Supprimer les paires qui referent cette enceinte
    s.paires = [p for p in s.paires if p.enceinte_bas != eid and p.enceinte_haut != eid]
    _save(s)
    return {"ok": True}


# -- Paires --

@router.get("/paires")
def get_paires():
    return _load().paires


@router.post("/paires")
def add_paire(p: Paire):
    s = _load()
    if any(x.id == p.id for x in s.paires):
        raise HTTPException(400, f"Paire '{p.id}' existe deja")
    s.paires.append(p)
    _save(s)
    return p


@router.put("/paires/{pid}")
def update_paire(pid: str, p: Paire):
    s = _load()
    for i, x in enumerate(s.paires):
        if x.id == pid:
            s.paires[i] = p
            _save(s)
            return p
    raise HTTPException(404, f"Paire '{pid}' introuvable")


@router.delete("/paires/{pid}")
def delete_paire(pid: str):
    s = _load()
    s.paires = [x for x in s.paires if x.id != pid]
    _save(s)
    return {"ok": True}
