# Numerical Methods Solver

All-in-one web platform that solves numerical-methods problems for engineering
students (ENSH 252, IOE / Tribhuvan University): the final answer, exam-style
step-by-step working, iteration tables, an interactive graph, error/convergence
information, a downloadable PDF/CSV report, and the method's theory, pseudocode
and Python source.

The platform is **schema-driven and registry-based**: the frontend renders every
form, page and navigation entry from metadata the backend serves, and the backend
discovers solvers automatically. Adding a method means adding one solver file and
one test file — no router or UI changes.

## Highlights

- **Exam-style working** — each method emits LaTeX steps rendered with KaTeX.
- **Interactive graphs** — Plotly figures built by the solvers (curve + root marker, etc.).
- **Error & convergence** — absolute/relative error and order of convergence where applicable.
- **Reports** — download a formatted PDF (reportlab) or a CSV of the iteration table.
- **Safe expression parsing** — user formulas go through SymPy with a whitelist; no `eval`/`exec`.
  Pasted notation is normalised (`−`→`-`, `×`→`*`, `÷`→`/`, `π`→`pi`, `√(`→`sqrt(`, `x²`→`x^2`).
- **On-screen keypad** — a shared, tabbed keypad (numbers / operators / functions /
  variables / edit) inserts at the cursor, shows a live KaTeX preview and remembers
  its open state in `localStorage`; matrix and vector inputs get a compact numeric pad.
- **Robust by construction** — per-request timeout, iteration/matrix caps, rate limiting.
- **51 methods in the catalogue** — 9 available and 42 syllabus methods as
  navigable "coming soon" stubs with theory and pseudocode already readable.

## Stack

- **Frontend:** React 19 + Vite + TypeScript, Tailwind CSS, React Router, Zustand,
  Plotly.js, KaTeX, mathjs (input preview/validation only).
- **Backend:** Python 3.11+, FastAPI, Pydantic v2, NumPy, SciPy, SymPy, reportlab.
- **Tests:** pytest (backend, 361 tests), Vitest + Testing Library (frontend, 45 tests).
- **Packaging:** Docker + docker-compose, `.env` configuration.

## Project structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI routers: health, methods, solve, export
│   │   ├── core/           # config, models, parser, registry, validation, errors, rate_limit
│   │   ├── reports/        # PDF (reportlab) and CSV report builders
│   │   ├── solvers/        # one folder per chapter; auto-discovered
│   │   │   ├── _common.py  # shared plotting/registration helpers (not a solver)
│   │   │   ├── ch1_nonlinear/{bisection.py, stubs.py}
│   │   │   └── ch2_linear/ … ch6_pde/
│   │   └── main.py         # app factory (lifespan loads all solvers)
│   ├── tests/              # pytest suite
│   ├── pyproject.toml      # deps + ruff/mypy/pytest config
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/client.ts   # the only module that knows the backend URL
│   │   ├── components/     # schema-driven form fields, panels, tabs, export buttons
│   │   ├── pages/          # Home, Chapter, MethodSolver, About, NotFound
│   │   ├── store/          # zustand stores (catalog, solver, theme)
│   │   ├── hooks/, utils/, types/
│   │   └── test/           # vitest suite
│   ├── vite.config.ts      # dev /api proxy + vendor chunking
│   ├── nginx.conf          # SPA fallback + /api proxy (production)
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Quick start (local dev)

### 1. Backend

```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e .                       # runtime deps
pip install pytest pytest-cov httpx ruff mypy   # dev tools (pip >= 25.1: pip install -e . --group dev)
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: <http://localhost:8000/docs> · health: <http://localhost:8000/api/health>

### 2. Frontend

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The Vite dev server proxies `/api` to `http://localhost:8000`, so browser requests
are same-origin and **CORS never applies in local development**. `VITE_API_BASE_URL`
is therefore left empty (see `frontend/.env.example`).

### 3. Open the app

Visit <http://localhost:5173>, pick a chapter, then a method (e.g. Bisection).

## Quick start (Docker)

```bash
docker compose up --build
# frontend: http://localhost:5173   backend API: http://localhost:8000/api
```

The frontend container serves the built SPA through nginx, which also proxies
`/api/` to the backend service — again same-origin, no CORS.

## Configuration

Copy `.env.example` to `.env` (root) and adjust. Backend settings use the
`Settings` class in `backend/app/core/config.py`:

| Variable | Default | Purpose |
| --- | --- | --- |
| `API_PREFIX` | `/api` | Prefix for every route. |
| `CORS_ORIGINS` | `localhost:5173,127.0.0.1:5173,localhost:3000,127.0.0.1:3000` | Comma-separated allowed origins (only relevant if you bypass the proxy). |
| `RATE_LIMIT_PER_MINUTE` | `60` | Per-IP limit for `/solve` and `/export`. |
| `SOLVER_TIMEOUT_SECONDS` | `10` | Wall-clock budget per solve. |
| `MAX_ITERATIONS_LIMIT` | `10000` | Cap solvers must respect. |
| `MAX_MATRIX_SIZE` | `50` | Largest accepted matrix dimension. |

