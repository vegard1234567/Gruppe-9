"""Numerisk validering av løsninger.

HVORFOR: Etterprøvbarhet er ikke valgfritt for ingeniører. Hvis appen sier at
en løsning stemmer, skal det være fordi vi faktisk sjekket det – ved å sette
løsningen inn i det originale problemet og evaluere numerisk i flere punkter.

TOLERANSE: 1e-6. SymPy sin `evalf()` regner som standard med 15 sikre siffer,
så reelle avvik (feil fortegn, manglende ledd, feil konstant) blir mange
størrelsesordener over dette, mens avrundingsstøy fra selve flyttallregningen
ligger mange størrelsesordener under. 1e-6 er dermed strengt nok til å fange
ekte feil, men slakt nok til å tåle flyttallsunøyaktighet.

OPPGAVETYPER SOM IKKE KAN VALIDERES SLIK: bevis/begrepsoppgaver (f.eks.
«bevis Pythagoras' læresetning»), åpne/ubestemte integraler uten lukket
uttrykk, og svar som ikke lar seg tolke som SymPy-uttrykk i det hele tatt
(fri tekst). For disse returnerer `validate` ÆRLIG `validert=False` med en
forklaring i `detaljer` – aldri `True` fordi det "ser bra ut".

`operasjon` lar kalleren (llm_client) fortelle validatoren nøyaktig hvilken
sjekk som er relevant ("derive", "integrate", "solve_equation", "solve_ode").
Standardverdien "auto" prøver å gjenkjenne oppgavetypen selv, og brukes bl.a.
av selvtesten og som fallback for oppgavetyper vi ikke kjenner igjen (f.eks.
matrise-/komplekstalloppgaver, eller bevisoppgaver) – da forsøker den et par
generelle tolkninger, og gir ellers en ærlig "kan ikke validere"-forklaring.
"""

import random
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

TOLERANSE = 1e-6

_X = sp.Symbol("x")
_Y = sp.Function("y")


def _parse(streng: str, lokale: dict | None = None):
    return parse_expr(streng, local_dict=lokale, transformations=_TRANSFORMASJONER)


def _tilfeldige_punkter(n: int = 3, lav: float = -3.0, hoy: float = 3.0) -> list:
    # Fast frø: valideringen skal gi samme (etterprøvbare/forklarbare) resultat hver kjøring.
    tilfeldig = random.Random(42)
    return [sp.Float(tilfeldig.uniform(lav, hoy)) for _ in range(n)]


def _naer_null(verdi, toleranse: float = TOLERANSE) -> bool:
    try:
        if verdi.has(sp.nan) or verdi.has(sp.zoo) or verdi.has(sp.oo) or verdi.has(-sp.oo):
            return False
    except AttributeError:
        pass
    try:
        return abs(complex(verdi)) < toleranse
    except (TypeError, ValueError):
        return False


def _sjekk_i_punkter(uttrykk, var: sp.Symbol, ekstra_verdier: dict | None = None) -> tuple[bool, str]:
    """Evaluerer `uttrykk` (skal være ~0 hvis løsningen stemmer) i flere punkter for `var`."""
    ekstra = ekstra_verdier or {}
    punkter = _tilfeldige_punkter()
    detaljer_punkter = []
    alle_ok = True
    for p in punkter:
        try:
            verdi = uttrykk.subs({**ekstra, var: p}).evalf()
            ok = _naer_null(verdi)
        except Exception as e:
            verdi, ok = f"kunne ikke evalueres ({e})", False
        alle_ok = alle_ok and ok
        detaljer_punkter.append(f"{var}={float(p):.3f} -> avvik={verdi}")
    return alle_ok, "; ".join(detaljer_punkter)


def _fri_variabel(*uttrykk) -> sp.Symbol:
    symboler: set = set()
    for u in uttrykk:
        symboler |= u.free_symbols
    symboler = sorted(symboler, key=str)
    return symboler[0] if symboler else _X


# ---------------------------------------------------------------------------
# Differensialligninger
# ---------------------------------------------------------------------------

def _ser_ut_som_ode(problem: str) -> bool:
    return bool(re.search(r"y\s*''|y\s*'|Derivative\(\s*y|y\(x\)", problem))


def _forbered_ode_streng(s: str) -> str:
    s = s.replace(" ", "")
    s = s.replace("y''", "Derivative(y(x),x,2)")
    s = s.replace("y'", "Derivative(y(x),x)")
    s = re.sub(r"(?<![\w(])y(?!\()", "y(x)", s)
    return s


def _parse_ode_likning(problem: str) -> sp.Eq:
    lokale = {"x": _X, "y": _Y, "Eq": sp.Eq, "Derivative": sp.Derivative}
    s = _forbered_ode_streng(problem)
    if "Eq(" in s:
        parsed = _parse(s, lokale)
        return parsed if isinstance(parsed, sp.Eq) else sp.Eq(parsed, 0)
    if "=" in s:
        venstre, hoyre = s.split("=", 1)
        return sp.Eq(_parse(venstre, lokale), _parse(hoyre, lokale))
    return sp.Eq(_parse(s, lokale), 0)


