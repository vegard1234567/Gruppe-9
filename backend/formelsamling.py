"""Innebygd formelsamling – à la Jarle Johannessen: «Tekniske Tabeller».

Modellen skal referere til formler herfra i sine forklaringer.
Utvid gjerne med formler fra Edwards & Penney og Thomas' Calculus.

Feltet «bruk» hjelper modellen å velge regel. Modellen oppgir formel-ID i
løsningssteget; appen kontrollerer ID-en og henter navn og referanse herfra.

HVORFOR: Sporbarhet. «Hvilken formel brukte du, og hvor står den?» er et
spørsmål enhver ingeniør må kunne svare på.
"""

FORMELSAMLING = {
    "D1": {
        "navn": "Produktregelen",
        "formel": r"(uv)' = u'v + uv'",
        "referanse": "Thomas' Calculus, kap. 3",
        "bruk": "Når et produkt av to funksjoner skal deriveres.",
    },
    "D2": {
        "navn": "Kjerneregelen",
        "formel": r"\frac{dy}{dx} = \frac{dy}{du}\cdot\frac{du}{dx}",
        "referanse": "Thomas' Calculus, kap. 3",
        "bruk": "Når en sammensatt funksjon skal deriveres.",
    },
    "D3": {
        "navn": "Kvotientregelen",
        "formel": r"\left(\frac{u}{v}\right)' = \frac{u'v - uv'}{v^2}",
        "referanse": "Thomas' Calculus, kap. 3",
        "bruk": "Når en brøk av to funksjoner skal deriveres.",
    },
    "D4": {
        "navn": "Potensregelen",
        "formel": r"\frac{d}{dx}x^n = n x^{n-1}",
        "referanse": "Thomas' Calculus, kap. 3",
        "bruk": "Når en potens av variabelen skal deriveres.",
    },
    "I1": {
        "navn": "Delvis integrasjon",
        "formel": r"\int u\,dv = uv - \int v\,du",
        "referanse": "Thomas' Calculus, kap. 8",
        "bruk": "Når integralet inneholder et produkt som blir enklere etter derivasjon av én faktor.",
    },
    "I2": {
        "navn": "Substitusjon (variabelskifte)",
        "formel": r"\int f(g(x))g'(x)\,dx = \int f(u)\,du,\quad u = g(x)",
        "referanse": "Thomas' Calculus, kap. 5",
        "bruk": "Når integranden er en sammensatt funksjon ganget med den indre funksjonens deriverte.",
    },
    "I3": {
        "navn": "Standardintegral 1/x",
        "formel": r"\int \frac{1}{x}\,dx = \ln|x| + C",
        "referanse": "Thomas' Calculus, kap. 5",
        "bruk": "Når integranden er den reelle funksjonen 1/x.",
    },
    "I4": {
        "navn": "Potensregelen for integrasjon",
        "formel": r"\int x^n\,dx = \frac{x^{n+1}}{n+1} + C,\quad n \neq -1",
        "referanse": "Thomas' Calculus, kap. 5",
        "bruk": "Når en potens av variabelen skal integreres.",
    },
    "O1": {
        "navn": "Karakteristisk ligning (2. ordens lineær ODE)",
        "formel": r"ar^2 + br + c = 0 \text{ for } ay'' + by' + cy = 0",
        "referanse": "Edwards & Penney, kap. 3",
        "bruk": "Når en homogen lineær differensialligning med konstante koeffisienter skal løses.",
    },
    "O2": {
        "navn": "Førsteordens lineær ODE – integrerende faktor",
        "formel": r"\mu(x) = e^{\int p(x)\,dx} \text{ for } y' + p(x)y = q(x)",
        "referanse": "Edwards & Penney, kap. 1",
        "bruk": "Når en førsteordens lineær differensialligning skal løses med integrerende faktor.",
    },
    "K1": {
        "navn": "Eulers formel",
        "formel": r"e^{i\theta} = \cos\theta + i\sin\theta",
        "referanse": "Buanes: Komplekse tall",
        "bruk": "Når komplekse tall skal kobles mellom eksponentialform og trigonometrisk form.",
    },
    "K2": {
        "navn": "Polarform av komplekst tall",
        "formel": r"z = a + bi = r(\cos\theta + i\sin\theta),\quad r = |z| = \sqrt{a^2+b^2}",
        "referanse": "Buanes: Komplekse tall",
        "bruk": "Når et komplekst tall skal skrives om fra rektangulær til polar form.",
    },
    "K3": {
        "navn": "De Moivres formel",
        "formel": r"z^n = r^n(\cos(n\theta) + i\sin(n\theta))",
        "referanse": "Buanes: Komplekse tall",
        "bruk": "Når potenser eller røtter av et komplekst tall på polarform skal beregnes.",
    },
    "M1": {
        "navn": "Determinant (2x2)",
        "formel": r"\det\begin{pmatrix}a & b\\ c & d\end{pmatrix} = ad - bc",
        "referanse": "Edwards & Penney, kap. 4",
        "bruk": "Når determinanten til en 2x2-matrise skal beregnes eller inverterbarhet vurderes.",
    },
    "M2": {
        "navn": "Determinant (3x3, Sarrus' regel)",
        "formel": r"\det A = a_{11}a_{22}a_{33} + a_{12}a_{23}a_{31} + a_{13}a_{21}a_{32} - a_{13}a_{22}a_{31} - a_{11}a_{23}a_{32} - a_{12}a_{21}a_{33}",
        "referanse": "Edwards & Penney, kap. 4",
        "bruk": "Når determinanten til en 3x3-matrise skal beregnes for hånd.",
    },
    "M3": {
        "navn": "Egenverdier",
        "formel": r"\det(A - \lambda I) = 0",
        "referanse": "Edwards & Penney, kap. 4",
        "bruk": "Når egenverdiene til en kvadratisk matrise A skal bestemmes.",
    },
    "M4": {
        "navn": "Løsning av lineært likningssystem (Ax = b)",
        "formel": r"x = A^{-1}b \text{ (dersom } A \text{ er inverterbar)}",
        "referanse": "Edwards & Penney, kap. 3",
        "bruk": "Når et lineært likningssystem med like mange likninger som ukjente skal løses.",
    },
    "T1": {
        "navn": "Pythagoras' læresetning",
        "formel": r"a^2 + b^2 = c^2",
        "referanse": "Thomas' Calculus, appendiks / grunnleggende geometri",
        "bruk": "Når sammenhengen mellom katetene og hypotenusen i en rettvinklet trekant er relevant, f.eks. i bevisoppgaver.",
    },
}
