"""Validering av matematiske svar."""

import sympy as sp


def validate(equation: str, solution: str) -> dict:
    """Validerer en SymPy-ligning mot en foreslått løsning."""
    try:
        expr = sp.sympify(equation, locals={"y": sp.Function("y"), "x": sp.symbols("x")})
        proposed = sp.sympify(solution, locals={"y": sp.Function("y"), "x": sp.symbols("x")})
        if isinstance(expr, sp.Equality):
            expected = expr.rhs
            actual = proposed
            valid = sp.simplify(expected - actual) == 0
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
