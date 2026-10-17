"""Pydantic models: the unified response contract and method metadata schema.

Every solver — present and future — speaks these models, which keeps the API
stable and the frontend fully schema-driven.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

# ---------------------------------------------------------------------------
# Chapters (navigation / syllabus map)
# ---------------------------------------------------------------------------


class Chapter(StrEnum):
    """The six syllabus chapters the platform is organised around."""

    CH1_NONLINEAR = "ch1_nonlinear"
    CH2_LINEAR = "ch2_linear"
    CH3_INTERPOLATION = "ch3_interpolation"
    CH4_DIFF_INTEGRATION = "ch4_diff_integration"
    CH5_ODE = "ch5_ode"
    CH6_PDE = "ch6_pde"


CHAPTER_TITLES: dict[Chapter, str] = {
    Chapter.CH1_NONLINEAR: "Non-linear Equations",
    Chapter.CH2_LINEAR: "Linear Systems",
    Chapter.CH3_INTERPOLATION: "Interpolation",
    Chapter.CH4_DIFF_INTEGRATION: "Differentiation & Integration",
    Chapter.CH5_ODE: "Ordinary Differential Equations",
    Chapter.CH6_PDE: "Partial Differential Equations",
}

CHAPTER_DESCRIPTIONS: dict[Chapter, str] = {
    Chapter.CH1_NONLINEAR: "Roots of non-linear equations: bisection, Newton-Raphson, secant and more.",
    Chapter.CH2_LINEAR: "Direct and iterative solvers for systems of linear equations, eigenvalues.",
    Chapter.CH3_INTERPOLATION: "Polynomial interpolation, finite differences and least-squares fitting.",
    Chapter.CH4_DIFF_INTEGRATION: "Numerical differentiation and quadrature (Newton-Cotes, Romberg, Gauss).",
    Chapter.CH5_ODE: "Initial and boundary value problems: Euler, Runge-Kutta, shooting, finite differences.",
    Chapter.CH6_PDE: "Classification and finite-difference solutions: Laplace, heat and wave equations.",
}


class ChapterInfo(BaseModel):
    """Chapter card payload for the home page."""

    id: Chapter
    number: int
    title: str
    description: str
    method_count: int = 0
    available_count: int = 0


# ---------------------------------------------------------------------------
# Input schema (drives the auto-generated frontend forms)
# ---------------------------------------------------------------------------

FieldType = Literal[
    "function",
    "number",
    "integer",
    "boolean",
    "text",
    "select",
    "vector",
    "data_points",
    "matrix",
    "tolerance",
    "max_iterations",
    "precision",
]

NUMERIC_FIELD_TYPES: frozenset[str] = frozenset({"number", "tolerance"})
INTEGER_FIELD_TYPES: frozenset[str] = frozenset({"integer", "max_iterations", "precision"})


class SelectOption(BaseModel):
    value: str
    label: str


class InputField(BaseModel):
    """One input control on a method's form."""

    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    type: FieldType
    required: bool = True
    default: Any = None
    help: str = ""
    placeholder: str = ""
    min: float | None = None
    max: float | None = None
    variable: str | None = None  # for "function" fields, e.g. "x"
    rows: int | None = None  # initial rows for matrix fields
    cols: int | None = None
    options: list[SelectOption] = []


class MethodExample(BaseModel):
    """A ready-to-load demo problem shown via the 'Examples' button."""

    name: str
    inputs: dict[str, Any]
    description: str = ""


class LabeledLatex(BaseModel):
    label: str
    latex: str


class MethodStatus(StrEnum):
    AVAILABLE = "available"
    COMING_SOON = "coming_soon"


class MethodMeta(BaseModel):
    """A method's full metadata: theory, schema, examples (drives the UI)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    chapter: Chapter
    variables: list[str] = []  # symbols the keypad may offer (e.g. ["x", "y"])
    name: str
    status: MethodStatus = MethodStatus.AVAILABLE
    summary: str = ""
    theory: str = ""
    pseudocode: str = ""
    formulas: list[LabeledLatex] = []
    input_schema: list[InputField]
    examples: list[MethodExample] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chapter_title(self) -> str:
        return CHAPTER_TITLES[self.chapter]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def chapter_number(self) -> int:
        return int(self.chapter.value.split("_", maxsplit=1)[0].replace("ch", ""))


class MethodCatalog(BaseModel):
    """Response of GET /api/methods."""

    chapters: list[ChapterInfo]
    methods: list[MethodMeta]


# ---------------------------------------------------------------------------
# Unified solve response contract
# ---------------------------------------------------------------------------


class SolveStatus(StrEnum):
    CONVERGED = "converged"
    DIVERGED = "diverged"
    MAX_ITER = "max_iter"
    FAILED = "failed"


class Step(BaseModel):
    """One exam-style working step, rendered with KaTeX on the frontend."""

    title: str
    latex: str = ""
    note: str = ""


class DataTable(BaseModel):
    """One iteration / difference table."""

    title: str
    columns: list[str]
    rows: list[list[Any]]


class PlotPayload(BaseModel):
    """Plotly figure fragment; solvers only fill data, never styling defaults."""

    traces: list[dict[str, Any]] = []
    layout: dict[str, Any] = {}


class ErrorInfo(BaseModel):
    absolute: float | None = None
    relative_percent: float | None = None
    order_of_convergence: float | None = None


class SolveResponse(BaseModel):
    """The single response shape returned by every solver (see master prompt)."""

    method: str
    status: SolveStatus
    result: dict[str, Any] = {}
    steps: list[Step] = []
    tables: list[DataTable] = []
    plot: PlotPayload = Field(default_factory=PlotPayload)
    errors: ErrorInfo = Field(default_factory=ErrorInfo)
    warnings: list[str] = []
    pseudocode: str = ""
    python_source: str = ""


# ---------------------------------------------------------------------------
# Runtime limits passed into solvers (keeps them pure and configurable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SolverLimits:
    """Safety budget handed to every solver call."""

    timeout_seconds: float = 10.0
    max_iterations: int = 10_000
    max_matrix_size: int = 50
