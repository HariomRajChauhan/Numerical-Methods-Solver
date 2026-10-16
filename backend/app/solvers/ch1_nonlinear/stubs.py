"""Coming-soon stubs for Chapter 1 — Non-linear Equations (ENSH 252 syllabus).

These register with ``status=coming_soon`` so they appear in navigation, search
and the chapter page (with a badge) and expose their theory/pseudocode, but
``POST /api/solve/<id>`` returns 409 until a real solver replaces the stub.
``bisection`` is the one implemented method and lives in ``bisection.py``.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH1_NONLINEAR

register_coming_soon(
    CHAPTER,
    "errors_accuracy",
    "Errors and Accuracy",
    "Measures of error — absolute, relative and percentage — and significant digits.",
    theory=(
        "Numerical results are always approximate. The standard measures are the "
        "absolute error |x - x*| and the relative error |x - x*|/|x| (often quoted as a "
        "percentage); accuracy is described by the number of significant digits. Error "
        "analysis separates truncation error (introduced by the method) from round-off "
        "error (from finite-precision arithmetic)."
    ),
    pseudocode=(
        "Error concepts:\n"
        "    absolute error  Ea <- |true - approx|\n"
        "    relative error  Er <- Ea / |true|\n"
        "    percentage error  <- Er * 100%\n"
        "    significant digits are related to the relative error"
    ),
)

register_coming_soon(
    CHAPTER,
    "false_position",
    "False Position Method",
    "Root finding by linear interpolation between the bracket endpoints; "
    "faster than bisection but can stall at one end.",
    theory=(
        "The false position (regula falsi) method brackets a root like bisection, "
        "but instead of the midpoint it takes the x-intercept of the secant line "
        "through (a, f(a)) and (b, f(b)). The sign of f at that point decides which "
        "endpoint is replaced. It usually converges faster than bisection, though for "
        "some functions one endpoint can stop moving and slow it down."
    ),
    pseudocode=(
        "FalsePosition(f, a, b, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        c  <- b - f(b)*(b - a)/(f(b) - f(a))\n"
        "        fc <- f(c)\n"
        "        if |fc| < tol or |c - prev| < tol: return c, k\n"
        "        if f(a)*fc < 0: b <- c else: a <- c\n"
        "        prev <- c"
    ),
)

register_coming_soon(
    CHAPTER,
    "secant",
    "Secant Method",
    "Root finding from a secant line through the last two iterates; "
    "no derivative needed, super-linear convergence.",
    theory=(
        "The secant method replaces the derivative with a finite difference across "
        "the two most recent points and takes the x-intercept of that secant line as "
        "the next estimate. It needs two starting values but no derivative, and "
        "converges super-linearly (order about 1.618). Unlike bisection it is not "
        "guaranteed to keep the root bracketed."
    ),
    pseudocode=(
        "Secant(f, x0, x1, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        x2 <- x1 - f(x1)*(x1 - x0)/(f(x1) - f(x0))\n"
        "        if |x2 - x1| < tol: return x2, k\n"
        "        x0 <- x1; x1 <- x2"
    ),
)

register_coming_soon(
    CHAPTER,
    "newton_raphson",
    "Newton-Raphson Method",
    "Quadratic root finding using f(x) and its derivative f'(x) from a single guess.",
    theory=(
        "Newton-Raphson follows the tangent line at the current point to its "
        "x-intercept, giving x(k+1) = x(k) - f(x(k))/f'(x(k)). Started near the root "
        "it converges quadratically (the number of correct digits roughly doubles each "
        "step); a poor guess or a near-zero derivative can make it diverge."
    ),
    pseudocode=(
        "NewtonRaphson(f, df, x0, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        x1 <- x0 - f(x0)/df(x0)\n"
        "        if |x1 - x0| < tol: return x1, k\n"
        "        x0 <- x1"
    ),
)

register_coming_soon(
    CHAPTER,
    "fixed_point",
    "Fixed-Point Iteration",
    "Solve x = g(x) by repeated substitution; converges when |g'(x)| < 1 near the root.",
    theory=(
        "A root of f(x) = 0 is rearranged into the fixed-point form x = g(x). Iterating "
        "x(k+1) = g(x(k)) converges to a fixed point when |g'(x)| < 1 in the "
        "neighbourhood of the solution; the smaller the derivative, the faster the "
        "convergence."
    ),
    pseudocode=(
        "FixedPoint(g, x0, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        x1 <- g(x0)\n"
        "        if |x1 - x0| < tol: return x1, k\n"
        "        x0 <- x1"
    ),
)

register_coming_soon(
    CHAPTER,
    "method_comparison",
    "Comparison of Root-Finding Methods",
    "Compare bisection, false position, secant, Newton-Raphson and fixed point.",
    theory=(
        "Bracketing methods (bisection, false position) are robust but slower, with "
        "linear or slightly super-linear convergence. Open methods (secant, "
        "Newton-Raphson) converge faster (super-linear/quadratic) but can diverge or "
        "leave the bracket. This topic compares convergence order, function evaluations "
        "and reliability so an appropriate method can be chosen for a given problem."
    ),
    pseudocode=(
        "Compare methods on a common problem:\n"
        "    record iterations, final error, convergence order, evaluations\n"
        "    tabulate and plot the convergence histories"
    ),
)

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
