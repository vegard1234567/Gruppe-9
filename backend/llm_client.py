"""
llm_client.py – Kaller språkmodellen med tool-calling-løkke.
Orkestrerer kommunikasjon mellom modell, verktøy og validering.
"""

import os
import json
import httpx
from dotenv import load_dotenv
from typing import Any
from backend.tools import TOOL_DEFINITIONS, call_tool
from backend.formelsamling import FORMELSAMLING

load_dotenv()

API_KEY = os.getenv("API_KEY", "")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1").rstrip("/")
USE_TOOLS = os.getenv("USE_TOOLS", "true").lower() == "true"

SYSTEM_PROMPT = """Du er en matematikklærer for ingeniørstudenter. Din oppgave er å løse matteoppgaver stegvis og pedagogisk.

VIKTIG: Bruk verktøyene (SymPy) til ALL beregning når oppgaven lar seg beregne.

For hver løsning:
1. Forklar hvert steg pedagogisk på norsk.
2. Bruk verktøyene når det kreves beregning.
3. Oppgi formel-ID fra formelsamlingen når en formel brukes.
4. Vis LaTeX-uttrykk med \\( \\) rundt dem.

Tilgjengelige verktøy: derive, integrate, solve_equation, solve_ode, matrix_op, complex_op

FORMELSAMLING:
"""

for formel_id, data in FORMELSAMLING.items():
    SYSTEM_PROMPT += f"\n{formel_id}: {data['navn']}\n  Formel: {data['formel']}\n  Bruk: {data['bruk']}\n  Referanse: {data['referanse']}\n"

SYSTEM_PROMPT += "\nBruk disse ID-ene når du oppgir hvilke formler du brukte."


def solve_task(oppgave: str) -> dict:
    if not API_KEY:
        return {"svar": "Feil: API_KEY ikke satt. Se .env.example.", "steg": [], "formler_brukt": [], "validert": False, "tokens_brukt": 0, "estimert_kostnad": 0.0, "error": "API_KEY missing"}

    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": oppgave}]
    tools_param = TOOL_DEFINITIONS if USE_TOOLS else None
    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls_made = []
    final_response = ""

    try:
        for _ in range(10):
            payload = {"model": MODEL_NAME, "messages": messages, "temperature": 0.2, "max_tokens": 2000}
            if tools_param:
                payload["tools"] = tools_param
                payload["tool_choice"] = "auto"
            response = httpx.post(f"{API_BASE_URL}/chat/completions", headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, json=payload, timeout=60.0)
            if response.status_code != 200:
                return {"svar": f"Feil fra API ({response.status_code}). Sjekk API_KEY, MODEL_NAME og API_BASE_URL.", "steg": [], "formler_brukt": [], "validert": False, "tokens_brukt": 0, "estimert_kostnad": 0.0, "error": response.text[:1000]}
            data = response.json()
            usage = data.get("usage", {})
            total_input_tokens += usage.get("prompt_tokens", 0)
            total_output_tokens += usage.get("completion_tokens", 0)
            assistant_message = data["choices"][0]["message"]
            messages.append(assistant_message)
            calls = assistant_message.get("tool_calls", []) or []
            if not calls:
                final_response = assistant_message.get("content", "") or "Modellen returnerte ikke et svar."
                break
            for tool_call in calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"].get("arguments", "{}"))
                tool_result = call_tool(tool_name, **tool_args)
                tool_calls_made.append({"tool": tool_name, "args": tool_args, "result": tool_result})
                messages.append({"role": "tool", "tool_call_id": tool_call["id"], "content": json.dumps(tool_result, ensure_ascii=False)})
        else:
            return {"svar": "For mange beregningssteg.", "steg": [], "formler_brukt": [], "validert": False, "tokens_brukt": total_input_tokens + total_output_tokens, "estimert_kostnad": 0.0, "error": "max_iterations"}

        steg = parse_steg(final_response)
        formler_brukt = extract_formler(final_response)
        return {"svar": final_response, "steg": steg, "formler_brukt": formler_brukt, "validert": bool(tool_calls_made), "tokens_brukt": total_input_tokens + total_output_tokens, "estimert_kostnad": round(estimate_cost(MODEL_NAME, total_input_tokens, total_output_tokens), 6), "tool_calls": tool_calls_made}
    except Exception as e:
        return {"svar": f"Feil: {e}", "steg": [], "formler_brukt": [], "validert": False, "tokens_brukt": total_input_tokens + total_output_tokens, "estimert_kostnad": 0.0, "error": str(e)}


def parse_steg(response: str) -> list[str]:
    steg = []
    for line in response.split("\n"):
        s = line.strip()
        if s and (s[0].isdigit() or s.startswith("•")):
            steg.append(s)
    if len(steg) < 2:
        steg = [s.strip() for s in response.split(".") if s.strip()]
    return steg[:20]


def extract_formler(response: str) -> list[str]:
    return [f"{k}: {v['navn']} ({v['referanse']})" for k, v in FORMELSAMLING.items() if k in response]


def estimate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    prices = {"gpt-4o": {"input": 5.0, "output": 15.0}, "gpt-4o-mini": {"input": 0.15, "output": 0.6}}
    p = prices.get(model_name, {"input": 0.0, "output": 0.0})
    return (input_tokens / 1000000) * p["input"] + (output_tokens / 1000000) * p["output"]
