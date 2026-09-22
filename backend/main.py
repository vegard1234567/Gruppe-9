"""FastAPI-kobling for MatteHjelpen."""

from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from . import llm_client, validator

app = FastAPI(title="MatteHjelpen")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class Oppgave(BaseModel):
    oppgave: str


@app.get("/")
async def index():
    return FileResponse(Path(__file__).resolve().parent.parent / "frontend" / "index.html")


@app.post("/solve")
async def solve(oppgave: Oppgave):
    if not oppgave.oppgave.strip():
        return {"svar": "Oppgaven kan ikke være tom.", "steg": [], "formler_brukt": [], "validert": False, "tokens_brukt": 0, "estimert_kostnad": 0.0, "feil": "Tom oppgave."}
    try:
        result = llm_client.solve_task(oppgave.oppgave)
        checked = validator.validate(oppgave.oppgave, result.get("svar", ""))
        return {**result, **checked}
    except Exception as exc:
        return {"svar": "Løsningen kunne ikke fullføres.", "steg": [f"Ærlig feilmelding: {exc}"], "formler_brukt": [], "validert": False, "tokens_brukt": 0, "estimert_kostnad": 0.0, "feil": str(exc)}
