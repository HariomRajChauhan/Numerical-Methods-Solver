"""Chapter 2 coming-soon stubs.

Only the power method remains as a stub; the direct solvers and the iterative
methods (Jacobi, Gauss-Seidel) now have real solver modules.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH2_LINEAR

register_coming_soon(
    CHAPTER,
    "power_method",
    "Power Method (Eigenvalues)",
    "Find the dominant eigenvalue and its eigenvector by repeated multiplication by A.",
    theory=(
        "Repeatedly multiplying a vector by A amplifies the component along the "
        "eigenvector of the largest-magnitude eigenvalue, so the vector direction "
        "converges to that eigenvector and the Rayleigh quotient to the dominant "
        "eigenvalue. It requires the dominant eigenvalue to be strictly larger in "
        "magnitude than the others."
    ),
    pseudocode=(
        "PowerMethod(A, x0, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        y <- A x\n"
        "        lambda <- largest |component| of y      # or ||y|| / ||x||\n"
        "        x <- y / ||y||\n"
        "        if |lambda - lambda_prev| < tol: return lambda, x"
    ),
)
