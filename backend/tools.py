"""Deterministiske matteverktøy (SymPy) for MatteHjelpen.

PRINSIPP: Modellen resonnerer – verktøyet regner. En språkmodell skal ALDRI
gjøre symbolsk/numerisk regning selv.

TOLKNING AV NOTASJON (bevisst valg, jf. «aha-punkt» i OPPGAVE.md): `^` tolkes
som potens (konvertert til `**`), i tråd med standard dataverktøy/parsere.
Det betyr at `sin^-1(x)` parses som `sin(x)**(-1)` (dvs. 1/sin(x)), IKKE som
arcsin(x) – selv om noen lærebøker bruker `sin^-1` for den inverse
funksjonen. Skal du ha arcsin, skriv `asin(x)` eksplisitt. Vi endrer ikke på
dette automatisk, fordi det er nettopp denne tvetydigheten oppgaven ber oss
legge merke til: SymPy regner riktig ut fra FEIL tolket notasjon.

Feilhåndtering: alle funksjonene under kaster `ValueError` med en forklarende
norsk feilmelding ved ugyldig syntaks, udefinerte operasjoner (f.eks. deling
på null, singulær matrise, feil matrisedimensjoner) eller andre problemer –
de returnerer ALDRI en stille/feil verdi. `llm_client.py` fanger disse og
sender feilteksten tilbake til modellen som tool-resultat, slik at modellen
kan forklare problemet til brukeren i stedet for at appen krasjer.
"""

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

_TRANSFORMASJONER = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)


def _parse(uttrykk: str, lokale_symboler: dict | None = None):
    """Tolker en streng som et SymPy-uttrykk. Kaster ValueError ved ugyldig syntaks."""
    try:
        return parse_expr(uttrykk, local_dict=lokale_symboler, transformations=_TRANSFORMASJONER)
    except Exception as e:
        raise ValueError(f"Klarte ikke å tolke uttrykket {uttrykk!r}: {e}") from e


def derive(uttrykk: str, variabel: str = "x") -> dict:
    """Deriverer `uttrykk` med hensyn på `variabel`, med SymPy."""
    x = sp.Symbol(variabel)
    expr = _parse(uttrykk, {variabel: x})
    try:
        resultat = sp.diff(expr, x)
    except Exception as e:
        raise ValueError(f"Klarte ikke å derivere {uttrykk!r}: {e}") from e
    return {"resultat": str(resultat), "latex": sp.latex(resultat)}


def integrate(uttrykk: str, variabel: str = "x") -> dict:
    """Finner et antiderivert uttrykk for `uttrykk` med hensyn på `variabel`, med SymPy."""
    x = sp.Symbol(variabel)
    expr = _parse(uttrykk, {variabel: x})
    try:
        resultat = sp.integrate(expr, x)
    except Exception as e:
        raise ValueError(f"Klarte ikke å integrere {uttrykk!r}: {e}") from e
    if resultat.has(sp.Integral):
        raise ValueError(
            f"Fant ikke et lukket uttrykk for integralet av {uttrykk!r} – SymPy klarte ikke å løse det symbolsk."
        )
    return {"resultat": str(resultat), "latex": sp.latex(resultat)}


def solve_equation(ligning: str, variabel: str = "x") -> dict:
    """Løser `ligning` (f.eks. 'x**2 - 4 = 0' eller 'x**2 - 4') for `variabel`, med SymPy."""
    x = sp.Symbol(variabel)
    lokale = {variabel: x, "Eq": sp.Eq}
    try:
        if "Eq(" in ligning:
            parsed = _parse(ligning, lokale)
            eq = parsed if isinstance(parsed, sp.Eq) else sp.Eq(parsed, 0)
        elif "=" in ligning and "==" not in ligning:
            venstre, hoyre = ligning.split("=", 1)
            eq = sp.Eq(_parse(venstre, lokale), _parse(hoyre, lokale))
        else:
            eq = sp.Eq(_parse(ligning, lokale), 0)
        losninger = sp.solve(eq, x)
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Klarte ikke å løse likningen {ligning!r}: {e}") from e

    if not losninger:
        raise ValueError(
            f"Fant ingen løsning for {ligning!r} – kan ha tom løsningsmengde eller være for komplekst for SymPy."
        )
    resultat_str = ", ".join(f"{variabel} = {s}" for s in losninger)
    latex = r",\ ".join(f"{variabel} = {sp.latex(s)}" for s in losninger)
    return {"resultat": resultat_str, "latex": latex}


def _forbered_ode_streng(s: str) -> str:
    """Gjør vanlig ODE-notasjon (y'', y', bare 'y') om til eksplisitt SymPy-form."""
    s = s.replace(" ", "")
    s = s.replace("y''", "Derivative(y(x),x,2)")
    s = s.replace("y'", "Derivative(y(x),x)")
    s = re.sub(r"(?<![\w(])y(?!\()", "y(x)", s)
    return s


