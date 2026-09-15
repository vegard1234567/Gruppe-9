"""MatteHjelpen – FastAPI-backend.

`main.py` er koblingslaget: den leser inn en oppgave, kaller
`llm_client.solve_task(...)`, sender resultatet videre til
`validator.validate(...)`, og former ÉN stabil JSON-respons til frontend –
uansett om noe underveis feiler. Alle 6 påkrevde felt (`svar`, `steg`,
`formler_brukt`, `validert`, `tokens_brukt`, `estimert_kostnad`) er alltid
til stede, pluss `valideringsdetaljer` som forklarer HVORFOR noe ble/ikke
ble validert (ærlighetsprinsippet – appen later aldri som noe er sjekket
når det ikke er det).

FEILHÅNDTERING: en feil i `llm_client` (f.eks. API nede, ugyldig nøkkel, tom
kvote) fanges og vises som en ærlig forklaring i `svar`, med HTTP 502 – ikke
en generisk 500 med stack trace, og ikke et falskt "vellykket" svar. Tomt
input gir 400. En feil i selve valideringen krasjer ikke resten av svaret:
brukeren får fortsatt løsningen, men markert som ikke validert.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from backend import llm_client, validator

app = FastAPI(title="MatteHjelpen")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_FRONTEND_INDEX = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


class Oppgave(BaseModel):
    oppgave: str


@app.get("/")
async def index():
    return FileResponse(_FRONTEND_INDEX)


@app.post("/solve")
async def solve(oppgave: Oppgave):
    tekst = oppgave.oppgave.strip()
    if not tekst:
        return JSONResponse(
            status_code=400,
            content={
                "svar": "Oppgaven er tom – skriv inn en matteoppgave først.",
                "steg": [],
                "formler_brukt": [],
                "validert": False,
                "tokens_brukt": 0,
                "estimert_kostnad": 0.0,
                "valideringsdetaljer": "Ingen oppgave å validere.",
            },
        )

    try:
        resultat = llm_client.solve_task(tekst)
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={
                "svar": f"Kunne ikke hente svar fra språkmodellen akkurat nå. Teknisk feilmelding: {e}",
                "steg": [],
                "formler_brukt": [],
                "validert": False,
                "tokens_brukt": 0,
                "estimert_kostnad": 0.0,
                "valideringsdetaljer": "Ingen validering utført – ingen løsning ble mottatt fra modellen.",
            },
        )

    problem_v = resultat.get("valider_problem") or tekst
    losning_v = resultat.get("valider_losning") or resultat.get("svar", "")
    operasjon_v = resultat.get("valider_operasjon", "auto")
    try:
        validering = validator.validate(problem_v, losning_v, operasjon_v)
    except Exception as e:
        validering = {"validert": False, "detaljer": f"Validering krasjet teknisk: {e}"}

    return {
        "svar": resultat.get("svar", ""),
        "steg": resultat.get("steg", []),
        "formler_brukt": resultat.get("formler_brukt", []),
        "validert": bool(validering.get("validert", False)),
        "tokens_brukt": resultat.get("tokens_brukt", 0),
        "estimert_kostnad": resultat.get("estimert_kostnad", 0.0),
        "valideringsdetaljer": validering.get("detaljer", ""),
    }
