"""LLM-klient for MatteHjelpen: kaller modellen og styrer tool-calling-løkken.

ARKITEKTUR: `solve_task(...)` er en orkestrator, ikke en matte-motor. Modellen
foreslår hvilket SymPy-verktøy som trengs; `backend/tools.py` gjør selve
beregningen; denne filen sender resultatet tilbake til modellen til den er
ferdig, og pakker sluttresultatet som en dict `main.py` kan sende som JSON.

STRUKTURERT SLUTTSVAR: I stedet for å tolke fri tekst (skjørt og lett å
mistolke), MÅ modellen levere sluttsvaret via funksjonen `lever_svar`
(se `_LEVER_SVAR_TOOL` under) – på samme måte som den kaller `derive`,
`integrate` osv. Det gir strukturerte steg og formel-ID-er vi kan kontrollere
programmatisk, i stedet for å måtte gjette ut fra rå tekst.

ANTI-HALLUSINASJON: Verktøyloggen (`verktoy_brukt`) bygges KUN fra faktiske
`tool_calls` modellen ber om i løkken – aldri fra det modellen selv skriver
at den "har gjort". Formel-ID-er fra `lever_svar` kontrolleres mot
FORMELSAMLING før de tas med i responsen; en ukjent ID blir stille forkastet
(vi stoler ikke på at modellen dikter opp en referanse). En gyldig ID beviser
uansett bare at formelen finnes i samlingen – ikke at den ble brukt riktig.

AHA-BRYTER 1 (OPPGAVE.md): sett USE_TOOLS = False for å se hvordan appen
oppfører seg uten SymPy-verktøyene tilgjengelig (kun `lever_svar` er da
tilgjengelig, så modellen må resonnere/"regne" helt på egen hånd).
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from backend import tools
from backend.formelsamling import FORMELSAMLING

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

USE_TOOLS = True  # <-- Aha-bryter nr. 1

MAKS_VERKTOYRUNDER = 8  # Øvre grense for modell<->verktøy-runder – unngår evighetsløkke.
# Et fast tall fremfor "til modellen er fornøyd": åtte runder dekker god margin for de fleste
# oppgaver her (typisk 1-3 verktøykall + ett `lever_svar`-kall), uten å risikere at en
# forvirret modell kjører (og koster tokens) i det uendelige.

SYSTEMPROMPT_KJERNE = """Du er en matematikklærer for ingeniørstudenter. Bruk verktøyene (SymPy)
til all beregning når oppgaven lar seg beregne slik – du skal ALDRI late
som du har brukt et verktøy du ikke faktisk kalte. Kan oppgaven ikke
beregnes (f.eks. et bevis eller en begrepsforklaring), resonnerer du i
tekst og sier eksplisitt at svaret IKKE er verifisert av et verktøy.
Forklar hvert steg pedagogisk på norsk, og oppgi nøyaktig hvilke
formler/verktøy du faktisk brukte. Knytt hver formel-ID til steget der
den brukes, og ta med navn og referanse fra formelsamlingen.
Hvis du er usikker, si det eksplisitt.

Unngå unødvendig fagsjargong, og forklar alltid HVORFOR et steg gjøres
(ikke bare hva som gjøres) – målet er at en medstudent skal forstå
resonnementet, ikke bare fasiten.

