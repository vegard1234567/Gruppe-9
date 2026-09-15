"""
validator.py – Numerisk validering av løsninger.
Setter løsningen inn i originalproblemet og sjekker om den passer.
"""

import sympy as sp
import random
from typing import Any


def validate_equation_solution(equation_str: str, variable_str: str, solution_str: str) -> dict:
    """
    Validerer om en løsning faktisk løser en ligning.
    
    Args:
        equation_str: Original ligning (f.eks. "x**2 - 4 = 0")
        variable_str: Variabelen som ble løst for
        solution_str: Foreslått løsning
    
    Returns:
        dict med validering resultat
    """
    try:
        x = sp.symbols(variable_str)
        
        # Parse ligning
        if '=' in equation_str:
            left, right = equation_str.split('=')
            equation = sp.Eq(sp.sympify(left), sp.sympify(right))
        else:
            equation = sp.Eq(sp.sympify(equation_str), 0)
        
        # Parse løsning – kan være kommaseparert
        if isinstance(solution_str, str) and ',' in solution_str:
            solutions = [sp.sympify(s.strip()) for s in solution_str.split(',')]
        else:
            solutions = [sp.sympify(solution_str)]
        
        # Sjekk hver løsning
        all_valid = True
        details = []
        
        for sol in solutions:
            try:
                # Substituer løsning inn i ligning og evaluer
                left_val = equation.lhs.subs(x, sol).evalf()
                right_val = equation.rhs.subs(x, sol).evalf()
                
                # Sammenlign (med liten toleranse for numeriske feil)
                diff = abs(float(left_val - right_val))
                is_valid = diff < 1e-6
                
                if not is_valid:
                    all_valid = False
                
                details.append({
                    "solution": str(sol),
                    "left_value": float(left_val),
                    "right_value": float(right_val),
                    "difference": diff,
                    "valid": is_valid
                })
            except Exception as e:
                all_valid = False
                details.append({
                    "solution": str(sol),
                    "error": str(e),
                    "valid": False
                })
        
        return {
            "validated": all_valid,
            "type": "equation",
            "details": details
        }
    
    except Exception as e:
        return {
            "validated": False,
            "type": "equation",
            "error": str(e)
        }


def validate_derivative(original_expr_str: str, derivative_str: str, variable_str: str) -> dict:
    """
    Validerer om en foreslått derivert er korrekt.
    
    Args:
        original_expr_str: Original uttrykk
        derivative_str: Foreslått derivert
        variable_str: Variabel
    
    Returns:
        dict med validering
    """
    try:
        x = sp.symbols(variable_str)
        original = sp.sympify(original_expr_str)
        proposed_derivative = sp.sympify(derivative_str)
        actual_derivative = sp.diff(original, x)
        
        # Simplify begge og sammenlign
        proposed_simplified = sp.simplify(proposed_derivative)
        actual_simplified = sp.simplify(actual_derivative)
        
        is_equal = sp.simplify(proposed_simplified - actual_simplified) == 0
        
        # Test numerisk på 3 tilfeldige punkter
        test_points = [random.uniform(-10, 10) for _ in range(3)]
        numeric_valid = True
        numeric_details = []
        
        for point in test_points:
            try:
                proposed_val = float(proposed_simplified.subs(x, point).evalf())
                actual_val = float(actual_simplified.subs(x, point).evalf())
                diff = abs(proposed_val - actual_val)
                numeric_valid = numeric_valid and (diff < 1e-5)
                numeric_details.append({
                    "point": point,
                    "proposed": proposed_val,
                    "actual": actual_val,
                    "difference": diff
                })
            except:
                numeric_valid = False
        
        return {
            "validated": is_equal and numeric_valid,
            "type": "derivative",
            "symbolic_match": is_equal,
            "numeric_details": numeric_details
        }
    
    except Exception as e:
        return {
            "validated": False,
            "type": "derivative",
            "error": str(e)
        }


def validate_integral(original_expr_str: str, integral_str: str, variable_str: str) -> dict:
    """
    Validerer om en foreslått integral er korrekt ved å derivere den igjen.
    
    Args:
        original_expr_str: Opprinnelig integrand
        integral_str: Foreslått integral (uten + C)
        variable_str: Variabel
    
    Returns:
        dict med validering
    """
    try:
        x = sp.symbols(variable_str)
        original = sp.sympify(original_expr_str)
        proposed_integral = sp.sympify(integral_str)
        
        # Derivér integralet – skal gi tilbake originen
        derivative_of_integral = sp.diff(proposed_integral, x)
        
        # Simplify og sammenlign
        derivative_simplified = sp.simplify(derivative_of_integral)
        original_simplified = sp.simplify(original)
        
        is_equal = sp.simplify(derivative_simplified - original_simplified) == 0
        
        # Numerisk test
        test_points = [random.uniform(-10, 10) for _ in range(3)]
        numeric_valid = True
        numeric_details = []
        
        for point in test_points:
            try:
                deriv_val = float(derivative_simplified.subs(x, point).evalf())
                orig_val = float(original_simplified.subs(x, point).evalf())
                diff = abs(deriv_val - orig_val)
                numeric_valid = numeric_valid and (diff < 1e-5)
                numeric_details.append({
                    "point": point,
                    "derivative": deriv_val,
                    "original": orig_val,
                    "difference": diff
                })
            except:
                numeric_valid = False
        
        return {
            "validated": is_equal and numeric_valid,
            "type": "integral",
            "symbolic_match": is_equal,
            "numeric_details": numeric_details
        }
    
    except Exception as e:
        return {
            "validated": False,
            "type": "integral",
            "error": str(e)
        }


def validate_general(solution_description: str) -> dict:
    """
    Generisk validering når løsningen ikke er numerisk testbar
    (f.eks. bevis eller begrepsforklaring).
    
    Args:
        solution_description: Beskrivelse fra modellen
    
    Returns:
        dict som indikerer at validering ikke var mulig
    """
    return {
        "validated": False,
        "type": "general",
        "message": "Denne løsningen kan ikke valideres numerisk. Det kan være et bevis, en begrepsforklaring, eller en oppgave som ikke har en direkte numerisk løsning.",
        "human_review_needed": True
    }


def validate_solution(problem_type: str, **kwargs) -> dict:
    """
    Wrapper-funksjon for å validere løsninger basert på problemtype.
    
    Args:
        problem_type: "equation", "derivative", "integral", "general", etc.
        **kwargs: Argumenter som avhenger av problemtype
    
    Returns:
        dict med valideringsresultat
    """
    if problem_type == "equation":
        return validate_equation_solution(
            kwargs.get("equation", ""),
            kwargs.get("variable", "x"),
            kwargs.get("solution", "")
        )
    elif problem_type == "derivative":
        return validate_derivative(
            kwargs.get("expression", ""),
            kwargs.get("derivative", ""),
            kwargs.get("variable", "x")
        )
    elif problem_type == "integral":
        return validate_integral(
            kwargs.get("expression", ""),
            kwargs.get("integral", ""),
            kwargs.get("variable", "x")
        )
    else:
        return validate_general(kwargs.get("description", ""))
