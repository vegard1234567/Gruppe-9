"""LLM-klient for MatteHjelpen.

SKJELETT – TODO:
- Les API_KEY, MODEL_NAME og API_BASE_URL fra .env (python-dotenv).
- Bruk openai-biblioteket med base_url mot et OpenAI-kompatibelt API
  (f.eks. OpenRouter, OpenAI selv, eller en annen leverandør).
- SYSTEMPROMPT (viktig – ikke fjern kravene uten å forstå konsekvensen!):

  "Du er en matematikklærer for ingeniørstudenter. Bruk verktøyene (SymPy)
  til all beregning når oppgaven lar seg beregne slik – du skal ALDRI late
  som du har brukt et verktøy du ikke faktisk kalte. Kan oppgaven ikke
  beregnes (f.eks. et bevis eller en begrepsforklaring), resonnerer du i
  tekst og sier eksplisitt at svaret IKKE er verifisert av et verktøy.
  Forklar hvert steg pedagogisk på norsk, og oppgi nøyaktig hvilke
  formler/verktøy du faktisk brukte. Knytt hver formel-ID til steget der den
  brukes, og ta med navn og referanse fra formelsamlingen.
  Hvis du er usikker, si det eksplisitt."

  MERK: «all beregning gjøres via verktøy» gjelder ting SymPy faktisk kan
  regne (derivasjon, ligninger, matriser, ...) – ikke bevis eller
  begrepsforklaringer. Det er legitime matteoppgaver appen skal svare
  ærlig på, uten å late som SymPy validerte noe den ikke kan validere.

- ANTI-HALLUSINASJON: Ikke stol på at modellen forteller sant om egen
  verktøybruk. Bygg verktøyloggen fra faktiske tool_calls. Modellen kan
  foreslå formel-ID per steg, men ID-en må finnes i formelsamlingen; hent
  navn og referanse derfra i stedet for å stole på fri tekst.

- FORMELSAMLING: Send oppføringene fra formelsamling.py til modellen i et
  kompakt format med ID, navn, formel, bruk og referanse. Kontroller at alle
  returnerte formel-ID-er finnes i FORMELSAMLING. Formelreferanser forklarer
  metoden; de beviser ikke at et SymPy-verktøy faktisk ble kalt.

- Implementer tool-calling-løkke:
  1) Send oppgaven + tool-definisjoner fra tools.py
  2) Hvis modellen ber om tool-kall: kjør funksjonen, legg resultatet i samtalen
  3) Gjenta til modellen gir endelig svar
- Tell tokens (response.usage) og estimer kostnad.

EKSPERIMENT-BRYTER: Sett USE_TOOLS = False og se hva som skjer med en billig
modell. Dokumenter i EKSPERIMENT.md!
"""

import json
import os
import re

from dotenv import load_dotenv
from openai import OpenAI

from .formelsamling import FORMELSAMLING
from .tools import TOOL_DEFINITIONS, call_tool


USE_TOOLS = True
MAX_ROUNDS = 8
SYSTEM_PROMPT = """Du er en matematikklærer for ingeniørstudenter. Bruk verktøyene (SymPy) til all symbolsk og numerisk beregning når oppgaven lar seg beregne slik. Du skal aldri late som du har brukt et verktøy du ikke faktisk kalte. Bevis og begrepsforklaringer kan besvares i tekst, men si eksplisitt at de IKKE er verifisert av et verktøy. Forklar pedagogisk på norsk.

Returner til slutt kun JSON med feltene svar (streng), steg (liste av strenger), og formler_brukt (liste av objekter med id og steg). Formel-ID-er må hentes fra formelsamlingen under. Knytt hver formel til steget der den faktisk brukes. Ikke bruk en beregning i forklaringen som ikke kommer fra et tool-resultat.

FORMELSAMLING:
""" + json.dumps(FORMELSAMLING, ensure_ascii=False)


def _model_config():
  load_dotenv()
  api_key = os.getenv("API_KEY")
  model = os.getenv("MODEL_NAME")
  if not api_key or not model:
    raise RuntimeError("API_KEY og MODEL_NAME må være satt i .env før appen kan bruke språkmodellen.")
  kwargs = {"api_key": api_key}
  if os.getenv("API_BASE_URL"):
    kwargs["base_url"] = os.getenv("API_BASE_URL")
  return OpenAI(**kwargs), model


def _usage_total(usage):
  if not usage:
    return 0
  return int(getattr(usage, "total_tokens", 0) or 0)


def _cost(tokens: int) -> float:
  input_rate = float(os.getenv("INPUT_COST_PER_1M", "0"))
  output_rate = float(os.getenv("OUTPUT_COST_PER_1M", "0"))
  return round(tokens * (input_rate + output_rate) / 2_000_000, 8)


def _normalise_result(content: str) -> dict:
  try:
    match = re.search(r"\{.*\}", content, re.DOTALL)
    parsed = json.loads(match.group(0) if match else content)
  except (json.JSONDecodeError, TypeError):
    parsed = {"svar": content, "steg": [line.strip() for line in content.splitlines() if line.strip()], "formler_brukt": []}
  valid_formulas = []
  for item in parsed.get("formler_brukt", []):
    item = {"id": item} if isinstance(item, str) else item
    formula_id = item.get("id") if isinstance(item, dict) else None
    if formula_id in FORMELSAMLING:
      valid_formulas.append({"id": formula_id, "navn": FORMELSAMLING[formula_id]["navn"], "referanse": FORMELSAMLING[formula_id]["referanse"], "steg": item.get("steg", "")})
  return {"svar": parsed.get("svar", content), "steg": parsed.get("steg", []), "formler_brukt": valid_formulas}


def solve_task(oppgave: str) -> dict:
  """Orkestrerer modellen og faktiske SymPy tool-kall."""
  client, model = _model_config()
  messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": oppgave}]
  tools = TOOL_DEFINITIONS if USE_TOOLS else None
  total_tokens = 0
  tool_log = []
  final_content = ""
  for _ in range(MAX_ROUNDS):
    response = client.chat.completions.create(model=model, messages=messages, tools=tools, temperature=0.1)
    total_tokens += _usage_total(getattr(response, "usage", None))
    message = response.choices[0].message
    if not message.tool_calls:
      final_content = message.content or "Modellen returnerte ikke noe svar."
      break
    messages.append({"role": "assistant", "content": message.content or "", "tool_calls": [{"id": call.id, "type": "function", "function": {"name": call.function.name, "arguments": call.function.arguments}} for call in message.tool_calls]})
    for call in message.tool_calls:
      result = call_tool(call.function.name, call.function.arguments)
      tool_log.append({"navn": call.function.name, "argumenter": call.function.arguments, "resultat": result})
      messages.append({"role": "tool", "tool_call_id": call.id, "content": json.dumps(result, ensure_ascii=False)})
  else:
    raise RuntimeError(f"Modellen brukte mer enn {MAX_ROUNDS} tool-runder uten å avslutte.")
  if not final_content:
    raise RuntimeError("Modellen avsluttet uten et tekstsvar.")
  result = _normalise_result(final_content)
  result.update({"tokens_brukt": total_tokens, "estimert_kostnad": _cost(total_tokens), "verktoy_brukt": tool_log})
  return result
