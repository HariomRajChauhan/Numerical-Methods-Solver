"""Coming-soon stubs for Chapter 5 — Ordinary Differential Equations (ENSH 252 syllabus).

Stubs use ``register_coming_soon`` from ``app.solvers._common``; every method
imports it the same way until a real solver replaces the stub.
"""

from __future__ import annotations

from app.core.models import Chapter
from app.solvers._common import register_coming_soon

CHAPTER = Chapter.CH5_ODE

register_coming_soon(
    CHAPTER,
    "ode_system_rk",
    "Systems of ODEs (Runge-Kutta)",
    "Solve a system of first-order ODEs simultaneously with RK4.",
    theory=(
        "A system y' = f(x, y) with a vector y is advanced with RK4 by applying the "
        "four-stage scheme to every component at once. This is how coupled equations and "
        "higher-order ODEs (converted to first-order systems) are solved."
    ),
    pseudocode=(
        "RK4System(f, x0, y0 vector, h, n):\n"
        "    for k = 0..n-1:\n"
        "        K1<-f(x,y); K2<-f(x+h/2, y+h K1/2); K3<-f(x+h/2, y+h K2/2); K4<-f(x+h, y+h K3)\n"
        "        y <- y + h/6*(K1 + 2K2 + 2K3 + K4)      # vector update\n"
        "        x <- x + h"
    ),
)

register_coming_soon(
    CHAPTER,
    "ode_second_order_rk",
    "Second-Order ODEs (Runge-Kutta)",
    "Solve y'' = f(x, y, y') by reducing it to a first-order system and applying RK4.",
    theory=(
        "A second-order ODE is rewritten as two first-order equations by introducing "
        "v = y', giving y' = v and v' = f(x, y, v). RK4 then advances (y, v) together, "
        "the standard approach for vibrating systems and deflection problems."
    ),
    pseudocode=(
        "RK4SecondOrder(f, x0, y0, yp0, h, n):\n"
        "    set y' = v and v' = f(x, y, v)\n"
        "    apply RK4 to the two-component system (y, v)"
    ),
)

register_coming_soon(
    CHAPTER,
    "bvp_shooting",
    "Boundary Value Problems (Shooting)",
    "Solve a BVP by guessing the missing initial slope and correcting it to hit the boundary.",
    theory=(
        "The shooting method converts a boundary value problem into a root-finding "
        "problem: guess the unknown initial slope, integrate the initial value problem "
        "to the far end, and adjust the guess until the computed endpoint matches the "
        "given boundary condition (e.g. by secant or Newton iteration)."
    ),
    pseudocode=(
        "ShootingBVP(f, a, b, ya, yb, tol):\n"
        "    guess the slope s\n"
        "    integrate the IVP from a to b with y(a)=ya, y'(a)=s  ->  y(b; s)\n"
        "    adjust s until y(b; s) = yb"
    ),
)

register_coming_soon(
    CHAPTER,
    "bvp_finite_difference",
    "Boundary Value Problems (Finite Difference)",
    "Discretise the BVP on a grid and solve the resulting tridiagonal system.",
    theory=(
        "The finite-difference method replaces y' and y'' with central differences on a "
        "grid of points, giving a linear (usually tridiagonal) system for the interior "
        "values with the boundary values moved to the right-hand side. It is solved "
        "directly or iteratively."
    ),
    pseudocode=(
        "FiniteDifferenceBVP(p, q, r, a, b, ya, yb, n):\n"
        "    discretise y'' with central differences on the grid\n"
        "    assemble and solve the tridiagonal system for y_i"
    ),
)