def solve_ode(ligning: str) -> dict:
    """Løser en differensialligning i y(x) (f.eks. "y'' + 4*y = 0"), med SymPy dsolve.

    Støtter både `y''`/`y'`-notasjon og eksplisitt `Derivative(y(x), x, ...)`.
    """
    x = sp.Symbol("x")
    y = sp.Function("y")
    lokale = {"x": x, "y": y, "Eq": sp.Eq, "Derivative": sp.Derivative}
    try:
        s = _forbered_ode_streng(ligning)
        if "Eq(" in s:
            parsed = _parse(s, lokale)
            eq = parsed if isinstance(parsed, sp.Eq) else sp.Eq(parsed, 0)
        elif "=" in s:
            venstre, hoyre = s.split("=", 1)
            eq = sp.Eq(_parse(venstre, lokale), _parse(hoyre, lokale))
        else:
            eq = sp.Eq(_parse(s, lokale), 0)
        losning = sp.dsolve(eq, y(x))
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Klarte ikke å løse differensialligningen {ligning!r}: {e}") from e
    return {"resultat": str(losning), "latex": sp.latex(losning)}


def matrix_op(operasjon: str, matrise: list) -> dict:
    """Matriseoperasjoner: determinant, invers, egenverdier, eller løs Ax=b.

    For `operasjon="los_ax_b"` skal `matrise` være den UTVIDEDE matrisen
    [A | b], dvs. siste kolonne er b (kvadratisk A i de øvrige kolonnene).
    """
    try:
        M = sp.Matrix(matrise)
    except Exception as e:
        raise ValueError(f"Klarte ikke å tolke matrisen {matrise!r}: {e}") from e

    op = operasjon.strip().lower()
    try:
        if op == "determinant":
            if M.rows != M.cols:
                raise ValueError(f"Determinant krever en kvadratisk matrise, fikk {M.rows}x{M.cols}.")
            resultat = M.det()
            resultat_str, latex = str(resultat), sp.latex(resultat)

        elif op in ("invers", "inverse"):
            if M.rows != M.cols:
                raise ValueError(f"Invers krever en kvadratisk matrise, fikk {M.rows}x{M.cols}.")
            if M.det() == 0:
                raise ValueError("Matrisen er singulær (determinant 0) og har ingen invers.")
            resultat = M.inv()
            resultat_str, latex = str(resultat), sp.latex(resultat)

        elif op in ("egenverdier", "eigenvalues"):
            if M.rows != M.cols:
                raise ValueError(f"Egenverdier krever en kvadratisk matrise, fikk {M.rows}x{M.cols}.")
            ev = M.eigenvals()
            resultat_str = ", ".join(f"{verdi} (multiplisitet {mult})" for verdi, mult in ev.items())
            latex = r",\ ".join(sp.latex(verdi) for verdi in ev.keys())

        elif op in ("los_ax_b", "løs_ax_b", "solve_ax_b"):
            if M.cols < 2:
                raise ValueError("Forventet en utvidet matrise [A | b] med minst 2 kolonner.")
            A = M[:, :-1]
            b = M[:, -1]
            if A.rows != A.cols:
                raise ValueError(f"A må være kvadratisk for denne metoden, fikk {A.rows}x{A.cols}.")
            if A.det() == 0:
                raise ValueError("A er singulær (determinant 0) – systemet har ingen entydig løsning.")
            resultat = A.solve(b)
            resultat_str, latex = str(resultat.T), sp.latex(resultat)

        else:
            raise ValueError(
                f"Ukjent matriseoperasjon: {operasjon!r}. Gyldige: determinant, invers, egenverdier, los_ax_b."
            )
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Feil under matriseoperasjon {operasjon!r}: {e}") from e

    return {"resultat": resultat_str, "latex": latex}


def _parse_komplekst(tall: str):
    """Tolker en komplekstall-streng. Aksepterer både `I` (SymPy) og `j` (Python)."""
    s = tall.replace(" ", "")
    s = re.sub(r"(?<=\d)j\b", "*I", s)
    s = re.sub(r"\bj\b", "I", s)
    return _parse(s)


