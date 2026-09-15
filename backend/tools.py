"""
tools.py – SymPy-baserte verktøy for matematisk beregning.
Modellen ber om tool-kall; vi kjører utregning her og returnerer resultat + LaTeX.
"""

import sympy as sp
from sympy import symbols, diff, integrate, solve, dsolve, Matrix, I, re, im, Abs, arg, exp, simplify
from sympy import Function, Eq
import json
from typing import Any


def derive(expression_str: str, variable_str: str) -> dict:
    """
    Deriverer et uttrykk med hensyn på en variabel.
    
    Args:
        expression_str: Matematisk uttrykk som string (f.eks. "x**2 + 3*x")
        variable_str: Variabel å derivere med hensyn på (f.eks. "x")
    
    Returns:
        dict med 'result' (LaTeX), 'result_raw' (som string) og 'success'
    """
    try:
        x = symbols(variable_str)
        expr = sp.sympify(expression_str)
        derivative = diff(expr, x)
        result_latex = sp.latex(derivative)
        result_raw = str(derivative)
        return {
            "success": True,
            "result": result_latex,
            "result_raw": result_raw,
            "operation": "derive"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": "derive"
        }


def integrate(expression_str: str, variable_str: str) -> dict:
    """
    Integrerer et uttrykk med hensyn på en variabel (ubestemt integral).
    
    Args:
        expression_str: Matematisk uttrykk som string
        variable_str: Variabel å integrere med hensyn på
    
    Returns:
        dict med resultat og LaTeX
    """
    try:
        x = symbols(variable_str)
        expr = sp.sympify(expression_str)
        integral = integrate(expr, x)
        result_latex = sp.latex(integral) + " + C"
        result_raw = str(integral) + " + C"
        return {
            "success": True,
            "result": result_latex,
            "result_raw": result_raw,
            "operation": "integrate"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": "integrate"
        }


def solve_equation(equation_str: str, variable_str: str) -> dict:
    """
    Løser en ligning for en gitt variabel.
    
    Args:
        equation_str: Ligning som string (f.eks. "x**2 - 4 = 0" eller bare "x**2 - 4")
        variable_str: Variabel å løse for
    
    Returns:
        dict med løsninger
    """
    try:
        x = symbols(variable_str)
        
        # Parse ligning – hvis ikke '=', antar vi = 0
        if '=' in equation_str:
            left, right = equation_str.split('=')
            eq = sp.Eq(sp.sympify(left), sp.sympify(right))
        else:
            eq = sp.Eq(sp.sympify(equation_str), 0)
        
        solutions = solve(eq, x)
        
        # Format resultat
        if not solutions:
            solutions_latex = "Ingen løsning"
            solutions_raw = "[]"
        else:
            solutions_latex = ", ".join([sp.latex(sol) for sol in solutions])
            solutions_raw = ", ".join([str(sol) for sol in solutions])
        
        return {
            "success": True,
            "result": solutions_latex,
            "result_raw": solutions_raw,
            "num_solutions": len(solutions),
            "operation": "solve_equation"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": "solve_equation"
        }


def solve_ode(equation_str: str, function_name: str = "y") -> dict:
    """
    Løser en ordinær differentialligning (ODE).
    
    Args:
        equation_str: ODE som string (f.eks. "y'' + 4*y = 0")
        function_name: Navn på funktionen (vanligvis "y")
    
    Returns:
        dict med løsning
    """
    try:
        x = symbols('x')
        y = Function(function_name)
        
        # Parse ODE – hvis ikke '=', antar vi = 0
        if '=' in equation_str:
            left, right = equation_str.split('=')
            ode = sp.Eq(sp.sympify(left.replace(function_name, str(y(x)))), sp.sympify(right))
        else:
            ode = sp.Eq(sp.sympify(equation_str.replace(function_name, str(y(x)))), 0)
        
        solution = dsolve(ode, y(x))
        result_latex = sp.latex(solution)
        result_raw = str(solution)
        
        return {
            "success": True,
            "result": result_latex,
            "result_raw": result_raw,
            "operation": "solve_ode"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": "solve_ode"
        }


def matrix_op(operation: str, matrix_data: Any, *args) -> dict:
    """
    Utfører matriseoperasjoner.
    
    Args:
        operation: "determinant", "inverse", "eigenvalues", "solve_linear"
        matrix_data: Matrise som nested list eller string, eller første matrise
        *args: Ekstra argumenter (f.eks. høyreside for solve_linear)
    
    Returns:
        dict med resultat
    """
    try:
        # Parse matrise
        if isinstance(matrix_data, str):
            mat = Matrix(sp.sympify(matrix_data))
        else:
            mat = Matrix(matrix_data)
        
        if operation == "determinant":
            result = mat.det()
            result_latex = sp.latex(result)
            return {
                "success": True,
                "result": result_latex,
                "result_raw": str(result),
                "operation": "matrix_determinant"
            }
        
        elif operation == "inverse":
            result = mat.inv()
            result_latex = sp.latex(result)
            return {
                "success": True,
                "result": result_latex,
                "result_raw": str(result),
                "operation": "matrix_inverse"
            }
        
        elif operation == "eigenvalues":
            eigenvals = mat.eigenvals()
            result_latex = ", ".join([f"{sp.latex(k)}: {v}" for k, v in eigenvals.items()])
            return {
                "success": True,
                "result": result_latex,
                "result_raw": str(eigenvals),
                "operation": "matrix_eigenvalues"
            }
        
        elif operation == "solve_linear":
            # Args[0] skal være høyreside (b i Ax=b)
            if not args:
                return {"success": False, "error": "solve_linear krever høyreside", "operation": "matrix_solve_linear"}
            
            b_data = args[0]
            if isinstance(b_data, str):
                b = Matrix(sp.sympify(b_data))
            else:
                b = Matrix(b_data)
            
            solution = mat.solve(b)
            result_latex = sp.latex(solution)
            return {
                "success": True,
                "result": result_latex,
                "result_raw": str(solution),
                "operation": "matrix_solve_linear"
            }
        
        else:
            return {"success": False, "error": f"Ukjent operasjon: {operation}", "operation": "matrix_op"}
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": "matrix_op"
        }


