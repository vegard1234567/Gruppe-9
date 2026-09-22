"""Deterministiske matteverktøy som kan kalles av språkmodellen."""

import json
import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)


TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)
LOCAL_DICT = {
    name: getattr(sp, name)
    for name in ("E", "I", "pi", "sin", "cos", "tan", "exp", "log", "sqrt")
}


def _expression(value: str):
    """Parser et begrenset SymPy-uttrykk, uten å evaluere Python-kode."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Uttrykket kan ikke være tomt.")
    if "__" in value or re.search(r"\b(import|exec|eval|open)\b", value):
        raise ValueError("Uttrykket inneholder ikke tillatte konstruksjoner.")
    return parse_expr(value.replace("^", "**"), local_dict=LOCAL_DICT, transformations=TRANSFORMATIONS)


def _success(value):
    return {"resultat": str(value), "latex": sp.latex(value)}


def derive(uttrykk: str, variabel: str = "x") -> dict:
    """Deriverer et uttrykk symbolsk med SymPy."""
    expression = _expression(uttrykk)
    variable = sp.Symbol(variabel)
    return _success(sp.simplify(sp.diff(expression, variable)))


def integrate(uttrykk: str, variabel: str = "x") -> dict:
    """Beregner et ubestemt integral symbolsk med SymPy."""
    expression = _expression(uttrykk)
    variable = sp.Symbol(variabel)
    return _success(sp.integrate(expression, variable))


def solve_equation(ligning: str, variabel: str = "x") -> dict:
    """Løser en ligning eller et uttrykk lik null med SymPy."""
    variable = sp.Symbol(variabel)
    if "=" in ligning:
        left, right = ligning.split("=", 1)
        equation = _expression(left) - _expression(right)
    else:
        equation = _expression(ligning)
    return _success(sp.solve(equation, variable))


def solve_ode(ligning: str) -> dict:
    """Løser en vanlig differensialligning med SymPy dsolve."""
    x = sp.Symbol("x")
    y = sp.Function("y")
    expression = parse_expr(
        ligning.replace("^", "**"),
        local_dict={**LOCAL_DICT, "x": x, "y": y},
        transformations=TRANSFORMATIONS,
    )
    return _success(sp.dsolve(sp.Eq(expression, 0)))


def matrix_op(operasjon: str, matrise: list) -> dict:
    """Utfører en deterministisk matriseoperasjon med SymPy."""
    matrix = sp.Matrix(matrise)
    operation = operasjon.lower().strip()
    if operation in {"det", "determinant"}:
        value = matrix.det()
    elif operation in {"invers", "inverse"}:
        value = matrix.inv()
    elif operation in {"egenverdier", "eigenvalues"}:
        value = matrix.eigenvals()
    elif operation in {"løs ax=b", "los ax=b", "solve", "solve_ax_b"}:
        if matrix.cols != matrix.rows + 1:
            raise ValueError("For 'løs Ax=b' må matriseargumentet være [A|b].")
        value = matrix[:, :-1].gauss_jordan_solve(matrix[:, -1])[0]
    else:
        raise ValueError(f"Ukjent matriseoperasjon: {operasjon}")
    return _success(value)


def complex_op(operasjon: str, tall: str) -> dict:
    """Utfører polarform, potens eller røtter for et komplekst tall."""
    value = _expression(tall.replace("j", "*I"))
    operation = operasjon.lower().strip()
    if operation in {"polar", "polarform"}:
        result = (sp.Abs(value), sp.arg(value))
    elif operation in {"euler", "eulers formel", "eulers_formel"}:
        result = sp.expand_complex(value)
    elif operation.startswith("potens:"):
        result = sp.simplify(value ** _expression(operation.split(":", 1)[1]))
    elif operation.startswith("rot:") or operation.startswith("røtter:"):
        degree = int(operation.split(":", 1)[1])
        if degree <= 0:
            raise ValueError("Rotgraden må være positiv.")
        result = [sp.root(value, degree, k) for k in range(degree)]
    else:
        raise ValueError(f"Ukjent kompleks operasjon: {operasjon}")
    return _success(result)


TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "derive", "description": "Deriver et uttrykk med SymPy.", "parameters": {"type": "object", "properties": {"uttrykk": {"type": "string"}, "variabel": {"type": "string", "default": "x"}}, "required": ["uttrykk"]}}},
    {"type": "function", "function": {"name": "integrate", "description": "Integrer et uttrykk med SymPy.", "parameters": {"type": "object", "properties": {"uttrykk": {"type": "string"}, "variabel": {"type": "string", "default": "x"}}, "required": ["uttrykk"]}}},
    {"type": "function", "function": {"name": "solve_equation", "description": "Løs en ligning med SymPy.", "parameters": {"type": "object", "properties": {"ligning": {"type": "string"}, "variabel": {"type": "string", "default": "x"}}, "required": ["ligning"]}}},
    {"type": "function", "function": {"name": "solve_ode", "description": "Løs en differensialligning med SymPy.", "parameters": {"type": "object", "properties": {"ligning": {"type": "string"}}, "required": ["ligning"]}}},
    {"type": "function", "function": {"name": "matrix_op", "description": "Utfør determinant, invers, egenverdier eller løs Ax=b.", "parameters": {"type": "object", "properties": {"operasjon": {"type": "string"}, "matrise": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}}}, "required": ["operasjon", "matrise"]}}},
    {"type": "function", "function": {"name": "complex_op", "description": "Regn med komplekse tall.", "parameters": {"type": "object", "properties": {"operasjon": {"type": "string"}, "tall": {"type": "string"}}, "required": ["operasjon", "tall"]}}},
]


def call_tool(name: str, arguments: str | dict) -> dict:
    """Kaller kun en av funksjonene som er eksponert til modellen."""
    functions = {"derive": derive, "integrate": integrate, "solve_equation": solve_equation,
                 "solve_ode": solve_ode, "matrix_op": matrix_op, "complex_op": complex_op}
    if name not in functions:
        raise ValueError(f"Ukjent verktøy: {name}")
    parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
    if not isinstance(parsed, dict):
        raise ValueError("Tool-argumentene må være et JSON-objekt.")
    try:
        return functions[name](**parsed)
    except (TypeError, ValueError, SyntaxError, sp.SympifyError) as exc:
        return {"feil": str(exc), "resultat": "Beregningen kunne ikke utføres.", "latex": ""}
