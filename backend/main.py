"""
main.py – FastAPI-hovedapp.
Setter opp /solve-endepunktet og serverer frontend.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import asyncio

from backend import llm_client
from backend.validator import validate


app = FastAPI(title="MatteHjelpen")

# CORS – åpent for lokal utvikling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OppgaveRequest(BaseModel):
    oppgave: str


class OppgaveResponse(BaseModel):
    svar: str
    steg: list[str]
    formler_brukt: list[str]
    validert: bool
    tokens_brukt: int
    estimert_kostnad: float


@app.post("/solve", response_model=OppgaveResponse)
async def solve(request: OppgaveRequest):
    """Løser en matteoppgave og returnerer et stabilt responsformat."""
    if not request.oppgave or not request.oppgave.strip():
        raise HTTPException(status_code=400, detail="Oppgave kan ikke være tom")

    try:
        result = await asyncio.to_thread(llm_client.solve_task, request.oppgave)

        if not isinstance(result, dict):
            raise HTTPException(status_code=500, detail="Ugyldig svar fra løsemotoren")

        if result.get("error"):
            raise HTTPException(status_code=500, detail=result.get("svar", "Ukjent feil"))

        # Sørg for at API-et alltid har alle feltene frontend forventer.
        result.setdefault("svar", "")
        result.setdefault("steg", [])
        result.setdefault("formler_brukt", [])
        result.setdefault("validert", False)
        result.setdefault("tokens_brukt", 0)
        result.setdefault("estimert_kostnad", 0.0)

        return OppgaveResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Kunne ikke løse oppgaven: {e}")


@app.get("/")
async def root():
    """Returner frontend (index.html)."""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"error": "Frontend not found"}


# Monter statiske filer (CSS, JS, etc.)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