def complex_op(operation: str, number_str: str) -> dict:
    """
    Utfører operasjoner på komplekse tall.
    
    Args:
        operation: "polar", "power", "root", "euler"
        number_str: Komplekst tall som string (f.eks. "3+4*I")
    
    Returns:
        dict med resultat
    """
    try:
        z = sp.sympify(number_str)
        
        if operation == "polar":
            magnitude = Abs(z)
            angle = arg(z)
            result_latex = f"|z| = {sp.latex(magnitude)}, \\arg(z) = {sp.latex(angle)}"
            return {
                "success": True,
                "result": result_latex,
                "result_raw": f"|z|={magnitude}, arg(z)={angle}",
                "operation": "complex_polar"
            }
        
        elif operation == "power":
            # Antar z^2 som standard
            result = z**2
            result_latex = sp.latex(result)
            return {
                "success": True,
                "result": result_latex,
                "result_raw": str(result),
                "operation": "complex_power"
            }
        
        elif operation == "root":
            # Kvadratrot
            result = sp.sqrt(z)
            result_latex = sp.latex(result)
            return {
                "success": True,
                "result": result_latex,
                "result_raw": str(result),
                "operation": "complex_root"
            }
        
        elif operation == "euler":
            # Konverter til polarform og bruk Eulers formel
            magnitude = Abs(z)
            angle = arg(z)
            result = f"{sp.latex(magnitude)} e^{{i {sp.latex(angle)}}}"
            return {
                "success": True,
                "result": result,
                "result_raw": f"{magnitude} * exp(i*{angle})",
                "operation": "complex_euler"
            }
        
        else:
            return {"success": False, "error": f"Ukjent operasjon: {operation}", "operation": "complex_op"}
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "operation": "complex_op"
        }


# Tool-definisjoner for function calling
TOOL_DEFINITIONS = [
    {
        "name": "derive",
        "description": "Deriverer et matematisk uttrykk med hensyn på en variabel",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Matematisk uttrykk (f.eks. 'x**2 + 3*x')"
                },
                "variable": {
                    "type": "string",
                    "description": "Variabel å derivere med hensyn på (f.eks. 'x')"
                }
            },
            "required": ["expression", "variable"]
        }
    },
    {
        "name": "integrate",
        "description": "Integrerer et matematisk uttrykk (ubestemt integral)",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Matematisk uttrykk"
                },
                "variable": {
                    "type": "string",
                    "description": "Variabel å integrere med hensyn på"
                }
            },
            "required": ["expression", "variable"]
        }
    },
    {
        "name": "solve_equation",
        "description": "Løser en algebraisk ligning for en variabel",
        "parameters": {
            "type": "object",
            "properties": {
                "equation": {
                    "type": "string",
                    "description": "Ligning (f.eks. 'x**2 - 4 = 0' eller bare 'x**2 - 4')"
                },
                "variable": {
                    "type": "string",
                    "description": "Variabel å løse for"
                }
            },
            "required": ["equation", "variable"]
        }
    },
    {
        "name": "solve_ode",
        "description": "Løser en ordinær differentialligning (ODE)",
        "parameters": {
            "type": "object",
            "properties": {
                "equation": {
                    "type": "string",
                    "description": "ODE (f.eks. 'y'' + 4*y = 0')"
                },
                "function": {
                    "type": "string",
                    "description": "Navn på funksjonen (vanligvis 'y')"
                }
            },
            "required": ["equation"]
        }
    },
    {
        "name": "matrix_op",
        "description": "Utfører matriseoperasjoner",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["determinant", "inverse", "eigenvalues", "solve_linear"],
                    "description": "Matriseoperasjon"
                },
                "matrix": {
                    "description": "Matrise som nested list eller string"
                },
                "right_side": {
                    "description": "Høyreside (for solve_linear)"
                }
            },
            "required": ["operation", "matrix"]
        }
    },
    {
        "name": "complex_op",
        "description": "Utfører operasjoner på komplekse tall",
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["polar", "power", "root", "euler"],
                    "description": "Kompleks operasjon"
                },
                "number": {
                    "type": "string",
                    "description": "Komplekst tall (f.eks. '3+4*I')"
                }
            },
            "required": ["operation", "number"]
        }
    }
]


def call_tool(tool_name: str, **kwargs) -> dict:
    """
    Wrapper for å kalle verktøy fra llm_client.
    """
    if tool_name == "derive":
        return derive(kwargs.get("expression", ""), kwargs.get("variable", ""))
    elif tool_name == "integrate":
        return integrate(kwargs.get("expression", ""), kwargs.get("variable", ""))
    elif tool_name == "solve_equation":
        return solve_equation(kwargs.get("equation", ""), kwargs.get("variable", ""))
    elif tool_name == "solve_ode":
        return solve_ode(kwargs.get("equation", ""), kwargs.get("function", "y"))
    elif tool_name == "matrix_op":
        right_side = kwargs.get("right_side")
        if right_side:
            return matrix_op(kwargs.get("operation", ""), kwargs.get("matrix", []), right_side)
        else:
            return matrix_op(kwargs.get("operation", ""), kwargs.get("matrix", []))
    elif tool_name == "complex_op":
        return complex_op(kwargs.get("operation", ""), kwargs.get("number", ""))
    else:
        return {"success": False, "error": f"Ukjent verktøy: {tool_name}"}
