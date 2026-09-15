"""Validering av matematiske svar."""

import sympy as sp


def _locals():
    x = sp.symbols("x")
    y = sp.Function("y")
    return {"x": x, "y": y, "Eq": sp.Eq, "Derivative": sp.Derivative, "exp": sp.exp}


def validate(equation: str, solution: str) -> dict:
    """Validerer et uttrykk, en ligning eller en enkel ODE mot en løsning."""
    try:
        locals_map = _locals()
        expr = sp.sympify(equation, locals=locals_map)
        proposed = sp.sympify(solution, locals=locals_map)

        # ODE/ligning: hvis løsningen er skrevet som y(x) = ..., sett den inn
        # i venstre og høyre side av originalen og sjekk at ligningen stemmer.
        if isinstance(expr, sp.Equality):
            if isinstance(proposed, sp.Equality):
                substitutions = {proposed.lhs: proposed.rhs}
                left = expr.lhs.subs(substitutions)
                right = expr.rhs.subs(substitutions)
                valid = sp.simplify(left - right) == 0
            else:
                valid = sp.simplify(expr.lhs - proposed) == 0 or sp.simplify(expr.rhs - proposed) == 0
        elif isinstance(expr, sp.Derivative):
            valid = sp.simplify(expr - proposed) == 0
        else:
            valid = sp.simplify(expr - proposed) == 0

        return {"validert": bool(valid), "detaljer": "Symbolsk sammenligning utført."}
    except Exception as e:
        return {"validert": False, "detaljer": f"Kunne ikke validere: {e}"}


def validate_solution(problem_type: str, **kwargs) -> dict:
    if problem_type == "equation":
        return validate(kwargs.get("equation", ""), kwargs.get("solution", ""))
    return {"validert": False, "detaljer": "Ingen generell validering implementert."}
