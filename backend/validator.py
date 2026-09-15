"""Validering av matematiske svar."""

import sympy as sp


def _locals():
    x = sp.symbols("x")
    y = sp.Function("y")
    return {"x": x, "y": y, "Eq": sp.Eq, "Derivative": sp.Derivative, "exp": sp.exp}


def _parse_solution(solution: str, locals_map: dict):
    """Parser både vanlige uttrykk og løsninger skrevet som lhs = rhs."""
    if "=" in solution and "==" not in solution:
        left, right = solution.split("=", 1)
        return sp.Eq(
            sp.sympify(left.strip(), locals=locals_map),
            sp.sympify(right.strip(), locals=locals_map),
        )
    return sp.sympify(solution, locals=locals_map)


def validate(equation: str, solution: str) -> dict:
    """Validerer et uttrykk, en ligning eller en enkel ODE mot en løsning."""
    try:
        locals_map = _locals()
        expr = sp.sympify(equation, locals=locals_map)
        proposed = _parse_solution(solution, locals_map)

        if isinstance(expr, sp.Equality):
            if isinstance(proposed, sp.Equality):
                # En eksplisitt løsning, f.eks. y(x) = C1*exp(x).
                left = expr.lhs.subs(proposed.lhs, proposed.rhs)
                right = expr.rhs.subs(proposed.lhs, proposed.rhs)
                valid = sp.simplify(left - right) == 0
            else:
                valid = (
                    sp.simplify(expr.lhs - proposed) == 0
                    or sp.simplify(expr.rhs - proposed) == 0
                )
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
