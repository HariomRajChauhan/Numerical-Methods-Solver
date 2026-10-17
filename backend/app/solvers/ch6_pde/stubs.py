"""Coming-soon stubs for Chapter 6 — Partial Differential Equations (ENSH 252 syllabus).

Stubs use ``register_coming_soon`` from ``app.solvers._common``; every method
imports it the same way until a real solver replaces the stub.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH6_PDE

register_coming_soon(
    CHAPTER,
    "pde_classification",
    "Classification of PDEs",
    "Classify a second-order PDE as elliptic, parabolic or hyperbolic from its discriminant.",
    theory=(
        "A second-order linear PDE A u_xx + B u_xy + C u_yy + ... is classified by the "
        "discriminant B^2 - 4AC: negative gives elliptic (e.g. Laplace/Poisson, "
        "steady state), zero gives parabolic (e.g. heat, diffusion) and positive gives "
        "hyperbolic (e.g. wave, vibration). The class dictates which finite-difference "
        "scheme and which boundary/initial conditions apply."
    ),
    pseudocode=(
        "Classify(A, B, C):\n"
        "    D <- B^2 - 4AC\n"
        "    D < 0 -> elliptic;  D = 0 -> parabolic;  D > 0 -> hyperbolic"
    ),
)

register_coming_soon(
    CHAPTER,
    "fd_approximations",
    "Finite Difference Approximations for PDEs",
    "Forward/backward/central difference formulas used to discretise PDE derivatives.",
    theory=(
        "Partial derivatives are replaced by finite differences on a mesh: forward or "
        "backward differences for time (first-order) and central differences for space "
        "(second-order). The resulting difference equation, with the boundary and "
        "initial conditions, is marched or solved to approximate the PDE."
    ),
    pseudocode=(
        "Approximations(h, k):\n"
        "    u_x  ~ (u[i+1,j] - u[i-1,j])/(2h)              # central in space\n"
        "    u_xx ~ (u[i+1,j] - 2u[i,j] + u[i-1,j])/h^2\n"
        "    u_t  ~ (u[i,j+1] - u[i,j])/k                   # forward in time"
    ),
)

register_coming_soon(
    CHAPTER,
    "laplace",
    "Laplace Equation",
    "Solve the steady-state (Laplace) equation on a grid by finite differences.",
    theory=(
        "The Laplace equation u_xx + u_yy = 0 governs steady-state problems. "
        "Discretising the second derivatives gives u(i,j) = (u(i-1,j) + u(i+1,j) + "
        "u(i,j-1) + u(i,j+1))/4 at each interior node, solved iteratively "
        "(Gauss-Seidel/Liebmann) or directly."
    ),
    pseudocode=(
        "Laplace(grid, boundary, tol, max_iter):\n"
        "    initialise the interior to 0\n"
        "    repeat:\n"
        "        for each interior (i, j): u[i][j] <- average of its 4 neighbours\n"
        "    until max change < tol"
    ),
)

register_coming_soon(
    CHAPTER,
    "poisson",
    "Poisson Equation",
    "Solve the non-homogeneous steady-state equation u_xx + u_yy = f on a grid.",
    theory=(
        "The Poisson equation adds a source term to Laplace's equation. Discretising "
        "with the 5-point stencil gives u(i,j) = (sum of the four neighbours - "
        "h^2 f(i,j))/4, solved iteratively (Gauss-Seidel, SOR) or directly."
    ),
    pseudocode=(
        "Poisson(grid, f, boundary, tol, max_iter):\n"
        "    repeat:\n"
        "        for each interior (i, j):\n"
        "            u[i][j] <- (u[i-1,j]+u[i+1,j]+u[i,j-1]+u[i,j+1] - h^2 f[i][j]) / 4\n"
        "    until max change < tol"
    ),
)

register_coming_soon(
    CHAPTER,
    "heat_bendre_schmidt",
    "Heat Equation (Bender-Schmidt)",
    "Explicit finite-difference scheme for the 1-D heat equation; stable when r <= 1/2.",
    theory=(
        "The Bender-Schmidt explicit scheme advances u from neighbouring space nodes at "
        "the previous time level. It is stable only when r = alpha*k/h^2 <= 1/2; "
        "choosing r = 1/2 gives the classic simple averaging form but ties the time step "
        "to the space step."
    ),
    pseudocode=(
        "BenderSchmidt(alpha, u0, h, k, steps):     # r = alpha*k/h^2 <= 1/2\n"
        "    for each time step:\n"
        "        for each interior i:\n"
        "            u_new[i] <- (1 - 2r)*u[i] + r*(u[i-1] + u[i+1])"
    ),
)

register_coming_soon(
    CHAPTER,
    "heat_crank_nicolson",
    "Heat Equation (Crank-Nicolson)",
    "Implicit, unconditionally stable scheme averaging the two time levels.",
    theory=(
        "Crank-Nicolson averages the spatial difference at the current and next time "
        "levels, giving O(k^2 + h^2) accuracy and unconditional stability for any time "
        "step. Each step requires solving a tridiagonal system for the new values."
    ),
    pseudocode=(
        "CrankNicolson(alpha, u0, h, k, steps):\n"
        "    r <- alpha*k/(2h^2)\n"
        "    each step solve the tridiagonal system:\n"
        "        -r*u_new[i-1] + (1+2r)*u_new[i] - r*u_new[i+1]\n"
        "            = r*u_old[i-1] + (1-2r)*u_old[i] + r*u_old[i+1]"
    ),
)

register_coming_soon(
    CHAPTER,
    "wave",
    "Wave Equation",
    "Solve the 1-D hyperbolic wave equation u_tt = c^2 u_xx with an explicit scheme.",
    theory=(
        "The wave equation models vibrating strings and wave propagation. A central "
        "difference in both space and time advances the solution from the two previous "
        "time levels, and the scheme is stable when the Courant number c*k/h <= 1."
    ),
    pseudocode=(
        "WaveExplicit(c, u0, u1, h, k, steps):\n"
        "    r <- (c*k/h)^2\n"
        "    for each time step and interior i:\n"
        "        u_new[i] <- 2*u[i] - u_prev[i] + r*(u[i-1] - 2*u[i] + u[i+1])"
    ),
)
