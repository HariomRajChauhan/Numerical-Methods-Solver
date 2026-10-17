"""Coming-soon stubs for Chapter 1 — Non-linear Equations (ENSH 252 syllabus).

These register with ``status=coming_soon`` so they appear in navigation, search
and the chapter page (with a badge) and expose their theory/pseudocode, but
``POST /api/solve/<id>`` returns 409 until a real solver replaces the stub.
``bisection``, ``errors_accuracy``, ``false_position``, ``secant``,
``newton_raphson``, ``fixed_point`` and ``method_comparison`` are implemented and
live in their own modules.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH1_NONLINEAR

register_coming_soon(
    CHAPTER,
    "nonlinear_system_direct",
    "Non-linear Systems (Direct/Iteration)",
    "Solve a system of non-linear equations by fixed-point (successive substitution).",
    theory=(
        "A system f1(x,y) = 0, f2(x,y) = 0 is rearranged as x = g1(x,y), y = g2(x,y) "
        "and solved by simultaneous iteration. Convergence requires the spectral radius "
        "of the Jacobian of g to be below one near the solution. It extends fixed-point "
        "iteration to several unknowns."
    ),
    pseudocode=(
        "NonlinearFixedPoint(g1, g2, x0, y0, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        (x, y) <- (g1(x0, y0), g2(x0, y0))\n"
        "        if ||(x, y) - (x0, y0)|| < tol: return x, y, k\n"
        "        (x0, y0) <- (x, y)"
    ),
)

register_coming_soon(
    CHAPTER,
    "nonlinear_system_newton",
    "Non-linear Systems (Newton's Method)",
    "Solve a system of non-linear equations with the multi-variable Newton-Raphson method.",
    theory=(
        "Newton's method for systems linearises f at the current guess using the "
        "Jacobian J and solves J(xk) dx = -f(xk), then updates x(k+1) = xk + dx. It "
        "converges quadratically near the solution but needs the Jacobian (analytically "
        "or numerically) and a good initial guess."
    ),
    pseudocode=(
        "NonlinearNewton(f, J, x0, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        solve the linear system J(x) dx = -f(x)\n"
        "        x <- x + dx\n"
        "        if ||dx|| < tol: return x, k"
    ),
)
