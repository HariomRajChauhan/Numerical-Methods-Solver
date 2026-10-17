"""Chapter 2 coming-soon stubs.

Only the iterative / eigenvalue methods remain as stubs; the direct solvers
(Gauss-Jordan, Gauss elimination, matrix inversion and the LU decompositions)
now have real solver modules. Every stub imports ``register_coming_soon`` the
same way until a real solver replaces it.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH2_LINEAR

register_coming_soon(
    CHAPTER,
    "jacobi",
    "Jacobi Iteration",
    "Iterative solver updating all unknowns from the previous sweep; needs diagonal dominance.",
    theory=(
        "The Jacobi method solves each equation for one unknown and updates all "
        "unknowns simultaneously using values from the previous iteration. It converges "
        "when A is diagonally dominant, but is slower than Gauss-Seidel and needs a "
        "reasonable starting vector."
    ),
    pseudocode=(
        "Jacobi(A, b, x0, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        for i: x_new[i] <- (b[i] - sum_{j!=i} A[i][j] x_old[j]) / A[i][i]\n"
        "        if ||x_new - x_old|| < tol: return x_new, k\n"
        "        x_old <- x_new"
    ),
)

register_coming_soon(
    CHAPTER,
    "gauss_seidel",
    "Gauss-Seidel Iteration",
    "Like Jacobi but reuses each updated value immediately; converges roughly twice as fast.",
    theory=(
        "Gauss-Seidel updates the unknowns one at a time and immediately reuses the "
        "freshest values within the same sweep. This typically converges about twice as "
        "fast as Jacobi and converges for a wider class of matrices (diagonally "
        "dominant or symmetric positive-definite)."
    ),
    pseudocode=(
        "GaussSeidel(A, b, x, tol, max_iter):\n"
        "    for k = 1 to max_iter:\n"
        "        for i: x[i] <- (b[i] - sum_{j!=i} A[i][j] x[j]) / A[i][i]   # fresh x[j]\n"
        "        if ||x - x_prev|| < tol: return x, k"
    ),
)

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
