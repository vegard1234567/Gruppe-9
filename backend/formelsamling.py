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
    "I1": {
        "navn": "Delvis integrasjon",
        "formel": r"\int u\,dv = uv - \int v\,du",
        "referanse": "Thomas' Calculus, kap. 8",
        "bruk": "Når integralet inneholder et produkt som blir enklere etter derivasjon av én faktor.",
    },
    "O1": {
        "navn": "Karakteristisk ligning (2. ordens lineær ODE)",
        "formel": r"ar^2 + br + c = 0 \text{ for } ay'' + by' + cy = 0",
        "referanse": "Edwards & Penney, kap. 3",
        "bruk": "Når en homogen lineær differensialligning med konstante koeffisienter skal løses.",
    },
    "K1": {
        "navn": "Eulers formel",
        "formel": r"e^{i\theta} = \cos\theta + i\sin\theta",
        "referanse": "Buanes: Komplekse tall",
        "bruk": "Når komplekse tall skal kobles mellom eksponentialform og trigonometrisk form.",
    },
    "M1": {
        "navn": "Determinant (2x2)",
        "formel": r"\det\begin{pmatrix}a & b\\ c & d\end{pmatrix} = ad - bc",
        "referanse": "Edwards & Penney, kap. 4",
        "bruk": "Når determinanten til en 2x2-matrise skal beregnes eller inverterbarhet vurderes.",
    },
    "D3": {"navn": "Kvotientregelen", "formel": r"\left(\frac{u}{v}\right)' = \frac{u'v-uv'}{v^2}", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Når en funksjon er skrevet som en kvotient."},
    "D4": {"navn": "Potensregelen", "formel": r"(x^n)' = nx^{n-1}", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Når en potensfunksjon skal deriveres."},
    "D5": {"navn": "Derivert av eksponentialfunksjon", "formel": r"(e^x)' = e^x", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Når en eksponentialfunksjon skal deriveres."},
    "D6": {"navn": "Deriverte av sinus og cosinus", "formel": r"(\sin x)'=\cos x,\quad (\cos x)'=-\sin x", "referanse": "Thomas' Calculus, kap. 3", "bruk": "Når trigonometriske funksjoner skal deriveres."},
    "I2": {"navn": "Substitusjon i integral", "formel": r"\int f(g(x))g'(x)\,dx = \int f(u)\,du", "referanse": "Thomas' Calculus, kap. 8", "bruk": "Når et integral inneholder en sammensatt funksjon og den deriverte indre funksjonen."},
    "I3": {"navn": "Potensregelen for integrasjon", "formel": r"\int x^n\,dx = \frac{x^{n+1}}{n+1}+C,\ n\ne-1", "referanse": "Thomas' Calculus, kap. 5", "bruk": "Når en potens av x skal integreres."},
    "O2": {"navn": "Lineær superposisjon", "formel": r"y=c_1y_1+c_2y_2", "referanse": "Edwards & Penney, kap. 3", "bruk": "Når to lineært uavhengige løsninger kombineres for en homogen ODE."},
    "O3": {"navn": "Eksistens av generell ODE-løsning", "formel": r"y'=f(x,y)", "referanse": "Edwards & Penney, kap. 2", "bruk": "Når en førsteordens differensialligning identifiseres eller analyseres."},
    "M2": {"navn": "Egenverdiligning", "formel": r"\det(A-\lambda I)=0", "referanse": "Edwards & Penney, kap. 4", "bruk": "Når egenverdiene til en matrise skal finnes."},
    "M3": {"navn": "Invers matrise", "formel": r"AA^{-1}=I", "referanse": "Edwards & Penney, kap. 4", "bruk": "Når et lineært system løses ved hjelp av den inverse matrisen."},
    "M4": {"navn": "Lineært likningssystem", "formel": r"Ax=b", "referanse": "Edwards & Penney, kap. 4", "bruk": "Når flere lineære ligninger behandles samlet i matriseform."},
    "K2": {"navn": "Kompleks konjugering", "formel": r"z\overline{z}=|z|^2", "referanse": "Edwards & Penney, kap. 7", "bruk": "Når modulus eller divisjon av komplekse tall skal beregnes."},
    "K3": {"navn": "De Moivres formel", "formel": r"(r e^{i\theta})^n=r^n e^{in\theta}", "referanse": "Edwards & Penney, kap. 7", "bruk": "Når potenser av komplekse tall skal beregnes i polarform."},
}