Frontend: `VITE_API_BASE_URL` (leave empty for same-origin; set a full URL only for
a remote backend).

## API reference

| Method & path | Purpose |
| --- | --- |
| `GET /api/health` | Liveness probe. |
| `GET /api/methods` | Chapter cards + all method metadata (drives all navigation and forms). |
| `GET /api/methods/{id}` | Full metadata for one method (schema, theory, formulas, pseudocode, examples). |
| `POST /api/solve/{id}` | Validate inputs, run the solver, return the unified contract. |
| `POST /api/export/{id}?format=pdf\|csv` | Re-run the solver and stream a downloadable report. |

Error responses are always JSON `{ "detail": ..., "code": ..., "hint": ... }` with
friendly messages. Notable codes: `invalid_input` (400), `expression_error` (400),
`method_not_found` (404), `method_unavailable` (409 for stubs), `timeout` (408),
`rate_limited` (429).

The distinction between a **400 error** and a **200 `failed`** response is
deliberate and applied consistently across every solver:

- **HTTP 400** is reserved for *malformed or invalid input*: an expression that
  cannot be parsed (`expression_error`), a non-bracketing interval, equal bounds
  (`a == b`) or equal starting guesses (`x0 == x1`), plus the schema checks run by
  `validate_inputs` (missing/invalid numbers, negative tolerance, …).
- **HTTP 200 with `status: "failed"`** is returned when the method *starts but
  breaks down for a mathematical reason*: `f'(x) = 0` (horizontal tangent or an
  identically zero derivative), `f(x0) = f(x1)` (a flat secant), or any division by
  zero. The response carries a `warnings` message explaining the breakdown, so the
  UI can display it like any other result instead of an error banner.

### The solver contract

Every solver returns the same `SolveResponse`:

```jsonc
{
  "method": "bisection",
  "status": "converged",          // converged | diverged | max_iter | failed
  "result": { "root": 1.3247, "iterations": 20 },
  "steps":  [ { "title": "Iteration 1", "latex": "c_1 = ...", "note": "..." } ],
  "tables": [ { "title": "Bisection iterations", "columns": ["Iteration", "..."], "rows": [[1, "..."]] } ],
  "plot":   { "traces": [ ... ], "layout": { ... } },
  "errors": { "absolute": 9.5e-7, "relative_percent": 7.2e-5, "order_of_convergence": 1.0 },
  "warnings": [],
  "pseudocode": "Bisection(f, a, b, ...)",
  "python_source": "def solve(inputs, limits): ..."
}
```

## How to add a new method

Adding a method is a two-file change (solver + test); the catalogue, chapter page,
sidebar, search, the auto-generated form, the method page and the export endpoint
all update themselves.

**1. Create the solver file** in its chapter folder, named after the method id
(`backend/app/solvers/<chapter>/<method_id>.py`). Chapter folders are
`ch1_nonlinear`, `ch2_linear`, `ch3_interpolation`, `ch4_diff_integration`,
`ch5_ode`, `ch6_pde`.

**2. Describe the method** with a `MethodMeta` and implement a pure `solve`.

```python
from typing import Any

from app.core.models import (
    Chapter, ErrorInfo, InputField, MethodExample, MethodMeta,
    SolveResponse, SolveStatus, SolverLimits, Step,
)
from app.core.parser import make_function, parse_expression
from app.core.registry import register

META = MethodMeta(
    id="fixed_point",
    chapter=Chapter.CH1_NONLINEAR,
    variables=["x"],  # optional; drives the keypad variable tab
    name="Fixed-Point Iteration",
    summary="Solve x = g(x) by repeated substitution.",
    theory="Iterate x(k+1) = g(x(k)); converges when |g'(x)| < 1 near the root.",
    pseudocode="FixedPoint(g, x0, tol, max_iter):\n    ...",
    input_schema=[
        InputField(key="function", label="Iteration function g(x)", type="function", variable="x"),
        InputField(key="x0", label="Initial guess x0", type="number", default=1.0),
        InputField(key="tolerance", label="Tolerance", type="tolerance",
                   default=1e-6, min=1e-15, max=1.0),
        InputField(key="max_iterations", label="Maximum iterations", type="max_iterations",
                   default=50, min=1, max=10_000),
    ],
    examples=[
        MethodExample(
            name="cos(x)",
            description="Fixed point of cosine near 0.7391.",
            inputs={"function": "cos(x)", "x0": 1.0, "tolerance": 1e-6, "max_iterations": 50},
        ),
    ],
)


@register(META)
def solve(inputs: dict[str, Any], limits: SolverLimits) -> SolveResponse:
    expression = parse_expression(inputs["function"], ("x",))
    g = make_function(expression, ("x",), strict=True)
    x = float(inputs["x0"])
    tolerance = float(inputs["tolerance"])
    max_iterations = min(int(inputs["max_iterations"]), limits.max_iterations)

    steps: list[Step] = []
    for k in range(1, max_iterations + 1):
        next_x = g(x)
        steps.append(Step(title=f"Iteration {k}",
                          latex=f"x_{{{k}}} = g(x_{{{k - 1}}}) = {next_x:.10g}"))
        if abs(next_x - x) < tolerance:
            return SolveResponse(
                method=META.id,
                status=SolveStatus.CONVERGED,
                result={"root": next_x, "iterations": k},
                steps=steps,
                errors=ErrorInfo(absolute=abs(next_x - x)),
            )
        x = next_x

    return SolveResponse(
        method=META.id,
        status=SolveStatus.MAX_ITER,
        result={"root": x, "iterations": max_iterations},
        steps=steps,
        warnings=["The tolerance was not reached within the iteration limit."],
    )
```

