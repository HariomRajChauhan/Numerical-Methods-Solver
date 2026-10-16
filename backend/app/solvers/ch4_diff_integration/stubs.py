"""Coming-soon stubs for Chapter 4 — Numerical Differentiation and Integration (ENSH 252).

See ``ch1_nonlinear/stubs.py`` for the pattern.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH4_DIFF_INTEGRATION

register_coming_soon(
    CHAPTER,
    "numerical_differentiation",
    "Numerical Differentiation",
    "Approximate f'(x) from function values using forward, backward or central differences.",
    theory=(
        "Derivatives are estimated from differences of nearby function values: forward "
        "(f(x+h)-f(x))/h, backward (f(x)-f(x-h))/h, and central "
        "(f(x+h)-f(x-h))/(2h). Central differences are more accurate; the step h trades "
        "truncation error against round-off."
    ),
    pseudocode=(
        "Differentiate(f, x, h, scheme):\n"
        "    forward : (f(x+h) - f(x)) / h\n"
        "    backward: (f(x) - f(x-h)) / h\n"
        "    central : (f(x+h) - f(x-h)) / (2h)"
    ),
)

register_coming_soon(
    CHAPTER,
    "local_extrema",
    "Local Maxima and Minima",
    "Locate extrema of a tabulated function from sign changes of the finite-difference slope.",
    theory=(
        "For equally-spaced data a local maximum or minimum is detected where the first "
        "difference changes sign (delta y goes + to - for a maximum, - to + for a "
        "minimum). Refining with higher-order differences or interpolation locates the "
        "turning point more precisely."
    ),
    pseudocode=(
        "LocalExtrema(xs, ys):\n"
        "    for i: if delta_y changes sign around i:\n"
        "        classify as maximum (+) or minimum (-)\n"
        "    optionally refine by interpolating around the turning point"
    ),
)

register_coming_soon(
    CHAPTER,
    "newton_cotes",
    "Newton-Cotes Quadrature",
    "Family of equal-spacing integration rules behind the trapezoidal and Simpson rules.",
    theory=(
        "Newton-Cotes formulas fit a polynomial through equally-spaced nodes and "
        "integrate it. The trapezoidal rule (degree 1) and Simpson's, Boole's and "
        "Weddle's rules (higher degrees) are special cases; accuracy improves with the "
        "polynomial degree for smooth integrands."
    ),
    pseudocode=(
        "NewtonCotes(f, a, b, n, degree):\n"
        "    fit the degree-d polynomial through the equally spaced nodes\n"
        "    integrate the polynomial over [a, b]"
    ),
)

register_coming_soon(
    CHAPTER,
    "trapezoidal",
    "Trapezoidal Rule",
    "Integrate by approximating the area with trapezoids; second-order accurate.",
    theory=(
        "The trapezoidal rule joins successive function values with straight lines, "
        "giving the integral as h/2 [y0 + 2(y1 + ... + y_{n-1}) + yn]. Its error is "
        "O(h^2) and it integrates any linear function exactly."
    ),
    pseudocode=(
        "Trapezoidal(f, a, b, n):\n"
        "    h <- (b - a) / n\n"
        "    I <- h/2 * (f(a) + f(b) + 2*sum_{i=1}^{n-1} f(a + i*h))"
    ),
)

register_coming_soon(
    CHAPTER,
    "simpson_13",
    "Simpson's 1/3 Rule",
    "Integrate over pairs of intervals with a quadratic fit; fourth-order accurate (n even).",
    theory=(
        "Simpson's 1/3 rule fits a parabola through each pair of subintervals, giving "
        "the integral as h/3 [y0 + 4(y1 + y3 + ...) + 2(y2 + y4 + ...) + yn]. Its error "
        "is O(h^4); the number of intervals must be even."
    ),
    pseudocode=(
        "Simpson13(f, a, b, n):        # n even\n"
        "    h <- (b - a) / n\n"
        "    I <- h/3 * (f(a) + f(b) + 4*sum(odd i) + 2*sum(even i, i<n))"
    ),
)

register_coming_soon(
    CHAPTER,
    "simpson_38",
    "Simpson's 3/8 Rule",
    "Integrate over triples of intervals with a cubic fit; fourth-order accurate (n multiple of 3).",
    theory=(
        "Simpson's 3/8 rule fits a cubic through each group of three subintervals, "
        "giving the integral as 3h/8 [y0 + 3(y1 + y2 + ...) + 2(y3 + ...) + yn]. It is "
        "handy when the number of intervals is a multiple of three."
    ),
    pseudocode=(
        "Simpson38(f, a, b, n):        # n multiple of 3\n"
        "    h <- (b - a) / n\n"
        "    I <- 3h/8 * (f(a) + f(b) + 3*sum(i not mult. of 3) + 2*sum(i mult. of 3, i<n))"
    ),
)

register_coming_soon(
    CHAPTER,
    "boole",
    "Boole's Rule",
    "Fifth-degree Newton-Cotes rule over four subintervals; sixth-order accurate.",
    theory=(
        "Boole's rule integrates a degree-5 polynomial over four equal subintervals "
        "using the weights 7:32:12:32:7 (times 2h/45). Its error is O(h^6), and it is "
        "exact for polynomials up to degree five."
    ),
    pseudocode=(
        "Boole(f, a, b, n):        # n multiple of 4\n"
        "    h <- (b - a) / n\n"
        "    per group of 4 intervals: (2h/45)*(7 y0 + 32 y1 + 12 y2 + 32 y3 + 7 y4)"
    ),
)

register_coming_soon(
    CHAPTER,
    "weddle",
    "Weddle's Rule",
    "Sixth-degree Newton-Cotes rule over six subintervals (weights 1,5,1,6,1,5,1).",
    theory=(
        "Weddle's rule integrates over six equal subintervals using the weights "
        "1:5:1:6:1:5:1 (times 3h/10). It is exact for polynomials up to degree five and "
        "is used to improve on Simpson's rule for tabulated data."
    ),
    pseudocode=(
        "Weddle(f, a, b, n):        # n multiple of 6\n"
        "    h <- (b - a) / n\n"
        "    per group of 6 intervals: (3h/10)*(y0 + 5y1 + y2 + 6y3 + y4 + 5y5 + y6)"
    ),
)

register_coming_soon(
    CHAPTER,
    "romberg",
    "Romberg Integration",
    "Accelerate the trapezoidal rule with Richardson extrapolation for high accuracy.",
    theory=(
        "Romberg integration applies Richardson extrapolation to a sequence of "
        "trapezoidal estimates on successively halved steps, cancelling leading error "
        "terms. The first extrapolation reproduces Simpson's rule, and higher levels "
        "converge very rapidly for smooth integrands."
    ),
    pseudocode=(
        "Romberg(f, a, b, order):\n"
        "    R[0][0] <- trapezoidal with 1 interval\n"
        "    for k = 1..order:\n"
        "        R[k][0] <- trapezoidal with 2^k intervals\n"
        "        for j = 1..k:\n"
        "            R[k][j] <- R[k][j-1] + (R[k][j-1] - R[k-1][j-1])/(4^j - 1)\n"
        "    return R[order][order]"
    ),
)

register_coming_soon(
    CHAPTER,
    "gauss_legendre",
    "Gauss-Legendre Quadrature",
    "Integrate exactly for polynomials up to degree 2n-1 using optimal nodes and weights.",
    theory=(
        "Gauss-Legendre quadrature chooses n interior nodes (the roots of the Legendre "
        "polynomial) and matching weights so that the rule is exact for polynomials of "
        "degree up to 2n-1. It needs fewer function evaluations than Newton-Cotes rules "
        "for the same accuracy."
    ),
    pseudocode=(
        "GaussLegendre(f, a, b, n):\n"
        "    obtain nodes x_i and weights w_i on [-1, 1]\n"
        "    map to [a, b]\n"
        "    I <- (b - a)/2 * sum_i w_i * f(x_i)"
    ),
)