def _parse_ode_losning(losning: str):
    """Returnerer y(x) uttrykt ved x (og evt. C1, C2, ...) fra løsningsstrengen."""
    lokale = {"x": _X, "y": _Y, "Eq": sp.Eq, "Derivative": sp.Derivative}
    s = _forbered_ode_streng(losning)
    if "Eq(" in s:
        parsed = _parse(s, lokale)
        return parsed.rhs if isinstance(parsed, sp.Eq) else parsed
    if "=" in s:
        _, hoyre = s.split("=", 1)
        return _parse(hoyre, lokale)
    return _parse(s, lokale)


def _valider_ode(problem: str, losning: str) -> dict:
    try:
        ligning = _parse_ode_likning(problem)
    except Exception as e:
        return {"validert": False, "detaljer": f"Klarte ikke å tolke differensialligningen {problem!r}: {e}"}
    try:
        y_uttrykk = _parse_ode_losning(losning)
    except Exception as e:
        return {"validert": False, "detaljer": f"Klarte ikke å tolke løsningen {losning!r}: {e}"}

    try:
        residual = (ligning.lhs - ligning.rhs).subs(_Y(_X), y_uttrykk).doit()
        residual = sp.simplify(residual)
    except Exception as e:
        return {"validert": False, "detaljer": f"Klarte ikke å sette løsningen inn i differensialligningen: {e}"}

    frie_konstanter = sorted(residual.free_symbols - {_X}, key=str)
    tilfeldig = random.Random(7)
    konst_verdier = {c: sp.Float(tilfeldig.uniform(0.5, 2.5)) for c in frie_konstanter}

    alle_ok, detaljer_punkter = _sjekk_i_punkter(residual, _X, konst_verdier)
    konst_tekst = f" (med {', '.join(f'{k}={float(v):.2f}' for k, v in konst_verdier.items())})" if konst_verdier else ""
    detaljer = (
        f"Satte løsningen inn i differensialligningen{konst_tekst} og evaluerte residualet numerisk "
        f"i 3 punkter (toleranse {TOLERANSE:g}): {detaljer_punkter}"
    )
    return {"validert": alle_ok, "detaljer": detaljer}


# ---------------------------------------------------------------------------
# Algebraiske likninger
# ---------------------------------------------------------------------------

def _parse_likning(problem: str) -> sp.Eq:
    s = problem.replace(" ", "")
    if "Eq(" in s:
        parsed = _parse(s, {"Eq": sp.Eq})
        return parsed if isinstance(parsed, sp.Eq) else sp.Eq(parsed, 0)
    if "=" in s:
        venstre, hoyre = s.split("=", 1)
        return sp.Eq(_parse(venstre), _parse(hoyre))
    return sp.Eq(_parse(s), 0)


def _hent_kandidatverdier(losning: str, var: sp.Symbol) -> list:
    funnet = []
    for del_ in re.split(r"[,;]|\bog\b", losning):
        del_ = del_.strip()
        if not del_:
            continue
        if "=" in del_:
            del_ = del_.split("=", 1)[1].strip()
        del_ = del_.strip("{}[]() ")
        if not del_:
            continue
        try:
            funnet.append(_parse(del_, {str(var): var}))
        except Exception:
            continue
    return funnet


def _valider_likning(problem: str, losning: str) -> dict:
    try:
        eq = _parse_likning(problem)
    except Exception as e:
        return {"validert": False, "detaljer": f"Klarte ikke å tolke likningen {problem!r}: {e}"}

    symboler = sorted(eq.free_symbols, key=str)
    if len(symboler) != 1:
        return {
            "validert": False,
            "detaljer": (
                f"Fant {len(symboler)} ukjente i {problem!r} – denne valideringsmetoden støtter "
                "kun likninger med nøyaktig én ukjent."
            ),
        }
    var = symboler[0]

    kandidater = _hent_kandidatverdier(losning, var)
    if not kandidater:
        return {
            "validert": False,
            "detaljer": f"Klarte ikke å tolke noen kandidatløsning ut fra {losning!r}.",
        }

    diff = eq.lhs - eq.rhs
    detaljer_punkter = []
    alle_ok = True
    for verdi in kandidater:
        try:
            avvik = sp.N(diff.subs(var, verdi))
            ok = _naer_null(avvik)
        except Exception as e:
            avvik, ok = f"kunne ikke evalueres ({e})", False
        alle_ok = alle_ok and ok
        detaljer_punkter.append(f"{var}={verdi} -> avvik={avvik}")

    detaljer = (
        f"Satte {len(kandidater)} kandidatløsning(er) inn i likningen (toleranse {TOLERANSE:g}): "
        + "; ".join(detaljer_punkter)
    )
    return {"validert": alle_ok, "detaljer": detaljer}


# ---------------------------------------------------------------------------
# Derivasjon / integrasjon
# ---------------------------------------------------------------------------

