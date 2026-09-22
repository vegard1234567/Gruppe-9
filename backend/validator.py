"""Numerisk kontroll av løsninger ved substitusjon i originalproblemet."""

import re

import sympy as sp
from sympy.parsing.sympy_parser import implicit_multiplication_application, parse_expr, standard_transformations


TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)
POINTS = (0.37, 1.11, 2.03)


def _parse(value: str, x, y):
  return parse_expr(value.replace("^", "**"), local_dict={"x": x, "y": y, "exp": sp.exp}, transformations=TRANSFORMATIONS)


def validate(problem: str, losning: str) -> dict:
  """Sjekker en ODE-løsning i tre faste numeriske punkter.

  Andre oppgavetyper får validert=False, siden tekstlig svar ikke kan
  kobles sikkert til en maskinlesbar originaloppgave her.
  """
  try:
    x = sp.Symbol("x")
    y = sp.Function("y")
    solution_match = re.search(r"(?:y\(x\)|y)\s*=\s*(.+)", losning, re.IGNORECASE)
    if not solution_match or not re.search(r"(?:y\(x\)|y).*diff|y['′]|Eq\(", problem):
      return {"validert": False, "detaljer": "Ikke numerisk validert: oppgaven eller svaret er ikke en støttet, maskinlesbar differensialligning."}

    solution = _parse(solution_match.group(1).strip(), x, y)
    original = problem.strip()
    if original.startswith("Eq("):
      equation = sp.sympify(original, locals={"x": x, "y": y, "Eq": sp.Eq})
      residual = equation.lhs - equation.rhs
    else:
      residual = _parse(original, x, y)
    substitutions = {y(x): solution}
    for derivative in residual.atoms(sp.Derivative):
      substitutions[derivative] = sp.diff(solution, x, derivative.derivative_count)
    checked = []
    for point in POINTS:
      value = complex(sp.N(residual.subs(substitutions).subs(x, point)))
      if abs(value) > 1e-7:
        return {"validert": False, "detaljer": f"Validering feilet ved x={point}: restleddet var {value}."}
      checked.append(f"x={point}")
    return {"validert": True, "detaljer": "SymPy satte løsningen inn i ligningen og fant restledd nær 0 ved " + ", ".join(checked) + "."}
  except Exception as exc:
    return {"validert": False, "detaljer": f"Ikke numerisk validert: SymPy kunne ikke tolke oppgaven eller løsningen ({exc})."}
