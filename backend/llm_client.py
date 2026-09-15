"""
llm_client.py – Kaller språkmodellen med tool-calling-løkke.
Orkestrerer kommunikasjon mellom modell, verktøy og validering.
"""

import os
import json
import httpx
from typing import Any
from backend.tools import TOOL_DEFINITIONS, call_tool
from backend.formelsamling import FORMELSAMLING


# Les fra .env
API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
USE_TOOLS = os.getenv("USE_TOOLS", "true").lower() == "true"

# Systemprompt
SYSTEM_PROMPT = """Du er en matematikklærer for ingeniørstudenter. Din oppgave er å løse matteoppgaver stegvis og pedagogisk.

VIKTIG: Bruk verktøyene (SymPy) til ALL beregning når oppgaven lar seg beregne – du skal ALDRI late som du har brukt et verktøy du ikke faktisk kalte.

Hvis oppgaven ikke kan beregnes (f.eks. et bevis eller en begrepsforklaring), resonnerer du i tekst og sier EKSPLISITT at svaret IKKE er verifisert av et verktøy. Dette er ikke noe å skjule – det er en legitim og forventet del av matematikken.

For hver løsning:
1. Forklar hvert steg pedagogisk på norsk.
2. Bruk verktøyene når det kreves beregning.
3. Oppgi formel-ID (fra formelsamlingen nedenfor) for hver formel du bruker, f.eks. "D1" for produktregelen.
4. Vis LaTeX-uttrykk med \\( \\) rundt dem.
5. Hvis du er usikker, si det eksplisitt.

Tilgjengelige verktøy: derive, integrate, solve_equation, solve_ode, matrix_op, complex_op

FORMELSAMLING (referanse):
"""

# Bygger systemprompt med formelsamling
for formel_id, data in FORMELSAMLING.items():
    SYSTEM_PROMPT += f"\n{formel_id}: {data['navn']}\n"
    SYSTEM_PROMPT += f"  Formel: {data['formel']}\n"
    SYSTEM_PROMPT += f"  Bruk: {data['bruk']}\n"
    SYSTEM_PROMPT += f"  Referanse: {data['referanse']}\n"

SYSTEM_PROMPT += "\nBruk disse ID-ene når du oppgir hvilke formler du brukte."