def _valider_derivert(problem: str, losning: str) -> dict:
    try:
        f = _parse(problem)
        g = _parse(losning)
    except Exception as e:
        return {"validert": False, "detaljer": f"Klarte ikke å tolke uttrykkene: {e}"}
    var = _fri_variabel(f, g)
    diff_uttrykk = sp.simplify(sp.diff(f, var) - g)
    alle_ok, detaljer_punkter = _sjekk_i_punkter(diff_uttrykk, var)
    detaljer = (
        "Deriverte det opprinnelige uttrykket på nytt og sammenlignet med den påståtte deriverte "
        f"i 3 punkter (toleranse {TOLERANSE:g}): {detaljer_punkter}"
    )
    return {"validert": alle_ok, "detaljer": detaljer}


def _valider_antiderivert(problem: str, losning: str) -> dict:
    try:
        f = _parse(problem)
        F = _parse(losning)
    except Exception as e:
        return {"validert": False, "detaljer": f"Klarte ikke å tolke uttrykkene: {e}"}
    var = _fri_variabel(f, F)
    diff_uttrykk = sp.simplify(sp.diff(F, var) - f)
    alle_ok, detaljer_punkter = _sjekk_i_punkter(diff_uttrykk, var)
    detaljer = (
        "Deriverte den påståtte antideriverte og sammenlignet med integranden i 3 punkter "
        f"(F'(x) skal være lik f(x); toleranse {TOLERANSE:g}): {detaljer_punkter}"
    )
    return {"validert": alle_ok, "detaljer": detaljer}


def _valider_uttrykk_auto(problem: str, losning: str) -> dict:
    try:
        a = _parse(problem)
        b = _parse(losning)
    except Exception as e:
        return {
            "validert": False,
            "detaljer": (
                f"Kunne ikke tolke '{problem}' og/eller '{losning}' som SymPy-uttrykk – trolig en "
                f"bevis-, begreps- eller matrise-/komplekstalloppgave denne generelle sjekken ikke "
                f"dekker ennå. Svaret er IKKE verifisert av et verktøy. ({e})"
            ),
        }

    for retning, (uttrykk_f, uttrykk_g) in (
        ("løsningen ser ut som den deriverte av oppgaven", (a, b)),
        ("løsningen ser ut som en antiderivert av oppgaven", (b, a)),
    ):
        try:
            var = _fri_variabel(uttrykk_f, uttrykk_g)
            diff_uttrykk = sp.simplify(sp.diff(uttrykk_f, var) - uttrykk_g)
            alle_ok, detaljer_punkter = _sjekk_i_punkter(diff_uttrykk, var)
            if alle_ok:
                return {
                    "validert": True,
                    "detaljer": f"Tolket automatisk som at {retning}; stemte numerisk i 3 punkter: {detaljer_punkter}",
                }
        except Exception:
            continue

    try:
        var = _fri_variabel(a, b)
        if var in (a.free_symbols | b.free_symbols):
            alle_ok, detaljer_punkter = _sjekk_i_punkter(sp.simplify(a - b), var)
        else:
            avvik = sp.N(a - b)
            alle_ok, detaljer_punkter = _naer_null(avvik), f"avvik={avvik}"
        if alle_ok:
            return {"validert": True, "detaljer": f"Oppgave og svar er numerisk like: {detaljer_punkter}"}
    except Exception:
        pass

    return {
        "validert": False,
        "detaljer": (
            "Klarte ikke å bekrefte sammenhengen mellom oppgaven og svaret automatisk (denne generelle "
            "sjekken dekker ikke alle oppgavetyper, f.eks. matrise-/komplekstalloppgaver). "
            "Svaret er IKKE numerisk validert – stol ikke blindt på det."
        ),
    }


# ---------------------------------------------------------------------------
# Offentlig funksjon
# ---------------------------------------------------------------------------

def validate(problem: str, losning: str, operasjon: str = "auto") -> dict:
    """Sjekker om `losning` faktisk stemmer med `problem`, numerisk med SymPy.

    `operasjon`: "solve_ode", "solve_equation", "derive", "integrate" tvinger
    en bestemt tolkning (brukt av llm_client, som vet hvilket verktøy som ga
    svaret). "auto" (standard) prøver å gjenkjenne oppgavetypen selv – brukt
    av selvtesten og som ærlig fallback for oppgavetyper vi ikke kjenner.
    """
    try:
        if operasjon == "solve_ode" or (operasjon == "auto" and _ser_ut_som_ode(problem)):
            return _valider_ode(problem, losning)
        if operasjon == "solve_equation" or (
            operasjon == "auto" and ("=" in problem or "Eq(" in problem) and not _ser_ut_som_ode(problem)
        ):
            return _valider_likning(problem, losning)
        if operasjon == "derive":
            return _valider_derivert(problem, losning)
        if operasjon == "integrate":
            return _valider_antiderivert(problem, losning)
        return _valider_uttrykk_auto(problem, losning)
    except Exception as e:
        return {"validert": False, "detaljer": f"Validering feilet teknisk: {e!r}. Svaret er IKKE bekreftet."}
