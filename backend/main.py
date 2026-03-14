"""Point d'entree du backend FastAPI.

Lance avec : uvicorn backend.main:app --reload --port 8765
"""

import asyncio
import subprocess
import sys
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.routers import rew, dsp, calage, systeme, presets

app = FastAPI(
    title="Calage Systeme IA",
    description="Backend pour le calage automatique de systemes son",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(rew.router, prefix="/rew", tags=["REW"])
app.include_router(dsp.router, prefix="/dsp", tags=["DSP"])
app.include_router(calage.router, prefix="/calage", tags=["Calage"])
app.include_router(systeme.router, prefix="/systeme", tags=["Systeme"])
app.include_router(presets.router, prefix="/presets", tags=["Presets"])


@app.get("/")
def root():
    return {"app": "Calage Systeme IA", "version": "0.1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


class CommandRequest(BaseModel):
    command: str


@app.post("/terminal/execute")
def execute_command(req: CommandRequest):
    """Execute une commande et retourne la sortie."""
    try:
        result = subprocess.run(
            req.command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=".",
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Timeout (30s)", "returncode": -1}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1}


@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """WebSocket pour terminal interactif avec streaming."""
    await websocket.accept()
    try:
        while True:
            command = await websocket.receive_text()
            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    cwd=".",
                )
                while True:
                    line = await asyncio.wait_for(
                        process.stdout.readline(), timeout=30
                    )
                    if not line:
                        break
                    await websocket.send_text(line.decode("utf-8", errors="replace"))
                await process.wait()
                await websocket.send_text(f"\n[exit: {process.returncode}]\n")
            except asyncio.TimeoutError:
                await websocket.send_text("\n[timeout]\n")
            except Exception as e:
                await websocket.send_text(f"\n[erreur: {e}]\n")
    except WebSocketDisconnect:
        pass
