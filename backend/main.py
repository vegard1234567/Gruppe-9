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
from backend.llm_client import solve_task


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
    """
    Løser en matteoppgave.
    
    Request: {"oppgave": "..."}
    Response: JSON med løsning, steg, formler, validering, tokens
    """
    if not request.oppgave or not request.oppgave.strip():
        raise HTTPException(status_code=400, detail="Oppgave kan ikke være tom")
    
    try:
        # Kall llm_client – kjør synkront i tråd
        loop = asyncio.get_event_loop()
        result = await asyncio.to_thread(solve_task, request.oppgave)
        
        # Sjekk for feil
        if "error" in result:
            raise HTTPException(status_code=500, detail=result.get("svar", "Ukjent feil"))
        
        return OppgaveResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Returner frontend (index.html)"""
    frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    else:
        return {"error": "Frontend not found"}


# Monter statiske filer (CSS, JS, etc.)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.isdir(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