def solve_task(oppgave: str) -> dict:
    """
    Løser en matteoppgave ved hjelp av LLM + tool-calling.
    
    Args:
        oppgave: Matteoppgaven som en string
    
    Returns:
        dict med svar, steg, formler, validering, og tokens
    """
    
    if not API_KEY:
        return {
            "svar": "Feil: API_KEY ikke satt. Se .env.example.",
            "steg": [],
            "formler_brukt": [],
            "validert": False,
            "tokens_brukt": 0,
            "estimert_kostnad": 0.0,
            "error": "API_KEY missing"
        }
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": oppgave}
    ]
    
    # Tools parameter (kun hvis USE_TOOLS er True)
    tools_param = TOOL_DEFINITIONS if USE_TOOLS else None
    
    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls_made = []
    
    try:
        # Tool-calling loop
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Kall modellen
            response = httpx.post(
                f"{API_BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {API_KEY}"},
                json={
                    "model": MODEL_NAME,
                    "messages": messages,
                    "tools": tools_param,
                    "tool_choice": "auto" if USE_TOOLS else None,
                    "temperature": 0.7,
                    "max_tokens": 2000
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                return {
                    "svar": f"Feil fra API: {response.status_code}",
                    "steg": [],
                    "formler_brukt": [],
                    "validert": False,
                    "tokens_brukt": 0,
                    "estimert_kostnad": 0.0,
                    "error": response.text
                }
            
            data = response.json()
            
            # Tell tokens
            if "usage" in data:
                total_input_tokens += data["usage"].get("prompt_tokens", 0)
                total_output_tokens += data["usage"].get("completion_tokens", 0)
            
            choice = data["choices"][0]
            assistant_message = choice["message"]
            messages.append(assistant_message)
            
            # Sjekk om det er tool-kall
            if "tool_calls" not in assistant_message or not assistant_message["tool_calls"]:
                # Ferdig – vi har endelig svar
                final_response = assistant_message.get("content", "")
                break
            
            # Håndter tool-kall
            for tool_call in assistant_message["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                tool_id = tool_call["id"]
                
                # Kall verktøy
                try:
                    tool_result = call_tool(tool_name, **tool_args)
                    tool_calls_made.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": tool_result
                    })
                except Exception as e:
                    tool_result = {"success": False, "error": str(e)}
                
                # Legg resultat tilbake i samtalen
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": json.dumps(tool_result)
                })
        
        # Parse svaret – trekk ut steg, formler, osv.
        steg = parse_steg(final_response)
        formler_brukt = extract_formler(final_response)
        
        # Validering (simpel versjon – kan utvides)
        validert = len(tool_calls_made) > 0 and validate_response(final_response)
        
        # Estimér kostnad (avhenger av modell)
        estimert_kostnad = estimate_cost(MODEL_NAME, total_input_tokens, total_output_tokens)
        
        return {
            "svar": final_response,
            "steg": steg,
            "formler_brukt": formler_brukt,
            "validert": validert,
            "tokens_brukt": total_input_tokens + total_output_tokens,
            "estimert_kostnad": round(estimert_kostnad, 6),
            "tool_calls": tool_calls_made
        }
    
    except Exception as e:
        return {
            "svar": f"Feil: {str(e)}",
            "steg": [],
            "formler_brukt": [],
            "validert": False,
            "tokens_brukt": total_input_tokens + total_output_tokens,
            "estimert_kostnad": 0.0,
            "error": str(e)
        }


def parse_steg(response: str) -> list[str]:
    """
    Trekk ut løsningssteg fra modellens svar.
    (Enkel heuristikk – kan forbedres.)
    """
    steg = []
    lines = response.split('\n')
    
    for line in lines:
        # Hvis linja starter med tall + punkt eller bindestreker, er det nok et steg
        if line.strip() and (line.strip()[0].isdigit() or line.strip().startswith('•')):
            steg.append(line.strip())
    
    # Hvis få steg funnet, del på punkter
    if len(steg) < 2:
        steg = [s.strip() for s in response.split('.') if s.strip()]
    
    return steg[:20]  # Max 20 steg


def extract_formler(response: str) -> list[str]:
    """
    Trekk ut refererte formel-ID-er fra svaret.
    """
    formler = []
    
    # Søk etter formel-ID-er (D1, D2, I1, osv.)
    for formel_id in FORMELSAMLING.keys():
        if formel_id in response:
            data = FORMELSAMLING[formel_id]
            formler.append(f"{formel_id}: {data['navn']} ({data['referanse']})")
    
    return formler


def validate_response(response: str) -> bool:
    """
    Enkel validering av om svaret ser ut til å være fullstendig.
    """
    # Hvis svaret inneholder LaTeX eller tall, antar vi det er validert
    return "(" in response and ("(" in response or "=" in response)


def estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    Estimerer kostnad basert på modell og token-bruk.
    (Prisene er eksempler – oppdater med faktiske priser.)
    """
    # Priser per 1M tokens (eksempel for OpenAI, nov 2024)
    prices = {
        "gpt-4o": {"input": 5.0, "output": 15.0},
        "gpt-4o-mini": {"input": 0.15, "output": 0.6},
        "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
    }
    
    # Standard til billigste hvis ikke kjent
    price_info = prices.get(model_name, {"input": 0.1, "output": 0.3})
    
    input_cost = (input_tokens / 1_000_000) * price_info["input"]
    output_cost = (output_tokens / 1_000_000) * price_info["output"]
    
    return input_cost + output_cost