**3. If a coming-soon stub exists for that id, remove it.** Delete the matching
`register_coming_soon(...)` call from the chapter's `stubs.py`. Registering two
methods with the same id raises a `RegistrationError` at startup, so the app will
tell you if you forget.

**4. Add a test file** `backend/tests/test_<method_id>.py` covering the solver
directly and through the API (mirror `backend/tests/test_bisection.py`).

**5. Run the checks** (below). No frontend or router edits are needed — redeploying
the backend is enough for the method to appear everywhere.

### Input field types

Pick a `type` per field; the frontend renders the matching control and the backend
validates/coerces it (`app/core/validation.py`).

| `type` | Control | Delivered to `solve` as |
| --- | --- | --- |
| `function` | expression box (parsed early) | `str` (re-parse with `parse_expression`) |
| `number`, `tolerance` | number input | `float` |
| `integer`, `max_iterations`, `precision` | integer input | `int` |
| `boolean` | checkbox | `bool` |
| `text`, `select` | text input / dropdown (a `rows` value renders a textarea) | `str` |
| `vector` | comma/space list | `list[float]` |
| `data_points` | `x,y; x,y; …` | `list[[x, y]]` |
| `matrix` | editable grid | `list[list[float]]` |

Useful building blocks: `app/solvers/_common.py` (`sample_curve`, `line_trace`,
`marker_trace`), `app/core/parser.py` (`parse_expression`, `make_function`,
`expr_to_latex`), `app/core/errors.py` (`InvalidInputError`, `EvaluationError`),
and `app/core/utils.py` (`to_builtin`, `split_points`, `float_list`). Raise
`InvalidInputError`/`EvaluationError` for student-friendly messages; the API layer
converts them into 400 responses.

System methods (`ch1_nonlinear/nonlinear_system_*`) accept several equations per
`text` field separated by `;`, a newline **or a comma** (top-level commas only, so
calls such as `Max(x, y)` survive), and tolerate the unicode notation above. An
equation may be written either as an expression or as `left = right`.

### The expression keypad

Every `function`/`text` field shows a shared, schema-driven **keypad** (`frontend/src/components/fields/MathKeypad.tsx`).
It has no method-specific code: the **Variables** tab is fed from `MethodMeta.variables`
(falling back to each field's `variable`). The keypad remembers its open/hidden state
in `localStorage` (`nms.keypad.open`; numeric keypads use `nms.keypad.numeric.open`),
inserts at the caret (never overwriting the field), and every key updates the live
KaTeX preview. `matrix`/`vector` fields get a compact numeric keypad
(0-9, `.`, `-`, `/`); matrix cells are also navigable with the arrow keys (and `Tab`).

## Checks (quality gates)

Run all of these before considering a change done:

```bash
# Backend
cd backend
ruff check .
mypy
pytest

# Frontend
cd frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Roadmap / status

| Chapter | Methods | Status |
| --- | --- | --- |
| 1 · Non-linear Equations | errors_accuracy, Bisection, false_position, secant, Newton-Raphson, Fixed-Point Iteration, Method Comparison, nonlinear_system_direct, nonlinear_system_newton | Available |
| 2 · Linear Systems | gauss_jordan, gauss_elimination, matrix_inverse, doolittle, crout, jacobi, gauss_seidel, power_method | Coming soon |
| 3 · Interpolation | finite_differences, newton_forward, newton_backward, stirling, bessel, newton_divided_difference, lagrange, least_squares, cubic_spline | Coming soon |
| 4 · Differentiation & Integration | numerical_differentiation, local_extrema, newton_cotes, trapezoidal, simpson_13, simpson_38, boole, weddle, romberg, gauss_legendre | Coming soon |
| 5 · ODEs | taylor_series, euler, runge_kutta_2, runge_kutta_4, ode_system_rk, ode_second_order_rk, bvp_shooting, bvp_finite_difference | Coming soon |
| 6 · PDEs | pde_classification, fd_approximations, laplace, poisson, heat_bendre_schmidt, heat_crank_nicolson, wave | Coming soon |

Coming-soon methods are fully navigable: their theory and pseudocode are already
readable, and the API returns `409 method_unavailable` if a solve is attempted.
