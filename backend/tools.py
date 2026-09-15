"""SymPy-baserte verktøy for matematisk beregning."""
import sympy as sp
from sympy import Matrix, Function
from typing import Any


def _ok(result: Any, operation: str) -> dict:
    return {"resultat": str(result), "latex": sp.latex(result), "success": True, "result": sp.latex(result), "result_raw": str(result), "operation": operation}


def _error(error: Exception, operation: str) -> dict:
    return {"resultat": f"Feil: {error}", "latex": "", "success": False, "error": str(error), "operation": operation}


def derive(expression_str: str, variable_str: str) -> dict:
    try:
        x = sp.symbols(variable_str)
        return _ok(sp.diff(sp.sympify(expression_str), x), "derive")
    except Exception as e: return _error(e, "derive")


def integrate(expression_str: str, variable_str: str) -> dict:
    try:
        x = sp.symbols(variable_str); result = sp.integrate(sp.sympify(expression_str), x)
        return {"resultat": f"{result} + C", "latex": sp.latex(result) + " + C", "success": True, "result": sp.latex(result) + " + C", "result_raw": f"{result} + C", "operation": "integrate"}
    except Exception as e: return _error(e, "integrate")


def solve_equation(equation_str: str, variable_str: str) -> dict:
    try:
        x = sp.symbols(variable_str)
        if "=" in equation_str:
            left, right = equation_str.split("=", 1); eq = sp.Eq(sp.sympify(left), sp.sympify(right))
        else: eq = sp.Eq(sp.sympify(equation_str), 0)
        solutions = sp.solve(eq, x)
        latex = ", ".join(sp.latex(s) for s in solutions) if solutions else "Ingen løsning"
        return {"resultat": str(solutions), "latex": latex, "success": True, "result": latex, "result_raw": str(solutions), "num_solutions": len(solutions), "operation": "solve_equation"}
    except Exception as e: return _error(e, "solve_equation")


def solve_ode(equation_str: str, function_name: str = "y") -> dict:
    try:
        x = sp.symbols("x"); y = Function(function_name)
        expr = equation_str.replace(f"{function_name}(x)", "y(x)")
        if "=" in expr:
            left, right = expr.split("=", 1); ode = sp.Eq(sp.sympify(left, locals={"y": y, "x": x}), sp.sympify(right, locals={"y": y, "x": x}))
        else: ode = sp.Eq(sp.sympify(expr, locals={"y": y, "x": x}), 0)
        return _ok(sp.dsolve(ode, y(x)), "solve_ode")
    except Exception as e: return _error(e, "solve_ode")


def matrix_op(operation: str, matrix_data: Any, *args) -> dict:
    try:
        mat = Matrix(sp.sympify(matrix_data)) if isinstance(matrix_data, str) else Matrix(matrix_data)
        if operation == "determinant": result = mat.det()
        elif operation == "inverse": result = mat.inv()
        elif operation == "eigenvalues": result = mat.eigenvals()
        elif operation == "solve_linear":
            if not args: raise ValueError("solve_linear krever høyreside")
            b = Matrix(sp.sympify(args[0])) if isinstance(args[0], str) else Matrix(args[0]); result = mat.solve(b)
        else: raise ValueError(f"Ukjent operasjon: {operation}")
        return _ok(result, f"matrix_{operation}")
    except Exception as e: return _error(e, "matrix_op")


def complex_op(operation: str, number_str: str) -> dict:
    try:
        z = sp.sympify(number_str, locals={"I": sp.I})
        if operation == "polar":
            r = f"|z| = {sp.latex(sp.Abs(z))}, arg(z) = {sp.latex(sp.arg(z))}"
            return {"resultat": r, "latex": r, "success": True, "result": r, "result_raw": r, "operation": "complex_polar"}
        if operation == "power": return _ok(sp.simplify(z**2), "complex_power")
        if operation == "root": return _ok(sp.sqrt(z), "complex_root")
        if operation == "euler":
            r = f"{sp.latex(sp.Abs(z))} e^{{i {sp.latex(sp.arg(z))}}}"
            return {"resultat": r, "latex": r, "success": True, "result": r, "result_raw": r, "operation": "complex_euler"}
        raise ValueError(f"Ukjent operasjon: {operation}")
    except Exception as e: return _error(e, "complex_op")


TOOL_DEFINITIONS = [
 {"name":"derive","description":"Deriverer et matematisk uttrykk","parameters":{"type":"object","properties":{"expression":{"type":"string"},"variable":{"type":"string"}},"required":["expression","variable"]}},
 {"name":"integrate","description":"Integrerer et matematisk uttrykk","parameters":{"type":"object","properties":{"expression":{"type":"string"},"variable":{"type":"string"}},"required":["expression","variable"]}},
 {"name":"solve_equation","description":"Løser en ligning","parameters":{"type":"object","properties":{"equation":{"type":"string"},"variable":{"type":"string"}},"required":["equation","variable"]}},
 {"name":"solve_ode","description":"Løser en ODE","parameters":{"type":"object","properties":{"equation":{"type":"string"},"function":{"type":"string"}},"required":["equation"]}},
 {"name":"matrix_op","description":"Utfører matriseoperasjoner","parameters":{"type":"object","properties":{"operation":{"type":"string","enum":["determinant","inverse","eigenvalues","solve_linear"]},"matrix":{},"right_side":{}},"required":["operation","matrix"]}},
 {"name":"complex_op","description":"Utfører operasjoner på komplekse tall","parameters":{"type":"object","properties":{"operation":{"type":"string","enum":["polar","power","root","euler"]},"number":{"type":"string"}},"required":["operation","number"]}},
]


def call_tool(tool_name: str, **kwargs) -> dict:
    if tool_name == "derive": return derive(kwargs.get("expression", ""), kwargs.get("variable", ""))
    if tool_name == "integrate": return integrate(kwargs.get("expression", ""), kwargs.get("variable", ""))
    if tool_name == "solve_equation": return solve_equation(kwargs.get("equation", ""), kwargs.get("variable", ""))
    if tool_name == "solve_ode": return solve_ode(kwargs.get("equation", ""), kwargs.get("function", "y"))
    if tool_name == "matrix_op":
        return matrix_op(kwargs.get("operation", ""), kwargs.get("matrix", []), kwargs["right_side"]) if "right_side" in kwargs else matrix_op(kwargs.get("operation", ""), kwargs.get("matrix", []))
    if tool_name == "complex_op": return complex_op(kwargs.get("operation", ""), kwargs.get("number", ""))
    return {"resultat":"", "latex":"", "success":False, "error":f"Ukjent verktøy: {tool_name}"}