Når du er klar til å gi det endelige svaret, MÅ du kalle funksjonen
lever_svar med hele svaret strukturert (svar, steg, formel-ID-er).
Ikke skriv sluttsvaret som vanlig chat-tekst."""


def _formelsamling_tekst() -> str:
    linjer = [
        f"- {fid}: {f['navn']} | {f['formel']} | Bruk: {f['bruk']} | Ref: {f['referanse']}"
        for fid, f in FORMELSAMLING.items()
    ]
    return "Tilgjengelig formelsamling (bruk kun disse ID-ene i formel_id):\n" + "\n".join(linjer)


_LEVER_SVAR_TOOL = {
    "type": "function",
    "function": {
        "name": "lever_svar",
        "description": "Leverer det endelige, strukturerte svaret til studenten. Kall denne til slutt, alltid.",
        "parameters": {
            "type": "object",
            "properties": {
                "svar": {
                    "type": "string",
                    "description": "Kort, konkret sluttsvar. Kan inneholde LaTeX i \\( ... \\).",
                },
                "steg": {
                    "type": "array",
                    "description": "Stegvis, pedagogisk forklaring på norsk – ett steg per element.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "tekst": {"type": "string", "description": "Forklaringen for dette steget."},
                            "formel_id": {
                                "type": ["string", "null"],
                                "description": "ID fra formelsamlingen brukt i DETTE steget, eller null om ingen.",
                            },
                        },
                        "required": ["tekst"],
                    },
                },
                "kan_valideres_maskinelt": {
                    "type": "boolean",
                    "description": (
                        "True hvis svaret er et konkret uttrykk/likning et SymPy-verktøy kan sjekke "
                        "numerisk (derivasjon, integral, likning, ODE). False for bevis/begrepsoppgaver "
                        "eller andre svar uten en enkelt sjekkbar formel."
                    ),
                },
                "usikker": {
                    "type": "boolean",
                    "description": "True hvis du selv er usikker på om svaret er riktig.",
                },
            },
            "required": ["svar", "steg", "kan_valideres_maskinelt"],
        },
    },
}


def _tool_definisjoner() -> list:
    definisjoner = [_LEVER_SVAR_TOOL]
    if USE_TOOLS:
        definisjoner += tools.TOOL_DEFINITIONS
    return definisjoner


def _kjor_verktoy(navn: str, argumenter: dict) -> dict:
    fn = getattr(tools, navn, None)
    if fn is None or navn not in {t["function"]["name"] for t in tools.TOOL_DEFINITIONS}:
        return {"feil": f"Ukjent verktøy: {navn!r}."}
    try:
        return fn(**argumenter)
    except TypeError as e:
        return {"feil": f"Feil argumenter til {navn}: {e}"}
    except ValueError as e:
        return {"feil": str(e)}
    except Exception as e:
        return {"feil": f"Uventet feil i {navn}: {e}"}


def _hent_klient() -> OpenAI:
    api_key = os.getenv("API_KEY")
    base_url = os.getenv("API_BASE_URL")
    if not api_key or api_key == "sk-xxx":
        raise RuntimeError(
            "API_KEY er ikke satt. Kopiér .env.example til .env og fyll inn en gyldig (gratis) API-nøkkel."
        )
    if not base_url:
        raise RuntimeError("API_BASE_URL er ikke satt i .env.")
    return OpenAI(api_key=api_key, base_url=base_url)


def _bygg_valideringsgrunnlag(kall: dict) -> tuple[str | None, str | None]:
    """Gjenskaper (problem, løsning) for validator.py fra ET faktisk tool-kall."""
    navn, args, res = kall["navn"], kall["argumenter"], kall["resultat"]
    if "feil" in res:
        return None, None
    if navn in ("derive", "integrate"):
        return args.get("uttrykk"), res.get("resultat")
    if navn in ("solve_equation", "solve_ode"):
        return args.get("ligning"), res.get("resultat")
    return None, None


def _estimer_kostnad(usage_sum: dict) -> tuple:
    """Regner ut estimert kostnad i USD fra akkumulert token-forbruk.

    Prisen leses fra .env (PRIS_PER_1M_INPUT_TOKENS / PRIS_PER_1M_OUTPUT_TOKENS),
    og er 0 som standard (riktig for gratis-modeller, jf. gratisprinsippet i
    OPPGAVE.md) – sett dem selv for å estimere kostnad med en betalt modell i
    Del B. Mangler API-et token-tall i det hele tatt (skjer ikke med `openai`
    mot et ekte API, men er en ærlig fallback), vises "ukjent" fremfor et
    hardkodet 0-tall vi ikke faktisk vet stemmer.
    """
    if usage_sum["total_tokens"] == 0 and usage_sum["prompt_tokens"] == 0:
        return "ukjent", 0.0
    pris_inn = float(os.getenv("PRIS_PER_1M_INPUT_TOKENS", "0") or 0)
    pris_ut = float(os.getenv("PRIS_PER_1M_OUTPUT_TOKENS", "0") or 0)
    kostnad = (usage_sum["prompt_tokens"] * pris_inn + usage_sum["completion_tokens"] * pris_ut) / 1_000_000
    return usage_sum["total_tokens"], round(kostnad, 6)


def solve_task(oppgave: str) -> dict:
    """Løser en matteoppgave via LLM + SymPy-verktøy. Returnerer dict iht. SYSTEMBESKRIVELSE.md."""
    modell = os.getenv("MODEL_NAME")
    if not modell:
        raise RuntimeError("MODEL_NAME er ikke satt i .env.")
    klient = _hent_klient()

    meldinger = [
        {"role": "system", "content": SYSTEMPROMPT_KJERNE + "\n\n" + _formelsamling_tekst()},
        {"role": "user", "content": oppgave},
    ]

    verktoy_brukt: list = []
    usage_sum = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    strukturert_svar: dict | None = None

    for runde in range(MAKS_VERKTOYRUNDER):
        respons = klient.chat.completions.create(
            model=modell,
            messages=meldinger,
            tools=_tool_definisjoner(),
        )
        if respons.usage:
            for felt in usage_sum:
                usage_sum[felt] += getattr(respons.usage, felt, 0) or 0

        melding = respons.choices[0].message
        meldinger.append(melding.model_dump(exclude_none=True))

        if not melding.tool_calls:
            if runde == MAKS_VERKTOYRUNDER - 1:
                break
            meldinger.append(
                {
                    "role": "user",
                    "content": "Husk å levere sluttsvaret ved å kalle funksjonen lever_svar, ikke som ren tekst.",
                }
            )
            continue

        ferdig = False
        for tool_call in melding.tool_calls:
            navn = tool_call.function.name
            try:
                argumenter = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                argumenter = {}

            if navn == "lever_svar":
                strukturert_svar = argumenter
                resultat_for_modell = {"status": "mottatt"}
                ferdig = True
            else:
                resultat_for_modell = _kjor_verktoy(navn, argumenter)
                verktoy_brukt.append({"navn": navn, "argumenter": argumenter, "resultat": resultat_for_modell})

            meldinger.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(resultat_for_modell, ensure_ascii=False),
                }
            )

        if ferdig:
            break

    tokens_brukt, estimert_kostnad = _estimer_kostnad(usage_sum)

    if strukturert_svar is None:
        siste_innhold = meldinger[-1].get("content")
        siste_tekst = siste_innhold if isinstance(siste_innhold, str) and siste_innhold else None
        return {
            "svar": siste_tekst
            or "Modellen klarte ikke å levere et strukturert svar innenfor rundegrensen. Prøv igjen, "
            "gjerne med en enklere/mer presist formulert oppgave.",
            "steg": [],
            "formler_brukt": [],
            "tokens_brukt": tokens_brukt,
            "estimert_kostnad": estimert_kostnad,
            "valider_problem": None,
            "valider_losning": None,
            "valider_operasjon": "auto",
        }

    steg_tekster = []
    formler_brukt = []
    for i, steg in enumerate(strukturert_svar.get("steg") or [], start=1):
        if isinstance(steg, dict):
            tekst = steg.get("tekst", "")
            formel_id = steg.get("formel_id")
        else:
            tekst, formel_id = str(steg), None
        steg_tekster.append(tekst)
        if formel_id and formel_id in FORMELSAMLING:
            f = FORMELSAMLING[formel_id]
            formler_brukt.append({"id": formel_id, "navn": f["navn"], "referanse": f["referanse"], "steg": i})

    svar_tekst = strukturert_svar.get("svar", "")
    if strukturert_svar.get("usikker"):
        svar_tekst += "\n\n⚠️ Modellen har selv markert dette svaret som usikkert."

    valider_problem = valider_losning = None
    valider_operasjon = "auto"
    if strukturert_svar.get("kan_valideres_maskinelt") and verktoy_brukt:
        siste_vellykkede = next((k for k in reversed(verktoy_brukt) if "feil" not in k["resultat"]), None)
        if siste_vellykkede is not None:
            valider_operasjon = siste_vellykkede["navn"]
            valider_problem, valider_losning = _bygg_valideringsgrunnlag(siste_vellykkede)

    return {
        "svar": svar_tekst,
        "steg": steg_tekster,
        "formler_brukt": formler_brukt,
        "tokens_brukt": tokens_brukt,
        "estimert_kostnad": estimert_kostnad,
        "valider_problem": valider_problem,
        "valider_losning": valider_losning,
        "valider_operasjon": valider_operasjon,
    }
