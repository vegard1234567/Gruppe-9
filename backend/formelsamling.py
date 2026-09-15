"""Innebygd formelsamling for MatteHjelpen."""

FORMELSAMLING = {
    "D1": {"navn": "Produktregelen", "formel": r"(uv)' = u'v + uv'", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Produkt av funksjoner."},
    "D2": {"navn": "Kjerneregelen", "formel": r"(f(g(x)))' = f'(g(x))g'(x)", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Sammensatte funksjoner."},
    "D3": {"navn": "Potensregelen", "formel": r"(x^n)' = nx^{n-1}", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Potenser."},
    "D4": {"navn": "Kvotientregelen", "formel": r"(u/v)' = (u'v-uv')/v^2", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Kvotient av funksjoner."},
    "D5": {"navn": "Derivert av e^x", "formel": r"(e^x)'=e^x", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Eksponentialfunksjoner."},
    "I1": {"navn": "Delvis integrasjon", "formel": r"\int u\,dv=uv-\int v\,du", "referanse": "Thomas' Calculus, kap. 8", "bruk": "Produkt i integrand."},
    "I2": {"navn": "Potensregelen for integrasjon", "formel": r"\int x^n dx=x^{n+1}/(n+1)+C", "referanse": "Thomas' Calculus, kap. 8", "bruk": "Potenser med n ulik -1."},
    "I3": {"navn": "Substitusjon", "formel": r"\int f(g(x))g'(x)dx=\int f(u)du", "referanse": "Thomas' Calculus, kap. 8", "bruk": "Sammensatte uttrykk."},
    "I4": {"navn": "Fundamentalteoremet", "formel": r"\int_a^b f(x)dx=F(b)-F(a)", "referanse": "Thomas' Calculus, kap. 5", "bruk": "Bestemt integral."},
    "O1": {"navn": "Karakteristisk ligning", "formel": r"ar^2+br+c=0", "referanse": "Edwards & Penney, kap. 3", "bruk": "Homogen lineær ODE av 2. orden."},
    "O2": {"navn": "Førsteordens separasjon", "formel": r"dy/dx=g(x)h(y)", "referanse": "Edwards & Penney, kap. 2", "bruk": "Separable ODE."},
    "K1": {"navn": "Eulers formel", "formel": r"e^{i\theta}=\cos\theta+i\sin\theta", "referanse": "Buanes: Komplekse tall", "bruk": "Eksponentialform."},
    "K2": {"navn": "Absoluttverdi av komplekst tall", "formel": r"|a+bi|=\sqrt{a^2+b^2}", "referanse": "Buanes: Komplekse tall", "bruk": "Modulus."},
    "M1": {"navn": "Determinant 2x2", "formel": r"det(A)=ad-bc", "referanse": "Edwards & Penney, kap. 4", "bruk": "Determinant av 2x2-matrise."},
    "M2": {"navn": "Invers 2x2", "formel": r"A^{-1}=1/(ad-bc)[[d,-b],[-c,a]]", "referanse": "Edwards & Penney, kap. 4", "bruk": "Invers matrise når determinanten er ulik null."},
}
