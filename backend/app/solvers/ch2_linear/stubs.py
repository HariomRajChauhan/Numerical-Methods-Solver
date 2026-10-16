"""Coming-soon stubs for Chapter 2 — Linear Systems (ENSH 252 syllabus).

See ``ch1_nonlinear/stubs.py`` for the pattern.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH2_LINEAR

register_coming_soon(
    CHAPTER,
    "gauss_jordan",
    "Gauss-Jordan Elimination",
    "Reduce the augmented matrix to reduced row-echelon form to read the solution directly.",
    theory=(
        "Gauss-Jordan elimination continues eliminating above each pivot as well, "
        "producing reduced row-echelon form so every unknown is read directly without "
        "back-substitution. Applying the same steps to an identity matrix yields the "
        "matrix inverse A^-1."
    ),
    pseudocode=(
        "GaussJordan(A, b):\n"
        "    for each column k:\n"
        "        normalise row k by the pivot A[k][k]\n"
        "        eliminate column k from every other row\n"
        "    solution is the final column"
    ),
)

register_coming_soon(
    CHAPTER,
    "gauss_elimination",
    "Gauss Elimination",
    "Solve Ax = b by forward elimination then back-substitution, with partial or complete pivoting.",
    theory=(
        "Gauss elimination reduces the augmented matrix [A|b] to upper-triangular form "
        "with elementary row operations, then recovers the unknowns by "
        "back-substitution. Stability is improved by pivoting: partial pivoting swaps "
        "rows to bring the largest available pivot to the diagonal, while complete "
        "pivoting also swaps columns to use the largest element of the submatrix. The "
        "pivoting strategy can be selected as an option."
    ),
    pseudocode=(
        "GaussElimination(A, b, pivoting='partial'):\n"
        "    for k = 1 to n-1:\n"
        "        choose the pivot (largest |A[i][k]| for partial, whole submatrix for complete)\n"
        "        swap rows (and columns) accordingly\n"
        "        eliminate the entries below the pivot\n"
        "    back-substitute to obtain x"
    ),
)

register_coming_soon(
    CHAPTER,
    "matrix_inverse",
    "Matrix Inversion",
    "Compute A^-1 by applying Gauss-Jordan elimination to [A | I].",
    theory=(
        "The inverse is found by augmenting A with the identity matrix and reducing the "
        "left block to the identity with Gauss-Jordan elimination; the right block then "
        "becomes A^-1. It exists only when A is non-singular, and partial pivoting is "
        "used to improve numerical stability."
    ),
    pseudocode=(
        "Inverse(A):\n"
        "    form the augmented matrix [A | I]\n"
        "    Gauss-Jordan reduce the left block to I\n"
        "    return the right block, now A^-1"
    ),
)

register_coming_soon(
    CHAPTER,
    "doolittle",
    "Doolittle's LU Method",
    "LU factorisation with unit lower-triangular L, so U carries the pivots.",
    theory=(
        "Doolittle's method factors A = L U where L is unit lower-triangular (ones on "
        "the diagonal) and U is upper-triangular. The factors are computed column by "
        "column from the standard LU equations; forward and back substitution then solve "
        "A x = b cheaply for repeated right-hand sides."
    ),
    pseudocode=(
        "Doolittle(A):\n"
        "    for k = 1..n:\n"
        "        U[k][j] <- A[k][j] - sum_{s<k} L[k][s]*U[s][j]\n"
        "        L[i][k] <- (A[i][k] - sum_{s<k} L[i][s]*U[s][k]) / U[k][k]"
    ),
)

register_coming_soon(
    CHAPTER,
    "crout",
    "Crout's LU Method",
    "LU factorisation with unit upper-triangular U, so L carries the pivots.",
    theory=(
        "Crout's method is the transpose arrangement of Doolittle: L is lower-triangular "
        "with the pivots on its diagonal and U is unit upper-triangular. Both give the "
        "same A = L U factorisation, differing only in where the divisions fall."
    ),
    pseudocode=(
        "Crout(A):\n"
        "    for k = 1..n:\n"
        "        L[i][k] <- A[i][k] - sum_{s<k} L[i][s]*U[s][k]\n"
        "        U[k][j] <- (A[k][j] - sum_{s<k} L[k][s]*U[s][j]) / L[k][k]"
    ),
)

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