def complex_op(operasjon: str, tall: str) -> dict:
    """Operasjoner på komplekse tall: polar, potens, røtter, euler.

    For `operasjon="røtter"` kan `tall` inneholde et gradstall etter et
    semikolon, f.eks. `"1+I; 3"` for de 3 kubikkrøttene av 1+i. Uten
    semikolon antas kvadratrøtter (n=2).
    """
    op = operasjon.strip().lower()
    try:
        if op in ("røtter", "rotter", "roots"):
            if ";" in tall:
                z_str, n_str = tall.split(";", 1)
                n = int(n_str.strip())
            else:
                z_str, n = tall, 2
            if n < 1:
                raise ValueError(f"Antall røtter må være et positivt heltall, fikk {n}.")
            z = _parse_komplekst(z_str)
            k = sp.symbols("k")
            roller = [sp.simplify(sp.root(z, n) * sp.exp(2 * sp.pi * sp.I * i / n)) for i in range(n)]
            resultat_str = ", ".join(str(r) for r in roller)
            latex = r",\ ".join(sp.latex(r) for r in roller)
            return {"resultat": resultat_str, "latex": latex}

        z = _parse_komplekst(tall)
        if op == "polar":
            r = sp.simplify(sp.Abs(z))
            theta = sp.simplify(sp.arg(z))
            resultat_str = f"r = {r}, theta = {theta} rad"
            latex = rf"{sp.latex(r)}\left(\cos({sp.latex(theta)}) + i\sin({sp.latex(theta)})\right)"
        elif op in ("potens", "power", "forenkle"):
            resultat = sp.expand(z, complex=True)
            resultat_str, latex = str(resultat), sp.latex(resultat)
        elif op in ("euler", "eksponentialform"):
            r = sp.simplify(sp.Abs(z))
            theta = sp.simplify(sp.arg(z))
            resultat_str = f"{r}*exp(I*{theta})"
            latex = rf"{sp.latex(r)}\,e^{{i {sp.latex(theta)}}}"
        else:
            raise ValueError(
                f"Ukjent operasjon for komplekse tall: {operasjon!r}. Gyldige: polar, potens, røtter, euler."
            )
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Feil under komplekstallsoperasjon {operasjon!r} på {tall!r}: {e}") from e

    return {"resultat": resultat_str, "latex": latex}


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "derive",
            "description": (
                "Deriverer et matematisk uttrykk med hensyn på én variabel. `^` tolkes som potens "
                "(sin^-1(x) blir altså 1/sin(x), IKKE arcsin – bruk asin(x) for arcsin)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "uttrykk": {
                        "type": "string",
                        "description": "Uttrykket som skal deriveres, f.eks. 'x**2*sin(x)'.",
                    },
                    "variabel": {
                        "type": "string",
                        "description": "Variabelen det deriveres med hensyn på.",
                        "default": "x",
                    },
                },
                "required": ["uttrykk"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "integrate",
            "description": "Finner et antiderivert (ubestemt integral) av et uttrykk med hensyn på én variabel.",
            "parameters": {
                "type": "object",
                "properties": {
                    "uttrykk": {
                        "type": "string",
                        "description": "Uttrykket (integranden) som skal integreres, f.eks. 'x*exp(x)'.",
                    },
                    "variabel": {
                        "type": "string",
                        "description": "Integrasjonsvariabelen.",
                        "default": "x",
                    },
                },
                "required": ["uttrykk"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solve_equation",
            "description": "Løser en algebraisk likning for én ukjent variabel, f.eks. 'x**2 - 4 = 0'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ligning": {
                        "type": "string",
                        "description": "Likningen, f.eks. 'x**2 - 4 = 0' eller bare 'x**2 - 4' (antas = 0).",
                    },
                    "variabel": {
                        "type": "string",
                        "description": "Den ukjente variabelen som skal løses for.",
                        "default": "x",
                    },
                },
                "required": ["ligning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "solve_ode",
            "description": (
                "Løser en differensialligning for y(x), f.eks. \"y'' + 4*y = 0\" eller "
                "\"Eq(Derivative(y(x), x), y(x))\". Returnerer den generelle løsningen (med C1, C2 ...)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "ligning": {
                        "type": "string",
                        "description": "Differensialligningen i y(x), med y', y'' eller Derivative(...)-notasjon.",
                    },
                },
                "required": ["ligning"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "matrix_op",
            "description": (
                "Matriseoperasjoner: determinant, invers, egenverdier eller løsning av Ax=b. "
                "For 'los_ax_b' sender du inn DEN UTVIDEDE matrisen [A | b] (b som siste kolonne)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operasjon": {
                        "type": "string",
                        "enum": ["determinant", "invers", "egenverdier", "los_ax_b"],
                        "description": "Hvilken matriseoperasjon som skal utføres.",
                    },
                    "matrise": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "Matrisen som liste av rader, f.eks. [[1,2],[3,4]].",
                    },
                },
                "required": ["operasjon", "matrise"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complex_op",
            "description": (
                "Operasjoner på komplekse tall: polar (polarform), potens (forenkle/utvid en potens), "
                "røtter (n-te røtter – bruk 'tall; n', f.eks. '1+I; 3'), euler (eksponentialform)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operasjon": {
                        "type": "string",
                        "enum": ["polar", "potens", "røtter", "euler"],
                        "description": "Hvilken operasjon som skal utføres.",
                    },
                    "tall": {
                        "type": "string",
                        "description": "Det komplekse tallet/uttrykket, f.eks. '1+I' eller '(1+I)**4'.",
                    },
                },
                "required": ["operasjon", "tall"],
            },
        },
    },
]
