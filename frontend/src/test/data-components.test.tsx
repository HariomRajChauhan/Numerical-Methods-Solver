import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { StepsPanel } from "../components/StepsPanel";
import { DataTable } from "../components/DataTable";
import { CodePanel } from "../components/CodePanel";
import { ResultHeader } from "../components/ResultHeader";
import type { SolveResponse } from "../types/api";

const MOCK_SOLVE_RESPONSE: SolveResponse = {
  method: "bisection",
  status: "converged",
  result: { root: 1.414213 },
  steps: [
    { title: "Initial guess", latex: "x_0 = 1.0", note: "Given" },
    { title: "First iteration", latex: "x_1 = 1.5", note: "Converging" },
  ],
  tables: [
    {
      title: "Bisection Iterations",
      columns: ["i", "a", "b", "c", "f(c)"],
      rows: [
        [0, 1.0, 2.0, 1.5, 0.25],
        [1, 1.0, 1.5, 1.25, -0.12],
      ],
    },
  ],
  plot: { traces: [], layout: {} },
  errors: { absolute: 0.001, relative_percent: 0.05, order_of_convergence: 1.0 },
  warnings: ["Function changes sign."],
  pseudocode: "while b - a > tol:\n    c = (a + b) / 2",
  python_source: "def bisection(f, a, b):\n    return c",
};

describe("Phase 4 Data Components", () => {
  it("renders steps timeline with working items", () => {
    render(
      <StepsPanel
        steps={[
          { title: "Initial guess", latex: "x_0 = 1.0", note: "Given" },
          { title: "First iteration", latex: "x_1 = 1.5", note: "Converging" },
        ]}
      />
    );
    expect(screen.getByText("Initial guess")).toBeInTheDocument();
    expect(screen.getAllByText("First iteration").length).toBeGreaterThan(0);
  });

  it("renders tables with sticky columns and download options", () => {
    render(
      <DataTable
        table={{
          title: "Iteration Table",
          columns: ["i", "x_i"],
          rows: [
            [0, 1.0],
            [1, 1.5],
          ],
        }}
      />
    );
    expect(screen.getByText("Iteration Table")).toBeInTheDocument();
    expect(screen.getByText("Copy table")).toBeInTheDocument();
  });

  it("renders code block with syntax and copy", () => {
    render(<CodePanel title="Python Implementation" code="print('hello')" language="python" />);
    expect(screen.getByText("Python Implementation")).toBeInTheDocument();
    expect(screen.getByText("print('hello')")).toBeInTheDocument();
  });

  it("renders result header with headline answer, stat row, summary and warnings", () => {
    render(<ResultHeader response={MOCK_SOLVE_RESPONSE} />);
    expect(screen.getByTestId("result-headline")).toBeInTheDocument();
    expect(screen.getByTestId("stat-row")).toBeInTheDocument();
    expect(screen.getByTestId("result-summary")).toBeInTheDocument();
    expect(screen.getByText("Function changes sign.")).toBeInTheDocument();
  });
});
