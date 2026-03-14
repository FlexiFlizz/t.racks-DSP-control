"""Router FastAPI pour les presets d'enceintes."""

import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List

router = APIRouter()

PRESETS_FILE = os.path.join(os.path.dirname(__file__), "..", "presets", "enceintes.json")
CUSTOM_FILE = os.path.join(os.path.dirname(__file__), "..", "presets", "custom.json")


def _load_presets() -> dict:
    with open(PRESETS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_custom() -> list:
    if os.path.exists(CUSTOM_FILE):
        with open(CUSTOM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _save_custom(data: list):
    os.makedirs(os.path.dirname(CUSTOM_FILE), exist_ok=True)
    with open(CUSTOM_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class PresetEnceinte(BaseModel):
    id: str
    nom: str
    type: str
    hp: str = ""
    bande: str = ""
    hpf_hz: Optional[float] = None
    lpf_hz: Optional[float] = None
    notes: str = ""


@router.get("")
def list_presets():
    """Liste tous les presets (built-in + custom)."""
    data = _load_presets()
    custom = _load_custom()
    if custom:
        data["categories"].append({
            "nom": "Mes enceintes",
            "enceintes": custom,
        })
    return data


@router.get("/flat")
def list_flat():
    """Liste tous les presets a plat (sans categories)."""
    data = _load_presets()
    custom = _load_custom()
    all_presets = []
    for cat in data.get("categories", []):
        for enc in cat.get("enceintes", []):
            enc["categorie"] = cat["nom"]
            all_presets.append(enc)
    for enc in custom:
        enc["categorie"] = "Mes enceintes"
        all_presets.append(enc)
    return all_presets


@router.post("/custom")
def add_custom(preset: PresetEnceinte):
    """Ajoute un preset custom."""
    custom = _load_custom()
    if any(p["id"] == preset.id for p in custom):
        raise HTTPException(400, f"Preset '{preset.id}' existe deja")
    custom.append(preset.model_dump())
    _save_custom(custom)
    return preset


@router.put("/custom/{pid}")
def update_custom(pid: str, preset: PresetEnceinte):
    """Met a jour un preset custom."""
    custom = _load_custom()
    for i, p in enumerate(custom):
        if p["id"] == pid:
            custom[i] = preset.model_dump()
            _save_custom(custom)
            return preset
    raise HTTPException(404, f"Preset '{pid}' introuvable")


@router.delete("/custom/{pid}")
def delete_custom(pid: str):
    """Supprime un preset custom."""
    custom = _load_custom()
    custom = [p for p in custom if p["id"] != pid]
    _save_custom(custom)
    return {"ok": True}
